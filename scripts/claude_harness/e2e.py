"""Test « logiciel lancé » de bout en bout du banc MISPL Agent.

1. Démarre le serveur LLM factice (fake_llm_server.py, 127.0.0.1, port libre).
2. Crée une base SQLite de test isolée (outputs/claude_harness/e2e_run/e2e.db),
   son schéma et un compte admin via api.admin_bootstrap.create_admin_account
   (mécanisme de scripts/create_admin.py). data/mispl.db n'est jamais touché
   (empreinte vérifiée avant/après).
3. Lance l'API FastAPI réelle (uvicorn, via _e2e_server.py) avec
   MISPL_LLM_BASE_URL → serveur factice et OPENROUTER_API_KEY=sk-test-local.
4. Crée des comptes DSI / technicien via POST /admin/users, se connecte
   (cookie de session), envoie les questions ayant une réponse dans answers/
   à la vraie route POST /chat/ask, vérifie codes HTTP, temps de réponse et
   cohérence exacte avec le report.json de `harness.py finalize`.
5. Vérifie auth, conversations (liste, détail, isolation, suppression),
   comptabilisation d'usage, réponse inconnue → 503, puis arrête proprement
   les deux serveurs.

Usage :
    PYTHONUTF8=1 .venv/Scripts/python.exe scripts/claude_harness/e2e.py [--ids A B ...]
"""

from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import os
import shutil
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

sys.path.insert(0, str(C.ROOT))

import httpx  # noqa: E402

PY = sys.executable
RUN_DIR = C.OUT_DIR / "e2e_run"
E2E_REPORT = C.OUT_DIR / "e2e_report.json"
REAL_DB = C.ROOT / "data" / "mispl.db"
ADMIN_EMAIL = "admin-e2e@example.com"
ADMIN_PASSWORD = "harness-admin-pass-1"
RATE_LIMIT = 20          # api/routers/chat.py::_CHAT_RATE_LIMIT_PER_USER
RATE_WINDOW = 61.0       # fenêtre 60 s + marge
SLOW_SECONDS = 30.0


class _Abort(Exception):
    """Arrêt anticipé : les post-conditions et le rapport sont quand même produits."""


class Checks:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, name: str, ok: bool, detail: str = "") -> bool:
        self.items.append({"name": name, "ok": bool(ok), "detail": detail})
        print(f"  [{'OK' if ok else 'KO'}] {name}" + (f" — {detail}" if detail and not ok else ""), flush=True)
        return ok

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.items if not c["ok"]]


