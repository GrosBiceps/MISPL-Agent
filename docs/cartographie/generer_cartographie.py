"""Génère la cartographie des dépendances internes du dépôt MISPL Agent.

Parse les imports Python (module `ast`, sans exécuter aucun code) des
paquets `api/`, `src/`, `scripts/` et `tools/`, plus `app.py` et
`conftest.py` à la racine, puis produit :

  - graphe_imports.json : graphe des imports internes (nœuds + arêtes)
  - carte_interactive.html : carte interactive autonome (un seul fichier),
    vis-network chargé depuis cdn.jsdelivr.net, zoom/déplacement/recherche,
    infobulle avec chemin et rôle du module.

Usage :
    python docs/cartographie/generer_cartographie.py

Ne lit et n'écrit jamais de contenu de `rag_knowledge_base/`, `DSI/`,
`data/` ni de donnée de ligne — uniquement la structure du code source
(chemins de fichiers, imports, nombre de lignes).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent

# Paquets/fichiers analysés — code applicatif Python uniquement (pas les
# tests, pas la base de connaissances, pas le frontend Next.js/TypeScript).
SCAN_DIRS = ["api", "src", "scripts", "tools"]
SCAN_FILES = ["app.py", "conftest.py", "setup.py"]

EXCLUDE_DIR_NAMES = {"__pycache__"}

# Rôle en une courte phrase par module ou préfixe de module — utilisé comme
# infobulle dans la carte interactive et comme légende de package. Tenu à
# jour manuellement ; un module non listé retombe sur une description
# générique dérivée de son chemin.
ROLE_BY_MODULE: dict[str, str] = {
    "app": "Interface Streamlit historique — toujours en production (start.ps1, Dockerfile).",
    "conftest": "Fixtures pytest partagées à la racine du dépôt.",
    "setup": "Métadonnées d'empaquetage du projet.",
    "api.main": "Point d'entrée FastAPI — middlewares, montage des routers, lifespan (warm-up RAG, purge).",
    "api.db": "Connexion SQLite + base déclarative SQLAlchemy.",
    "api.models": "Modèles ORM : comptes, sessions, conversations, messages, usage.",
    "api.schemas": "Schémas Pydantic des requêtes/réponses de l'API.",
    "api.security": "Hachage Argon2id des mots de passe, génération de mot de passe temporaire.",
    "api.auth": "Authentification par mot de passe avec verrouillage anti-bruteforce.",
    "api.session_store": "Cycle de vie des sessions de connexion (création, validation, révocation).",
    "api.dependencies": "Dépendances FastAPI — utilisateur courant, garde admin.",
    "api.ownership": "Vérification de propriété d'une conversation (contrôle d'accès).",
    "api.admin_bootstrap": "Création du tout premier compte admin.",
    "api.audit": "Journal d'audit de sécurité (connexions, échecs, actions d'administration).",
    "api.routers.auth": "Routes /auth : login, logout, utilisateur courant.",
    "api.routers.admin": "Routes /admin : gestion des comptes techniciens.",
    "api.routers.chat": "Route /chat/ask — encapsule ask_mispl() derrière l'authentification.",
    "api.routers.conversations": "Routes /conversations — historique de chat par compte.",
    "src.agent.mispl_agent": "Cœur de l'agent RAG : ask_mispl, cache, repli entre modèles, garde-fous.",
    "src.agent.prompt_builder": "Construction du prompt système, garde anti-extraction.",
    "src.agent.linter": "Lint et auto-corrections du code MISPL généré.",
    "src.rag.retriever": "Retrieval hybride BM25 + dense (ChromaDB), fusion RRF.",
    "src.rag.reranker": "Reranking cross-encoder multilingue des candidats après RRF.",
    "src.rag.ingest_knowledge_base": "Découpage et ingestion de la base de connaissances en chunks.",
    "src.rag.build_vectorstore": "Reconstruction de l'index ChromaDB + BM25 à partir des chunks.",
    "src.security.access_mode": "Modes Technicien/DSI — restriction et barrière dure sur les boucles.",
    "src.security.dlp": "Détection de données potentiellement identifiantes (DLP) avant persistance.",
    "src.utils.resource_monitor": "Monitoring CPU/RAM/disque/réseau/GPU, rapport Plotly.",
    "scripts.create_admin": "Script CLI : création du tout premier compte admin.",
    "scripts.set_dsi_password": "Script CLI : configuration du mot de passe DSI partagé (mode Streamlit).",
    "scripts.eval_retrieval_kb": "Évaluation hit@k / MRR du retrieval sur la base de connaissances.",
    "scripts.health_check": "Vérification de l'état de santé de l'installation.",
    "scripts.list_free_models": "Liste les modèles OpenRouter gratuits disponibles.",
    "scripts.full_eval_and_report": "Évaluation complète + génération de rapport HTML/Plotly.",
    "scripts.generate_rapport_complet": "Génère le rapport d'évaluation complet.",
    "scripts.verify_reproducibility": "Vérifie la reproductibilité des réponses de l'agent.",
    "scripts.eval_chu": "Évaluation sur un jeu de requêtes type CHU.",
    "scripts.eval_chu_v2": "Évaluation sur un jeu de requêtes type CHU (v2).",
    "scripts.eval_technicien": "Évaluation spécifique au mode Technicien (sans boucles).",
    "scripts.eval_large": "Évaluation sur un jeu de requêtes étendu.",
    "scripts.regen_report": "Régénère un rapport d'évaluation à partir de résultats existants.",
    "scripts.debug_parser": "Script de débogage du parseur de fiches Markdown.",
    "scripts.inspect_html2": "Script d'inspection du HTML source (aide GLIMS, hors dépôt public).",
    "scripts.claude_harness.harness": "Harnais d'exécution de bancs d'essai automatisés (E2E, régression).",
    "scripts.claude_harness.e2e": "Banc de test bout-en-bout (API + agent + LLM factice).",
    "scripts.claude_harness.common": "Utilitaires partagés du harnais de test.",
    "scripts.claude_harness.fake_llm_server": "Serveur LLM factice pour les tests E2E hors ligne.",
    "scripts.claude_harness._e2e_server": "Démarrage du serveur API pour les tests E2E.",
    "scripts.claude_harness.eval_retrieval_harness": "Harnais d'évaluation du retrieval, intégré au banc E2E.",
    "tools.check_ip_similarity": "Garde-fou de propriété intellectuelle vs. le manuel GLIMS.",
}

PACKAGE_DESCRIPTIONS: dict[str, str] = {
    "api": "Backend FastAPI (routes, auth, base de données).",
    "api.routers": "Routes HTTP de l'API FastAPI.",
    "src.agent": "Agent RAG : orchestration question → réponse MISPL.",
    "src.rag": "Ingestion, retrieval hybride et reranking de la base de connaissances.",
    "src.security": "Contrôle d'accès par mode et détection de données sensibles (DLP).",
    "src.utils": "Utilitaires transverses (monitoring).",
    "scripts": "Scripts d'exploitation en ligne de commande.",
    "tools": "Outils de contrôle (propriété intellectuelle).",
    "(racine)": "Points d'entrée et configuration à la racine du dépôt.",
}


def _module_name_for_path(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    parts = rel.parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else path.stem


def _package_of(module_name: str) -> str:
    parts = module_name.split(".")
    if len(parts) <= 1:
        return "(racine)"
    return ".".join(parts[:-1]) if len(parts) > 2 else parts[0]


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
                continue
            files.append(p)
    for f in SCAN_FILES:
        p = ROOT / f
        if p.exists():
            files.append(p)
    return sorted(set(files))


def _internal_imports(path: Path, all_modules: set[str]) -> set[str]:
    """Retourne l'ensemble des modules internes (parmi all_modules) importés
    par ce fichier, résolus par préfixe le plus long (import de sous-module
    ou de symbole depuis un module interne compte comme dépendance du module
    parent). N'exécute aucun code — analyse purement syntaxique (ast.parse)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    found: set[str] = set()

    def _resolve(name: str) -> str | None:
        # Cherche le module interne connu le plus spécifique qui préfixe `name`.
        node_parts = name.split(".")
        for i in range(len(node_parts), 0, -1):
            candidate = ".".join(node_parts[:i])
            if candidate in all_modules:
                return candidate
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve(alias.name)
                if resolved:
                    found.add(resolved)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Import relatif (`from . import x` / `from .foo import y`) —
                # résolu depuis le paquet du fichier courant.
                base_parts = _module_name_for_path(path).split(".")[: -node.level]
                base = ".".join(base_parts)
                target = f"{base}.{node.module}" if node.module else base
                resolved = _resolve(target)
                if resolved:
                    found.add(resolved)
                continue
            if node.module:
                resolved = _resolve(node.module)
                if resolved:
                    found.add(resolved)

    self_name = _module_name_for_path(path)
    found.discard(self_name)
    return found


