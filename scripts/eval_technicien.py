"""
Évaluation questions en langage technicien non-expert.
Usage : python scripts/eval_technicien.py
"""
from __future__ import annotations
import io, json, sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

QUESTIONS = [
    {
        "id": "TQ1",
        "question": "Si mon analyse de PSA rend un résultat entre 3.4 et 6 alors lance automatiquement un PSAL",
        "must_contain": ["LOGICAL PROGRAM", "3.4", "6", "PSAL"],
        "must_not_contain": ["GetValue(", "Left(", "CreatePerson("],
    },
    {
        "id": "TQ2",
        "question": "Je veux qu'un commentaire s'ajoute automatiquement sur mon résultat quand il dépasse 500",
        "must_contain": ["LOGICAL PROGRAM", "500", "AddInternalComment"],
        "must_not_contain": ["GetValue(", "Left(", "CreatePerson("],
    },
    {
        "id": "TQ3",
        "question": "Comment je fais pour que GLIMS envoie un mail au médecin quand un résultat est critique ?",
        "must_contain": ["SendMail"],
        "must_not_contain": ["GetValue(", "CreatePerson("],
    },
    {
        "id": "TQ4",
        "question": "Mon patient est mineur (moins de 18 ans), je veux déclencher une analyse spéciale B_COMM_PEDIATRIE",
        "must_contain": ["LOGICAL PROGRAM", "AgeInYears", "18", "B_COMM_PEDIATRIE"],
        "must_not_contain": ["GetValue(", "Left(", "CreatePerson("],
    },
    {
        "id": "TQ5",
        "question": "Comment annuler un résultat qui existe déjà sur le dossier avant d'en relancer un nouveau ?",
        "must_contain": ["LOGICAL PROGRAM", "Cancel", "AddRequest"],
        "must_not_contain": ["GetValue(", "CreatePerson("],
    },
]


def evaluate(test, response):
    errors = []
    for term in test.get("must_contain", []):
        if term.lower() not in response.lower():
            errors.append("MANQUANT: " + term)
    for term in test.get("must_not_contain", []):
        if term in response:
            errors.append("INTERDIT: " + term)
    # Check syntaxe commentaires
    if "//" in response:
        errors.append("SYNTAXE: commentaire // invalide en MISPL")
    return {"pass": len(errors) == 0, "errors": errors,
            "score": max(0, 10 - len(errors) * 3)}


def run():
    from src.agent.mispl_agent import ask_mispl, DEFAULT_MODEL

    print("\n" + "="*60)
    print("EVAL TECHNICIEN — Questions langage naturel")
    print("Modele : " + DEFAULT_MODEL)
    print("="*60 + "\n")

    results = []
    total_score = 0

    for q in QUESTIONS:
        print("[" + q["id"] + "] " + q["question"])
        start = time.time()
        try:
            response, docs = ask_mispl(q["question"], top_k=6, save_session=False)
            elapsed = round(time.time() - start, 1)
            ev = evaluate(q, response)
            total_score += ev["score"]
            status = "PASS" if ev["pass"] else "FAIL"
            print("  " + status + " -- score " + str(ev["score"]) + "/10 -- " + str(elapsed) + "s")
            for e in ev["errors"]:
                print("    [ERR] " + e)
            if not ev["errors"]:
                print("    [OK] Tous criteres passes")
            sources = [d.get("source", "")[-35:] for d in docs[:3]]
            print("    Sources: " + str(sources))
            print("    Reponse (300c): " + response[:300])
            results.append({"id": q["id"], "question": q["question"],
                           "response": response, "status": status,
                           "score": ev["score"], "elapsed": elapsed,
                           "errors": ev["errors"], "sources": sources})
        except Exception as e:
            print("  ERROR -- " + str(e))
            results.append({"id": q["id"], "question": q["question"],
                           "status": "ERROR", "score": 0, "error": str(e)})
        time.sleep(2)

    passed = sum(1 for r in results if r["status"] == "PASS")
    avg = total_score / len(QUESTIONS)
    print("\n" + "="*60)
    print("RESULTATS")
    print("  Passes   : " + str(passed) + "/" + str(len(QUESTIONS)))
    print("  Score moy: " + str(round(avg, 1)) + "/10")
    print("="*60)

    out = ROOT / "outputs" / "eval_technicien.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Rapport: " + str(out))


if __name__ == "__main__":
    run()
