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
    def test_blends_reranker_rank_with_original_rrf_rank(self, monkeypatch):
        """La fusion RRF entre le rang pré-reranking (dense+BM25) et le rang
        post-reranking doit éviter qu'un jugement isolé du cross-encoder ne
        fasse sortir du top_k un candidat pourtant très bien classé par la
        recherche hybride d'origine — régression constatée en vérification
        finale sur AddLogEntry (#1 BM25, mais hors top-5 par le cross-encoder
        seul sur ce corpus technique français)."""
        docs = [
            {"id": "target", "text": "fort en RRF, modere au reranking", "score": 0.0,
             "category": "misc", "function_name": "", "has_examples": False},
            {"id": "b", "text": "fort partout", "score": 0.0, "category": "misc",
             "function_name": "", "has_examples": False},
            {"id": "c", "text": "moyen", "score": 0.0, "category": "misc",
             "function_name": "", "has_examples": False},
            {"id": "d", "text": "faible", "score": 0.0, "category": "misc",
             "function_name": "", "has_examples": False},
            {"id": "e", "text": "tres faible", "score": 0.0, "category": "misc",
             "function_name": "", "has_examples": False},
        ]
        # Pré-reranking (RRF sur dense seul ici) : target est #1.
        retriever = _make_retriever_with_fake_state(dense_docs=docs, bm25_docs=[])

        def _fake_rerank(query, pool):
            # Le reranker seul reléguerait "target" en 4e position sur 5.
            order = ["b", "c", "d", "target", "e"]
            by_id = {d["id"]: d for d in pool}
            return [by_id[doc_id] for doc_id in order]

        monkeypatch.setattr(retriever_mod, "rerank", _fake_rerank)
        result = retriever.query("une question", top_k=3)
        result_ids = [d["id"] for d in result]
        assert "target" in result_ids, (
            "le blending RRF doit garder 'target' dans le top_k malgre son "
            f"classement bas par le reranker seul (resultat: {result_ids})"
        )

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

    def test_reorder_uses_list_order_not_raw_score(self):
        """_reorder_for_llm ne doit JAMAIS re-trier par score — seul l'ordre
        de la liste d'entrée compte. Ici les scores sont délibérément dans
        l'ordre INVERSE de la position pour prouver qu'ils sont ignorés."""
        from src.rag.retriever import _reorder_for_llm

        docs = [
            {"id": "first", "score": 0.01},
            {"id": "second", "score": 0.5},
            {"id": "third", "score": 0.3},
            {"id": "fourth", "score": 0.99},
        ]
        result = _reorder_for_llm(docs)
        # Attendu : position 1 reste "first" (position 0 d'entrée), "second"
        # (position 1 d'entrée) passe en dernier, le reste garde son ordre —
        # peu importe que "fourth" ait le score le plus élevé.
        assert [d["id"] for d in result] == ["first", "third", "fourth", "second"]
