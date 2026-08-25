# RAG — Filtrage par métadonnées + Reranking Cross-Encoder — Design

**Statut :** Approuvé par l'utilisateur (session du 2026-08-25), implémentation en pilotage autonome.

## Contexte

Audit du pipeline RAG (`src/rag/retriever.py`, `src/agent/mispl_agent.py`) mené le 2026-08-25. Constats principaux :

- Le corpus source réel est `rag_knowledge_base/` (38 fichiers Markdown, 426 chunks), pas `french/` (HTML) comme documenté dans `CLAUDE.md`. `french/` n'existe plus sur disque.
- L'embedding réel est `sentence-transformers` local (`paraphrase-multilingual-MiniLM-L12-v2`), pas OpenAI/nomic-embed-text comme documenté.
- Le retrieval est déjà hybride : dense (ChromaDB cosine) + BM25, fusion RRF (`RRF_K=25`), exact-match par nom de fonction (`where={"function_name": ...}`), expansion de requête par table de mots-clés statique (`_INTENT_EXPANSIONS`), `top_k` adaptatif, boosts multiplicatifs post-RRF (`×1.12`/`×1.08`/`×1.04`), réordonnancement anti-"lost in the middle".
- Le paramètre `category_filter` existe sur `MISPLRetriever.query()` mais n'est jamais appelé par `ask_mispl` — mort de fait.
- Le boost `×1.08` "catégorie MISPL pure" (`_MISPL_PURE_CATEGORIES`) est **déjà un no-op silencieux** : cette liste blanche (`string`, `datetime`, `math`...) ne correspond à AUCUNE valeur réelle de `domaine` dans la base. Les vraies catégories (frontmatter `domaine`, ~38 valeurs) sont par exemple `manipulation_chaines`, `table_result_extended`, `date_heure`, `calculs_mathematiques`, `reflexe_analytique`, `table_order_navigation`, etc.
- `skill_profile`/`access_mode` n'influencent jamais aujourd'hui QUELS chunks sont récupérés — seulement le prompt système et un filtre post-génération.
- Le cache (`_cache_key`) ne tient compte d'aucun paramètre interne au retrieval (table d'expansion, boosts, futur reranker) — seulement `question`, `model`, `top_k`, `skill_profile`, `access_mode`, historique.
- `sentence-transformers` (qui contient aussi `CrossEncoder`) est déjà une dépendance installée — aucune nouvelle dépendance nécessaire pour le reranking.
- Aucun test n'exerce `category_filter`, le reranking (inexistant), ou l'invalidation de cache liée au retrieval.

## Objectif

Améliorer la pertinence du retrieval sans introduire de risque d'hallucination, en deux volets combinés dans ce chantier :

1. **Filtrage par métadonnées** (révisé en boost non-excluant, cf. discussion) — utiliser `skill_profile` comme signal pour garantir la présence de catégories pertinentes dans le pool de candidats, sans jamais exclure de chunk.
2. **Reranking par cross-encoder** — remplacer les boosts heuristiques arbitraires par un score de pertinence sémantique réel, calculé sur un pool élargi de candidats RRF.

Plus : mise en cohérence du cache avec ces changements, et mise à jour de `CLAUDE.md` pour refléter le pipeline v3 réel.

## Global Constraints

