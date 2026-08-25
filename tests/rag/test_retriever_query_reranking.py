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

    def test_exact_match_always_stays_first_even_with_high_reranker_scores(self, monkeypatch):
        """Régression pour le finding F1 : un score de reranker élevé (logit
        cross-encoder non borné, peut dépasser le score sentinelle 1.0 des
        exact-match) ne doit jamais faire passer un candidat reranké devant un
        résultat exact-match."""
        exact = [{"id": "exact-1", "text": "fonction exacte", "score": 1.0,
                  "exact_match": True, "category": "misc", "function_name": "Substr",
                  "has_examples": False}]
        pool_docs = [
            {"id": "z", "text": "tres pertinent selon le reranker", "score": 0.0,
             "category": "misc", "function_name": "", "has_examples": False},
        ]
        retriever = _make_retriever_with_fake_state(dense_docs=pool_docs, bm25_docs=[])
        retriever._exact_match_search = lambda fn: exact
        retriever._detect_function_name = lambda q: "Substr"

        def _high_score_rerank(query, pool):
            # Simule un logit cross-encoder très supérieur au score sentinelle 1.0
            return [{**d, "score": 9.87} for d in pool]

        monkeypatch.setattr(retriever_mod, "rerank", _high_score_rerank)
        result = retriever.query("Substr question", top_k=3)
        assert result[0]["id"] == "exact-1"
        assert result[0]["exact_match"] is True

    def test_category_filter_param_removed(self):
        import inspect

        sig = inspect.signature(MISPLRetriever.query)
        assert "category_filter" not in sig.parameters

    def test_pool_size_constant_defined(self):
        assert retriever_mod.RERANK_POOL_SIZE >= 15
