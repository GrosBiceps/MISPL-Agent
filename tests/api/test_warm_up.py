"""Préchargement du RAG au démarrage de l'API (api.main.warm_up_rag)."""

import src.rag.retriever as retriever_module
from api.main import warm_up_rag


class _FakeRetriever:
    def __init__(self, calls):
        self.calls = calls

    def query(self, question, active_skills=None):
        self.calls.append((question, active_skills))
        return []


def test_warm_up_loads_retriever_and_runs_one_query(monkeypatch):
    calls = []
    monkeypatch.delenv("MISPL_PRELOAD_RETRIEVER", raising=False)
    monkeypatch.setattr(retriever_module, "get_retriever", lambda **kw: _FakeRetriever(calls))
    assert warm_up_rag() is True
    assert len(calls) == 1


def test_warm_up_can_be_disabled(monkeypatch):
    monkeypatch.setenv("MISPL_PRELOAD_RETRIEVER", "false")

    def boom(**kw):
        raise AssertionError("get_retriever ne doit pas être appelé")

    monkeypatch.setattr(retriever_module, "get_retriever", boom)
    assert warm_up_rag() is False


def test_warm_up_failure_never_raises(monkeypatch):
    monkeypatch.delenv("MISPL_PRELOAD_RETRIEVER", raising=False)

    def missing_index(**kw):
        raise FileNotFoundError("Corpus BM25 absent")

    monkeypatch.setattr(retriever_module, "get_retriever", missing_index)
    assert warm_up_rag() is False
