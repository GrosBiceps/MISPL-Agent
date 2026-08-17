# Chantier C — Dashboard admin et suivi de tokens — Design

## Contexte

Le backend CRUD `/admin/users` (création, liste, modification de rôle/mode
DSI/statut actif, reset password, révocation de sessions) existe depuis le
chantier auth (`api/routers/admin.py`) et est déjà testé. Aucune interface
frontend ne l'utilise. Ce chantier construit cette interface et y ajoute un
suivi de consommation de tokens par utilisateur — un nouveau sous-système,
faute d'infrastructure existante.

Le projet utilise exclusivement des modèles OpenRouter **gratuits**
(`FREE_MODELS` dans `src/agent/mispl_agent.py`) : le suivi de tokens n'a
aucun enjeu de facturation. Son objectif est la **visibilité d'usage**
(qui utilise l'outil, combien, avec quelle tendance dans le temps) — pas
de quota ni de blocage automatique.

**Investigation préalable** : `client.chat.completions.create(...)`
(`mispl_agent.py:319`) retourne un objet `completion` dont le champ
`usage` (tokens prompt/réponse/total, standard API compatible OpenAI)
n'est aujourd'hui pas exploité — seul `completion.choices[0].message.content`
est lu (`mispl_agent.py:437`). Le tracking est donc possible sans changer
l'infrastructure d'appel LLM.

**Contrainte identifiée** : `ask_mispl()` est appelée par une douzaine de
scripts (`scripts/eval_*.py`, `scripts/health_check.py`, `app.py` Streamlit
legacy, tests) qui déstructurent son retour en tuple `(response, docs)`.
Changer cette signature casserait tous ces appelants. La capture de tokens
passe donc par un paramètre de sortie optionnel, rétrocompatible.

## A. Capture des tokens (backend)

`ask_mispl(..., usage_out: dict | None = None)` — nouveau paramètre
optionnel en fin de signature. Quand fourni, la fonction y écrit
`{"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}`
juste après l'appel OpenRouter (à partir de `completion.usage`), avant de
retourner `(response_text, docs)` comme aujourd'hui. Aucun appelant
existant n'est affecté (paramètre optionnel, comportement de retour
inchangé).

Nouveau modèle SQLAlchemy `UsageDaily` (`api/models.py`, même style que
`Conversation`/`Message`) :

```
UsageDaily
  id: int PK
  user_id: int FK -> users.id
  date: Date (jour UTC)
  prompt_tokens: int, default 0
  completion_tokens: int, default 0
  request_count: int, default 0
```

Contrainte unique `(user_id, date)`.

Dans `api/routers/chat.py`, après un appel `ask_mispl()` réussi et non
bloqué par le DLP : upsert de la ligne du jour courant pour l'utilisateur
(incrémente les compteurs si la ligne existe déjà pour aujourd'hui, la
crée sinon avec `request_count=1`). Un message bloqué par le DLP n'appelle
jamais `ask_mispl()` — comme pour la persistance de conversation
(chantier B), rien n'est loggé dans ce cas, cohérent avec l'existant.

## B. Extensions API admin

- `GET /admin/users` — la réponse de chaque utilisateur s'enrichit de deux
  champs calculés :
  - `total_tokens_30d` : somme glissante de `prompt_tokens + completion_tokens`
    sur les 30 derniers jours (sous-requête agrégée sur `UsageDaily`).
  - `last_active_at` : date de la ligne `UsageDaily` la plus récente pour
    cet utilisateur (`None` si aucune activité).
- `GET /admin/users/{id}/usage-daily?days=30` — nouvelle route (garde
  `require_admin`, 404 si l'utilisateur n'existe pas), retourne la série
  quotidienne `[{date, prompt_tokens, completion_tokens, request_count}]`
  triée par date croissante, pour le graphique détaillé.

Le reste de l'API admin (création, modification, reset password,
révocation de sessions) ne change pas.

## C. Page admin (frontend)

Nouvelle route `frontend/app/admin/page.tsx`, protégée : au montage,
`getMe()` vérifie `platform_role === "admin"` ; sinon redirection vers
`/chat` (même pattern que la garde d'auth existante dans `chat/page.tsx`).
Un lien vers `/admin` apparaît dans `AccountMenu`, visible uniquement pour
les comptes admin.

**En-tête** : titre « Administration », bouton « + Nouveau compte » ouvrant
un formulaire modal (email, nom, rôle, case « Accès DSI »). À la création,
le mot de passe temporaire généré par l'API est affiché une seule fois
dans une bannière de confirmation (l'API ne le renvoie qu'à la création,
jamais consultable après).

**Tableau des comptes** — colonnes :
- Compte (avatar initiales + nom + email)
- Rôle (badge admin/user)
- Mode DSI (bascule — appelle `PATCH /admin/users/{id}` directement,
  mise à jour optimiste avec rollback si l'appel échoue)
- Statut actif (bascule, même mécanisme)
- Tokens (30j) (`total_tokens_30d` formaté, ex. « 12,4k »)
- Dernière activité (`last_active_at` relatif, ex. « il y a 2h », ou
  « jamais » si `null`)
- Actions : réinitialiser le mot de passe (affiche le nouveau mot de passe
  temporaire une fois), révoquer les sessions

La protection « impossible de désactiver/rétrograder le dernier admin
actif » est déjà appliquée côté API (409) — le frontend affiche l'erreur
retournée telle quelle, pas de logique dupliquée côté client.

**Panneau de détail** : cliquer sur une ligne (hors zone des actions/bascules)
ouvre un panneau latéral (`.card`, même traitement visuel que le panneau
du menu compte) avec les informations du compte et le graphique de
consommation (section D).

## D. Graphique de consommation

Composant `frontend/components/UsageChart.tsx` — barres verticales en SVG
inline, une par jour sur la fenêtre demandée (30 jours par défaut, appel à
`GET /admin/users/{id}/usage-daily?days=30`). Hauteur de chaque barre
proportionnelle au total de tokens du jour (`prompt_tokens + completion_tokens`),
couleur `var(--accent)`, axe de dates discret sous les barres (jour/mois,
un label sur deux si l'espace manque), infobulle native (`title`) au survol
d'une barre avec le détail prompt/réponse/nombre de requêtes. Aucune
nouvelle dépendance — cohérent avec l'approche SVG inline déjà suivie pour
les icônes (`AssistantAvatarIcon`, icônes de la sidebar). Jours sans
activité : barre à hauteur minimale visuelle (pas absente), pour que
l'axe temporel reste lisible.

## Tests

**Backend (pytest)** :
- `ask_mispl(usage_out=...)` peuple correctement le dict fourni sans
  changer la valeur de retour ; appel sans `usage_out` inchangé (non-régression
  des appelants existants).
- Upsert `UsageDaily` : première requête du jour crée la ligne,
  requêtes suivantes incrémentent ; DLP bloqué ne crée aucune ligne ;
  isolation entre utilisateurs et entre jours.
- `GET /admin/users` inclut `total_tokens_30d`/`last_active_at` corrects
  (agrégation sur plusieurs jours, utilisateur sans activité → `0`/`null`).
- `GET /admin/users/{id}/usage-daily` : série triée, fenêtre `days`
  respectée, 404 sur utilisateur inexistant, 403 pour un non-admin.

**Frontend** : comme pour les chantiers précédents, aucun framework de
test n'est configuré dans ce projet — vérification via `npx tsc --noEmit`,
`npm run build`, et vérification manuelle (garde de route non-admin,
création de compte, bascules de rôle/DSI/actif, affichage du graphique).
