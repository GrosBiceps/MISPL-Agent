"""
Agent principal MISPL v2 — OpenRouter backend.
OpenRouter expose une API compatible OpenAI → on utilise openai SDK.
Modèles gratuits disponibles sur OpenRouter (ex: mistral-7b, llama-3-8b, gemma-2-9b...).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

import time
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.retriever import get_retriever
from src.agent.prompt_builder import build_system_prompt, SKILL_PROFILES
from src.agent.linter import lint_response, autofix_mispl, Severity
from src.security.access_mode import enforce_access_mode, MODE_DSI


# ── Config ─────────────────────────────────────────────────────────────────────
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Modèles gratuits sur OpenRouter — mis à jour 2026-06
# Vérifier la liste actuelle : python scripts/list_free_models.py
FREE_MODELS = {
    "nemotron-super-120b":  "nvidia/nemotron-3-super-120b-a12b:free",   # testé OK
    "kimi-k2":              "moonshotai/kimi-k2.6:free",                 # testé OK
    "llama-3.3-70b":        "meta-llama/llama-3.3-70b-instruct:free",
    "qwen3-coder":          "qwen/qwen3-coder:free",                     # code spécialisé
    "gemma-4-31b":          "google/gemma-4-31b-it:free",
    "llama-3.2-3b":         "meta-llama/llama-3.2-3b-instruct:free",
    "nemotron-nano-12b":    "nvidia/nemotron-nano-12b-v2-vl:free",
    "hermes-405b":          "nousresearch/hermes-3-llama-3.1-405b:free",
}

# Modèle par défaut — nemotron-120b, testé disponible 2026-06
DEFAULT_MODEL = FREE_MODELS["nemotron-super-120b"]

# Ordre de fallback si rate-limit ou 404 (ordre priorité décroissante)
FALLBACK_ORDER = [
    FREE_MODELS["nemotron-super-120b"],
    FREE_MODELS["kimi-k2"],
    FREE_MODELS["llama-3.3-70b"],
    FREE_MODELS["qwen3-coder"],
    FREE_MODELS["gemma-4-31b"],
    FREE_MODELS["llama-3.2-3b"],
]
DEFAULT_TOP_K = 6
SESSIONS_DIR = ROOT / "outputs" / "sessions"
CACHE_DIR = ROOT / "outputs" / "cache"

# Durée de rétention des sessions journalisées (questions + réponses, potentiellement
# des alertes DLP non bloquantes) avant purge automatique. Configurable via
# MISPL_SESSION_RETENTION_DAYS.
SESSION_RETENTION_DAYS = int(os.environ.get("MISPL_SESSION_RETENTION_DAYS", "30"))


def purge_old_sessions(max_age_days: int = SESSION_RETENTION_DAYS) -> int:
    """Supprime les fichiers de session plus anciens que max_age_days. Retourne le nombre supprimé."""
    if not SESSIONS_DIR.exists():
        return 0
    cutoff = datetime.datetime.now().timestamp() - max_age_days * 86400
    removed = 0
    for f in SESSIONS_DIR.glob("session_*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed


CACHE_RETENTION_HOURS = int(os.environ.get("MISPL_CACHE_RETENTION_HOURS", "24"))


def purge_old_cache(max_age_hours: int = CACHE_RETENTION_HOURS) -> int:
    """Supprime les fichiers de cache plus anciens que max_age_hours (par défaut
    la même fenêtre que la fraîcheur du cache lui-même, cf. _cache_get). Sans
    purge périodique, chaque combinaison unique (question, historique, modèle,
    mode d'accès) laisse un fichier .json permanent sur disque — croissance non
    bornée qui peut aussi retenir indéfiniment du contexte labo en clair sans
    contrôle d'accès (cf. audit sécurité). Retourne le nombre de fichiers supprimés."""
    if not CACHE_DIR.exists():
        return 0
    cutoff = datetime.datetime.now().timestamp() - max_age_hours * 3600
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    return removed


# ── Cache question→réponse 24h ─────────────────────────────────────────────────

# Version du pipeline de génération. À incrémenter dès que le system prompt,
# le post-traitement (strip CoT) ou le format de réponse change → invalide
# automatiquement tout le cache obsolète sans avoir à le vider à la main.
CACHE_VERSION = "v24"

def _cache_key(
    question: str,
    model: str,
    top_k: int,
    skill_profile: list[str] | None,
    access_mode: str,
    conversation_history: list[dict] | None,
) -> str:
    # skill_profile et access_mode changent le prompt système ; l'historique
    # change le contexte envoyé au LLM → tous doivent entrer dans la clé,
    # sinon une réponse mise en cache dans un contexte fuite vers un autre
    # (ex: réponse DSI servie telle quelle à un technicien).
    skills_part = ",".join(sorted(skill_profile)) if skill_profile else "auto"
    hist_part = hashlib.sha256(
        json.dumps(conversation_history or [], ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:12]
    raw = f"{CACHE_VERSION}|{question}|{model}|{top_k}|{skills_part}|{access_mode}|{hist_part}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_get(key: str) -> tuple[str, list] | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        age = datetime.datetime.now().timestamp() - data["ts"]
        if age > 86400:  # 24h
            path.unlink(missing_ok=True)
            return None
        return data["response"], data["docs"]
    except (json.JSONDecodeError, KeyError, OSError) as e:
        # Fichier corrompu (écriture interrompue) → ne jamais planter la requête,
        # juste ignorer le cache et le supprimer.
        logger.warning(f"Cache corrompu ({key}), ignoré : {e}")
        path.unlink(missing_ok=True)
        return None


def _cache_set(key: str, response: str, docs: list) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps({
        "ts": datetime.datetime.now().timestamp(),
        "response": response,
        "docs": docs,
    }, ensure_ascii=False), encoding="utf-8")


# ── Nettoyage chain-of-thought ───────────────────────────────────────────────

import re as _re

# Marqueurs de début de la VRAIE réponse structurée (format imposé)
_ANSWER_MARKERS = [
    "## Contexte GLIMS",
    "## Contexte",
    "**Contexte GLIMS**",
    "⚠️ Fonction non trouvée",
    "## Code MISPL",
]

# Phrases typiques d'un raisonnement à voix haute (anglais — nemotron raisonne en EN)
_COT_SIGNATURES = (
    # Anglais — nemotron/kimi/llama raisonnent en EN
    "okay,", "okay let", "okay!", "let's tackle", "let's break", "let me",
    "first, i", "first i need", "first, let", "first i'll", "first, i'll",
    "looking at the", "the user", "the user is", "the user wants", "the user asked",
    "wait,", "wait ", "i need to", "i should", "i'll check", "i'll look",
    "checking ", "given that", "alternative approach", "let's structure",
    "but the user", "so, ", "therefore,", "now, ", "now i", "alright,",
    "to answer", "to solve", "to address", "the question is", "the query",
    "based on the", "looking at doc", "from the doc", "from doc",
    "hmm,", "hmm ", "well,", "actually,", "essentially,",
    # Raisonnement long nemotron-120b (CoT étendu)
    "but wait,", "re-read", "re read", "so i need", "let me re",
    "the docs", "the provided docs", "the provided documentation",
    "per the user", "per the instruction", "according to the instruction",
    "since the docs", "since there", "since no", "since the provided",
    "in this case,", "in this context,", "this is a bit", "this is tricky",
    "conflicting.", "conflict", "however,", "but since", "but looking",
    "but that seems", "but the absolute", "but per", "but if",
    "check the exact", "check if", "re-check", "reconsider",
    "strictly based", "strictly follow", "strictly speaking",
    # Français — certains modèles raisonnent en FR
    "d'accord,", "voyons", "je dois", "je vais", "tout d'abord",
    "l'utilisateur", "la question est", "en fait,", "d'abord,",
    "il faut verifier", "il faut vérifier", "regardons",
)

def _strip_chain_of_thought(response: str) -> str:
    """
    Supprime tout texte de raisonnement précédant la réponse structurée.

    Stratégie : si un marqueur de réponse (## Contexte GLIMS, ## Code MISPL...)
    apparaît plus loin dans le texte ET que le début ressemble à du raisonnement,
    on coupe tout ce qui précède le premier marqueur.
    """
    if not response:
        return response

    # Trouver la première occurrence d'un marqueur de réponse structurée
    earliest = None
    for marker in _ANSWER_MARKERS:
        idx = response.find(marker)
        if idx != -1 and (earliest is None or idx < earliest):
            earliest = idx

    # Pas de marqueur trouvé → retourner tel quel
    if earliest is None or earliest == 0:
        return response

    preamble = response[:earliest]
    preamble_lower = preamble.lower()

    # Stratégie 1 : CoT signature explicite → couper
    if any(sig in preamble_lower for sig in _COT_SIGNATURES):
        return response[earliest:].lstrip()

    # Stratégie 2 : preamble > 150 chars → coupe inconditionnelle
    # Tout preamble long avant ## Contexte GLIMS EST du raisonnement
    stripped_preamble = preamble.strip()
    if len(stripped_preamble) > 150:
        return response[earliest:].lstrip()

    return response


# ── Détection profil skill ─────────────────────────────────────────────────────
_REPORT_KEYWORDS = {"rapport", "compte-rendu", "etiquette", "label", "template", "imprim"}
_ERD_KEYWORDS    = {"table", "champ", "erd", "relation", "schema", "field", "sample.", "patient.", "order."}
_PERF_KEYWORDS   = {"optimis", "performance", "lent", "rapide", "boucle", "loop"}

def _detect_skill_profile(question: str) -> list[str]:
    q = question.lower()
    if any(k in q for k in _REPORT_KEYWORDS):
        return SKILL_PROFILES["report"]
    if any(k in q for k in _ERD_KEYWORDS):
        return SKILL_PROFILES["erd"]
    if any(k in q for k in _PERF_KEYWORDS):
        return SKILL_PROFILES["perf"]
    return SKILL_PROFILES["code"]


# ── top_k adaptatif (requêtes multi-fonction) ─────────────────────────────────
_ACTION_MARKERS = [
    "ajouter", "déclencher", "declencher", "annuler", "envoyer", "mail", "email",
    "commentaire", "sévérité", "severite", "valider", "imprimer", "calculer",
    "vérifier", "verifier", "fixer", "marquer", "supprimer", "créer", "creer",
    "postprocess", "étiquette", "etiquette", "et que", "ainsi que",
]

def _adaptive_top_k(question: str, base_top_k: int) -> int:
    """Augmente top_k pour les requêtes multi-fonction (3-4→8, ≥5→10)."""
    q = question.lower()
    n = sum(1 for m in _ACTION_MARKERS if m in q)
    if n >= 5:
        return max(base_top_k, 10)
    if n >= 3:
        return max(base_top_k, 8)
    return base_top_k


def _build_fewshot_hint(docs: list) -> str:
    """Si un pattern/cas d'usage complet est dans les docs, invite à l'utiliser comme modèle."""
    template_cats = ("patterns_courants", "reflexe_analytique", "cas_usage")
    labels = []
    for d in docs[:8]:
        cat = str(d.get("category", ""))
        section = str(d.get("section", ""))
        if any(tc in cat for tc in template_cats) or "Pattern" in section or "UC-" in section or "Cas d'usage" in section:
            lab = section[:60] if section else cat
            if lab and lab not in labels:
                labels.append(lab)
    if labels:
        return ("## Modele de reference detecte\n"
                "Les extraits contiennent des patterns complets applicables : " + " · ".join(labels[:3]) + "\n"
                "→ Utilise-les comme base, en adaptant mnemoniques et seuils.\n\n")
    return ""


# ── Client OpenRouter ──────────────────────────────────────────────────────────

def _get_client(api_key: str | None = None) -> OpenAI:
    # api_key explicite (passé par l'appelant) prioritaire sur l'environnement —
    # évite de muter os.environ (partagé entre toutes les sessions du process
    # Streamlit) pour transporter la clé d'une requête individuelle.
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY manquant.\n"
            "PowerShell : $env:OPENROUTER_API_KEY='sk-or-v1-...'\n"
            "Ou definir dans .env : OPENROUTER_API_KEY=sk-or-v1-..."
        )
    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://mispl-agent.lab",  # obligatoire OpenRouter
            "X-Title": "MISPL Agent GLIMS",
        },
    )


