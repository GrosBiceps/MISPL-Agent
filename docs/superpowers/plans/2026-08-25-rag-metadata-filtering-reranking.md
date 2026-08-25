# RAG Metadata Boost + Cross-Encoder Reranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the retriever's dead/arbitrary heuristics (a no-op category whitelist boost, three magic multipliers) with a real cross-encoder relevance score, add a non-exclusionary skill-based category inclusion guarantee, keep the cache airtight, and fix stale documentation.

**Architecture:** A new standalone `src/rag/reranker.py` module wraps a multilingual `sentence-transformers` `CrossEncoder`, with a safe fallback to input order on any failure. `MISPLRetriever.query()` widens its RRF candidate pool (to ~20), optionally tops it up with category-relevant candidates fetched via ChromaDB's `where` filter (guarantee-of-inclusion, never exclusion) keyed off the caller's active skills, then hands the whole pool to the reranker before truncating to `top_k`. `ask_mispl` computes `active_skills` earlier so it can pass it into retrieval (previously computed only after retrieval, for the prompt). The cache key gains a new pipeline-version axis so this whole change invalidates all pre-existing cached responses.

**Tech Stack:** Python 3.10+, `sentence-transformers` (already a pinned dependency — provides both the existing bi-encoder embedding function and, new here, `CrossEncoder`), ChromaDB (`collection.get(where=...)`), pytest.

**Spec:** `docs/superpowers/specs/2026-08-25-rag-metadata-filtering-reranking-design.md`

## Global Constraints

- No new pip dependency — everything relies on `sentence-transformers`, already in `requirements.txt`.
- Category-based filtering must never EXCLUDE a candidate — inclusion-guarantee only.
- `access_mode` (DSI/Technicien) is explicitly OUT of scope for retrieval filtering — do not wire it into anything in this plan.
- Exact-match docs (verbatim function name detected) always stay pinned first, never passed to the reranker, never affected by category widening.
- Reranker failures (model load or inference) must never raise — always fall back to the pre-reranking order.
- Any change to retrieval scoring/ordering logic must be reflected in `RETRIEVAL_PIPELINE_VERSION` so cached responses from before this change are never served after it.
- Follow the existing project test convention: pure logic gets fast mocked/fixture-based unit tests (no real model downloads, no real ChromaDB in tests); only `tests/mispl_examples/test_basic_functions.py`'s existing `TestRAGRetrieval` class touches the real on-disk vectorstore, and this plan does not add to that file.

---

### Task 1: Reranker module (`src/rag/reranker.py`)

**Files:**
- Create: `src/rag/reranker.py`
- Test: `tests/rag/test_reranker.py`

**Interfaces:**
- Consumes: nothing from other tasks (fully standalone). Uses `sentence_transformers.CrossEncoder` (imported lazily inside the module, already installed).
- Produces: `rerank(query: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]` — the only public entry point later tasks will call. Each input/output doc is a `dict` with at least a `"text"` key; output docs are copies (never mutates the input list or its dict elements) with `"score"` overwritten to the cross-encoder's float score, sorted descending by that score. Returns the input list unchanged (same objects, same order) if reranking is disabled or fails at any point.

- [ ] **Step 1: Write the failing tests**

Create `tests/rag/test_reranker.py`:

