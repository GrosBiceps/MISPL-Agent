"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from api.db import Base, engine
from api.routers import admin, auth, chat, conversations


logger = logging.getLogger(__name__)


def warm_up_rag() -> bool:
    """Précharge le retriever (ChromaDB + modèle d'embeddings + index BM25) et
    le cross-encoder de reranking, puis exécute une requête à blanc.

    Sans ce préchargement, la première question posée après le démarrage
    payait tout le chargement : 43 s au banc e2e du 2026-09-24 (60 s pour le
    retriever et 7 s pour le cross-encoder mesurés isolément), contre ~11 s
    ensuite. Désactivable via MISPL_PRELOAD_RETRIEVER=false (démarrage rapide
    en développement). Ne fait jamais échouer le démarrage de l'API : en cas
    d'erreur (index absent...), la première requête retentera le chargement
    et remontera l'erreur comme avant. Retourne True si le préchargement a
    eu lieu et a réussi."""
    if os.environ.get("MISPL_PRELOAD_RETRIEVER", "true").strip().lower() in ("false", "0", "no"):
        return False
    try:
        from src.agent.mispl_agent import DEFAULT_TOP_K
        from src.rag.retriever import get_retriever

        start = time.monotonic()
        get_retriever(top_k=DEFAULT_TOP_K).query("Substr", active_skills=["mispl-core"])
        logger.info(f"RAG préchargé en {time.monotonic() - start:.1f}s")
        return True
    except Exception as e:  # noqa: BLE001 — le démarrage ne doit jamais échouer ici
        logger.warning(f"Préchargement du RAG impossible ({e}) : chargement différé à la première requête")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Exécuté uniquement au démarrage réel du serveur (uvicorn) — jamais à
    # l'import du module. Les tests ne passent jamais par ici : ils créent
    # leurs propres tables sur un moteur SQLite en mémoire séparé (cf.
    # tests/api/conftest.py) et n'instancient/démarrent jamais ce serveur.
    Base.metadata.create_all(bind=engine)
    from src.agent.mispl_agent import purge_old_cache, purge_old_sessions
    purge_old_sessions()
    purge_old_cache()
    # Bloquant avant d'accepter des requêtes : aucune requête ne peut
    # déclencher un second chargement concurrent du singleton du retriever.
    warm_up_rag()
    yield


app = FastAPI(title="MISPL Agent API", lifespan=lifespan)

# Taille maximale acceptée pour le corps d'une requête HTTP. Le payload JSON
# de /chat/ask (question + lab_context + conversation_history, tous bornés
# côté schéma Pydantic — cf. api/schemas.py) ne devrait jamais s'en approcher ;
# cette limite est une défense en profondeur contre un corps de requête
# volumineux qui saturerait la mémoire/le CPU avant même la validation Pydantic.
MAX_REQUEST_BODY_BYTES = 1 * 1024 * 1024  # 1 Mo


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Corps de requête trop volumineux"},
                )
        except ValueError:
            pass

    # Content-Length est absent pour un corps en Transfer-Encoding: chunked —
    # un client peut alors contourner le contrôle ci-dessus. On borne aussi le
    # flux réel, chunk par chunk, indépendamment de tout en-tête déclaré par
    # le client (jamais fiable pour une limite de sécurité).
    received = 0
    original_receive = request.receive

    async def limited_receive():
        nonlocal received
        message = await original_receive()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > MAX_REQUEST_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Corps de requête trop volumineux")
        return message

    request._receive = limited_receive
    return await call_next(request)


# Chemins servant du HTML/JS interactif (Swagger UI / ReDoc, générés par
# FastAPI) : ils ont besoin d'exécuter des scripts/styles externes (CDN) et
# ne peuvent donc pas recevoir le CSP strict "default-src 'none'" appliqué au
# reste de l'API (purement JSON). On les exempte explicitement plutôt que de
# relâcher le CSP globalement.
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path not in _DOCS_PATHS:
        response.headers["Content-Security-Policy"] = "default-src 'none'"
    return response


_frontend_origins = os.environ.get("MISPL_FRONTEND_ORIGIN", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(conversations.router)