def build_graph() -> dict:
    files = _iter_source_files()
    module_names = {_module_name_for_path(p): p for p in files}
    all_modules = set(module_names)

    nodes = []
    for name, path in sorted(module_names.items()):
        rel_path = path.relative_to(ROOT).as_posix()
        try:
            line_count = sum(1 for _ in path.open(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            line_count = 0
        package = _package_of(name)
        role = ROLE_BY_MODULE.get(name) or PACKAGE_DESCRIPTIONS.get(package, "")
        nodes.append(
            {
                "id": name,
                "path": rel_path,
                "package": package,
                "lines": line_count,
                "role": role,
            }
        )

    edges = []
    for name, path in module_names.items():
        for target in sorted(_internal_imports(path, all_modules)):
            edges.append({"source": name, "target": target})

    return {"nodes": nodes, "edges": edges}


def render_html(graph: dict) -> str:
    graph_json = json.dumps(graph, ensure_ascii=False)
    packages = sorted({n["package"] for n in graph["nodes"]})
    return HTML_TEMPLATE.replace("__GRAPH_JSON__", graph_json).replace(
        "__PACKAGES_JSON__", json.dumps(packages, ensure_ascii=False)
    )


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Carte interactive — dépendances internes MISPL Agent</title>
<script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  :root {
    --bg: #0f1115;
    --panel: #171a21;
    --border: #2a2e38;
    --text: #e6e8ee;
    --muted: #9aa1b1;
    --accent: #5b9dff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 16px;
    align-items: center;
    flex-wrap: wrap;
    background: var(--panel);
  }
  header h1 {
    font-size: 15px;
    margin: 0;
    font-weight: 600;
    white-space: nowrap;
  }
  #search {
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 13px;
    min-width: 220px;
  }
  #legend {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 12px;
    color: var(--muted);
  }
  .legend-item { display: flex; align-items: center; gap: 4px; }
  .legend-swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
  #main { flex: 1; position: relative; min-height: 0; }
  #network { width: 100%; height: 100%; }
  #tooltip {
    position: absolute;
    display: none;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 12px;
    max-width: 320px;
    pointer-events: none;
    z-index: 10;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  }
  #tooltip .path { color: var(--accent); font-family: monospace; margin-bottom: 4px; }
  #tooltip .role { color: var(--muted); }
  #stats { font-size: 12px; color: var(--muted); white-space: nowrap; }
