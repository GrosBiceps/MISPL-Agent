# Accès et autorisation

> Vérifié contre `api/dependencies.py`, `api/ownership.py`, `api/security.py`,
> `api/auth.py`, `api/audit.py`, `api/routers/*.py`, `src/security/access_mode.py`,
> `.gitignore` et `data/mispl.db` (schéma et comptages uniquement, lecture
> seule). Voir `schema.md`, section « Écart modèle ORM / fichier réel », pour
> l'état d'avancement du chantier sécurité concurrent (`must_change_password`,
> `audit_events`) au 2026-09-24.

## Deux axes d'autorisation distincts

Le système combine deux mécanismes indépendants, tous deux portés par la
table `users` :

1. **`platform_role`** (`'admin'` / `'user'`) — contrôle l'accès aux routes
   `/admin/*` (gestion des comptes). Appliqué par la dépendance FastAPI
   `require_admin` (`api/dependencies.py:25-28`), qui lève `403` si
   `user.platform_role != "admin"`.
2. **`can_use_dsi_mode`** (booléen) — contrôle, indépendamment du rôle
   plateforme, si les réponses générées par l'agent RAG peuvent contenir des
   boucles `WHILE`/`REPEAT` (mode DSI) ou sont bridées (mode Technicien,
   défaut fail-safe). Traduit en mode via `access_mode_for_user`
   (`src/security/access_mode.py:231-240`), appliqué en génération
   (prompt système) puis en barrière dure post-génération
   (`enforce_access_mode`, `src/security/access_mode.py:204-228`) qui
   remplace la réponse si une boucle apparaît malgré la consigne.

