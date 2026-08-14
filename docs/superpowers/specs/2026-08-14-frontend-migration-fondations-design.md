# Migration frontend — Fondations (chantier A)

Date : 2026-08-14
Statut : approuvé, prêt pour plan d'implémentation

## Contexte

MISPL Agent est vendu comme produit à des laboratoires hospitaliers. L'UI
actuelle (`app.py`, Streamlit + injection CSS via `window.parent`) a un
plafond de verre déjà identifié : pas de vrai sidebar, pas de streaming
propre, pas de navigation multi-page — inadapté à un produit commercial
avec plusieurs comptes et un historique persistant.

Le système de comptes (auth API FastAPI, `api/`) est en place et mergé.
Ce chantier est le premier des quatre qui composent la migration complète :

1. **Chantier A (ce document)** — fondations : stack frontend, connexion,
   chat de base (parité fonctionnelle minimale avec `app.py`)
2. Chantier B — historique de sessions de chat en sidebar
3. Chantier C — dashboard admin (gestion des comptes)
4. Chantier D — mise à jour du script de lancement `.bat`

Chaque chantier a sa propre spec → plan → implémentation. Ce document ne
couvre QUE le chantier A.

Décisions actées en amont (non rediscutées ici) :
- Stack : Next.js + React (TypeScript), App Router
- Style CSS : CSS pur (variables/tokens), pas de framework utilitaire —
  fidélité à l'esthétique « Quiet Luxury » validée sur `biochimie-biologbook`
  (fond crème chaud, accent sauge sourd, titres serif, cartes arrondies
  douces, ombres discrètes)
- Pas de streaming dans ce chantier (réponse complète d'un coup) —
  chantier séparé plus tard
- Clé OpenRouter uniquement côté serveur (`.env`), jamais exposée ni
  saisissable côté technicien
- Mode DSI/Technicien dérivé du compte (`can_use_dsi_mode`, via
  `access_mode_for_user()` déjà construit dans `src/security/access_mode.py`)
  — plus de déverrouillage par mot de passe partagé dans le nouveau frontend
- Sélecteurs de modèle LLM et de « mode skill » masqués — tout automatique,
  cohérent avec le comportement par défaut déjà backend (`skill_profile=None`
  → auto-détection dans `ask_mispl`)
- Deux process séparés au lancement : FastAPI (:8000) et Next.js (:3000)

## Périmètre

**Inclus :**
- Nouveau dossier `frontend/` (Next.js, TypeScript) à la racine du dépôt
- Page de connexion (`/login`)
- Page de chat protégée (`/chat`) : poser une question, recevoir une
  réponse sourcée, contexte labo optionnel, exemples de questions en état
  vide, bouton nouvelle conversation
- Déconnexion
- Nouveau routeur API `api/routers/chat.py` (`POST /chat/ask`), protégé par
  authentification de compte
- Gestion des erreurs : DLP bloqué, session expirée (redirection login),
  erreur serveur/LLM indisponible
- CORS + configuration cookie cross-process (:3000 ↔ :8000)

**Explicitement hors périmètre (chantiers suivants ou non planifiés) :**
- Historique de sessions de chat (sidebar) — chantier B
- Dashboard admin — chantier C
- Script `.bat` — chantier D
- Streaming de la réponse
- Export de conversation (présent dans `app.py`, pas repris ici — pas
  essentiel à la parité fonctionnelle minimale, réévaluable plus tard)
- Monitoring ressources (CPU/RAM/GPU) — reste uniquement sur `app.py`
  tant que celui-ci existe ; pas un besoin technicien, outil DSI/dev
- Sélecteurs modèle/skill visibles — masqués par décision explicite
- `app.py`/Streamlit n'est PAS supprimé dans ce chantier — il continue de
  tourner en parallèle jusqu'à ce que le nouveau frontend couvre un
  périmètre suffisant pour le remplacer (décision de bascule finale hors
  périmètre de ce document)

## Architecture

```
┌─────────────────┐         HTTP (credentials: include)        ┌──────────────────┐
│  Next.js :3000   │ ───────────────────────────────────────►  │  FastAPI :8000    │
│  frontend/        │ ◄───────────────────────────────────────  │  api/              │
└─────────────────┘         cookie session_token (httpOnly)     └──────────────────┘
                                                                          │
                                                                          ▼
                                                                 ask_mispl() (src/agent)
```

`http://localhost:3000` et `http://localhost:8000` sont **same-site** (même
domaine `localhost`, seul le port diffère — la notion de "site" pour
`SameSite` ignore le port). Le cookie `session_token` (`SameSite=Strict`,
posé par `api/routers/auth.py`) circule donc normalement entre les deux en
local, sans changement de sa politique. Il faut seulement :
- Activer `CORSMiddleware` sur l'app FastAPI (`api/main.py`) avec
  `allow_origins=["http://localhost:3000"]` et `allow_credentials=True`
  (configurable via variable d'environnement pour un futur déploiement où
  les origines diffèrent)
- Que chaque appel `fetch()` côté frontend passe `credentials: "include"`

## Backend — nouveau routeur `api/routers/chat.py`

```
POST /chat/ask
  Auth : requiert une session valide (get_current_user)
  Body : { question: str, lab_context?: str }
  Réponse 200 : { response: str, sources: list[dict], blocked: false }
  Réponse 200 (DLP bloquant) : { response: null, sources: [], blocked: true, dlp_alerts: list[str] }
  Réponse 401 : non authentifié / session invalide (déjà géré par la dépendance)
  Réponse 503 : LLM/OpenRouter indisponible (message utilisateur clair, pas de trace brute)
```

Logique interne :
1. Construit `question_enriched` (question + contexte labo si fourni),
   même logique que `app.py` actuel
2. `dlp_check(question_enriched)` — si bloquant, retourne `blocked: true`
   sans jamais appeler le LLM (reprend exactement le comportement DLP
   actuel de `app.py`, juste déplacé côté API)
3. Sinon, appelle `ask_mispl(question_enriched, access_mode=access_mode_for_user(user.can_use_dsi_mode), save_session=True)`
   — `api_key` non passé explicitement : `ask_mispl` retombe sur
   `OPENROUTER_API_KEY` de l'environnement serveur (`.env`), déjà son
   comportement par défaut
4. Retourne la réponse + les sources (liste de dicts déjà retournée par
   `ask_mispl`, sérialisable telle quelle en JSON)

Pas de persistance de l'historique dans ce chantier (`save_session=True`
écrit déjà dans `outputs/sessions/` comme aujourd'hui — c'est la
journalisation existante, pas le futur historique de sessions par compte
du chantier B, qui sera un mécanisme différent lié à `user.id`).

