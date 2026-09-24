# Cartographie du dépôt

> Vérifié le 2026-09-24 contre l'arborescence réelle du dépôt, `requirements.txt`,
> `frontend/package.json`, `Dockerfile`, `README.md`, `CLAUDE.md` et le graphe
> d'imports généré par `generer_cartographie.py` (voir ce fichier). Le contenu
> de `rag_knowledge_base/`, `DSI/` et `docs/audit_PI_*/` n'est ni cité ni
> reproduit ici (voir `CLAUDE.md`, section « Dépôt public »).

## Arborescence commentée

```
MISPL/
├── api/                      Backend FastAPI (comptes, sessions, chat, admin)
│   ├── main.py                Point d'entrée — middlewares, routers, lifespan
│   ├── db.py                  Connexion SQLite + SQLAlchemy, migration légère (upgrade_schema)
│   ├── models.py               Modèles ORM (users, sessions, conversations, messages, usage_daily, audit_events)
│   ├── schemas.py              Schémas Pydantic des requêtes/réponses
│   ├── security.py             Hachage Argon2id, politique de mot de passe
│   ├── auth.py                 Authentification, verrouillage anti-bruteforce, re-hachage transparent
│   ├── audit.py                Journal d'audit de sécurité (écriture seule)
│   ├── session_store.py        Cycle de vie des sessions (création, validation, révocation)
│   ├── dependencies.py         Dépendances FastAPI (utilisateur courant, garde admin)
│   ├── ownership.py            Contrôle de propriété d'une conversation
│   ├── admin_bootstrap.py      Création du tout premier compte admin
│   └── routers/
│       ├── auth.py             /auth : login, logout, me, change-password
│       ├── admin.py            /admin : gestion des comptes techniciens
│       ├── chat.py             /chat/ask : question → réponse (encapsule ask_mispl)
│       └── conversations.py    /conversations : historique de chat par compte
│
├── src/                      Moteur partagé par l'API et Streamlit
│   ├── agent/
│   │   ├── mispl_agent.py      Cœur de l'agent : ask_mispl, cache, repli entre modèles
│   │   ├── prompt_builder.py   Prompt système par profil de skills, garde anti-extraction
│   │   └── linter.py           Lint et auto-corrections du code MISPL généré
│   ├── rag/
│   │   ├── retriever.py        Retrieval hybride BM25 + dense (ChromaDB), fusion RRF
│   │   ├── reranker.py         Reranking cross-encoder multilingue
│   │   ├── ingest_knowledge_base.py  Découpage de la base de connaissances en chunks
│   │   └── build_vectorstore.py      Reconstruction de l'index à partir des chunks
│   ├── security/
│   │   ├── access_mode.py      Modes Technicien/DSI, barrière dure anti-boucle
│   │   └── dlp.py               Détection de données potentiellement identifiantes
│   └── utils/
│       └── resource_monitor.py Monitoring CPU/RAM/disque/réseau/GPU, rapport Plotly
│
├── frontend/                 Frontend Next.js 16 / React 19
│   ├── app/
│   │   ├── page.tsx             Page d'accueil
│   │   ├── login/page.tsx       Connexion
│   │   ├── chat/page.tsx        Interface de chat
│   │   └── admin/page.tsx       Tableau de bord d'administration
│   └── lib/                    Client API, utilitaires (formatage, groupement de conversations...)
│
├── app.py                    Interface Streamlit historique (mono-poste), toujours en production
├── data/                     Fichier SQLite (data/mispl.db) — jamais versionné
├── docs/                     Documentation (ce dossier inclus)
│   ├── base_de_donnees/        Schéma, qui écrit quoi, accès (lot C2)
│   ├── cartographie/           Ce document + carte interactive (lot C2)
│   ├── securite/                Audit de sécurité (autre lot)
│   ├── specifications/, architecture/, guides/, sphinx/  (autres lots)
│   ├── chunks/                  Index RAG généré (ChromaDB, BM25) — non versionné
│   └── audit_PI_*/              Audit propriété intellectuelle — exclu du dépôt public
├── rag_knowledge_base/        Fiches source du RAG (voir CLAUDE.md avant modification)
├── outputs/                   Sessions journalisées, cache réponses, rapports — largement non versionné
├── scripts/                   Scripts d'exploitation et d'évaluation en ligne de commande
│   └── claude_harness/          Harnais de bancs d'essai automatisés (E2E, régression)
├── tools/                     Outils de contrôle (propriété intellectuelle)
├── tests/                     Suite pytest (agent, api, rag, security, mispl_examples)
├── .claude/                   Skills métier, règles, sous-agents Claude Code
├── DSI/                       Notes internes/juridiques — jamais versionné
├── requirements.txt           Dépendances Python
├── Dockerfile                 Déploiement Streamlit (type Hugging Face Space)
└── start.ps1                  Lance l'interface Streamlit
```

