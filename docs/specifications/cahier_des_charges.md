# Cahier des charges

## Contexte

Le laboratoire de biologie médicale utilise le SIL (système d'information de
laboratoire) **GLIMS**, édité par Clinisys/MIPS. GLIMS embarque un langage de
script propriétaire, **MISPL**, utilisé pour écrire des règles de calcul, des
validations automatiques, des comptes-rendus, des déclenchements d'analyses et
des navigations dans le modèle de données (ERD) du SIL.

MISPL est peu documenté publiquement, syntaxiquement proche d'un dialecte
Progress ABL / OpenEdge, et sa mauvaise maîtrise peut avoir des conséquences
directes sur la production de résultats de biologie médicale (boucle infinie
côté serveur, mauvaise validation, effacement d'un log obligatoire...). Les
techniciens de laboratoire qui écrivent ou modifient des scripts MISPL n'ont
généralement pas de formation de développeur, et la documentation éditeur
n'est accessible qu'au travers du manuel GLIMS (propriété de l'éditeur, non
redistribuable).

MISPL Agent est un assistant conversationnel (RAG + LLM) qui répond en
français aux questions des techniciens et de la DSI sur MISPL, en s'appuyant
sur une base de connaissances interne rédigée spécifiquement pour ce projet,
et qui cite systématiquement ses sources.

## Objectifs

1. **Réduire le risque d'erreur** dans l'écriture de scripts MISPL en
   fournissant des réponses sourcées, avec un niveau de certitude explicite,
   plutôt que des réponses génériques d'un LLM généraliste qui pourrait
   halluciner des fonctions inexistantes.
2. **Adapter la réponse au rôle** : un technicien de laboratoire ne doit pas
   se voir proposer de code utilisant des boucles (risque de boucle infinie
   côté serveur GLIMS partagé), alors que la DSI, qui valide et déploie les
   scripts, doit pouvoir obtenir du code complet.
3. **Offrir deux interfaces** : une interface historique mono-poste
   (Streamlit) et une plateforme multi-utilisateurs (API FastAPI + frontend
   Next.js) avec comptes, historique de conversations et suivi d'usage,
   pour couvrir aussi bien l'usage individuel que le déploiement en service.
4. **Protéger les données patient** : aucune information susceptible
   d'identifier un patient ne doit être transmise au LLM (hébergé par un
   tiers, OpenRouter).
5. **Respecter la propriété intellectuelle de l'éditeur GLIMS** : la base de
   connaissances ne doit contenir aucune reprise de l'expression du manuel
   éditeur, tout en documentant fidèlement les fonctions MISPL utiles.

## Périmètre

### Inclus

- Agent question/réponse sur la syntaxe et les fonctions MISPL, avec citation
  de sources et niveau de certitude.
- Génération de code MISPL adaptée à deux modes d'accès (Technicien / DSI).
- Retrieval hybride (BM25 + dense + reranking) sur une base de connaissances
  Markdown propre au projet (`rag_knowledge_base/`).
- Deux interfaces : Streamlit (mono-poste) et API FastAPI + frontend Next.js
  (multi-utilisateurs, avec comptes et historique).
- Protections applicatives : DLP (détection de données patient), limitation
  de débit, verrouillage anti-bruteforce, en-têtes de sécurité HTTP.
- Outillage de contrôle qualité : suite de tests, évaluation du retrieval,
  contrôle anti-régression de propriété intellectuelle, banc de test avec LLM
  substitué (`scripts/claude_harness/`).

### Exclus

- L'agent ne se connecte jamais directement à un serveur GLIMS et ne modifie
  aucune configuration ou donnée de production : il ne fait que proposer du
  code MISPL que la DSI relit et déploie elle-même.
- L'agent ne stocke ni ne traite de données patient réelles : le DLP vise à
  bloquer leur saisie avant tout envoi au LLM, mais l'usage prévu reste des
  questions génériques sur la syntaxe et les fonctions, jamais des extraits de
  dossiers patients.
