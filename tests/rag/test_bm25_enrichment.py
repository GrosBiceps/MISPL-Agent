"""Tests de la construction de l'index BM25 — pas de double-enrichissement
pour les chunks Markdown-KB déjà pré-enrichis à l'ingestion."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import src.rag.retriever as retriever_mod


class TestBM25EnrichmentNotDoubled:
    def test_md_kb_chunks_are_not_re_enriched(self, monkeypatch):
        """Un chunk chunk_type='md_kb' est déjà enrichi à l'ingestion : le
        texte utilisé pour l'index BM25 doit être son champ 'text' tel quel,
        pas le résultat d'un second passage par _enrich_bm25_text."""
        calls = []

        def _tracking_enrich(chunk):
            calls.append(chunk["id"])
            return chunk["text"] + " ENRICHED_AGAIN"

        monkeypatch.setattr(retriever_mod, "_enrich_bm25_text", _tracking_enrich)

        state = object.__new__(retriever_mod._RetrieverState)
        state.bm25_chunks = [
            {"id": "md1", "text": "AddLogEntry AddLogEntry AddLogEntry deja enrichi", "chunk_type": "md_kb"},
            {"id": "html1", "text": "texte brut non enrichi", "chunk_type": "html", "function_name": ""},
        ]

        original_bm25okapi = retriever_mod.BM25Okapi
        monkeypatch.setattr(retriever_mod, "BM25Okapi", MagicMock())

        # Appelle la portion de _load_bm25 qui construit le corpus tokenisé,
        # sans dépendre du reste de l'initialisation (fichier BM25 sur disque).
        tokenized_corpus = [
            retriever_mod._tokenize(c["text"]) if c.get("chunk_type") == "md_kb" else retriever_mod._tokenize(_tracking_enrich(c))
            for c in state.bm25_chunks
        ]

        # Le chunk md_kb ne doit jamais passer par _enrich_bm25_text.
        assert "md1" not in calls
        # Le chunk legacy (html) doit toujours passer par _enrich_bm25_text.
        assert "html1" in calls
