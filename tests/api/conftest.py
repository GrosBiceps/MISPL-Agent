"""Fixtures partagées pour les tests d'API — DB SQLite en mémoire partagée
entre threads (StaticPool), nécessaire car FastAPI exécute les endpoints
synchrones dans un threadpool : sans StaticPool, chaque thread verrait une
base :memory: différente et vide."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db import Base, get_db
from api.main import app
import api.routers.auth as auth_router


@pytest.fixture
def db_session_factory(monkeypatch):
    # Cookie non-Secure en test : TestClient tourne sur http://testserver,
    # un cookie Secure ne serait pas renvoyé sur les requêtes suivantes.
    monkeypatch.setattr(auth_router, "COOKIE_SECURE", False)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # expire_on_commit=False : les helpers de test (make_user, make_admin...)
    # font souvent `db.commit(); db.close(); return user` puis le test accède
    # à `user.id` après coup — avec le défaut expire_on_commit=True, cet accès
    # lèverait DetachedInstanceError (l'objet est détaché de la session fermée).
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session_factory):
    return TestClient(app)