- Pas de génération automatique de configuration GLIMS (référentiel
  d'analyses, bornes, création de patients) : ces opérations, hors du langage
  MISPL, sont explicitement signalées comme impossibles par l'agent.
- Pas d'hébergement du LLM en interne : le projet s'appuie sur des modèles
  gratuits tiers via OpenRouter (voir l'ADR correspondante pour la
  justification et les limites de ce choix).

## Exigences fonctionnelles

- **EF-01** — L'utilisateur peut poser une question en français sur MISPL et
  obtenir une réponse structurée (contexte, code, source, niveau de
  certitude, notes techniques).
- **EF-02** — Toute fonction MISPL citée dans une réponse doit être sourcée
  vers un fichier et une section de `rag_knowledge_base/`.
- **EF-03** — Si une fonction demandée n'existe pas dans la base, l'agent le
  signale explicitement et propose du pseudo-code plutôt que d'inventer une
  fonction.
- **EF-04** — En mode Technicien, l'agent ne génère jamais de boucle
  `WHILE`/`REPEAT` ; en mode DSI, la génération est complète.
- **EF-05** — L'utilisateur peut consulter l'historique de ses conversations
  et le supprimer (plateforme API/Next.js).
- **EF-06** — Un administrateur peut créer, modifier, désactiver un compte,
  réinitialiser un mot de passe, révoquer les sessions actives d'un compte,
  et consulter la consommation de jetons par utilisateur et par période.
- **EF-07** — La base de connaissances peut être reconstruite en index de
  recherche (BM25 + vectoriel) à la demande, après toute modification.
- **EF-08** — Un contrôle de similarité avec le manuel éditeur peut être
  exécuté avant tout ajout ou modification de la base de connaissances.
- **EF-09** — La fiabilité du retrieval (capacité à retrouver la bonne
  documentation) peut être mesurée par un script d'évaluation (exact-match et
  requêtes sémantiques).

## Exigences non fonctionnelles

### Sécurité

- Mots de passe hachés avec **Argon2id** (voir
  `docs/architecture/adr/0005-argon2id-mots-de-passe.md`), jamais en clair,
  jamais réversibles.
- Sessions par cookie `HttpOnly`, attribut `Secure` par défaut en production,
  durée de vie bornée (8 h).
- Verrouillage de compte après 5 échecs de connexion consécutifs (15 min), et
  limitation des tentatives par adresse IP pour limiter le *credential
  stuffing*.
- Filtrage DLP de toute question, contexte labo et historique envoyés au LLM,
  avec blocage des motifs à haut risque (identifiants patient) et escalade en
  blocage d'une combinaison de motifs individuellement non bloquants (par
  exemple un nom et une date).
- Limitation de débit sur `/chat/ask` (20 requêtes/minute/utilisateur) et sur
  les tentatives de connexion.
- Taille de corps de requête bornée (1 Mo), y compris en transfert par blocs
  (`Transfer-Encoding: chunked`), pour éviter la saturation mémoire/CPU.
- En-têtes de durcissement HTTP (`Content-Security-Policy`,
  `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`) sur l'API et
  le frontend.
- CORS restreint aux origines explicitement autorisées
  (`MISPL_FRONTEND_ORIGIN`).
- Isolation stricte entre comptes : un utilisateur ne peut consulter ou
  supprimer que ses propres conversations.

### Disponibilité et résilience

- Repli automatique entre plusieurs modèles LLM gratuits en cas de limite de
  débit ou d'indisponibilité (`FALLBACK_ORDER`), avec un budget de temps total
  borné pour ne jamais bloquer un worker indéfiniment.
- Cache réponse de 24 h (question → réponse), versionné, pour réduire la
  dépendance au LLM tiers et le temps de réponse perçu sur les questions
  répétées.
- Préchargement du pipeline RAG au démarrage de l'API pour éviter un premier
  temps de réponse dégradé.

### Performance

- Le retrieval doit rester pertinent : la référence d'évaluation du
  2026-09-24 est hit@1 = 1,000 en exact-match (301 fonctions) et hit@1 =
  0,600 / MRR = 0,693 sur 50 requêtes sémantiques. Toute modification du
  retrieval ne doit pas dégrader ces chiffres sans justification écrite.
- Le code MISPL généré doit privilégier les fonctions intégrées du serveur
  GLIMS aux boucles manuelles, pour limiter la charge sur le serveur GLIMS
  partagé entre tous les laboratoires du site.

### Conformité santé et propriété intellectuelle

- Aucune donnée patient réelle n'est un intrant attendu du système ; le DLP
  est un filet de sécurité, pas une autorisation à saisir des données
  patient.
- La base de connaissances ne doit contenir aucune reprise de l'expression du
  manuel éditeur GLIMS (propriété intellectuelle de Clinisys/MIPS) : voir
  `docs/architecture/adr/0003-base-connaissances-clean-room.md` et
  `rag_knowledge_base/SOURCES.md`.
