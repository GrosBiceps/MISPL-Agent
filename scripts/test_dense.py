"""Debug dense search scores."""
import sys
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")
from src.rag.retriever import _RetrieverState, _tokenize
from rank_bm25 import BM25Okapi

state = _RetrieverState.get(use_openai=False)
print(f"ChromaDB collection count: {state.collection.count()}")
print(f"BM25 corpus size: {len(state.bm25_chunks)}")

# Test dense direct
q = "extraire une partie d une chaine de caracteres"
results = state.collection.query(
    query_texts=[q],
    n_results=5,
    include=["documents", "metadatas", "distances"],
)
print(f"\nDense top-5 pour '{q}':")
for i in range(len(results["ids"][0])):
    fn = results["metadatas"][0][i].get("function_name", "-")
    dist = results["distances"][0][i]
    sim = 1 - dist
    text_preview = results["documents"][0][i][:60]
    print(f"  fn={fn:20s} sim={sim:.3f} | {text_preview}")

# Test BM25 direct
print(f"\nBM25 top-5 pour '{q}':")
tokens = _tokenize(q)
scores = state.bm25.get_scores(tokens)
top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
for idx in top_idx:
    c = state.bm25_chunks[idx]
    print(f"  fn={c.get('function_name','-'):20s} score={scores[idx]:.3f} | {c['text'][:60]}")
