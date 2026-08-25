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
