---
title: Mispl Agent
emoji: 🚀
colorFrom: blue
colorTo: red
sdk: streamlit
app_file: app.py
pinned: false
---

# MISPL Agent

Assistant IA spécialisé dans le langage **MISPL** (le langage de scripting propriétaire du SIL **GLIMS**, édité par Clinisys/MIPS). Il aide les **techniciens de laboratoire de biologie médicale** et la DSI à écrire, comprendre et sécuriser des scripts MISPL (règles de calcul, validations, comptes-rendus, navigation ERD) en répondant en français, avec des sources documentaires citées à chaque réponse.

Priorité absolue : **zéro hallucination**. L'agent ne doit jamais inventer une fonction MISPL — toute réponse s'appuie sur une base de connaissances constituée manuellement (593 fonctions indexées), et signale explicitement quand la documentation est absente ou partielle.

## Architecture

- **RAG hybride BM25 + ChromaDB** (`src/rag/retriever.py`) : fusion par *Reciprocal Rank Fusion* entre une recherche lexicale BM25 (stemming français) et une recherche vectorielle dense ChromaDB, avec boost sur les correspondances exactes de nom de fonction et réordonnancement anti-« lost in the middle ». La base est construite depuis `rag_knowledge_base/` par `src/rag/build_vectorstore.py` / `src/rag/ingest_knowledge_base.py` et stockée dans `docs/chunks/`.
- **LLM via OpenRouter** (`src/agent/mispl_agent.py`) : appel à l'API OpenRouter (compatible OpenAI) avec une liste de modèles gratuits (`FREE_MODELS`), un ordre de repli automatique en cas de rate-limit, un cache question→réponse (24h) et une purge automatique des sessions journalisées.
- **Prompt système** (`src/agent/prompt_builder.py`) : construit dynamiquement selon le profil de skill sélectionné (`auto`, `code`, `report`, `erd`, `perf`), en s'appuyant sur les skills métier définies dans `.claude/skills/`.
- **Linter de sécurité MISPL** (`src/agent/linter.py`) : analyse le code généré avant affichage — détecte boucles infinies potentielles, division par zéro, assignation de champs read-only, division entière silencieuse sur des résultats biologiques.
- **Modes d'accès DSI / Technicien** (`src/security/access_mode.py`) : défense en profondeur à deux couches. Le mode par défaut (**Technicien**) interdit la génération de boucles `WHILE`/`REPEAT` — à la fois via une consigne injectée dans le prompt système et via une barrière post-génération (`enforce_access_mode`) qui remplace la réponse si une boucle apparaît malgré tout. Le mode **DSI** (génération complète) ne se débloque qu'avec un mot de passe dont le hash PBKDF2-HMAC-SHA256 est stocké dans `.env` (généré via `scripts/set_dsi_password.py`) ; sans ce hash configuré, le mode DSI est définitivement inatteignable (fail-safe).
- **DLP (protection des données patient)** (`src/security/dlp.py`) : filtre les questions et le contexte labo avant envoi au LLM — bloque les motifs à haut risque (NIR, IPP/NIP) et alerte sur les motifs sensibles (noms, dates de naissance).
- **Interface** : application Streamlit (`app.py`) avec suivi des sources RAG par réponse, export de conversation, et relevé optionnel des ressources machine (CPU/RAM/GPU) avec rapport Plotly HTML (`src/utils/resource_monitor.py`).

## Installation

Prérequis : Python 3.10+.

```powershell
# 1. Créer et activer un environnement virtuel (ou utiliser setup.py)
python -m venv .venv
.venv\Scripts\activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Copier le fichier d'environnement et renseigner la clé API
Copy-Item .env.example .env
# éditer .env et renseigner OPENROUTER_API_KEY (clé gratuite sur https://openrouter.ai/keys)

# 4. (Optionnel) Configurer le mot de passe du mode DSI
python scripts/set_dsi_password.py
```

Sans exécution de `set_dsi_password.py`, le mode DSI reste inatteignable et l'agent fonctionne uniquement en mode Technicien (bridé, sans génération de boucles).

## Construction de la base RAG

La base vectorielle (ChromaDB + corpus BM25) doit être construite une fois avant le premier lancement, à partir des fiches de `rag_knowledge_base/` :

```powershell
.\start.ps1 build
```

Équivalent direct : `python src\rag\build_vectorstore.py`. Le résultat est écrit dans `docs/chunks/` (vectorstore ChromaDB, corpus BM25, manifest). Sans cette base, l'interface affiche une erreur « Base documentaire absente ».

## Lancement

```powershell
.\start.ps1 run
```

Ouvre l'interface Streamlit sur `http://localhost:8501`. Équivalent direct : `streamlit run app.py`.

Un mode CLI interactif est aussi disponible :

```powershell
.\start.ps1 cli
```

## Structure du repo

- `rag_knowledge_base/` — base de connaissances MISPL constituée manuellement (rétro-ingénierie clean room), organisée par thème (`01_core_syntax/`, `02_functions/`, `03_chu_use_cases/`), avec registre de traçabilité (`SOURCES.md`).
- `docs/chunks/` — chunks vectorisés générés par le pipeline RAG (ChromaDB, corpus BM25, manifest) ; non versionnés en l'état source, reconstruits via `start.ps1 build`.
- `src/rag/` — pipeline de chunking, ingestion et récupération hybride (BM25 + ChromaDB).
- `src/agent/` — agent principal (`mispl_agent.py`), construction du prompt système (`prompt_builder.py`), linter de sécurité (`linter.py`).
- `src/security/` — modes d'accès DSI/Technicien (`access_mode.py`) et protection des données patient (`dlp.py`).
- `src/utils/` — utilitaires, notamment le monitoring de ressources machine.
- `.claude/skills/` — skills métier MISPL pilotant le comportement de l'IA selon le profil de demande (code, comptes-rendus, ERD, performance).
- `.claude/rules/` — règles globales de l'agent (anti-hallucination, sécurité laboratoire).
- `.claude/agents/` — définitions de sous-agents spécialisés (génération et revue de code MISPL).
- `outputs/generated_scripts/` — scripts MISPL générés, journalisés à des fins de traçabilité.
- `outputs/sessions/` — sessions de conversation journalisées (purge automatique configurable via `MISPL_SESSION_RETENTION_DAYS`).
- `outputs/monitoring/` — rapports HTML Plotly du monitoring ressources.
- `scripts/` — scripts utilitaires (configuration du mot de passe DSI, évaluations, health check, inspection HTML, etc.).
- `tests/` — suite de tests (agent, sécurité, exemples MISPL validés).

## Tests

```powershell
pytest tests/
```

La suite couvre le cache et le linter de l'agent (`tests/agent/`), les modes d'accès et le DLP (`tests/security/`), ainsi que des exemples de fonctions MISPL validés (`tests/mispl_examples/`).
