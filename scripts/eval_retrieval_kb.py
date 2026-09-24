"""Évaluation rapide de la fiabilité du retrieval sur l'index reconstruit.

1. Exact-match : chaque fonction connue interrogée par son nom -> la fonction attendue
   doit apparaître en top-1 / top-3 / top-5.
2. Sémantique : questions en français (sans nom de fonction) -> fonction attendue.

Usage : .venv/Scripts/python.exe scripts/eval_retrieval_kb.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.rag.retriever import get_retriever  # noqa: E402

SEMANTIC = [
    ("extraire une partie d'une chaîne de caractères", {"Substr"}),
    ("longueur d'une chaîne", {"Len"}),
    ("convertir une chaîne en minuscules", {"ToLower"}),
    ("remplacer un texte par un autre dans une chaîne", {"Replace"}),
    ("supprimer les espaces à gauche", {"Ltrim", "Strip"}),
    ("compléter une chaîne à gauche jusqu'à une longueur", {"Lpad"}),
    ("compléter une chaîne à droite", {"Rpad"}),
    ("position d'une sous-chaîne dans une chaîne", {"Index"}),
    ("tester si une chaîne correspond à un motif", {"Matches"}),
    ("code caractère d'une lettre", {"Ord"}),
    ("caractère correspondant à un code", {"Chr"}),
    ("valeur absolue d'un nombre", {"Abs", "Fabs"}),
    ("racine carrée", {"Sqrt"}),
    ("arrondir un nombre décimal", {"Round"}),
    ("tronquer la partie décimale", {"Truncate", "FractionalToInteger"}),
    ("logarithme en base 10", {"Log10"}),
    ("reste de la division de deux décimaux", {"Fmod"}),
    ("date du jour", {"Today"}),
    ("date et heure actuelles", {"Now"}),
    ("convertir une chaîne en date", {"StringToDate"}),
    ("convertir une date en texte", {"DateToString"}),
    ("convertir un entier en texte", {"IntegerToString"}),
    ("convertir un texte en entier", {"StringToInteger"}),
    ("convertir un texte en nombre décimal", {"StringToFractional"}),
    ("âge du patient en années", {"AgeInYears", "Age"}),
    ("date de naissance du patient", {"BirthDate"}),
    ("nombre d'années entre deux dates", {"DateDiffInYears"}),
    ("vérifier si un jour est férié", {"IsHoliday"}),
    ("utilisateur connecté", {"CurrentUser"}),
    ("envoyer un courriel", {"SendMail"}),
    ("afficher une question oui non à l'utilisateur", {"AskYesNo"}),
    ("demander une saisie de texte à l'utilisateur", {"AskString"}),
    ("écrire dans le journal", {"Log", "AddLogEntry"}),
    ("tester si une valeur est vide", {"IsEmpty"}),
    ("ajouter un commentaire interne", {"AddInternalComment"}),
    ("ajouter un commentaire externe", {"AddExternalComment"}),
    ("valider un résultat", {"Validate"}),
    ("annuler des résultats", {"CancelResults", "Cancel"}),
    ("résultat antérieur du patient", {"GetPriorResult", "HasPreviousResults"}),
    ("valeur de référence d'un résultat", {"ReferenceValue"}),
    ("lire un attribut", {"Attribute", "GetSiteAttribute"}),
    ("modifier un attribut", {"SetAttribute"}),
    ("nombre d'éléments d'une liste séparée", {"NumEntries"}),
    ("extraire un élément d'une liste séparée", {"Entry"}),
    ("trier une liste", {"Sort"}),
    ("échapper les caractères XML", {"XmlEscaped"}),
    ("nombre écrit en toutes lettres", {"NumberToStringInFull"}),
    ("heure de prélèvement", {"SamplingTime"}),
    ("ajouter une demande d'analyse", {"AddRequest"}),
    ("vérifier si une analyse est demandée", {"IsRequested"}),
]


def fn_of(doc):
    return (doc.get("function_name") or "").strip()


def rank_of(docs, expected):
    for i, d in enumerate(docs, 1):
        if fn_of(d) in expected:
            return i
    return None


def evaluate(pairs, r):
    ranks, misses = [], []
    for q, exp in pairs:
        docs = r.query(q)
        rk = rank_of(docs, exp)
        ranks.append(rk)
        if rk is None or rk > 3:
            misses.append({"query": q, "expected": sorted(exp), "rank": rk,
                           "top3": [fn_of(d) for d in docs[:3]]})
    n = len(ranks)
    hit = lambda k: sum(1 for x in ranks if x and x <= k) / n
    mrr = sum(1 / x for x in ranks if x) / n
    return {"n": n, "hit@1": round(hit(1), 3), "hit@3": round(hit(3), 3),
            "hit@5": round(hit(5), 3), "MRR": round(mrr, 3), "misses": misses}


def main():
    r = get_retriever()
    exact = (evaluate([(f, {f}) for f in sorted(r.known_functions)], r)
             if "--semantic-only" not in sys.argv else {"n": 0, "hit@1": 0, "hit@3": 0, "hit@5": 0, "MRR": 0, "misses": []})
    sem = evaluate(SEMANTIC, r)
    out = {"exact_match": exact, "semantic": sem}
    Path(ROOT / "outputs").mkdir(exist_ok=True)
    out_name = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "eval_retrieval_kb.json"
    (ROOT / "outputs" / out_name).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, res in out.items():
        print(f"{name:12s} n={res['n']:3d} hit@1={res['hit@1']:.3f} hit@3={res['hit@3']:.3f} "
              f"hit@5={res['hit@5']:.3f} MRR={res['MRR']:.3f} misses(>3)={len(res['misses'])}")
    print(json.dumps(sem["misses"], ensure_ascii=False))
    print("exact misses:", [m["query"] for m in exact["misses"]])


if __name__ == "__main__":
    main()
