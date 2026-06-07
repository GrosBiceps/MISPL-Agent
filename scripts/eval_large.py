"""
Évaluation large — 20 prompts variés, langage technicien + technique.
Couvre un maximum de patterns. Vérifie ZÉRO CascadeRequest dans les réponses.
Usage : python scripts/eval_large.py
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

TESTS = [
    # ── Langage technicien pur ────────────────────────────────────────────────
    {"id": "L01", "label": "Reflex glucose technicien",
     "q": "Si ma glycémie dépasse 7 mmol/L je veux lancer automatiquement une HbA1c",
     "must": ["LOGICAL PROGRAM", "AddRequest"], "no": ["CascadeRequest(", "GetValue(", "Left("]},
    {"id": "L02", "label": "Commentaire si valeur basse",
     "q": "Je veux ajouter un commentaire sur le résultat si la kaliémie est en dessous de 3",
     # AddInternalComment OU AddExternalComment valides (commentaire non spécifié interne/externe)
     "must": ["LOGICAL PROGRAM", "Comment"], "no": ["CascadeRequest(", "GetValue("]},
    {"id": "L03", "label": "Sévérité valeur panique",
     "q": "Mettre le résultat en alerte rouge quand le potassium dépasse 6.5",
     "must": ["LOGICAL PROGRAM", "SetManualSeverity"], "no": ["CascadeRequest(", "GetValue("]},
    {"id": "L04", "label": "Email prescripteur critique",
     "q": "Envoyer un mail au médecin qui a prescrit si la troponine est très élevée",
     "must": ["SendMail"], "no": ["CascadeRequest(", "SendMailToRole("]},
    {"id": "L05", "label": "Patient pédiatrique",
     "q": "Pour un enfant de moins de 12 ans, déclencher l'analyse B_PEDIA_SPECIAL",
     "must": ["LOGICAL PROGRAM", "AgeInYears", "AddRequest"], "no": ["CascadeRequest(", "Left("]},
    # ── Langage technique précis ──────────────────────────────────────────────
    {"id": "L06", "label": "RelatedResult deux analyses",
     "q": "Si le résultat lié B_VOLUME et le résultat lié B_TEMPS ont une valeur, ajouter B_CALC",
     "must": ["LOGICAL PROGRAM", "RelatedResult", "AddRequest"], "no": ["CascadeRequest(", "Order.Result("]},
    {"id": "L07", "label": "ObjectType person check",
     "q": "Vérifier que c'est un humain via EnumeratedToString ObjectType puis ajouter B_HUMAN",
     "must": ["LOGICAL PROGRAM", "EnumeratedToString", "person", "AddRequest"], "no": ["CascadeRequest("]},
    {"id": "L08", "label": "Annuler résultat doublon",
     "q": "Annuler le résultat B_OLD existant s'il a une valeur puis créer B_NEW",
     "must": ["LOGICAL PROGRAM", "Cancel", "AddRequest"], "no": ["CascadeRequest(", "GetValue("]},
    {"id": "L09", "label": "Substr filtrer qualificatif",
     "q": "Extraire le premier caractère de la valeur pour vérifier si c'est < ou >",
     "must": ["Substr"], "no": ["Left(", "Mid(", "CascadeRequest("]},
    {"id": "L10", "label": "Multi AddRequest",
     "q": "Ajouter d'un coup les analyses B_A, B_B et B_C sur le dossier",
     "must": ["LOGICAL PROGRAM", "AddRequest"], "no": ["CascadeRequest("]},
    # ── Délai / temps ─────────────────────────────────────────────────────────
    {"id": "L11", "label": "Délai acheminement",
     "q": "Si le délai d'acheminement en minutes dépasse 4 heures, mettre sévérité 3 et commenter",
     "must": ["LOGICAL PROGRAM", "StringToInteger", "SetManualSeverity"], "no": ["CascadeRequest("]},
    {"id": "L12", "label": "Garde week-end",
     "q": "Détecter si le dossier est arrivé un week-end ou jour férié",
     "must": ["LOGICAL PROGRAM", "IsHoliday"], "no": ["CascadeRequest("]},
    # ── Anti-hallucination ────────────────────────────────────────────────────
    {"id": "L13", "label": "Impossible créer patient",
     "q": "Comment créer un nouveau patient dans GLIMS via MISPL ?",
     # Vérifie que le modèle répond impossible. Les mentions CreatePerson dans les
     # notes pédagogiques ("n'existe pas") sont légitimes — on vérifie juste qu'il
     # ne GÉNÈRE pas un appel CreatePerson( comme solution dans un bloc code mispl.
     "must": ["impossible"], "no": ["CreatePerson(\"", "NewPatient(\""],
     "check_no_fake_in_code": True},
    {"id": "L14", "label": "Impossible modifier bornes",
     "q": "Je veux changer les valeurs de référence d'une analyse via MISPL",
     "must": ["pas"], "no": ["SetReferenceRange(", "CreatePerson("]},
    # ── Conversion / valeur ───────────────────────────────────────────────────
    {"id": "L15", "label": "Lire valeur numérique",
     "q": "Comment lire la valeur numérique d'un résultat ?",
     "must": ["NumericValue"], "no": ["GetValue(", "CascadeRequest("]},
    {"id": "L16", "label": "Convertir chaîne en décimal",
     "q": "Convertir une chaîne de caractères en nombre décimal",
     "must": ["StringToFractional"], "no": ["StringToReal(", "Val("]},
    # ── PostProcess / étiquettes ──────────────────────────────────────────────
    {"id": "L17", "label": "Imprimer étiquettes",
     "q": "Ajouter une analyse étiquette puis imprimer les étiquettes échantillons",
     "must": ["LOGICAL PROGRAM", "AddRequest", "PostProcess"], "no": ["CascadeRequest("]},
    # ── Alerte multi-action complexe ──────────────────────────────────────────
    {"id": "L18", "label": "Alerte critique multi-action",
     "q": "Si CRP > 200 chez patient > 70 ans, sévérité 11, commentaire interne et email au rôle BIOLOGISTE_GARDE",
     "must": ["LOGICAL PROGRAM", "NumericValue", "AgeInYears", "SetManualSeverity", "AddInternalComment", "GetRole"], "no": ["CascadeRequest(", "SendMailToRole(", "GetValue("]},
    # ── Valeur textuelle codée ────────────────────────────────────────────────
    {"id": "L19", "label": "Valeur textuelle Non",
     "q": "Si le résultat qualitatif vaut exactement 'Positif', ajouter B_CONFIRM",
     "must": ["LOGICAL PROGRAM", "Attribute", "AddRequest"], "no": ["CascadeRequest(", "GetValue("]},
    # ── Boucle liste ──────────────────────────────────────────────────────────
    {"id": "L20", "label": "Boucle WHILE explicite sur liste",
     "q": "Écris une boucle WHILE en MISPL qui parcourt élément par élément une liste CSV avec NumEntries et Entry, et affiche chaque élément",
     "must": ["WHILE", "DONE", "NumEntries", "Entry"], "no": ["CascadeRequest("]},
]


def _code_blocks(response):
    import re
    return "\n".join(re.findall(r"```mispl(.*?)```", response, re.DOTALL))

def evaluate(test, response):
    errors = []
    rl = response.lower()
    for t in test["must"]:
        if t.lower() not in rl:
            errors.append("MANQUANT: " + t)
    for t in test["no"]:
        if t in response:
            errors.append("INTERDIT: " + t)
    # Vérif spéciale : fausses fonctions interdites SEULEMENT dans le code généré
    if test.get("check_no_fake_in_code"):
        code = _code_blocks(response)
        for fake in ["CreatePerson(", "NewPatient(", "CreateObject("]:
            if fake in code:
                errors.append("INTERDIT (dans code): " + fake)
    return len(errors) == 0, errors, max(0, 10 - len(errors) * 3)


def run():
    from src.agent.mispl_agent import ask_mispl, DEFAULT_MODEL
    print("\n" + "="*64)
    print("EVAL LARGE — 20 prompts variés (technicien + technique)")
    print("Verif : ZERO CascadeRequest, zero hallucination")
    print("Modele : " + DEFAULT_MODEL)
    print("="*64 + "\n")

    results = []
    total = 0
    cascade_found = 0

    for t in TESTS:
        print("[" + t["id"] + "] " + t["label"])
        start = time.time()
        try:
            resp, docs = ask_mispl(t["q"], save_session=False)
            elapsed = round(time.time() - start, 1)
            passed, errors, score = evaluate(t, resp)
            total += score
            if "CascadeRequest(" in resp:
                cascade_found += 1
            status = "PASS" if passed else "FAIL"
            print("  " + status + " " + str(score) + "/10 — " + str(elapsed) + "s")
            for e in errors:
                print("    [ERR] " + e)
            results.append({"id": t["id"], "label": t["label"], "q": t["q"],
                           "response": resp, "status": status, "score": score,
                           "errors": errors, "elapsed": elapsed,
                           "sources": [d.get("source","")[-30:] for d in docs[:3]]})
        except Exception as e:
            print("  ERROR: " + str(e)[:80])
            results.append({"id": t["id"], "status": "ERROR", "score": 0, "error": str(e)})
        time.sleep(2)

    passed = sum(1 for r in results if r.get("status") == "PASS")
    avg = total / len(TESTS)
    print("\n" + "="*64)
    print("RESULTATS")
    print("  Passes        : " + str(passed) + "/" + str(len(TESTS)))
    print("  Score moy     : " + str(round(avg,1)) + "/10")
    print("  CascadeRequest: " + str(cascade_found) + " (doit etre 0)")
    print("="*64)

    out = ROOT / "outputs" / ("eval_large_" + str(int(time.time())) + ".json")
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Rapport: " + str(out))


if __name__ == "__main__":
    run()
