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
