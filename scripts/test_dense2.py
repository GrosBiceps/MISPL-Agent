"""Debug RRF scores."""
import sys
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")
from src.rag.retriever import _RetrieverState, _tokenize, _enrich_bm25_text, _reciprocal_rank_fusion

state = _RetrieverState.get(False)
q = "extraire une partie d une chaine de caracteres"

# Dense
dense_res = state.collection.query(query_texts=[q], n_results=10,
    include=["documents", "metadatas", "distances"])
dense_ids = dense_res["ids"][0]
print("Dense top-5 IDs et distances:")
for i in range(5):
    fn = dense_res["metadatas"][0][i].get("function_name", "-")
    dist = dense_res["distances"][0][i]
    print(f"  {dense_ids[i][:8]} fn={fn:20s} dist={dist:.4f} sim={1-dist:.4f}")

# BM25
from src.rag.retriever import _tokenize, _enrich_bm25_text
tokens = _tokenize(q)
scores = state.bm25.get_scores(tokens)
top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:10]
bm25_ids = [state.bm25_chunks[i]["id"] for i in top_idx]
print("\nBM25 top-5:")
for i in range(5):
    idx = top_idx[i]
    c = state.bm25_chunks[idx]
    print(f"  {c['id'][:8]} fn={c.get('function_name','-'):20s} score={scores[idx]:.3f}")

# RRF
rrf = _reciprocal_rank_fusion(dense_ids, bm25_ids)
print("\nRRF top-5:")
all_map = {dense_res["ids"][0][i]: dense_res["metadatas"][0][i] for i in range(len(dense_ids))}
for chunk_id in bm25_ids:
    c = next((x for x in state.bm25_chunks if x["id"] == chunk_id), {})
    all_map[chunk_id] = c
for doc_id, rrf_score in rrf[:5]:
    meta = all_map.get(doc_id, {})
    fn = meta.get("function_name", "-")
    print(f"  {doc_id[:8]} fn={fn:20s} rrf={rrf_score:.4f}")