```python
"""Tests du module reranker — cross-encoder de reclassement post-RRF."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import src.rag.reranker as reranker_mod
from src.rag.reranker import rerank


class _FakeCrossEncoder:
    """Simule un CrossEncoder : score = longueur du texte du doc (déterministe,
    aucun téléchargement de modèle réel dans les tests)."""

    def predict(self, pairs):
        return [float(len(doc_text)) for _query, doc_text in pairs]


class TestRerank:
    def test_empty_docs_returns_empty(self, monkeypatch):
        monkeypatch.setattr(reranker_mod, "_get_cross_encoder", lambda: _FakeCrossEncoder())
        assert rerank("une question", []) == []

    def test_reorders_by_cross_encoder_score(self, monkeypatch):
        monkeypatch.setattr(reranker_mod, "_get_cross_encoder", lambda: _FakeCrossEncoder())
        docs = [
            {"id": "short", "text": "abc"},
            {"id": "long", "text": "abcdefghijklmnop"},
        ]
        result = rerank("une question", docs)
        assert [d["id"] for d in result] == ["long", "short"]
        assert result[0]["score"] > result[1]["score"]

    def test_does_not_mutate_input_list_or_dicts(self, monkeypatch):
        monkeypatch.setattr(reranker_mod, "_get_cross_encoder", lambda: _FakeCrossEncoder())
        docs = [{"id": "a", "text": "x"}, {"id": "b", "text": "yy"}]
        original = [dict(d) for d in docs]
        rerank("une question", docs)
        assert docs == original

    def test_model_load_failure_falls_back_to_input_order(self, monkeypatch):
        monkeypatch.setattr(reranker_mod, "_get_cross_encoder", lambda: None)
        docs = [{"id": "a", "text": "x"}, {"id": "b", "text": "yy"}]
        result = rerank("une question", docs)
        assert result == docs

    def test_inference_exception_falls_back_to_input_order(self, monkeypatch):
        class _RaisingEncoder:
            def predict(self, pairs):
                raise RuntimeError("boom")

        monkeypatch.setattr(reranker_mod, "_get_cross_encoder", lambda: _RaisingEncoder())
        docs = [{"id": "a", "text": "x"}, {"id": "b", "text": "yy"}]
        result = rerank("une question", docs)
        assert result == docs

    def test_disabled_via_env_var_skips_model_entirely(self, monkeypatch):
        monkeypatch.setenv("MISPL_RERANK_ENABLED", "false")

        def _boom():
            raise AssertionError("le modèle ne doit pas être chargé quand désactivé")

        monkeypatch.setattr(reranker_mod, "_get_cross_encoder", _boom)
        docs = [{"id": "a", "text": "x"}]
        result = rerank("une question", docs)
        assert result == docs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/test_reranker.py -v` (adjust the relative `../../../` prefix if not running from a worktree — use whatever path reaches the repo's `.venv/Scripts/python.exe` from the current working directory)
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.reranker'`

- [ ] **Step 3: Implement `src/rag/reranker.py`**

```python
"""
Reranker cross-encoder — score de pertinence sémantique réel entre la question
et chaque chunk candidat, en remplacement des anciens boosts heuristiques
arbitraires post-RRF (×1.12/×1.08/×1.04, cf. src/rag/retriever.py).

Modèle multilingue (corpus et questions MISPL Agent majoritairement en
français) : cross-encoder/mmarco-mMiniLMv2-L12-H384-v1, chargé via
sentence-transformers (déjà une dépendance du projet — aucun ajout requis).

Repli automatique sur l'ordre d'entrée en cas d'échec (modèle non chargeable,
erreur d'inférence, désactivation via variable d'env) — ne doit jamais faire
échouer une requête de chat.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

RERANKER_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

_cross_encoder = None
_load_failed = False


def _rerank_enabled() -> bool:
    return os.environ.get("MISPL_RERANK_ENABLED", "true").strip().lower() not in ("false", "0", "no")


def _get_cross_encoder():
    """Singleton lazy — charge le modèle une seule fois par process. Retourne
    None si le chargement échoue (mémorisé pour ne pas retenter à chaque appel)."""
    global _cross_encoder, _load_failed
    if _cross_encoder is not None or _load_failed:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder(RERANKER_MODEL_NAME)
    except Exception as e:
        logger.warning(f"Reranker : échec de chargement du modèle ({e}), repli sur l'ordre RRF")
        _load_failed = True
        _cross_encoder = None
    return _cross_encoder


def rerank(query: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Trie `docs` par pertinence sémantique réelle (cross-encoder) au lieu du
    score RRF/heuristique. Retourne une NOUVELLE liste de nouveaux dicts (ne
    mute jamais `docs` ni ses éléments). En cas d'échec à n'importe quelle
    étape (désactivé, modèle non chargeable, erreur d'inférence), retourne
    `docs` inchangé (mêmes objets, même ordre) — jamais d'exception propagée.
    """
    if not docs or not _rerank_enabled():
        return docs

    model = _get_cross_encoder()
    if model is None:
        return docs

    try:
        start = time.monotonic()
        pairs = [(query, d.get("text", "")) for d in docs]
        scores = model.predict(pairs)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(f"Reranker : {len(docs)} candidats en {elapsed_ms:.0f}ms")
        reranked = []
        for doc, score in zip(docs, scores):
            new_doc = dict(doc)
            new_doc["score"] = float(score)
            reranked.append(new_doc)
        reranked.sort(key=lambda d: d["score"], reverse=True)
        return reranked
    except Exception as e:
        logger.warning(f"Reranker : échec à l'inférence ({e}), repli sur l'ordre d'entrée")
        return docs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/test_reranker.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/rag/reranker.py tests/rag/test_reranker.py
git commit -m "feat(rag): add standalone cross-encoder reranker module"
```

---

### Task 2: Wire the reranker into `MISPLRetriever.query()`, remove dead heuristic boosts

**Files:**
- Modify: `src/rag/retriever.py` (imports section near top; `_MISPL_PURE_CATEGORIES` constant removed; `MISPLRetriever.query()` method body)
- Test: `tests/rag/test_retriever_query_reranking.py`

**Interfaces:**
- Consumes: `rerank` from Task 1 (`from src.rag.reranker import rerank`).
- Produces: `MISPLRetriever.query()` now returns docs whose final ordering (beyond the pinned `exact_match` docs) comes from the cross-encoder, not from RRF score × heuristic multipliers. `category_filter` parameter is REMOVED from `query()`'s signature (it was unused by every caller in the codebase — confirmed by `grep -rn "category_filter"` finding zero call sites outside its own definition — and its only use, a hard category exclusion, is being replaced by Task 3's non-exclusionary widening). A new module-level constant `RERANK_POOL_SIZE = 20` is added near `RRF_K` (top of file). Task 3 will add an `active_skills` parameter to `query()` — that is not part of this task.

