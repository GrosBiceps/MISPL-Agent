# Journal des bugs rencontrés et corrigés

Ce journal recense les bugs les plus significatifs identifiés dans
l'historique git (commits `fix:`) et le `CHANGELOG.md`. Il ne reprend pas
l'intégralité des 70+ commits `fix` du dépôt (voir `git log --grep=^fix`
pour la liste exhaustive), mais les corrections qui illustrent des classes de
bugs récurrentes ou des enseignements réutilisables pour la suite du projet.

## Agent et génération

### Auto-évaluation de certitude non fiable par le LLM

- **Date** : 2026-08-26.
- **Symptôme** : le LLM répondait « ✅ Certain » alors que tous les scores de
  retrieval associés étaient inférieurs à 0,17.
- **Cause** : la qualification du niveau de certitude reposait uniquement
  sur une consigne de prompt système, sans vérification mécanique du score
  réel.
- **Correctif** : garde-fou mécanique indépendant du LLM, appliqué en code
  après génération (`_enforce_weak_evidence_warning`,
  `src/agent/mispl_agent.py`). Voir ADR-0010.
- **Commit** : `b71ef02`.

### Fuite de scores de retrieval internes dans le texte visible

- **Date** : 2026-08-26, corrigé une deuxième fois le 2026-08-27.
- **Symptôme** : le LLM recopiait parfois le score interne de retrieval dans
  sa justification (« score de 1,00 dans le RAG »), une fuite
  d'implémentation non destinée à l'utilisateur.
- **Cause** : le contexte envoyé au LLM inclut `Score : 0.xxx` par document
  pour l'aider à calibrer sa certitude ; rien n'empêchait le LLM de le
  répéter tel quel.
- **Correctif** : nettoyage par expression régulière (`_strip_leaked_retrieval_scores`),
  appliqué hors des blocs de code pour ne jamais réécrire du code MISPL
  généré. Une première version cassait la syntaxe MISPL à point initial
  (`.Sample.Id` → `IF.Sample.Id`) et confondait score de retrieval avec un
  score clinique (Glasgow, APACHE) — corrigé en restreignant le motif à un
  nombre au format `0.xxx`/`1.xxx` et en excluant les blocs ``` ``` ```.
- **Commits** : `ed10de6`, `61c7989` (régression réintroduite puis
  re-corrigée lors d'une récupération de travail après reset de worktree).

### Répétition du chain-of-thought en anglais

- **Symptôme constaté dès la conception** : les modèles gratuits (notamment
  nemotron) laissent parfois fuiter leur raisonnement interne (« Okay, let me
  check... ») avant la réponse structurée attendue.
- **Correctif** : `_strip_chain_of_thought` (`src/agent/mispl_agent.py`)
  détecte les marqueurs de début de réponse structurée et coupe tout
  préambule ressemblant à un raisonnement, avec une liste de signatures
  anglaises et françaises typiques.
- **Fichier** : présent dès les premières versions du pipeline agent, entretenu au fil des versions.

### Retrait de l'en-tête `<TYPE> PROGRAM`, superflu en usage réel

- **Date** : 2026-09-24.
- **Symptôme** : le banc de test temps réel a révélé que la consigne de
  génération d'une ligne d'en-tête `<TYPE> PROGRAM` en tête de chaque bloc de
  code produisait un bruit systématique sans utilité pour le technicien.
- **Correctif** : retrait de la consigne, incrément de `CACHE_VERSION` à
  `v31`. Voir ADR-0012.
- **Commit** : `02b3225`.

## Mode d'accès Technicien (barrière anti-boucle)

### Contournement par fence générique sans tag `mispl`

- **Date** : 2026-08-27.
- **Symptôme** : une boucle `WHILE`/`REPEAT` placée dans un bloc de code
  fenêtré (```) sans le tag `mispl` et sans le mot `PROGRAM` échappait à la
  détection, car `extract_mispl_blocks` (linter) ne l'extrayait pas.
- **Cause** : la barrière du mode Technicien ne vérifiait que les blocs
  effectivement extraits par le linter, pas le texte hors de ces blocs.
- **Correctif** : `_contains_unfenced_loop` scanne aussi le texte hors des
  blocs déjà vérifiés, avec une détection de « saveur MISPL » à proximité
  pour ne pas bloquer à tort une prose ordinaire contenant le mot anglais
  « while ».
- **Commits** : `cc4d6dc`, `f73790c`.

### Faux positif sur une citation de source `.htm`

