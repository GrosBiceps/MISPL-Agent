# Authentification & comptes — MISPL Agent

Date : 2026-08-14
Statut : approuvé, prêt pour plan d'implémentation

## Contexte

MISPL Agent va être vendu comme produit à des laboratoires hospitaliers (CHU).
Aujourd'hui, l'application (`app.py`, Streamlit) n'a aucune notion de compte :
tout l'état vit dans `st.session_state` (perdu au refresh), et le mode DSI
(génération complète, boucles autorisées) se déverrouille via un mot de passe
partagé stocké en hash dans `.env` (`src/security/access_mode.py`).

Ce chantier est le **préalable technique** à trois features prévues ensuite :
historique de sessions de chat par utilisateur, quotas d'usage, dashboard
admin. Aucune des trois n'est faisable sans identifiant de compte stable.

Décisions actées en amont (non rediscutées ici) :
- Une seule instance déployée pour l'instant (un seul CHU, le vôtre) — pas de
  multi-tenant dans ce chantier.
- Comptes créés uniquement par l'admin — pas d'auto-inscription, jamais.
- Sécurité de connexion cible pour le lancement : email + mot de passe
  robuste (pas de 2FA au lancement — extensible plus tard).
- Reset de mot de passe géré par l'admin (pas de flow email — évite une
  dépendance à un service d'envoi d'email pour le lancement).
- Le mode DSI devient un attribut de compte (`can_use_dsi_mode`), assigné par
  l'admin, et remplace le mot de passe DSI partagé actuel.
- Sessions révocables côté serveur (pas de JWT stateless) — un compte
  compromis ou un technicien qui quitte le service doit pouvoir être coupé
  instantanément, ce qu'un JWT ne permet pas sans réimplémenter une liste de
  révocation (donc autant faire des sessions serveur directement).

## Périmètre

**Inclus dans ce chantier :**
- Modèle de données comptes + sessions (SQLite)
- API FastAPI : login, logout, vérification de session, gestion admin des
  comptes (créer/lister/modifier/désactiver/reset mot de passe/révoquer
  sessions)
- Migration de `can_use_dsi_mode` : `src/security/access_mode.py` prend ce
  flag de compte au lieu du mot de passe DSI partagé
- Script de bootstrap du tout premier compte admin
- Tests unitaires et d'intégration légère de l'API

**Explicitement hors périmètre (chantiers suivants, non traités ici) :**
- Historique de sessions de chat (dépend de ce chantier mais n'est pas ce
  chantier)