- [ ] **Step 1: Write the failing test**

Create `tests/rag/test_retriever_query_reranking.py`:

```python
"""Tests d'intégration du reranking cross-encoder dans MISPLRetriever.query()."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import src.rag.retriever as retriever_mod
from src.rag.retriever import MISPLRetriever


def _make_retriever_with_fake_state(dense_docs, bm25_docs, known_functions=frozenset()):
    """Construit un MISPLRetriever sans passer par __init__ (évite de charger
    un vrai ChromaDB/BM25) et remplace les méthodes de recherche internes par
    des doublures déterministes."""
    retriever = object.__new__(MISPLRetriever)
    retriever.top_k = 6

    class _FakeState:
        pass

    retriever._state = _FakeState()
    retriever._state.known_functions = set(known_functions)
    retriever._state.collection = MagicMock()
    retriever._state.collection.count.return_value = 1000

    retriever._dense_search = lambda query, n: list(dense_docs)
    retriever._bm25_search = lambda query, n: list(bm25_docs)
    retriever._exact_match_search = lambda fn: []
    retriever._detect_function_name = lambda q: None
    return retriever


class TestQueryUsesReranker:
    def test_final_order_follows_reranker_not_rrf_score(self, monkeypatch):
        # Le doc "b" a un meilleur score RRF (rang dense 0) mais le reranker
        # (mocké) le classe après "a" — le résultat final doit suivre le reranker.
        docs = [
            {"id": "b", "text": "peu pertinent", "score": 0.0, "category": "misc",
             "function_name": "", "has_examples": False},
            {"id": "a", "text": "tres pertinent", "score": 0.0, "category": "misc",
             "function_name": "", "has_examples": False},
        ]
        retriever = _make_retriever_with_fake_state(dense_docs=docs, bm25_docs=[])

        def _fake_rerank(query, pool):
            # Inverse l'ordre reçu et assigne un score cohérent avec ce nouvel ordre.
            reversed_pool = list(reversed(pool))
            for i, d in enumerate(reversed_pool):
                d = dict(d)
                d["score"] = float(len(reversed_pool) - i)
                reversed_pool[i] = d
            return reversed_pool

        monkeypatch.setattr(retriever_mod, "rerank", _fake_rerank)
        result = retriever.query("une question", top_k=2)
        assert [d["id"] for d in result] == ["a", "b"]

    def test_category_filter_param_removed(self):
        import inspect

        sig = inspect.signature(MISPLRetriever.query)
        assert "category_filter" not in sig.parameters

    def test_pool_size_constant_defined(self):
        assert retriever_mod.RERANK_POOL_SIZE >= 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/test_retriever_query_reranking.py -v`
