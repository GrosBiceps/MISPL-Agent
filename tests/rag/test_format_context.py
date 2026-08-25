"""Tests du formatage du contexte LLM — MISPLRetriever.format_context()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.rag.retriever import MISPLRetriever


def _make_bare_retriever():
    return object.__new__(MISPLRetriever)


class TestFormatContext:
    def test_divider_appears_between_each_document(self):
        retriever = _make_bare_retriever()
        docs = [
            {"id": "a", "text": "contenu du doc 1", "score": 0.9},
            {"id": "b", "text": "contenu du doc 2", "score": 0.8},
            {"id": "c", "text": "contenu du doc 3", "score": 0.7},
        ]
        result = retriever.format_context(docs)
        divider = "─" * 60
        # Le séparateur doit apparaître exactement 2 fois pour 3 documents
        # (entre 1-2 et entre 2-3), jamais avant le premier ni après le dernier.
        assert result.count(divider) == 2
        # Chaque bloc [Doc N] doit apparaître, dans l'ordre.
        assert result.index("[Doc 1]") < result.index("[Doc 2]") < result.index("[Doc 3]")

    def test_single_document_has_no_divider(self):
        retriever = _make_bare_retriever()
        docs = [{"id": "a", "text": "seul contenu", "score": 0.9}]
        result = retriever.format_context(docs)
        assert "─" * 60 not in result
