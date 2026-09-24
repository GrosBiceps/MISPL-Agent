"""Utilitaires partagés du banc « temps réel » MISPL Agent (scripts/claude_harness/).

Principe du banc : le VRAI pipeline tourne (retrieval hybride, prompt système
issu des skills, post-traitements, lint, API FastAPI), seul l'appel au LLM
externe est remplacé par des réponses écrites par des subagents Claude
(fichiers outputs/claude_harness/answers/<id>.md).

Garde-fous réseau : AUCUNE requête ne doit partir vers OpenRouter (ni vers
aucun hôte externe). `install_network_guard()` remplace socket.connect /
getaddrinfo pour lever `ExternalNetworkBlocked` sur toute destination non
loopback, et journalise bruyamment la tentative sur stderr.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
ROOT = HARNESS_DIR.parent.parent
OUT_DIR = ROOT / "outputs" / "claude_harness"
PROMPTS_DIR = OUT_DIR / "prompts"
ANSWERS_DIR = OUT_DIR / "answers"
FINAL_DIR = OUT_DIR / "finalized"
HASH_INDEX_PATH = OUT_DIR / "hash_index.json"
RETRIEVAL_PATH = OUT_DIR / "retrieval.json"
MANIFEST_PATH = OUT_DIR / "prompts_manifest.json"
REPORT_JSON = OUT_DIR / "report.json"
REPORT_MD = OUT_DIR / "report.md"
QUESTIONS_PATH = HARNESS_DIR / "questions.json"

FAKE_API_KEY = "sk-test-local"
# Port loopback fermé : si un appel LLM échappait au monkeypatch dans
# prepare/finalize, il échouerait localement au lieu de partir vers OpenRouter.
DEAD_LOCAL_LLM_URL = "http://127.0.0.1:9/v1"

# Marqueurs du prompt utilisateur construit par ask_mispl (src/agent/mispl_agent.py).
USER_QUESTION_HEADER = "## Question du technicien\n"
USER_DOC_HEADER = "\n\n## Documentation GLIMS disponible"

NETWORK_BLOCK_MARKER = "!!! EXTERNAL NETWORK BLOCKED !!!"

VALID_MODES = ("dsi", "technicien")
VALID_BEHAVIORS = ("answer", "impossible", "blocked_loop", "not_found", "injection_resist", "redirect")


# ── Environnement hors-ligne ───────────────────────────────────────────────────

def set_offline_env(llm_base_url: str = DEAD_LOCAL_LLM_URL) -> None:
    """À appeler AVANT tout import de src.agent.mispl_agent / api.main.

    - clé factice (jamais de clé réelle ; load_dotenv n'écrase pas une variable
      déjà définie, donc une clé présente dans .env n'est jamais chargée) ;
    - MISPL_LLM_BASE_URL vers loopback ;
    - Hugging Face / Chroma hors-ligne (modèles déjà en cache local)."""
    os.environ["OPENROUTER_API_KEY"] = FAKE_API_KEY
    os.environ["MISPL_LLM_BASE_URL"] = llm_base_url
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ.pop("OPENAI_API_KEY", None)


# ── Garde réseau ────────────────────────────────────────────────────────────────

class ExternalNetworkBlocked(RuntimeError):
    """Tentative de connexion vers un hôte non loopback pendant le banc."""


BLOCKED_ATTEMPTS: list[str] = []
_LOCAL_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost", ""}


def _is_loopback_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode(errors="ignore")
    host = str(host).strip("[]").lower()
    if host in _LOCAL_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


def _record_block(what: str) -> None:
    BLOCKED_ATTEMPTS.append(what)
    print(f"\n{NETWORK_BLOCK_MARKER} {what}\n", file=sys.stderr, flush=True)


def install_network_guard() -> None:
    """Refuse toute connexion / résolution DNS hors loopback, bruyamment."""
    if getattr(socket, "_mispl_harness_guard", False):
        return
    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex
    orig_getaddrinfo = socket.getaddrinfo

    def _check_address(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and isinstance(address, tuple):
            if not _is_loopback_host(address[0]):
                _record_block(f"connect -> {address!r}")
                raise ExternalNetworkBlocked(f"Connexion externe interdite par le banc : {address!r}")

    def guarded_connect(self, address):
        _check_address(self, address)
        return orig_connect(self, address)

    def guarded_connect_ex(self, address):
        _check_address(self, address)
        return orig_connect_ex(self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_loopback_host(host):
            _record_block(f"getaddrinfo -> {host!r}")
            raise ExternalNetworkBlocked(f"Résolution DNS externe interdite par le banc : {host!r}")
        return orig_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.getaddrinfo = guarded_getaddrinfo
    socket._mispl_harness_guard = True


def assert_no_blocked_attempts() -> None:
    if BLOCKED_ATTEMPTS:
        print(f"\n{NETWORK_BLOCK_MARKER} {len(BLOCKED_ATTEMPTS)} tentative(s) réseau externe :", file=sys.stderr)
        for a in BLOCKED_ATTEMPTS:
            print(f"  - {a}", file=sys.stderr)
        sys.exit(3)


# ── Questions ───────────────────────────────────────────────────────────────────

def question_hash(question: str) -> str:
    return hashlib.sha256(question.strip().encode("utf-8")).hexdigest()[:16]


def extract_question_from_user_prompt(content: str) -> str | None:
    """Retrouve la question brute dans le prompt utilisateur construit par ask_mispl."""
    if not content or USER_QUESTION_HEADER not in content:
        return None
    start = content.index(USER_QUESTION_HEADER) + len(USER_QUESTION_HEADER)
    end = content.find(USER_DOC_HEADER, start)
    if end == -1:
        return None
    return content[start:end]


def load_questions(path: Path = QUESTIONS_PATH, ids: list[str] | None = None) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data["questions"] if isinstance(data, dict) else data
    if ids:
        wanted = set(ids)
        missing = wanted - {q["id"] for q in questions}
        if missing:
            raise SystemExit(f"Ids inconnus dans {path.name} : {sorted(missing)}")
        questions = [q for q in questions if q["id"] in wanted]
    return questions


def validate_questions(questions: list[dict], known_functions: set[str]) -> list[str]:
    """Retourne la liste des problèmes de cohérence du fichier de questions."""
    problems = []
    seen_ids, seen_hashes = set(), {}
    for q in questions:
        qid = q.get("id")
        if not qid or qid in seen_ids:
            problems.append(f"id manquant ou dupliqué : {qid!r}")
        seen_ids.add(qid)
        h = question_hash(q.get("question", ""))
        if h in seen_hashes:
            problems.append(f"{qid}: texte de question identique à {seen_hashes[h]} (hash non unique)")
        seen_hashes[h] = qid
        if q.get("mode") not in VALID_MODES:
            problems.append(f"{qid}: mode invalide {q.get('mode')!r}")
        if q.get("expected_behavior") not in VALID_BEHAVIORS:
            problems.append(f"{qid}: expected_behavior invalide {q.get('expected_behavior')!r}")
        for item in q.get("expected_functions", []):
            for fn in (item if isinstance(item, list) else [item]):
                if fn not in known_functions:
                    problems.append(f"{qid}: fonction attendue absente de known_functions : {fn}")
        for m in q.get("conversation_history", []) or []:
            if m.get("role") not in ("user", "assistant") or not m.get("content"):
                problems.append(f"{qid}: message d'historique invalide")
    return problems


# ── Analyse de texte MISPL ─────────────────────────────────────────────────────

FENCE_RE = re.compile(r"```[^\n`]*\n?([\s\S]*?)```")
_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/|//[^\n]*")
_STRING_RE = re.compile(r'"(?:[^"\\\n]|\\.)*"')
_CALL_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\(")

MISPL_KEYWORDS = {
    "IF", "THEN", "ELSE", "ELSEIF", "ENDIF", "WHILE", "DO", "DONE", "REPEAT", "UNTIL",
    "RETURN", "PROGRAM", "AND", "OR", "NOT", "INTEGER", "FRACTIONAL", "STRING", "LOGICAL",
    "DATE", "DATETIME", "TIME", "ENUMERATED", "YES", "NO", "MNEMONIC",
}


def code_blocks(text: str) -> list[str]:
    return [m.group(1) for m in FENCE_RE.finditer(text or "")]


def called_functions(text: str) -> list[str]:
    """Noms appelés (`Nom(`) dans les blocs de code fenêtrés, hors commentaires,
    chaînes littérales et mots-clés MISPL. Ordre d'apparition, sans doublon."""
    names: list[str] = []
    for block in code_blocks(text):
        clean = _COMMENT_RE.sub(" ", block)
        clean = _STRING_RE.sub('""', clean)
        for m in _CALL_RE.finditer(clean):
            name = m.group(1)
            if name.upper() in MISPL_KEYWORDS:
                continue
            if name not in names:
                names.append(name)
    return names


def uses_function(text: str, fn: str, code_only: bool = True) -> bool:
    """Vrai si `fn` apparaît comme identifiant (insensible à la casse, MISPL
    l'étant) dans les blocs de code (ou dans tout le texte si aucun bloc et
    code_only=False)."""
    pattern = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(fn) + r"(?![A-Za-z0-9_])", re.IGNORECASE)
    blocks = code_blocks(text)
    haystacks = blocks if (blocks or code_only) else [text]
    for h in haystacks:
        clean = _COMMENT_RE.sub(" ", h)
        if pattern.search(clean):
            return True
    return False


def calls_function(text: str, fn: str) -> bool:
    target = fn.casefold()
    return any(n.casefold() == target for n in called_functions(text))


def normalize_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^(?:[-*>]|#{1,6}|\d+\.)\s*", "", line)
    return re.sub(r"\s+", " ", line).strip()


def dump_json(path: Path, obj) -> None:
    """Écriture atomique (fichier temporaire + os.replace) : un lecteur
    concurrent (e2e.py relisant report.json pendant finalize) ne voit jamais
    un fichier à moitié écrit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def ensure_out_dirs() -> None:
    for d in (OUT_DIR, PROMPTS_DIR, ANSWERS_DIR, FINAL_DIR):
        d.mkdir(parents=True, exist_ok=True)
    gi = OUT_DIR / ".gitignore"
    if not gi.exists():
        # outputs/claude_harness/ n'est pas couvert par le .gitignore racine
        # (seuls outputs/*.json, sessions/, cache/ le sont) : on ignore tout ici.
        gi.write_text("*\n", encoding="utf-8")