- **Date** : 2026-08-27.
- **Symptôme** : un refus légitime en mode Technicien, qui citait sa source
  en prose (`Source : function_string.htm`), était bloqué à tort par la
  détection de « saveur MISPL » (le motif générique `.MotMajuscule` matchait
  l'extension de fichier).
- **Correctif** : le motif d'accesseur `.Champ` est passé en sensible à la
  casse (`(?-i:\.[A-Z][A-Za-z0-9_]*\b)`), pour ne plus matcher une extension
  de fichier en minuscules.
- **Commit** : `9762d8c`.

### Mention en prose confondue avec une boucle réelle

- **Date** : 2026-09-24 (banc de test temps réel, cas ORD-001).
- **Symptôme** : une réponse valide contenant la phrase « Aucune boucle
  WHILE/REPEAT requise » était remplacée à tort par le refus mode DSI.
- **Cause** : le mot-clé de boucle était détecté sans distinguer une mention
  en prose d'une position d'instruction réelle.
- **Correctif** : distinction entre une structure de boucle complète
  (toujours bloquante, quelle que soit la position) et un mot-clé isolé en
  position d'instruction (début de ligne) avec saveur MISPL à proximité,
  seul cas désormais bloquant pour une mention isolée.
- **Commit** : `5951b46` (banc de test temps réel).

## Linter et autofix

### Faux positif « Programme sans RETURN » sur un commentaire contenant `//`

- **Date** : 2026-09-24.
- **Symptôme** : un commentaire bloc `/* ... // ... */` faisait déclencher à
  tort l'avertissement « Programme sans RETURN » du linter.
- **Cause** : absence d'un analyseur lexical unique distinguant chaînes,
  commentaires `/* */` et `//` dans le code source du linter.
- **Correctif** : introduction d'un analyseur lexical unique traitant
  correctement les trois contextes (chaînes, commentaires bloc, commentaires
  ligne).
- **Commit** : `5951b46`.

### Autofix qui réécrivait l'intérieur des commentaires et des chaînes

- **Date** : 2026-09-24.
- **Symptôme** : l'autofix `CascadeRequest→AddRequest` réécrivait à tort un
  commentaire de type « ANCIEN : CascadeRequest(...) » en « ANCIEN :
  AddRequest(...) », et la conversion `// → /* */` cassait une chaîne
  contenant `"http://..."`.
- **Correctif** : l'autofix, comme le linter, s'appuie désormais sur
  l'analyseur lexical unique pour ne jamais toucher l'intérieur d'un
  commentaire ou d'une chaîne ; la conversion `//` neutralise les séquences
  `*/` et `//` internes avant réécriture.
- **Commit** : `5951b46`.

## Sécurité — authentification et API

### Absence de limite de débit par adresse IP sur la connexion

- **Date** : 2026-08-17, renforcé le 2026-08-25.
- **Symptôme** : seul le compte ciblé était protégé par le verrouillage
  après échecs (5 essais/15 min) ; un attaquant pouvait tester de nombreux
  e-mails différents depuis la même IP sans être ralenti (*credential
  stuffing*), y compris en faisant tourner les e-mails testés.
- **Correctif** : limitation de connexion par IP en complément du
  verrouillage par compte (`c8135a5`), puis élargie pour capter la rotation
  d'e-mails depuis la même IP (`0a4c99c`).

### Situation de concurrence TOCTOU (Time-Of-Check-To-Time-Of-Use)

- **Date** : 2026-08-26.
- **Symptôme** : identifié lors d'un audit de sécurité API, parmi 5
  constats corrigés dans le même commit (limites de payload, TOCTOU, fuite
  et couverture incomplète du rate limiting).
- **Correctif** : voir `d800e98`. Le détail précis de la fenêtre de
  concurrence corrigée n'est pas repris ici (dépôt public) ; se référer au
  rapport d'audit de sécurité (`docs/securite/`, rédigé séparément) pour
  l'analyse complète.

### Course d'unicité d'e-mail non gérée proprement

- **Date** : 2026-08-25.
- **Symptôme** : la création simultanée de deux comptes avec le même e-mail
  pouvait lever une erreur de contrainte d'intégrité SQL brute plutôt qu'une
  réponse HTTP propre.
- **Correctif** : capture explicite de l'erreur d'intégrité et renvoi d'un
  409 Conflict propre.
- **Commit** : `15c0e0d`.

### Contournement de la limite de taille de corps de requête en `Transfer-Encoding: chunked`

- **Date** : 2026-08-26.
- **Symptôme** : la limite de taille de corps de requête (1 Mo), basée sur
  l'en-tête `Content-Length`, pouvait être contournée par un client envoyant
  le corps en transfert par blocs (`chunked`), où cet en-tête est absent.
- **Correctif** : bornage du flux reçu chunk par chunk, indépendamment de
  tout en-tête déclaré par le client (voir `api/main.py::limit_request_body_size`).
- **Commit** : `397714e`.

## DLP (protection contre les données patient)

### Nom + date de naissance non détectés sous forme longue ou réordonnée

- **Date** : 2026-08-25 et 2026-08-27.
- **Symptôme** : la détection de nom patient ne couvrait que les titres
  abrégés (« M », « Mr », « Mme », « Dr »), pas les formes longues
  (« Monsieur », « Madame », « Docteur ») ; et un mot intercalaire
  (« patiente née le ... ») entre le nom et la date déjouait la détection de
  la combinaison nom + date.
- **Correctif** : alternance explicite sur la casse du titre en formes
  courtes et longues ; tolérance d'un vocabulaire intercalaire restreint
  (« né(e) le ») entre nom et date, y compris quand le mot intercalaire suit
  le nom plutôt que de le précéder.
- **Commits** : `36e5bbe`, `5292173`.

### Faux positifs sur des paires d'acronymes techniques

- **Date** : 2026-08-25.
- **Symptôme** : le motif générique de détection de nom capitalisé
  matchait à tort des paires de mots techniques minuscules après un mot
  déclencheur (« patient », « Dr »...), en raison d'un `re.IGNORECASE`
  appliqué à toute l'expression plutôt qu'au seul titre.
- **Correctif** : `IGNORECASE` restreint au titre uniquement, la partie nom
  restant sensible à la casse (`[A-Z]`).
- **Commit** : `f74be81`.

### Double comptage d'une date de naissance dans l'escalade combinatoire

- **Symptôme** : une même date apparaissant à la fois dans le motif « né(e)
  le DD/MM/YYYY » et dans le motif générique « date DD/MM/YYYY » comptait
  deux fois dans l'escalade combinatoire (2 motifs identifiants ≥ blocage),
  bloquant à tort une simple question sans nom associé.
- **Correctif** : le motif « date de naissance nominative » est marqué
  `is_identifying=False`, le comptage restant porté par le seul motif de
  date générique.
- **Commit** : `36e5bbe`.

## RAG et retrieval

### Ré-application d'un tri sur des documents déjà ordonnés, à une échelle de score incompatible

- **Date** : 2026-08-25.
- **Symptôme** : des documents déjà ordonnés par le pipeline RRF +
  reranking étaient re-triés par un score d'une échelle différente,
  produisant un ordre final incohérent.
- **Correctif** : suppression du second tri, avec correction associée du
  placement du séparateur de contexte et de la marge de sur-récupération par
  catégorie.
- **Commit** : `86f9107`.

### Double enrichissement du texte BM25 pour des chunks déjà enrichis

- **Symptôme** : certains chunks de la base de connaissances, déjà enrichis
  de métadonnées pour BM25 au moment de l'ingestion, se voyaient
  ré-enrichis une seconde fois au moment du retrieval, faussant les
  fréquences de termes.
- **Correctif** : la décision d'enrichissement est extraite dans une
  fonction testable dédiée, invoquée une seule fois par chunk.
- **Commit** : `847b148` (et `86f9107` pour le constat initial).

## Propriété intellectuelle de la base de connaissances

### Reprise de l'expression du manuel éditeur GLIMS

- **Date** : audit du 2026-09-23, correctif du 2026-09-24.
- **Symptôme** : un audit de similarité a détecté 281 signalements ÉLEVÉ et
  153 signalements MOYEN de reprise littérale ou quasi littérale de
  l'expression du manuel GLIMS dans `rag_knowledge_base/`, notamment dans
  `math_functions.md` et `string_functions.md`.
- **Cause** : une partie de la base initiale (rédigée avant la mise en place
  du contrôle `check_ip_similarity.py`) reprenait de trop près des
  formulations et des exemples du manuel.
- **Correctif** : régénération de la base à partir de fiches de faits bruts,
  réécriture programmatique des fichiers `*_extended.md`/`*_missing.md` et de
  `complete_function_data.json`, remplacement des exemples repris par des
  exemples originaux. Contre-audit du 2026-09-23 : 0 signalement ÉLEVÉ/MOYEN.
  Voir ADR-0003.
- **Commit** : `584ac55`.

## Voir aussi

- `CHANGELOG.md` : journal des modifications notables par version.
- `docs/architecture/adr/` : décisions structurantes associées à plusieurs
  de ces corrections (modes d'accès, garde de faible évidence, base clean
  room, cache versionné).
- `docs/securite/` (rédigé séparément) : rapport d'audit de sécurité complet.
