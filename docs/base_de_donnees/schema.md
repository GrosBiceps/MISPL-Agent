# Schéma de la base de données

> Vérifié le 2026-09-24 contre `api/models.py`, `api/db.py` et le schéma réel
> de `data/mispl.db` (lecture seule, `SELECT sql FROM sqlite_master`). Aucune
> donnée de ligne n'a été lue ni n'apparaît dans ce document — uniquement la
> structure (tables, colonnes, contraintes, index) et des comptages de lignes.
>
> **Le code évolue en parallèle de ce document** (lot sécurité concurrent).
> Deux écarts constatés entre `api/models.py` et le fichier réel
> `data/mispl.db` au moment de la rédaction sont documentés explicitement
> ci-dessous plutôt que masqués : la colonne `users.must_change_password` et
> la table `audit_events`, présentes dans le code ORM mais pas encore dans le
> fichier SQLite existant (voir « Écart modèle ORM / fichier réel »).

## Moteur et fichier

- SGBD : **SQLite**, fichier `data/mispl.db` (`api/db.py:14`).
- Le fichier n'est jamais versionné (`data/*.db` dans `.gitignore`).
- Pragmas activés à chaque connexion (`api/db.py:19-27`) :
  - `PRAGMA foreign_keys=ON` — les contraintes de clé étrangère déclarées
    ci-dessous sont réellement appliquées par le moteur, pas seulement
    documentaires ;
  - `PRAGMA busy_timeout=5000` — sous écriture concurrente, une requête
    attend jusqu'à 5 s un verrou libéré plutôt que d'échouer immédiatement.
- ORM : SQLAlchemy (`DeclarativeBase`), modèles dans `api/models.py`.
- Création du schéma : `Base.metadata.create_all(bind=engine)`, appelée au
  démarrage de l'API (`api/main.py:61`, dans `lifespan`) et par
  `scripts/create_admin.py:22` pour un déploiement vierge. `create_all` crée
  les tables manquantes mais **ne modifie jamais une table déjà existante**
  (n'ajoute pas de colonne à une table présente).
- `api/db.py` définit aussi `upgrade_schema()` (`api/db.py:54-71`), qui
  ajoute par `ALTER TABLE ... ADD COLUMN` les colonnes listées dans
  `_ADDED_COLUMNS` (actuellement `users.must_change_password`) si elles
  n'existent pas encore — non destructif, idempotent. **Au 2026-09-24, cette
  fonction n'est appelée nulle part** (`api/main.py` et
  `scripts/create_admin.py` appellent toujours directement
  `Base.metadata.create_all`, pas `upgrade_schema`) : sur une base déjà
  créée avant l'ajout de cette colonne, comme le fichier `data/mispl.db`
  inspecté pour ce document, la colonne `must_change_password` n'existe pas
  encore réellement en base tant que `upgrade_schema()` n'aura pas été
  branché puis exécuté. Pas de système de migration type Alembic dans ce
  dépôt : toute évolution de colonne suit ce même mécanisme manuel.

## Diagramme entité-association

```{mermaid}
erDiagram
    USERS ||--o{ SESSIONS : "possède"
    USERS ||--o{ CONVERSATIONS : "possède"
    USERS ||--o{ USAGE_DAILY : "cumule"
    CONVERSATIONS ||--o{ MESSAGES : "contient"

    USERS {
        integer id PK
        string email UK "unique, indexé"
        string password_hash "Argon2id"
        string display_name
        string platform_role "admin | user"
        boolean can_use_dsi_mode
        boolean is_active
        boolean must_change_password "modèle ORM seulement, cf. note"
        integer failed_login_count
        datetime locked_until "nullable"
        datetime created_at
        datetime last_login_at "nullable"
    }

    AUDIT_EVENTS {
        integer id PK "modèle ORM seulement, cf. note"
        datetime created_at "indexé"
        string event "indexé"
        integer actor_user_id "nullable, pas de FK"
        integer target_user_id "nullable, pas de FK"
        string source_ip "nullable"
        string detail "nullable, tronqué à 200 caractères"
    }

    SESSIONS {
        string token PK "secret, 32 octets urlsafe"
        integer user_id FK
        datetime created_at
        datetime expires_at
        datetime revoked_at "nullable"
    }

    CONVERSATIONS {
        integer id PK
        integer user_id FK "indexé"
        string title
        datetime created_at
        datetime updated_at
    }

    MESSAGES {
        integer id PK
        integer conversation_id FK "indexé"
        string role "user | assistant"
        string content
        string sources_json "nullable"
        datetime created_at
    }

    USAGE_DAILY {
        integer id PK
        integer user_id FK "indexé"
        date date
        integer prompt_tokens
        integer completion_tokens
        integer request_count
    }
```