</style>
</head>
<body>
<header>
  <h1>Dépendances internes — MISPL Agent</h1>
  <input id="search" type="text" placeholder="Rechercher un module ou un chemin..." />
  <div id="legend"></div>
  <div id="stats"></div>
</header>
<div id="main">
  <div id="network"></div>
  <div id="tooltip"></div>
</div>
<script>
const graph = __GRAPH_JSON__;
const packages = __PACKAGES_JSON__;

// Palette qualitative fixe (indépendante du nombre de paquets détectés).
const palette = ["#5b9dff", "#ff8c5b", "#5bffa3", "#f2d75b", "#c95bff", "#ff5b8c", "#5bf2ff", "#a3ff5b"];
const colorByPackage = {};
packages.forEach((p, i) => { colorByPackage[p] = palette[i % palette.length]; });

const minLines = Math.min(...graph.nodes.map(n => n.lines || 1), 1);
const maxLines = Math.max(...graph.nodes.map(n => n.lines || 1), 1);
function sizeFor(lines) {
  const lo = 14, hi = 46;
  if (maxLines === minLines) return (lo + hi) / 2;
  const t = (lines - minLines) / (maxLines - minLines);
  return lo + t * (hi - lo);
}

const nodesData = new vis.DataSet(graph.nodes.map(n => ({
  id: n.id,
  label: n.id.split(".").slice(-1)[0],
  title: "",
  color: { background: colorByPackage[n.package], border: "#ffffff33" },
  size: sizeFor(n.lines || 1),
  font: { color: "#e6e8ee", size: 12 },
  shape: "dot",
  _path: n.path,
  _role: n.role,
  _lines: n.lines,
  _package: n.package,
})));