- Le dépôt de code étant public, aucun secret, aucune donnée interne du CHU,
  aucun extrait du manuel GLIMS ne doit y être versionné (voir
  `CLAUDE.md`, section « Dépôt public »).

### Maintenabilité

- Toute modification du prompt système, du post-traitement de réponse ou des
  garde-fous de sortie doit incrémenter `CACHE_VERSION`
  (`src/agent/mispl_agent.py`) pour éviter de servir des réponses obsolètes
  depuis le cache.
- Toute modification de l'expansion de requête, du boost de catégorie ou du
  modèle de reranking doit incrémenter `RETRIEVAL_PIPELINE_VERSION`
  (`src/rag/retriever.py`).
- La suite de tests (pytest) et le script d'évaluation du retrieval doivent
  être exécutés avant toute fusion de modification touchant l'agent, le RAG
  ou la sécurité.

## Contraintes

- Le dépôt GitHub est **public** : `DSI/`, `docs/audit_PI_*/`, `.env`,
  `data/*.db` et tout extrait du manuel GLIMS sont exclus par `.gitignore` et
  ne doivent jamais être versionnés.
- L'environnement d'exécution cible est Windows (PowerShell), avec un
  déploiement possible en conteneur (`Dockerfile`, type Hugging Face Space
  pour l'interface Streamlit).
- Les modèles LLM utilisés sont des modèles gratuits mis à disposition par
  OpenRouter : leur disponibilité, leurs limites de débit et leur qualité de
  réponse ne sont pas garanties par le projet (voir
  `docs/architecture/adr/0002-openrouter-modeles-gratuits-fallback.md`).
- HTTPS est obligatoire en production (le cookie de session porte l'attribut
  `Secure` par défaut) ; en développement local HTTP,
  `MISPL_COOKIE_SECURE=false` doit être positionné explicitement.

## Glossaire

| Terme | Définition |
|---|---|
| **MISPL** | Langage de script propriétaire du SIL GLIMS, dialecte proche de Progress ABL/OpenEdge, utilisé pour les règles de calcul, validations, comptes-rendus et navigation dans le modèle de données. |
| **GLIMS** | Système d'information de laboratoire (SIL) édité par Clinisys/MIPS. |
| **SIL** | Système d'Information de Laboratoire. |
| **RAG** | *Retrieval-Augmented Generation* : technique consistant à fournir au LLM des extraits de documentation pertinents avant de lui demander de répondre, pour réduire le risque d'hallucination. |
| **LLM** | *Large Language Model*, modèle de langage utilisé pour générer la réponse en langage naturel et le code MISPL. |
| **DLP** | *Data Loss Prevention* : filtrage visant à empêcher l'envoi de données sensibles (ici, potentiellement identifiantes pour un patient) vers un tiers (le LLM). |
| **ERD** | *Entity-Relationship Diagram* : modèle de données de GLIMS (tables Order, Result, Patient, Specimen...), que MISPL permet de parcourir. |
| **RRF** | *Reciprocal Rank Fusion* : méthode de fusion de deux classements (ici BM25 et recherche vectorielle dense) en un classement unique. |
| **Reranking** | Réordonnancement d'un ensemble de candidats par un modèle spécialisé (cross-encoder) après une première étape de retrieval, pour affiner la pertinence. |
| **Mode Technicien** | Mode de génération par défaut : ne génère jamais de boucle `WHILE`/`REPEAT`, pour limiter le risque de boucle infinie côté serveur GLIMS. |
| **Mode DSI** | Mode de génération complet, réservé aux comptes disposant du droit `can_use_dsi_mode`. |
| **Clean room (salle blanche)** | Méthode de documentation consistant à ne retenir que des faits techniques observables (signature, comportement) et à les rédiger avec ses propres mots, sans reprendre l'expression d'une source protégée. |
| **Argon2id** | Fonction de hachage de mot de passe résistante aux attaques GPU/ASIC, recommandée par l'OWASP. |
| **Cache versionné** | Cache disque question → réponse (24 h), dont la clé inclut des numéros de version (`CACHE_VERSION`, `RETRIEVAL_PIPELINE_VERSION`) qui s'incrémentent à chaque changement de comportement, pour éviter de servir une réponse calculée avec un ancien comportement. |
