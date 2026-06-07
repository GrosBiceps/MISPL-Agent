# 2 — Librairies et dépendances

Inventaire exhaustif des dépendances externes, avec leur rôle **précis dans ce projet**.

---

## RAG & Vectorstore

### `chromadb` (>=0.5.0)
**Rôle** : base de données vectorielle persistée sur disque (`PersistentClient`).
**Pourquoi ici** : stocke les embeddings denses des chunks de documentation GLIMS et permet la recherche par similarité cosinus.
- Collection unique `glims_mispl_docs`, métrique `hnsw:space = cosine` (configurée à la création dans `build_vectorstore.py`).
- À l'ingestion : `collection.add(ids, documents, metadatas)` par batch de 500.
- À la recherche : `collection.query(query_texts, n_results, include=["documents","metadatas","distances"])`.
- Sert aussi à l'**exact-match** via un filtre de métadonnée : `where={"function_name": X}`.

### `sentence-transformers` (>=3.0.0)
**Rôle** : génère les embeddings denses **localement** (hors-ligne, sans API).
**Pourquoi ici** : modèle `paraphrase-multilingual-MiniLM-L12-v2` — multilingue, ce qui est essentiel car les **questions sont en français** mais la **documentation contient des termes techniques anglais** (noms de fonctions MISPL). Embeddings 384 dimensions.
- Branché dans ChromaDB via `embedding_functions.SentenceTransformerEmbeddingFunction`.
- Alternative OpenAI (`text-embedding-3-small`) disponible mais optionnelle (`use_openai=True`).

### `rank-bm25` (>=0.2.2)
**Rôle** : recherche lexicale **sparse** (algorithme BM25 Okapi).
**Pourquoi ici** : complète le dense. Les embeddings ratent parfois un **nom de fonction exact** (`Substr`, `AddLogEntry`) ; BM25 l'attrape par correspondance de tokens. C'est la moitié « lexicale » de la recherche hybride.
- `BM25Okapi(tokenized_corpus)` construit l'index en mémoire au chargement.
- Le corpus est **enrichi** avant indexation : nom de fonction répété ×3, synonymes FR/EN, signature (voir fichier 3).

### `beautifulsoup4` (>=4.12.0) + `lxml` (>=5.0.0)
**Rôle** : parsing du HTML de la documentation GLIMS.
**Pourquoi ici** : la doc GLIMS est un ensemble de fichiers `.htm`. BeautifulSoup (backend `lxml`, plus robuste que `html.parser`) extrait les `<h3>` (une fonction par section), les `<table>` (signatures), les `<p>` (descriptions), les `<pre>/<code>` (exemples).

### `chardet` (>=5.2.0)
**Rôle** : détection automatique de l'encodage des fichiers HTML.
**Pourquoi ici** : la doc GLIMS mélange les encodages (UTF-8, latin-1). `chardet.detect()` devine l'encodage ; fallback latin-1 si échec. Évite les caractères corrompus dans les chunks.

---

## LLM

### `openai` (>=1.50.0)
**Rôle** : client HTTP pour l'API LLM.
**Pourquoi ici** : **OpenRouter** expose une API compatible OpenAI. On utilise donc le SDK `openai` pointé vers `https://openrouter.ai/api/v1`. Permet d'accéder à des modèles gratuits (nemotron-120b, kimi, llama, etc.) via une seule interface.
- `OpenAI(api_key, base_url, default_headers)` — les headers `HTTP-Referer` et `X-Title` sont obligatoires côté OpenRouter.
- `client.chat.completions.create(...)` avec `timeout=45`.
- Gestion explicite de `RateLimitError` pour le retry/fallback.

---

## Interface

### `streamlit` (>=1.40.0)
**Rôle** : framework d'interface web pure-Python.
**Pourquoi ici** : remplace une stack Docker/web lourde. Gère l'état de session (`st.session_state`), le chat (`st.chat_message`, `st.chat_input`), le cache de ressources (`@st.cache_resource`), les téléchargements (`st.download_button`).
- **Point critique** : `@st.cache_resource` (PAS `@st.cache_data`) pour charger l'agent, car la valeur de retour contient des **fonctions non-sérialisables**.

---

## Utilitaires

### `python-dotenv` (>=1.0.0)
**Rôle** : charge les variables d'environnement depuis `.env`.
**Pourquoi ici** : lit `OPENROUTER_API_KEY` (et optionnellement `OPENAI_API_KEY`) au démarrage sans les hardcoder.

### `tqdm` (>=4.66.0)
**Rôle** : barres de progression.
**Pourquoi ici** : feedback visuel pendant le build du vectorstore (parsing de centaines de fichiers HTML + ingestion par batch).

---

## Standard library notable

| Module | Usage dans le projet |
|---|---|
| `hashlib` | SHA-256 pour la clé de cache ; MD5 pour les IDs de chunks. |
| `unicodedata` | Dé-accentuation (`chaîne` → `chaine`) pour le matching cross-langue dans le tokenizer BM25. |
| `re` | Tokenisation PascalCase, détection de noms de fonctions, nettoyage de texte. |
| `json` | Sérialisation du corpus BM25, du manifest, des sessions et du cache. |
| `html` | `html.escape()` sur les entrées utilisateur affichées (anti-XSS). |
| `logging` | Logs structurés (rate-limit, fallback, erreurs avec ID de référence). |
| `functools.lru_cache` | Cache mémoire sur `_load_skill` et `_load_rules`. |
