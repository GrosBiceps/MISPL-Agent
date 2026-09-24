# Chronologie du projet

Chronologie reconstruite à partir de l'historique git (`git log --format='%ad
%h %s' --date=short`, premier commit 2026-06-07, 153 commits au
2026-09-24) et de `CHANGELOG.md`. Les dates sont celles des commits
(`%ad`, date d'auteur) ; un même jour peut regrouper plusieurs étapes
distinctes menées à la suite.

## 2026-06-07 — Fondations : agent v2 et base de connaissances clean room

- Premier commit du dépôt : `058c34c`, `feat: MISPL Agent v2 — base de
  connaissances manuelle (Clean Room)`. Mise en place du retrieval hybride
  BM25 + dense ChromaDB + RRF, de la base de connaissances rédigée en
  méthode clean room (voir ADR-0003), du cache réponse et de l'interface
  Streamlit.
- `5d4d27a`, `fix: restaurer tous les fixes v2 écrasés par rebase`.
- `92da0c5`, `chore: retirer dossiers documentation interne (audit, archi,
  faisabilité, présentation)` — première trace de la vigilance sur le
  caractère public du dépôt.
- `40b9e41`, `fix: reproductibilité — CreatePatient bloqué + RelatedResult
  forcé + cas impossible` — première règle de refus explicite pour les
  opérations hors périmètre MISPL (création de patient).

## 2026-06-15 — Audit du retrieval

- `db7269f`, `fix(rag): audit retrieval — fonctions courtes, expansion,
  synonymes, contamination`. Premier affinage du pipeline de retrieval après
  constat de faiblesses (voir ADR-0001).

## 2026-06-30 — Documentation interne

- `33a94c3`, `docs(dsi): dossier architecture technique & sécurité MISPL
  Agent` (documentation interne, non publique — `DSI/`).

## 2026-07-02 — Monitoring des ressources

- `e9e5c1b`, `feat(monitor): relevé ressources machine + rapport Plotly
  HTML` — ajout de `src/utils/resource_monitor.py`.
- `24eaa27`, `fix(app): retire @st.cache_resource du moniteur ressources
  (TokenError)`.

## 2026-08-14 — Authentification, plateforme API/Next.js, modes d'accès (77 commits)

Journée la plus dense du projet : mise en place de la plateforme
multi-utilisateurs complète.

- Spécifications et plan d'implémentation (`80afee3`, `57d8641`) pour
  l'authentification et les comptes.
- Modèles ORM, hachage Argon2id (`e9a0a97`, voir ADR-0005), sessions
  révocables, verrouillage anti-bruteforce, routes `/auth/*` et
  `/admin/*` (`02754e5` à `7e0ecbc`).
- Modes d'accès Technicien/DSI (`a0050d6`, `71611ea`, voir ADR-0007) et DLP
  (première version, intégrée au même chantier).
- Scaffold du frontend Next.js (`b3e387a`), page de connexion, page de chat,
  route `/chat/ask` côté API (`4104278`, `b621bf4`, `4784cb6`) — voir
  ADR-0006.
- Correctifs de revue finale sur l'authentification (`97eca9a`, 6 constats :
  bootstrap, casse de l'e-mail, attaque temporelle, révocation).
- Polish UI, landing page, thèmes visuels, historique de conversations en
  sidebar (nombreux commits `feat(frontend)`/`fix(frontend)` du même jour).
- Dashboard admin et suivi de tokens : spec et plan (`99e9e28`, `bdf0059`),
  capture des tokens OpenRouter, modèle `UsageDaily`
  (commits du 2026-08-17, qui prolongent ce chantier).

## 2026-08-17 — Dashboard admin, robustesse, sécurité (21 commits)

- Usage agrégé et détaillé par compte (`a45ee82`, `c749cd6`), dashboard admin
  React (`de41918`, `a0220a2`).
- Correctifs de robustesse : upsert atomique `UsageDaily` (`04d9a23`),
  budget de temps borné sur le repli LLM (`3026f31`), purge du cache
  disque obsolète et `busy_timeout` SQLite (`861d7f8`).
- Sécurité : escalade DLP sur combinaison de motifs (`b049b58`), re-vérification
  DLP à chaque tour de l'historique Streamlit (`1153353`), limitation de
  connexion par IP (`c8135a5`).
- `e4c7351`, correctifs de revue finale multiples (verrou de chargement,
  DLP historique, écart d'escalade nom+date, clé de rate-limit, course sur
  les bascules admin).

## 2026-08-25 — Reranking cross-encoder et durcissement (24 commits)

- Spécification et plan pour le reranking cross-encoder et le boost de
  catégorie par skill (`e441681`, `f3d37ad`).
- Module de reranking (`9616300`), intégration au pipeline RRF (`6935da5`,
  `019b0a1`), garantie d'inclusion des catégories pertinentes (`05b4da4`),
  version du pipeline dans la clé de cache (`1da1a1e`) — voir ADR-0001 et
  ADR-0009.
- Éditable dans le dashboard admin : nom, e-mail, rôle (`b6769ea`), graphique
  de consommation avec sélecteur de période (`4e65980`).
- Corrections DLP supplémentaires : noms au format worklist sans titre,
  faux positifs sur acronymes techniques (`36e5bbe`, `f74be81`, `24304e4`).
- Corrections API : conflit d'e-mail en 409 propre, longueur de question
  bornée (`15c0e0d`) ; focus trap clavier et fuite d'état entre utilisateurs
  côté frontend (`ff0ffaa`).

## 2026-08-26 — Garde de certitude mécanique et findings d'audit (7 commits)

- Garde-fou mécanique de certitude indépendant de l'auto-évaluation du LLM
  (`b71ef02`, voir ADR-0010), corrigé le même jour (`c909848`).
- 5 constats d'audit de sécurité API corrigés : limites de payload, TOCTOU,
  fuite/couverture du rate limiting (`d800e98`).
- Retrait des scores de retrieval qui fuitaient dans le texte, correctifs de
  repli 429, mention légale ajoutée (`ed10de6`, `dba9d98`, `397714e`).

## 2026-08-27 — Fermeture des contournements de la barrière Technicien (10 commits)

- Restauration du retrait des scores dans le garde de faible évidence
  (`61c7989`).
- Trois correctifs successifs sur la détection des boucles hors bloc de code
  du mode Technicien (`cc4d6dc`, `f73790c`, `9762d8c`) — voir ADR-0007.
- Fermeture d'un contournement DLP nom + date de naissance (`5292173`).
- Défense anti-extraction du prompt système (`108daf9`, corrigée le même
  jour par `e34c2d2` — formulation inversée).
- En-têtes de durcissement HTTP (`d948456`).
- `2e576b6`, `docs: record the security-audit-remaining-findings fix-wave
  plan` — trace du plan de correctifs restants après audit.

## 2026-09-24 — Banc de test temps réel et remédiation de propriété intellectuelle (6 commits)

- `02b3225`, `feat(agent): supprime l'en-tête « <TYPE> PROGRAM », fiches
  utilitaires pour scripts, rappel mode Technicien` — voir ADR-0012.
- `5951b46`, `feat: banc de test temps réel, retrieval r2, correctifs agent
  et documentation` — mise en place de `scripts/claude_harness/`, voir
  ADR-0011. `CACHE_VERSION` passe de `v29` à `v30`. 25 tests ajoutés.
- `a802c95`, `docs(rag): retire l'adresse e-mail professionnelle de
  SOURCES.md`.
- `b853cad`, `test(rag): script d'évaluation du retrieval (exact-match + 50
  requêtes sémantiques)` — `scripts/eval_retrieval_kb.py`.
- `daca42c`, fusion des correctifs de sécurité dans la branche de
  remédiation de propriété intellectuelle.
- `584ac55`, `fix(rag): régénère la base à partir de fiches de faits,
  supprime les reprises du manuel GLIMS` — voir ADR-0003. Contre-audit du
  2026-09-23 : 0 signalement ÉLEVÉ/MOYEN (contre 281 ÉLEVÉ et 153 MOYEN
  avant remédiation). 270 tests passés.
- Référence d'évaluation retenue ce jour : exact-match hit@1 = 1,000 (301
  fonctions) ; sémantique hit@1 = 0,600, hit@3 = 0,740, hit@5 = 0,800, MRR =
  0,693 (50 requêtes).

## Repères de synthèse

| Date | Événement |
|---|---|
| 2026-06-07 | Premier commit — agent v2, RAG hybride, base clean room |
| 2026-06-15 | Premier audit et affinage du retrieval |
| 2026-07-02 | Monitoring des ressources machine |
| 2026-08-14 | Comptes, sessions, API FastAPI, frontend Next.js, modes Technicien/DSI, DLP |
| 2026-08-17 | Dashboard admin, suivi d'usage, robustesse (repli LLM borné, cache purgé) |
| 2026-08-25 | Reranking cross-encoder, durcissement DLP et API |
| 2026-08-26 | Garde de certitude mécanique, 5 constats d'audit API corrigés |
| 2026-08-27 | Fermeture des contournements de la barrière Technicien, anti-extraction, en-têtes HTTP |
| 2026-09-24 | Banc de test temps réel, retrait de l'en-tête `<TYPE> PROGRAM`, remédiation PI de la base de connaissances |
