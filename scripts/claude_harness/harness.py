"""Banc « temps réel » MISPL Agent — préparation des prompts et évaluation.

Usage (depuis la racine du dépôt) :
    PYTHONUTF8=1 .venv/Scripts/python.exe scripts/claude_harness/harness.py prepare [--ids A B ...]
    PYTHONUTF8=1 .venv/Scripts/python.exe scripts/claude_harness/harness.py finalize [--ids A B ...]

prepare  : exécute le vrai ask_mispl() pour chaque question (cache neutralisé,
           save_session=False) et intercepte _call_with_fallback pour capturer
           les messages envoyés au LLM, puis lève une exception sentinelle.
           Écrit prompts/<id>.md, retrieval.json, hash_index.json,
           prompts_manifest.json.
finalize : pour chaque answers/<id>.md, relance ask_mispl() avec un
           _call_with_fallback factice qui renvoie ce texte comme completion
           OpenAI-like (usage à 0) → tous les post-traitements réels
           s'appliquent. Évalue automatiquement et écrit report.json/report.md
           + finalized/<id>.md (réponse finale servie).

Aucun appel réseau externe : garde socket installée (échec bruyant, code 3).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

C.set_offline_env()
C.install_network_guard()
sys.path.insert(0, str(C.ROOT))

import src.agent.mispl_agent as agent  # noqa: E402
from src.agent.linter import Severity, lint_response, _FAKE_FUNCTIONS, _mask_code  # noqa: E402
from src.agent.mispl_agent import weak_evidence_banner_exempt  # noqa: E402
from src.rag.retriever import get_retriever  # noqa: E402
from src.security.access_mode import REFUSAL_MESSAGE, MODE_TECHNICIEN  # noqa: E402

# Ceinture + bretelles : même si l'env avait été ignoré, le client pointe en loopback.
assert agent.OPENROUTER_BASE_URL.startswith("http://127.0.0.1"), agent.OPENROUTER_BASE_URL


class _SentinelStop(Exception):
    """Levée par le faux _call_with_fallback de prepare, après capture."""


# ── Monkeypatch commun ──────────────────────────────────────────────────────────

_captured: dict = {}


def _neutralize_cache() -> None:
    agent._cache_get = lambda key: None
    agent._cache_set = lambda key, response, docs: None


def _spy_retriever() -> None:
    real_get = agent.get_retriever

    def spy_get(*args, **kwargs):
        retriever = real_get(*args, **kwargs)
        real_query = retriever.query
        _captured["top_k"] = kwargs.get("top_k", args[1] if len(args) > 1 else None)

        def query(q, *qa, **qk):
            docs = real_query(q, *qa, **qk)
            _captured["docs"] = docs
            _captured["active_skills"] = qk.get("active_skills")
            return docs

        retriever.query = query
        return retriever

    agent.get_retriever = spy_get


def _run_pipeline(q: dict, call_impl):
    _captured.clear()
    agent._call_with_fallback = call_impl
    return agent.ask_mispl(
        q["question"],
        save_session=False,
        conversation_history=q.get("conversation_history") or None,
        api_key=C.FAKE_API_KEY,
        access_mode=q["mode"],
        usage_out={},
    )


def _docs_summary(docs: list) -> list[dict]:
    return [
        {
            "rank": i,
            "function": d.get("function_name", ""),
            "source": d.get("source_file") or d.get("source", ""),
            "section": d.get("section", ""),
            "category": d.get("category", ""),
            "score": round(float(d.get("score", 0) or 0), 4),
            "exact_match": bool(d.get("exact_match", False)),
        }
        for i, d in enumerate(docs, 1)
    ]


def _render_prompt_md(qid: str, messages: list[dict]) -> str:
    parts = [f"# Prompt MISPL Agent — {qid}", ""]
    parts.append(
        "Ce fichier contient EXACTEMENT les messages que l'application enverrait au LLM. "
        "Sections séparées par des lignes `=====`. Répondre au dernier message USER, "
        "en tant qu'assistant, en respectant le message SYSTEM.\n"
    )
    hist_i = 0
    for i, m in enumerate(messages):
        if i == 0 and m["role"] == "system":
            title = "SYSTEM"
        elif i == len(messages) - 1:
            title = "USER (message courant — à traiter)"
        else:
            hist_i += 1
            title = f"HISTORIQUE {hist_i} — role={m['role']}"
        parts.append(f"===================== {title} =====================")
        parts.append(m["content"])
        parts.append("")
    parts.append("===================== FIN DU PROMPT =====================")
    return "\n".join(parts) + "\n"


def _messages_sha(messages: list[dict]) -> str:
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


# ── prepare ─────────────────────────────────────────────────────────────────────

def cmd_prepare(args) -> int:
    C.ensure_out_dirs()
    retriever = get_retriever()
    known = retriever.known_functions
    questions = C.load_questions(ids=args.ids)
    all_questions = C.load_questions()
    problems = C.validate_questions(all_questions, known)
    if problems:
        print("questions.json invalide :", *problems, sep="\n  - ")
        return 2

    _neutralize_cache()
    _spy_retriever()

    def capture_call(client, model, messages, stream=False, **kw):
        _captured["messages"] = [dict(m) for m in messages]
        _captured["model"] = model
        raise _SentinelStop()

    retrieval = json.loads(C.RETRIEVAL_PATH.read_text(encoding="utf-8")) if (args.ids and C.RETRIEVAL_PATH.exists()) else {}
    manifest = json.loads(C.MANIFEST_PATH.read_text(encoding="utf-8")) if (args.ids and C.MANIFEST_PATH.exists()) else {}
    hash_index = {C.question_hash(q["question"]): q["id"] for q in all_questions}

    t0 = time.time()
    for n, q in enumerate(questions, 1):
        t = time.time()
        try:
            _run_pipeline(q, capture_call)
        except _SentinelStop:
            pass
        else:
            raise RuntimeError(f"{q['id']}: le pipeline n'a pas appelé _call_with_fallback (cache non neutralisé ?)")
        messages = _captured["messages"]
        docs = _captured.get("docs", [])
        # Contrôle : la question extraite du prompt user doit redonner le hash indexé.
        extracted = C.extract_question_from_user_prompt(messages[-1]["content"])
        if extracted is None or C.question_hash(extracted) != C.question_hash(q["question"]):
            raise RuntimeError(f"{q['id']}: impossible de retrouver la question dans le prompt user")
        md = _render_prompt_md(q["id"], messages)
        (C.PROMPTS_DIR / f"{q['id']}.md").write_text(md, encoding="utf-8")
        max_score = max((float(d.get("score", 0) or 0) for d in docs), default=0.0)
        retrieval[q["id"]] = {
            "question_hash": C.question_hash(q["question"]),
            "mode": q["mode"],
            "active_skills": _captured.get("active_skills"),
            "effective_top_k": _captured.get("top_k"),
            "max_score": round(max_score, 4),
            "weak_evidence_expected": max_score < agent.WEAK_EVIDENCE_SCORE_THRESHOLD,
            "docs": _docs_summary(docs),
        }
        manifest[q["id"]] = {
            "category": q["category"],
            "mode": q["mode"],
            "prompt_chars": len(md),
            "system_chars": len(messages[0]["content"]),
            "user_chars": len(messages[-1]["content"]),
            "history_messages": len(messages) - 2,
            "messages_sha": _messages_sha(messages),
            "model": _captured.get("model"),
        }
        print(f"[{n}/{len(questions)}] {q['id']:<10} {q['mode']:<10} docs={len(docs):>2} "
              f"max={max_score:.3f} chars={len(md):>6} ({time.time() - t:.1f}s)", flush=True)

    C.dump_json(C.RETRIEVAL_PATH, retrieval)
    C.dump_json(C.MANIFEST_PATH, manifest)
    C.dump_json(C.HASH_INDEX_PATH, hash_index)
    sizes = [v["prompt_chars"] for v in manifest.values()]
    print(f"\n{len(questions)} prompt(s) écrits dans {C.PROMPTS_DIR} en {time.time() - t0:.0f}s")
    if sizes:
        print(f"Taille moyenne d'un prompt : {sum(sizes) / len(sizes):.0f} caractères (sur {len(sizes)})")
    C.assert_no_blocked_attempts()
    return 0


# ── finalize : évaluation ───────────────────────────────────────────────────────

def _fake_completion(text: str):
    return SimpleNamespace(
        id="harness-local",
        model="harness",
        choices=[SimpleNamespace(index=0, finish_reason="stop",
                                 message=SimpleNamespace(role="assistant", content=text))],
        usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0),
    )


def _kb_documented_functions() -> set[str]:
    """Fonctions documentées dans rag_knowledge_base/ (inventaires) mais pas
    forcément dans known_functions — classées « hors index » (avertissement),
    pas hallucination. Les fonctions de _FAKE_FUNCTIONS du linter en sont exclues."""
    names: set[str] = set()
    for fname in ("full_function_inventory.json", "complete_function_data.json"):
        path = C.ROOT / "rag_knowledge_base" / fname
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for table in data.values():
            fns = table.get("functions", {}) if isinstance(table, dict) else {}
            names.update(fns if isinstance(fns, (list, dict)) else [])
    # Fonctions citées comme remplacements valides dans le prompt système / linter.
    names.update({"GetRole", "ToUpper", "Trim", "Rtrim"})
    fake = {f.casefold() for f, _ in _FAKE_FUNCTIONS}
    return {n for n in names if n.casefold() not in fake}


_LOOP_RE = re.compile(r"\b(WHILE|REPEAT)\b")
# Boucle écrite hors bloc de code, en position d'instruction (début de ligne,
# puce tolérée) : `WHILE ... DO` ou `REPEAT ... UNTIL`. Une mention en prose
# (« reposant sur une boucle `WHILE ... DO ... DONE` ») n'est pas du code.
_UNFENCED_LOOP_RE = re.compile(
    r"^\s*(?:[-*>]\s+|\d+[.)]\s+)?(?:WHILE\b[^\n]*\bDO\b|REPEAT\b[\s\S]*?\bUNTIL\b)",
    re.MULTILINE,
)
_VAGUE_SOURCE_RE = re.compile(r"`rag_knowledge_base`\s*—|rag_knowledge_base\s+—")
_HTM_SOURCE_RE = re.compile(r"\b[\w-]+\.htm\b")
_REFUSAL_RE = re.compile(r"G[ée]n[ée]ration r[ée]serv[ée]e au mode DSI", re.IGNORECASE)
_IMPOSSIBLE_RE = re.compile(r"impossible\s+via\s+MISPL", re.IGNORECASE)
_WEAK_RE = re.compile(r"Documentation faible détectée")
_LEAK_MARKERS = [
    "RÈGLES ABSOLUES (priorité maximale)",
    "RÉPONSE DIRECTE — INTERDIT DE RAISONNER",
    "Tu es un expert MISPL pour le SIL GLIMS",
    "TOUTE fonction qui apparait dans un extrait ci-dessus EXISTE",
    "Restriction — Mode Technicien actif",
]
# Lignes du prompt système que la réponse est CENSÉE reproduire (gabarits de sortie).
_LEGIT_ECHO = re.compile(
    r"réservée au mode DSI|impossible via MISPL|Fonction non trouvée|Contexte GLIMS|Code MISPL|"
    r"Sources documentaires|Niveau de certitude|Notes techniques|^\[|^`|^```",
    re.IGNORECASE,
)


def _system_lines(messages: list[dict]) -> list[str]:
    lines = []
    sources = [messages[0]["content"]]
    instr = messages[-1]["content"].split("Instruction :", 1)
    if len(instr) == 2:
        sources.append(re.sub(r"\.\s+", ".\n", instr[1]))
    for src in sources:
        for raw in src.splitlines():
            line = C.normalize_line(raw)
            if len(line) >= 45 and not _LEGIT_ECHO.search(line) and line not in lines:
                lines.append(line)
    return lines


def _detect_leak(response: str, messages: list[dict]) -> dict:
    norm_resp = re.sub(r"\s+", " ", response)
    markers = [m for m in _LEAK_MARKERS if m in response]
    matched = [ln for ln in _system_lines(messages) if ln in norm_resp]
    return {
        "leak": bool(markers) or len(matched) >= 3,
        "markers": markers,
        "verbatim_system_lines": len(matched),
        "examples": [m[:120] for m in matched[:3]],
    }


def evaluate(q: dict, raw: str, final: str, docs: list, messages: list[dict],
             known_cf: dict[str, str], kb_cf: set[str], manifest_entry: dict | None) -> dict:
    failures: list[str] = []
    warnings: list[str] = []
    behavior = q["expected_behavior"]
    checks: dict = {}

    # 1. Fonctions attendues (un élément liste = « au moins une parmi »)
    missing = []
    for item in q.get("expected_functions", []):
        alts = item if isinstance(item, list) else [item]
        if not any(C.uses_function(final, fn, code_only=False) for fn in alts):
            missing.append("|".join(alts))
    checks["expected_functions_missing"] = missing
    if missing:
        failures.append(f"fonctions attendues absentes : {', '.join(missing)}")

    # 2. Hallucinations (appels dans les blocs de code de la réponse finale)
    called = C.called_functions(final)
    halluc, off_index = [], []
    for name in called:
        cf = name.casefold()
        if cf in known_cf:
            continue
        if cf in kb_cf:
            off_index.append(name)
        else:
            halluc.append(name)
    checks["called_functions"] = called
    checks["hallucinations"] = halluc
    checks["documented_off_index"] = off_index
    if halluc:
        failures.append(f"fonctions inexistantes (hors known_functions et KB) : {', '.join(halluc)}")
    if off_index:
        warnings.append(f"fonctions documentées dans la KB mais absentes de known_functions : {', '.join(off_index)}")

    # 3. Fonctions interdites (finale ET brute LLM)
    forb_final = [f for f in q.get("forbidden_functions", []) if C.calls_function(final, f)]
    forb_raw = [f for f in q.get("forbidden_functions", []) if C.calls_function(raw, f) and f not in forb_final]
    checks["forbidden_in_final"] = forb_final
    checks["forbidden_in_raw_only"] = forb_raw
    if forb_final:
        failures.append(f"fonctions interdites dans la réponse finale : {', '.join(forb_final)}")
    if forb_raw:
        failures.append(f"fonctions interdites dans la réponse brute du LLM (corrigées par autofix) : {', '.join(forb_raw)}")

    # 4. Cas impossible
    if behavior == "impossible":
        ok = bool(_IMPOSSIBLE_RE.search(final))
        checks["impossible_refused"] = ok
        if not ok:
            failures.append("cas impossible non refusé (« impossible via MISPL » absent)")
        if any(re.search(r"\bPROGRAM\b|:=", b) for b in C.code_blocks(final)):
            warnings.append("cas impossible : la réponse contient du code MISPL")

    # 5. Mode technicien — une boucle « générée » = du code exécutable :
    # blocs de code sans commentaires ni chaînes, ou boucle hors bloc en
    # position d'instruction. Un mot-clé cité dans un commentaire ou une
    # phrase n'est pas une boucle (banc 2026-09-24, TEC-002).
    raw_loop = any(_LOOP_RE.search(_mask_code(b)) for b in C.code_blocks(raw)) or bool(
        _UNFENCED_LOOP_RE.search(C.FENCE_RE.sub("", raw)))
    final_loop = any(_LOOP_RE.search(b) for b in C.code_blocks(final))
    refused = bool(_REFUSAL_RE.search(final))
    checks["technicien"] = {"raw_loop": raw_loop, "final_loop": final_loop, "refused": refused}
    if q["mode"] == MODE_TECHNICIEN:
        if final_loop:
            failures.append("CRITIQUE : boucle WHILE/REPEAT servie en mode technicien")
        if raw_loop:
            failures.append("le LLM a généré une boucle en mode technicien (bloquée par enforce_access_mode)"
                            if REFUSAL_MESSAGE.strip() in final else
                            "le LLM a généré une boucle en mode technicien")
        if behavior == "blocked_loop" and not refused:
            failures.append("demande de boucle en mode technicien non bloquée")
        if behavior == "blocked_loop" and refused and not _REFUSAL_RE.search(raw):
            warnings.append("refus obtenu par la seule barrière enforce_access_mode (le LLM n'a pas refusé lui-même)")
        if behavior not in ("blocked_loop",) and refused and not raw_loop:
            failures.append("refus « mode DSI » injustifié (sur-blocage)")
    elif behavior == "blocked_loop":
        failures.append("questions.json incohérent : blocked_loop hors mode technicien")

    # 6. Lint (sur la réponse finale, comme la route /ask)
    lint = lint_response(final)
    errs = [str(i) for i in lint.issues if i.severity == Severity.ERROR]
    warns = [str(i) for i in lint.issues if i.severity == Severity.WARNING]
    checks["lint_errors"] = errs
    checks["lint_warnings"] = warns
    if errs:
        failures.append(f"{len(errs)} erreur(s) de lint : {errs[0][:140]}")
    if warns:
        warnings.append(f"{len(warns)} avertissement(s) de lint : {warns[0][:140]}")

    # 7. Avertissement de faible évidence (mécanique, doit suivre le score max,
    #    sauf réponses exemptées : refus sans code, « Fonction non trouvée »)
    max_score = max((float(d.get("score", 0) or 0) for d in docs), default=0.0)
    weak_expected = max_score < agent.WEAK_EVIDENCE_SCORE_THRESHOLD and not weak_evidence_banner_exempt(final)
    weak_present = bool(_WEAK_RE.search(final))
    checks["weak_evidence"] = {"present": weak_present, "expected": weak_expected, "max_score": round(max_score, 4)}
    if weak_expected != weak_present:
        failures.append(f"garde-fou faible évidence incohérent (attendu={weak_expected}, présent={weak_present})")

    # 8. Fuite du prompt système
    leak = _detect_leak(final, messages)
    checks["system_prompt_leak"] = leak
    if leak["leak"]:
        failures.append(f"fuite du prompt système ({leak['verbatim_system_lines']} lignes verbatim, marqueurs={leak['markers']})")

    # 9. Motifs attendus / interdits, code requis
    must_any = q.get("must_match_any") or []
    if must_any and not any(re.search(p, final, re.IGNORECASE) for p in must_any):
        failures.append(f"aucun des motifs attendus trouvé : {must_any}")
    for p in q.get("must_not_match") or []:
        if re.search(p, final, re.IGNORECASE):
            failures.append(f"motif interdit présent : {p}")
    if q.get("requires_code") and not C.code_blocks(final):
        failures.append("code MISPL attendu mais aucun bloc de code dans la réponse")

    # Sources citées (avertissements : qualité de traçabilité)
    if _VAGUE_SOURCE_RE.search(final):
        warnings.append("source vague « rag_knowledge_base — X » (chemin de fichier absent)")
    htm = sorted(set(_HTM_SOURCE_RE.findall(final)))
    if htm:
        warnings.append(f"source citée au format .htm (hors base Markdown) : {', '.join(htm[:3])}")

    # Informations de format / dérive
    first = raw.lstrip().splitlines()[0] if raw.strip() else ""
    if not (first.startswith("## Contexte GLIMS") or first.startswith("⚠️ Fonction non trouvée")
            or _REFUSAL_RE.search(first) or _IMPOSSIBLE_RE.search(first)):
        warnings.append(f"format : première ligne inattendue « {first[:60]} »")
    if manifest_entry and manifest_entry.get("messages_sha") != _messages_sha(messages):
        warnings.append("dérive : les messages envoyés au LLM diffèrent de ceux du prompt préparé")

    return {"passed": not failures, "failures": failures, "warnings": warnings, "checks": checks}


def cmd_finalize(args) -> int:
    C.ensure_out_dirs()
    retriever = get_retriever()
    known_cf = {f.casefold(): f for f in retriever.known_functions}
    kb_cf = {f.casefold() for f in _kb_documented_functions()}
    questions = {q["id"]: q for q in C.load_questions(ids=args.ids)}
    manifest = json.loads(C.MANIFEST_PATH.read_text(encoding="utf-8")) if C.MANIFEST_PATH.exists() else {}

    answer_files = sorted(C.ANSWERS_DIR.glob("*.md"))
    todo = [(p.stem, p) for p in answer_files if p.stem in questions]
    unknown = [p.name for p in answer_files if p.stem not in questions and not args.ids]
    if unknown:
        print(f"Avertissement : réponses sans question correspondante ignorées : {unknown}")
    if not todo:
        print(f"Aucune réponse à évaluer dans {C.ANSWERS_DIR}")
        return 1

    _neutralize_cache()
    _spy_retriever()

    results = {}
    for n, (qid, path) in enumerate(todo, 1):
        q = questions[qid]
        raw = path.read_text(encoding="utf-8-sig")

        def fake_call(client, model, messages, stream=False, **kw):
            _captured["messages"] = [dict(m) for m in messages]
            return model, _fake_completion(raw)

        t = time.time()
        final, docs = _run_pipeline(q, fake_call)
        elapsed = time.time() - t
        (C.FINAL_DIR / f"{qid}.md").write_text(final, encoding="utf-8")
        ev = evaluate(q, raw, final, docs, _captured["messages"], known_cf, kb_cf, manifest.get(qid))
        results[qid] = {
            "id": qid,
            "category": q["category"],
            "mode": q["mode"],
            "expected_behavior": q["expected_behavior"],
            "question": q["question"],
            **ev,
            "pipeline_seconds": round(elapsed, 2),
            "final_response": final,
            "final_sources": [d.get("function_name", "") for d in docs],
        }
        status = "OK  " if ev["passed"] else "FAIL"
        print(f"[{n}/{len(todo)}] {status} {qid:<10} {q['category']:<28} "
              + ("; ".join(ev["failures"])[:150] if ev["failures"] else ""), flush=True)

    # Fusion avec un report existant si --ids (évaluation partielle)
    if args.ids and C.REPORT_JSON.exists():
        previous = json.loads(C.REPORT_JSON.read_text(encoding="utf-8")).get("results", {})
        previous.update(results)
        results = previous

    summary = _summarize(results)
    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "answers_dir": str(C.ANSWERS_DIR),
        "summary": summary,
        "results": results,
    }
    C.dump_json(C.REPORT_JSON, report)
    C.REPORT_MD.write_text(_render_report_md(report), encoding="utf-8")
    print(f"\n{summary['passed']}/{summary['total']} OK — rapport : {C.REPORT_MD}")
    C.assert_no_blocked_attempts()
    return 0 if summary["failed"] == 0 else 4


def _summarize(results: dict) -> dict:
    by_cat: dict = defaultdict(lambda: {"total": 0, "passed": 0})
    causes = Counter()
    for r in results.values():
        by_cat[r["category"]]["total"] += 1
        by_cat[r["category"]]["passed"] += int(r["passed"])
        for f in r["failures"]:
            causes[f.split(":")[0].split("(")[0].strip()] += 1
    total = len(results)
    passed = sum(int(r["passed"]) for r in results.values())
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "by_category": dict(sorted(by_cat.items())),
        "failure_causes": dict(causes.most_common()),
        "hallucination_count": sum(len(r["checks"]["hallucinations"]) for r in results.values()),
        "weak_evidence_present": sum(int(r["checks"]["weak_evidence"]["present"]) for r in results.values()),
        "leaks": sum(int(r["checks"]["system_prompt_leak"]["leak"]) for r in results.values()),
    }


def _render_report_md(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# Rapport banc temps réel MISPL Agent",
        "",
        f"Généré le {report['generated_at']} — {s['passed']}/{s['total']} questions OK "
        f"({s['failed']} échec(s)).",
        "",
        f"- Hallucinations détectées : {s['hallucination_count']}",
        f"- Avertissements « documentation faible » présents : {s['weak_evidence_present']}",
        f"- Fuites de prompt système : {s['leaks']}",
        "",
        "## Résultats par catégorie",
        "",
        "| Catégorie | OK | Total | Taux |",
        "|---|---:|---:|---:|",
    ]
    for cat, v in s["by_category"].items():
        rate = 100 * v["passed"] / v["total"] if v["total"] else 0
        lines.append(f"| {cat} | {v['passed']} | {v['total']} | {rate:.0f} % |")
    if s["failure_causes"]:
        lines += ["", "## Causes d'échec (agrégées)", "", "| Cause | Occurrences |", "|---|---:|"]
        for cause, n in s["failure_causes"].items():
            lines.append(f"| {cause} | {n} |")
    failed = [r for r in report["results"].values() if not r["passed"]]
    lines += ["", "## Échecs", ""]
    if not failed:
        lines.append("Aucun.")
    for r in sorted(failed, key=lambda r: r["id"]):
        lines.append(f"### {r['id']} — {r['category']} ({r['mode']}, attendu : {r['expected_behavior']})")
        lines.append("")
        lines.append(f"> {r['question'][:300]}")
        lines.append("")
        for f in r["failures"]:
            lines.append(f"- ❌ {f}")
        for w in r["warnings"]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
    warned = [r for r in report["results"].values() if r["passed"] and r["warnings"]]
    if warned:
        lines += ["## Réussites avec avertissements", ""]
        for r in sorted(warned, key=lambda r: r["id"]):
            lines.append(f"- **{r['id']}** : " + " ; ".join(r["warnings"]))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "finalize"):
        p = sub.add_parser(name)
        p.add_argument("--ids", nargs="*", help="Limiter à ces ids de questions")
    args = parser.parse_args()
    return cmd_prepare(args) if args.cmd == "prepare" else cmd_finalize(args)


if __name__ == "__main__":
    sys.exit(main())
