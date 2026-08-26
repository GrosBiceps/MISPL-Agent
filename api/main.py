"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

import os
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