Comptage de lignes au 2026-09-24 (contrôle de cohérence uniquement, pas une
donnée à suivre dans le temps) : `users` = 1, `sessions` = 12,
`conversations` = 12, `messages` = 34, `usage_daily` = 4.

## Table `users`

Définie dans `api/models.py:13-35`.

| Colonne | Type SQL | Contraintes | Sensibilité |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrément | — |
| `email` | VARCHAR | `NOT NULL`, **unique**, indexé (`ix_users_email`) | **Donnée personnelle** (identifiant direct) |
| `password_hash` | VARCHAR | `NOT NULL` | **Secret** — hash Argon2id, jamais le mot de passe en clair (voir `acces.md`) |
| `display_name` | VARCHAR | `NOT NULL` | Donnée personnelle (nom affiché) |
| `platform_role` | VARCHAR | `NOT NULL`, `CHECK (platform_role IN ('admin','user'))` (`ck_users_platform_role`) | — |
| `can_use_dsi_mode` | BOOLEAN | `NOT NULL`, défaut `False` | — (droit applicatif) |
| `is_active` | BOOLEAN | `NOT NULL`, défaut `True` | — |
| `must_change_password` | BOOLEAN | `NOT NULL`, défaut `False` (présent dans `api/models.py:30-32` et dans `_ADDED_COLUMNS` de `api/db.py`, **pas encore dans le fichier `data/mispl.db` inspecté** — voir note en tête de document) | — (droit applicatif) |
| `failed_login_count` | INTEGER | `NOT NULL`, défaut `0` | — (compteur anti-bruteforce) |
| `locked_until` | DATETIME | nullable | — |
| `created_at` | DATETIME | `NOT NULL`, défaut `utcnow()` | — |
| `last_login_at` | DATETIME | nullable | Donnée personnelle (trace d'activité) |

Index : `ix_users_email` (unique). Relation : `sessions` (1→N,
`cascade="all, delete-orphan"` côté ORM — supprimer un `User` supprime ses
`UserSession` associées).

Il n'existe **aucune table de rôle "technicien/DSI" séparée** : le mode DSI
est un simple booléen (`can_use_dsi_mode`) sur le compte, distinct du rôle
plateforme (`admin`/`user`) qui gouverne l'accès aux routes `/admin/*`. Voir
`acces.md` pour le détail des deux axes de contrôle.

## Table `sessions`

Définie dans `api/models.py:38-49`, gérée par `api/session_store.py`.

| Colonne | Type SQL | Contraintes | Sensibilité |
|---|---|---|---|
| `token` | VARCHAR | **PK** (pas d'`id` séparé) | **Secret** — jeton de session opaque, `secrets.token_urlsafe(32)` (`api/session_store.py:12,23`), équivalent à un mot de passe temporaire |
| `user_id` | INTEGER | `NOT NULL`, FK → `users.id` | — |
| `created_at` | DATETIME | `NOT NULL` | — |
| `expires_at` | DATETIME | `NOT NULL` | — |
| `revoked_at` | DATETIME | nullable | — |

Pas de rotation programmée en base : la table grossit tant qu'aucune purge
n'est exécutée (aucun script de purge des lignes `sessions` expirées/révoquées
n'a été trouvé dans le dépôt — voir `acces.md`, section rétention).

## Table `conversations`

Définie dans `api/models.py:52-67`.

| Colonne | Type SQL | Contraintes | Sensibilité |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrément | — |
| `user_id` | INTEGER | `NOT NULL`, FK → `users.id`, indexé (`ix_conversations_user_id`) | Donnée personnelle (rattache l'historique à un compte) |
| `title` | VARCHAR | `NOT NULL` — dérivé des 50 premiers caractères de la première question (`api/routers/chat.py:69-73`) | Peut contenir une donnée métier/labo selon la question posée |
| `created_at` | DATETIME | `NOT NULL` | — |
| `updated_at` | DATETIME | `NOT NULL` | — |

Relation : `messages` (1→N, `cascade="all, delete-orphan"`).

## Table `messages`

Définie dans `api/models.py:70-85`.

| Colonne | Type SQL | Contraintes | Sensibilité |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrément | — |
| `conversation_id` | INTEGER | `NOT NULL`, FK → `conversations.id`, indexé (`ix_messages_conversation_id`) | — |
| `role` | VARCHAR | `NOT NULL`, `CHECK (role IN ('user','assistant'))` (`ck_messages_role`) | — |
| `content` | VARCHAR | `NOT NULL` | **Donnée potentiellement de santé / métier CHU** — contenu libre saisi par le technicien (question) ou généré (réponse MISPL). Un contrôle DLP (`src/security/dlp.py`) s'exécute avant écriture pour bloquer les patterns identifiants connus (NIR, IPP...), mais ne garantit pas l'absence de toute donnée sensible dans un texte libre |
| `sources_json` | VARCHAR | nullable — sérialisation JSON des sources RAG citées | — |
| `created_at` | DATETIME | `NOT NULL` | — |

## Table `usage_daily`

Définie dans `api/models.py:88-99`.

| Colonne | Type SQL | Contraintes | Sensibilité |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrément | — |
| `user_id` | INTEGER | `NOT NULL`, FK → `users.id`, indexé | — |
| `date` | DATE | `NOT NULL` | — |
| `prompt_tokens` | INTEGER | `NOT NULL`, défaut `0` | — |
| `completion_tokens` | INTEGER | `NOT NULL`, défaut `0` | — |
| `request_count` | INTEGER | `NOT NULL`, défaut `0` | — |

Contrainte : `UNIQUE(user_id, date)` (`uq_usage_daily_user_date`) — une seule
ligne par compte et par jour, alimentée par upsert atomique (voir
`qui_ecrit_quoi.md`).

## Table `audit_events` (modèle ORM — pas encore dans le fichier réel)

Définie dans `api/models.py:109-129`, alimentée par `api/audit.py`
(`record_event`). **Absente de `data/mispl.db` au 2026-09-24** — voir
« Écart modèle ORM / fichier réel » ci-dessous.

| Colonne | Type SQL | Contraintes | Sensibilité |
|---|---|---|---|
| `id` | INTEGER | PK, autoincrément | — |
| `created_at` | DATETIME | `NOT NULL`, indexé | — |
| `event` | VARCHAR | `NOT NULL`, indexé — ex. `login_success`, `login_failure`, `account_locked`, `logout`, `password_changed`, `password_change_failed`, `password_rehashed`, `admin_user_created`, `admin_user_updated`, `admin_password_reset`, `admin_sessions_revoked` (constantes `api/audit.py:20-29`) | — |
| `actor_user_id` | INTEGER | nullable, **pas de clé étrangère** (volontaire, voir ci-dessous) | Donnée personnelle indirecte (identifiant de compte) |
| `target_user_id` | INTEGER | nullable, pas de clé étrangère | Donnée personnelle indirecte |
| `source_ip` | VARCHAR | nullable | Donnée personnelle (adresse IP) |
| `detail` | VARCHAR | nullable, tronqué à 200 caractères par `record_event` (`api/audit.py:44-45`) | Le docstring du module impose explicitement l'absence de mot de passe, de hachage, de jeton de session ou de contenu de conversation dans ce champ |

Absence intentionnelle de clé étrangère vers `users` (docstring
`api/models.py:109-117`) : le journal d'audit doit rester lisible même après
suppression d'un compte — cas qui n'est actuellement exposé par aucune route
(voir `qui_ecrit_quoi.md`, table `users`), mais que le modèle anticipe.

## Écart modèle ORM / fichier réel (2026-09-24)

Ce document décrit à la fois **le modèle ORM actuel** (`api/models.py`) et
**le fichier SQLite réellement présent** (`data/mispl.db`, inspecté en
lecture seule le 2026-09-24). Les deux ne coïncident pas complètement au
moment de la rédaction, parce qu'un chantier sécurité concurrent
(`docs/securite/`, lots A/B de `docs/engineering/SUIVI_TRAVAUX.md`) a ajouté
`must_change_password` et `AuditEvent` au code sans que le mécanisme de
migration (`upgrade_schema()`, `api/db.py:54-71`) ait encore été branché
dans `api/main.py` ni exécuté sur ce fichier. Concrètement :

- la colonne `users.must_change_password` n'existe pas dans
  `data/mispl.db` — toute requête ORM qui la lit ou l'écrit échouera contre
  ce fichier tant qu'`upgrade_schema()` n'aura pas tourné ;
- la table `audit_events` n'existe pas dans `data/mispl.db` — les appels à
  `audit.record_event()` échoueront contre ce fichier (le code les entoure
  d'un `try/except` qui journalise l'échec sans faire échouer la requête
  métier, `api/audit.py:44-58`, donc ceci n'interrompt pas l'API mais aucun
  événement n'est réellement persisté tant que la table n'existe pas).

Ce point relève du suivi du lot sécurité, pas de ce lot cartographie/BDD —
il est documenté ici pour qu'un lecteur du schéma ne soit pas surpris par
l'écart, et pour qu'un successeur sache qu'une re-vérification du schéma
réel après le prochain démarrage de l'API (une fois `upgrade_schema()`
branché) est nécessaire.

## Ce qui n'est PAS en base relationnelle

Voir `acces.md`, section « Autres stockages persistants », pour le cache de
réponses (`outputs/cache/`), les sessions RAG journalisées
(`outputs/sessions/`) et les index ChromaDB/BM25 (`docs/chunks/`), qui sont
des fichiers sur disque en dehors de `data/mispl.db`.
