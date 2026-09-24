# ADR-0004 — ChromaDB local comme vectorstore

## Statut

Accepté.

## Date

2026-06-07 (commit `058c34c`, `feat: MISPL Agent v2 — base de connaissances
manuelle (Clean Room)`) — ChromaDB fait partie du pipeline RAG dès la version
initiale documentée dans l'historique git.

## Contexte

Le retrieval dense a besoin d'un vectorstore pour indexer et interroger les
embeddings des fiches de `rag_knowledge_base/`. Le corpus est de taille
modeste (38 fiches, 439 blocs au 2026-09-24) et le projet s'exécute sur un
poste ou petit serveur du laboratoire, sans infrastructure de base de données
dédiée.

## Décision

Utiliser **ChromaDB** en mode local (persistant sur disque, sous
`docs/chunks/vectorstore/`), sans service serveur séparé à administrer. La
collection (`glims_mispl_docs`) est construite par
`src/rag/build_vectorstore.py`, qui délègue l'ingestion à
`src/rag/ingest_knowledge_base.py`.

## Alternatives étudiées

- **Un service vectoriel managé (cloud)** : écarté — coût récurrent non
  justifié pour un corpus de cette taille, et transfert de la base de
  connaissances (même « clean room ») vers un tiers externe non nécessaire.
- **FAISS ou une structure d'index maison** : plus léger, mais aurait
  nécessité de réimplémenter la gestion des métadonnées (source, section,
  nom de fonction, catégorie) que ChromaDB gère nativement par document.
- **Base vectorielle serveur (Postgres + pgvector, Milvus...)** : capacité
  largement supérieure au besoin réel (quelques centaines de chunks) ;
  aurait ajouté un service à déployer et opérer sans bénéfice mesurable pour
  ce volume.

## Conséquences

- L'index (`docs/chunks/`) est un artefact généré, non versionné (exclu par
  `.gitignore`), reconstruit par `python src/rag/build_vectorstore.py` après
  toute modification de la base de connaissances.
- ChromaDB étant local, aucune donnée du corpus ne transite vers un tiers
  pour l'étape de retrieval (contrairement à l'appel LLM, qui lui transite
  par OpenRouter).
- La capacité de ChromaDB local est suffisante pour le volume actuel, mais
  une croissance importante du corpus (au-delà de quelques milliers de
  chunks) pourrait nécessiter de revisiter ce choix.