Expected: FAIL — either `AttributeError: module 'src.rag.retriever' has no attribute 'rerank'` or `AssertionError` on the ordering/constant checks (the current heuristic-boost code doesn't call any `rerank` function and has no `RERANK_POOL_SIZE`).

- [ ] **Step 3: Implement the change in `src/rag/retriever.py`**

Add this import near the top of the file, alongside the existing imports (after `from rank_bm25 import BM25Okapi`):

```python
from src.rag.reranker import rerank
```

Near the `RRF_K = 25` constant, add:

```python
# Taille du pool de candidats envoyés au reranker cross-encoder après RRF
# (avant troncature au top_k final) — plus large que top_k pour laisser le
# reranker choisir parmi un ensemble représentatif, pas seulement les k
# premiers du score RRF brut.
RERANK_POOL_SIZE = 20
```

Remove the `_MISPL_PURE_CATEGORIES` constant entirely (it is a no-op today — none of its whitelisted values match any real `category`/`domaine` value in the corpus — and the reranker replaces the boost that used it).

In `MISPLRetriever.query()`, remove `category_filter: str | None = None` from the method signature and its docstring `Args:` line. Replace the entire block from `# Assembler résultats RRF` through the `return _reorder_for_llm(combined)` line (i.e. everything after the `bm25_docs = self._bm25_search(...)` line) with:

```python
        # RRF
        dense_ids = [d["id"] for d in dense_docs]
        bm25_ids = [d["id"] for d in bm25_docs]
        rrf_ranked = _reciprocal_rank_fusion(dense_ids, bm25_ids)

        # Construire dict id → doc pour lookup rapide
        all_docs_map: dict[str, dict[str, Any]] = {}
        for d in dense_docs + bm25_docs:
            if d["id"] not in all_docs_map:
                all_docs_map[d["id"]] = d

        # Assembler pool de candidats RRF élargi (pour laisser le reranker
        # cross-encoder trancher parmi un choix plus large que k)
        pool_size = max(k * 3, RERANK_POOL_SIZE)
        rrf_docs: list[dict[str, Any]] = []
        seen_ids: set[str] = set(d["id"] for d in exact_docs)
        for doc_id, rrf_score in rrf_ranked:
            if doc_id in seen_ids:
                continue
            if doc_id in all_docs_map:
                doc = all_docs_map[doc_id].copy()
                doc["score"] = rrf_score
                doc["exact_match"] = False
                rrf_docs.append(doc)
                seen_ids.add(doc_id)
            if len(rrf_docs) >= pool_size:
                break

        # Reranking cross-encoder — score de pertinence sémantique réel,
        # remplace les anciens boosts heuristiques arbitraires post-RRF.
        rrf_docs = rerank(question, rrf_docs)

        # Fusionner : exact_docs en tête (score 1.0, non passés au reranker),
        # puis les candidats rerankés, tronqué au top_k final.
        combined = exact_docs + rrf_docs
        combined = combined[:k]

        # Reorder anti-Lost-in-the-Middle
        return _reorder_for_llm(combined)
```

Note the `dense_ids`/`bm25_ids`/`rrf_ranked`/`all_docs_map` lines above already exist in the current file immediately before the block you're replacing — this reproduces them unchanged so the replacement is a clean drop-in for everything from `# RRF` onward; do not duplicate them if your diff tool shows them as already present just above your edit point.

- [ ] **Step 4: Run test to verify it passes**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/test_retriever_query_reranking.py -v`
Expected: 3 passed

- [ ] **Step 5: Run the reranker tests from Task 1 too (regression check)**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/ -v`
Expected: 9 passed (6 from Task 1 + 3 from this task)

- [ ] **Step 6: Commit**

```bash
git add src/rag/retriever.py tests/rag/test_retriever_query_reranking.py
git commit -m "feat(rag): rerank RRF candidates with cross-encoder, drop dead heuristic boosts"
```

---

### Task 3: Skill-based category inclusion guarantee

**Files:**
- Modify: `src/rag/retriever.py` (`SKILL_CATEGORY_BOOST` constant; `MISPLRetriever._category_widen` new method; `MISPLRetriever.query()` — add `active_skills` param and widening call)
- Modify: `src/agent/mispl_agent.py` (`ask_mispl` — compute `active_skills` before retrieval, pass it to `retriever.query()`)
- Test: `tests/rag/test_retriever_categories.py`

**Interfaces:**
- Consumes: `MISPLRetriever.query()` from Task 2 (the version with `RERANK_POOL_SIZE`/`rerank` wired in, no `category_filter`).
- Produces: `MISPLRetriever.query(question, top_k=None, active_skills=None)` — new optional third parameter, a list of skill names like `["mispl-core", "mispl-erd-safety"]` (exactly the values already produced by `SKILL_PROFILES` in `src/agent/prompt_builder.py` and returned by `_detect_skill_profile` in `src/agent/mispl_agent.py`). `MISPLRetriever._category_widen(relevant_categories: set[str], exclude_ids: set[str], limit: int) -> list[dict[str, Any]]` — new private method, later tasks do not call it directly.

- [ ] **Step 1: Write the failing tests**

Create `tests/rag/test_retriever_categories.py`:

```python
"""Tests du boost d'inclusion par catégorie (SKILL_CATEGORY_BOOST) sur le retriever."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.rag.retriever import SKILL_CATEGORY_BOOST, MISPLRetriever


class TestSkillCategoryBoostMapping:
    def test_all_known_skills_have_a_mapping(self):
        for skill in ["mispl-core", "mispl-reports", "mispl-erd-safety", "mispl-performance"]:
            assert skill in SKILL_CATEGORY_BOOST
            assert len(SKILL_CATEGORY_BOOST[skill]) > 0

    def test_mapping_values_are_string_sets(self):
        for categories in SKILL_CATEGORY_BOOST.values():
            assert isinstance(categories, set)
            assert all(isinstance(c, str) for c in categories)


class _FakeCollection:
    def __init__(self, rows):
        self._rows = rows  # list of (id, text, metadata dict)

    def get(self, where=None, limit=None, include=None):
        allowed = set(where["category"]["$in"]) if where else None
        matched = [r for r in self._rows if allowed is None or r[2].get("category") in allowed]
        matched = matched[: limit or len(matched)]
        return {
            "ids": [r[0] for r in matched],
            "documents": [r[1] for r in matched],
            "metadatas": [r[2] for r in matched],
        }


def _make_bare_retriever():
    retriever = object.__new__(MISPLRetriever)
    retriever.top_k = 6

    class _FakeState:
        pass

    retriever._state = _FakeState()
    return retriever


class TestCategoryWiden:
    def test_widen_returns_docs_from_relevant_categories_only(self):
        retriever = _make_bare_retriever()
        retriever._state.collection = _FakeCollection([
            ("a", "texte table order", {"category": "table_order"}),
            ("b", "texte string", {"category": "manipulation_chaines"}),
        ])
        docs = retriever._category_widen({"table_order"}, exclude_ids=set(), limit=10)
        assert [d["id"] for d in docs] == ["a"]
        assert docs[0]["score"] == 0.0

    def test_widen_excludes_already_seen_ids(self):
        retriever = _make_bare_retriever()
        retriever._state.collection = _FakeCollection([
            ("a", "texte table order", {"category": "table_order"}),
        ])
        docs = retriever._category_widen({"table_order"}, exclude_ids={"a"}, limit=10)
        assert docs == []

    def test_widen_returns_empty_for_no_relevant_categories(self):
        retriever = _make_bare_retriever()
        retriever._state.collection = _FakeCollection([("a", "x", {"category": "table_order"})])
        assert retriever._category_widen(set(), exclude_ids=set(), limit=10) == []

    def test_widen_falls_back_to_empty_on_collection_error(self):
        retriever = _make_bare_retriever()

        class _RaisingCollection:
            def get(self, **kwargs):
                raise RuntimeError("boom")

        retriever._state.collection = _RaisingCollection()
        assert retriever._category_widen({"table_order"}, exclude_ids=set(), limit=10) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/test_retriever_categories.py -v`
Expected: FAIL — `ImportError: cannot import name 'SKILL_CATEGORY_BOOST'`

- [ ] **Step 3: Implement in `src/rag/retriever.py`**

Add near the top of the file, after the `RERANK_POOL_SIZE` constant added in Task 2:

```python
# Mapping skill (nom de fichier .md sous .claude/skills/) → catégories de la
# base pertinentes pour ce skill. Utilisé pour GARANTIR l'inclusion de chunks
# de ces catégories dans le pool envoyé au reranker (jamais pour exclure —
# cf. spec docs/superpowers/specs/2026-08-25-rag-metadata-filtering-reranking-design.md
# section A). Estimation sémantique à partir des vraies valeurs de `category`
# (frontmatter `domaine`) présentes dans rag_knowledge_base/ — ajustable ici
# sans toucher à la logique de retrieval.
SKILL_CATEGORY_BOOST: dict[str, set[str]] = {
    "mispl-core": {
        "structure_programme", "manipulation_chaines", "date_heure",
        "calculs_mathematiques", "conversion_types", "patterns_courants",
        "patterns_complexes", "variables_partagees", "contexte_execution",
        "interactions_utilisateur", "fonctions_diverses",
    },
    "mispl-reports": {
        "table_result", "table_result_extended", "result_missing",
        "table_correspondent", "correspondent_extended", "tables_diverses",
    },
    "mispl-erd-safety": {
        "table_order", "table_order_extended", "table_order_navigation",
        "order_missing", "table_object", "table_object_extended",
        "object_missing", "table_specimen", "table_specimen_extended",
        "specimen_missing", "table_action", "table_microbiology",
        "microbiology_missing", "table_blood_transfusion",
        "table_pathology_nonconformity", "table_person_site",
        "site_extended", "person_extended", "genetique_moleculaire",
        "tables_diverses",
    },
    "mispl-performance": {
        "reflexe_analytique", "validation_automatique_garde",
        "patterns_complexes",
    },
}
```

Add this new method to `MISPLRetriever`, placed right before the `# ── Query principal ──` section comment (i.e. just before the `def query(` method):

```python
    # ── Boost d'inclusion par catégorie (skill actif) ──────────────────────────

    def _category_widen(
        self, relevant_categories: set[str], exclude_ids: set[str], limit: int
    ) -> list[dict[str, Any]]:
        """Récupère jusqu'à `limit` chunks des catégories pertinentes pour le(s)
        skill(s) actif(s), même s'ils n'ont pas été remontés par la recherche
        dense/BM25 — garantit leur présence dans le pool envoyé au reranker sans
        jamais retirer de candidat déjà sélectionné. Score neutre (0.0) : c'est
        le reranker cross-encoder qui tranche leur pertinence réelle."""
        if not relevant_categories:
            return []
        try:
            results = self._state.collection.get(
                where={"category": {"$in": sorted(relevant_categories)}},
                limit=limit,
                include=["documents", "metadatas"],
            )
        except Exception:
            return []
        docs = []
        ids = results.get("ids", [])
        for i, doc_id in enumerate(ids):
            if doc_id in exclude_ids:
                continue
            meta = results["metadatas"][i]
            docs.append({
                "id": doc_id,
                "text": results["documents"][i],
                "score": 0.0,
                "exact_match": False,
                **{k: meta.get(k, "") for k in [
                    "source", "source_file", "section", "doc_title", "function_name",
                    "return_type", "signature", "category", "priority",
                    "has_examples", "is_table_independent",
                ]},
            })
        return docs
```

In `query()`'s signature, add the new parameter (after `top_k`, before the removed `category_filter` slot):

```python
    def query(
        self,
        question: str,
        top_k: int | None = None,
        active_skills: list[str] | None = None,
    ) -> list[dict[str, Any]]:
```

Also update the docstring's `Args:` block to add `active_skills: Skills actifs (ex. ["mispl-core"]) — élargit le pool de candidats avec des chunks des catégories associées, sans jamais en exclure d'autres.`

In the method body, insert this block right after the `rrf_docs`-building loop (i.e. right after the `if len(rrf_docs) >= pool_size: break` loop from Task 2, and BEFORE the `rrf_docs = rerank(question, rrf_docs)` line):

```python
        # Garantie d'inclusion par catégorie selon les skills actifs — n'exclut
        # jamais de candidat existant, ajoute seulement des candidats manquants
        # avant le reranking, qui tranchera leur pertinence réelle.
        relevant_categories: set[str] = set()
        for skill in active_skills or []:
            relevant_categories |= SKILL_CATEGORY_BOOST.get(skill, set())
        if relevant_categories:
            widened = self._category_widen(relevant_categories, exclude_ids=seen_ids, limit=4)
            for doc in widened:
                if doc["id"] not in seen_ids:
                    rrf_docs.append(doc)
                    seen_ids.add(doc["id"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/test_retriever_categories.py -v`
Expected: 7 passed

- [ ] **Step 5: Wire `active_skills` through `ask_mispl` in `src/agent/mispl_agent.py`**

Find this block (currently around line 455-464):

```python
    # 1. Retrieval hybride BM25 + dense
    retriever = get_retriever(use_openai=use_openai_embeddings, top_k=effective_top_k)
    docs = retriever.query(question)
    context = retriever.format_context(docs)

    # 2. Prompt système depuis Skills Markdown
    active_skills = skill_profile or _detect_skill_profile(question)
    system_prompt = build_system_prompt(active_skills=active_skills, access_mode=access_mode)
```

Replace with:

```python
    # 1. Skills actifs déterminés AVANT le retrieval — sert de signal
    # d'inclusion par catégorie pour le retriever (SKILL_CATEGORY_BOOST), en
    # plus de son usage existant pour le prompt système ci-dessous.
    active_skills = skill_profile or _detect_skill_profile(question)

    # 2. Retrieval hybride BM25 + dense
    retriever = get_retriever(use_openai=use_openai_embeddings, top_k=effective_top_k)
    docs = retriever.query(question, active_skills=active_skills)
    context = retriever.format_context(docs)

    # 3. Prompt système depuis Skills Markdown
    system_prompt = build_system_prompt(active_skills=active_skills, access_mode=access_mode)
```

- [ ] **Step 6: Run the full RAG + agent test suites to confirm no regression**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/rag/ tests/agent/ -v`
Expected: all pass (16 in `tests/rag/` + existing `tests/agent/` suite, 0 failures)

- [ ] **Step 7: Commit**

```bash
git add src/rag/retriever.py src/agent/mispl_agent.py tests/rag/test_retriever_categories.py
git commit -m "feat(rag): guarantee skill-relevant categories reach the reranker pool"
```

---

### Task 4: Cache key — new retrieval pipeline version axis

**Files:**
- Modify: `src/rag/retriever.py` (new `RETRIEVAL_PIPELINE_VERSION` constant)
- Modify: `src/agent/mispl_agent.py` (import it; fold into `_cache_key`)
- Test: `tests/agent/test_cache.py` (extend `TestCacheKeyIsolation`)

**Interfaces:**
- Consumes: nothing new from earlier tasks (independent of Tasks 1-3's internals, only needs to exist as a constant name).
- Produces: `src.rag.retriever.RETRIEVAL_PIPELINE_VERSION: str` — a version string later work must bump whenever `_INTENT_EXPANSIONS`, `SKILL_CATEGORY_BOOST`, or the reranker model choice changes, so stale cached responses are never served.

- [ ] **Step 1: Write the failing test**

Add this test method to the existing `TestCacheKeyIsolation` class in `tests/agent/test_cache.py` (add it as a new method inside that class, alongside `test_different_access_mode_different_key` etc. — do not create a new class):

```python
    def test_different_pipeline_version_different_key(self, monkeypatch):
        monkeypatch.setattr(agent_mod, "RETRIEVAL_PIPELINE_VERSION", "r1")
        key_a = self._key()
        monkeypatch.setattr(agent_mod, "RETRIEVAL_PIPELINE_VERSION", "r2")
        key_b = self._key()
        assert key_a != key_b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/agent/test_cache.py::TestCacheKeyIsolation::test_different_pipeline_version_different_key -v`
Expected: FAIL with `AttributeError: <module 'src.agent.mispl_agent'> does not have the attribute 'RETRIEVAL_PIPELINE_VERSION'`

- [ ] **Step 3: Add the constant in `src/rag/retriever.py`**

Near the top of the file, alongside `RRF_K`/`RERANK_POOL_SIZE`:

```python
# Version du pipeline de retrieval (expansion de requête + boost d'inclusion
# par catégorie + modèle de reranking). À incrémenter dès que l'un de ces
# trois éléments change, pour invalider le cache réponse de mispl_agent.py
# (cf. RETRIEVAL_PIPELINE_VERSION dans src/agent/mispl_agent.py::_cache_key).
RETRIEVAL_PIPELINE_VERSION = "r1"
```

- [ ] **Step 4: Wire it into `_cache_key` in `src/agent/mispl_agent.py`**

Update the import line (currently `from src.rag.retriever import get_retriever`) to:

```python
from src.rag.retriever import get_retriever, RETRIEVAL_PIPELINE_VERSION
```

Replace the `_cache_key` function body:

```python
def _cache_key(
    question: str,
    model: str,
    top_k: int,
    skill_profile: list[str] | None,
    access_mode: str,
    conversation_history: list[dict] | None,
) -> str:
    # skill_profile et access_mode changent le prompt système ; l'historique
    # change le contexte envoyé au LLM → tous doivent entrer dans la clé,
    # sinon une réponse mise en cache dans un contexte fuite vers un autre
    # (ex: réponse DSI servie telle quelle à un technicien).
    skills_part = ",".join(sorted(skill_profile)) if skill_profile else "auto"
    hist_part = hashlib.sha256(
        json.dumps(conversation_history or [], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:12]
    raw = f"{CACHE_VERSION}|{question}|{model}|{top_k}|{skills_part}|{access_mode}|{hist_part}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

With:

```python
def _cache_key(
    question: str,
    model: str,
    top_k: int,
    skill_profile: list[str] | None,
    access_mode: str,
    conversation_history: list[dict] | None,
) -> str:
    # skill_profile et access_mode changent le prompt système ; l'historique
    # change le contexte envoyé au LLM → tous doivent entrer dans la clé,
    # sinon une réponse mise en cache dans un contexte fuite vers un autre
    # (ex: réponse DSI servie telle quelle à un technicien). RETRIEVAL_PIPELINE_VERSION
    # couvre la table d'expansion de requête, le boost d'inclusion par catégorie et
    # le modèle de reranking cross-encoder — à incrémenter si l'un de ces trois
    # change, indépendamment de CACHE_VERSION ci-dessus (cf. src/rag/retriever.py).
    skills_part = ",".join(sorted(skill_profile)) if skill_profile else "auto"
    hist_part = hashlib.sha256(
        json.dumps(conversation_history or [], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:12]
    raw = (
        f"{CACHE_VERSION}|{RETRIEVAL_PIPELINE_VERSION}|{question}|{model}|{top_k}|"
        f"{skills_part}|{access_mode}|{hist_part}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/agent/test_cache.py -v`
Expected: all pass (existing `TestCacheKeyIsolation`/`TestCacheGetRobustness`/`TestCachePurge` tests plus the new one)

- [ ] **Step 6: Run the full backend suite to confirm no regression anywhere**

Run: `../../../.venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/mispl_examples`
Expected: all pass, 0 failures (this is the first point in the plan where the full suite — not just `tests/rag/`/`tests/agent/` — should be checked, since `_cache_key`'s signature/behavior touches code exercised by `tests/api/test_chat_routes.py` too via `ask_mispl`)

- [ ] **Step 7: Commit**

```bash
git add src/rag/retriever.py src/agent/mispl_agent.py tests/agent/test_cache.py
git commit -m "fix(rag): fold retrieval-pipeline version into the response cache key"
```

---

### Task 5: Fix stale `CLAUDE.md` documentation

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: nothing from earlier tasks — purely descriptive text, independent of the code changes' internals (though it should describe the end state Tasks 1-4 produced).
- Produces: nothing consumed by later tasks or code — this is a terminal, standalone documentation fix.

- [ ] **Step 1: Read the current file**

Read `CLAUDE.md` in full first to confirm it still matches what's shown below (no other task in this plan touches it, but confirm nothing else changed it out of band).

- [ ] **Step 2: Apply the fixes**

Replace this block (lines 7-11 currently):

```markdown
## Stack
- Python 3.10+, LangChain / LlamaIndex, ChromaDB (vectorstore local)
- Modèle LLM : Claude API (claude-sonnet-4-6) ou modèle local (Ollama/Mistral)
- Embedding : text-embedding-3-small (OpenAI) ou nomic-embed-text (local)
- Documentation source : `french/` — manuel HTML GLIMS complet
```

With:

```markdown
## Stack
- Python 3.10+, ChromaDB (vectorstore local) + rank_bm25 (recherche lexicale) + Reciprocal Rank Fusion
- Modèle LLM : modèles gratuits OpenRouter (cf. `FREE_MODELS` dans `src/agent/mispl_agent.py`)
- Embedding : `sentence-transformers` local (`paraphrase-multilingual-MiniLM-L12-v2`) par défaut, OpenAI `text-embedding-3-small` en option (`use_openai_embeddings=True`)
- Reranking : cross-encoder multilingue (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, via `sentence-transformers`) sur le pool de candidats post-RRF
- Documentation source : `rag_knowledge_base/` — fiches Markdown (format Clean Room), chunkées par section H2
```

Replace this line in the "Repository map" section:

```markdown
- `french/` — documentation GLIMS source (HTML, ne pas modifier)
```

With:

```markdown
- `rag_knowledge_base/` — fiches source RAG (Markdown, ne pas modifier sans repasser par `src/rag/build_vectorstore.py`)
```

Leave every other section of `CLAUDE.md` (Règles absolues Anti-Hallucination, Format de réponse, Types de données MISPL, Structures de contrôle MISPL, ELN/Contraintes lab) completely unchanged — none of it is affected by this plan.

- [ ] **Step 3: Verify**

Run: `grep -n "french/\|LangChain\|LlamaIndex\|nomic-embed\|text-embedding-3-small (OpenAI) ou" CLAUDE.md`
Expected: no output (all stale references removed) — the one legitimate remaining mention of `text-embedding-3-small` (as the OpenAI option, not the default) is fine and expected.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: align CLAUDE.md with the real v3 RAG pipeline (Markdown corpus, sentence-transformers, cross-encoder reranking)"
```

---

## Post-plan verification (final task, run by whoever executes the last step)

After all 5 tasks are committed, run the complete verification sweep before considering this plan done:

```bash
../../../.venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/mispl_examples
../../../.venv/Scripts/python.exe -m pytest tests/mispl_examples/ -q
```

Both must show 0 failures (the second command may show the pre-existing, unrelated `TestRAGRetrieval` suite passing against the real vectorstore — this plan does not modify that file, but it's worth confirming the reranker/category-widening changes don't regress real-corpus retrieval quality, since that suite is the only place this plan's changes get exercised against real data end-to-end).
