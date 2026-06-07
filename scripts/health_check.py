"""
MISPL Agent — Health Check complet.
Usage : python scripts/health_check.py
Retourne exit code 0 si tout OK, 1 si un test échoue.
"""
import sys, os, json, time, traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OK   = "\033[32m[OK  ]\033[0m"
FAIL = "\033[31m[FAIL]\033[0m"
WARN = "\033[33m[WARN]\033[0m"

passed, failed, warned = 0, 0, 0


def run(label: str, fn, warn_only: bool = False):
    global passed, failed, warned
    try:
        detail = fn()
        print(f"  {OK}  {label}  {detail or ''}")
        passed += 1
        return True
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()[-1]
        if warn_only:
            print(f"  {WARN}  {label}  {tb}")
            warned += 1
            return False
        print(f"  {FAIL}  {label}")
        print(f"         {tb}")
        failed += 1
        return False


# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 65)
print("  MISPL Agent — Health Check")
print("=" * 65)

# ── 1. Fichiers essentiels ────────────────────────────────────────────────────
print("\n[1] Fichiers essentiels")

run(".env présent",
    lambda: (None, "")[not (ROOT / ".env").exists()] or "OK")

run("OPENROUTER_API_KEY définie", lambda: (
    lambda k: (
        (_ for _ in ()).throw(AssertionError(f"Clé invalide: {k[:10]}"))
        if not (k and k.startswith("sk-or"))
        else f"...{k[-6:]}"
    )(os.environ.get("OPENROUTER_API_KEY", ""))
))

run("Vectorstore présent", lambda: (
    None if (ROOT / "docs" / "chunks" / "vectorstore").exists()
    else (_ for _ in ()).throw(AssertionError("Lancer: .\\start.ps1 build"))
) or "OK")

run("BM25 corpus présent", lambda: (
    None if (ROOT / "docs" / "chunks" / "bm25_corpus.json").exists()
    else (_ for _ in ()).throw(AssertionError("Lancer: .\\start.ps1 build"))
) or "OK")

def check_manifest():
    p = ROOT / "docs" / "chunks" / "manifest.json"
    assert p.exists(), "manifest.json absent"
    m = json.loads(p.read_text(encoding="utf-8"))
    n_ch = m.get("total_chunks", 0)
    n_fn = m.get("known_functions_count", 0)
    assert n_ch > 5000, f"Seulement {n_ch} chunks — rebuild nécessaire"
    assert n_fn > 50,   f"Seulement {n_fn} fonctions — rebuild nécessaire"
    return f"{n_ch} chunks | {n_fn} fonctions MISPL"
run("Manifest valide", check_manifest)

# ── 2. Imports Python ─────────────────────────────────────────────────────────
print("\n[2] Imports Python")

def check_openai():
    import openai
    return f"openai v{openai.__version__}"
run("openai SDK", check_openai)

def check_chromadb():
    import chromadb
    return f"chromadb v{chromadb.__version__}"
run("chromadb", check_chromadb)

def check_bm25():
    from rank_bm25 import BM25Okapi
    return "OK"
run("rank_bm25", check_bm25)

def check_st():
    import sentence_transformers as st_mod
    return f"sentence-transformers v{st_mod.__version__}"
run("sentence-transformers", check_st)

def check_agent_import():
    from src.agent.mispl_agent import ask_mispl, FREE_MODELS, DEFAULT_MODEL
    n = len(FREE_MODELS)
    mod = DEFAULT_MODEL.split("/")[-1][:30]
    return f"{n} modèles | défaut={mod}"
run("mispl_agent importable", check_agent_import)

def check_linter():
    from src.agent.linter import lint_mispl_code
    return "OK"
run("linter importable", check_linter)

def check_prompt():
    from src.agent.prompt_builder import build_system_prompt
    p = build_system_prompt()
    assert len(p) > 500
    return f"{len(p)} chars"
run("prompt_builder", check_prompt)

# ── 3. Retriever ──────────────────────────────────────────────────────────────
print("\n[3] Retriever RAG")

def check_retriever_load():
    from src.rag.retriever import _RetrieverState, get_retriever
    _RetrieverState.invalidate()
    r = get_retriever()
    n = len(r.known_functions)
    assert n > 50, f"Seulement {n} fonctions"
    return f"{n} fonctions connues"
run("Chargement retriever", check_retriever_load)

def check_exact_substr():
    from src.rag.retriever import get_retriever
    r = get_retriever()
    docs = r.query("Substr")
    assert docs, "Aucun résultat"
    fn = docs[0].get("function_name")
    assert fn == "Substr", f"Top-1 fn={fn}"
    assert docs[0].get("exact_match"), "Pas exact_match"
    return f"score={docs[0]['score']:.3f}"
run("Exact-match Substr", check_exact_substr)

def check_exact_today():
    from src.rag.retriever import get_retriever
    r = get_retriever()
    docs = r.query("Today")
    assert docs and docs[0].get("function_name") == "Today"
    return f"score={docs[0]['score']:.3f}"
