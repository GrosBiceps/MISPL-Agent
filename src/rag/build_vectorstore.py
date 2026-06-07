"""
Pipeline d'ingestion MISPL v3 — Knowledge Base Markdown.

Entrée  : rag_knowledge_base/*.md (fiches concepts MISPL, format Clean Room)
Sortie  : ChromaDB + BM25 corpus JSON

Remplace l'ancienne logique HTML (v2). Délègue entièrement à
ingest_knowledge_base.py (parsing frontmatter YAML, chunking par section ##,
enrichissement BM25, ingestion additive ou rebuild).

Usage :
    python src/rag/build_vectorstore.py            # rebuild complet
    python src/rag/build_vectorstore.py --additive # ajout sans suppression
    python src/rag/build_vectorstore.py --dry-run  # stats sans écriture
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

# Chemins publics — conservés pour compatibilité avec retriever.py
VECTORSTORE_PATH = ROOT / "docs" / "chunks" / "vectorstore"
BM25_CORPUS_PATH = ROOT / "docs" / "chunks" / "bm25_corpus.json"
COLLECTION_NAME = "glims_mispl_docs"

# Chargé dynamiquement depuis le corpus BM25 après build — utilisé par retriever.py
KNOWN_FUNCTION_NAMES: set[str] = set()


def _load_known_functions() -> None:
    import json
    if BM25_CORPUS_PATH.exists():
        with open(BM25_CORPUS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        KNOWN_FUNCTION_NAMES.update(data.get("known_functions", []))


def build_vectorstore(
    use_openai: bool = False,
    rebuild: bool = True,
    model: str = "paraphrase-multilingual-MiniLM-L12-v2",
) -> None:
    """Point d'entrée principal — délègue à ingest_knowledge_base."""
    from src.rag.ingest_knowledge_base import ingest_knowledge_base
    ingest_knowledge_base(rebuild=rebuild, model=model)
    _load_known_functions()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build MISPL vectorstore v3 (Markdown KB)")
    parser.add_argument("--additive", action="store_true",
                        help="Ingestion additive sans supprimer la collection")
    parser.add_argument("--dry-run", action="store_true", help="Simuler sans écrire")
    parser.add_argument("--model", default="paraphrase-multilingual-MiniLM-L12-v2",
                        help="Modèle SentenceTransformer local")
    args = parser.parse_args()

    if args.dry_run:
        from src.rag.ingest_knowledge_base import ingest_knowledge_base
        ingest_knowledge_base(rebuild=False, dry_run=True, model=args.model)
    else:
        build_vectorstore(rebuild=not args.additive, model=args.model)
