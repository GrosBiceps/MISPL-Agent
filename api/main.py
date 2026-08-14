"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db import Base, engine
from api.routers import admin, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Exécuté uniquement au démarrage réel du serveur (uvicorn) — jamais à
    # l'import du module. Les tests ne passent jamais par ici : ils créent
    # leurs propres tables sur un moteur SQLite en mémoire séparé (cf.
    # tests/api/conftest.py) et n'instancient/démarrent jamais ce serveur.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MISPL Agent API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(admin.router)
