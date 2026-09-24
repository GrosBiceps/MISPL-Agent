# MISPL Agent — Règles de travail pour Claude

## Mission
Assistant IA spécialisé MISPL/GLIMS pour les techniciens de laboratoire de biologie médicale.
Priorités : zéro hallucination, traçabilité documentaire, code MISPL optimisé pour le serveur GLIMS.

## Dépôt public : règles impératives
- **Le dépôt GitHub est public.** Ne jamais versionner ni recopier dans un fichier suivi :
  - un extrait du manuel GLIMS (aide HTML/PDF) ;
  - une donnée patient ou une donnée interne du CHU ;
  - un nom d'hôte, une IP, un chemin réseau interne, un identifiant ou un secret.
- `docs/audit_PI_*/` contient le texte du manuel : ce dossier est exclu par `.gitignore` et ne doit jamais être versionné.
- `DSI/` (notes internes et juridiques) n'est pas suivi et ne doit pas l'être. Ne pas l'ajouter, ne pas citer son contenu.
- `.env` et `data/*.db` ne sont jamais versionnés. Toute nouvelle variable d'environnement se documente sans valeur.

## Stack
- Python 3.10 ou plus récent.
- RAG : ChromaDB (vectorstore local) + `rank_bm25` (stemming français NLTK), fusionnés par Reciprocal Rank Fusion (k = 25).
- Embeddings : `sentence-transformers` local (`paraphrase-multilingual-MiniLM-L12-v2`) par défaut ; OpenAI `text-embedding-3-small` en option (`use_openai_embeddings=True`).
- Reranking : cross-encoder multilingue (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) sur le pool de candidats après RRF. Désactivable par `MISPL_RERANK_ENABLED=false`.
- LLM : modèles gratuits OpenRouter (`FREE_MODELS` et `FALLBACK_ORDER` dans `src/agent/mispl_agent.py`).
- Backend : FastAPI + SQLAlchemy/SQLite (`api/`), Argon2, sessions par cookie.
- Frontend : Next.js 16 / React 19 (`frontend/`). Lire `frontend/AGENTS.md` avant de toucher au code : les API de cette version de Next.js diffèrent des versions antérieures.
- Interface historique : Streamlit (`app.py`), toujours lancée par `start.ps1` et par le `Dockerfile`.
- Base de connaissances : `rag_knowledge_base/`, fiches Markdown découpées par section H2 (38 fiches, 439 blocs, 301 fonctions reconnues).

## Carte du dépôt
- `rag_knowledge_base/` : fiches source du RAG. Voir « Propriété intellectuelle » avant toute modification.
- `docs/chunks/` : index généré (`vectorstore/`, `bm25_corpus.json`, `manifest_kb.json`), non versionné.
- `src/rag/` : ingestion (`ingest_knowledge_base.py`, appelé par `build_vectorstore.py`), retrieval hybride (`retriever.py`), reranking (`reranker.py`).
- `src/agent/` :
  - `mispl_agent.py` : `ask_mispl`, cache, repli entre modèles, garde-fous de sortie ;
  - `prompt_builder.py` : prompt système, garde anti-extraction ;
  - `linter.py` : lint et auto-corrections MISPL.
- `src/security/` : `access_mode.py` (modes Technicien/DSI) et `dlp.py` (données patient).
- `api/` : routes `auth`, `chat`, `conversations`, `admin`. `frontend/` : pages `login`, `chat`, `admin`.
- `tools/check_ip_similarity.py` et `tools/ip_allowlist.json` : garde-fou de propriété intellectuelle.
- `scripts/` : `create_admin.py`, `set_dsi_password.py`, `eval_retrieval_kb.py`, `health_check.py`, `list_free_models.py`, etc.
- `.claude/skills/mispl-*` : skills métier chargées dans le prompt système. `.claude/rules/` : règles globales. `.claude/agents/` : sous-agents.
- `tests/` : `agent/`, `api/`, `rag/`, `security/`, `mispl_examples/`.
- `outputs/` : scripts générés, sessions, cache, rapports (en grande partie non versionnés).

## Commandes utiles
```powershell
python src/rag/build_vectorstore.py              # reconstruit l'index après toute modification de la base
pytest                                           # 270 tests (tests/mispl_examples requiert l'index)
python scripts/eval_retrieval_kb.py              # hit@k / MRR, exact-match + 50 requêtes sémantiques
python tools/check_ip_similarity.py --manual "<chemin local de l'aide GLIMS>"   # contrôle PI
uvicorn api.main:app --port 8000                 # API
cd frontend; npm run dev                         # frontend (http://localhost:3000)
.\start.ps1 run                                  # interface Streamlit (http://localhost:8501)
```
Référence de l'évaluation (2026-09-24) : exact-match hit@1 = 1,000 sur 301 fonctions. Sémantique, 50 requêtes : hit@1 = 0,600, hit@3 = 0,740, hit@5 = 0,800, MRR = 0,693. Une modification du retrieval ne doit pas dégrader ces chiffres sans justification.

