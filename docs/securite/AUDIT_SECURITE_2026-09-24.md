# Audit de sécurité de MISPL Agent : code et base de données

- Date : 2026-09-24
- Périmètre : dépôt `MISPL-Agent` (branche `main`), poste de développement, fichier `data/mispl.db`.
- Réalisé par un agent de développement (lots A et B du fichier `docs/engineering/SUIVI_TRAVAUX.md`). Cet audit ne remplace ni un test d'intrusion ni un audit de configuration de l'infrastructure de production.
- Document public (le dépôt GitHub l'est) : il ne contient **aucun secret, aucune empreinte de mot de passe ni aucune donnée personnelle**. Les constats sur la base ne donnent que des comptages et des formats.

Document associé : `docs/securite/NOTE_RSSI_HACHAGE_MOTS_DE_PASSE.md` (argumentaire Argon2id pour le RSSI).

---

## 1. Méthodologie

1. **Revue de code manuelle** de `api/` (routes, dépendances, sessions, modèles), `src/security/`, `src/agent/mispl_agent.py` (appel LLM, cache, journalisation des sessions), `app.py` (Streamlit), `frontend/` (Next.js), `Dockerfile`, `.gitignore`, `.env.example`, `scripts/`.
2. **Recherches ciblées** : mots de passe dans les journaux et les exceptions, `dangerouslySetInnerHTML`, `unsafe_allow_html`, `localStorage`, SQL brut, variables d'environnement sensibles.
3. **Base de données** : inspection de `data/mispl.db` en **lecture seule** (`sqlite3`, URI `?mode=ro`). Schéma, index, contraintes, comptages, format des empreintes sans les afficher, passage du filtre DLP sur les textes saisis (comptages seulement). L'empreinte SHA-256 du fichier a été contrôlée avant et après chaque étape de cet audit.
4. **Dépendances** : `pip-audit` 2.10.1 sur l'environnement `.venv` ; `npm audit --omit=dev` dans `frontend/`.
5. **Historique git public** : `git log --all -p` sur 153 commits, balayé par un script de motifs (clés OpenRouter, OpenAI, GitHub, Hugging Face, AWS, Slack, clés privées, empreintes Argon2, empreintes et sels DSI, adresses IP privées). Le script ne consigne que le type de motif, le fichier et le nombre de commits, jamais la valeur. Fichiers sensibles ajoutés un jour à l'index : recherche par nom.
6. **Tests** : chaque correctif est couvert par un test unitaire ou d'intégration (voir § 7).

Échelle de gravité : **CRITIQUE** (exploitation directe, impact majeur) ; **ÉLEVÉ** (impact fort ou exigence de conformité non tenue) ; **MOYEN** (exploitation conditionnelle ou défense en profondeur manquante) ; **FAIBLE** (durcissement) ; **INFO** (bonne pratique constatée ou contexte).

Statut : **CORRIGÉ** (dans ce lot, avec des tests), **À ARBITRER** (décision de l'utilisateur, du RSSI ou du DPO requise, ou correctif non sûr dans ce lot).

## 2. Périmètre

| Composant | Inclus | Remarque |
|---|---|---|
| API FastAPI (`api/`) | Oui | Authentification, sessions, administration, chat, conversations. |
| Agent et RAG (`src/agent/`, `src/rag/`) | Partiel | Appel LLM, cache, journalisation, injection de prompt. Pas de revue de la qualité du retrieval. |
| Sécurité (`src/security/`) | Oui | Modes d'accès, DLP. |
| Interface Streamlit (`app.py`) | Oui | Toujours lancée par `start.ps1` et par le `Dockerfile`. |
| Frontend Next.js (`frontend/`) | Oui | XSS, stockage, en-têtes, dépendances. |
| Base `data/mispl.db` | Oui, en lecture seule | Voir § 4. |
| Infrastructure de production (TLS, proxy, sauvegardes, supervision) | Non | Inconnue du dépôt : points à vérifier par la DSI (§ 5). |

## 3. Constats

Synthèse :

| Gravité | Nombre | Corrigés | À arbitrer |
|---|---|---|---|
| CRITIQUE | 2 | 2 | 0 (une vérification reste à faire pour C2) |
| ÉLEVÉ | 6 | 3 | 3 |
| MOYEN | 8 | 1 | 7 |
| FAIBLE | 10 | 8 | 2 |
| INFO | 9 | — | — |

### 3.1 CRITIQUE

#### C1. Next.js 16.3.1 : exécution de code à distance sans authentification (CORRIGÉ)
- **Où** : `frontend/package.json:11` (`"next": "16.3.1"`).
- **Preuve** : `npm audit --omit=dev` signalait, pour `next` de 16.0.0 à 16.3.2, deux avis de gravité critique : GHSA-p293-qw3h-jr36 (exécution de code à distance non authentifiée **sur un serveur hébergé sous Windows**, qui est la plateforme du projet) et GHSA-2xp9-vwfh-vxw4 (exécution de code à distance via l'API d'optimisation d'images avec des fichiers AVIF). Il signalait aussi `sharp` < 0.35.4 (élevé, dépendance transitive de `libheif`).
- **Impact** : prise de contrôle du serveur frontend, puis accès au réseau interne.
- **Correctif** : `next` épinglé en **16.3.6**, `npm audit fix` pour `sharp`. `npm audit --omit=dev` renvoie désormais **0 vulnérabilité**. `npx tsc --noEmit` passe sans erreur.
- **Recommandation** : lancer `npm audit --omit=dev` à chaque mise à jour (en intégration continue, idéalement).

#### C2. Image Docker construite avec `.env`, la base, les notes DSI et le texte du manuel (CORRIGÉ, vérification à faire)
- **Où** : `Dockerfile:31` (`COPY --chown=user:user . .`), sans aucun `.dockerignore`. Le commentaire de `Dockerfile:16` indique que l'image est destinée à Hugging Face.
- **Preuve** : sans `.dockerignore`, tout le répertoire de travail entre dans l'image : `.env` (clé OpenRouter), `data/mispl.db` (comptes, empreintes, jetons de session, conversations), `DSI/` (notes internes et juridiques), `docs/audit_PI_*` (texte intégral du manuel GLIMS, propriété de l'éditeur), `outputs/sessions/` (questions et réponses).
- **Impact** : publier l'image, ou un Space public construit depuis le poste, suffit à divulguer la clé API, la base et un contenu protégé par le droit d'auteur.
- **Correctif** : ajout de `.dockerignore`, qui exclut ces chemins et conserve `.claude/skills` et `.claude/rules`, lus par le prompt système. Test : `tests/security/test_repo_hygiene.py::TestDockerignore`.
- **À vérifier par l'utilisateur** : une image a-t-elle déjà été construite et poussée (Hugging Face ou registre) depuis ce poste ? Si oui, **révoquer et régénérer la clé OpenRouter**, supprimer l'image et les Spaces concernés, et traiter la question du manuel avec l'avocat PI.

### 3.2 ÉLEVÉ

#### E1. Mot de passe temporaire définitif : aucun changement possible ni imposé (CORRIGÉ)
- **Où** : `api/routers/admin.py` (création, réinitialisation), `api/routers/auth.py` (aucune route de changement).
- **Preuve** : l'administrateur recevait le mot de passe en clair à la création et à la réinitialisation, et aucune route ne permettait à l'utilisateur de le changer. L'administrateur connaissait donc indéfiniment le mot de passe de chaque compte.
- **Impact** : aucune imputabilité (un administrateur peut agir sous l'identité d'un technicien), ce qui est contraire à la recommandation CNIL 2022-100 sur les mots de passe temporaires.
- **Correctif** : colonne `users.must_change_password`, positionnée à la création (`api/routers/admin.py:77`) et à la réinitialisation (`api/routers/admin.py:213`). Route `POST /auth/change-password` (`api/routers/auth.py:150`), qui exige le mot de passe actuel, applique la politique, révoque les autres sessions et compte un échec pour le verrouillage. Garde `get_current_user` (`api/dependencies.py`) qui renvoie `403 password_change_required` tant que le mot de passe n'a pas été changé. Page frontend `/change-password` et redirections depuis la connexion, `/chat` et `/admin`. Migration non destructive `upgrade_schema()` (`api/db.py`), appelée au démarrage de l'API (`api/main.py:63`) et par `scripts/create_admin.py`, et validée sur une **copie** de `data/mispl.db`. Tests : `tests/api/test_password_lifecycle.py::TestForcedPasswordChange`, `::TestSchemaUpgrade`.

#### E2. Clé OpenRouter du serveur envoyée au navigateur par Streamlit (CORRIGÉ)
- **Où** : `app.py`, champ « Cle API OpenRouter » (ancienne version : `value=st.session_state.api_key`, pré-rempli depuis `.env`).
- **Preuve** : la valeur d'un `st.text_input` est transmise au navigateur, même avec `type="password"` (seul l'affichage est masqué). Tout visiteur de l'interface, qui n'a pas d'authentification, pouvait lire la clé du serveur dans le DOM ou le flux WebSocket.
- **Impact** : vol de la clé API, consommation à nos frais, usurpation.
- **Correctif** : le champ démarre vide (`app.py:339`) et sert seulement à saisir une clé personnelle. À défaut, la clé du serveur est utilisée côté serveur (`src/security/openrouter_key.py`). Tests : `tests/security/test_repo_hygiene.py::TestStreamlitApiKeyNotSentToBrowser`.
- **Recommandation** : si l'interface Streamlit a été exposée hors du poste, régénérer la clé OpenRouter.

#### E3. Aucune traçabilité des accès (CORRIGÉ en partie)
- **Où** : il n'existait aucun journal des connexions, échecs, verrouillages ou actions d'administration. Seuls `users.last_login_at` et `sessions` subsistaient.
- **Impact** : l'imputabilité, exigée en santé (PGSSI-S, ISO 27001 pour HDS), n'était pas assurée.
- **Correctif** : table `audit_events` (`api/models.py`), écrite par `api/audit.py` pour les événements `login_success`, `login_failure`, `account_locked`, `logout`, `password_changed`, `password_change_failed`, `password_rehashed`, `admin_user_created`, `admin_user_updated`, `admin_password_reset` et `admin_sessions_revoked`. Chaque événement porte l'auteur, la cible et l'adresse IP. Le journal ne contient **ni mot de passe, ni empreinte, ni jeton, ni contenu de conversation**, ce que vérifie `tests/api/test_password_lifecycle.py::TestNoPasswordLeak::test_audit_trail_records_events_without_secrets`.
- **À arbitrer** : durée de conservation du journal (les recommandations CNIL sur la journalisation évoquent 6 mois à 1 an, à confirmer), export vers le SIEM de l'établissement, protection contre la modification (la table est modifiable par quiconque peut écrire dans la base), et consultation par un administrateur (aucune route de lecture n'existe à ce jour).