def _fingerprint(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"{h}:{path.stat().st_mtime_ns}"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _port_closed(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0


def _wait_port_closed(port: int, timeout: float = 15.0) -> tuple[bool, float]:
    """Attend que plus rien n'écoute sur `port`. Retourne (libéré, secondes).

    Sous Windows, `.venv/Scripts/python.exe` est un lanceur : l'interpréteur
    réel (qui détient la socket d'écoute) est un processus ENFANT, tué par
    l'OS de façon asynchrone après la mort du lanceur. Un sondage immédiat
    tombait donc parfois sur l'enfant encore vivant (faux « port non libéré »,
    banc 2026-09-24). Les sockets en TIME_WAIT ne répondent pas à connect()
    et ne faussent pas ce test."""
    start = time.monotonic()
    while True:
        if _port_closed(port):
            return True, time.monotonic() - start
        if time.monotonic() - start >= timeout:
            return False, time.monotonic() - start
        time.sleep(0.25)


def _wait_http(url: str, proc: subprocess.Popen, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    return False


def _stop(proc: subprocess.Popen | None) -> None:
    """Arrête le processus ET ses descendants.

    Sous Windows, proc.terminate() ne tue que le lanceur venv : l'enfant
    (interpréteur réel, qui écoute sur le port) disparaît plus tard. On tue
    donc l'arbre entier avec `taskkill /T /F`."""
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def _load_finalize_results(ids: list[str], wait_seconds: float) -> tuple[dict, str]:
    """Charge les résultats de `harness.py finalize` pour comparaison.

    Retourne (résultats, problème) ; `problème` est vide si report.json est
    exploitable : présent, lisible, plus récent que toutes les réponses
    answers/<id>.md et couvrant tous les ids envoyés. Sinon, attend jusqu'à
    `wait_seconds` (finalize lancé en parallèle) en relisant le fichier."""
    answers_mtime = max((C.ANSWERS_DIR / f"{i}.md").stat().st_mtime for i in ids)
    deadline = time.monotonic() + wait_seconds
    while True:
        problem = ""
        results: dict = {}
        if not C.REPORT_JSON.exists():
            problem = "report.json absent"
        else:
            try:
                results = json.loads(C.REPORT_JSON.read_text(encoding="utf-8")).get("results", {})
            except (json.JSONDecodeError, OSError) as e:  # écriture en cours
                problem = f"report.json illisible ({e.__class__.__name__})"
            else:
                missing = [i for i in ids if i not in results]
                if C.REPORT_JSON.stat().st_mtime < answers_mtime:
                    problem = "report.json antérieur à la dernière réponse de answers/"
                elif missing:
                    problem = f"report.json ne couvre pas {len(missing)} id(s) (ex. {missing[:3]})"
        if not problem or time.monotonic() >= deadline:
            return results, problem
        time.sleep(5)


class UserClient:
    def __init__(self, base: str, email: str, mode: str):
        self.email, self.mode = email, mode
        self.http = httpx.Client(base_url=base, timeout=300)
        self.sent: collections.deque[float] = collections.deque()
        self.conversation_ids: list[int] = []
        self.id: int | None = None

    def throttle(self) -> None:
        now = time.monotonic()
        while self.sent and now - self.sent[0] > RATE_WINDOW:
            self.sent.popleft()
        if len(self.sent) >= RATE_LIMIT:
            wait = RATE_WINDOW - (now - self.sent[0])
            print(f"    (rate limit {self.email} : pause {wait:.0f}s)", flush=True)
            time.sleep(max(0, wait))
            self.sent.popleft()
        self.sent.append(time.monotonic())


def _bootstrap_db(db_path: Path) -> None:
    """Schéma + premier admin, par les mécanismes du projet (cf. scripts/create_admin.py)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from api.admin_bootstrap import create_admin_account
    from api.db import Base
    import api.models  # noqa: F401  (enregistre les tables)

    engine = create_engine(f"sqlite:///{db_path.resolve().as_posix()}")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        create_admin_account(db, ADMIN_EMAIL, "Admin banc e2e", ADMIN_PASSWORD)
    finally:
        db.close()
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", nargs="*", help="Limiter à ces ids (défaut : toutes les questions ayant answers/<id>.md)")
    parser.add_argument("--users-per-mode", type=int, default=2)
    parser.add_argument("--startup-timeout", type=float, default=300,
                        help="Attente max du démarrage de l'API (inclut le préchargement du RAG)")
    parser.add_argument("--wait-report", type=float, default=0,
                        help="Secondes d'attente d'un report.json à jour (finalize lancé en parallèle)")
    args = parser.parse_args()

    questions = C.load_questions(ids=args.ids)
    answered = [q for q in questions if (C.ANSWERS_DIR / f"{q['id']}.md").exists()]
    if not answered:
        print(f"Aucune question avec réponse dans {C.ANSWERS_DIR}")
        return 1
    if not C.HASH_INDEX_PATH.exists():
        print("hash_index.json absent : lancer d'abord `harness.py prepare`")
        return 1
    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    RUN_DIR.mkdir(parents=True)
    db_path = RUN_DIR / "e2e.db"
    real_db_before = _fingerprint(REAL_DB)
    checks = Checks()
    fake_proc = api_proc = None
    fake_port = api_port = None
    logs = {name: open(RUN_DIR / f"{name}.log", "w", encoding="utf-8")
            for name in ("fake_llm_stdout", "fake_llm_stderr", "api_stdout", "api_stderr")}
    per_question: list[dict] = []
    bodies: dict[str, dict] = {}
    latencies: list[float] = []
    started = time.time()

    try:
        # 1. Serveur LLM factice
        port_file = RUN_DIR / "fake_llm.port"
        fake_proc = subprocess.Popen(
            [PY, str(C.HARNESS_DIR / "fake_llm_server.py"), "--port", "0",
             "--port-file", str(port_file), "--log", str(RUN_DIR / "fake_llm_requests.jsonl")],
            stdout=logs["fake_llm_stdout"], stderr=logs["fake_llm_stderr"], cwd=str(C.ROOT),
        )
        deadline = time.time() + 20
        while not port_file.exists() and time.time() < deadline and fake_proc.poll() is None:
            time.sleep(0.1)
        fake_port = int(port_file.read_text()) if port_file.exists() else None
        fake_base = f"http://127.0.0.1:{fake_port}"
        if not checks.add("serveur LLM factice démarré (/health)",
                          fake_port is not None and _wait_http(f"{fake_base}/health", fake_proc, 20)):
            raise _Abort()
        r = httpx.post(f"{fake_base}/v1/chat/completions", json={"messages": []},
                       headers={"Authorization": "Bearer sk-or-v1-real-key-should-never-be-used"})
        checks.add("serveur factice refuse une clé non factice (401)", r.status_code == 401, str(r.status_code))

        # 2. Base de test isolée + admin
        _bootstrap_db(db_path)
        checks.add("base SQLite de test créée + admin (create_admin_account)", db_path.exists())

        # 3. API réelle
        api_port = _free_port()
        env = dict(os.environ)
        env.update({
            "PYTHONUTF8": "1",
            "MISPL_LLM_BASE_URL": f"{fake_base}/v1",
            "OPENROUTER_API_KEY": C.FAKE_API_KEY,
            "MISPL_COOKIE_SECURE": "false",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "ANONYMIZED_TELEMETRY": "False",
        })
        env.pop("OPENAI_API_KEY", None)
        api_proc = subprocess.Popen(
            [PY, str(C.HARNESS_DIR / "_e2e_server.py"), "--port", str(api_port),
             "--db", str(db_path), "--workdir", str(RUN_DIR)],
            stdout=logs["api_stdout"], stderr=logs["api_stderr"], cwd=str(C.ROOT), env=env,
        )
        base = f"http://127.0.0.1:{api_port}"
        if not checks.add("API FastAPI démarrée (GET /openapi.json 200)",
                          _wait_http(f"{base}/openapi.json", api_proc, args.startup_timeout)):
            raise _Abort()
        paths = httpx.get(f"{base}/openapi.json").json().get("paths", {})
        health_routes = [p for p in paths if "health" in p.lower()]
        checks.add("routes attendues exposées (/chat/ask, /conversations, /auth/login)",
                   all(p in paths for p in ("/chat/ask", "/conversations", "/auth/login")), str(sorted(paths)))
        print(f"  (routes de santé dédiées : {health_routes or 'aucune — /openapi.json sert de sonde'})")

        anon = httpx.Client(base_url=base, timeout=30)
        checks.add("GET /auth/me sans cookie → 401", anon.get("/auth/me").status_code == 401)
        checks.add("POST /chat/ask sans cookie → 401",
                   anon.post("/chat/ask", json={"question": "test"}).status_code == 401)
        checks.add("GET /conversations sans cookie → 401", anon.get("/conversations").status_code == 401)
        r = anon.get("/openapi.json")
        checks.add("en-têtes de sécurité présents", r.headers.get("X-Content-Type-Options") == "nosniff")

        # 4. Comptes
        admin = UserClient(base, ADMIN_EMAIL, "dsi")
        r = admin.http.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if not checks.add("login admin → 200", r.status_code == 200, r.text[:200]):
            raise _Abort()
        checks.add("GET /auth/me admin", admin.http.get("/auth/me").json().get("platform_role") == "admin")

        users: dict[str, list[UserClient]] = {"dsi": [], "technicien": []}
        for mode in ("dsi", "technicien"):
            for i in range(args.users_per_mode):
                email = f"{mode}{i + 1}-e2e@example.com"
                r = admin.http.post("/admin/users", json={
                    "email": email, "display_name": f"{mode} e2e {i + 1}",
                    "platform_role": "user", "can_use_dsi_mode": mode == "dsi"})
                ok = checks.add(f"POST /admin/users {email} → 201", r.status_code == 201, r.text[:200])
                if not ok:
                    raise _Abort()
                uc = UserClient(base, email, mode)
                uc.id = r.json()["id"]
                temp_password = r.json()["temporary_password"]
                r = uc.http.post("/auth/login", json={"email": email, "password": temp_password})
                checks.add(f"login {email} → 200", r.status_code == 200, r.text[:200])
                # Mot de passe temporaire : changement imposé avant tout usage
                # (403 password_change_required sinon, depuis le 2026-09-24).
                checks.add(f"{email} : /conversations refusé avant changement du mot de passe → 403",
                           uc.http.get("/conversations").status_code == 403)
                r = uc.http.post("/auth/change-password", json={
                    "current_password": temp_password, "new_password": f"Banc-e2e-{mode}-{i + 1}-Mdp!"})
                checks.add(f"{email} : changement du mot de passe temporaire → 200", r.status_code == 200, r.text[:200])
                me = uc.http.get("/auth/me").json()
                checks.add(f"{email} can_use_dsi_mode={mode == 'dsi'}", me.get("can_use_dsi_mode") == (mode == "dsi"))
                users[mode].append(uc)

        # 5. Questions → /chat/ask
        print(f"\nEnvoi de {len(answered)} question(s) à POST /chat/ask ...", flush=True)
        rr = {"dsi": 0, "technicien": 0}
        for n, q in enumerate(answered, 1):
            pool = users[q["mode"]]
            uc = pool[rr[q["mode"]] % len(pool)]
            rr[q["mode"]] += 1
            payload = {"question": q["question"]}
            if q.get("conversation_history"):
                payload["conversation_history"] = q["conversation_history"]
            uc.throttle()
            t = time.perf_counter()
            r = uc.http.post("/chat/ask", json=payload)
            dt = time.perf_counter() - t
            entry = {"id": q["id"], "mode": q["mode"], "user": uc.email, "status": r.status_code,
                     "seconds": round(dt, 2), "problems": []}
            if r.status_code != 200:
                entry["problems"].append(f"HTTP {r.status_code} : {r.text[:200]}")
            else:
                body = r.json()
                if body.get("blocked"):
                    entry["problems"].append(f"bloqué par le DLP : {body.get('dlp_alerts')}")
                if body.get("conversation_id") is None:
                    entry["problems"].append("conversation_id absent")
                else:
                    uc.conversation_ids.append(body["conversation_id"])
                    entry["conversation_id"] = body["conversation_id"]
                bodies[q["id"]] = body
            if n > 1:
                latencies.append(dt)
            if dt > SLOW_SECONDS and n > 1:
                entry["problems"].append(f"temps de réponse élevé ({dt:.1f}s > {SLOW_SECONDS:.0f}s)")
            per_question.append(entry)
            print(f"  [{n}/{len(answered)}] {q['id']:<10} {r.status_code} {dt:6.2f}s "
                  + ("OK" if not entry["problems"] else "KO " + " | ".join(entry["problems"])[:160]), flush=True)
        bad = [e for e in per_question if e["problems"]]
        checks.add(f"/chat/ask : {len(per_question) - len(bad)}/{len(per_question)} réponses HTTP conformes "
                   "(200, non bloquées, conversation créée)", not bad,
                   "; ".join(f"{e['id']}: {e['problems'][0]}" for e in bad[:5]))

        # Comparaison avec finalize, APRÈS l'envoi : si finalize tourne en
        # parallèle, son report.json a le temps d'être écrit (--wait-report).
        finalized, report_problem = _load_finalize_results([q["id"] for q in answered], args.wait_report)
        if report_problem:
            checks.add("comparaison avec harness.py finalize", False,
                       f"{report_problem} — lancer `harness.py finalize` jusqu'au bout (pas en parallèle), "
                       "puis relancer e2e, ou passer --wait-report <secondes>")
        else:
            diff = []
            for e in per_question:
                body, fin = bodies.get(e["id"]), finalized[e["id"]]
                if body is None:
                    continue
                e["finalize_passed"] = fin["passed"]
                if (body.get("response") or "") != fin["final_response"]:
                    e["problems"].append("réponse API ≠ réponse finale de finalize")
                api_sources = [s["function_name"] for s in body.get("sources", [])]
                if api_sources != fin.get("final_sources"):
                    e["problems"].append(f"sources API ≠ finalize ({api_sources} vs {fin.get('final_sources')})")
                if e["problems"]:
                    diff.append(e)
            checks.add(f"/chat/ask : {len(bodies) - len(diff)}/{len(bodies)} réponses identiques à finalize",
                       not diff, "; ".join(f"{e['id']}: {e['problems'][-1]}" for e in diff[:5]))

        # 6. Réponse inconnue du serveur factice → 404 côté LLM → 503 côté API
        probe = users["dsi"][0]
        probe.throttle()
        r = probe.http.post("/chat/ask", json={"question": "Question de sonde sans réponse préparée (test 404 du serveur factice)."})
        checks.add("question sans réponse préparée → API 503 (fallback épuisé sur 404 du factice)",
                   r.status_code == 503, f"{r.status_code} {r.text[:150]}")

        # 7. Conversations
        owner = next((u for u in users["dsi"] + users["technicien"] if u.conversation_ids), None)
        if owner:
            r = owner.http.get("/conversations")
            ids = [c["id"] for c in r.json()] if r.status_code == 200 else []
            checks.add("GET /conversations → liste des conversations du compte",
                       r.status_code == 200 and sorted(ids) == sorted(owner.conversation_ids),
                       f"{r.status_code} {ids} vs {owner.conversation_ids}")
            cid = owner.conversation_ids[0]
            r = owner.http.get(f"/conversations/{cid}")
            detail = r.json() if r.status_code == 200 else {}
            msgs = detail.get("messages", [])
            checks.add("GET /conversations/{id} → 2 messages (user + assistant)",
                       r.status_code == 200 and [m["role"] for m in msgs] == ["user", "assistant"],
                       f"{r.status_code} {[m.get('role') for m in msgs]}")
            other = next(u for u in users["technicien"] + users["dsi"] if u is not owner)
            checks.add("conversation d'un autre compte → 404 (isolation)",
                       other.http.get(f"/conversations/{cid}").status_code == 404)
            checks.add("DELETE /conversations/{id} → 200", owner.http.delete(f"/conversations/{cid}").status_code == 200)
            checks.add("conversation supprimée → 404", owner.http.get(f"/conversations/{cid}").status_code == 404)
            # Usage : les tokens renvoyés par le serveur factice doivent être comptabilisés.
            r = admin.http.get(f"/admin/users/{owner.id}/usage-daily")
            usage = r.json() if r.status_code == 200 else []
            reqs = sum(u["request_count"] for u in usage)
            toks = sum(u["prompt_tokens"] + u["completion_tokens"] for u in usage)
            checks.add("usage journalier comptabilisé (requêtes + tokens du factice)",
                       r.status_code == 200 and reqs == len(owner.conversation_ids) and toks > 0,
                       f"{r.status_code} requêtes={reqs} tokens={toks}")

        # 8. Déconnexion
        uc = users["technicien"][0]
        checks.add("POST /auth/logout → 200", uc.http.post("/auth/logout").status_code == 200)
        checks.add("après logout, /auth/me → 401", uc.http.get("/auth/me").status_code == 401)

    except _Abort:
        checks.add("scénario e2e complet (arrêt anticipé sur échec bloquant)", False)
    finally:
        _stop(api_proc)
        _stop(fake_proc)
        for f in logs.values():
            f.close()

    # 9. Post-conditions
    checks.add("serveurs arrêtés (processus terminés)",
               (api_proc is None or api_proc.poll() is not None) and (fake_proc is None or fake_proc.poll() is not None))
    for label, port in (("port API libéré", api_port), ("port serveur factice libéré", fake_port)):
        if port:
            freed, waited = _wait_port_closed(port)
            checks.add(label, freed, f"port {port} toujours à l'écoute après {waited:.0f}s")
    stderr_all = "".join((RUN_DIR / f"{n}.log").read_text(encoding="utf-8", errors="replace")
                         for n in ("api_stderr", "api_stdout", "fake_llm_stderr"))
    checks.add("aucune tentative réseau externe (garde socket)", C.NETWORK_BLOCK_MARKER not in stderr_all)
    fake_log = RUN_DIR / "fake_llm_requests.jsonl"
    entries = [json.loads(line) for line in fake_log.read_text(encoding="utf-8").splitlines()] if fake_log.exists() else []
    served = [e for e in entries if e.get("status") == 200]
    checks.add("serveur factice : 1 requête servie par question envoyée",
               len(served) == len(answered), f"{len(served)} servies pour {len(answered)} questions")
    checks.add("serveur factice : 404 explicite journalisé pour la sonde",
               any(e.get("code") == "answer_not_found" for e in entries))
    checks.add("data/mispl.db inchangé", _fingerprint(REAL_DB) == real_db_before)

    lat = sorted(latencies)
    stats = {}
    if lat:
        stats = {
            "count": len(lat),
            "min": round(lat[0], 2),
            "median": round(statistics.median(lat), 2),
            "p95": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 2),
            "max": round(lat[-1], 2),
        }
    first = per_question[0]["seconds"] if per_question else None
    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "duration_seconds": round(time.time() - started, 1),
        "questions_sent": len(per_question),
        "first_request_seconds_warmup": first,
        "latency_seconds_excluding_warmup": stats,
        "checks": checks.items,
        "failed_checks": checks.failed,
        "per_question": per_question,
        "run_dir": str(RUN_DIR),
    }
    C.dump_json(E2E_REPORT, report)
    print(f"\nLatence (hors 1re requête) : {stats}  — 1re requête : {first}s")
    print(f"{len(checks.items) - len(checks.failed)}/{len(checks.items)} vérifications OK — rapport : {E2E_REPORT}")
    return 0 if not checks.failed else 5


if __name__ == "__main__":
    sys.exit(main())
