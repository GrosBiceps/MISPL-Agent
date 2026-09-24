# ADR-0005 — Argon2id pour les mots de passe (comptes de la plateforme API)

## Statut

Accepté — décision confirmée avec le RSSI le 2026-09-24.

## Date

Implémentation initiale : 2026-08-14 (commit `e9a0a97`, `feat(api): hachage
Argon2id + génération de mot de passe temporaire`). Confirmation explicite de
conserver Argon2id (plutôt que de migrer vers bcrypt) : 2026-09-24, décision
utilisateur validée avec le RSSI (voir `docs/engineering/SUIVI_TRAVAUX.md`,
Lot A, et `docs/securite/`, rédigé séparément par le lot en charge de la
sécurité).

## Contexte

Les comptes de la plateforme API (`api/models.py::User`) stockent un
`password_hash`. Un audit de sécurité a demandé une validation explicite du
choix de l'algorithme de hachage avec le RSSI, en le comparant explicitement
à bcrypt, algorithme plus ancien et plus répandu.

## Décision

Conserver **Argon2id** (`argon2-cffi`, `api/security.py`) comme algorithme de
hachage des mots de passe, sans migration vers bcrypt. Argon2id est
l'algorithme recommandé en tête par l'OWASP *Password Storage Cheat Sheet*
pour les nouveaux systèmes : il est résistant aux attaques par circuits
dédiés (ASIC/FPGA) et par GPU grâce à son coût mémoire réglable, ce que
bcrypt (coût uniquement en temps CPU, mémoire fixe et faible) ne couvre pas.
`PasswordHasher()` d'`argon2-cffi` est utilisé avec ses paramètres par
défaut, revus périodiquement par la bibliothèque elle-même pour rester
alignés sur les recommandations de coût courantes.

Note de périmètre : ce choix concerne les comptes de la plateforme API
(`api/security.py`). Le mode DSI de l'interface Streamlit utilise un
mécanisme séparé et plus ancien, un mot de passe partagé haché en
PBKDF2-HMAC-SHA256 (`src/security/access_mode.py::hash_password`), documenté
dans l'ADR-0007.

## Alternatives étudiées

- **bcrypt** : très répandu, bien audité, mais sa résistance aux attaques par
  matériel dédié est inférieure à celle d'Argon2id à budget de calcul
  comparable, en raison de son empreinte mémoire fixe et faible. Le RSSI a
  validé qu'il n'apportait pas d'avantage justifiant une migration.
- **PBKDF2** : déjà utilisé ailleurs dans le projet pour le mot de passe DSI
  partagé (ADR-0007), mais moins résistant qu'Argon2id aux attaques
  matérielles pour un usage de mot de passe de compte individuel ; non
  retenu pour les comptes de la plateforme.
- **scrypt** : profil de résistance proche d'Argon2id, mais moins
  standardisé dans l'écosystème Python/FastAPI utilisé ici ; Argon2id est
  la recommandation OWASP de premier rang et dispose d'une bibliothèque
  Python mature (`argon2-cffi`).

## Conséquences

- Aucune migration de hachage n'est nécessaire : les comptes existants
  restent valides tels quels.
- Le hachage Argon2id garantit qu'un mot de passe ne peut pas être retrouvé
  en clair à partir de la base — seule une vérification par nouvel essai
  (`verify_password`) est possible.
- Le coût mémoire d'Argon2id (plus élevé que bcrypt à sécurité égale) est
  négligeable au volume de connexions du projet (un laboratoire, pas un
  service à trafic massif).
- Ce choix est indépendant du mécanisme historique de mot de passe DSI
  partagé de Streamlit (PBKDF2, ADR-0007), qui reste en place tant que sa
  migration n'est pas un chantier engagé.