- Quotas d'usage / comptage de tokens
- Dashboard analytics admin (interface graphique)
- Migration du frontend hors Streamlit (ce chantier livre une API testable
  indépendamment, l'intégration UI viendra avec la migration frontend)
- Streaming des réponses
- SSO / annuaire d'établissement (écarté explicitement pour le lancement —
  trop coûteux à intégrer par client, un client par déploiement pour l'instant)
- Auto-inscription, 2FA, reset par email — écartés explicitement pour le
  lancement, réévaluables plus tard sans changement de modèle de données
  bloquant (les colonnes ajoutées ici n'empêchent pas ces extensions)

## Modèle de données

Nouveau fichier SQLite : `data/mispl.db` (nouveau dossier `data/` à la racine
du projet, à ajouter au `.gitignore` — contient des données de production,
jamais dans le repo).

### Table `users`

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | INTEGER | PK autoincrement | |
| `email` | TEXT | UNIQUE NOT NULL | identifiant de connexion |
| `password_hash` | TEXT | NOT NULL | Argon2id |
| `display_name` | TEXT | NOT NULL | affiché dans l'UI |
| `platform_role` | TEXT | NOT NULL, CHECK IN ('admin','user') | rôle plateforme |
| `can_use_dsi_mode` | BOOLEAN | NOT NULL DEFAULT 0 | remplace le mot de passe DSI partagé |
| `is_active` | BOOLEAN | NOT NULL DEFAULT 1 | désactivation sans suppression |
| `failed_login_count` | INTEGER | NOT NULL DEFAULT 0 | anti-bruteforce |
| `locked_until` | DATETIME | NULLABLE | verrouillage temporaire |
| `created_at` | DATETIME | NOT NULL | |
| `last_login_at` | DATETIME | NULLABLE | |

### Table `sessions`

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `token` | TEXT | PK | `secrets.token_urlsafe(32)`, jamais prévisible |
| `user_id` | INTEGER | FK → users.id NOT NULL | |
| `created_at` | DATETIME | NOT NULL | |
| `expires_at` | DATETIME | NOT NULL | glissant, renouvelé à chaque requête active |
| `revoked_at` | DATETIME | NULLABLE | NULL = session active |

`platform_role` (admin/user) et `can_use_dsi_mode` (bool) sont deux axes
indépendants : un `user` peut avoir `can_use_dsi_mode=true`, un `admin` peut
avoir `can_use_dsi_mode=false`. Ne pas coupler les deux dans le code.

## Flux d'authentification

- `POST /auth/login` `{email, password}` :
  1. Cherche l'utilisateur par email, `is_active=true`
  2. Si `locked_until` dans le futur → 423 Locked
  3. Vérifie `password_hash` (Argon2id)
  4. Échec → incrémente `failed_login_count` ; si ≥5 → `locked_until = now + 15min`, reset au prochain succès
  5. Succès → reset `failed_login_count`, crée une ligne `sessions` (`expires_at = now + 8h`), pose le cookie
  6. Réponse : cookie `session_token` (httpOnly, Secure, SameSite=Strict, jamais lisible en JS) + `{display_name, platform_role, can_use_dsi_mode}` dans le corps (pour que le frontend affiche l'état sans requête supplémentaire)

- **Vérification de session** (dépendance FastAPI réutilisée par tous les endpoints protégés) : lit le cookie → cherche en base → valide si `revoked_at IS NULL AND expires_at > now` → sinon 401 → si valide, prolonge `expires_at = now + 8h` (session glissante) et injecte l'utilisateur courant dans la requête

- `POST /auth/logout` : `revoked_at = now` sur la session courante, supprime le cookie

- `GET /auth/me` : retourne l'utilisateur courant (pour que le frontend sache qui est connecté au chargement)

## Administration

Toutes les routes ci-dessous exigent `platform_role='admin'` (403 sinon) :

- `POST /admin/users` `{email, display_name, platform_role, can_use_dsi_mode}` → crée le compte, génère un mot de passe temporaire aléatoire (12+ caractères), le retourne **une seule fois** dans la réponse (jamais stocké en clair, jamais renvoyé ensuite) — à communiquer manuellement au technicien
- `GET /admin/users` → liste (sans les hashs)
- `PATCH /admin/users/{id}` → modifier `display_name`, `platform_role`, `can_use_dsi_mode`, `is_active`
- `POST /admin/users/{id}/reset-password` → génère et retourne un nouveau mot de passe temporaire (même logique que la création)
- `POST /admin/users/{id}/revoke-sessions` → `revoked_at = now` sur toutes les sessions actives de l'utilisateur (coupure immédiate)

Pas d'interface graphique dans ce chantier — ces routes sont testées via
Swagger (`/docs` généré automatiquement par FastAPI) ou `curl`/`httpx`. L'écran
admin graphique arrive avec le chantier dashboard.

### Bootstrap du premier compte

`scripts/create_admin.py` (calqué sur `scripts/set_dsi_password.py` existant) :
prompt interactif email/mot de passe/nom, crée directement la ligne `users`
avec `platform_role='admin'`, `can_use_dsi_mode=true`. Seul moyen de créer le
tout premier compte — aucune route API ne peut créer un admin.

## Intégration avec le code existant

`src/security/access_mode.py` change de responsabilité :
- `verify_dsi_password()`, `hash_password()`, `generate_salt()` : **supprimés**
  — remplacés par l'attribut `user.can_use_dsi_mode` porté par le compte
- `MODE_DSI` / `MODE_TECHNICIEN` / `build_restrictions_prompt()` /
  `enforce_access_mode()` : **conservés tels quels**, mais le paramètre
  `access_mode: str` que reçoit `ask_mispl()` est désormais dérivé côté
  appelant par `MODE_DSI if user.can_use_dsi_mode else MODE_TECHNICIEN` — la
  fonction `ask_mispl()` elle-même ne change pas de signature
- `scripts/set_dsi_password.py` : **supprimé** (remplacé par
  `scripts/create_admin.py` + gestion via `PATCH /admin/users/{id}`)
- `.env` : les variables `MISPL_DSI_PASSWORD_SALT` / `MISPL_DSI_PASSWORD_HASH`
  deviennent obsolètes, à retirer de `.env.example`

Aucun changement dans `src/agent/`, `src/rag/`, ni dans les règles du linter
— ces couches restent découplées de l'authentification, elles reçoivent juste
`access_mode` comme aujourd'hui.

## Stack technique

- **API** : FastAPI (nouveau dossier `api/` à la racine, séparé de `src/` qui
  reste la logique métier pure)
- **DB** : SQLite via SQLAlchemy (ORM léger, migration facile vers Postgres
  plus tard si le multi-instance l'exigeait — non nécessaire aujourd'hui)
- **Hash mot de passe** : Argon2id (`argon2-cffi`), remplace PBKDF2 utilisé
  jusqu'ici pour le mot de passe DSI — Argon2id est la recommandation OWASP
  actuelle
- **Tokens de session** : `secrets.token_urlsafe(32)`, stockés en clair côté
  serveur (ce ne sont pas des mots de passe, pas besoin de les hasher — un
  vol de la base donnerait de toute façon accès à `sessions` directement)

## Erreurs & cas limites

- Compte désactivé (`is_active=false`) qui tente de se connecter → 401
  identique à mauvais mot de passe (ne pas révéler que le compte existe)
- Session valide mais compte désactivé entre-temps → la vérification de
  session doit aussi checker `is_active`, pas seulement l'expiration
- Dernier admin : `PATCH /admin/users/{id}` refuse de désactiver ou repasser
  en `user` le compte admin s'il ne reste qu'un seul admin actif (évite de se
  bloquer soi-même hors du système)
- Mot de passe temporaire généré : assez fort par défaut (12+ caractères,
  alphanumérique + symboles) pour ne pas nécessiter de politique de
  complexité supplémentaire à la création

## Tests

**Unitaires** (pas de serveur, logique pure) :
- Hash/vérification de mot de passe (Argon2)
- Validation de session : valide / expirée / révoquée / utilisateur désactivé
- Anti-bruteforce : verrouillage après 5 échecs, déverrouillage après 15 min,
  reset du compteur après succès
- Dérivation `access_mode` depuis `can_use_dsi_mode`

**Intégration API** (FastAPI `TestClient`, DB SQLite en mémoire) :
- Login réussi → cookie posé → `GET /auth/me` retourne le bon utilisateur
- Login échoué (mauvais mot de passe) → 401, pas d'indice sur l'existence du compte
- Logout → session révoquée → accès à un endpoint protégé refusé ensuite
- Endpoint admin appelé par un compte `user` → 403
- Création de compte par admin → mot de passe temporaire présent une seule
  fois dans la réponse, jamais dans les logs
- Révocation de session par l'admin → l'utilisateur ciblé perd l'accès
  immédiatement (avant expiration naturelle)
- Refus de désactiver le dernier admin actif