## Frontend — structure

```
frontend/
  app/
    login/page.tsx        — formulaire connexion
    chat/page.tsx          — page de chat protégée
    layout.tsx              — layout racine, tokens Quiet Luxury en CSS globale
    globals.css              — variables de design (cf. palette ci-dessous)
  lib/
    api.ts                    — wrapper fetch (base URL API, credentials include, gestion 401)
  components/
    ChatMessage.tsx
    SourcesPanel.tsx
    EmptyState.tsx
```

**Palette Quiet Luxury (tokens CSS, adaptés de biologbook, à ajuster pour
un outil de chat plutôt qu'un dashboard clinique) :**
- `--bg: #faf9f6` (crème chaud), `--surface: #ffffff`
- `--ink: #1a1a1a`, `--ink-soft: #5c5c5c`, `--line: #e6e3dc`
- `--accent: #6f7d6a` (sauge sourde), `--accent-soft: #eef0ec`
- `--danger: #a8584f` (alertes DLP/erreurs)
- `--radius: 14px`, `--shadow: 0 1px 2px rgba(0,0,0,.03), 0 8px 24px rgba(0,0,0,.04)`
- `--serif: "Iowan Old Style", "Palatino Linotype", Georgia, serif` (titres)
- `--sans: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif` (corps)

**Protection de route `/chat`** : au chargement, appel `GET /auth/me` — si
401, redirection vers `/login`. Pas de middleware Next.js complexe pour ce
chantier (le cookie httpOnly n'est de toute façon pas lisible côté client
pour une vérification synchrone) — un simple guard côté client suffit vu le
périmètre.

## Gestion des erreurs

- **DLP bloquant** : message d'erreur inline dans le fil de conversation
  (reprend le texte actuel de `app.py`), pas de bulle assistant générée
- **Session expirée (401 sur `/chat/ask` en cours d'usage)** : redirection
  vers `/login` avec message "Session expirée, reconnectez-vous"
- **Erreur serveur/LLM (503 ou exception)** : message générique avec
  référence d'erreur (reprend le pattern `error_id` déjà présent dans
  `app.py`), pas de stack trace affichée

## Tests

**Backend** (`tests/api/test_chat_routes.py`) : route protégée (401 sans
session), DLP bloquant retourne `blocked: true` sans appeler `ask_mispl`
(mocké), mode DSI vs Technicien correctement dérivé du compte et transmis
à `ask_mispl` (vérifié via mock/spy), erreur LLM retourne 503 propre.

**Frontend** : pas de suite de tests automatisés dans ce chantier (premier
contact avec la stack, périmètre volontairement minimal) — vérification
manuelle documentée dans le plan (parcours : connexion → question → réponse
sourcée → DLP bloqué → déconnexion → session expirée). Une suite de tests
frontend (Playwright ou équivalent) pourra être ajoutée dans un chantier
ultérieur si le produit grandit.
