# ADR-0006 — FastAPI + Next.js en plus de Streamlit

## Statut

Accepté.

## Date

2026-08-14 : première route API (commit `c00948b`, `feat(api): routes
/auth/login /auth/logout /auth/me`) et scaffold du frontend (commit
`b3e387a`, `feat(frontend): scaffold Next.js + design tokens Quiet Luxury`),
le même jour que les fondations de l'authentification par comptes
(`02754e5`, `e9a0a97`...). Contexte préalable documenté dans
`docs/superpowers/specs/` (spec « fondations migration frontend hors
Streamlit », commit `5b19baa`).

## Contexte

L'interface Streamlit (`app.py`) est mono-poste : un seul mode d'accès actif
par processus, pas de notion de compte individuel, pas d'historique par
utilisateur, pas de tableau de bord d'administration. Le besoin exprimé est
passé à plusieurs techniciens/DSI utilisant le service en parallèle, avec un
historique de conversations personnel et un suivi de consommation de jetons
par compte (les modèles LLM gratuits ont des limites de débit collectives,
cf. ADR-0002).

## Décision

Ajouter une plateforme multi-utilisateurs composée de :
- une **API FastAPI** (`api/`) : authentification par comptes (sessions par
  cookie), routes `/chat/ask`, `/conversations`, `/admin/users`, persistance
  SQLite (SQLAlchemy) ;
- un **frontend Next.js 16 / React 19** (`frontend/`, App Router) : pages
  `/login`, `/chat`, `/admin`.

Les deux composants appellent le même moteur Python (`src/agent/`,
`src/rag/`, `src/security/`) que l'interface Streamlit, sans dupliquer la
logique métier — `api/routers/chat.py` encapsule `ask_mispl()` derrière
l'authentification de compte (commit `4104278`, `feat(api): route
/chat/ask — encapsule ask_mispl derrière l'auth de compte`).

L'interface Streamlit **n'est pas retirée** : elle reste l'interface de
production pour l'usage mono-poste (déploiement Hugging Face Space via le
`Dockerfile`).

## Alternatives étudiées

- **Ajouter les comptes et l'historique directement à Streamlit** : écarté —
  Streamlit gère mal les sessions HTTP multi-utilisateurs avec cookies et
  droits d'accès fins ; une API dédiée avec un frontend séparé donne un
  contrôle complet sur l'authentification, les en-têtes de sécurité et le
  modèle de données relationnel (conversations, messages, usage).
- **Remplacer entièrement Streamlit par la plateforme API/Next.js** : écarté
  pour l'instant — Streamlit reste déployé en production (Hugging Face
  Space) et fonctionnel ; le retirer aurait interrompu un usage existant sans
  bénéfice immédiat.
- **Un framework frontend différent (SPA React sans Next.js, Vue...)** :
  Next.js a été retenu pour son App Router (routage par dossiers,
  server/client components) sans qu'une alternative n'ait été documentée
  comme sérieusement étudiée dans l'historique du projet.

## Conséquences

- Deux surfaces à maintenir en parallèle (Streamlit et API/Next.js), qui
  partagent heureusement le même moteur (`src/`) : un changement dans
  `ask_mispl()` ou les garde-fous de sortie profite aux deux interfaces sans
  duplication.
- Deux mécanismes de mode d'accès coexistent : mot de passe DSI partagé
  (Streamlit, ADR-0007) et droit `can_use_dsi_mode` par compte (API). La
  fonction `access_mode_for_user()` documente explicitement que le second
  mécanisme est destiné à terme à remplacer le premier, sans date de
  migration engagée.
- `frontend/AGENTS.md` avertit que la version de Next.js utilisée diffère
  des versions antérieures dans ses conventions : tout développeur doit lire
  ce fichier avant de modifier le code frontend.
- La plateforme API introduit une base de données (`data/mispl.db`) et donc
  une surface de sécurité supplémentaire (authentification, sessions,
  autorisation par ressource) que Streamlit n'avait pas.
