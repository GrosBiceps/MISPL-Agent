# 3 — Méthodes et logique cœur (Deep Dive)

Analyse approfondie des classes, méthodes et algorithmes. C'est le cœur de la documentation.

---

## A. Ingestion — `src/rag/build_vectorstore.py`

Pipeline **hors-ligne** : documentation HTML GLIMS → chunks structurés → ChromaDB + corpus BM25. Exécuté une fois (ou après mise à jour de la doc).

### Stratégie de chunking : « function-aware »

Principe directeur : **un chunk = une fonction MISPL atomique**. Contrairement à un découpage naïf par taille fixe, le chunking respecte la structure documentaire pour ne jamais couper une fonction en deux.

#### Routage du parser — `parse_html_file(filepath, rel_path)`
Choisit le parser selon le nom de fichier :
- Fichiers de référence de fonctions (`function_string`, `function_datetime`, `function_mathematical`...) → `_parse_function_file` (parser spécialisé).
- Tout le reste (pages conceptuelles, ERD, syntaxe) → `_parse_generic_file`.

#### `_parse_function_file` — parser spécialisé
1. Lit le HTML (`_read_html` avec détection d'encodage).
2. Trouve tous les `<h3>` — chaque `<h3>` marque une fonction.
3. Si aucun `<h3>` → bascule sur `_parse_generic_file` (fallback).
4. Pour chaque `<h3>` :
   - Normalise le nom : `"Current Device"` → `"CurrentDevice"` (suppression des espaces typographiques de la doc).
   - **Filtres anti-bruit** : ignore les titres < 2 caractères, les non-PascalCase, et les headers de navigation contenant `MISPL`, `Fonctions`, `Function`, `Syntax`, `Note`.
   - Collecte tous les nœuds frères jusqu'au `<h3>` suivant.
   - Traite chaque nœud via `_process_node` (description, signature, exemples).
5. Construit un texte de chunk **structuré** :
   ```
   FONCTION : Substr
   SIGNATURE : String Substr(String Source, Integer Position, Integer Length)
   TYPE DE RETOUR : String
   DESCRIPTION : ...
   EXEMPLES :
     - ...
   ```
6. Si le chunk dépasse `CHUNK_MAX_CHARS` (1400) → split via `_split_preserving_signature`.

#### `_process_node(inner)` — extraction par type de nœud
Fonction récursive qui traite chaque élément HTML :
- `<blockquote>` → déplie et traite récursivement les enfants.
- `<p>` → ajouté à la description.
- `<table>` → passé à `_extract_signature_from_table` (extraction de signature).
- `<ul>/<ol>` → items ajoutés aux exemples.
- `<pre>/<code>` → ajouté comme exemple préfixé « Exemple : ».
- `<h4>/<h5>` → sous-titre dans la description.

#### `_extract_signature_from_table(table)` — extraction de signature
Reconstruit `ReturnType FunctionName(params)` depuis un tableau GLIMS. Logique défensive :
- N'utilise **que la première ligne** (`rows[0]`) — les lignes suivantes sont des exemples ou des tableaux de paramètres qui parasitent la détection.
- **Garde anti-exemple** : si la ligne contient `"`, `rend`, `returns`, `renvoie`, `exemple`, `example` → ce n'est pas une signature, on retourne vide.
- Détecte le type de retour parmi `MISPL_RETURN_TYPES` (`String`, `Integer`, `Fractional`, `Logical`, `Date`, `Datetime`, `Time`, `Void`).
- Détecte le nom de fonction : soit cellule PascalCase dédiée, soit regex `ReturnType FuncName(` sur le texte complet.
- **Liste d'exclusion** `_NOT_FUNC_NAMES` : `Directive`, `Description`, `Example`, `Note`, `Parameter`, etc. — évite de prendre un terme de doc pour un nom de fonction.

#### `_split_preserving_signature(text, signature, max_chars)` — découpe sûre
Quand un chunk dépasse la taille max, le découpe par paragraphes **en réinjectant toujours la signature** dans chaque sous-chunk. La signature est l'info la plus critique : ne jamais la perdre. Overlap de `CHUNK_OVERLAP_CHARS` (400) entre sous-chunks, dimensionné pour couvrir une signature complète.

### Structure de données — le chunk

`_make_chunk` produit un dictionnaire :
```python
{
  "id": "<md5(source_idx_text60)>",
  "text": "FONCTION : ...\nSIGNATURE : ...",
  "metadata": {
    "source": "Content/.../function_string.htm",
    "doc_title": "...",
    "section": "...",
    "function_name": "Substr",       # ← clé pour exact-match
    "return_type": "String",
    "signature": "String Substr(...)",  # tronqué à 300 chars
    "has_examples": True,
    "category": "string",            # déduit du chemin via CATEGORY_MAP
    "is_table_independent": False,
    "priority": True,                # fichiers MISPL prioritaires
    "char_count": 412,
  }
}
```

Chaque `function_name` détecté est ajouté au set global `KNOWN_FUNCTION_NAMES`, **sérialisé dans `bm25_corpus.json`** sous `known_functions` → c'est ce qui permet l'exact-match à la recherche.

### Sorties du build
1. **ChromaDB** (`docs/chunks/vectorstore/`) — embeddings denses.
2. **`bm25_corpus.json`** — textes + métadonnées + `known_functions`.
3. **`manifest.json`** — stats du build (`total_chunks`, `known_functions_count`, `embedding_model`...).

---

## B. Recherche hybride — `src/rag/retriever.py` (STAGE 2)

Le composant central. Trois niveaux de recherche fusionnés.

### Tokenisation BM25 — `_tokenize(text)`
Tokeniseur sur mesure pour le mélange FR/EN/identifiants techniques :
1. Découpe sur `[A-Za-z0-9À-ɏ_-]+`.
2. Ajoute la version minuscule.
3. Ajoute la version **dé-accentuée** (`_normalize` via `unicodedata`) → `chaîne` matche `chaine`.
4. **Découpe PascalCase** : `GetSiteAttribute` → `get`, `site`, `attribute`. Crucial : permet à une question « obtenir attribut site » de matcher la fonction `GetSiteAttribute`.

### Enrichissement du corpus BM25 — `_enrich_bm25_text(chunk)`
Avant indexation, chaque chunk est augmenté pour booster la pertinence lexicale :
- Texte original.
- **Nom de fonction répété ×3** → booste son TF (term frequency) dans BM25.
- Sous-mots PascalCase ×2.
- **Synonymes FR/EN** depuis `_FN_SYNONYMS` (dictionnaire manuel : `Substr` → « extraire sous-chaine substring portion », etc.). Permet de retrouver une fonction depuis une question en français qui n'emploie jamais le nom anglais.
- Signature.

### Le singleton — `_RetrieverState`
Charge **une seule fois** la collection ChromaDB et l'index BM25 (coûteux). Réutilisé entre requêtes via `_RetrieverState.get(use_openai)`. Recharge seulement si le mode embeddings change. `invalidate()` force le rechargement après un rebuild.

### `query(question, top_k)` — l'algorithme complet

```
k = top_k (défaut 6)
fetch_n = k × 3   # sur-échantillonnage pour la fusion
```

**Niveau 1 — Exact-match (priorité absolue)**
`_detect_function_name(question)` :
- Tokenise la question, intersecte avec `known_functions`.
- Si match → prend le **token le plus long** (évite `Log` quand `Log10` est présent).
- `_exact_match_search(fn)` interroge ChromaDB avec `where={"function_name": fn}` → docs avec **score 1.0** et flag `exact_match=True`. Ces docs **court-circuitent** le ranking.

**Niveau 2 — Double recherche parallèle**
- `_dense_search` : ChromaDB sémantique, `score = 1.0 − distance` (cosinus).
- `_bm25_search` : `bm25.get_scores(tokens)`, garde les n meilleurs scores > 0.

**Fusion — `_reciprocal_rank_fusion(dense_ids, bm25_ids, k=60)`**
```python
score(d) = Σ  1 / (RRF_K + rank_i + 1)
```
Point technique clé : RRF fusionne les **rangs**, pas les scores bruts. Impossible d'additionner directement un score BM25 (échelle ouverte) et une similarité cosinus (0–1). En se basant sur la position dans chaque classement, RRF est **robuste aux différences d'échelle**. `k=60` est la valeur standard de la littérature (Cormack et al. 2009).

**Raffinement post-fusion**
1. Déduplication (les `exact_docs` déjà vus sont sautés).
2. **Tri par priorité** : chunks AVEC `function_name` d'abord, pages génériques (release notes, config) ensuite — évite que les pages bavardes noient les vraies fonctions.
3. Concaténation : `exact_docs` (tête) + `rrf_docs`.
4. Troncature à `top_k`.

**Reorder anti-« Lost in the Middle » — `_reorder_for_llm(docs)`**
Basé sur Liu et al. 2023 : les LLM lisent mieux les positions #1 et dernière. Donc :
- meilleur chunk → position 1 (tête)
- 2ᵉ meilleur → position dernière (queue)
- le reste au milieu (recall nécessaire mais moins lu)

### Formatage — `format_context(docs)`
Transforme les chunks en texte injectable : en-tête par doc (numéro, ⭐ si exact-match, nom de fonction, type, source, score), signature mise en avant (« SIGNATURE CONFIRMÉE »), puis le texte.

---

## C. Orchestration — `src/agent/mispl_agent.py`

### `ask_mispl(question, ...)` → `tuple[str, list]`
Chef d'orchestre. Retourne `(réponse, docs)` — les `docs` sont remontés pour éviter une **double requête RAG** côté UI.

Séquence :
1. **Cache** — `_cache_key` (SHA-256 de `CACHE_VERSION|question|model|top_k`), `_cache_get` (TTL 24h). `CACHE_VERSION` permet d'invalider tout le cache obsolète en bumpant une constante.
2. **Retrieval** — `retriever.query` + `format_context`.
3. **Prompt système** — `build_system_prompt` selon le profil skill détecté.
4. **Messages** — `[system] + historique[-6:] + [user]`. L'historique est injecté entre system et user pour le contexte conversationnel (limité à 6 échanges pour ne pas dépasser la fenêtre).
5. **Appel LLM** — `_call_with_fallback`.
6. **Strip CoT** — `_strip_chain_of_thought` (voir ci-dessous).
7. **Lint** — `lint_response`.
8. **Cache set** + sauvegarde session.

### `_call_with_fallback(client, model, messages)` — résilience LLM
- Construit `models_to_try` : modèle demandé + `FALLBACK_ORDER`.
- Pour chaque modèle, `max_retries` tentatives :
  - `RateLimitError` (429) → lit `retry_after_seconds` des métadonnées, `time.sleep(min(retry_after, 20))`, log warning, passe au modèle suivant.
  - Erreur 404 (modèle inexistant) → fallback immédiat sans retry.
  - `timeout=45` sur chaque appel.
- Retourne `(used_model, completion)`. Si fallback, l'UI le signale.

### `_strip_chain_of_thought(response)` — filet de sécurité anti-CoT
Certains modèles (nemotron-120b) **ignorent** l'interdiction du prompt et raisonnent à voix haute. Cette fonction nettoie côté code :
- Cherche le premier **marqueur de réponse structurée** (`## Contexte GLIMS`, `## Code MISPL`, `⚠️ Fonction non trouvée`...).
- Si le préambule qui précède contient des **signatures de raisonnement** (`okay`, `let me`, `the user`, `wait`, `looking at`...) → coupe tout ce qui précède le marqueur.
- Si aucun marqueur ou pas de signature CoT → ne touche à rien (réponses libres préservées).

### Détection de profil — `_detect_skill_profile(question)`
Mots-clés → profil : `rapport/template` → report, `table/champ/erd` → erd, `optimis/lent/boucle` → perf, sinon → code.

---

## D. Prompt — `src/agent/prompt_builder.py`

### `build_system_prompt(active_skills, include_rules, max_tokens_budget)`
Assemble : `_BASE_SYSTEM` (règles absolues) + règles globales + Skills Markdown, dans un budget de tokens approximé (`max_tokens_budget × 4` chars).

### `_load_skill(skill_name)` — sécurisé et caché
- `@lru_cache(maxsize=20)` — évite les I/O disque répétés.
- **Whitelist anti-path-traversal** : `re.match(r'^[a-z0-9_-]+$', skill_name)` — bloque `../../etc/passwd`.
- Troncature intelligente : si > 3000 chars, coupe au **dernier paragraphe complet** (split `\n\n`), jamais en plein milieu d'une phrase.

### `_BASE_SYSTEM` — les règles absolues
Règle 0 : interdit le chain-of-thought visible. Règle 1 : zéro hallucination. Règle 2 : traçabilité obligatoire (source par fonction). Règle 3 : niveau de certitude (✅/⚠️/🔬). Règles 4–6 : gestion valeur inconnue `?`, piège de la division entière, efficience serveur GLIMS. Plus un format de réponse imposé et une référence de syntaxe MISPL.

---

## E. Linter — `src/agent/linter.py`

### `lint_response(llm_response)` → `LintResult`
1. `extract_mispl_blocks` — extrait les blocs ` ```mispl ` ou ` ``` ` contenant `PROGRAM`.
2. `lint_mispl_code` sur chaque bloc.

### `lint_mispl_code(code)` — analyse statique
- Supprime les commentaires (`//`, `/* */`).
- Applique `_RULES` (regex → sévérité → message) :
  - **ERREURS** : `WHILE TRUE` (boucle infinie), assignation `.Id`/`.ValidationStatus`/`.OrderStatus` (champs read-only), `REPEAT` sans `UNTIL`, division par zéro.
  - **AVERTISSEMENTS** : division entière silencieuse (`5/2=2`), modification de résultat patient sans `AddLogEntry`, `NumEntries()` dans une condition `WHILE`.
  - **CONSEILS** : `SetSiteAttribute` (état global partagé), accès champ sans vérifier `?`.
- **Vérifications d'équilibre** : `IF`/`ENDIF`, `WHILE`/`DONE`, présence de `RETURN` dans tout `PROGRAM`.

`LintResult` expose `is_clean`, `has_errors`, `format_report_md()` (rapport Markdown avec emojis pour Streamlit).