## Diagramme d'architecture des modules

```{mermaid}
flowchart TB
    subgraph Interfaces
        NEXT["Frontend Next.js\n(frontend/)"]
        STREAM["Interface Streamlit\n(app.py)"]
    end

    subgraph Backend["Backend FastAPI (api/)"]
        MAIN["api.main"]
        ROUTERS["api.routers.*\n(auth, admin, chat, conversations)"]
        AUTHMOD["api.auth / api.security\n/ api.session_store / api.audit"]
        DEPS["api.dependencies\n/ api.ownership"]
        DB["api.db / api.models"]
    end

    subgraph Moteur["Moteur partagé (src/)"]
        AGENT["src.agent.mispl_agent\n(ask_mispl)"]
        PROMPT["src.agent.prompt_builder"]
        LINT["src.agent.linter"]
        RAG["src.rag.retriever\n+ reranker"]
        SEC["src.security.access_mode\n+ dlp"]
    end

    subgraph Stockage
        SQLITE[("data/mispl.db\n(SQLite)")]
        CHROMA[("docs/chunks/\nChromaDB + BM25")]
        CACHE[("outputs/cache/\noutputs/sessions/")]
    end

    NEXT -->|HTTP JSON, cookie de session| MAIN
    STREAM -->|appel direct en process| AGENT

    MAIN --> ROUTERS
    ROUTERS --> DEPS
    ROUTERS --> AUTHMOD
    DEPS --> DB
    AUTHMOD --> DB
    ROUTERS -->|POST /chat/ask| AGENT

    AGENT --> PROMPT
    AGENT --> RAG
    AGENT --> LINT
    AGENT --> SEC
    AGENT --> CACHE

    DB --> SQLITE
    RAG --> CHROMA
```

## Graphe des dépendances internes Python

Généré par `docs/cartographie/generer_cartographie.py`, qui parse les
imports (module `ast`, sans exécution de code) de `api/`, `src/`,
`scripts/`, `tools/`, plus `app.py`, `conftest.py` et `setup.py` à la
racine. Sortie : `graphe_imports.json` (données) et
`carte_interactive.html` (carte interactive autonome — voir plus bas).

État au 2026-09-24 : **60 modules**, **93 imports internes détectés**.

Aperçu simplifié (paquets uniquement — le détail module par module est
dans la carte interactive) :

```{mermaid}
flowchart LR
    api_routers["api.routers.*"] --> api_pkg["api.*\n(auth, db, models, security,\nsession_store, audit, dependencies,\nownership, admin_bootstrap)"]
    api_pkg --> agent["src.agent.*"]
    api_routers --> agent
    agent --> rag["src.rag.*"]
    agent --> security["src.security.*"]
    agent --> agent
    app["app.py"] --> agent
    app --> rag
    app --> security
    scripts["scripts.*"] --> agent
    scripts --> rag
    scripts --> api_pkg
    scripts --> security
    tools["tools.*"] -.->|indépendant, pas d'import vers api/src| tools
```

Points notables du graphe complet (voir `graphe_imports.json` pour le détail) :
- `api.routers.chat` est le seul point de jonction entre le backend FastAPI
  et le moteur RAG (`src.agent.mispl_agent`, `src.security.access_mode`,
  `src.security.dlp`).
