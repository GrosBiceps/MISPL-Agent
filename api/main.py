"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    yield


app = FastAPI(title="MISPL Agent API", lifespan=lifespan)

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
