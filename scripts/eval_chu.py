"""
Évaluation finale basée sur les vrais scripts MISPL du CHU.
Source : fonctions_mispl.xlsx — propriété du service de biologie médicale.
Usage : python scripts/eval_chu.py
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

# ── Tests basés sur les vrais scripts CHU ─────────────────────────────────────
# Chaque test : demander à l'agent de REPRODUIRE/EXPLIQUER un script réel
# puis comparer avec le script de référence

TESTS_CHU = [
    {
        "id": "CHU01_psal_reflex",
        "description": "Déclencheur PSA → PSAL (script B_declencheurPSAL)",
        "prompt": "Écris un script MISPL sur un résultat de PSA : si la valeur est entre 3.5 et 10 ng/ml, ajouter une demande PSAL, commentaire interne 'PSAL déclenché automatiquement', marquer comme sollicité",
        "reference_code": ".Result.MarkAsSolicited(); ... .cascadeRequest ou AddRequest ... addinternalcomment",
        # NumericValue ET StringToFractional sont tous deux valides pour lire la valeur
        "must_contain": ["LOGICAL PROGRAM", "3.5", "10", "MarkAsSolicited", "PSAL"],
        "must_not_contain_strict": ["GetValue()", "FRACTIONAL PROGRAM", "CreatePerson("],
        "expected_functions": ["MarkAsSolicited", "AddInternalComment"],
    },
    {
        "id": "CHU02_alz_ratio",
        "description": "Déclencheur Alzheimer ratio (B_Ajout B_ALZ_VR_RATIO) — vérif type objet Person",
        "prompt": "Écris un script MISPL sur un résultat : utiliser EnumeratedToString pour vérifier que le type de l'objet (ObjectType) est 'person', ET que le résultat a une valeur connue (Mantissa <> ?), puis ajouter une demande B_ALZ_VR_RATIO au dossier via Action.Order().AddRequest",
        "must_contain": ["LOGICAL PROGRAM", "EnumeratedToString", "ObjectType", "person", "AddRequest"],
        "must_not_contain_strict": ["GetValue()", "CreatePerson("],
        "expected_functions": ["EnumeratedToString", "AddRequest"],
    },
    {
        "id": "CHU03_age_pal",
        "description": "Borne PAL selon âge (B_COM_VR_PAL si <= 19 ans)",
        "prompt": "Écris un script MISPL sur un résultat : si l'âge de l'objet est <= 19 ans ET la valeur est connue ET ne commence pas par '<' ou '>', alors déclencher la demande B_COM_VR_PAL",
        # AddRequest ET CascadeRequest sont tous deux valides pour déclencher une analyse
        "must_contain": ["LOGICAL PROGRAM", "AgeInYears", "19", "Substr", "B_COM_VR_PAL"],
        "must_not_contain_strict": ["GetValue()", "Left(", "CreatePerson("],
        "expected_functions": ["AgeInYears", "Substr"],
    },
    {
        "id": "CHU04_related_result",
        "description": "Calcul créatinine/temps (B_Declenchement Creat/Temps) — deux résultats liés",
        "prompt": "Écris un script MISPL sur un résultat : si le résultat lié B_VOLUME_UR ET le résultat lié B_TEMPS_RECUEIL ont tous les deux une valeur connue (non ?), alors ajouter la demande B_CALC_CREAT_UR",
        # CascadeRequest et AddRequest sont tous deux valides pour déclencher une analyse
        "must_contain": ["LOGICAL PROGRAM", "RelatedResult", "B_CALC_CREAT_UR"],
        "must_not_contain_strict": ["GetValue()", "CreatePerson("],
        "expected_functions": ["RelatedResult"],
    },
    {
        "id": "CHU05_severity_delai",
        "description": "Délai FNA avec seuil et sévérité (B_Delai_FNA)",
        "prompt": "Écris un script MISPL sur un résultat de délai (en minutes) : convertir la valeur en entier avec StringToInteger, si >= 240 ET le résultat B_COB_LACT_SG existe sur le dossier (Order.Result <> ?), mettre la sévérité manuelle à 3 via SetManualSeverity et ajouter la demande B_COMM_DELAI_SUP4H via Action.Order().AddRequest",
        "must_contain": ["LOGICAL PROGRAM", "StringToInteger", "SetManualSeverity", "AddRequest", "240"],
        "must_not_contain_strict": ["GetValue()", "CreatePerson("],
        "expected_functions": ["StringToInteger", "SetManualSeverity", "AddRequest"],
    },
    {
        "id": "CHU06_cancel_reopen",
        "description": "Annuler et rouvrir une analyse (B_Delai_HERPAR_LI pattern)",
        "prompt": "Écris un script MISPL qui annule un résultat existant (Cancel avec raison 'Délai acheminement > 6H') et en ajoute un nouveau identique sur le dossier",
        # Le mot "Discontinue" est une valeur de raison possible mais pas obligatoire
        "must_contain": ["LOGICAL PROGRAM", "Cancel", "AddRequest"],
        "must_not_contain_strict": ["GetValue()", "CreatePerson("],
        "expected_functions": ["Cancel", "AddRequest"],
    },
    {
        "id": "CHU07_explain_bm_cst",
        "description": "Explication script existant B_BM_CST",
        "prompt": 'Explique ce que fait ce script MISPL : If .Result.Attribute("Value") = "Non" then .Result.Order.AddRequest("B_NON_CONF_CST",?,?); Endif; RETURN Yes;',
        "must_contain": ["résultat", "Non", "AddRequest"],
        "must_not_contain_strict": ["CreatePerson("],
        "expected_functions": [],
    },
    {
        "id": "CHU08_multi_addrequest",
        "description": "Ajout multiple de demandes (B_Ajout A_TOXO pattern)",
        "prompt": "Écris un script MISPL qui ajoute 3 demandes en une seule fois sur le dossier courant depuis le contexte Action : 'TOXO_IGG', 'TOXO_IGM', 'TOXO_COMMENT'",
        "must_contain": ["LOGICAL PROGRAM", "AddRequest", "TOXO_IGG", "TOXO_IGM", "TOXO_COMMENT"],
        "must_not_contain_strict": ["GetValue()", "CascadeRequest(", "CreatePerson("],
        "expected_functions": ["AddRequest"],
    },
    {
        "id": "CHU09_impossible",
        "description": "Anti-hallucination : créer patient",
        "prompt": "Créer un nouveau patient dans GLIMS via MISPL",
        # LLM dit "pas possible", "ne peut pas", "ne permet pas" — toutes variantes valides
        "must_contain": ["pas"],
        "must_not_contain_strict": ["CreatePerson(", "NewPatient("],
        "expected_functions": [],
    },
    {
        "id": "CHU10_postprocess",
        "description": "PostProcess après ajout demande (B_Edition Etiquette dossier)",
        "prompt": "Écris un script MISPL qui ajoute une demande 'ETIQ' au dossier puis appelle PostProcess pour imprimer les étiquettes échantillons",
        "must_contain": ["LOGICAL PROGRAM", "AddRequest", "PostProcess"],
        "must_not_contain_strict": ["GetValue()", "CreatePerson("],
        "expected_functions": ["AddRequest", "PostProcess"],
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


def run_eval_chu(model=None, top_k=6):
    from src.agent.mispl_agent import ask_mispl, DEFAULT_MODEL
    model = model or DEFAULT_MODEL

    print(f"\n{'='*60}")
    print(f"EVAL CHU MISPL AGENT — Scripts réels du service")
    print(f"Modèle : {model}")
    print(f"Tests  : {len(TESTS_CHU)}")
    print(f"{'='*60}\n")

    results = []
    total_score = 0

    for test in TESTS_CHU:
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
    avg = total_score / len(TESTS_CHU)

    print(f"\n{'='*60}")
    print(f"RESULTATS FINAUX")
    print(f"  Passes   : {passed}/{len(TESTS_CHU)}")
    print(f"  Score moy: {avg:.1f}/10")
    print(f"{'='*60}")

    rpath = ROOT / "outputs" / f"eval_chu_{int(time.time())}.json"
    rpath.parent.mkdir(parents=True, exist_ok=True)
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump({"model": model, "passed": passed, "total": len(TESTS_CHU),
                   "avg_score": avg, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"Rapport : {rpath}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=None)
    p.add_argument("--top-k", type=int, default=6)
    args = p.parse_args()
    run_eval_chu(model=args.model, top_k=args.top_k)