const edgesData = new vis.DataSet(graph.edges.map((e, i) => ({
  id: i,
  from: e.source,
  to: e.target,
  arrows: "to",
  color: { color: "#3a3f4c", highlight: "#5b9dff", opacity: 0.6 },
  smooth: { type: "dynamic" },
})));

const container = document.getElementById("network");
const data = { nodes: nodesData, edges: edgesData };
const options = {
  physics: {
    solver: "forceAtlas2Based",
    forceAtlas2Based: { gravitationalConstant: -60, springLength: 120, springConstant: 0.06 },
    stabilization: { iterations: 200 },
  },
  interaction: { hover: true, tooltipDelay: 999999, navigationButtons: false, keyboard: true },
  edges: { width: 1 },
};
const network = new vis.Network(container, data, options);

// Légende
const legend = document.getElementById("legend");
packages.forEach(p => {
  const item = document.createElement("div");
  item.className = "legend-item";
  const sw = document.createElement("span");
  sw.className = "legend-swatch";
  sw.style.background = colorByPackage[p];
  const label = document.createElement("span");
  label.textContent = p;
  item.appendChild(sw);
  item.appendChild(label);
  legend.appendChild(item);
});

document.getElementById("stats").textContent =
  graph.nodes.length + " modules, " + graph.edges.length + " imports internes";

// Infobulle personnalisée (chemin + rôle), affichée au survol.
const tooltip = document.getElementById("tooltip");
network.on("hoverNode", (params) => {
  const n = nodesData.get(params.node);
  tooltip.innerHTML =
    "<div class='path'>" + n._path + "</div>" +
    "<div>" + n._lines + " lignes — paquet " + n._package + "</div>" +
    (n._role ? "<div class='role'>" + n._role + "</div>" : "");
  tooltip.style.display = "block";
});
network.on("blurNode", () => { tooltip.style.display = "none"; });
network.on("dragging", () => { tooltip.style.display = "none"; });
container.addEventListener("mousemove", (e) => {
  const rect = container.getBoundingClientRect();
  tooltip.style.left = (e.clientX - rect.left + 16) + "px";
  tooltip.style.top = (e.clientY - rect.top + 16) + "px";
});

// Recherche : surligne les nœuds correspondants, estompe les autres.
const searchBox = document.getElementById("search");
searchBox.addEventListener("input", () => {
  const q = searchBox.value.trim().toLowerCase();
  if (!q) {
    nodesData.update(graph.nodes.map(n => ({ id: n.id, opacity: 1 })));
    return;
  }
  const updates = graph.nodes.map(n => {
    const match = n.id.toLowerCase().includes(q) || n.path.toLowerCase().includes(q);
    return { id: n.id, opacity: match ? 1 : 0.15 };
  });
  nodesData.update(updates);
  const firstMatch = graph.nodes.find(n => n.id.toLowerCase().includes(q) || n.path.toLowerCase().includes(q));
  if (firstMatch) {
    network.focus(firstMatch.id, { scale: 1.2, animation: { duration: 400 } });
  }
});
</script>
</body>
</html>
"""


def main() -> None:
    graph = build_graph()
    json_path = OUT_DIR / "graphe_imports.json"
    html_path = OUT_DIR / "carte_interactive.html"

    json_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(graph), encoding="utf-8")

    print(f"Modules analysés : {len(graph['nodes'])}")
    print(f"Imports internes détectés : {len(graph['edges'])}")
    print(f"Écrit : {json_path.relative_to(ROOT)}")
    print(f"Écrit : {html_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
