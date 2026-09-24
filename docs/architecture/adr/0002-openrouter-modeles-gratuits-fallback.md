# ADR-0002 — OpenRouter et modèles gratuits avec repli

## Statut

Accepté.

## Date

2026-06-07 (commit `058c34c`, `feat: MISPL Agent v2 — base de connaissances
manuelle (Clean Room)`) pour le choix initial d'OpenRouter et de modèles
gratuits. Robustesse du repli renforcée le 2026-08-17 (commit `3026f31`,
`fix(agent): cap total LLM-fallback retry time and log every failed
attempt`) et corrigée le 2026-08-26 (`ed10de6` et suivants, correction du
repli sur les erreurs 429).

## Contexte

Le projet ne dispose pas d'un budget dédié à un LLM payant à haute
disponibilité, et l'hébergement d'un modèle en interne n'est pas envisageable
pour un laboratoire de biologie médicale sans infrastructure GPU dédiée.
OpenRouter expose une API compatible OpenAI donnant accès à plusieurs modèles
gratuits, mais chacun avec ses propres limites de débit et une disponibilité
non garantie.

## Décision

Utiliser l'API OpenRouter (client `openai` Python, `base_url` pointée vers
OpenRouter) avec une liste de modèles gratuits (`FREE_MODELS`) et un ordre de
repli explicite (`FALLBACK_ORDER`) en cas d'erreur 429 (limite de débit) ou
d'indisponibilité. Le repli :
- retente le modèle courant avec un délai indiqué par l'API (`retry_after`)
  avant de passer au modèle suivant ;
- s'arrête immédiatement sur une erreur 404 (modèle inexistant côté
  fournisseur) sans retenter ;
- est borné par un budget de temps total (`_MAX_TOTAL_WAIT_SECONDS = 60`),
  tous modèles et tentatives confondus, pour qu'un worker FastAPI synchrone
  ne reste jamais bloqué plusieurs minutes si tous les modèles gratuits sont
  rate-limités simultanément.

Le nom du modèle effectivement utilisé est ajouté en tête de réponse quand il
diffère du modèle demandé (transparence pour l'utilisateur).

## Alternatives étudiées

- **Un seul modèle gratuit, sans repli** : plus simple, mais un modèle
  gratuit peut devenir indisponible sans préavis (limite de débit collective
  à tous les utilisateurs d'OpenRouter) ; le repli était nécessaire dès la
  version initiale du projet.
- **Modèle payant unique** : disponibilité meilleure, mais coût récurrent non
  budgété pour ce projet, et dépendance à un seul fournisseur.
- **Hébergement local d'un modèle open source** : évite la dépendance à un
  tiers, mais nécessite une infrastructure GPU que le laboratoire ne possède
  pas ; écarté pour cette raison.

## Conséquences

- La qualité et la disponibilité du service dépendent de facteurs hors du
  contrôle du projet (limites de débit d'OpenRouter, retrait d'un modèle
  gratuit). `scripts/list_free_models.py` permet de vérifier la liste
  actuelle des modèles disponibles.
- Le budget de temps de 60 secondes signifie qu'un utilisateur peut recevoir
  une erreur 503 (`Tous les modèles OpenRouter sont indisponibles`) en cas
  d'indisponibilité générale, plutôt qu'une attente indéfinie.
- Le cache réponse de 24 h (voir ADR-0009) réduit la dépendance au LLM tiers
  pour les questions déjà posées récemment.
