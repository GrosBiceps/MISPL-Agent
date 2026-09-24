# ADR-0009 — Cache réponse 24 h versionné

## Statut

Accepté.

## Date

Cache disque question → réponse : présent dès la version initiale
documentée (commit `058c34c`, 2026-06-07). Versionnement explicite par
`CACHE_VERSION` et inclusion de `RETRIEVAL_PIPELINE_VERSION` dans la clé :
évolution continue, `CACHE_VERSION` étant à `v31` au 2026-09-24 (commit
`02b3225`).

## Contexte

Appeler le LLM à chaque question a un coût en temps de réponse (plusieurs
secondes à dizaines de secondes) et consomme le budget de débit partagé des
modèles gratuits OpenRouter (voir ADR-0002). Des questions identiques ou très
proches sont posées à plusieurs reprises par différents techniciens. À
l'inverse, servir une réponse obsolète (calculée avec un ancien prompt
système, un ancien post-traitement, ou un ancien index RAG) après une
modification du comportement de l'agent serait trompeur.

## Décision

Mettre en cache disque (`outputs/cache/`) la réponse à une question, pour
**24 heures**, avec une clé qui combine :
- le texte de la question, le modèle demandé, `top_k`, le profil de skills,
  le mode d'accès et un hash de l'historique de conversation (pour éviter
  qu'une réponse calculée dans un contexte — par exemple mode DSI — ne fuite
  vers un autre contexte, par exemple mode Technicien) ;
- `CACHE_VERSION` (`src/agent/mispl_agent.py`), à incrémenter à chaque
  modification du prompt système, du post-traitement de réponse ou des
  garde-fous de sortie ;
- `RETRIEVAL_PIPELINE_VERSION` (`src/rag/retriever.py`), à incrémenter à
  chaque modification de l'expansion de requête, du boost de catégorie ou du
  modèle de reranking.

Une purge automatique (`purge_old_cache`) supprime les fichiers de cache plus
anciens que la fenêtre de rétention (`MISPL_CACHE_RETENTION_HOURS`, défaut 24
h) au démarrage de l'API, pour éviter une croissance non bornée du dossier de
cache et la rétention indéfinie de contexte labo en clair sur disque.

## Alternatives étudiées

- **Pas de cache** : simple, mais chaque question identique reposée
  consommerait à nouveau le budget de débit partagé et le temps de réponse
  perçu serait systématiquement élevé.
- **Cache sans versionnement** : plus simple à implémenter, mais un
  changement de comportement de l'agent (nouvelle consigne de prompt,
  nouveau garde-fou) resterait invisible pendant jusqu'à 24 h pour les
  questions déjà en cache — risque identifié explicitement dans le code
  (commentaire de `_cache_key`).
- **Cache en base de données plutôt que sur disque** : non retenu — le
  volume et la durée de vie (24 h, purge automatique) ne justifient pas une
  table dédiée ; le cache disque est un artefact jetable, non versionné.

## Conséquences

- Reconstruire l'index RAG (`build_vectorstore.py`) **ne vide pas** le
  cache automatiquement : une réponse mise en cache avant la reconstruction
  peut continuer à être servie jusqu'à son expiration à 24 h. Un
  développeur qui a besoin d'observer l'effet immédiat d'un changement de
  base de connaissances doit vider `outputs/cache/` manuellement.
- Oublier d'incrémenter `CACHE_VERSION` ou `RETRIEVAL_PIPELINE_VERSION`
  après une modification pertinente peut faire servir une réponse obsolète
  pendant jusqu'à 24 h — un risque documenté explicitement dans `CLAUDE.md`
  et rappelé à chaque évolution du pipeline.
- Le cache contient potentiellement du contexte labo en clair (texte de la
  question) sur disque, sans chiffrement dédié ; sa fenêtre de rétention
  courte (24 h par défaut) limite l'exposition.