# ── Appel LLM avec retry + fallback modèle ────────────────────────────────────

# Budget de temps total pour tous les modèles/tentatives combinés : évite qu'un
# worker FastAPI (thread synchrone) reste bloqué plusieurs minutes si tous les
# modèles gratuits sont rate-limités simultanément (6 modèles x 2 tentatives x
# jusqu'à 20s d'attente = plusieurs minutes dans le pire cas, ce qui peut
# épuiser le threadpool sous charge concurrente — cf. audit sécurité).
_MAX_TOTAL_WAIT_SECONDS = 60


def _call_with_fallback(
    client: OpenAI,
    model: str,
    messages: list,
    stream: bool = False,
    max_retries: int = 2,
):
    """
    Appelle OpenRouter avec retry sur 429 et fallback automatique sur autre modèle gratuit.
    Retourne le completion object (stream ou non).
    """
    models_to_try = [model]
    # Ajouter les fallbacks qui ne sont pas déjà le modèle demandé
    for fb in FALLBACK_ORDER:
        if fb != model and fb not in models_to_try:
            models_to_try.append(fb)

    last_error = None
    deadline = time.monotonic() + _MAX_TOTAL_WAIT_SECONDS
    for current_model in models_to_try:
        for attempt in range(max_retries):
            try:
                return current_model, client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.1,
                    stream=stream,
                    timeout=45,
                )
            except RateLimitError as e:
                last_error = e
                retry_after = 15
                try:
                    meta = (e.body or {}).get("error", {}).get("metadata", {})
                    retry_after = int(meta.get("retry_after_seconds", 15))
                except Exception:
                    pass
                logger.warning(f"RateLimit sur {current_model}, retry dans {retry_after}s")
                remaining = deadline - time.monotonic()
                if attempt < max_retries - 1 and remaining > 0:
                    time.sleep(max(0, min(retry_after, 20, remaining)))
                break  # prochain modèle
            except Exception as e:
                last_error = e
                status_code = getattr(e, "status_code", 0)
                logger.warning(f"Échec sur {current_model} (status={status_code or 'n/a'}): {e}")
                if status_code == 404:
                    logger.warning(f"Modèle {current_model} introuvable (404), fallback")
                    break  # modèle inexistant → prochain sans retry
                remaining = deadline - time.monotonic()
                if attempt < max_retries - 1 and remaining > 0:
                    time.sleep(max(0, min(2, remaining)))
                else:
                    break
        if time.monotonic() >= deadline:
            logger.warning("Budget de temps total des fallbacks OpenRouter épuisé, abandon des modèles restants")
            break

    raise last_error or RuntimeError("Tous les modèles OpenRouter sont indisponibles")


