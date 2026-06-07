# 4 — Installation et maintenance

## Initialisation à partir de zéro

### Prérequis
- Python 3.10+
- Une clé API **OpenRouter** (gratuite sur openrouter.ai).

### Étapes

1. **Cloner et installer les dépendances**
   ```bash
   git clone https://github.com/GrosBiceps/MISPL-Agent.git
   cd MISPL-Agent
   pip install -r requirements.txt
   ```

2. **Configurer la clé API**
   Créer un fichier `.env` à la racine :
   ```
   OPENROUTER_API_KEY=sk-or-v1-...
   ```
   (Alternative : saisir la clé directement dans l'UI via le panneau « Parametres ».)

3. **Construire le vectorstore** (si absent — voir section maintenance)
   ```bash
   python src/rag/build_vectorstore.py
   ```
   Le premier lancement télécharge le modèle d'embeddings `paraphrase-multilingual-MiniLM-L12-v2` (~100 Mo).

4. **Lancer l'application**
   ```bash
   streamlit run app.py
   ```
   Ou sous Windows : `.\start.ps1`. L'app s'ouvre sur `http://localhost:8501`.

### Déploiement Streamlit Cloud
- Le vectorstore ChromaDB est **commité dans le dépôt** → l'app fonctionne directement sans rebuild.
- Renseigner `OPENROUTER_API_KEY` dans **Streamlit Secrets** (ou via le champ Paramètres de l'UI).
- Premier boot : ~2-3 min (téléchargement du modèle d'embeddings).

---

## Mise à jour de la base de connaissances

La documentation source vit dans `french/Content/` (fichiers `.htm` GLIMS).

### Procédure
1. Remplacer/ajouter les fichiers `.htm` dans `french/Content/`.
2. Reconstruire :
   ```bash
   python src/rag/build_vectorstore.py            # rebuild complet (défaut)
   python src/rag/build_vectorstore.py --no-rebuild  # ajout sans recréer la collection
   ```
3. **Invalider le cache de réponses** : incrémenter `CACHE_VERSION` dans `mispl_agent.py` (ex. `"v3"` → `"v4"`) OU vider `outputs/cache/`. Sinon d'anciennes réponses (potentiellement basées sur l'ancienne doc) seront resservies pendant 24h.
4. Redémarrer l'app. Le singleton `_RetrieverState` rechargera l'index ; au besoin appeler `_RetrieverState.invalidate()`.

### Embeddings OpenAI (optionnel, meilleure qualité sémantique)
```bash
python src/rag/build_vectorstore.py --openai   # nécessite OPENAI_API_KEY
```
Attention : doit être cohérent entre build et recherche (même modèle d'embeddings des deux côtés).

---

## Points de vigilance techniques

### Goulots d'étranglement
- **Latence LLM** : nemotron-120b en free tier OpenRouter = 4–16 s typiques, jusqu'à 30 s+ aux heures de pointe. C'est le goulot principal, pas le RAG (~100–300 ms).
- **Premier chargement** : init du singleton (ChromaDB + index BM25 reconstruit en mémoire + modèle d'embeddings) = ~quelques secondes au premier appel. Acceptable car amorti ensuite.
- **Index BM25 reconstruit à chaque démarrage** : `BM25Okapi` n'est pas persisté, il est recalculé depuis `bm25_corpus.json` à chaque init du process. Pour un très gros corpus, envisager une persistance.

### Gestion mémoire
- Le corpus BM25 (`bm25_corpus.json`, ~15 Mo) est chargé entièrement en RAM.
- ChromaDB charge l'index HNSW en mémoire.
- Le sur-échantillonnage `fetch_n = top_k × 3` crée un dict intermédiaire `all_docs_map` à chaque requête — négligeable à `top_k=6`, à surveiller si `top_k` augmente fortement.

### Limites de l'architecture actuelle
1. **`@st.cache_resource` obligatoire** : `_load_agent` retourne des fonctions non-sérialisables. Ne JAMAIS repasser à `@st.cache_data` (régression connue : le chatbot devient muet silencieusement).
2. **Clé API via `os.environ` temporaire** : l'UI positionne la clé dans `os.environ` le temps de l'appel puis restaure. Acceptable en mono-utilisateur ; en multi-utilisateur strict, préférer une injection par paramètre.
3. **`manifest.json` n'écrit pas de date de build** : la pill « Build YYYY-MM-DD » de l'UI cherche `build_date`/`timestamp`/`built_at`, absents du manifest actuel → elle ne s'affiche jamais. *À corriger* : ajouter un champ daté dans le manifest lors du build.
4. **Strip CoT heuristique** : `_strip_chain_of_thought` repose sur une liste de signatures anglaises. Un modèle raisonnant en français ou avec d'autres tournures pourrait passer au travers. Robuste pour nemotron, à étendre si changement de modèle par défaut.
5. **Synonymes BM25 manuels** : `_FN_SYNONYMS` est maintenu à la main. Toute nouvelle fonction importante gagne à y être ajoutée pour le matching FR.
6. **Vectorstore versionné dans git** (~137 Mo) : `chroma.sqlite3` ~93 Mo déclenche un warning GitHub (>50 Mo) sans bloquer. Si la doc grossit beaucoup, envisager Git LFS ou un rebuild au déploiement.

### Sécurité
- Entrées utilisateur échappées (`html.escape`) avant affichage → anti-XSS.
- Whitelist sur les noms de skills → anti-path-traversal.
- Stack traces non exposées : message générique + ID de référence loggé serveur.
- Linter MISPL : filet de sécurité sur le code généré (boucles infinies, champs read-only, division entière), mais **ne remplace pas une validation humaine** avant déploiement en production GLIMS.
