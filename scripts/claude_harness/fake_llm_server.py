"""Serveur OpenAI-compatible factice pour le banc « temps réel » MISPL Agent.

Écoute UNIQUEMENT sur 127.0.0.1. Répond à POST /v1/chat/completions en
retrouvant la réponse pré-écrite dans outputs/claude_harness/answers/<id>.md :
la question est extraite du dernier message user (format du prompt construit
par ask_mispl), hachée (common.question_hash) puis résolue via
outputs/claude_harness/hash_index.json (écrit par `harness.py prepare`).

- Réponse inconnue (hash absent ou answers/<id>.md manquant) → 404 explicite.
- Clé différente de la clé factice sk-test-local → 401 (garantit qu'aucune
  clé réelle ne transite, même vers ce serveur local).
- stream=true → 400 (l'application n'utilise que le mode non-streaming).
- GET /health → 200.

Usage :
    .venv/Scripts/python.exe scripts/claude_harness/fake_llm_server.py --port 0 --port-file X --log Y
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

_log_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "MISPLFakeLLM/1.0"
    answers_dir: Path = C.ANSWERS_DIR
    hash_index_path: Path = C.HASH_INDEX_PATH
    request_log: Path | None = None

    def log_message(self, fmt, *args):  # silence du log HTTP par défaut
        pass

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self, entry: dict) -> None:
        entry["ts"] = time.time()
        line = json.dumps(entry, ensure_ascii=False)
        print(line, flush=True)
        if self.request_log:
            with _log_lock, open(self.request_log, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _error(self, status: int, code: str, message: str, **extra) -> None:
        self._record({"status": status, "code": code, **extra})
        self._send(status, {"error": {"message": message, "type": "fake_llm_error", "code": code, **extra}})

    def do_GET(self):
        if self.path.rstrip("/") in ("/health", "/v1/health"):
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": {"message": f"route inconnue : {self.path}", "code": "not_found"}})

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            return self._error(404, "unknown_route", f"route inconnue : {self.path}")
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {C.FAKE_API_KEY}":
            return self._error(401, "invalid_api_key", "clé API inattendue : seul sk-test-local est accepté")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            return self._error(400, "bad_json", f"corps JSON invalide : {e}")
        if body.get("stream"):
            return self._error(400, "stream_unsupported", "stream=true non supporté par le serveur factice")

        messages = body.get("messages") or []
        users = [m for m in messages if m.get("role") == "user"]
        if not users:
            return self._error(400, "no_user_message", "aucun message user")
        question = C.extract_question_from_user_prompt(users[-1].get("content") or "")
        if question is None:
            return self._error(400, "question_not_found", "question introuvable dans le dernier message user")
        qhash = C.question_hash(question)
        try:
            index = json.loads(self.hash_index_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            index = {}
        qid = index.get(qhash)
        answer_path = self.answers_dir / f"{qid}.md" if qid else None
        if not qid or not answer_path.exists():
            return self._error(
                404, "answer_not_found",
                f"Réponse inconnue pour la question hash={qhash} (id={qid or '?'}) : "
                f"answers/{qid or '<id>'}.md absent — lancer `harness.py prepare` puis écrire la réponse.",
                question_hash=qhash, question_id=qid,
            )

        content = answer_path.read_text(encoding="utf-8-sig")
        prompt_chars = sum(len(m.get("content") or "") for m in messages)
        usage = {
            "prompt_tokens": max(1, prompt_chars // 4),
            "completion_tokens": max(1, len(content) // 4),
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        self._record({"status": 200, "question_id": qid, "question_hash": qhash,
                      "model": body.get("model"), "messages": len(messages)})
        self._send(200, {
            "id": f"chatcmpl-fake-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model") or "fake-llm",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": usage,
        })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0, help="0 = port libre choisi par l'OS")
    parser.add_argument("--port-file", type=Path, help="Fichier où écrire le port effectif")
    parser.add_argument("--log", type=Path, help="Journal JSONL des requêtes")
    parser.add_argument("--answers-dir", type=Path, default=C.ANSWERS_DIR)
    parser.add_argument("--hash-index", type=Path, default=C.HASH_INDEX_PATH)
    args = parser.parse_args()

    Handler.answers_dir = args.answers_dir
    Handler.hash_index_path = args.hash_index
    Handler.request_log = args.log
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    port = server.server_address[1]
    if args.port_file:
        args.port_file.write_text(str(port), encoding="utf-8")
    print(f"fake LLM server listening on http://127.0.0.1:{port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
