# ADR-0001 — RAG hybride BM25 + dense + RRF + reranker cross-encoder

## Statut

Accepté.

## Date

Retrieval hybride BM25 + dense + RRF : 2026-06-07 (commit `058c34c`, `feat:
MISPL Agent v2 — base de connaissances manuelle (Clean Room)`), affiné le
2026-06-15 (commit `db7269f`, `fix(rag): audit retrieval — fonctions
courtes, expansion, synonymes, contamination`).

Ajout du reranking cross-encoder : 2026-08-25 (commit `9616300`, `feat(rag):
add standalone cross-encoder reranker module`, et `6935da5`, `feat(rag):
rerank RRF candidates with cross-encoder, drop dead heuristic boosts`).

## Contexte

MISPL Agent doit répondre à des questions sur des fonctions MISPL nommées
explicitement (« comment utiliser Substr ? ») aussi bien qu'à des questions
sémantiques sans nom de fonction (« comment tronquer une chaîne de
caractères ? »). Une recherche purement lexicale (mots-clés) rate les
reformulations ; une recherche purement dense (embeddings) rate parfois les
correspondances exactes de nom de fonction ou de termes techniques rares
dans le corpus d'entraînement des modèles d'embeddings.

## Décision

Combiner deux méthodes de retrieval :
- **BM25** (`rank_bm25`) sur un corpus tokenisé avec stemming français
  (NLTK `SnowballStemmer`), en préservant les identifiants MISPL en
  PascalCase (non stemmés).
- **Recherche dense** sur ChromaDB, avec des embeddings
  `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2` par
  défaut, embeddings OpenAI en option).

Les deux classements sont fusionnés par **Reciprocal Rank Fusion** (RRF,
`k=25` — calibré empiriquement pour un corpus technique dense d'environ 300
chunks pertinents ; `k=60`, valeur usuelle en RRF, diluait trop le signal sur
ce volume). Un **exact-match** de nom de fonction connu force un score de
1.0. Le pool de candidats post-RRF (`RERANK_POOL_SIZE = 20`) est ensuite
réordonné par un **cross-encoder multilingue**
(`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`), dont le rang est fusionné
avec le rang RRF plutôt que de le remplacer entièrement (`019b0a1`, `fix(rag):
blend reranker rank with original RRF rank instead of replacing it`).

Le reranking est désactivable via `MISPL_RERANK_ENABLED=false`.

## Alternatives étudiées

- **Dense seul** : plus simple, mais rate les correspondances exactes de nom
  de fonction et les termes techniques rares (constat de l'audit du
  2026-06-15).
- **BM25 seul** : rapide et précis sur les noms de fonction, mais ne
  généralise pas aux reformulations sémantiques.
- **RRF sans reranking** : suffisant en exact-match mais moins performant sur
  les requêtes sémantiques (référence documentée avant/après reranking dans
  `README.md` : hit@1 sémantique passé de 0,560 à 0,600 après l'ajout du
  reranking et de la garantie d'inclusion de catégories par skill).

## Conséquences

- Le pipeline a une version explicite (`RETRIEVAL_PIPELINE_VERSION` dans
  `src/rag/retriever.py`), à incrémenter à chaque changement d'expansion de
  requête, de boost de catégorie ou de modèle de reranking, pour invalider le
  cache réponse de l'agent.
- Le reranking ajoute un coût de calcul (chargement d'un modèle
  cross-encoder supplémentaire) et un temps de traitement par requête,
  compensé par le préchargement au démarrage de l'API
  (`api.main.warm_up_rag`).
- Toute évolution du retrieval doit être validée par
  `scripts/eval_retrieval_kb.py` contre la référence documentée dans
  `CLAUDE.md`/`README.md`, pour détecter une régression de pertinence.
