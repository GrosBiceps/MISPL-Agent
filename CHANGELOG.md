# Journal des modifications

Ce fichier recense les changements notables du projet MISPL Agent. Les dates sont au format AAAA-MM-JJ.

## 2026-09-24

### Sécurité : hachage des mots de passe et audit (lots A et B)
- **Mots de passe (Argon2id conservé, décision du 2026-09-24)** :
  - paramètres figés dans `src/security/password_hashing.py` : m = 64 Mio, t = 3, p = 4, sel de 16 octets, empreinte de 32 octets (RFC 9106) ;
  - re-hachage transparent à la connexion quand les paramètres changent ;
  - politique de mot de passe : 12 caractères et 3 familles, ou phrase de passe de 16 caractères ;
  - le calcul Argon2 est aussi effectué pour un compte verrouillé, ce qui supprime un oracle temporel.
- **Mot de passe temporaire à changer** : colonne `users.must_change_password` (migration non destructive `upgrade_schema()` au démarrage). Nouvelle route `POST /auth/change-password` ; les autres routes renvoient `403 password_change_required` tant que le mot de passe n'a pas été changé. Nouvelle page frontend `/change-password`.
- **Mot de passe DSI (Streamlit)** : passage en Argon2id. L'ancien format PBKDF2 reste accepté, avec un avertissement invitant à relancer `scripts/set_dsi_password.py`.
- **Journal d'audit** : nouvelle table `audit_events` pour les connexions, échecs, verrouillages, changements et réinitialisations de mot de passe, et actions d'administration. Elle ne contient aucun secret.
- **Fuites** :
  - les erreurs 422 ne renvoient plus la valeur soumise ;
  - les réponses de l'API portent `Cache-Control: no-store` ;
  - Streamlit n'envoie plus la clé OpenRouter du serveur au navigateur.
