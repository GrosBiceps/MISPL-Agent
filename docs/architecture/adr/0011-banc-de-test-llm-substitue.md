# ADR-0011 — Banc de test avec LLM substitué (`scripts/claude_harness/`)

## Statut

Accepté.

## Date

2026-09-24 (commit `5951b46`, `feat: banc de test temps réel, retrieval r2,
correctifs agent et documentation`).

## Contexte

La suite `pytest` du projet n'appelle jamais un vrai LLM (pour rester rapide,
déterministe et gratuite), en testant le pipeline par des réponses simulées
ou des cas unitaires ciblés. Cela ne permet pas de vérifier le comportement
de bout en bout de l'agent face à des questions réalistes, formulées comme
un technicien les formulerait, ni de détecter des régressions de
comportement (barrière de mode Technicien contournée, bandeau mal placé,
lint qui casse un commentaire) qui n'apparaissent qu'avec des réponses
longues et variées, proches de ce qu'un vrai LLM produirait.

## Décision

Construire un banc de test « temps réel » (`scripts/claude_harness/`) en deux
phases :
- **`harness.py prepare`** : exécute le vrai `ask_mispl()` pour un ensemble
  de questions réalistes (`questions.json`, 122 prompts), intercepte l'appel
  réseau juste avant qu'il ne parte, et écrit les prompts effectivement
  construits (system + user) dans `prompts/<id>.md`.
- Les réponses à ces prompts sont produites par des **subagents Claude** (le
  modèle qui exécute ce projet en tant qu'assistant de développement), qui
  jouent le rôle du LLM cible en répondant comme le ferait le modèle réel en
  production, sans jamais appeler OpenRouter.
- **`harness.py finalize`** : relance `ask_mispl()` avec un
  `_call_with_fallback` factice qui renvoie ces réponses comme une
  complétion OpenAI-compatible, pour que **tous les post-traitements réels**
  s'appliquent (auto-fix, barrière de mode d'accès, garde de faible
  évidence, lint), puis évalue automatiquement le résultat et écrit
  `report.json`/`report.md`.
- **`e2e.py`** ajoute un test de bout en bout « logiciel lancé » : démarre un
  serveur LLM factice (`fake_llm_server.py`) et la vraie API FastAPI sur une
  base SQLite isolée, crée des comptes, envoie les questions à la vraie route
  `POST /chat/ask`, et vérifie la cohérence avec `report.json`.
- Une **garde réseau** (`common.install_network_guard`) fait échouer bruyamment
  (code de sortie 3) toute tentative d'appel réseau externe pendant
  l'exécution du banc, pour garantir qu'aucun test ne dépend silencieusement
  d'OpenRouter.

## Alternatives étudiées

- **Tests manuels ponctuels avant chaque mise en production** : c'était la
  pratique implicite avant le 2026-09-24 ; non reproductible, non
  systématique, ne laisse pas de trace exploitable pour détecter une
  régression future.
- **Appeler un vrai LLM dans les tests automatisés** : écarté — coût, lenteur,
  non-déterminisme (réponses différentes à chaque exécution), dépendance à
  la disponibilité d'OpenRouter, incompatible avec une suite de tests reproductible.
- **Se limiter à la suite `pytest` existante** : insuffisant pour détecter les
  régressions de comportement de bout en bout observées lors de l'audit
  (barrière de mode Technicien contournable, bandeau mal placé sur des refus
  sans code) — ces cas nécessitent des réponses réalistes, longues et
  variées, que les tests unitaires ne couvrent pas de façon exhaustive.

## Conséquences

- Le banc de test a permis de détecter et corriger plusieurs régressions
  réelles le 2026-09-24 : faux positifs du linter sur des commentaires bloc,
  contournement de la barrière Technicien par une mention en prose, bandeau
  de documentation faible superflu sur des refus. `CACHE_VERSION` est passé
  de `v29` à `v30` à la suite de ces correctifs. 25 tests supplémentaires ont
  été ajoutés à la suite pytest pour figer ces comportements.
- Le banc dépend de la disponibilité de subagents Claude pour produire les
  réponses de `prepare` : ce n'est pas un test automatisable en continu sans
  intervention, contrairement à `pytest`.
- `api.main.warm_up_rag()` (préchargement du RAG au démarrage) a été ajouté
  directement à la suite d'une mesure faite par ce banc (43 s de première
  requête sans préchargement, mesurées par `e2e.py`).
