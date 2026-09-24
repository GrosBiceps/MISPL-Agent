# Guide développeur

Ce guide s'adresse à toute personne qui modifie le code du projet (moteur
agent/RAG/sécurité, API, frontend) ou la base de connaissances. Il complète
`CLAUDE.md`, qui reste la référence normative pour les règles de travail
(anti-hallucination, propriété intellectuelle, dépôt public).

## Installation

Prérequis : Python 3.10 ou plus récent, Node.js pour le frontend.

```powershell
# Environnement virtuel
python -m venv .venv
.venv\Scripts\activate

# Dépendances Python
pip install -r requirements.txt

# Fichier d'environnement
Copy-Item .env.example .env
# puis renseigner OPENROUTER_API_KEY dans .env

# Frontend
cd frontend
npm install
```

Au premier usage, les modèles d'embedding et de reranking sont téléchargés
depuis Hugging Face puis mis en cache localement. Construisez l'index RAG
avant le premier lancement :

```powershell
python src/rag/build_vectorstore.py
```

## Conventions

- **Langue** : code et commentaires en français dans la majorité du projet ;
  certains commits et modules plus récents (sécurité, API) utilisent
  l'anglais dans les messages de commit et parfois les commentaires — suivez
  la convention déjà en place dans le fichier que vous modifiez.