run("Exact-match Today", check_exact_today)

def check_semantic_substr():
    from src.rag.retriever import get_retriever
    r = get_retriever()
    docs = r.query("extraire partie chaine caracteres")
    fns = [d.get("function_name","") for d in docs[:6]]
    assert "Substr" in fns, f"Substr absent du top-6: {fns}"
    return f"Substr en #{fns.index('Substr')+1}"
run("Sémantique: sous-chaîne → Substr", check_semantic_substr)

def check_semantic_round():
    from src.rag.retriever import get_retriever
    r = get_retriever()
    docs = r.query("arrondir decimal")
    fns = [d.get("function_name","") for d in docs[:4]]
    assert "Round" in fns, f"Round absent: {fns}"
    return f"Round en #{fns.index('Round')+1}"
run("Sémantique: arrondir → Round", check_semantic_round)

# ── 4. OpenRouter API ─────────────────────────────────────────────────────────
print("\n[4] OpenRouter API")

from openai import OpenAI
from src.agent.mispl_agent import FREE_MODELS, FALLBACK_ORDER, DEFAULT_MODEL

api_key = os.environ.get("OPENROUTER_API_KEY", "")
client_or = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
    default_headers={"HTTP-Referer": "https://mispl-agent.lab", "X-Title": "MISPL Agent"},
)

working_model = None
for model_id in FALLBACK_ORDER:
    lbl = next((k for k, v in FREE_MODELS.items() if v == model_id), model_id.split("/")[1][:20])

    def _test_model(mid=model_id, label=lbl):
        global working_model
        r = client_or.chat.completions.create(
            model=mid,
            messages=[{"role": "user", "content": "Réponds juste OK"}],
            max_tokens=10,
            timeout=20,
        )
        txt = (r.choices[0].message.content or "").strip()[:20]
        working_model = mid
        return f"-> {repr(txt)}"

    ok = run(f"Modèle {lbl}", _test_model, warn_only=True)
    if ok:
        break

if not working_model:
    print(f"\n  {FAIL}  AUCUN modèle OpenRouter disponible")
    print("         Vérifier la clé API et les quotas sur https://openrouter.ai/keys")
    failed += 1

# ── 5. Pipeline complet ───────────────────────────────────────────────────────
print("\n[5] Pipeline complet (RAG + LLM)")

if working_model:
    def check_pipeline():
        from src.agent.mispl_agent import ask_mispl
        t0 = time.time()
        resp = ask_mispl(
            "Donne la syntaxe de Substr en MISPL.",
            stream=False,
            save_session=False,
            model=working_model,
        )
        elapsed = time.time() - t0
        assert resp and len(resp) > 80, f"Réponse trop courte: {repr(resp[:50])}"
        has_substr = "Substr" in resp or "substr" in resp.lower()
        assert has_substr, "Substr absent de la réponse"
        return f"{len(resp)} chars en {elapsed:.1f}s"
    run("Question Substr end-to-end", check_pipeline)

    def check_pipeline_stream():
        from src.agent.mispl_agent import ask_mispl
        gen = ask_mispl("Que fait la fonction Len en MISPL ?",
                        stream=True, save_session=False, model=working_model)
        tokens = list(gen)
        resp = "".join(tokens)
        assert len(resp) > 50, f"Réponse stream vide: {repr(resp[:50])}"
        return f"{len(resp)} chars, {len(tokens)} yield(s)"
    run("Stream end-to-end (mode Streamlit)", check_pipeline_stream)
else:
    print(f"  {WARN}  Pipeline complet — skippé (aucun LLM)")
    warned += 1

# ── 6. Linter ─────────────────────────────────────────────────────────────────
print("\n[6] Linter MISPL")

def check_lint_while():
    from src.agent.linter import lint_mispl_code
    r = lint_mispl_code("STRING PROGRAM\n  WHILE TRUE DO\n  DONE;\nRETURN '';\n")
    assert r.has_errors, "WHILE TRUE non détecté"
    return f"{len(r.issues)} issue(s)"
run("Détecte WHILE TRUE", check_lint_while)

def check_lint_id():
    from src.agent.linter import lint_mispl_code
    r = lint_mispl_code("STRING PROGRAM\n  .Sample.Id := 'X';\nRETURN '';\n")
    assert r.has_errors
    return "OK"
run("Détecte .Sample.Id :=", check_lint_id)

def check_lint_clean():
    from src.agent.linter import lint_mispl_code
    r = lint_mispl_code("STRING PROGRAM\n  STRING x;\n  x := 'hello';\nRETURN x;\n")
    assert r.is_clean, f"Faux positif: {[str(i) for i in r.issues]}"
    return "OK"
run("Code valide sans faux positif", check_lint_clean)

# ── Rapport final ─────────────────────────────────────────────────────────────
total = passed + failed + warned
print()
print("=" * 65)
print(f"  {passed}/{total} OK  |  {failed} échecs  |  {warned} avertissements")
print("=" * 65)

if failed > 0:
    print()
    sys.exit(1)
print()
sys.exit(0)
