"""
Vérifie la reproductibilité : re-pose chaque prompt du rapport et compare
la nouvelle réponse à celle stockée. Confirme que le code restauré n'a rien cassé.
Usage : python scripts/verify_reproducibility.py
"""
from __future__ import annotations
import io, json, re, sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def extract_functions(text):
    """Extrait l'ensemble des fonctions MISPL appelées dans le code (Nom suivi de '(')."""
    code = "\n".join(re.findall(r"```mispl(.*?)```", text, re.DOTALL))
    fns = set(re.findall(r"\b([A-Z][A-Za-z0-9]+)\s*\(", code))
    # Garder seulement les vraies fonctions MISPL (pas LOGICAL/IF/etc)
    keywords = {"IF", "THEN", "ELSE", "ENDIF", "WHILE", "DONE", "RETURN", "PROGRAM",
                "AND", "OR", "NOT", "LOGICAL", "STRING", "INTEGER", "FRACTIONAL", "DATE"}
    return fns - keywords


def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    from src.agent.mispl_agent import ask_mispl

    data = json.loads((ROOT / "outputs/full_eval_data_fixed.json").read_text(encoding="utf-8"))
    all_tests = []
    for bat in ["v1", "v2", "tq"]:
        for r in data[bat]:
            prompt = r.get("prompt", "")
            if prompt:
                all_tests.append({
                    "id": r["id"],
                    "prompt": prompt,
                    "stored_response": r.get("response", ""),
                })

    print("\n" + "=" * 66)
    print("VERIFICATION REPRODUCTIBILITE — " + str(len(all_tests)) + " tests")
    print("Re-pose chaque prompt, compare fonctions MISPL au rapport stocké")
    print("=" * 66 + "\n")

    identical = 0
    equivalent = 0
    different = 0
    results = []

    for t in all_tests:
        stored = t["stored_response"]
        stored_fns = extract_functions(stored)
        print("[" + t["id"] + "] " + t["prompt"][:55])
        try:
            new_resp, _ = ask_mispl(t["prompt"], save_session=False)
            new_fns = extract_functions(new_resp)
            sim = jaccard(stored_fns, new_fns)
            # Comparaison stricte du code
            stored_code = "\n".join(re.findall(r"```mispl(.*?)```", stored, re.DOTALL)).strip()
            new_code = "\n".join(re.findall(r"```mispl(.*?)```", new_resp, re.DOTALL)).strip()
            exact = (stored_code == new_code)

            if exact:
                verdict = "IDENTIQUE"
                identical += 1
            elif sim >= 0.7:
                verdict = "EQUIVALENT (mêmes fonctions clés)"
                equivalent += 1
            else:
                verdict = "DIFFERENT"
                different += 1

            missing = stored_fns - new_fns
            added = new_fns - stored_fns
            print("  " + verdict + " — similarité fonctions: " + str(round(sim * 100)) + "%")
            if missing:
                print("    fonctions perdues: " + str(missing))
            if added:
                print("    fonctions ajoutées: " + str(added))
            results.append({"id": t["id"], "verdict": verdict, "similarity": sim,
                           "stored_fns": sorted(stored_fns), "new_fns": sorted(new_fns),
                           "missing": sorted(missing), "added": sorted(added)})
        except Exception as e:
            print("  ERROR: " + str(e)[:80])
            results.append({"id": t["id"], "verdict": "ERROR", "error": str(e)})
        time.sleep(2)

    print("\n" + "=" * 66)
    print("SYNTHESE")
    print("  Identiques (code exact)     : " + str(identical) + "/" + str(len(all_tests)))
    print("  Équivalents (mêmes fonctions): " + str(equivalent) + "/" + str(len(all_tests)))
    print("  Différents                  : " + str(different) + "/" + str(len(all_tests)))
    print("  Reproductibilité fonctionnelle: " + str(round((identical + equivalent) / len(all_tests) * 100)) + "%")
    print("=" * 66)

    out = ROOT / "outputs" / "verify_reproducibility.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Détails : " + str(out))


if __name__ == "__main__":
    main()
