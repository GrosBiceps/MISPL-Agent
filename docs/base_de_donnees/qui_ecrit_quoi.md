# Qui écrit quoi

> Pour chaque table : les opérations (création, lecture, mise à jour,
> suppression), le composant et le fichier qui les déclenche, la route ou le
> script concerné, et le rôle qui en est à l'origine. Vérifié contre
> `api/routers/*.py`, `api/auth.py`, `api/audit.py`, `api/session_store.py`,
> `api/admin_bootstrap.py`, `scripts/create_admin.py`,
> `scripts/set_dsi_password.py` et `src/agent/mispl_agent.py`.
>
> Un chantier sécurité concurrent a ajouté un flux `/auth/change-password`
> et une table `audit_events` pendant la rédaction de ce document (voir
> `schema.md`, section « Écart modèle ORM / fichier réel ») ; les deux sont
> documentés ci-dessous tels qu'ils existent dans le code au 2026-09-24.

Rôles utilisés dans ce document :
- **Système** — code exécuté sans action utilisateur directe (démarrage API,
  script d'exploitation lancé par un opérateur en ligne de commande).
- **Utilisateur** — compte `platform_role = 'user'`, authentifié.
- **Admin** — compte `platform_role = 'admin'`, authentifié.
- **Anonyme** — requête non authentifiée (uniquement `POST /auth/login`).

## Table `users`

| Opération | Déclencheur | Fichier / ligne | Rôle |
|---|---|---|---|
| Création (premier admin) | `scripts/create_admin.py` → `create_admin_account` | `api/admin_bootstrap.py:14-33` | Système (opérateur exécutant le script en CLI, avant tout compte existant) |
| Création (compte suivant) | `POST /admin/users` | `api/routers/admin.py:46-78` | Admin |
| Lecture (liste + agrégats d'usage) | `GET /admin/users` | `api/routers/admin.py:81-121` | Admin |
| Lecture (résolution session→compte) | `validate_session` | `api/session_store.py:36-61` | Système, à chaque requête authentifiée (Utilisateur ou Admin) |
| Lecture (authentification) | `authenticate_user` | `api/auth.py:29-57` | Anonyme (avant obtention d'une session) |
| Mise à jour (profil, rôle, statut) | `PATCH /admin/users/{id}` | `api/routers/admin.py:124-176` | Admin |
| Mise à jour (mot de passe temporaire) | `POST /admin/users/{id}/reset-password` | `api/routers/admin.py:179-190` | Admin |
| Mise à jour (mot de passe choisi par l'utilisateur) | `POST /auth/change-password` | `api/routers/auth.py:150-190` | Utilisateur ou Admin (sur son propre compte, mot de passe actuel requis) |
| Mise à jour (compteur d'échecs, verrouillage, `last_login_at`, re-hachage transparent) | `authenticate_user`, `register_failed_attempt` | `api/auth.py:32-88` | Système, déclenché par une tentative de connexion (Anonyme) ou un mauvais mot de passe actuel sur `/auth/change-password` |
| Suppression | Aucune route ne supprime un compte `users` | — | — (désactivation via `is_active=False`, pas de suppression) |

Il n'existe pas de flux de réinitialisation de mot de passe en libre-service
(« mot de passe oublié », sans être déjà authentifié) : les deux voies sont
`POST /admin/users/{id}/reset-password` (Admin, génère un mot de passe
temporaire, pas de saisie du mot de passe précédent) et `POST
/auth/change-password` (l'utilisateur change lui-même son mot de passe,
mais doit déjà être connecté et fournir son mot de passe actuel).

**Écart constaté au 2026-09-24** : le modèle `User.must_change_password`
existe (`api/models.py:30-32`) et `api/dependencies.py:29-34` bloque déjà
l'accès aux routes protégées tant qu'il vaut `True`. `create_admin_account`
le positionne correctement à `False` (`api/admin_bootstrap.py:31`) — cohérent,
puisque l'admin choisit lui-même son mot de passe et le soumet à
`password_policy_errors`. En revanche, **les deux flux qui génèrent un mot
de passe *temporaire* ne positionnent `must_change_password` à `True` nulle
part** : ni `POST /admin/users` (création, `api/routers/admin.py:46-78`,
via `generate_temp_password`), ni `POST /admin/users/{id}/reset-password`
(`api/routers/admin.py:179-190`, même génération). Seul `POST
/auth/change-password` repositionne le champ, à `False`, après un
changement réussi (`api/routers/auth.py:180`). Concrètement, un compte créé
ou réinitialisé par un admin reçoit un mot de passe temporaire mais n'est
actuellement jamais forcé à le changer à la prochaine connexion — le
garde-fou existe côté modèle/dépendance mais n'est pas encore déclenché en
pratique. Ce point relève du chantier sécurité en cours, pas de ce lot ;
noté ici pour traçabilité.

## Table `sessions`

| Opération | Déclencheur | Fichier / ligne | Rôle |
|---|---|---|---|
| Création | `create_session`, appelée par `POST /auth/login` | `api/session_store.py:22-33`, `api/routers/auth.py:103` | Anonyme (devient Utilisateur/Admin dès la création) |
| Lecture / renouvellement glissant (`expires_at` repoussée) | `validate_session`, appelée par la dépendance `get_current_user` sur chaque route protégée | `api/session_store.py:36-61`, `api/dependencies.py:15-22` | Utilisateur ou Admin, à chaque requête |
| Mise à jour (révocation ciblée) | `revoke_session`, appelée par `POST /auth/logout` | `api/session_store.py:64-68`, `api/routers/auth.py:115-126` | Utilisateur ou Admin (sur sa propre session) |
| Mise à jour (révocation en masse) | `revoke_all_sessions_for_user`, appelée par `POST /admin/users/{id}/revoke-sessions`, par `reset-password`, et par `POST /auth/change-password` (avec `except_token` pour préserver la session courante) | `api/session_store.py:71-82`, `api/routers/admin.py:193-199,189`, `api/routers/auth.py:186` | Admin (sur les sessions d'un autre compte) ou Utilisateur/Admin (sur ses propres autres sessions, via change-password) |
| Suppression | Aucune route ne supprime une ligne `sessions` ; `cascade="all, delete-orphan"` supprime les sessions d'un `User` si ce dernier était supprimé (chemin non exposé par une route actuellement) | `api/models.py:33-35` | — |

## Table `conversations`

| Opération | Déclencheur | Fichier / ligne | Rôle |
|---|---|---|---|
| Création | `POST /chat/ask`, quand `conversation_id` est absent du payload | `api/routers/chat.py:182-185` | Utilisateur ou Admin (auteur de la question) |
| Lecture (liste) | `GET /conversations` | `api/routers/conversations.py:19-26` | Utilisateur ou Admin, filtré sur `user_id == <compte courant>` |
| Lecture (détail) | `GET /conversations/{id}` | `api/routers/conversations.py:29-43` | Utilisateur ou Admin, propriétaire uniquement (`get_owned_conversation_or_404`) |
| Lecture (implicite, pour reconstruire l'historique envoyé au LLM) | `POST /chat/ask` | `api/routers/chat.py:103-104` | Utilisateur ou Admin, propriétaire uniquement |
| Mise à jour (`updated_at`) | `POST /chat/ask` | `api/routers/chat.py:198` | Utilisateur ou Admin |
| Suppression | `DELETE /conversations/{id}` | `api/routers/conversations.py:46-53` | Utilisateur ou Admin, propriétaire uniquement — supprime en cascade les `messages` associés |

## Table `messages`

| Opération | Déclencheur | Fichier / ligne | Rôle |
|---|---|---|---|
| Création (message utilisateur + réponse assistant, en une transaction) | `POST /chat/ask` | `api/routers/chat.py:188-197` | Utilisateur ou Admin (question) ; Système (réponse générée par `ask_mispl`) |
| Lecture | `GET /conversations/{id}` et `POST /chat/ask` (reconstruction d'historique) | `api/routers/conversations.py:34-42`, `api/routers/chat.py:119-125` | Utilisateur ou Admin, propriétaire uniquement |
| Mise à jour | Aucune route ne modifie un message existant | — | — |
| Suppression | Cascade depuis `DELETE /conversations/{id}` uniquement (pas de suppression individuelle de message) | `api/models.py:65-67` | Utilisateur ou Admin, propriétaire de la conversation |

Avant écriture, chaque question et chaque historique passent par
`dlp_check` (`src/security/dlp.py`, appelé depuis `api/routers/chat.py:141-146`)
qui peut bloquer l'échange (rien n'est alors persisté, `ChatResponse(blocked=True)`).

## Table `usage_daily`

| Opération | Déclencheur | Fichier / ligne | Rôle |
|---|---|---|---|
| Création / mise à jour (upsert atomique `INSERT ... ON CONFLICT DO UPDATE`, clé `(user_id, date)`) | `_record_usage`, appelée par `POST /chat/ask` après chaque appel LLM réussi | `api/routers/chat.py:76-95,199` | Système, pour le compte de l'Utilisateur ou Admin ayant posé la question |
| Lecture (par jour, sur une période) | `GET /admin/users/{id}/usage-daily` | `api/routers/admin.py:202-234` | Admin |
| Lecture (agrégats 30 jours, liste des comptes) | `GET /admin/users` | `api/routers/admin.py:85-105` | Admin |
| Suppression | Aucune route ne supprime de ligne `usage_daily` | — | — |

## Table `audit_events` (modèle ORM — absente du fichier réel au 2026-09-24)

Voir `schema.md`, section « Écart modèle ORM / fichier réel », pour l'écart
entre ce que le code écrit et ce qui existe réellement dans
`data/mispl.db`.

| Opération | Déclencheur | Fichier / ligne | Rôle |
|---|---|---|---|
| Création | `record_event`, appelée par `authenticate_user`/`register_failed_attempt` (connexion, échec, verrouillage, re-hachage) et par les routes `POST /auth/logout` et `POST /auth/change-password` | `api/audit.py:32-58`, `api/auth.py:42,57,64,69,86-87`, `api/routers/auth.py:135-138,167-170,187-189` | Système, pour le compte de l'acteur (Anonyme en cas d'échec de connexion, Utilisateur/Admin pour logout et change-password) |
| Lecture | Aucune route n'expose de lecture du journal d'audit | — | — |
| Mise à jour / Suppression | Aucune — le journal est en écriture seule par conception (pas de clé étrangère vers `users`, pour survivre à la suppression d'un compte) | — | — |

Les événements `admin_user_created`, `admin_user_updated`,
`admin_password_reset` et `admin_sessions_revoked` sont définis comme
constantes dans `api/audit.py:26-29` mais **ne sont actuellement émis par
aucune route** : `api/routers/admin.py` n'importe pas `api.audit` (vérifié
par recherche textuelle dans le fichier). Seuls les événements liés à
`/auth/*` sont réellement journalisés au 2026-09-24.

## Diagrammes de séquence

### Création de compte

```{mermaid}
sequenceDiagram
    actor Admin
    participant API as POST /admin/users
    participant Dep as require_admin
    participant DB as users (table)

    Admin->>API: display_name, email, platform_role, can_use_dsi_mode
    API->>Dep: vérifie platform_role == 'admin' de l'appelant
    Dep-->>API: OK
    API->>API: generate_temp_password()
    API->>API: hash_password() (Argon2id)
    API->>DB: INSERT users (email unique, password_hash, ...)
    DB-->>API: compte créé
    API-->>Admin: CreateUserResponse (inclut le mot de passe temporaire, une seule fois)
```

### Connexion

```{mermaid}
sequenceDiagram
    actor U as Utilisateur/Admin
    participant Auth as POST /auth/login
    participant RL as Rate limiter (mémoire, par IP/email)
    participant Chk as authenticate_user
    participant DB as users (table)
    participant Sess as create_session
    participant SDB as sessions (table)
    participant Aud as audit_events (table, cf. écart schema.md)

    U->>Auth: email, password
    Auth->>RL: vérifie quota (10/5min par compte, 30/5min par IP)
    RL-->>Auth: OK (sinon 429)
    Auth->>Chk: authenticate_user(db, email, password, source_ip)
    Chk->>DB: SELECT users WHERE email=... AND is_active
    alt compte inconnu ou inactif
        Chk->>Aud: INSERT login_failure (detail=unknown_or_inactive)
        Chk-->>Auth: erreur invalid_credentials (temps égalisé via hash factice)
    else compte verrouillé (locked_until > now)
        Chk->>Aud: INSERT login_failure (detail=locked)
        Chk-->>Auth: erreur account_locked (même code HTTP que invalid_credentials)
    else mot de passe incorrect
        Chk->>DB: UPDATE failed_login_count (+ locked_until si seuil atteint)
        Chk->>Aud: INSERT account_locked (si seuil atteint), puis login_failure
        Chk-->>Auth: erreur invalid_credentials
    else mot de passe correct
        Chk->>DB: UPDATE failed_login_count=0, locked_until=NULL, last_login_at=now
        opt hachage obsolète (needs_rehash)
            Chk->>DB: UPDATE password_hash (Argon2id recalculé)
            Chk->>Aud: INSERT password_rehashed
        end
        Chk->>Aud: INSERT login_success
        Chk-->>Auth: user
    end
    Auth->>Sess: create_session(db, user)
    Sess->>SDB: INSERT sessions (token, expires_at = +8h)
    Auth-->>U: cookie httpOnly "session_token" + profil (dont must_change_password)
```

### Question avec historique

```{mermaid}
sequenceDiagram
    actor U as Utilisateur/Admin
    participant API as POST /chat/ask
    participant Dep as get_current_user
    participant DLP as dlp_check
    participant Agent as ask_mispl
    participant ConvDB as conversations (table)
    participant MsgDB as messages (table)
    participant UsageDB as usage_daily (table)

    U->>API: question, conversation_id?, lab_context?
    API->>Dep: valide le cookie de session
    Dep-->>API: user courant
    API->>ConvDB: SELECT conversation si conversation_id fourni (propriété vérifiée)
    API->>MsgDB: SELECT historique persisté de cette conversation (12 derniers messages)
    API->>DLP: dlp_check(question + historique)
    alt bloqué (donnée identifiante détectée)
        DLP-->>API: blocked=True
        API-->>U: ChatResponse(blocked=True, response=None) — rien n'est persisté
    else non bloqué
        DLP-->>API: OK
        API->>Agent: ask_mispl(question, historique, access_mode)
        Agent-->>API: réponse, sources, usage tokens
        API->>ConvDB: INSERT conversation si nouvelle, sinon UPDATE updated_at
        API->>MsgDB: INSERT message(role=user), INSERT message(role=assistant)
        API->>UsageDB: upsert usage_daily(user_id, date)
        API-->>U: ChatResponse(response, sources, conversation_id)
    end
```

### Réinitialisation de mot de passe (par un admin)

```{mermaid}
sequenceDiagram
    actor Admin
    participant API as POST /admin/users/{id}/reset-password
    participant Dep as require_admin
    participant DB as users (table)
    participant Sess as revoke_all_sessions_for_user
    participant SDB as sessions (table)

    Admin->>API: user_id
    API->>Dep: vérifie platform_role == 'admin'
    Dep-->>API: OK
    API->>DB: SELECT user (404 si absent)
    API->>API: generate_temp_password()
    API->>DB: UPDATE password_hash, failed_login_count=0, locked_until=NULL
    Note over API,DB: must_change_password n'est PAS positionné à True ici (écart constaté, cf. ci-dessus)
    API->>Sess: revoke_all_sessions_for_user(db, user_id)
    Sess->>SDB: UPDATE sessions SET revoked_at=now WHERE user_id=... AND revoked_at IS NULL
    API-->>Admin: ResetPasswordResponse (mot de passe temporaire, une seule fois)
```

### Changement de mot de passe (par l'utilisateur lui-même)

```{mermaid}
sequenceDiagram
    actor U as Utilisateur/Admin
    participant API as POST /auth/change-password
    participant Dep as get_authenticated_user
    participant Pol as password_policy_errors
    participant DB as users (table)
    participant Sess as revoke_all_sessions_for_user
    participant SDB as sessions (table)
    participant Aud as audit_events (table, cf. écart schema.md)

    U->>API: current_password, new_password
    API->>Dep: valide le cookie de session (must_change_password toléré)
    Dep-->>API: user courant
    API->>API: verify_password(current_password, user.password_hash)
    alt mot de passe actuel incorrect
        API->>DB: UPDATE failed_login_count (register_failed_attempt)
        API->>Aud: INSERT password_change_failed
        API-->>U: 400 invalid_current_password
    else mot de passe actuel correct
        API->>Pol: password_policy_errors(new_password, email, display_name)
        alt politique non respectée ou new == current
            Pol-->>API: liste d'erreurs
            API-->>U: 422 (erreurs, sans jamais renvoyer le mot de passe)
        else conforme
            API->>DB: UPDATE password_hash, must_change_password=False, failed_login_count=0, locked_until=NULL
            API->>Sess: revoke_all_sessions_for_user(db, user_id, except_token=session courante)
            Sess->>SDB: UPDATE sessions SET revoked_at=now WHERE user_id=... AND token != session courante
            API->>Aud: INSERT password_changed
            API-->>U: 200 "Mot de passe modifié"
        end
    end
```

Il n'existe pas de flux où un utilisateur non authentifié réinitialise son
mot de passe (pas de route publique de type « mot de passe oublié » avant
connexion trouvée dans `api/routers/`).
