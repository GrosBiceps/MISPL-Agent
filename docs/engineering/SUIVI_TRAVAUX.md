# Suivi des travaux — sécurité, audit et documentation d'ingénierie

> Fichier de reprise : chaque lot coche ses cases au fur et à mesure et note
> l'état exact où il s'est arrêté. Pour reprendre, lire ce fichier puis
> relancer uniquement les cases non cochées.

Demande initiale (2026-09-24) : hachage des mots de passe validé avec le RSSI
(bcrypt), audit de sécurité complet (code + base de données), documentation
d'ingénierie complète (Sphinx possible), cartographie du dépôt, diagramme de cas
d'utilisation et diagramme d'activité, dates de chaque étape conservées.

## Lot A — Hachage des mots de passe
- [x] Décision (2026-09-24, utilisateur) : CONSERVER Argon2id (pas de bcrypt) ; garantir
      qu'aucun mot de passe ne puisse jamais être retrouvé ; argumentaire écrit pour le RSSI
- [x] Implémentation + migration transparente des hachages existants
- [x] Tests
- [x] Note de justification (docs/securite/)
État : 2026-09-24 — LOT A TERMINÉ. Code : src/security/password_hashing.py (Argon2id figé m=64Mio,t=3,p=4), api/security.py (politique), re-hachage transparent (api/auth.py), must_change_password + POST /auth/change-password (403 password_change_required), upgrade_schema() branché au démarrage (api/main.py) et dans scripts/create_admin.py, validé sur COPIE de data/mispl.db ; DSI Streamlit en Argon2id + compat PBKDF2 ; frontend /change-password. Note : docs/securite/NOTE_RSSI_HACHAGE_MOTS_DE_PASSE.md. pytest complet : 383 passed, 1 xfailed. Écarts C2 (upgrade_schema non branché, must_change_password non positionné) : traités (api/main.py:63, api/routers/admin.py:77 et :213). Rien à reprendre.

## Lot B — Audit de sécurité (code + base de données)
- [x] Audit code (API, agent, frontend, dépendances)
- [x] Audit base de données (schéma, données, droits, chiffrement, sauvegardes)
- [x] Rapport docs/securite/AUDIT_SECURITE_2026-09-24.md
- [x] Correctifs appliqués / à arbitrer
État : 2026-09-24 — LOT B TERMINÉ. Rapport : docs/securite/AUDIT_SECURITE_2026-09-24.md (2 CRITIQUE corrigés, 6 ÉLEVÉ dont 3 corrigés, 8 MOYEN dont 1 corrigé, 10 FAIBLE dont 8 corrigés). CHANGELOG.md mis à jour. data/mispl.db jamais modifié par ce lot (empreinte inchangée par pytest) ; NB : une table vide audit_events y a été créée vers 14:38 par un create_all extérieur, colonne must_change_password ajoutée au prochain démarrage de l'API. À arbitrer par l'utilisateur/RSSI/DPO : DSI/ suivi par git (E4, test xfail strict à retirer ensuite), Streamlit sans auth (E5), chiffrement BDD (E6/BDD-1), dépendances Python (M5), jetons de session en clair (M2), rétention/purge (M4), vérifier si une image Docker a été publiée (C2) → révoquer la clé OpenRouter le cas échéant. Rien à reprendre côté code.