Un compte `platform_role='user'` peut avoir `can_use_dsi_mode=True` : les
deux axes ne sont pas hiérarchiquement liés dans le modèle de données (un
Admin n'a pas automatiquement le mode DSI — `create_admin_account` le force
à `True` pour le tout premier compte, mais `POST /admin/users` laisse
`can_use_dsi_mode` au choix de l'Admin créateur pour les comptes suivants).

Un mécanisme plus ancien et distinct subsiste dans `access_mode.py`
(`verify_dsi_password`, `hash_password`/PBKDF2) : un mot de passe DSI
partagé, configuré via les variables d'environnement
`MISPL_DSI_PASSWORD_HASH`/`MISPL_DSI_PASSWORD_SALT` et positionné par
`scripts/set_dsi_password.py`. D'après le commentaire dans le code
(`src/security/access_mode.py:231-239`), ce mécanisme reste utilisé par
`app.py` (Streamlit), qui n'a pas de notion de compte individuel, tandis que
l'API FastAPI utilise exclusivement `can_use_dsi_mode` par compte.

## Authentification

- Hachage : **Argon2id**, via `argon2.PasswordHasher` avec des paramètres
  figés explicitement plutôt qu'hérités des valeurs par défaut de la
  bibliothèque (`api/security.py:24-37`) : `time_cost=3`,
  `memory_cost=65536` KiB (64 Mio), `parallelism=4`, `hash_len=32` octets,
  `salt_len=16` octets. Ce profil correspond au second profil recommandé
  par la RFC 9106 §4 et dépasse le minimum OWASP. Décision actée le
  2026-09-24 avec le RSSI : conserver Argon2id plutôt que migrer vers bcrypt
  (voir `docs/engineering/SUIVI_TRAVAUX.md`, lot A, et
  `docs/securite/NOTE_RSSI_HACHAGE_MOTS_DE_PASSE.md` pour l'argumentaire
  détaillé — hors périmètre de ce document).
- Re-hachage transparent : `needs_rehash()` (`api/security.py:75-82`)
  détecte un hachage produit avec d'autres paramètres ; s'il diffère de la
  configuration courante, `authenticate_user` le recalcule au moment de la
  connexion réussie (seul instant où le mot de passe en clair est
  disponible) et journalise `password_rehashed` (`api/auth.py:76-87`). Ce
  mécanisme permet de renforcer les paramètres Argon2id dans le futur sans
  forcer une réinitialisation de masse.
- Politique de mot de passe choisi par l'utilisateur
  (`password_policy_errors`, `api/security.py:98-128`), appliquée sur
  `POST /auth/change-password` : 12 caractères minimum avec au moins 3 des
  4 familles de caractères (minuscules, majuscules, chiffres, spéciaux), OU
  une phrase de passe d'au moins 16 caractères ; 256 caractères maximum ; ne
  doit pas contenir l'identifiant (partie locale de l'email) ni le nom
  affiché ; ne doit pas figurer dans une liste de mots de passe triviaux.
  Cette politique **ne s'applique pas** à la création de compte ni au reset
  admin (mot de passe temporaire généré aléatoirement par
  `generate_temp_password`, non soumis au choix de l'utilisateur).
- Le mot de passe en clair n'est jamais stocké ni journalisé par le code de
  ce dépôt : seul `password_hash` est persisté (`api/models.py:22`). Le
  journal d'audit (`audit_events`, voir plus bas) est explicitement conçu
  pour ne jamais recevoir de mot de passe, de hachage ni de jeton de
  session (docstring `api/audit.py:1-4`).
- **Changement de mot de passe obligatoire (`must_change_password`)** :
  colonne booléenne sur `users`, vérifiée par `get_current_user`
  (`api/dependencies.py:29-34`), qui bloque `403
  password_change_required` sur toute route sauf `/auth/me`,
  `/auth/logout` et `/auth/change-password` (dépendance
  `get_authenticated_user`, plus permissive) tant qu'elle vaut `True`.
  **Constat au 2026-09-24** : les flux qui génèrent un mot de passe
  temporaire (création par un admin, reset par un admin) ne positionnent ce
  champ à `True` nulle part dans le code actuel — voir `qui_ecrit_quoi.md`
  pour le détail. Le garde-fou existe côté modèle et côté dépendance
  FastAPI mais n'est pas encore déclenché en pratique.
- Session : jeton opaque aléatoire (`secrets.token_urlsafe(32)`,
  `api/session_store.py:12,23`), transmis par cookie `httpOnly`,
  `SameSite=Strict`, `Secure` (configurable via `MISPL_COOKIE_SECURE`,
  vrai par défaut) — jamais transmis en URL ni en JSON de réponse.
  TTL glissant de 8 h (`SESSION_TTL_HOURS`), renouvelé à chaque requête
  valide (`api/session_store.py:36-51`).
- Révocation serveur : une session peut être invalidée immédiatement (logout,
  reset de mot de passe, action admin `revoke-sessions`) sans attendre
  l'expiration — pas de JWT auto-porteur, chaque requête revalide la ligne
  `sessions` en base (`api/session_store.py:1-7`, commentaire de module).
- Anti-bruteforce :
  - par compte : verrouillage après `LOCK_THRESHOLD=5` échecs, pour
    `LOCK_DURATION_MINUTES=15` (`api/auth.py:15-16,36-42`) ; le même
    compteur/verrouillage est partagé avec `POST /auth/change-password`
    (un mauvais mot de passe *actuel* compte comme un échec de connexion,
    via `register_failed_attempt`, `api/auth.py:32-42`) ;
  - au niveau HTTP : rate limiting en mémoire par (IP, email) et par IP seule
    sur `POST /auth/login` (`api/routers/auth.py:49-95`) ;
  - égalisation de temps de réponse entre « compte inconnu », « compte
    verrouillé » et « mot de passe incorrect » via un hash Argon2 factice
    constant (`api/auth.py:18-24,52-66`), pour limiter l'énumération de
    comptes et la détection de l'état d'un compte ;
  - le code HTTP et le message sont identiques pour `INVALID_CREDENTIALS` et
    `ACCOUNT_LOCKED` (`api/routers/auth.py:104-111`), pour la même raison.

## Journal d'audit (`api/audit.py`, table `audit_events`)

Journal d'imputabilité en écriture seule (voir `qui_ecrit_quoi.md` pour le
détail des événements et l'écart constaté). Points d'accès :
- **Écriture** : uniquement par le code serveur (`record_event`), jamais
  directement par une route exposée à un rôle — aucun rôle ne peut écrire
  arbitrairement dans ce journal.
- **Lecture** : aucune route ne l'expose actuellement. Ni un Utilisateur ni
  un Admin ne peut consulter le journal d'audit via l'API au 2026-09-24 ;
  une éventuelle consultation nécessiterait un accès direct à la base ou un
  futur endpoint dédié.
- Garantie de contenu : `record_event` tronque `detail` à 200 caractères et
  le docstring du module interdit explicitement tout mot de passe, hachage,
  jeton de session ou contenu de conversation dans ce champ — mais rien
  dans le code ne le fait respecter mécaniquement (pas de filtre/validation
  sur le contenu de `detail`, seule la discipline des appelants actuels
  l'assure).

## Contrôle de propriété (`api/ownership.py`)

`get_owned_conversation_or_404(db, conversation_id, user_id)`
(`api/ownership.py:13-17`) est le point unique de vérification qu'une
conversation appartient bien à l'utilisateur courant (`conversation.user_id
== user_id`, sinon `404` — pas `403`, pour ne pas confirmer l'existence
d'une conversation appartenant à un autre compte). Utilisé par :
- `POST /chat/ask` (`api/routers/chat.py:104`) ;
- `GET /conversations/{id}` (`api/routers/conversations.py:33`) ;
- `DELETE /conversations/{id}` (`api/routers/conversations.py:50`).

`GET /conversations` filtre directement par `user_id` en base
(`api/routers/conversations.py:23`) plutôt que de passer par cette fonction,
puisqu'il n'y a pas d'identifiant de ressource unique à vérifier.

Aucune route ne permet à un Utilisateur d'accéder à une conversation, un
message ou un compte d'un autre utilisateur.

## Matrice rôles × tables

| Table | Anonyme | Utilisateur | Admin |
|---|---|---|---|
| `users` | Créer sa propre session (lecture indirecte via `authenticate_user`) | Lecture de son propre profil (`GET /auth/me`) uniquement | Création, lecture (liste complète), mise à jour (rôle, statut, email, mode DSI), reset de mot de passe — de **tout** compte |
| `sessions` | Création de sa session au login | Création (login), lecture/renouvellement implicite à chaque requête, révocation de sa propre session (logout) | Idem Utilisateur pour son propre compte, + révocation en masse des sessions de **tout** compte |
| `conversations` | — | CRUD complet, restreint à ses propres conversations | Idem Utilisateur (un Admin n'a pas de vue sur les conversations des autres comptes — pas de route d'administration des conversations) |
| `messages` | — | Création (via `/chat/ask`) et lecture, restreintes à ses propres conversations. Pas de modification ni de suppression individuelle | Idem Utilisateur |
| `usage_daily` | — | Aucun accès direct (pas de route `/me/usage-daily`) ; alimentée en écriture pour son propre compte à chaque question | Lecture de l'usage de **tout** compte (`GET /admin/users/{id}/usage-daily`, agrégats dans `GET /admin/users`) |
| `audit_events` *(modèle ORM, absente du fichier réel — cf. `schema.md`)* | — | Aucun accès (écriture système uniquement lors de login/logout/change-password) | Aucun accès en lecture par l'API (voir « Journal d'audit » ci-dessus) |

Il n'existe pas de rôle « technicien » ou « DSI » au sens d'une valeur de
`platform_role` distincte : ces deux profils métier correspondent au
booléen `can_use_dsi_mode` sur un compte `platform_role='user'` (ou
`'admin'`), comme détaillé plus haut.

## Accès au fichier sur le serveur

- `data/mispl.db` est un fichier SQLite unique sur le système de fichiers du
  serveur — aucun contrôle d'accès applicatif supplémentaire au niveau du
  fichier n'est implémenté dans ce dépôt (les permissions du système
  d'exploitation sur le répertoire `data/` ne sont pas gérées par le code).
  Toute personne ayant un accès shell/fichier au serveur d'hébergement peut
  lire ce fichier directement — hors du contrôle applicatif décrit ci-dessus.
- Le fichier n'est jamais versionné (`data/*.db`, `data/*.db-journal` dans
  `.gitignore`) et ne doit jamais être copié dans une branche ou un artefact
  destiné au dépôt public.
- Aucun chiffrement au repos du fichier SQLite n'est mis en œuvre par le
  code de ce dépôt (pas d'extension SQLCipher ni équivalent trouvée dans les
  dépendances).

## Rétention et purge

| Donnée | Mécanisme de purge | Durée | Référence |
|---|---|---|---|
| `sessions` (lignes expirées ou révoquées) | **Aucune purge automatique trouvée dans le code.** Les lignes restent en base indéfiniment après expiration/révocation (seul `expires_at`/`revoked_at` change de valeur) | — | `api/session_store.py` (pas de fonction de purge) |
| `users`, `conversations`, `messages`, `usage_daily` | Aucune purge automatique — désactivation (`is_active=False`) plutôt que suppression pour `users` ; suppression manuelle uniquement pour `conversations` (et en cascade `messages`) via `DELETE /conversations/{id}` | Indéfinie sauf action explicite de l'utilisateur/admin | `api/routers/conversations.py:46-53` |
| `audit_events` *(modèle ORM, absente du fichier réel)* | Aucune purge automatique trouvée dans le code | Indéfinie | `api/audit.py` (pas de fonction de purge) |
| Cache de réponses (`outputs/cache/`) | `purge_old_cache()`, appelée au démarrage de l'API (`lifespan`) | 24 h (`MISPL_CACHE_RETENTION_HOURS`) | `src/agent/mispl_agent.py:91-108`, `api/main.py:64` |
| Sessions RAG journalisées (`outputs/sessions/`) | `purge_old_sessions()`, appelée au démarrage de l'API | 30 jours (`MISPL_SESSION_RETENTION_DAYS`) | `src/agent/mispl_agent.py:63-82`, `api/main.py:63` |

La purge de `outputs/cache/` et `outputs/sessions/` ne s'exécute qu'au
démarrage du processus API (`lifespan`, une fois) — un processus qui tourne
plusieurs jours sans redémarrage accumule des fichiers au-delà des durées
indiquées jusqu'au prochain démarrage.

## Sauvegardes

**Aucun mécanisme de sauvegarde automatisée de `data/mispl.db` n'a été
trouvé dans ce dépôt** (pas de script, pas de tâche planifiée, pas de
configuration dans `start.ps1` ou le `Dockerfile`). Toute politique de
sauvegarde relève actuellement d'une procédure d'exploitation externe au
code (hors périmètre de ce document — à documenter par l'équipe
infrastructure/DSI si une telle procédure existe).

## Autres stockages persistants (hors `data/mispl.db`)

| Stockage | Chemin | Qui écrit | Quoi | Durée de vie |
|---|---|---|---|---|
| Cache question→réponse | `outputs/cache/*.json` | Système, dans `ask_mispl()` après chaque appel LLM réussi (`src/agent/mispl_agent.py`, fonction `_cache_set`, appelée en fin de `ask_mispl`) | Question, réponse générée, sources RAG, clé dérivée de `(CACHE_VERSION, RETRIEVAL_PIPELINE_VERSION, question, modèle, top_k, skills, mode d'accès, hash de l'historique)` | 24 h (`CACHE_RETENTION_HOURS`), purge au démarrage de l'API uniquement |
| Sessions RAG journalisées | `outputs/sessions/session_<horodatage>.json` | Système, dans `_save_session()` appelée depuis `ask_mispl()` si `save_session=True` (le cas pour `/chat/ask`, `api/routers/chat.py:157-163`) | Question, sources RAG utilisées, résultat du lint MISPL, mode d'accès, réponse complète — **peut contenir le contenu intégral d'une question/réponse**, y compris si celle-ci contenait une donnée sensible non détectée par le DLP | 30 jours (`SESSION_RETENTION_DAYS`), purge au démarrage de l'API uniquement |
| Index vectoriel ChromaDB | `docs/chunks/vectorstore/` | Script d'ingestion (`src/rag/ingest_knowledge_base.py`, via `src/rag/build_vectorstore.py`), exécuté manuellement par un développeur/opérateur — jamais par l'API en service | Embeddings des fiches de `rag_knowledge_base/` (base de connaissances MISPL/GLIMS, pas de donnée patient ni de compte) | Reconstruit à la demande ; non versionné (`docs/chunks/vectorstore/` dans `.gitignore`) |
| Index BM25 | `docs/chunks/bm25_corpus.json` | Même script d'ingestion | Corpus texte des mêmes fiches, pour la recherche lexicale | Reconstruit à la demande ; non versionné |
| Manifeste de la base de connaissances | `docs/chunks/manifest.json`, `docs/chunks/manifest_kb.json` | Même script d'ingestion | Métadonnées de découpage (nombre de fiches, blocs, fonctions reconnues) | Reconstruit à la demande ; non versionné |

Ces stockages ne contiennent jamais de donnée provenant de la table `users`
(pas d'email, pas de hash de mot de passe) — seuls `outputs/sessions/` et
`outputs/cache/` peuvent contenir le texte libre d'une question ou d'une
réponse, potentiellement porteur d'une donnée métier ou de santé si le
contrôle DLP en amont (`src/security/dlp.py`) ne l'a pas détectée.
