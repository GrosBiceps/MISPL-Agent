"""
Évaluation v2 — scripts CHU supplémentaires non couverts par eval_chu.py.
Source : fonctions_mispl.xlsx — propriété du service de biologie médicale.
Usage : python scripts/eval_chu_v2.py
"""
from __future__ import annotations
import io, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

TESTS_CHU_V2 = [
    {
        "id": "V2_01_alz_related_result",
        "description": "RelatedResult.Id + Mantissa + CascadeRequest (B_Ajout B_ALZ_RATIO_ABETA42_40)",
        "prompt": "Écris un script MISPL sur un résultat : si le résultat lié B_PROT_BETA_AMYL existe (Id <> ?) ET que le résultat courant a une valeur connue (Mantissa <> ?), déclencher B_ALZ_RATIO_ABETA42_40",
        "must_contain": ["LOGICAL PROGRAM", "RelatedResult", "Mantissa", "B_ALZ_RATIO_ABETA42_40"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson(", "Order.Result("],
        "expected_functions": ["RelatedResult", "Mantissa"],
    },
    {
        "id": "V2_02_objecttype_mantissa",
        "description": "ObjectType=person + Mantissa + AddRequest (B_Ajout B_COMM_ACTH)",
        "prompt": "Écris un script MISPL sur un résultat : vérifier avec EnumeratedToString que le type de l'objet est 'person', ET que le résultat a une valeur connue (Mantissa <> ?), puis ajouter la demande B_COMM_ACTH via Action.Order().AddRequest. Si l'objet n'est pas 'person', retourner NO.",
        "must_contain": ["LOGICAL PROGRAM", "EnumeratedToString", "person", "Mantissa", "AddRequest", "B_COMM_ACTH"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["EnumeratedToString", "Mantissa", "AddRequest"],
    },
    {
        "id": "V2_03_attribute_value_code",
        "description": "Attribute(Value) comparaison code entre accolades (B_Ajout B_BM_MICROSAT)",
        "prompt": "Écris un script MISPL sur un résultat : lire la valeur via .ResultAttribute('Value') ou .Result.Attribute('Value'), si cette valeur est égale à '{O}' alors déclencher B_BM_MICROSAT et appeler PostProcess",
        "must_contain": ["LOGICAL PROGRAM", "Attribute", "{O}", "B_BM_MICROSAT"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["Attribute"],
    },
    {
        "id": "V2_04_mantissa_only_cascade",
        "description": "Pattern simple Mantissa + CascadeRequest (B_Ajout B_COMM_AMH)",
        "prompt": "Écris un script MISPL sur un résultat : si le résultat courant a une valeur connue (Mantissa différent de ?), ajouter la demande B_COMM_AMH via Action.Order().AddRequest",
        "must_contain": ["LOGICAL PROGRAM", "Mantissa", "B_COMM_AMH"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["Mantissa"],
    },
    {
        "id": "V2_05_specimen_cancel",
        "description": "Cancel via Specimen.Result (B_BM_DSC_METH_2230)",
        "prompt": "Écris un script MISPL sur un résultat : annuler le résultat B_BM_METH_2230 trouvé sur le prélèvement courant (Result.Specimen.Result avec statuts 1 à 5) avec la raison 'discontinue' et le commentaire 'méthode 2226 remplace méthode 2230'",
        "must_contain": ["LOGICAL PROGRAM", "Specimen", "Result", "cancel", "discontinue"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["Specimen", "Cancel"],
    },
    {
        "id": "V2_06_suppr_doublon_rawvalue",
        "description": "Cancel conditionnel via RawValue (B_SUPPR_PROT_PLASMATIQUE)",
        "prompt": "Écris un script MISPL sur un résultat : si le résultat B_MOD_PRO_SG de statut 'Initial' à 'Validated' sur le dossier a un RawValue connu (non ?), alors l'annuler avec la raison 'Discontinue' et le commentaire 'Protéine Sérique réalisée discontinue la protéine plasmatique'",
        "must_contain": ["LOGICAL PROGRAM", "RawValue", "Cancel", "B_MOD_PRO_SG"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["RawValue", "Cancel"],
    },
    {
        "id": "V2_07_numericvalue_severite_double_seuil",
        "description": "NumericValue avec double seuil OR (B_Valid_Bio_Inf_10_ou_sup_300)",
        "prompt": "Écris un script MISPL sur un résultat : si la valeur numérique est inférieure ou égale à 10 OU supérieure ou égale à 300, fixer la sévérité manuelle à 11 (critique), sinon la remettre à 0 (normal)",
        "must_contain": ["LOGICAL PROGRAM", "NumericValue", "10", "300", "SetManualSeverity", "11"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["NumericValue", "SetManualSeverity"],
    },
    {
        "id": "V2_08_result_order_addrequest",
        "description": "Result.Order.AddRequest sans navigation Action (B_Ajout B_BM_LEGI)",
        "prompt": "Écris un script MISPL sur un résultat : ajouter directement la demande B_BM_LEGI sur le dossier via Result.Order.AddRequest (pas via Action.Order())",
        "must_contain": ["LOGICAL PROGRAM", "Order", "AddRequest", "B_BM_LEGI"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["AddRequest"],
    },
    {
        "id": "V2_09_non_conf_garde_lookupdate",
        "description": "Garde/férié avec LookUp + DateTimeToString + SetManualSeverity + validate (B_non_conf_en_garde)",
        "prompt": "Écris un script MISPL : déterminer si le dossier a été reçu en garde (week-end, férié ou hors plage 08h-18h en semaine) en utilisant LookUp sur DateTimeToString du ReceiptTime avec '%a', IsHoliday, et les plages horaires. Si en garde : SetManualSeverity(500) et validate(). Sinon : SetManualSeverity(0).",
        "must_contain": ["LOGICAL PROGRAM", "LookUp", "IsHoliday", "SetManualSeverity"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["LookUp", "IsHoliday", "SetManualSeverity"],
    },
    {
        "id": "V2_10_annulation_cascade_rawvalue",
        "description": "Annulation en cascade de plusieurs résultats (B_SUPPR_VR_CETO_LAC_PYR)",
        "prompt": "Écris un script MISPL sur un résultat : si B_VR_EPR_JEUNE1 (statut Initial à Validated) a un RawValue connu, alors annuler B_VR_PANEL_CETONEMIE ET B_VR_RAP_LAC_PYR chacun avec 'Discontinue' et un commentaire explicatif",
        "must_contain": ["LOGICAL PROGRAM", "RawValue", "Cancel", "B_VR_EPR_JEUNE1"],
        "must_not_contain_strict": ["GetValue(", "CreatePerson("],
        "expected_functions": ["RawValue", "Cancel"],
    },
]


def evaluate(test: dict, response: str) -> dict:
    errors, warnings = [], []
    resp_lower = response.lower()
    for term in test.get("must_contain", []):
        if term.lower() not in resp_lower:
            errors.append(f"MANQUANT: '{term}'")
    for term in test.get("must_not_contain_strict", []):
        if term in response:
            errors.append(f"INTERDIT: '{term}'")
    return {
        "pass": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "score": max(0, 10 - len(errors) * 3 - len(warnings)),
    }


def run_eval_v2(model=None, top_k=6):
    from src.agent.mispl_agent import ask_mispl, DEFAULT_MODEL
    model = model or DEFAULT_MODEL

    print(f"\n{'='*60}")
    print(f"EVAL CHU v2 — Scripts supplémentaires")
    print(f"Modèle : {model}")
    print(f"Tests  : {len(TESTS_CHU_V2)}")
    print(f"{'='*60}\n")

    results = []
    total_score = 0

    for test in TESTS_CHU_V2:
        print(f"[{test['id']}] {test['description']}")
        start = time.time()
        try:
            response, docs = ask_mispl(test["prompt"], top_k=top_k, model=model, save_session=False)
            elapsed = round(time.time() - start, 1)
            ev = evaluate(test, response)
            total_score += ev["score"]
            status = "PASS" if ev["pass"] else "FAIL"
            print(f"  {status} -- score {ev['score']}/10 -- {elapsed}s")
            for e in ev["errors"]:   print(f"    [ERR]  {e}")
            for w in ev["warnings"]: print(f"    [WARN] {w}")
            if not ev["errors"] and not ev["warnings"]:
                print(f"    [OK]   Tous criteres passes")
            sources = [d.get("source","?")[-40:] for d in docs[:3]]
            print(f"    Sources: {sources}")
            results.append({"id": test["id"], "desc": test["description"],
                            "status": status, "score": ev["score"],
                            "elapsed": elapsed, "errors": ev["errors"],
                            "sources": sources, "excerpt": response[:200]})
        except Exception as e:
            print(f"  ERROR -- {e}")
            results.append({"id": test["id"], "status": "ERROR", "score": 0, "error": str(e)})
        time.sleep(2)

    passed = sum(1 for r in results if r["status"] == "PASS")
    avg = total_score / len(TESTS_CHU_V2)

    print(f"\n{'='*60}")
    print(f"RESULTATS FINAUX v2")
    print(f"  Passes   : {passed}/{len(TESTS_CHU_V2)}")
    print(f"  Score moy: {avg:.1f}/10")
    print(f"{'='*60}")

    rpath = ROOT / "outputs" / f"eval_chu_v2_{int(time.time())}.json"
    rpath.parent.mkdir(parents=True, exist_ok=True)
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump({"model": model, "passed": passed, "total": len(TESTS_CHU_V2),
                   "avg_score": avg, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"Rapport : {rpath}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=None)
    p.add_argument("--top-k", type=int, default=6)
    args = p.parse_args()
    run_eval_v2(model=args.model, top_k=args.top_k)