- Aucune nouvelle dépendance pip (tout repose sur `sentence-transformers` déjà installé).
- Le filtrage par métadonnées ne doit JAMAIS exclure un chunk potentiellement pertinent — boost/garantie d'inclusion uniquement, jamais d'exclusion dure basée sur `skill_profile`.
- `access_mode` (DSI/Technicien) N'EST PAS câblé au filtrage retrieval — aucune catégorie de la base ne correspond à cette distinction (c'est une restriction de génération post-retrieval, pas un axe documentaire). Périmètre explicitement exclu.
- Les résultats exact-match (nom de fonction détecté) restent épinglés en tête de liste, non affectés par le reranking.
- Le reranking doit avoir un repli automatique sur l'ordre RRF existant en cas d'échec (modèle non chargeable, erreur d'inférence) — jamais d'erreur bloquante pour l'utilisateur final.
- Toute modification touchant le score/ordre de retrieval doit invalider le cache existant (bump de version).
- Respect de la règle anti-hallucination du projet (`.claude/rules/anti-hallucination.md`) : ce chantier ne touche à aucune étape de génération de code MISPL, uniquement au retrieval en amont.

---

## A. Filtrage par métadonnées (boost d'inclusion, pas filtre dur)

### A.1 Mapping skill → catégories

Nouveau dict statique dans `src/rag/retriever.py` (ou un nouveau petit module `src/rag/skill_categories.py` si `retriever.py` devient trop chargé) :

```python
SKILL_CATEGORY_BOOST: dict[str, set[str]] = {
    "mispl-core": {
        "structure_programme", "manipulation_chaines", "date_heure",
        "calculs_mathematiques", "conversion_types", "patterns_courants",
        "patterns_complexes", "variables_partagees", "contexte_execution",
        "interactions_utilisateur", "fonctions_diverses",
    },
    "mispl-reports": {
        "table_result", "table_result_extended", "result_missing",
        "table_correspondent", "correspondent_extended", "tables_diverses",
    },
    "mispl-erd-safety": {
        "table_order", "table_order_extended", "table_order_navigation",
        "order_missing", "table_object", "table_object_extended",
        "object_missing", "table_specimen", "table_specimen_extended",
        "specimen_missing", "table_action", "table_microbiology",
        "microbiology_missing", "table_blood_transfusion",
        "table_pathology_nonconformity", "table_person_site",
        "site_extended", "person_extended", "genetique_moleculaire",
        "tables_diverses",
    },
    "mispl-performance": {
        "reflexe_analytique", "validation_automatique_garde",
        "patterns_complexes",
    },
}
```

Ce mapping est une estimation sémantique à partir des noms de catégories réelles de la base — pas une vérité absolue. Il est centralisé dans une seule constante pour être facilement ajustable après coup sans toucher à la logique de retrieval.

### A.2 Intégration dans `MISPLRetriever.query()`

`active_skills` (liste de noms de skills, ex. `["mispl-core", "mispl-erd-safety"]`) doit être calculé et passé à `query()` — actuellement ce calcul (`_detect_skill_profile`) se fait APRÈS l'appel à `retriever.query()` dans `ask_mispl`. Il faut le déplacer avant.

Nouveau paramètre sur `query()` : `active_skills: list[str] | None = None`.

Comportement : construire l'union des catégories pertinentes (`relevant_categories = union(SKILL_CATEGORY_BOOST.get(s, set()) for s in active_skills)`). Lors de la construction du pool de candidats RRF envoyé au reranker (section B), garantir qu'au moins N candidats (ex. 3-4) dont la catégorie est dans `relevant_categories` sont inclus dans le pool, même s'ils sont juste sous le seuil de coupe RRF — sans jamais retirer les candidats déjà sélectionnés par RRF. Concrètement : élargir `fetch_n`/le pool RRF pour ce sous-ensemble de catégories si nécessaire (requête `where`-filtrée additionnelle sur ChromaDB, fusionnée au pool existant, dédupliquée par id).

Si `active_skills` est vide/None (mode "auto" sans détection) : aucun effet, comportement actuel préservé.

### A.3 Cache

Nouvelle constante `RETRIEVAL_PIPELINE_VERSION` dans `src/rag/retriever.py` (ex. `"r1"`), couvrant collectivement : la table d'expansion (`_INTENT_EXPANSIONS`), la logique de boost/inclusion par catégorie, et le modèle de reranking utilisé. Exportée et importée dans `src/agent/mispl_agent.py::_cache_key`, ajoutée à la chaîne `raw` de la clé de cache. Toute future modification de ces trois éléments doit s'accompagner d'un bump de cette constante (documenté en commentaire, à côté du commentaire existant sur `CACHE_VERSION`).

`skill_profile` est déjà dans la clé de cache existante (`skills_part`) — le nouveau boost par catégorie n'a donc besoin d'aucun axe de cache supplémentaire au-delà de `RETRIEVAL_PIPELINE_VERSION`.

### A.4 Documentation — `CLAUDE.md`

Corrections factuelles :
- Section "Stack" : remplacer la ligne embedding par la réalité (`sentence-transformers` local, `paraphrase-multilingual-MiniLM-L12-v2`, + reranking cross-encoder pour ce chantier). Retirer la mention LangChain/LlamaIndex — confirmé absent de `requirements.txt` et du code (`grep` négatif), jamais utilisé.
- Section "Stack" : remplacer "Documentation source : `french/`" par "Documentation source : `rag_knowledge_base/` — fiches Markdown (format Clean Room)".
- Section "Repository map" : remplacer l'entrée `french/` par `rag_knowledge_base/` — fiches source RAG (Markdown, ne pas modifier sans passer par le pipeline d'ingestion).