def _extract_usage(completion) -> dict:
    """Extrait les compteurs de tokens d'un objet completion OpenAI-compatible.
    Retourne des zéros si absent (ne devrait pas arriver hors tests, mais
    OpenRouter ne garantit pas formellement le champ pour tous les modèles)."""
    usage = getattr(completion, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
    }


# ── Core agent ─────────────────────────────────────────────────────────────────

def ask_mispl(
    question: str,
    use_openai_embeddings: bool = False,
    top_k: int = DEFAULT_TOP_K,
    model: str = DEFAULT_MODEL,
    skill_profile: list[str] | None = None,
    save_session: bool = True,
    conversation_history: list[dict] | None = None,
    api_key: str | None = None,
    access_mode: str = MODE_DSI,
    usage_out: dict | None = None,
) -> tuple[str, list]:
    """
    Pose une question MISPL/GLIMS à l'agent RAG + LLM via OpenRouter.

    Args:
        question: Question en langage naturel ou nom de fonction MISPL
        use_openai_embeddings: True = OpenAI embeddings (nécessite OPENAI_API_KEY)
        top_k: Chunks RAG récupérés
        model: ID modèle OpenRouter (utiliser FREE_MODELS[...] ou string direct)
        skill_profile: Skills à injecter (auto-détecté si None)
        save_session: Sauvegarder l'échange dans outputs/sessions/
        conversation_history: Historique conversationnel (list de dicts role/content).
            Max 6 derniers échanges injectés entre system et user pour ne pas dépasser
            la context window.
        api_key: Clé OpenRouter pour cette requête précise (prioritaire sur
            OPENROUTER_API_KEY de l'environnement — évite la mutation partagée
            entre sessions Streamlit concurrentes)
        access_mode: "dsi" (génération complète) ou "technicien" (bridé — pas
            de boucles WHILE/REPEAT, cf. src/security/access_mode.py)
        usage_out: si fourni, rempli avec {"prompt_tokens", "completion_tokens",
            "total_tokens"} après l'appel LLM (zéros si réponse servie depuis
            le cache — aucun appel OpenRouter n'a eu lieu).

    Returns:
        Tuple (response_text, docs) — docs réutilisable sans double RAG.
    """
    client = _get_client(api_key)

    # top_k adaptatif : requêtes multi-fonction → plus de chunks (Pattern complet)
    effective_top_k = _adaptive_top_k(question, top_k)

    # Cache 24h — évite d'appeler le LLM pour une question déjà posée récemment
    _key = _cache_key(question, model, effective_top_k, skill_profile, access_mode, conversation_history)
    _cached = _cache_get(_key)
    if _cached:
        logger.info(f"Cache hit pour question ({_key})")
        if usage_out is not None:
            usage_out.update({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        return _cached

    # 1. Retrieval hybride BM25 + dense
    retriever = get_retriever(use_openai=use_openai_embeddings, top_k=effective_top_k)
    docs = retriever.query(question)
    context = retriever.format_context(docs)

    # 2. Prompt système depuis Skills Markdown
    active_skills = skill_profile or _detect_skill_profile(question)
    system_prompt = build_system_prompt(active_skills=active_skills, access_mode=access_mode)

    # 3.b Few-shot dynamique : signaler un pattern/cas d'usage complet présent
    fewshot_hint = _build_fewshot_hint(docs)

    # 3. Prompt utilisateur
    user_prompt = (
        f"## Question du technicien\n{question}\n\n"
        f"## Documentation GLIMS disponible (resultats RAG hybride)\n"
        f"{context}\n\n"
        f"{fewshot_hint}"
        "Instruction : Construis ta reponse a partir des fonctions presentes dans la documentation "
        "ci-dessus. TOUTE fonction qui apparait dans un extrait ci-dessus EXISTE et doit etre "
        "utilisee directement (niveau Certain), JAMAIS marquee 'a verifier'. "
        "Ne marque 'a verifier dans GLIMS' QUE si une fonction est totalement absente de tous les extraits. "
        "Si un extrait montre un pattern complet correspondant a la demande, suis-le comme modele. "
        "INTERDIT d'utiliser CascadeRequest (ancienne version GLIMS) — toujours Action.Order().AddRequest. "
        "CAS IMPOSSIBLE (creer/supprimer un patient, un objet, une analyse au referentiel, modifier les bornes) : "
        "repondre UNIQUEMENT 'impossible via MISPL — se fait via la configuration GLIMS', "
        "SANS pseudo-code, SANS inventer CreatePatient/CreatePerson/CreateObject."
    )

    # Injection de l'historique entre system et user (max 6 échanges)
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        messages.extend(conversation_history[-6:])
    messages.append({"role": "user", "content": user_prompt})

    # Appel non-streaming avec retry + fallback
    used_model, completion = _call_with_fallback(client, model, messages, stream=False)
    if usage_out is not None:
        usage_out.update(_extract_usage(completion))
    response = completion.choices[0].message.content or ""
    # Filet de sécurité : strip le chain-of-thought que nemotron/autres laissent fuiter
    # (le system prompt l'interdit mais les modèles l'ignorent parfois)
    response = _strip_chain_of_thought(response)
    if used_model != model:
        response = f"*(modèle utilisé : {used_model} — {model} indisponible)*\n\n" + response

    # 3.5. Auto-correction (// → /* */, CascadeRequest→AddRequest, SendMailToRole→GetRole)
    response, autofixes = autofix_mispl(response)
    if autofixes:
        logger.info(f"Auto-corrections appliquées : {autofixes}")

    # 3.6. Barrière dure mode d'accès — ne fait rien en mode DSI. En mode
    # Technicien, remplace la réponse entière si une boucle est passée malgré
    # la consigne du prompt système (le LLM ne suit pas toujours ses consignes).
    response = enforce_access_mode(response, access_mode)

    # 4. Lint
    lint_result = lint_response(response)
    if not lint_result.is_clean:
        lint_block = f"\n\n---\n## Analyse de securite du code\n{lint_result.format_report_md()}"
        if lint_result.has_errors:
            lint_block += "\n\n**NE PAS DEPLOYER sans corriger les erreurs ci-dessus.**"
        response += lint_block

    # 5. Session
    if save_session:
        _save_session(question, docs, response, model, active_skills, lint_result, access_mode)

    # Mise en cache pour les 24h à venir
    _cache_set(_key, response, docs)

    return response, docs



# ── Sauvegarde session ─────────────────────────────────────────────────────────

def _save_session(
    question: str,
    docs: list,
    response: str,
    model: str,
    active_skills: list[str],
    lint_result,
    access_mode: str = MODE_DSI,
) -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session = {
        "timestamp": ts,
        "model": model,
        "access_mode": access_mode,
        "active_skills": active_skills,
        "question": question,
        "rag_sources": [
            {
                "source": d.get("source", ""),
                "section": d.get("section", ""),
                "function_name": d.get("function_name", ""),
                "score": round(d.get("score", 0), 3),
                "exact_match": d.get("exact_match", False),
            }
            for d in docs
        ],
        "lint": {
            "clean": lint_result.is_clean,
            "errors": sum(1 for i in lint_result.issues if i.severity == Severity.ERROR),
            "warnings": sum(1 for i in lint_result.issues if i.severity == Severity.WARNING),
            "issues": [str(i) for i in lint_result.issues],
        },
        "response": response,
    }
    with open(SESSIONS_DIR / f"session_{ts}.json", "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)


# ── CLI interactif ─────────────────────────────────────────────────────────────

def interactive_mode() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    print("=" * 65)
    print("  MISPL Agent v2 — OpenRouter backend (gratuit)")
    print(f"  Modele par defaut : {DEFAULT_MODEL}")
    print("=" * 65)
    print("  'exit' pour quitter")
    print("  'model <nom>' pour changer (mistral-small, llama-3.3-70b, gemma-2-27b, qwen-2.5-72b, deepseek-r1, phi-4)")
    print("  'models' pour lister les modeles gratuits disponibles\n")

    current_model = DEFAULT_MODEL

    while True:
        try:
            question = input("> Question MISPL : ").strip()
            if not question:
                continue
            if question.lower() in ("exit", "quit", "q"):
                break
            if question.lower() == "models":
                for k, v in FREE_MODELS.items():
                    print(f"  {k:20s} -> {v}")
                print()
                continue
            if question.lower().startswith("model "):
                key = question.split(maxsplit=1)[1].strip()
                if key in FREE_MODELS:
                    current_model = FREE_MODELS[key]
                    print(f"  Modele : {current_model}\n")
                else:
                    print(f"  Inconnu. Disponibles : {list(FREE_MODELS.keys())}\n")
                continue

            print("\n Recherche hybride en cours...\n")
            response, _docs = ask_mispl(question, model=current_model)
            print(response)
            print()

        except KeyboardInterrupt:
            break
        except FileNotFoundError as e:
            print(f"\n Vectorstore absent : {e}")
            print("  Lancer : python src/rag/build_vectorstore.py\n")
        except Exception as e:
            print(f"\n Erreur : {e}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(ask_mispl(" ".join(sys.argv[1:]))[0])
    else:
        interactive_mode()