#### E4. Notes internes `DSI/` versionnées et publiées sur le dépôt public (À ARBITRER)
- **Où** : deux fichiers de `DSI/` (dossier d'architecture technique et de sécurité) sont suivis par git depuis le commit `33a94c3` (2026-06-30) et présents sur `origin/main`, alors que `CLAUDE.md` et `.gitignore` interdisent ce dossier. `.gitignore` n'a aucun effet sur un fichier déjà suivi.
- **Preuve** : `git ls-files DSI` liste les deux fichiers. Aucun secret, aucune adresse IP ni aucun chemin réseau n'y a été détecté par motif. Leur contenu n'est pas cité ici.
- **Impact** : divulgation publique de l'architecture de sécurité et du raisonnement interne. Ce n'est pas conforme à la politique du dépôt.
- **Recommandation** : `git rm --cached DSI/Architecture_Technique_Securite_MISPL_Agent*.md`, puis commit. Décider ensuite s'il faut purger l'historique (`git filter-repo`, puis `git push --force`), en sachant que les clones et forks existants gardent une copie. Ce correctif n'a **pas** été appliqué, car la consigne interdit de commiter et qu'une réécriture d'historique relève de l'utilisateur. Test témoin : `tests/security/test_repo_hygiene.py::TestGitTrackedFiles::test_dsi_notes_not_tracked`, marqué `xfail(strict=True)`. Il passera une fois les fichiers retirés de l'index, et il faudra alors enlever le marqueur.

#### E5. Interface Streamlit sans authentification, exposée par le Dockerfile (À ARBITRER)
- **Où** : `Dockerfile:35` (`--server.address=0.0.0.0`, port 7860), `app.py` (aucun compte).
- **Preuve** : tout visiteur peut poser des questions en consommant la clé du serveur. Le mode DSI repose sur un mot de passe **partagé** (`app.py:321`), sans limite de tentatives propre à l'interface, et les échanges ne sont pas imputables.
- **Impact** : pas d'imputabilité, consommation de la clé, tentatives illimitées sur le mot de passe DSI (freinées seulement par le coût Argon2id, environ 86 ms par essai).
- **Correctifs partiels déjà faits** : mot de passe DSI passé en Argon2id avec compatibilité PBKDF2 et avertissement (`src/security/access_mode.py`, `scripts/set_dsi_password.py`), clé API non exposée (E2).
- **Recommandation** : ne pas exposer Streamlit hors du poste ou d'un réseau de confiance. À terme, le retirer au profit de l'API et du frontend Next.js, qui ont des comptes. Sinon, le placer derrière un proxy authentifiant (SSO de l'établissement).

#### E6. Base de données non chiffrée au repos, pour des contenus potentiellement sensibles (À ARBITRER)
- Détail au § 4 (constats BDD-1 à BDD-3). Recommandation : chiffrement du volume (BitLocker ou LUKS) au minimum, ou SQLCipher.

### 3.3 MOYEN

#### M1. Destination du LLM modifiable sans contrôle (`MISPL_LLM_BASE_URL`) (CORRIGÉ)
- **Où** : `src/agent/mispl_agent.py` (surcharge de l'URL de base, lue sans validation).
- **Impact** : une valeur erronée ou malveillante envoie chaque question, le contexte labo, l'historique **et la clé API** vers un serveur tiers.
- **Correctif** : `src/security/llm_endpoint.py::validate_llm_base_url`, appelé à la création du client (`src/agent/mispl_agent.py:453`) et bloquant en cas de refus (aucun repli silencieux). Sont acceptés : OpenRouter en HTTPS, la boucle locale (banc de test, LLM local), et tout autre hôte **en HTTPS et listé dans `MISPL_LLM_ALLOWED_HOSTS`**. Les identifiants dans l'URL sont refusés. Tests : `tests/security/test_repo_hygiene.py::TestLlmEndpoint`, `tests/agent/test_llm_base_url_override.py::test_client_refuses_unlisted_third_party_host`.
- **À cadrer par le RSSI** : quels hôtes d'inférence interne autoriser. Un basculement vers un LLM local supprime le transfert vers OpenRouter (voir § 5).

#### M2. Jetons de session stockés en clair (À ARBITRER)
- **Où** : `api/models.py:48` (`sessions.token`, clé primaire), `api/session_store.py:26`.
- **Impact** : quiconque lit la base (sauvegarde, copie) peut reprendre une session active, pendant 8 heures glissantes au plus.
- **Recommandation** : ne stocker que le SHA-256 du jeton (le cookie garde le jeton brut). Cela demande une migration qui invalide les sessions en cours. Le changement est sûr, mais il touche au schéma que le lot C2 documente : à planifier.

#### M3. Limitation du débit en mémoire, fondée sur l'IP vue par l'application (À ARBITRER)
- **Où** : `api/routers/auth.py:49` et `:99` (`request.client.host`).
- **Impact** : derrière un proxy inverse, tous les utilisateurs partagent la même IP, et 30 échecs en 5 minutes bloquent la connexion de tout le monde (déni de service). Avec plusieurs processus (workers), chaque processus a ses propres compteurs, et un redémarrage les remet à zéro.
- **Recommandation** : un seul worker, ou des compteurs partagés (en base). Derrière un proxy, activer `--proxy-headers` et `--forwarded-allow-ips` d'uvicorn en limitant les proxys de confiance. Le verrouillage par compte, lui, est persistant en base.

#### M4. Conservation des données sans purge (À ARBITRER, DPO)
- Conversations et messages en base conservés **indéfiniment** (seul l'utilisateur peut les supprimer). Sessions expirées ou révoquées jamais purgées. Voir BDD-4.
- `outputs/sessions/*.json` : question et réponse en clair, **sans identifiant d'utilisateur**, conservées 30 jours (`MISPL_SESSION_RETENTION_DAYS`). La purge n'a lieu qu'au démarrage de l'API ou de Streamlit (`api/main.py:66`, `app.py:63`). Les fichiers sont nommés à la seconde près (`src/agent/mispl_agent.py:716`) : deux échanges simultanés s'écrasent.
- **Recommandation** : fixer avec le DPO une durée de conservation par catégorie (conversations, journal d'audit, sessions), puis mettre en place une purge périodique, et pas seulement au démarrage.

#### M5. Dépendances Python avec des vulnérabilités connues (À ARBITRER)
- **Preuve** : `pip-audit` sur `.venv` (2026-09-24) : 67 identifiants distincts. `nltk` 3.9.4 : 30 (traversée de chemin, SSRF du téléchargeur, lecteurs de corpus ; correctif en 3.10.3). `gitpython` 3.1.50 : 24 (dépendance de Streamlit ; correctif en 3.1.60). `chromadb` 1.5.9 : 4 (injection de code **en mode serveur HTTP** ; pas de version corrigée listée). `aiohttp` 3.14.1 : 3. `anyio` 4.14.1 : 3 (correctif en 4.14.2). `torch` 2.12.1 : 1. `pip` et `setuptools` : 1 chacun.
- **Exploitabilité dans l'usage actuel** : faible. ChromaDB est utilisé en mode embarqué (`PersistentClient`), pas en serveur. NLTK ne sert qu'au stemming (le téléchargeur et les lecteurs de corpus ne sont pas exposés aux utilisateurs). GitPython n'est pas appelé par le code du projet.
- **Recommandation** : mettre à jour rapidement `anyio`, `aiohttp`, `pip` et `setuptools` (correctifs mineurs). Mettre à jour `nltk` puis relancer `scripts/eval_retrieval_kb.py`, car le stemming alimente BM25 et les chiffres de référence de `CLAUDE.md` doivent être tenus. Surveiller `chromadb`. Ces mises à jour n'ont pas été faites dans ce lot : elles peuvent modifier le retrieval.

#### M6. CSP du frontend avec `'unsafe-inline'` en `script-src` (À ARBITRER)
- **Où** : `frontend/next.config.ts:16`.
- **Impact** : si une injection HTML apparaissait un jour, le CSP ne bloquerait pas le script. Aucun vecteur n'a été trouvé à ce jour (voir I5).
- **Recommandation** : CSP avec nonce (middleware Next.js), à valider avec la documentation de Next.js 16 (`frontend/AGENTS.md`).

#### M7. TLS et HSTS non gérés par l'application (À ARBITRER, déploiement)
- `MISPL_COOKIE_SECURE=false` (`api/routers/auth.py:35`) désactive le drapeau `Secure` du cookie, et aucun en-tête `Strict-Transport-Security` n'est émis.
- **Recommandation** : terminer le TLS sur le proxy inverse, y ajouter HSTS, et interdire `MISPL_COOKIE_SECURE=false` hors développement.

#### M8. Aucun second facteur d'authentification (À ARBITRER, RSSI)
- À évaluer au regard de la PGSSI-S, au moins pour les comptes administrateurs (voir la note RSSI, § 8).

### 3.4 FAIBLE

| # | Constat | Où | Statut |
|---|---|---|---|
| F1 | Les erreurs 422 renvoyaient la valeur soumise (champ `input`), par exemple un mot de passe trop long. | `api/main.py:79` | CORRIGÉ : gestionnaire qui retire `input`, `ctx` et `url`. Test `TestNoPasswordLeak`. |
| F2 | Pas de `Cache-Control` sur les réponses de l'API, dont celles qui portent un mot de passe temporaire. | `api/main.py:147` | CORRIGÉ : `no-store` partout. |
| F3 | Chemin « compte verrouillé » sans calcul Argon2 : sa latence révélait l'existence et l'état du compte. | `api/auth.py:63` | CORRIGÉ : calcul factice. Test `test_locked_account_still_pays_argon2_cost`. |
| F4 | `verify_password` n'interceptait pas `VerificationError` en général (erreur 500 possible). | `src/security/password_hashing.py` | CORRIGÉ. |
| F5 | `MISPL_FRONTEND_ORIGIN="*"` était accepté : avec `allow_credentials=True`, Starlette renvoie alors l'origine appelante. | `api/main.py:153` | CORRIGÉ : « * » refusé. `SameSite=Strict` limitait déjà l'impact. |
| F6 | Mot de passe DSI en PBKDF2-SHA256 à 200 000 itérations, sous les 600 000 recommandées par l'OWASP. | `src/security/access_mode.py` | CORRIGÉ : Argon2id, ancien format accepté avec avertissement. |
| F7 | Politique minimale de 8 caractères pour le premier compte administrateur ; aucune politique ailleurs. | `api/admin_bootstrap.py` | CORRIGÉ : politique commune `api/security.py::password_policy_errors`. |
| F8 | `.gitignore` ne couvrait pas les fichiers `-wal` et `-shm` de SQLite. | `.gitignore` | CORRIGÉ. |
| F9 | Le filtre DLP ne détecte pas les secrets (mots de passe, clés) collés dans une question. Ils seraient conservés en base et dans `outputs/sessions/`, et envoyés au LLM. | `src/security/dlp.py` | À ARBITRER : ajouter des motifs de clés (`sk-…`) et un avertissement. |
| F10 | Image Docker très large (git, git-lfs, ffmpeg, cmake) et base `python:3.11-slim` non épinglée par empreinte. L'utilisateur n'est pas root (bon point). | `Dockerfile:1-14` | À ARBITRER : image multi-étapes, empreinte épinglée. |

### 3.5 INFO (bonnes pratiques constatées)

- **I1** : les empreintes de mots de passe de la base réelle sont conformes : le seul compte a une empreinte `argon2id`, `v=19`, `m=65536,t=3,p=4`, sel de 16 octets, empreinte de 32 octets.
- **I2** : pas d'injection SQL. Tout passe par l'ORM SQLAlchemy ou des requêtes paramétrées. Le seul SQL composé (`api/db.py:69`, migration) n'utilise que des constantes du code.
- **I3** : isolation entre comptes. `api/ownership.py::get_owned_conversation_or_404` renvoie 404 (et non 403) pour la conversation d'un autre compte. L'historique envoyé au LLM est relu en base, pas pris dans la requête du client (`api/routers/chat.py:110`). Les routes `/admin` sont protégées par `require_admin`. Le dernier administrateur actif ne peut être ni désactivé ni rétrogradé.
- **I4** : sessions. Jeton de 256 bits (`secrets.token_urlsafe(32)`), nouveau jeton à chaque connexion (pas de fixation), cookie `HttpOnly`, `Secure` par défaut, `SameSite=Strict`, durée glissante de 8 h, révocation côté serveur (déconnexion, réinitialisation, désactivation vérifiée à chaque requête).
- **I5** : frontend. `react-markdown` est utilisé sans `rehype-raw` (pas de HTML brut) et il n'y a aucun `dangerouslySetInnerHTML`. `localStorage` ne sert qu'au thème et à l'état de la barre latérale. Le mot de passe temporaire ne vit que dans l'état React de la page d'administration. Streamlit échappe les messages des utilisateurs (`html.escape`) avant tout `unsafe_allow_html`.
- **I6** : historique git. Aucun secret réel trouvé dans les 153 commits. Une seule détection, un faux positif : une clé factice volontaire dans le banc de test `scripts/claude_harness/e2e.py`. Seuls `.env.example` et `frontend/.env.local.example` ont été versionnés, et ils ne contiennent aucune valeur.
- **I7** : limites de taille. Corps de requête limité à 1 Mo, y compris en transfert par morceaux (`api/main.py`). Longueurs Pydantic bornées (question à 8 000 caractères, historique à 50 messages, mot de passe à 256).
- **I8** : injection de prompt. Consigne anti-extraction dans le prompt système (`src/agent/prompt_builder.py:17`). Barrière post-génération du mode Technicien (`enforce_access_mode`). Le code généré n'est jamais exécuté par l'application. Risque résiduel : le LLM peut être manipulé pour produire un contenu hors sujet, sans accès à d'autres données que celles de la conversation et de la base de connaissances (publique).
- **I9** : en-têtes de l'API. `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy` et CSP `default-src 'none'` sont en place, hors pages `/docs`.

## 4. Base de données

- **SGBD** : SQLite 3.49 (module `sqlite3` de Python), fichier `data/mispl.db` (`api/db.py:14`), accès par SQLAlchemy 2.0. `PRAGMA foreign_keys=ON` et `busy_timeout=5000` sont appliqués à chaque connexion de l'application (`api/db.py:25`).
- **État** : `PRAGMA quick_check` = ok, `journal_mode=delete`, `secure_delete=0`, `auto_vacuum=0`, `user_version=0` (pas de versionnement de schéma).

### 4.1 Schéma, index, contraintes

| Table | Lignes (2026-09-24) | Contraintes et index | Colonnes sensibles |
|---|---|---|---|
| `users` | 1 | PK `id` ; index unique `email` ; `CHECK platform_role IN ('admin','user')` | `email` (donnée personnelle), `password_hash` (Argon2id), `display_name` |
| `sessions` | 12 (toutes expirées ; 11 non révoquées) | PK `token` ; FK `user_id` | `token` **en clair** (M2) |
| `conversations` | 12 | PK ; FK `user_id` ; index `user_id` | `title` (début de la question) |
| `messages` | 34 (17 utilisateur, 17 assistant) | PK ; FK ; index `conversation_id` ; `CHECK role` | `content` (texte libre saisi) |
| `usage_daily` | 4 | PK ; `UNIQUE(user_id, date)` ; FK | — |
| `audit_events` | 0 | PK ; index `created_at`, `event` ; pas de FK (l'historique survit à la suppression d'un compte) | `source_ip` |

Absences relevées : pas d'`ON DELETE CASCADE` au niveau SQL (la cascade est gérée par l'ORM) ; pas de contrainte `CHECK` sur la longueur de l'email ; aucun versionnement de schéma (`user_version`). La migration `upgrade_schema()` ajoute les colonnes manquantes sans rien détruire.

**Écart constaté pendant l'audit** : l'empreinte SHA-256 du fichier a changé vers 14 h 38 (heure locale) le 2026-09-24. Une table `audit_events` vide y a été créée par un `create_all` extérieur à ce lot (la suite de tests, elle, ne modifie pas le fichier : empreinte identique avant et après son exécution complète). La colonne `users.must_change_password` n'existe pas encore dans le fichier réel. Elle sera ajoutée par `upgrade_schema()` au prochain démarrage de l'API, comme validé sur une copie (ajout de la colonne, valeur 0 pour le compte existant, second appel sans effet). **Aucune modification de `data/mispl.db` n'a été faite par ce lot.**

### 4.2 Constats sur la base

- **BDD-1 (ÉLEVÉ, À ARBITRER) : pas de chiffrement au repos.** SQLite stocke tout en clair. Quiconque copie le fichier (poste, sauvegarde, image Docker avant C2) lit les emails, les conversations et les jetons de session. **Recommandation** : au minimum, chiffrer le volume (BitLocker sur le poste Windows, LUKS ou équivalent sur le serveur) ; si le fichier doit circuler (sauvegardes externalisées), passer à **SQLCipher** (`sqlcipher3` avec le dialecte SQLAlchemy correspondant, clé fournie par un coffre de secrets et non par `.env`). Les empreintes Argon2id restent, elles, inexploitables sans attaque par dictionnaire.
- **BDD-2 (MOYEN) : données personnelles et risque de données de santé.** Les emails et noms affichés des comptes sont des données personnelles. Les messages sont du texte libre : un technicien peut y coller par erreur un identifiant patient. Le filtre DLP (`src/security/dlp.py`) bloque les motifs identifiants (NIR, IPP/NIP, NISS) avant tout envoi et tout enregistrement : une question bloquée n'est jamais persistée (`api/routers/chat.py:147`). Il laisse passer, en avertissement, des signaux faibles isolés (date, nom). Passé sur les 29 textes stockés (messages utilisateur et titres), le DLP donne **0 blocage et 0 alerte**. Le filtre reste heuristique : un nom seul ou un identifiant de format inconnu peut passer.
- **BDD-3 (MOYEN) : droits sur le fichier.** Sur le poste, les ACL NTFS sont héritées du profil utilisateur (SYSTEM, Administrateurs, utilisateur). C'est convenable sur un poste mono-utilisateur. Sur un serveur, restreindre au seul compte de service de l'API (mode 600 sous Linux) et exclure le fichier des partages.
- **BDD-4 (MOYEN) : conservation et purge.** Aucune purge des conversations ni des sessions expirées (voir M4). Le cache de réponses (`outputs/cache/`, 24 h, `MISPL_CACHE_RETENTION_HOURS`) ne contient que des réponses, pas les questions. Les sessions journalisées (`outputs/sessions/`, 30 jours) contiennent les questions.
- **BDD-5 (MOYEN, À ARBITRER) : sauvegardes.** Rien dans le dépôt ne sauvegarde ni ne restaure `data/mispl.db`. **Recommandation** : sauvegarde à chaud par l'API de sauvegarde SQLite (`sqlite3 … ".backup"`, cohérente même pendant l'écriture), chiffrée, avec une rétention définie par le DPO et un test de restauration périodique.
- **BDD-6 (corrigé en partie, voir E3) : traçabilité.** La table `audit_events` assure désormais l'imputabilité des accès et des actions d'administration. La lecture des conversations par leur propriétaire n'est pas journalisée (choix de minimisation, à confirmer).

## 5. Conformité RGPD et HDS : points à vérifier par le DPO et le RSSI

Ces points relèvent d'une analyse juridique que cet audit ne remplace pas.

1. **Registre des traitements (RGPD, art. 30)** : inscrire l'outil (finalité : assistance à l'écriture de scripts MISPL ; données : identifiants professionnels, questions, journal d'audit).
2. **Transfert vers OpenRouter** : chaque question non bloquée par le DLP, avec son historique, part vers un service tiers (OpenRouter, puis le fournisseur du modèle, potentiellement hors de l'UE). À qualifier : sous-traitance (RGPD, art. 28), transferts hors UE (chapitre V), et clauses et conditions d'utilisation des modèles gratuits (réutilisation des requêtes). Une alternative souveraine existe : un LLM local (le cadrage de `MISPL_LLM_BASE_URL`, M1, l'autorise en boucle locale ou sur un hôte interne listé).
3. **Données de santé** : l'outil n'est pas conçu pour en traiter, et le DLP bloque les identifiants patient. Si le DPO estime que le risque résiduel n'est pas négligeable, l'hébergement de la base et des journaux par un tiers relèverait de l'obligation HDS (CSP, art. L.1111-8). Une AIPD (RGPD, art. 35) peut être requise, notamment en raison de l'usage d'un LLM tiers.
4. **Durées de conservation** (RGPD, art. 5-1-e) : conversations, `outputs/sessions/`, journal d'audit, comptes inactifs (voir M4 et BDD-4).
5. **Sécurité (RGPD, art. 32)** : chiffrement au repos (BDD-1), sauvegardes (BDD-5), gestion des secrets (clé OpenRouter dans `.env` : préférer un coffre), second facteur (M8).
6. **Information des utilisateurs** (RGPD, art. 13) : mention sur la page de connexion (finalité, conservation, transfert vers le LLM, journalisation).
7. **PGSSI-S** : niveau d'authentification attendu et raccordement éventuel au SSO de l'établissement.
8. **Propriété intellectuelle** : C2 (image Docker) et E4 (notes `DSI/`) sont à examiner avec l'avocat PI si une image ou un Space a été publié.

## 6. Plan d'actions

| Priorité | Action | Qui | Statut |
|---|---|---|---|
| 1 | Vérifier si une image Docker ou un Space a été publié. Si oui : révoquer la clé OpenRouter, supprimer l'image (C2). | Utilisateur | À faire |
| 1 | Si Streamlit a été exposé hors du poste : régénérer la clé OpenRouter (E2). | Utilisateur | À faire |
| 1 | Retirer `DSI/` de l'index git, commiter, décider d'une purge de l'historique (E4). Retirer ensuite le marqueur `xfail` du test témoin. | Utilisateur | À arbitrer |
| 1 | Déployer : redémarrer l'API pour appliquer `upgrade_schema()` (colonne `must_change_password`). Relancer `scripts/set_dsi_password.py` si le mot de passe DSI est encore en PBKDF2. | Utilisateur ou DSI | À faire |
| 2 | Chiffrer le volume, ou passer la base en SQLCipher (BDD-1) ; mettre en place des sauvegardes chiffrées et testées (BDD-5). | DSI et RSSI | À arbitrer |
| 2 | Ne plus exposer Streamlit, ou le placer derrière un SSO (E5). | DSI | À arbitrer |
| 2 | Durées de conservation et purge périodique (M4, BDD-4) ; rétention et export du journal d'audit (E3). | DPO, puis développement | À arbitrer |
| 2 | Qualification RGPD du transfert vers OpenRouter, AIPD, registre (§ 5). | DPO | À arbitrer |
| 3 | Mises à jour des dépendances Python, avec évaluation du retrieval après `nltk` (M5). | Développement | À arbitrer |
| 3 | Empreinte SHA-256 des jetons de session (M2) ; limitation du débit derrière un proxy (M3). | Développement | À arbitrer |
| 3 | CSP avec nonce (M6), HSTS et TLS (M7), second facteur pour les administrateurs (M8). | Développement et RSSI | À arbitrer |
| 4 | Motifs de secrets dans le DLP (F9) ; image Docker minimale et épinglée (F10). | Développement | À arbitrer |

## 7. Correctifs appliqués et preuves

Fichiers modifiés ou créés par ce lot :

- `src/security/password_hashing.py` (nouveau), `api/security.py`, `api/auth.py`, `api/audit.py` (nouveau), `api/models.py`, `api/db.py`, `api/dependencies.py`, `api/schemas.py`, `api/session_store.py`, `api/admin_bootstrap.py`, `api/main.py`, `api/routers/auth.py`, `api/routers/admin.py` ;
- `src/security/access_mode.py`, `src/security/llm_endpoint.py` (nouveau), `src/security/openrouter_key.py` (nouveau), `src/agent/mispl_agent.py`, `app.py` ;
- `scripts/set_dsi_password.py`, `scripts/create_admin.py`, `scripts/claude_harness/e2e.py` (changement du mot de passe temporaire dans le scénario de bout en bout) ;
- `frontend/package.json`, `frontend/package-lock.json`, `frontend/lib/api.ts`, `frontend/app/login/page.tsx`, `frontend/app/chat/page.tsx`, `frontend/app/admin/page.tsx`, `frontend/app/change-password/page.tsx` (nouveau) ;
- `.dockerignore` (nouveau), `.gitignore`, `.env.example` (variables documentées sans valeur) ;
- tests : `tests/api/test_password_lifecycle.py` (nouveau), `tests/security/test_repo_hygiene.py` (nouveau), `tests/security/test_access_mode.py`, `tests/api/test_admin_bootstrap.py` (seuil 12 au lieu de 8), `tests/agent/test_llm_base_url_override.py`.

Vérifications :

- `pytest` complet (`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`, 2026-09-24) : **383 réussis, 1 `xfail` volontaire (E4), 0 échec**. Référence avant ce lot : 323 réussis.
- `npm audit --omit=dev` : 0 vulnérabilité. `npx tsc --noEmit` : aucune erreur. `npm run build` (Next.js 16.3.6) : réussi, avec la route `/change-password`.
- Migration validée sur une copie de `data/mispl.db`. Empreinte du fichier réel inchangée par la suite de tests.

Limites de l'audit : pas de test dynamique (DAST) ni de test d'intrusion ; pas d'accès à l'infrastructure de production ; `pip-audit` et `npm audit` ne couvrent que les vulnérabilités publiées ; le balayage de l'historique git repose sur des motifs, et un secret de format inhabituel pourrait lui échapper.