Pour éviter que des réponses périmées restent servies depuis le cache, incrémenter la version concernée :
- `CACHE_VERSION` (`src/agent/mispl_agent.py`) après une modification du prompt, du post-traitement ou des garde-fous de sortie ;
- `RETRIEVAL_PIPELINE_VERSION` (`src/rag/retriever.py`) après une modification de l'expansion de requête, du boost par catégorie ou du modèle de reranking.

Une reconstruction de l'index ne change pas la clé de cache : videz `outputs/cache/` si nécessaire.

## Propriété intellectuelle de la base de connaissances
- La base décrit des **faits techniques** : signature, paramètres, retour, comportement observable, contraintes. Ces faits sont rédigés avec nos propres mots, dans le vocabulaire du proxy Progress ABL / OpenEdge. **Ne jamais copier ni paraphraser de près une description ou un exemple du manuel**, ni réutiliser ses valeurs d'exemple.
- Les fichiers `*_extended.md`, `*_missing.md` et `complete_function_data.json` sont générés à partir de fiches de faits. Ne pas les réécrire à partir du manuel.
- Procédure avant tout ajout ou toute modification de `rag_knowledge_base/` :
  1. Lancer `tools/check_ip_similarity.py --manual ...`. Le résultat attendu est `RÉSULTAT : OK` (code de sortie 0). Tout signalement ÉLEVÉ ou MOYEN doit être corrigé. Une exception dans `tools/ip_allowlist.json` exige une justification écrite.
  2. Mettre à jour `rag_knowledge_base/SOURCES.md` si une nouvelle source est utilisée.
  3. Reconstruire l'index, puis relancer `pytest` et `scripts/eval_retrieval_kb.py`.
- Le rapport produit par `--report` et le dossier d'audit peuvent citer le manuel : ne jamais les versionner.
- Traçabilité complète : `rag_knowledge_base/SOURCES.md`.

## Règles absolues (anti-hallucination)

1. **Ne JAMAIS inventer une fonction MISPL.** Si la fonction n'est pas dans le RAG, répondre :
   > "Aucune documentation trouvée pour cette fonction. Voici du pseudo-code structuré."

2. **Toujours citer** le fichier source de la base et la section utilisée :
   > Source : `rag_knowledge_base/02_functions/string/string_functions.md` — section "Substr"

3. **Qualifier chaque réponse** avec un niveau de certitude :
   - ✅ **Certain** — fonction documentée, syntaxe confirmée
   - ⚠️ **Probable** — inférence depuis une documentation partielle
   - 🔬 **À vérifier** — syntaxe non trouvée, pseudo-code fourni

4. **Fallback obligatoire** si la syntaxe est absente : produire un pseudo-code commenté avec une structure MISPL valide.

5. **Efficience serveur GLIMS** : préférer les fonctions intégrées aux boucles manuelles et éviter les appels récursifs non nécessaires.

## Format de réponse
```
## Contexte GLIMS
[Rappel bref du contexte métier, 1-2 phrases]

## Code MISPL
[bloc de code]

## Source
[fichier + section documentaire]

## Niveau de certitude
[✅ Certain | ⚠️ Probable | 🔬 À vérifier]

## Notes techniques
[Risques, alternatives, conseils d'optimisation]
```

## Types de données MISPL
- `INTEGER`, `FRACTIONAL`, `STRING`, `LOGICAL`, `DATE`, `DATETIME`, `TIME`
- Valeur inconnue : `?` (UnknownValue). Toujours gérer les cas `?`.
- Opérateurs : `+`, `-`, `*`, `/`, `%`, `AND`/`&&`, `OR`/`||`, `NOT`/`!`
- Comparaisons : `EQ`/`=`, `NE`/`<>`, `LT`/`<`, `GT`/`>`, `LE`/`<=`, `GE`/`>=`

## Structures de contrôle MISPL
```mispl
IF condition THEN
  statement;
ELSE
  statement;
ENDIF

WHILE condition DO
  statement;
DONE

REPEAT
  statement;
UNTIL condition
```
En mode Technicien (mode par défaut), la génération de `WHILE`/`REPEAT` est interdite : consigne dans le prompt et barrière `enforce_access_mode` après génération.

## ELN / contraintes du laboratoire (ne pas modifier sans validation d'un biologiste)
- Identifiants d'échantillons : format propre au site, via `DatedIdentifier()` ou `NextValue()`.
- Logs obligatoires pour toute modification de résultat : `AddLogEntry()`.
- Variables partagées : accès via `GetSiteAttribute()` / `SetSiteAttribute()`.