- **Correctifs d'audit** :
  - Next.js 16.3.1 → 16.3.6 (RCE critique) et mise à jour de `sharp` ;
  - nouveau `.dockerignore` (l'image embarquait `.env`, la base, `DSI/` et le texte du manuel) ;
  - `MISPL_LLM_BASE_URL` limitée à OpenRouter, à la boucle locale ou aux hôtes listés dans `MISPL_LLM_ALLOWED_HOSTS` ;
  - CORS `*` refusé ;
  - `.gitignore` couvre les fichiers `-wal` et `-shm` de SQLite.
- Documents : `docs/securite/NOTE_RSSI_HACHAGE_MOTS_DE_PASSE.md` et `docs/securite/AUDIT_SECURITE_2026-09-24.md` (constats restant à arbitrer et plan d'actions).

### Base de connaissances : remédiation propriété intellectuelle
- `rag_knowledge_base/` a été régénérée à partir de fiches de faits bruts : signatures, paramètres, retours, comportements observables. Elle ne reprend plus l'expression du manuel éditeur GLIMS.
- `complete_function_data.json` et les fichiers `*_extended.md` / `*_missing.md` ont été réécrits par programme à partir de ces fiches.
- Les exemples repris de l'éditeur (notamment dans `math_functions.md` et `string_functions.md`) ont été remplacés par des exemples originaux.
- Contre-audit de similarité du 2026-09-23 : aucun risque ÉLEVÉ ni MOYEN (avant : 281 ÉLEVÉ et 153 MOYEN). `rag_knowledge_base/README.md` et `SOURCES.md` décrivent la méthode et l'audit.
- Le dossier d'audit `docs/audit_PI_*/` contient le texte du manuel. Il est exclu par `.gitignore` et n'est jamais versionné.

### Outils et évaluation
- Nouveau : `tools/check_ip_similarity.py` et `tools/ip_allowlist.json`. Ce contrôle anti-régression de propriété intellectuelle est à lancer avant chaque ajout ou modification de la base. Il combine :
  - la détection de reprises littérales par n-grammes ;
  - la similarité TF-IDF ;
  - en option, des embeddings e5 ;
  - la détection d'exemples d'appel identiques à ceux du manuel.
  
  Il sort avec le code 1 si un risque ÉLEVÉ ou MOYEN est détecté.
- `requirements.txt` : ajout des dépendances du contrôle PI, section optionnelle (`numpy`, `scikit-learn`, `beautifulsoup4`, `pypdf`).
- Index RAG reconstruit avec `python src/rag/build_vectorstore.py` : 38 fiches, 439 blocs, 301 fonctions reconnues. Les dossiers ChromaDB orphelins ont été purgés.
- Nouveau : `scripts/eval_retrieval_kb.py`, qui évalue le retrieval en deux volets :
  - exact-match sur toutes les fonctions connues : hit@1 = 1,000 sur 301 fonctions ;
  - 50 requêtes sémantiques : hit@1 = 0,600, hit@3 = 0,740, hit@5 = 0,800, MRR = 0,693 (index précédent : 0,560 / 0,720 / 0,740 / 0,662).
- Suite de tests : 270 tests passés.

### Sécurité et robustesse (correctifs récents intégrés à `main`)
- **Agent** :
  - défense anti-extraction du prompt système, dont la formulation inversée a été corrigée ;
  - garde-fou mécanique de certitude, indépendant de l'auto-évaluation du LLM, avec une regex ancrée en début de ligne ;
  - suppression des scores de retrieval qui fuitent dans les réponses, y compris dans le garde-fou « preuves faibles » ;
  - correction du repli entre modèles sur les erreurs 429 ;
  - retrait de faux positifs du linter ;
  - ajout d'une mention légale ;
  - correction de la corruption des blocs de code et de faux positifs sur les scores cliniques.
- **Modes d'accès** :
  - blocage des boucles `WHILE`/`REPEAT` hors bloc de code en mode Technicien ;
  - fermeture de la faille des blocs de code génériques (sans langage déclaré).
- **DLP** :
  - fermeture du contournement nom + date de naissance (titres écrits en toutes lettres, mots intercalaires) ;
  - détection des noms au format « liste de travail » sans titre ;
  - réduction des faux positifs sur les paires d'acronymes techniques ;
  - suppression du double comptage des dates de naissance ;
  - motif « MISPL » restreint pour ne plus capturer les citations de sources.
- **API** :
  - limites de taille de charge utile, y compris en `Transfer-Encoding: chunked` ;
  - correction d'une situation de concurrence TOCTOU ;
  - correction de la fuite et de la couverture incomplète du rate limiting ;
  - limite de connexion par IP contre le *credential stuffing* ;
  - conflit d'unicité d'e-mail renvoyé proprement en 409 ;
  - longueur de `question` et de `lab_context` bornée ;
  - en-têtes HTTP de durcissement (CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`) sur l'API et le frontend.
- **Frontend** :
  - piège de focus clavier dans les modales d'administration ;
  - fuite d'état entre utilisateurs corrigée ;
  - redirection sur 401 ;
  - accessibilité (ARIA, graphiques de consommation utilisables au clavier) ;
  - normalisation des erreurs Pydantic.
- **RAG** :
  - reranking cross-encoder des candidats issus de la RRF, avec fusion du rang reranké et du rang RRF ;
  - pool de candidats garanti pour les catégories des skills actifs ;
  - version du pipeline de retrieval incluse dans la clé de cache ;
  - corrections de l'enrichissement BM25 et du tri des documents.

### Agent / banc de test
Correctifs issus du banc « temps réel » (`scripts/claude_harness/`) : 122 prompts réels, avec des subagents Claude dans le rôle du LLM. `CACHE_VERSION` passe de `v29` à `v30`.
- **Barrière du mode Technicien** (`src/security/access_mode.py`) :
  - une simple mention en prose des mots-clés de boucle (« Aucune boucle WHILE/REPEAT requise ») ne remplace plus une réponse valide par le refus (ORD-001) ;
  - une boucle hors bloc de code reste bloquée si elle est structurée (`WHILE ... DO` ou `DONE`, `REPEAT ... UNTIL`, quelle que soit la longueur du corps) ou si le mot-clé est en position d'instruction avec une saveur MISPL à proximité.
- **Consigne du mode Technicien** :
  - le mode ne bride que les boucles ;
  - chercher d'abord une fonction intégrée qui rend la boucle inutile ;
  - sinon, refus au format `## Contexte GLIMS` sans bloc de code ;
  - ne jamais écrire les mots-clés de boucle, même dans les commentaires ou les notes (TEC-002).
- **Linter et autofix** (`src/agent/linter.py`) : un analyseur lexical unique traite les chaînes, les commentaires `/* */` et les `//`.
  - Linter : plus de faux « Programme sans RETURN » quand un `//` figure dans un commentaire bloc (PFI-002). Un appel écrit dans une chaîne n'est plus signalé (PIJ-005), ni un appel cité en commentaire (PCR-003). Les numéros de ligne sont conservés.
  - Autofix : il ne réécrit plus l'intérieur des commentaires, où « ANCIEN : CascadeRequest(...) » devenait « ANCIEN : AddRequest(...) » (PCR-002), ni les chaînes (`"http://..."` était cassé). La conversion `//` → `/* */` neutralise les `*/` et `//` internes.
- **Bandeau « Documentation faible détectée »** : il est omis pour les refus sans code (mode Technicien, extraction du prompt, cas impossible) et pour les réponses qui commencent déjà par « ⚠️ Fonction non trouvée ». La rétrogradation de « ✅ Certain » s'applique toujours.
- **Prompt système, règles et skills** :
  - une fonction nommée dans la question mais absente de la documentation n'est jamais appelée, même en pseudo-code. L'exemple de `.claude/rules/anti-hallucination.md` faisait précisément l'inverse (PFI-001) ;
  - commentaires uniquement au format `/* */` : les exemples du prompt et des skills utilisaient `//` ;
  - sources au format `rag_knowledge_base/...md` au lieu des anciens `.htm` ;
  - gabarit unique `## Contexte GLIMS` pour les refus et les cas impossibles ;
  - titres de sortie de `mispl-core` alignés sur le format obligatoire.
- **API** : préchargement du RAG (retriever, embeddings, BM25, cross-encoder) au démarrage, par `api.main.warm_up_rag()`. Il évite les 43 s de la première question. On peut le désactiver avec `MISPL_PRELOAD_RETRIEVER=false`, et un échec ne bloque jamais le démarrage.
- **Banc** :
  - `e2e.py` tue l'arbre de processus (lanceur venv et interpréteur enfant sous Windows) et attend la libération réelle des ports ;
  - il compare les réponses à `report.json` après l'envoi, avec un message clair si le rapport est absent ou périmé, et une option `--wait-report` ;
  - `dump_json` écrit de façon atomique ;
  - l'évaluateur ne compte plus comme boucle générée un mot-clé cité en commentaire ou en prose, applique les mêmes exemptions de bandeau et signale les sources `.htm` ou vagues.
- **Tests** : 25 tests ajoutés (11 linter/autofix, 5 barrière Technicien, 6 bandeau, 3 préchargement) ; suite complète : 299 tests passés.