- `api.auth` importe désormais `api.audit` (journal d'audit) en plus de
  `api.models` et `api.security`.
- `tools/check_ip_similarity.py` n'importe rien de `api/` ni `src/` : c'est
  un outil autonome de contrôle de propriété intellectuelle.
- `app.py` (Streamlit) et `api/routers/chat.py` convergent tous deux vers
  `src.agent.mispl_agent.ask_mispl` — c'est le seul moteur de génération,
  partagé par les deux interfaces.

## Dépendances externes principales

### Python (`requirements.txt`)

| Paquet | Rôle |
|---|---|
| `chromadb` | Vectorstore local persistant pour le RAG dense |
| `rank-bm25` | Recherche lexicale BM25 (fusionnée par RRF avec la recherche dense) |
| `sentence-transformers` | Embeddings locaux (`paraphrase-multilingual-MiniLM-L12-v2`) |
| `nltk` | Racinisation française (`SnowballStemmer`) pour l'indexation BM25 |
| `openai` | Client compatible OpenRouter (appel des LLM gratuits) |
| `streamlit` | Interface mono-poste historique (`app.py`) |
| `python-dotenv` | Chargement du fichier `.env` |
| `tqdm` | Barres de progression lors de l'ingestion |
| `psutil`, `GPUtil`, `plotly` | Monitoring ressources et rapport HTML (`src/utils/resource_monitor.py`) |
| `pytest`, `pytest-cov` | Tests et couverture |
| `fastapi`, `uvicorn` | API HTTP et serveur ASGI |
| `sqlalchemy` | ORM / accès à `data/mispl.db` |
| `argon2-cffi` | Hachage Argon2id des mots de passe |
| `email-validator` | Validation des emails par Pydantic (`EmailStr`) |
| `httpx` | Requis par `fastapi.testclient.TestClient` (tests) |
| `numpy`, `scikit-learn` | TF-IDF et similarité cosinus (`tools/check_ip_similarity.py`) |
| `beautifulsoup4`, `pypdf` | Extraction de texte pour le contrôle de propriété intellectuelle (optionnel) |

### Frontend (`frontend/package.json`)

| Paquet | Rôle |
|---|---|
| `next` (16.3.1) | Framework React — routage, rendu, build |
| `react` / `react-dom` (19.2.8) | Bibliothèque UI |
| `react-markdown` | Rendu Markdown des réponses de l'agent dans le chat |
| `typescript`, `@types/*` | Typage statique (dev uniquement) |

## Points d'entrée

| Point d'entrée | Commande | Fichier |
|---|---|---|
| API FastAPI | `uvicorn api.main:app --port 8000` | `api/main.py` |
| Frontend Next.js | `cd frontend; npm run dev` | `frontend/app/` |
| Interface Streamlit | `.\start.ps1 run` ou `streamlit run app.py` (Dockerfile) | `app.py` |
| Agent en CLI interactif | `python src/agent/mispl_agent.py` (interactif) ou `python src/agent/mispl_agent.py "<question>"` (une question) | `src/agent/mispl_agent.py:796-800` |
| Création du premier admin | `python scripts/create_admin.py` | `scripts/create_admin.py` |
| Mot de passe DSI partagé (Streamlit) | `python scripts/set_dsi_password.py` | `scripts/set_dsi_password.py` |
| Reconstruction de l'index RAG | `python src/rag/build_vectorstore.py` | `src/rag/build_vectorstore.py` |
| Évaluation du retrieval | `python scripts/eval_retrieval_kb.py` | `scripts/eval_retrieval_kb.py` |
| Contrôle de propriété intellectuelle | `python tools/check_ip_similarity.py --manual ...` | `tools/check_ip_similarity.py` |
| Suite de tests | `pytest` | `tests/`, `conftest.py`, `pytest.ini` |
| Déploiement conteneurisé | `docker build .` (Hugging Face Space, lance Streamlit) | `Dockerfile` |

## Carte interactive

`carte_interactive.html`, généré par `generer_cartographie.py`, est un
fichier HTML autonome (vis-network chargé depuis `cdn.jsdelivr.net`) :
nœuds = modules colorés par paquet, taille = nombre de lignes, arêtes =
imports internes détectés par `ast`. Zoom, déplacement, recherche par nom
de module ou de chemin, infobulle au survol (chemin, nombre de lignes,
rôle). À régénérer après toute modification de `api/`, `src/`, `scripts/`
ou `tools/` :

```powershell
.venv\Scripts\python.exe docs\cartographie\generer_cartographie.py
```
