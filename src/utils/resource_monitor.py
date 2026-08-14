"""
Moniteur de ressources système — échantillonne CPU / RAM / disque / réseau / GPU
en tâche de fond pendant l'exécution de l'application, puis génère un rapport
Plotly HTML autonome (ouvrable dans un navigateur, sans serveur).

Pourquoi : donner à la DSI une preuve chiffrée de l'empreinte réelle de MISPL Agent
sur la machine hôte (dimensionnement, coût énergétique, détection de fuite mémoire).

Usage :
    from src.utils.resource_monitor import start_monitoring
    start_monitoring()          # démarre le thread + flush auto à l'arrêt (atexit)

    # ou en autonome pour un benchmark ponctuel :
    python src/utils/resource_monitor.py --duration 60 --interval 1
"""

from __future__ import annotations

import atexit
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

try:
    import GPUtil
    _GPU_OK = True
except Exception:
    _GPU_OK = False


ROOT = Path(__file__).parent.parent.parent
MONITOR_DIR = ROOT / "outputs" / "monitoring"

# Intervalle d'échantillonnage par défaut (secondes). 2 s = compromis
# précision / surcoût négligeable (le monitoring ne doit pas fausser la mesure).
DEFAULT_INTERVAL = 2.0


class ResourceMonitor:
    """
    Échantillonneur de ressources en thread démon.

    Collecte à chaque tick : horodatage, CPU %, RAM (% + Mo), disque (% + I/O
    cumulés en Mo), réseau (envoyé/reçu cumulés en Mo), GPU (charge % + VRAM Mo
    + température) si un GPU NVIDIA est présent.
    """

    def __init__(self, interval: float = DEFAULT_INTERVAL):
        self.interval = interval
        self._samples: list[dict[str, Any]] = []
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._started_at: datetime | None = None
        # Compteurs cumulés de départ (pour calculer les deltas I/O et réseau)
        self._disk0 = psutil.disk_io_counters()
        self._net0 = psutil.net_io_counters()
        # Amorce cpu_percent (le 1er appel renvoie 0.0, on l'initialise ici)
        psutil.cpu_percent(interval=None)

    # ── Boucle d'échantillonnage ─────────────────────────────────────────────

    def _sample(self) -> dict[str, Any]:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(str(ROOT.anchor or "/"))
        dio = psutil.disk_io_counters()
        nio = psutil.net_io_counters()

        MB = 1024 * 1024
        row: dict[str, Any] = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": vm.percent,
            "ram_used_mb": round(vm.used / MB, 1),
            "ram_total_mb": round(vm.total / MB, 1),
            "disk_percent": disk.percent,
            # I/O cumulés depuis le démarrage du moniteur (deltas)
            "disk_read_mb": round((dio.read_bytes - self._disk0.read_bytes) / MB, 2) if dio else 0.0,
            "disk_write_mb": round((dio.write_bytes - self._disk0.write_bytes) / MB, 2) if dio else 0.0,
            "net_sent_mb": round((nio.bytes_sent - self._net0.bytes_sent) / MB, 2),
            "net_recv_mb": round((nio.bytes_recv - self._net0.bytes_recv) / MB, 2),
            "gpu_percent": None,
            "gpu_mem_used_mb": None,
            "gpu_mem_total_mb": None,
            "gpu_temp_c": None,
        }

        if _GPU_OK:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]  # 1er GPU (config cible = 1 seul GPU)
                    row["gpu_percent"] = round(g.load * 100, 1)
                    row["gpu_mem_used_mb"] = round(g.memoryUsed, 1)
                    row["gpu_mem_total_mb"] = round(g.memoryTotal, 1)
                    row["gpu_temp_c"] = g.temperature
            except Exception:
                pass  # GPU indisponible sur ce tick → laissé à None

        return row

    # ── Contrôle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._started_at = datetime.now()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="ResourceMonitor", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._samples.append(self._sample())
            except Exception:
                pass
            self._stop.wait(self.interval)

    def stop_and_report(self) -> Path | None:
        """Arrête le thread, écrit le JSON brut + le rapport Plotly HTML."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
        if not self._samples:
            return None
        return self._write_report()

    # ── API publique (consommée par app.py — ne pas utiliser les attributs _*) ──

    def sample_count(self) -> int:
        return len(self._samples)

    def write_report(self) -> Path | None:
        """Écrit le rapport sans arrêter le thread de collecte (rapport intermédiaire)."""
        if not self._samples:
            return None
        return self._write_report()

    # ── Génération du rapport ────────────────────────────────────────────────

    def _write_report(self) -> Path:
        MONITOR_DIR.mkdir(parents=True, exist_ok=True)
        stamp = (self._started_at or datetime.now()).strftime("%Y%m%d_%H%M%S")

        # 1. Dump JSON brut (réutilisable / archivable)
        json_path = MONITOR_DIR / f"resources_{stamp}.json"
        json_path.write_text(
            json.dumps(
                {
                    "started_at": self._started_at.isoformat() if self._started_at else None,
                    "ended_at": datetime.now().isoformat(),
                    "interval_s": self.interval,
                    "sample_count": len(self._samples),
                    "gpu_available": _GPU_OK and any(s["gpu_percent"] is not None for s in self._samples),
                    "samples": self._samples,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # 2. Rapport Plotly HTML autonome
        html_path = MONITOR_DIR / f"resources_{stamp}.html"
        self._build_plotly(html_path)
        return html_path

    def _build_plotly(self, out: Path) -> None:
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go

        s = self._samples
        ts = [r["ts"] for r in s]

        has_gpu = _GPU_OK and any(r["gpu_percent"] is not None for r in s)
        rows = 5 if has_gpu else 4
        titles = [
            "CPU (%)",
            "Mémoire RAM (%)",
            "Disque — I/O cumulés (Mo)",
            "Réseau — trafic cumulé (Mo)",
        ]
        if has_gpu:
            titles.append("GPU — charge (%) & VRAM (Mo)")

        fig = make_subplots(
            rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.06,
            subplot_titles=titles,
            specs=[[{"secondary_y": False}]] * (rows - (1 if has_gpu else 0))
                  + ([[{"secondary_y": True}]] if has_gpu else []),
        )

        def add(row, y, name, color, fill=True):
            fig.add_trace(
                go.Scatter(
                    x=ts, y=y, name=name, mode="lines",
                    line=dict(color=color, width=2),
                    fill="tozeroy" if fill else None,
                    fillcolor=color.replace("1)", "0.15)") if fill and "rgba" in color else None,
                ),
                row=row, col=1,
            )

        add(1, [r["cpu_percent"] for r in s], "CPU %", "rgba(99,102,241,1)")
        add(2, [r["ram_percent"] for r in s], "RAM %", "rgba(163,190,140,1)")
        add(3, [r["disk_read_mb"] for r in s], "Lecture Mo", "rgba(94,129,172,1)")
        add(3, [r["disk_write_mb"] for r in s], "Écriture Mo", "rgba(208,135,112,1)", fill=False)
        add(4, [r["net_recv_mb"] for r in s], "Reçu Mo", "rgba(136,192,208,1)")
        add(4, [r["net_sent_mb"] for r in s], "Envoyé Mo", "rgba(180,142,173,1)", fill=False)

        if has_gpu:
            fig.add_trace(
                go.Scatter(x=ts, y=[r["gpu_percent"] for r in s], name="GPU %",
                           line=dict(color="rgba(191,97,106,1)", width=2), fill="tozeroy"),
                row=5, col=1, secondary_y=False,
            )
            fig.add_trace(
                go.Scatter(x=ts, y=[r["gpu_mem_used_mb"] for r in s], name="VRAM Mo",
                           line=dict(color="rgba(235,203,139,1)", width=2, dash="dot")),
                row=5, col=1, secondary_y=True,
            )

        # Bornes 0-100 pour les axes en pourcentage
        fig.update_yaxes(range=[0, 100], row=1, col=1)
        fig.update_yaxes(range=[0, 100], row=2, col=1)

        # Résumé pour le titre (pics + moyennes)
        cpu_max = max(r["cpu_percent"] for r in s)
        ram_max = max(r["ram_percent"] for r in s)
        ram_mb_max = max(r["ram_used_mb"] for r in s)
        dur = len(s) * self.interval
        subtitle = (
            f"Durée {dur:.0f}s · {len(s)} points · "
            f"CPU pic {cpu_max:.0f}% · RAM pic {ram_max:.0f}% ({ram_mb_max:.0f} Mo)"
        )
        if has_gpu:
            gpu_max = max((r["gpu_percent"] or 0) for r in s)
            vram_max = max((r["gpu_mem_used_mb"] or 0) for r in s)
            subtitle += f" · GPU pic {gpu_max:.0f}% · VRAM pic {vram_max:.0f} Mo"

        fig.update_layout(
            template="plotly_dark",
            title=dict(
                text=f"MISPL Agent — Empreinte ressources<br><sub>{subtitle}</sub>",
                x=0.5, xanchor="center",
            ),
            height=260 * rows,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=110, l=60, r=40, b=40),
        )

        fig.write_html(str(out), include_plotlyjs="cdn", full_html=True)


# ── API module (singleton process-wide) ──────────────────────────────────────

_MONITOR: ResourceMonitor | None = None


def get_monitor() -> ResourceMonitor | None:
    """Retourne le moniteur déjà démarré sans en (re)démarrer un — None si jamais démarré."""
    return _MONITOR


def start_monitoring(interval: float = DEFAULT_INTERVAL) -> ResourceMonitor:
    """
    Démarre le moniteur global (idempotent) et enregistre le flush du rapport
    à la fermeture du process (atexit). Sûr à appeler plusieurs fois.
    """
    global _MONITOR
    if _MONITOR is None:
        _MONITOR = ResourceMonitor(interval=interval)
        _MONITOR.start()
        atexit.register(_flush)
    return _MONITOR


def _flush() -> None:
    global _MONITOR
    if _MONITOR is not None:
        path = _MONITOR.stop_and_report()
        if path:
            print(f"[monitor] Rapport ressources ecrit : {path}")
        _MONITOR = None


# ── Entrypoint autonome (benchmark ponctuel) ─────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Moniteur de ressources MISPL Agent")
    parser.add_argument("--duration", type=float, default=30, help="Durée d'observation (s)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Intervalle d'échantillonnage (s)")
    args = parser.parse_args()

    print(f"[monitor] Observation {args.duration}s (tick {args.interval}s)... GPU={'oui' if _GPU_OK else 'non'}")
    mon = ResourceMonitor(interval=args.interval)
    mon.start()
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\n[monitor] Interruption.")
    report = mon.stop_and_report()
    print(f"[monitor] Rapport : {report}")