## Arborescence cible (partagée entre les lots)
- docs/securite/ ............ lots A et B
- docs/specifications/ ...... lot C1 (besoins, cas d'utilisation, activité)
- docs/architecture/ ........ lot C1 (architecture, adr/, chronologie, journal des bugs)
- docs/guides/ .............. lot C1 (utilisateurs par rôle, développeur, exploitation)
- docs/base_de_donnees/ ..... lot C2 (schéma, qui écrit quoi, accès)
- docs/cartographie/ ........ lot C2 (carte du dépôt + carte interactive HTML)
- docs/sphinx/ .............. lot C1 (conf.py + index incluant tout ce qui précède)

## Lot C — Documentation d'ingénierie (C1 = specs/archi/guides/Sphinx, C2 = BDD/cartographie)
- [x] Spécifications (besoins, acteurs, cas d'utilisation, diagrammes d'activité)
- [x] Sphinx (docs/sphinx/) + build HTML
- [x] Architecture + ADR datés (historique git)
- [x] Base de données : schéma, qui écrit quoi, accès (lot C2, 2026-09-24)
- [x] Guides utilisateurs par rôle, guide développeur, exploitation
- [x] Journal des bugs rencontrés (historique git)
- [x] Cartographie du dépôt (schéma + carte interactive) (lot C2, 2026-09-24)
- [x] Diagramme de cas d'utilisation + diagramme d'activité
- [x] Chronologie datée du projet

### État C1 : terminé (2026-09-24)
Fait : `docs/specifications/` complet (cahier des charges, acteurs et rôles avec
matrice, cas d'utilisation avec diagramme Mermaid + 12 fiches, 2 diagrammes
d'activité). `docs/architecture/` complet : `architecture.md` (contexte,
conteneurs, composants, flux, déploiement, style C4 en Mermaid), 12 ADR
(`docs/architecture/adr/0001-...` à `0012-...`, format MADR, dates vérifiées
par `git log --follow`/`git log -S`), `chronologie.md` (reconstruite depuis
`git log --reverse`), `journal_bugs.md` (bugs significatifs depuis les
commits `fix:` et le CHANGELOG). `docs/guides/` complet (guide_technicien.md,
guide_dsi_administrateur.md, guide_developpeur.md, exploitation.md). Tout est
vérifié contre le code réel (`src/agent/mispl_agent.py`, `src/security/`,
`api/routers/`) et l'historique git — aucune date inventée.

`docs/sphinx/` complet : `conf.py` (myst-parser + sphinxcontrib-mermaid,
thème furo avec repli sphinx-rtd-theme, langue fr, conversion automatique des
fences ```mermaid en diagrammes rendus via `myst_fence_as_directive`),
`index.md` (toctree spécifications/architecture/ADR(glob)/guides, + toctree
par motif glob pour `base_de_donnees/`, `cartographie/` et `securite/` —
ces trois derniers rédigés par d'autres agents, non nommés explicitement),
`requirements-docs.txt`, `Makefile`, `make.bat`. `.gitignore` mis à jour
(`docs/sphinx/_build/`).

Point technique important pour un successeur : Sphinx ne découvre que les
documents SOUS son répertoire source (`docs/sphinx/`), jamais via `../` —
un premier essai avec des toctree `../specifications/...` échouait donc
entièrement (« nonexisting document » sur tout). Solution retenue : `conf.py`
recopie au début du build (avant la découverte des sources, donc dans l'en-tête
du module, pas dans une fonction `setup()`) `docs/specifications/`,
`docs/architecture/`, `docs/guides/`, `docs/base_de_donnees/`,
`docs/cartographie/` et `docs/securite/` vers des dossiers miroirs
`docs/sphinx/_src_<nom>/` (ignorés par Git). `index.md` référence ces
miroirs. Les mklink Windows ont été essayés d'abord et refusés
(droits administrateur requis) — d'où la copie. Un glob de toctree avec
extension explicite (`_src_cartographie/*.md`) ne matchait rien alors que
sans extension (`_src_cartographie/*`) fonctionne et ne prend que les `.md`
(les `.html`/`.py`/`.json` du dossier cartographie sont ignorés
automatiquement par le glob de toctree, qui ne retient que `source_suffix`) —
tous les globs du index.md utilisent donc la forme sans extension.

Build exécuté : dépendances installées dans `.venv` (sphinx, myst-parser,
sphinxcontrib-mermaid, furo, sphinx-rtd-theme — voir
`docs/sphinx/requirements-docs.txt`) ; `sphinx-build -b html docs/sphinx
docs/sphinx/_build/html` → **build succeeded, 1 warning** (le seul
avertissement restant est `toctree glob pattern '_src_securite/*' didn't
match any documents`, attendu tant que le lot A/B n'a pas encore écrit
`docs/securite/` — à revérifier une fois ce dossier peuplé, aucune action
prévue si le warning disparaît de lui-même). Diagrammes Mermaid vérifiés
rendus dans le HTML produit (pas de warning "Pygments lexer mermaid is not
known").

`README.md` : section « Documentation » ajoutée, renvoie vers
`docs/sphinx/index.md` et donne la commande de build.

Repère utile : premier commit git 2026-06-07 (`058c34c`), dernier commit
2026-09-24 (`02b3225`), 153 commits au total. Décision Argon2id déjà
implémentée le 2026-08-14 (commit `e9a0a97`), validée par l'utilisateur le
2026-09-24 (pas de migration bcrypt à documenter comme à venir).

**Lot C1 entièrement terminé.** Aucune action de reprise nécessaire côté C1.

### État C2 : terminé (2026-09-24)

Fichiers produits :
- `docs/base_de_donnees/schema.md` — diagramme ER Mermaid, colonnes/contraintes/
  index/sensibilité pour `users`, `sessions`, `conversations`, `messages`,
  `usage_daily`, et `audit_events` (modèle ORM). Comptages de lignes vérifiés
  en lecture seule sur `data/mispl.db` (aucune donnée de ligne citée nulle part).
- `docs/base_de_donnees/qui_ecrit_quoi.md` — matrice opération × déclencheur ×
  fichier/ligne × rôle pour chaque table, + 5 diagrammes de séquence Mermaid
  (création de compte, connexion, question avec historique, réinitialisation
  par un admin, changement de mot de passe par l'utilisateur).
- `docs/base_de_donnees/acces.md` — deux axes d'autorisation (`platform_role` /
  `can_use_dsi_mode`), authentification (Argon2id, paramètres RFC 9106,
  re-hachage transparent, politique de mot de passe, anti-bruteforce),
  contrôle de propriété (`api/ownership.py`), matrice rôles × tables, accès au
  fichier sur le serveur, rétention/purge, sauvegardes (aucune trouvée dans le
  code), et les autres stockages persistants (cache réponses, `outputs/sessions/`,
  index ChromaDB/BM25 de `docs/chunks/`).
- `docs/cartographie/cartographie.md` — arborescence commentée, diagramme
  d'architecture Mermaid, aperçu du graphe d'imports, dépendances externes
  (`requirements.txt`, `frontend/package.json`), points d'entrée.
- `docs/cartographie/generer_cartographie.py` — script reproductible (module
  `ast`, n'exécute jamais le code scanné) : génère `graphe_imports.json` et
  `carte_interactive.html`. Exécuté et vérifié : **60 modules, 93 imports
  internes**. Relancer après toute modification de `api/`, `src/`, `scripts/`
  ou `tools/` : `.venv\Scripts\python.exe docs\cartographie\generer_cartographie.py`
- `docs/cartographie/graphe_imports.json`, `docs/cartographie/carte_interactive.html`
  — sorties générées (fichier HTML autonome, vis-network via cdn.jsdelivr.net ;
  zoom/déplacement/recherche/infobulle vérifiés par relecture du code généré).

Point de vigilance transmis pour suite (hors périmètre C2, relève du lot A/B
en cours en parallèle) : `api/models.py` définit désormais
`users.must_change_password` et la table `audit_events`, mais le fichier réel
`data/mispl.db` inspecté ne les contient pas encore — le mécanisme de
migration `upgrade_schema()` (`api/db.py`) existe mais n'est appelé ni par
`api/main.py` ni par `scripts/create_admin.py` (tous deux appellent encore
`Base.metadata.create_all`, qui ne modifie jamais une table existante). Par
ailleurs, `POST /admin/users` et `POST /admin/users/{id}/reset-password`
génèrent un mot de passe temporaire mais ne positionnent jamais
`must_change_password=True` : le garde-fou existe côté modèle/dépendance
(`api/dependencies.py`) mais n'est pas déclenché en pratique. Les deux
constats sont documentés explicitement dans `docs/base_de_donnees/schema.md`
(section « Écart modèle ORM / fichier réel ») et `qui_ecrit_quoi.md`. Un
successeur qui reprendrait C2 n'a qu'à re-vérifier le schéma réel après
qu'`upgrade_schema()` aura été branché et exécuté, pour lever la mention
d'écart si elle n'est plus d'actualité — aucune autre action requise sur C2.
