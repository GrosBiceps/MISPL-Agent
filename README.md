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

Assistant IA spécialisé dans le langage **MISPL**, le langage de scripting propriétaire du SIL **GLIMS** (Clinisys/MIPS). Il aide les **techniciens de laboratoire de biologie médicale** et la DSI à écrire, comprendre et sécuriser des scripts MISPL (règles de calcul, validations, comptes-rendus, navigation ERD). Il répond en français et cite ses sources documentaires à chaque réponse.

Priorité absolue : **zéro hallucination**. L'agent ne doit jamais inventer une fonction MISPL. Chaque réponse s'appuie sur une base de connaissances rédigée pour ce projet (38 fiches Markdown, 301 fonctions reconnues par l'index), et l'agent signale explicitement quand la documentation est absente ou partielle.

## Architecture

Le projet comporte deux interfaces qui partagent le même moteur (agent, RAG, sécurité) :

- **Plateforme multi-utilisateurs** : API **FastAPI** (`api/`) et frontend **Next.js** (`frontend/`). Comptes, sessions, historique des conversations, tableau de bord d'administration et suivi de consommation de jetons.
- **Interface Streamlit** (`app.py`) : interface mono-poste historique, toujours fonctionnelle. Elle est lancée par `start.ps1 run` et par le `Dockerfile` (déploiement de type Hugging Face Space).

### Moteur

- **Agent** (`src/agent/mispl_agent.py`, fonction `ask_mispl`) : appelle l'API OpenRouter (compatible OpenAI) avec une liste de modèles gratuits (`FREE_MODELS`). En cas de limite de débit ou d'indisponibilité, il bascule automatiquement vers un autre modèle (`FALLBACK_ORDER`). Il utilise un cache question → réponse sur disque (24 h par défaut) et purge automatiquement les sessions journalisées. Avant de renvoyer une réponse, il applique plusieurs traitements :
  - suppression du raisonnement interne (*chain-of-thought*) qui aurait fuité ;
  - auto-corrections MISPL ;
  - barrière du mode d'accès ;
  - **garde-fou mécanique de certitude** : un avertissement est ajouté quand les preuves documentaires sont faibles, indépendamment de l'auto-évaluation du LLM ;
  - suppression des scores de retrieval internes qui auraient fuité ;
  - lint de sécurité.
- **Prompt système** (`src/agent/prompt_builder.py`) : construit selon le profil de skills (`code`, `report`, `erd`, `perf`, `full`, ou détection automatique) à partir des skills métier de `.claude/skills/mispl-*` et des règles de `.claude/rules/`. Il inclut toujours une **garde anti-extraction**, qui refuse de révéler ou de reformuler les instructions système.
- **Linter MISPL** (`src/agent/linter.py`) : analyse le code généré avant affichage. Il détecte les boucles potentiellement infinies, les divisions par zéro, les assignations de champs en lecture seule, les divisions entières silencieuses et les fonctions inventées connues.
- **RAG hybride** (`src/rag/retriever.py`) :
  - recherche lexicale BM25 (racinisation française, NLTK) et recherche dense ChromaDB (embeddings locaux `paraphrase-multilingual-MiniLM-L12-v2`), fusionnées par *Reciprocal Rank Fusion* (k = 25) ;
  - épinglage des correspondances exactes de nom de fonction et élargissement par catégorie selon les skills actifs ;
  - **reranking cross-encoder** (`src/rag/reranker.py`, `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`), désactivable par `MISPL_RERANK_ENABLED=false` ;
  - réordonnancement « anti lost-in-the-middle ».
  
  L'index est construit à partir de `rag_knowledge_base/` par `src/rag/build_vectorstore.py`, qui délègue à `src/rag/ingest_knowledge_base.py` (1 section H2 = 1 bloc, frontmatter YAML → métadonnées).
- **Sécurité** (`src/security/`) :
  - `access_mode.py` : modes **Technicien** (par défaut, sans génération de boucles `WHILE`/`REPEAT`) et **DSI** (génération complète). La défense est double : une consigne dans le prompt et une barrière après génération (`enforce_access_mode`), qui détecte aussi les boucles hors bloc de code. Dans Streamlit, le mode DSI se débloque par un mot de passe dont le hash PBKDF2-HMAC-SHA256 est stocké dans `.env`. Sans ce hash, le mode DSI est inatteignable (fail-safe). Dans l'API, le mode dépend du droit `can_use_dsi_mode` du compte, attribué par un administrateur.
  - `dlp.py` : filtre la question, le contexte labo et l'historique avant tout envoi au LLM. Il bloque les motifs à haut risque (NIR, NISS, IPP/NIP) et signale les motifs sensibles (noms, dates de naissance). Une combinaison de motifs identifiants, par exemple un nom et une date, devient bloquante.

### API (`api/`)

- Routes : `/auth` (login, logout, me), `/chat/ask`, `/conversations` (liste, détail, suppression), `/admin/users` (création, modification, réinitialisation du mot de passe, révocation des sessions, consommation quotidienne).
- Stockage SQLite (`data/mispl.db`, non versionné), créé au démarrage. Mots de passe hachés en Argon2.
- Sessions par cookie `HttpOnly`, valables 8 h.
- Protections : verrouillage du compte après 5 échecs (15 min) ; limite de tentatives de connexion par compte et par IP ; limite de 20 requêtes par minute et par utilisateur sur `/chat/ask` ; corps de requête limité à 1 Mo, y compris en `Transfer-Encoding: chunked` ; en-têtes de sécurité (CSP `default-src 'none'`, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`) ; CORS restreint à `MISPL_FRONTEND_ORIGIN`.
- Pour une conversation existante, l'historique envoyé au LLM est relu en base : le client ne le fournit pas.

### Frontend (`frontend/`)

Next.js 16 / React 19 (App Router), avec les pages `/login`, `/chat` et `/admin`. Il appelle l'API à l'adresse `NEXT_PUBLIC_API_BASE` (par défaut `http://localhost:8000`) et applique ses propres en-têtes de sécurité (`next.config.ts`). **Attention** : cette version de Next.js diffère des versions antérieures. Consultez `frontend/AGENTS.md` avant de modifier le code.

## Structure du dépôt

- `rag_knowledge_base/` : base de connaissances MISPL (fiches Markdown par thème : `01_core_syntax/`, `02_functions/`, `03_chu_use_cases/`), avec son registre de traçabilité `SOURCES.md`. Voir la section « Propriété intellectuelle » ci-dessous.
- `docs/chunks/` : index généré (ChromaDB `vectorstore/`, `bm25_corpus.json`, `manifest_kb.json`). Non versionné ; se reconstruit avec `build_vectorstore.py`.
- `src/agent/`, `src/rag/`, `src/security/` : moteur (voir plus haut). `src/utils/resource_monitor.py` : relevé CPU/RAM/GPU et rapport Plotly (Streamlit).
- `api/` : backend FastAPI. `frontend/` : interface Next.js. `app.py` : interface Streamlit.
- `tools/check_ip_similarity.py` et `tools/ip_allowlist.json` : contrôle anti-régression de propriété intellectuelle de la base.
- `scripts/` : utilitaires, dont `create_admin.py`, `set_dsi_password.py`, `eval_retrieval_kb.py`, `health_check.py`, `list_free_models.py` et d'anciens scripts d'évaluation.
- `tests/` : suite pytest (`agent/`, `api/`, `rag/`, `security/`, `mispl_examples/`).
- `.claude/skills/mispl-*`, `.claude/rules/` et `.claude/agents/` : skills métier, règles globales et sous-agents chargés dans le prompt système.
- `outputs/` : scripts générés, sessions, cache, rapports de monitoring et d'évaluation. Les sessions, le cache et les rapports JSON ne sont pas versionnés.
- `docs/superpowers/` : spécifications et plans de conception. `docs/etude_faisabilite.md` : étude de faisabilité initiale (juin 2026).

## Installation

Prérequis : Python 3.10 ou plus récent ; Node.js pour le frontend.

```powershell
# 1. Environnement virtuel (ou : python setup.py)
python -m venv .venv
.venv\Scripts\activate

# 2. Dépendances Python
pip install -r requirements.txt

# 3. Fichier d'environnement
Copy-Item .env.example .env
# puis renseigner OPENROUTER_API_KEY dans .env

# 4. (Optionnel, Streamlit) mot de passe du mode DSI
python scripts/set_dsi_password.py

# 5. Frontend
cd frontend
npm install
```

Au premier usage, les modèles d'embedding et de reranking sont téléchargés depuis Hugging Face, puis mis en cache localement.

## Variables d'environnement

Ne versionnez jamais les valeurs : `.env` est exclu par `.gitignore`.

| Variable | Rôle | Défaut |
|---|---|---|
| `OPENROUTER_API_KEY` | Clé API OpenRouter (obligatoire pour interroger le LLM) | — |
| `OPENAI_API_KEY` | Embeddings OpenAI en option (`use_openai_embeddings=True`) | — |
| `PYTHONUTF8` | Force l'UTF-8 sous Windows (`1`) | — |
| `MISPL_DSI_PASSWORD_SALT`, `MISPL_DSI_PASSWORD_HASH` | Mot de passe du mode DSI (Streamlit). Générés par `scripts/set_dsi_password.py`, jamais saisis à la main | absent = mode DSI inatteignable |
| `MISPL_SESSION_RETENTION_DAYS` | Durée de conservation des sessions journalisées (jours) | `30` |
| `MISPL_CACHE_RETENTION_HOURS` | Durée de conservation du cache de réponses (heures) | `24` |
| `MISPL_RERANK_ENABLED` | Active le reranking cross-encoder | `true` |
| `MISPL_MONITOR` | `0` désactive le monitoring des ressources (Streamlit) | `1` |
| `MISPL_FRONTEND_ORIGIN` | Origine(s) autorisée(s) par CORS, séparées par des virgules | `http://localhost:3000` |
| `MISPL_COOKIE_SECURE` | Attribut `Secure` du cookie de session (`false` uniquement en développement HTTP local) | `true` |
| `NEXT_PUBLIC_API_BASE` | URL de l'API appelée par le frontend | `http://localhost:8000` |

## Construction de l'index RAG

L'index (ChromaDB et corpus BM25) doit être construit avant le premier lancement, puis reconstruit après toute modification de `rag_knowledge_base/` :

```powershell
python src/rag/build_vectorstore.py          # reconstruction complète (équivalent : .\start.ps1 build)
python src/rag/build_vectorstore.py --dry-run  # statistiques, sans écriture
```

Le résultat est écrit dans `docs/chunks/`. Sur la base actuelle, la construction donne **38 fiches, 439 blocs et 301 fonctions reconnues** (voir `docs/chunks/manifest_kb.json`). Après une reconstruction, le cache de réponses (`outputs/cache/`) peut contenir des réponses calculées sur l'ancien index. Il expire au bout de 24 h ; vous pouvez aussi le vider manuellement.

## Démarrage

**Plateforme API et frontend :**

```powershell
# Terminal 1 : API (crée data/mispl.db au premier démarrage)
uvicorn api.main:app --host 127.0.0.1 --port 8000

# Premier compte administrateur (une seule fois)
python scripts/create_admin.py

# Terminal 2 : frontend
cd frontend
npm run dev        # http://localhost:3000
```

**HTTPS est obligatoire en production.** Le cookie de session porte l'attribut `Secure` par défaut (`MISPL_COOKIE_SECURE`). En HTTP simple, le navigateur refuse le cookie sans afficher d'erreur et la connexion échoue. En développement local HTTP, définissez `MISPL_COOKIE_SECURE=false`.

**Interface Streamlit :**

```powershell
.\start.ps1 run    # http://localhost:8501  (équivalent : streamlit run app.py)
.\start.ps1 cli    # mode ligne de commande interactif
```

## Tests

```powershell
pytest
```

La configuration se trouve dans `pytest.ini` (`testpaths = tests`). La suite compte 270 tests. Elle couvre :
- l'agent : cache, repli entre modèles, linter, prompt, garde-fou de certitude, consommation ;
- l'API : authentification, routes, CORS, en-têtes, limite de taille, propriété des conversations ;
- le RAG : enrichissement BM25, formatage, reranking, catégories ;
- la sécurité : modes d'accès, DLP ;
- des exemples MISPL.

Les tests n'appellent pas OpenRouter, et les tests d'API utilisent une base SQLite en mémoire. En revanche, `tests/mispl_examples/` interroge l'index réel : construisez-le avant de lancer la suite complète.

## Évaluation du retrieval

```powershell
python scripts/eval_retrieval_kb.py                  # exact-match + sémantique
python scripts/eval_retrieval_kb.py --semantic-only  # sémantique seule
python scripts/eval_retrieval_kb.py --out mon_eval.json
```

Le script mesure deux choses :
1. **Exact-match** : chaque fonction connue de l'index est interrogée par son nom.
2. **Sémantique** : 50 questions en français, sans nom de fonction.

Il affiche hit@1, hit@3, hit@5, le MRR et les échecs, et écrit le détail dans `outputs/eval_retrieval_kb.json`.

Résultats sur l'index reconstruit le 2026-09-24 :

| Évaluation | n | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|---|
| Exact-match | 301 | 1,000 | — | — | — |
| Sémantique, index actuel | 50 | 0,600 | 0,740 | 0,800 | 0,693 |
| Sémantique, index précédent | 50 | 0,560 | 0,720 | 0,740 | 0,662 |

## Propriété intellectuelle de la base de connaissances

Le dépôt est public. La base `rag_knowledge_base/` ne doit contenir **aucune reprise de l'expression du manuel éditeur GLIMS**. Le manuel lui-même, ses exports et tout rapport d'audit qui en cite le texte ne sont jamais versionnés : `.gitignore` exclut `*.htm`, `*.html`, `*.pdf` et `docs/audit_PI_*/`.

**Méthode.** La base décrit des **faits techniques** : noms de fonctions, types et ordre des paramètres, types de retour, comportements observables, contraintes. Ces faits sont rédigés à nouveau en style factuel, dans le vocabulaire du langage proxy Progress ABL / OpenEdge. Les fiches « complément » (`*_extended.md`, `*_missing.md`) et `complete_function_data.json` sont générées par programme à partir de fiches de faits intermédiaires, sans lecture du manuel ni des anciennes descriptions. Les exemples de code proviennent de scripts du laboratoire ou ont été créés pour la base.

**Remédiation de septembre 2026.** Un audit de similarité a détecté des reprises du manuel dans une version antérieure de la base. Les fichiers concernés ont été régénérés à partir des fiches de faits, et les exemples repris ont été remplacés par des exemples originaux. Le contre-audit du 2026-09-23 ne relève plus aucun risque ÉLEVÉ ni MOYEN (avant : 281 ÉLEVÉ et 153 MOYEN).

**Garde-fou : `tools/check_ip_similarity.py`.** Ce script compare toute la base au manuel, qui reste sur le poste local, et, si on les fournit, aux sources déclarées. Il recherche :
- les reprises littérales de n-grammes : ≥ 15 mots = ÉLEVÉ, 8 à 14 mots = MOYEN ;
- la similarité TF-IDF sur un segment de 8 mots ou plus : ≥ 0,80 = MOYEN ;
- en option, les paraphrases, par embeddings e5 (≥ 0,95 avec TF-IDF < 0,60 = MOYEN) ;
- les exemples d'appel identiques à ceux du manuel.

Le script sort avec le code 1 dès qu'un risque ÉLEVÉ ou MOYEN est trouvé. Les exceptions justifiées se déclarent dans `tools/ip_allowlist.json` (fichier, fragment, justification). Ce contrôle réduit le risque de reprise ; il ne constitue pas une garantie juridique.

```powershell
python tools/check_ip_similarity.py --manual "<chemin local de l'aide GLIMS>"
python tools/check_ip_similarity.py --manual "<...>" --sources "<dossier de sources déclarées>"
python tools/check_ip_similarity.py --manual "<...>" --gpu-host <alias-ssh>   # embeddings e5 sur un poste GPU (optionnel)
python tools/check_ip_similarity.py --manual "<...>" --report ip_check.json  # rapport détaillé
```

Dépendances : `numpy`, `scikit-learn` et `beautifulsoup4` ; `pypdf` est optionnel. Elles sont listées dans `requirements.txt`. Le rapport produit par `--report` peut citer des passages du manuel : ne le versionnez pas.

**Procédure avant tout ajout ou toute modification de la base :**
1. Relever uniquement des faits (signature, paramètres, retour, comportement) et les rédiger avec vos propres mots. N'utilisez jamais d'exemple ou de valeur d'exemple du manuel.
2. Lancer `python tools/check_ip_similarity.py --manual ...`. Il doit se terminer par `RÉSULTAT : OK`. Corrigez tout signalement ÉLEVÉ ou MOYEN ; n'ajoutez une exception à `tools/ip_allowlist.json` qu'avec une justification écrite.
3. Mettre à jour `rag_knowledge_base/SOURCES.md` si une nouvelle source est utilisée.
4. Reconstruire l'index (`python src/rag/build_vectorstore.py`), puis relancer `pytest` et `scripts/eval_retrieval_kb.py`.

Pour la traçabilité complète (méthode, langage proxy, sources publiques, scripts d'exemple, audit), voir [`rag_knowledge_base/SOURCES.md`](rag_knowledge_base/SOURCES.md) et [`rag_knowledge_base/README.md`](rag_knowledge_base/README.md).

Voir aussi [`CHANGELOG.md`](CHANGELOG.md).
