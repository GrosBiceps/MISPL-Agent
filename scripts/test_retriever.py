import sys
sys.path.insert(0, r"C:\Users\Florian Travail\Documents\MISPL Agent\MISPL")
from src.rag.retriever import get_retriever

r = get_retriever()
print(f"Fonctions connues: {len(r.known_functions)}")
print(f"Exemples: {sorted(r.known_functions)[:15]}")
print()

tests = [
    ("Substr",                                   "exact-match"),
    ("extraire une partie d une chaine",         "semantique string"),
    ("date du jour en MISPL",                    "semantique datetime"),
    ("GetSiteAttribute",                         "exact-match misc"),
    ("convertir entier en texte",                "semantique conversion"),
    ("arrondir un nombre decimal",               "semantique math"),
]

for query, label in tests:
    docs = r.query(query)
    top = docs[0] if docs else {}
    fn = top.get("function_name", "-")
    sig = (top.get("signature") or "")[:50]
    score = top.get("score", 0)
    exact = "EXACT" if top.get("exact_match") else "     "
    print(f"[{exact}] {label:35s} -> fn={fn:25s} score={score:.3f}")
    if sig:
        print(f"         sig: {sig}")
