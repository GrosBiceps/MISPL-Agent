"""Test final complet du pipeline."""
import sys
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")
from src.rag.retriever import _RetrieverState, get_retriever, _tokenize, _enrich_bm25_text

# Invalider le singleton pour forcer rechargement avec synonymes
_RetrieverState.invalidate()
r = get_retriever()

tests = [
    "Substr",
    "extraire une partie d une chaine de caracteres",
    "date du jour",
    "GetSiteAttribute",
    "convertir entier en texte",
    "arrondir un nombre decimal",
    "journal audit log",
    "longueur d une chaine",
    "utilisateur connecte",
]

for q in tests:
    docs = r.query(q)
    top3 = [(d.get("function_name","-"), round(d.get("score",0),3), d.get("exact_match",False))
            for d in docs[:3]]
    print(f"'{q[:45]:45s}' -> {top3}")

# Vérifier que Substr est dans le top3 pour la requête sémantique
print()
docs = r.query("extraire une partie d une chaine de caracteres")
fns = [d.get("function_name","") for d in docs[:6]]
print(f"Top-6 fns pour sous-chaine: {fns}")
print(f"Substr present: {'Substr' in fns}")

# Vérifier BM25 enrichi sur Substr
state = _RetrieverState.get(False)
# Trouver le chunk Substr
substr_chunk = next((c for c in state.bm25_chunks if c.get("function_name") == "Substr"), None)
if substr_chunk:
    enriched = _enrich_bm25_text(substr_chunk)
    print(f"\nTexte enrichi Substr (100 chars): {enriched[:200]}")
    tokens_q = _tokenize("extraire une partie d une chaine de caracteres")
    print(f"Tokens query: {tokens_q}")
    # Score BM25 pour Substr
    scores = state.bm25.get_scores(tokens_q)
    chunk_idx = state.bm25_chunks.index(substr_chunk)
    print(f"BM25 score Substr: {scores[chunk_idx]:.3f}")
    top10 = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:10]
    print(f"Top-10 BM25 fns: {[state.bm25_chunks[i].get('function_name','-')[:15] for i in top10]}")
