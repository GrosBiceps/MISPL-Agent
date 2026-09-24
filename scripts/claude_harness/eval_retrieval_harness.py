"""Évaluation du retrieval sur le banc de 122 questions, sans LLM.

Pour chaque question de `scripts/claude_harness/questions.json` ayant des
`expected_functions`, on reproduit EXACTEMENT l'appel de retrieval fait par
`ask_mispl` :
  - top_k effectif = `_adaptive_top_k(question, DEFAULT_TOP_K)` ;
  - `active_skills` = `_detect_skill_profile(question)` ;
  - `retriever.query(question, active_skills=active_skills)` (la question seule,
    l'historique de conversation n'entre pas dans le retrieval).

Mesures :
  - rappel strict : part des éléments attendus (un élément liste = « au moins
    une parmi ») présents comme `function_name` d'un doc récupéré ;
  - rappel « mention » : idem, mais un appel `Nom(` dans le texte d'un doc
    récupéré compte aussi (le LLM peut réutiliser une fonction vue dans un
    pattern ou un cas d'usage) ;
  - questions entièrement couvertes (strict).

Usage :
    .venv/Scripts/python.exe scripts/claude_harness/eval_retrieval_harness.py
    .venv/Scripts/python.exe scripts/claude_harness/eval_retrieval_harness.py --out base.json
    .venv/Scripts/python.exe scripts/claude_harness/eval_retrieval_harness.py --ids DAT-001,STR-010 -v
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.agent.mispl_agent import (  # noqa: E402
    DEFAULT_TOP_K,
    _adaptive_top_k,
    _detect_skill_profile,
)
from src.rag.retriever import get_retriever  # noqa: E402

QUESTIONS_PATH = ROOT / "scripts" / "claude_harness" / "questions.json"
OUT_DIR = ROOT / "outputs" / "claude_harness"


def _items(q: dict) -> list[list[str]]:
    return [it if isinstance(it, list) else [it] for it in q.get("expected_functions", [])]


def _mentions(text: str, fn: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(fn)}\s*\(", text or "") is not None


def evaluate(ids: set[str] | None = None, verbose: bool = False) -> dict:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]
    results = []
    n_items = n_strict = n_mention = n_full = n_q = 0
    for q in questions:
        if ids and q["id"] not in ids:
            continue
        items = _items(q)
        if not items:
            continue
        question = q["question"]
        top_k = _adaptive_top_k(question, DEFAULT_TOP_K)
        skills = _detect_skill_profile(question)
        docs = get_retriever(top_k=top_k).query(question, active_skills=skills)
        fns = [(d.get("function_name") or "").strip() for d in docs]
        missing_strict, missing_mention = [], []
        for alts in items:
            strict = any(a in fns for a in alts)
            mention = strict or any(_mentions(d.get("text", ""), a) for d in docs for a in alts)
            n_items += 1
            n_strict += strict
            n_mention += mention
            if not strict:
                missing_strict.append("|".join(alts))
            if not mention:
                missing_mention.append("|".join(alts))
        n_q += 1
        n_full += not missing_strict
        rec = {
            "id": q["id"],
            "category": q.get("category"),
            "top_k": top_k,
            "active_skills": skills,
            "retrieved": fns,
            "max_score": round(max((d.get("score", 0) or 0 for d in docs), default=0.0), 4),
            "missing_strict": missing_strict,
            "missing_mention": missing_mention,
        }
        results.append(rec)
        if verbose or missing_strict:
            print(f"{q['id']:8s} k={top_k:2d} miss={missing_strict} got={fns}")
    summary = {
        "questions": n_q,
        "items": n_items,
        "recall_strict": round(n_strict / max(n_items, 1), 3),
        "recall_mention": round(n_mention / max(n_items, 1), 3),
        "questions_fully_covered": round(n_full / max(n_q, 1), 3),
        "questions_with_miss": [r["id"] for r in results if r["missing_strict"]],
    }
    return {"summary": summary, "results": results}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="eval_retrieval_harness.json",
                    help="fichier de sortie sous outputs/claude_harness/")
    ap.add_argument("--ids", default="", help="liste d'ids séparés par des virgules")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    ids = {i.strip() for i in args.ids.split(",") if i.strip()} or None
    out = evaluate(ids, args.verbose)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    s = out["summary"]
    print(f"\nquestions={s['questions']} items={s['items']} "
          f"recall_strict={s['recall_strict']:.3f} recall_mention={s['recall_mention']:.3f} "
          f"fully_covered={s['questions_fully_covered']:.3f} misses={len(s['questions_with_miss'])}")


if __name__ == "__main__":
    main()