- **Commentaires MISPL** générés par l'agent : uniquement `/* ... */`, jamais
  `//` (`//` n'est pas un commentaire MISPL valide).
- **Style de commit** : préfixes `feat:`, `fix:`, `docs:`, `test:`, `chore:`,
  avec un scope entre parenthèses quand pertinent (`fix(security):`,
  `feat(rag):`...), cohérent avec `git log` existant.
- **Frontend** : lisez impérativement `frontend/AGENTS.md` avant de modifier
  le code — la version de Next.js utilisée (16, App Router) diffère des
  conventions plus anciennes sur lesquelles un modèle de langage a pu être
  entraîné.
- **Versions de cache** : toute modification du prompt système, du
  post-traitement de réponse ou des garde-fous de sortie doit incrémenter
  `CACHE_VERSION` (`src/agent/mispl_agent.py`). Toute modification de
  l'expansion de requête, du boost de catégorie ou du modèle de reranking
  doit incrémenter `RETRIEVAL_PIPELINE_VERSION` (`src/rag/retriever.py`).
  Une reconstruction de l'index ne change pas la clé de cache : videz
  `outputs/cache/` si vous avez besoin d'observer l'effet immédiat d'un
  changement de base de connaissances.

## Tests

```powershell
pytest
```

Configuration dans `pytest.ini` (`testpaths = tests`). La suite couvre
`tests/agent/`, `tests/api/`, `tests/rag/`, `tests/security/` et
`tests/mispl_examples/`. Les tests n'appellent jamais OpenRouter ; les tests
d'API utilisent une base SQLite en mémoire. `tests/mispl_examples/`
interroge en revanche le véritable index : construisez-le d'abord
(`python src/rag/build_vectorstore.py`).

## Banc de test « temps réel » (`scripts/claude_harness/`)

Ce banc complète `pytest` en confrontant l'agent à des questions réalistes
(`questions.json`, 122 prompts) sans jamais appeler un vrai LLM — les
réponses sont produites par des subagents Claude qui jouent le rôle du
modèle cible (voir
`docs/architecture/adr/0011-banc-de-test-llm-substitue.md`).

```powershell
# 1. Prépare les prompts réels (intercepte l'appel réseau avant qu'il ne parte)
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/claude_harness/harness.py prepare

# 2. (Les réponses sont produites hors de ce script, par des subagents Claude,
#    écrites dans scripts/claude_harness/answers/<id>.md)

# 3. Rejoue les réponses à travers le pipeline réel de post-traitement,
#    évalue et écrit report.json / report.md
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/claude_harness/harness.py finalize

# 4. Test de bout en bout « logiciel lancé » (API réelle + serveur LLM factice)
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/claude_harness/e2e.py
```

Une garde réseau installée par `common.install_network_guard()` fait échouer
bruyamment (code de sortie 3) toute tentative d'appel réseau externe pendant
l'exécution du banc — un signal que le test tente, par erreur, de contacter
un vrai service externe.

## Évaluation du retrieval

```powershell
python scripts/eval_retrieval_kb.py                  # exact-match + sémantique
python scripts/eval_retrieval_kb.py --semantic-only   # sémantique seule
python scripts/eval_retrieval_kb.py --out mon_eval.json
```

Deux volets : exact-match (chaque fonction connue interrogée par son nom) et
sémantique (50 questions en français sans nom de fonction). Référence du
2026-09-24 : exact-match hit@1 = 1,000 (301 fonctions) ; sémantique hit@1 =
0,600, hit@3 = 0,740, hit@5 = 0,800, MRR = 0,693. **Toute modification du
retrieval qui dégrade ces chiffres doit être justifiée explicitement**, pas
seulement fusionnée silencieusement.

## Modifier la base de connaissances

Procédure impérative avant tout ajout ou toute modification de
`rag_knowledge_base/` (détaillée avec diagramme dans
`docs/specifications/diagramme_activite.md`, second diagramme) :

1. Relever uniquement des **faits techniques** (signature, paramètres,
   retour, comportement), rédigés avec vos propres mots, dans le vocabulaire
   du langage proxy Progress ABL/OpenEdge (voir
   `docs/architecture/adr/0003-base-connaissances-clean-room.md`). Jamais
   d'exemple ou de valeur recopiée du manuel.
2. Lancer le contrôle anti-régression de propriété intellectuelle :
   ```powershell
   python tools/check_ip_similarity.py --manual "<chemin local du manuel GLIMS>"
   ```
   Le résultat attendu est `RÉSULTAT : OK` (code de sortie 0). Tout
   signalement ÉLEVÉ ou MOYEN doit être corrigé avant de continuer ; une
   exception nécessite une justification écrite dans
   `tools/ip_allowlist.json`.
3. Mettre à jour `rag_knowledge_base/SOURCES.md` si une nouvelle source est
   utilisée.
4. Reconstruire l'index :
   ```powershell
   python src/rag/build_vectorstore.py
   ```
5. Relancer `pytest` puis `scripts/eval_retrieval_kb.py`, et vérifier
   l'absence de régression face à la référence documentée ci-dessus.

**Rappel dépôt public** : le manuel GLIMS lui-même, le dossier d'audit
(`docs/audit_PI_*/`), `DSI/`, `.env` et `data/*.db` ne doivent jamais être
versionnés (voir `.gitignore` et `CLAUDE.md`, section « Dépôt public »).

## Procédure de contribution

1. Créer une branche depuis `main`.
2. Développer en suivant les conventions ci-dessus (TDD encouragé pour toute
   modification de `src/agent/`, `src/rag/`, `src/security/`, `api/`).
3. Lancer `pytest` (et le banc de test temps réel si le changement touche le
   comportement de génération ou les garde-fous de sortie).
4. Si `rag_knowledge_base/` est modifiée, suivre la procédure ci-dessus dans
   son intégralité (contrôle PI, reconstruction d'index, évaluation).
5. Mettre à jour `CHANGELOG.md` pour tout changement notable, et
   `docs/architecture/adr/` si la modification constitue une décision
   structurante nouvelle (au format MADR, avec la date réelle du commit).
6. Ouvrir une pull request ; ne jamais versionner de secret, de donnée CHU,
   ni d'extrait du manuel GLIMS.

## Commandes utiles

```powershell
python src/rag/build_vectorstore.py              # reconstruit l'index après toute modification de la base
pytest                                           # suite de tests (voir pytest.ini)
python scripts/eval_retrieval_kb.py              # hit@k / MRR, exact-match + 50 requêtes sémantiques
python tools/check_ip_similarity.py --manual "<chemin local de l'aide GLIMS>"   # contrôle PI
uvicorn api.main:app --port 8000                 # API
cd frontend; npm run dev                         # frontend (http://localhost:3000)
.\start.ps1 run                                  # interface Streamlit (http://localhost:8501)
python scripts/health_check.py                   # vérification de bout en bout de l'environnement
python scripts/list_free_models.py               # liste actuelle des modèles gratuits OpenRouter
python scripts/create_admin.py                   # bootstrap du premier compte admin (plateforme API)
python scripts/set_dsi_password.py               # configure le mot de passe DSI partagé (Streamlit)
```