Le reste de `CLAUDE.md` (règles anti-hallucination, format de réponse, types MISPL) n'est pas concerné par ce chantier et reste inchangé.

---

## B. Reranking par cross-encoder

### B.1 Nouveau module `src/rag/reranker.py`

Responsabilité unique : charger un `CrossEncoder` (paquet `sentence_transformers`, déjà installé) en singleton lazy (même pattern que `_RetrieverState` dans `retriever.py`), et exposer une fonction `rerank(query: str, docs: list[dict]) -> list[dict]` qui :
1. Construit les paires `(query, doc["text"])` pour chaque candidat.
2. Appelle `CrossEncoder.predict(pairs)` pour obtenir un score réel de pertinence sémantique par paire.
3. Retourne les docs triés par score décroissant, avec `doc["score"]` mis à jour (le score cross-encoder remplace le score RRF/boost pour ces docs).
4. En cas d'exception à n'importe quelle étape (modèle non chargeable, erreur d'inférence, etc.) : logger un warning et retourner les docs dans leur ordre d'entrée inchangé (repli sur l'ordre RRF) — ne jamais lever d'exception vers l'appelant.

Modèle : `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (multilingue — le corpus et les questions sont majoritairement en français, contrairement à `ms-marco-MiniLM-L-6-v2` qui est anglais uniquement).

Variable d'environnement `MISPL_RERANK_ENABLED` (défaut `"true"`) — si à `"false"`, `rerank()` retourne immédiatement les docs inchangés sans charger le modèle. Permet de désactiver le reranking en production sans redéploiement de code si un problème de latence/qualité est détecté.

### B.2 Intégration dans `MISPLRetriever.query()`

Remplacer le bloc de boost multiplicatif actuel (`×1.12`/`×1.08`/`×1.04`, incluant le `×1.08` déjà mort) :

- Élargir le pool de candidats RRF avant troncature : actuellement plafonné à `k * 2` dans la boucle d'assemblage — remplacer par un pool fixe `RERANK_POOL_SIZE = max(k * 3, 20)` (couvre le "top 15-20" demandé, tout en restant proportionnel si `k` est élevé).
- Appliquer la garantie d'inclusion par catégorie (section A.2) sur ce pool élargi.
- Appeler `reranker.rerank(question, rrf_docs_pool)` — le résultat remplace `rrf_docs` triés.
- Tronquer à `k` APRÈS reranking (pas avant).
- `exact_docs` (fonction détectée verbatim) restent en tête, non passés au reranker, comportement inchangé.

### B.3 Performance

Pas de garantie a priori sur la latence ajoutée — à mesurer empiriquement pendant l'implémentation (log `logger.info` du temps d'inférence du reranker). Le pool étant petit (~20 chunks courts, modèle MiniLM léger), l'ajout attendu est de l'ordre de quelques dizaines à ~200ms sur CPU, mais ceci doit être vérifié et rapporté, pas supposé.

---

## Tests

- `tests/mispl_examples/test_basic_functions.py::TestRAGRetrieval` : tests existants doivent continuer à passer inchangés (ils exercent le vectorstore réel).
- Nouveau `tests/rag/test_reranker.py` : chargement du module, `rerank()` sur une paire triviale, comportement de repli si le modèle échoue à charger (monkeypatch), comportement quand `MISPL_RERANK_ENABLED=false`.
- Nouveau ou étendu `tests/rag/test_retriever_categories.py` (ou ajout à un fichier existant si plus approprié — à évaluer lors de l'implémentation) : `SKILL_CATEGORY_BOOST` couvre bien les 4 skills existants, la garantie d'inclusion par catégorie ajoute effectivement des candidats sans en retirer, `active_skills=None` ne change rien au comportement actuel.
- Test de cache : `_cache_key` change quand `RETRIEVAL_PIPELINE_VERSION` change (ou plus simplement : test que la constante est bien incluse dans la clé générée).
- Pas de suppression de test existant.

## Hors périmètre (explicitement exclu de ce chantier)

- Reformulation de requête par LLM (Étape 3 de la proposition initiale) — non traitée ici, à reprendre dans un chantier séparé si souhaité.
- `access_mode` → filtrage retrieval (cf. Global Constraints — aucune justification trouvée).
- MMR (maximal marginal relevance) / pénalité de diversité — non demandé, non traité.
- Changement du modèle d'embedding bi-encoder (`paraphrase-multilingual-MiniLM-L12-v2`) — hors périmètre, seul le reranking cross-encoder est ajouté en aval.
