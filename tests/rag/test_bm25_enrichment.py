"""Tests de la construction de l'index BM25 — pas de double-enrichissement
pour les chunks Markdown-KB déjà pré-enrichis à l'ingestion."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.rag.retriever import _bm25_text_for_chunk


class TestBM25EnrichmentNotDoubled:
    def test_md_kb_chunk_text_used_as_is(self):
        """Un chunk chunk_type='md_kb' est déjà enrichi à l'ingestion : le
        texte utilisé pour l'index BM25 doit être son champ 'text' tel quel,
        sans repasser par _enrich_bm25_text."""
        chunk = {
            "id": "md1",
            "text": "AddLogEntry AddLogEntry AddLogEntry deja enrichi",
            "chunk_type": "md_kb",
            "function_name": "AddLogEntry",
        }
        assert _bm25_text_for_chunk(chunk) == chunk["text"]

    def test_legacy_html_chunk_still_gets_enriched(self):
        """Un chunk sans chunk_type='md_kb' (legacy HTML) doit toujours passer
        par _enrich_bm25_text — vérifié en confirmant que le nom de fonction
        est bien répété (signature du comportement d'enrichissement)."""
        chunk = {
            "id": "html1",
            "text": "texte brut non enrichi",
            "chunk_type": "html",
            "function_name": "Substr",
        }
        result = _bm25_text_for_chunk(chunk)
        assert result != chunk["text"]
        assert result.count("Substr") >= 3  # nom répété 3x par _enrich_bm25_text
