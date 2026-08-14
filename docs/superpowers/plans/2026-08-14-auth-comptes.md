# Authentification & comptes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à MISPL Agent un système de comptes réel (admin + techniciens), avec sessions révocables côté serveur, pour remplacer l'absence totale d'identité actuelle et servir de socle aux chantiers suivants (historique de sessions, quotas, dashboard admin).

**Architecture:** Nouvelle API FastAPI (dossier `api/`) séparée de la logique métier existante (`src/`), backée par SQLite via SQLAlchemy. Les mots de passe sont hashés en Argon2id, les sessions sont des lignes en base (token opaque en cookie httpOnly), révocables instantanément par un admin. `src/` (agent, rag, security) n'est pas touché sauf ajout d'un petit helper dans `access_mode.py`.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, SQLite, argon2-cffi, httpx (tests), pytest.

## ⚠️ Déviation par rapport au texte de la spec

La spec (`docs/superpowers/specs/2026-08-14-auth-comptes-design.md`, section "Intégration avec le code existant") prévoit de **supprimer** `verify_dsi_password`, `hash_password`, `generate_salt` de `src/security/access_mode.py` et de supprimer `scripts/set_dsi_password.py`.

Ce plan **ne le fait pas**. Raison : `app.py` (l'interface Streamlit actuelle, toujours en production) importe et appelle directement `verify_dsi_password` pour son bouton de déverrouillage du mode DSI. La migration du frontend hors Streamlit est un chantier séparé, explicitement hors périmètre ici (cf. spec, section "Périmètre"). Supprimer ces fonctions maintenant casserait l'application actuellement utilisée.

**Ce que ce plan fait à la place** (Task 8) : ajoute un helper `access_mode_for_user()` que la future API/frontend utilisera, sans toucher au mécanisme existant. Le mécanisme par mot de passe partagé reste en place, marqué comme legacy, à retirer explicitement lors du chantier de migration frontend (qui remplacera aussi l'appel dans `app.py`).

## Global Constraints

- Une seule instance déployée (un seul CHU) — pas de multi-tenant dans ce chantier
- Comptes créés uniquement par un admin — aucune route d'auto-inscription, jamais
- Pas de 2FA, pas de reset de mot de passe par email, pas de SSO dans ce chantier
- Hash de mot de passe : Argon2id (`argon2-cffi`) pour tout le nouveau code d'auth
- Sessions révocables côté serveur (table SQLite), pas de JWT
- Durée de session : 8h, glissante (renouvelée à chaque requête authentifiée valide)
- Verrouillage de compte après 5 échecs de connexion consécutifs, pour 15 minutes
- `platform_role` (admin/user) et `can_use_dsi_mode` (bool) sont deux axes indépendants — ne jamais les coupler dans le code
- Toujours garder au moins un compte admin actif (refuser de désactiver/rétrograder le dernier)
- Un mot de passe temporaire généré (création de compte, reset) n'est retourné qu'une seule fois dans la réponse HTTP, jamais loggé, jamais stocké en clair
- `data/mispl.db` ne doit jamais être commité (ajouter à `.gitignore`)

---

## Task 1: Dépendances, connexion DB et modèles ORM (users, sessions)

**Files:**
- Create: `api/__init__.py`
- Create: `api/db.py`
- Create: `api/models.py`
- Test: `tests/api/__init__.py`
- Test: `tests/api/test_models.py`
- Modify: `requirements.txt`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `api.db.Base` (declarative base), `api.db.engine`, `api.db.SessionLocal` (sessionmaker), `api.db.get_db()` (generator dependency)
- Produces: `api.models.User` (colonnes : id, email, password_hash, display_name, platform_role, can_use_dsi_mode, is_active, failed_login_count, locked_until, created_at, last_login_at ; relation `.sessions`)
- Produces: `api.models.UserSession` (colonnes : token (PK), user_id (FK), created_at, expires_at, revoked_at ; relation `.user`). Nommé `UserSession` et non `Session` pour ne pas entrer en collision avec `sqlalchemy.orm.Session`.

- [ ] **Step 1: Installer les dépendances**

```bash
.venv/Scripts/pip.exe install fastapi "uvicorn[standard]" "sqlalchemy>=2.0" argon2-cffi httpx email-validator
```

- [ ] **Step 2: Épingler les versions dans requirements.txt**

```bash
.venv/Scripts/pip.exe freeze | grep -iE "^(fastapi|uvicorn|starlette|sqlalchemy|argon2-cffi|argon2-cffi-bindings|httpx|anyio|h11|httpcore|pydantic|email-validator|dnspython)"
```

Ajouter une nouvelle section à la fin de `requirements.txt`, avec les versions exactes retournées ci-dessus :

```
# ── API & Authentification (comptes, sessions) ────────────────────────────────
fastapi==<version installée>
uvicorn[standard]==<version installée>
sqlalchemy==<version installée>
argon2-cffi==<version installée>
email-validator==<version installée>      # requis par pydantic.EmailStr
httpx==<version installée>                # requis par fastapi.testclient.TestClient
```

- [ ] **Step 3: Créer le package `api/`**

```python
# api/__init__.py
```

(fichier vide)

- [ ] **Step 4: Créer le package de test**

```python
# tests/api/__init__.py
```

(fichier vide)

- [ ] **Step 5: Écrire le test (doit échouer — api.db/api.models n'existent pas encore)**

```python
# tests/api/test_models.py
"""Tests des modèles ORM users/sessions — DB en mémoire, sans FastAPI."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import Base
from api.models import User, UserSession


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestUserModel:
    def test_create_and_query_user(self):
        db = make_session()
        user = User(
            email="tech1@labo.fr",
            password_hash="hash-placeholder",
            display_name="Tech Un",
            platform_role="user",
            can_use_dsi_mode=False,
        )
        db.add(user)
        db.commit()

        fetched = db.query(User).filter(User.email == "tech1@labo.fr").one()
        assert fetched.display_name == "Tech Un"
        assert fetched.platform_role == "user"
        assert fetched.can_use_dsi_mode is False
        assert fetched.is_active is True  # défaut
        assert fetched.failed_login_count == 0  # défaut

    def test_email_unique_constraint(self):
        db = make_session()
        db.add(User(email="dup@labo.fr", password_hash="h", display_name="A", platform_role="user"))
        db.commit()
        db.add(User(email="dup@labo.fr", password_hash="h", display_name="B", platform_role="user"))
        import pytest
        with pytest.raises(Exception):
            db.commit()


class TestUserSessionModel:
    def test_create_session_linked_to_user(self):
        db = make_session()
        user = User(email="tech2@labo.fr", password_hash="h", display_name="Tech Deux", platform_role="user")
        db.add(user)
        db.commit()

        now = datetime.datetime.utcnow()
        session_row = UserSession(
            token="tok-abc123",
            user_id=user.id,
            created_at=now,
            expires_at=now + datetime.timedelta(hours=8),
        )
        db.add(session_row)
        db.commit()

        fetched = db.get(UserSession, "tok-abc123")
        assert fetched.user_id == user.id
        assert fetched.revoked_at is None
        assert fetched.user.email == "tech2@labo.fr"
        assert user.sessions[0].token == "tok-abc123"
```

- [ ] **Step 6: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_models.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api.db'`

- [ ] **Step 7: Implémenter `api/db.py`**

```python
# api/db.py
"""Connexion SQLite + base déclarative SQLAlchemy pour l'API MISPL Agent."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'mispl.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 8: Implémenter `api/models.py`**

```python
# api/models.py
"""Modèles ORM : comptes utilisateurs et sessions de connexion."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("platform_role IN ('admin', 'user')", name="ck_users_platform_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    platform_role: Mapped[str] = mapped_column(String, nullable=False)
    can_use_dsi_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
```

- [ ] **Step 9: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_models.py -v`
Expected: PASS (3 tests)

- [ ] **Step 10: Ajouter `data/` au `.gitignore`**

Ajouter dans `.gitignore`, section à créer si absente :

```
# ── Base de données locale (comptes, sessions) — jamais dans le repo ────────
data/*.db
data/*.db-journal
```

- [ ] **Step 11: Commit**

```bash
git add api/__init__.py api/db.py api/models.py tests/api/__init__.py tests/api/test_models.py requirements.txt .gitignore
git commit -m "feat(api): modèles ORM users/sessions + connexion SQLite"
```

---

## Task 2: Hachage de mot de passe et génération de mot de passe temporaire

**Files:**
- Create: `api/security.py`
- Test: `tests/api/test_security.py`

**Interfaces:**
- Consumes: rien (module autonome)
- Produces: `api.security.hash_password(password: str) -> str`, `api.security.verify_password(password: str, password_hash: str) -> bool`, `api.security.generate_temp_password(length: int = 14) -> str`

- [ ] **Step 1: Écrire le test**

```python
# tests/api/test_security.py
"""Tests du hachage Argon2id et de la génération de mot de passe temporaire."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.security import generate_temp_password, hash_password, verify_password


class TestPasswordHashing:
    def test_verify_correct_password(self):
        h = hash_password("MotDePasseRobuste1!")
        assert verify_password("MotDePasseRobuste1!", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("MotDePasseRobuste1!")
        assert verify_password("AutreChose", h) is False

    def test_same_password_different_hash_each_time(self):
        h1 = hash_password("MotDePasseRobuste1!")
        h2 = hash_password("MotDePasseRobuste1!")
        assert h1 != h2  # sel aléatoire à chaque hash

    def test_verify_against_garbage_hash_does_not_raise(self):
        assert verify_password("quoiquecesoit", "pas-un-hash-valide") is False


class TestTempPasswordGeneration:
    def test_default_length(self):
        assert len(generate_temp_password()) == 14

    def test_custom_length(self):
        assert len(generate_temp_password(length=20)) == 20

    def test_two_calls_differ(self):
        assert generate_temp_password() != generate_temp_password()
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_security.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api.security'`

- [ ] **Step 3: Implémenter `api/security.py`**

```python
# api/security.py
"""Hachage de mot de passe (Argon2id) et génération de mot de passe temporaire."""

from __future__ import annotations

import secrets
import string

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

_hasher = PasswordHasher()

_TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_temp_password(length: int = 14) -> str:
    return "".join(secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(length))
```

- [ ] **Step 4: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_security.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add api/security.py tests/api/test_security.py
git commit -m "feat(api): hachage Argon2id + génération de mot de passe temporaire"
```

---

## Task 3: Cycle de vie des sessions (création, validation, révocation)

**Files:**
- Create: `api/session_store.py`
- Test: `tests/api/test_session_store.py`

**Interfaces:**
- Consumes: `api.models.User`, `api.models.UserSession`
- Produces: `api.session_store.SESSION_TTL_HOURS` (int, =8), `api.session_store.create_session(db, user: User) -> str`, `api.session_store.validate_session(db, token: str) -> User | None`, `api.session_store.revoke_session(db, token: str) -> None`, `api.session_store.revoke_all_sessions_for_user(db, user_id: int) -> int`

- [ ] **Step 1: Écrire le test**

```python
# tests/api/test_session_store.py
"""Tests du cycle de vie des sessions — création, validation, expiration, révocation."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import Base
from api.models import User, UserSession
from api.session_store import (
    create_session,
    revoke_all_sessions_for_user,
    revoke_session,
    validate_session,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def make_user(db, **overrides):
    defaults = dict(
        email="tech@labo.fr", password_hash="h", display_name="Tech",
        platform_role="user", is_active=True,
    )
    defaults.update(overrides)
    user = User(**defaults)
    db.add(user)
    db.commit()
    return user


class TestCreateAndValidate:
    def test_valid_session_returns_user(self):
        db = make_session()
        user = make_user(db)
        token = create_session(db, user)
        result = validate_session(db, token)
        assert result is not None
        assert result.id == user.id

    def test_unknown_token_returns_none(self):
        db = make_session()
        assert validate_session(db, "token-inexistant") is None

    def test_sliding_expiration_extends_on_validate(self):
        db = make_session()
        user = make_user(db)
        token = create_session(db, user)
        row_before = db.get(UserSession, token)
        original_expiry = row_before.expires_at
        # recule artificiellement l'expiration pour observer l'extension
        row_before.expires_at = original_expiry - datetime.timedelta(hours=1)
        db.commit()

        validate_session(db, token)
        row_after = db.get(UserSession, token)
        assert row_after.expires_at > original_expiry - datetime.timedelta(hours=1)


class TestExpiredAndRevoked:
    def test_expired_session_returns_none(self):
        db = make_session()
        user = make_user(db)
        token = create_session(db, user)
        row = db.get(UserSession, token)
        row.expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        db.commit()
        assert validate_session(db, token) is None

    def test_revoked_session_returns_none(self):
        db = make_session()
        user = make_user(db)
        token = create_session(db, user)
        revoke_session(db, token)
        assert validate_session(db, token) is None

    def test_inactive_user_session_returns_none(self):
        db = make_session()
        user = make_user(db, is_active=False)
        token = create_session(db, user)
        assert validate_session(db, token) is None


class TestRevokeAllForUser:
    def test_revokes_all_active_sessions(self):
        db = make_session()
        user = make_user(db)
        t1 = create_session(db, user)
        t2 = create_session(db, user)
        count = revoke_all_sessions_for_user(db, user.id)
        assert count == 2
        assert validate_session(db, t1) is None
        assert validate_session(db, t2) is None

    def test_does_not_revoke_other_users_sessions(self):
        db = make_session()
        u1 = make_user(db, email="u1@labo.fr")
        u2 = make_user(db, email="u2@labo.fr")
        t1 = create_session(db, u1)
        t2 = create_session(db, u2)
        revoke_all_sessions_for_user(db, u1.id)
        assert validate_session(db, t1) is None
        assert validate_session(db, t2) is not None
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_session_store.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api.session_store'`

- [ ] **Step 3: Implémenter `api/session_store.py`**

```python
# api/session_store.py
"""Cycle de vie des sessions de connexion — création, validation, révocation.

Sessions révocables côté serveur (pas de JWT) : chaque validation vérifie la
ligne en base, ce qui permet à un admin de couper l'accès d'un compte
instantanément (cf. api/routers/admin.py::revoke_sessions), sans attendre
l'expiration naturelle du token.
"""

from __future__ import annotations

import datetime
import secrets

from sqlalchemy.orm import Session as DBSession

from api.models import User, UserSession

SESSION_TTL_HOURS = 8
_TOKEN_BYTES = 32


def create_session(db: DBSession, user: User) -> str:
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    now = datetime.datetime.utcnow()
    row = UserSession(
        token=token,
        user_id=user.id,
        created_at=now,
        expires_at=now + datetime.timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(row)
    db.commit()
    return token


def validate_session(db: DBSession, token: str) -> User | None:
    row = db.get(UserSession, token)
    if row is None or row.revoked_at is not None:
        return None
    now = datetime.datetime.utcnow()
    if row.expires_at < now:
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None
    row.expires_at = now + datetime.timedelta(hours=SESSION_TTL_HOURS)  # glissant
    db.commit()
    return user


def revoke_session(db: DBSession, token: str) -> None:
    row = db.get(UserSession, token)
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.datetime.utcnow()
        db.commit()


def revoke_all_sessions_for_user(db: DBSession, user_id: int) -> int:
    now = datetime.datetime.utcnow()
    rows = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .all()
    )
    for row in rows:
        row.revoked_at = now
    db.commit()
    return len(rows)
```

- [ ] **Step 4: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_session_store.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add api/session_store.py tests/api/test_session_store.py
git commit -m "feat(api): cycle de vie des sessions révocables (create/validate/revoke)"
```

---

## Task 4: Authentification avec verrouillage anti-bruteforce

**Files:**
- Create: `api/auth.py`
- Test: `tests/api/test_auth.py`

**Interfaces:**
- Consumes: `api.models.User`, `api.security.verify_password`
- Produces: `api.auth.AuthError` (Enum : `INVALID_CREDENTIALS`, `ACCOUNT_LOCKED`), `api.auth.LOCK_THRESHOLD` (int, =5), `api.auth.LOCK_DURATION_MINUTES` (int, =15), `api.auth.authenticate_user(db, email: str, password: str) -> tuple[User | None, AuthError | None]`

- [ ] **Step 1: Écrire le test**

```python
# tests/api/test_auth.py
"""Tests de l'authentification avec verrouillage anti-bruteforce."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.auth import LOCK_DURATION_MINUTES, LOCK_THRESHOLD, AuthError, authenticate_user
from api.db import Base
from api.models import User
from api.security import hash_password


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def make_user(db, password="MotDePasseRobuste1!", **overrides):
    defaults = dict(
        email="tech@labo.fr", password_hash=hash_password(password),
        display_name="Tech", platform_role="user", is_active=True,
    )
    defaults.update(overrides)
    user = User(**defaults)
    db.add(user)
    db.commit()
    return user


class TestSuccessfulLogin:
    def test_correct_password_returns_user_no_error(self):
        db = make_session()
        make_user(db, password="MotDePasseRobuste1!")
        user, error = authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        assert error is None
        assert user is not None
        assert user.email == "tech@labo.fr"

    def test_success_resets_failed_count_and_sets_last_login(self):
        db = make_session()
        u = make_user(db, password="MotDePasseRobuste1!", failed_login_count=3)
        authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        db.refresh(u)
        assert u.failed_login_count == 0
        assert u.last_login_at is not None


class TestFailedLogin:
    def test_wrong_password_returns_invalid_credentials(self):
        db = make_session()
        make_user(db, password="MotDePasseRobuste1!")
        user, error = authenticate_user(db, "tech@labo.fr", "MauvaisMdp")
        assert user is None
        assert error == AuthError.INVALID_CREDENTIALS

    def test_unknown_email_returns_invalid_credentials(self):
        db = make_session()
        user, error = authenticate_user(db, "inconnu@labo.fr", "peuimporte")
        assert user is None
        assert error == AuthError.INVALID_CREDENTIALS

    def test_inactive_account_returns_invalid_credentials(self):
        db = make_session()
        make_user(db, password="MotDePasseRobuste1!", is_active=False)
        user, error = authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        assert user is None
        assert error == AuthError.INVALID_CREDENTIALS

    def test_wrong_password_increments_failed_count(self):
        db = make_session()
        u = make_user(db, password="MotDePasseRobuste1!")
        authenticate_user(db, "tech@labo.fr", "faux")
        db.refresh(u)
        assert u.failed_login_count == 1


class TestLockout:
    def test_lock_after_threshold_failures(self):
        db = make_session()
        u = make_user(db, password="MotDePasseRobuste1!")
        for _ in range(LOCK_THRESHOLD):
            authenticate_user(db, "tech@labo.fr", "faux")
        db.refresh(u)
        assert u.locked_until is not None
        assert u.locked_until > datetime.datetime.utcnow()

    def test_correct_password_rejected_while_locked(self):
        db = make_session()
        make_user(db, password="MotDePasseRobuste1!")
        for _ in range(LOCK_THRESHOLD):
            authenticate_user(db, "tech@labo.fr", "faux")
        user, error = authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        assert user is None
        assert error == AuthError.ACCOUNT_LOCKED

    def test_login_succeeds_after_lock_expires(self):
        db = make_session()
        u = make_user(db, password="MotDePasseRobuste1!")
        u.locked_until = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        u.failed_login_count = LOCK_THRESHOLD
        db.commit()
        user, error = authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        assert error is None
        assert user is not None
        db.refresh(u)
        assert u.failed_login_count == 0
        assert u.locked_until is None
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_auth.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api.auth'`

- [ ] **Step 3: Implémenter `api/auth.py`**

```python
# api/auth.py
"""Authentification par mot de passe avec verrouillage anti-bruteforce."""

from __future__ import annotations

import datetime
from enum import Enum

from sqlalchemy.orm import Session as DBSession

from api.models import User
from api.security import verify_password

LOCK_THRESHOLD = 5
LOCK_DURATION_MINUTES = 15


class AuthError(Enum):
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"


def authenticate_user(
    db: DBSession, email: str, password: str
) -> tuple[User | None, AuthError | None]:
    now = datetime.datetime.utcnow()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()

    if user is None:
        return None, AuthError.INVALID_CREDENTIALS

    if user.locked_until is not None and user.locked_until > now:
        return None, AuthError.ACCOUNT_LOCKED

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= LOCK_THRESHOLD:
            user.locked_until = now + datetime.timedelta(minutes=LOCK_DURATION_MINUTES)
        db.commit()
        return None, AuthError.INVALID_CREDENTIALS

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    return user, None
```

- [ ] **Step 4: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_auth.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add api/auth.py tests/api/test_auth.py
git commit -m "feat(api): authentification avec verrouillage anti-bruteforce"
```

---

## Task 5: API FastAPI — routes /auth (login, logout, me)

**Files:**
- Create: `api/schemas.py`
- Create: `api/dependencies.py`
- Create: `api/routers/__init__.py`
- Create: `api/routers/auth.py`
- Create: `api/main.py`
- Create: `tests/api/conftest.py`
- Test: `tests/api/test_auth_routes.py`

**Interfaces:**
- Consumes: `api.db.get_db`, `api.db.Base`, `api.auth.authenticate_user`, `api.auth.AuthError`, `api.session_store.create_session`, `api.session_store.revoke_session`, `api.models.User`
- Produces: `api.schemas.LoginRequest`, `api.schemas.MeResponse`, `api.dependencies.SESSION_COOKIE_NAME` (str, ="session_token"), `api.dependencies.get_current_user` (dépendance FastAPI), `api.dependencies.require_admin` (dépendance FastAPI), `api.main.app` (instance FastAPI), `api.routers.auth.COOKIE_SECURE` (bool, override en test)

- [ ] **Step 1: Créer le fixture de test partagé**

```python
# tests/api/conftest.py
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
```

- [ ] **Step 2: Écrire le test des routes /auth**

```python
# tests/api/test_auth_routes.py
"""Tests d'intégration des routes /auth/login, /auth/logout, /auth/me."""

from api.models import User
from api.security import hash_password


def make_user(db_session_factory, **overrides):
    defaults = dict(
        email="tech@labo.fr", password_hash=hash_password("MotDePasseRobuste1!"),
        display_name="Tech Un", platform_role="user", can_use_dsi_mode=False, is_active=True,
    )
    defaults.update(overrides)
    db = db_session_factory()
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.close()


class TestLogin:
    def test_correct_credentials_sets_cookie_and_returns_user(self, client, db_session_factory):
        make_user(db_session_factory)
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "MotDePasseRobuste1!"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "tech@labo.fr"
        assert resp.json()["can_use_dsi_mode"] is False
        assert "session_token" in resp.cookies

    def test_wrong_password_returns_401(self, client, db_session_factory):
        make_user(db_session_factory)
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "faux"})
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client, db_session_factory):
        resp = client.post("/auth/login", json={"email": "inconnu@labo.fr", "password": "peuimporte"})
        assert resp.status_code == 401


class TestMe:
    def test_me_without_login_returns_401(self, client, db_session_factory):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_after_login_returns_current_user(self, client, db_session_factory):
        make_user(db_session_factory, display_name="Tech Un")
        client.post("/auth/login", json={"email": "tech@labo.fr", "password": "MotDePasseRobuste1!"})
        resp = client.get("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Tech Un"


class TestLogout:
    def test_logout_then_me_returns_401(self, client, db_session_factory):
        make_user(db_session_factory)
        client.post("/auth/login", json={"email": "tech@labo.fr", "password": "MotDePasseRobuste1!"})
        logout_resp = client.post("/auth/logout")
        assert logout_resp.status_code == 200
        me_resp = client.get("/auth/me")
        assert me_resp.status_code == 401
```

- [ ] **Step 3: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_auth_routes.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api.main'`

- [ ] **Step 4: Implémenter `api/schemas.py`**

```python
# api/schemas.py
"""Schémas Pydantic — requêtes et réponses de l'API."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: int
    email: str
    display_name: str
    platform_role: str
    can_use_dsi_mode: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Implémenter `api/dependencies.py`**

```python
# api/dependencies.py
"""Dépendances FastAPI — utilisateur courant, garde admin."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.models import User
from api.session_store import validate_session

SESSION_COOKIE_NAME = "session_token"


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié")
    user = validate_session(db, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.platform_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs")
    return user
```

- [ ] **Step 6: Implémenter `api/routers/__init__.py`**

```python
# api/routers/__init__.py
```

(fichier vide)

- [ ] **Step 7: Implémenter `api/routers/auth.py`**

```python
# api/routers/auth.py
"""Routes d'authentification : login, logout, utilisateur courant."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DBSession

from api.auth import AuthError, authenticate_user
from api.db import get_db
from api.dependencies import SESSION_COOKIE_NAME, get_current_user
from api.models import User
from api.schemas import LoginRequest, MeResponse
from api.session_store import SESSION_TTL_HOURS, create_session, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])

# True en production (HTTPS obligatoire) ; désactivé dans les tests (TestClient
# tourne sur http://testserver, cf. tests/api/conftest.py).
COOKIE_SECURE = True


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db: DBSession = Depends(get_db)):
    user, error = authenticate_user(db, payload.email, payload.password)
    if error is not None:
        code = status.HTTP_423_LOCKED if error == AuthError.ACCOUNT_LOCKED else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=code, detail=error.value)

    token = create_session(db, user)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        max_age=SESSION_TTL_HOURS * 3600,
    )
    return user


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        revoke_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"detail": "déconnecté"}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 8: Implémenter `api/main.py`**

```python
# api/main.py
"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db import Base, engine
from api.routers import auth


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
```

- [ ] **Step 9: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_auth_routes.py -v`
Expected: PASS (6 tests)

- [ ] **Step 10: Commit**

```bash
git add api/schemas.py api/dependencies.py api/routers/__init__.py api/routers/auth.py api/main.py tests/api/conftest.py tests/api/test_auth_routes.py
git commit -m "feat(api): routes /auth/login /auth/logout /auth/me"
```

---

## Task 6: Routes admin — gestion des comptes

**Files:**
- Modify: `api/schemas.py`
- Create: `api/routers/admin.py`
- Modify: `api/main.py`
- Test: `tests/api/test_admin_routes.py`

**Interfaces:**
- Consumes: `api.dependencies.require_admin`, `api.session_store.revoke_all_sessions_for_user`, `api.security.hash_password`, `api.security.generate_temp_password`
- Produces: `api.schemas.UserOut`, `api.schemas.CreateUserRequest`, `api.schemas.CreateUserResponse`, `api.schemas.UpdateUserRequest`, `api.schemas.ResetPasswordResponse`, routes `POST/GET /admin/users`, `PATCH /admin/users/{id}`, `POST /admin/users/{id}/reset-password`, `POST /admin/users/{id}/revoke-sessions`

- [ ] **Step 1: Écrire le test**

```python
# tests/api/test_admin_routes.py
"""Tests d'intégration des routes /admin/users."""

from api.models import User
from api.security import hash_password


def make_admin(db_session_factory, email="admin@labo.fr"):
    db = db_session_factory()
    user = User(
        email=email, password_hash=hash_password("AdminMdp1!"),
        display_name="Admin", platform_role="admin", can_use_dsi_mode=True, is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()


def make_regular_user(db_session_factory, email="tech@labo.fr"):
    db = db_session_factory()
    user = User(
        email=email, password_hash=hash_password("TechMdp1!"),
        display_name="Tech", platform_role="user", can_use_dsi_mode=False, is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()
    return user


def login_as(client, email, password):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp


class TestCreateUser:
    def test_admin_can_create_user(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post("/admin/users", json={
            "email": "nouveau@labo.fr", "display_name": "Nouveau Tech",
            "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "nouveau@labo.fr"
        assert "temporary_password" in body
        assert len(body["temporary_password"]) >= 12

    def test_non_admin_cannot_create_user(self, client, db_session_factory):
        make_regular_user(db_session_factory)
        login_as(client, "tech@labo.fr", "TechMdp1!")
        resp = client.post("/admin/users", json={
            "email": "x@labo.fr", "display_name": "X", "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_user(self, client, db_session_factory):
        resp = client.post("/admin/users", json={
            "email": "x@labo.fr", "display_name": "X", "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 401

    def test_duplicate_email_rejected(self, client, db_session_factory):
        make_admin(db_session_factory)
        make_regular_user(db_session_factory, email="existe@labo.fr")
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post("/admin/users", json={
            "email": "existe@labo.fr", "display_name": "X", "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 409


class TestListUsers:
    def test_admin_can_list_users(self, client, db_session_factory):
        make_admin(db_session_factory)
        make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.get("/admin/users")
        assert resp.status_code == 200
        emails = {u["email"] for u in resp.json()}
        assert {"admin@labo.fr", "tech@labo.fr"} <= emails


class TestUpdateUser:
    def test_admin_can_toggle_dsi_mode(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.patch(f"/admin/users/{user.id}", json={"can_use_dsi_mode": True})
        assert resp.status_code == 200
        assert resp.json()["can_use_dsi_mode"] is True

    def test_cannot_demote_last_active_admin(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        db = db_session_factory()
        admin = db.query(User).filter(User.email == "admin@labo.fr").one()
        admin_id = admin.id
        db.close()
        resp = client.patch(f"/admin/users/{admin_id}", json={"platform_role": "user"})
        assert resp.status_code == 409

    def test_cannot_deactivate_last_active_admin(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        db = db_session_factory()
        admin = db.query(User).filter(User.email == "admin@labo.fr").one()
        admin_id = admin.id
        db.close()
        resp = client.patch(f"/admin/users/{admin_id}", json={"is_active": False})
        assert resp.status_code == 409


class TestResetPassword:
    def test_reset_generates_new_temp_password(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post(f"/admin/users/{user.id}/reset-password")
        assert resp.status_code == 200
        assert len(resp.json()["temporary_password"]) >= 12

    def test_old_password_rejected_after_reset(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        client.post(f"/admin/users/{user.id}/reset-password")
        client.post("/auth/logout")
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "TechMdp1!"})
        assert resp.status_code == 401


class TestRevokeSessions:
    def test_revoke_kills_active_session_immediately(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)

        # Le technicien se connecte dans un client séparé pour garder sa propre session
        from fastapi.testclient import TestClient
        from api.main import app
        tech_client = TestClient(app)
        login_as(tech_client, "tech@labo.fr", "TechMdp1!")
        assert tech_client.get("/auth/me").status_code == 200

        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post(f"/admin/users/{user.id}/revoke-sessions")
        assert resp.status_code == 200
        assert resp.json()["revoked"] == 1

        assert tech_client.get("/auth/me").status_code == 401
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_admin_routes.py -v`
Expected: FAIL avec `404 Not Found` sur `/admin/users` (route inexistante) — les assertions échouent sur les codes de statut

- [ ] **Step 3: Ajouter les schémas admin à `api/schemas.py`**

Ajouter à la fin de `api/schemas.py` :

```python
class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    platform_role: str
    can_use_dsi_mode: bool
    is_active: bool

    model_config = {"from_attributes": True}


class CreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str
    platform_role: str
    can_use_dsi_mode: bool = False


class CreateUserResponse(UserOut):
    temporary_password: str


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    platform_role: str | None = None
    can_use_dsi_mode: bool | None = None
    is_active: bool | None = None


class ResetPasswordResponse(BaseModel):
    temporary_password: str


class RevokeSessionsResponse(BaseModel):
    revoked: int
```

- [ ] **Step 4: Implémenter `api/routers/admin.py`**

```python
# api/routers/admin.py
"""Routes admin : création/gestion des comptes techniciens."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import require_admin
from api.models import User
from api.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordResponse,
    RevokeSessionsResponse,
    UpdateUserRequest,
    UserOut,
)
from api.security import generate_temp_password, hash_password
from api.session_store import revoke_all_sessions_for_user

router = APIRouter(prefix="/admin", tags=["admin"])


def _count_active_admins(db: DBSession) -> int:
    return (
        db.query(User)
        .filter(User.platform_role == "admin", User.is_active.is_(True))
        .count()
    )


def _get_user_or_404(db: DBSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user


@router.post("/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if payload.platform_role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="platform_role doit être 'admin' ou 'user'")
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    temp_password = generate_temp_password()
    user = User(
        email=payload.email,
        password_hash=hash_password(temp_password),
        display_name=payload.display_name,
        platform_role=payload.platform_role,
        can_use_dsi_mode=payload.can_use_dsi_mode,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return CreateUserResponse(
        **UserOut.model_validate(user).model_dump(), temporary_password=temp_password
    )


@router.get("/users", response_model=list[UserOut])
def list_users(db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)

    would_demote = (
        payload.platform_role is not None
        and payload.platform_role != "admin"
        and user.platform_role == "admin"
    )
    would_deactivate = payload.is_active is False and user.platform_role == "admin"
    if (would_demote or would_deactivate) and _count_active_admins(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de désactiver/rétrograder le dernier administrateur actif",
        )

    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.platform_role is not None:
        if payload.platform_role not in ("admin", "user"):
            raise HTTPException(status_code=422, detail="platform_role doit être 'admin' ou 'user'")
        user.platform_role = payload.platform_role
    if payload.can_use_dsi_mode is not None:
        user.can_use_dsi_mode = payload.can_use_dsi_mode
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    user_id: int, db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    user = _get_user_or_404(db, user_id)
    temp_password = generate_temp_password()
    user.password_hash = hash_password(temp_password)
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return ResetPasswordResponse(temporary_password=temp_password)


@router.post("/users/{user_id}/revoke-sessions", response_model=RevokeSessionsResponse)
def revoke_sessions(
    user_id: int, db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    _get_user_or_404(db, user_id)
    count = revoke_all_sessions_for_user(db, user_id)
    return RevokeSessionsResponse(revoked=count)
```

- [ ] **Step 5: Enregistrer le router admin dans `api/main.py`**

```python
# api/main.py
"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db import Base, engine
from api.routers import admin, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MISPL Agent API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(admin.router)
```

- [ ] **Step 6: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_admin_routes.py -v`
Expected: PASS (11 tests)

- [ ] **Step 7: Commit**

```bash
git add api/schemas.py api/routers/admin.py api/main.py tests/api/test_admin_routes.py
git commit -m "feat(api): routes admin — CRUD comptes, reset mdp, révocation de sessions"
```

---

## Task 7: Bootstrap du premier compte admin

**Files:**
- Create: `api/admin_bootstrap.py`
- Create: `scripts/create_admin.py`
- Test: `tests/api/test_admin_bootstrap.py`

**Interfaces:**
- Consumes: `api.models.User`, `api.security.hash_password`
- Produces: `api.admin_bootstrap.create_admin_account(db, email: str, display_name: str, password: str) -> User` (lève `ValueError` si email déjà utilisé ou mot de passe < 8 caractères)

- [ ] **Step 1: Écrire le test**

```python
# tests/api/test_admin_bootstrap.py
"""Tests de la logique de création du premier compte admin."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.admin_bootstrap import create_admin_account
from api.db import Base
from api.models import User
from api.security import verify_password


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestCreateAdminAccount:
    def test_creates_admin_with_correct_flags(self):
        db = make_session()
        user = create_admin_account(db, "admin@labo.fr", "Florian", "MotDePasseSolide1!")
        assert user.platform_role == "admin"
        assert user.can_use_dsi_mode is True
        assert user.is_active is True

    def test_password_is_hashed_and_verifiable(self):
        db = make_session()
        create_admin_account(db, "admin@labo.fr", "Florian", "MotDePasseSolide1!")
        stored = db.query(User).filter(User.email == "admin@labo.fr").one()
        assert verify_password("MotDePasseSolide1!", stored.password_hash)

    def test_duplicate_email_raises(self):
        db = make_session()
        create_admin_account(db, "admin@labo.fr", "Florian", "MotDePasseSolide1!")
        with pytest.raises(ValueError, match="déjà"):
            create_admin_account(db, "admin@labo.fr", "Autre", "AutreMotDePasse1!")

    def test_short_password_raises(self):
        db = make_session()
        with pytest.raises(ValueError, match="8 caractères"):
            create_admin_account(db, "admin@labo.fr", "Florian", "court")
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_admin_bootstrap.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api.admin_bootstrap'`

- [ ] **Step 3: Implémenter `api/admin_bootstrap.py`**

```python
# api/admin_bootstrap.py
"""Création du tout premier compte admin — logique testable, appelée par
scripts/create_admin.py. Aucune route API ne peut créer un compte admin :
c'est le seul point d'entrée."""

from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from api.models import User
from api.security import hash_password


def create_admin_account(db: DBSession, email: str, display_name: str, password: str) -> User:
    if len(password) < 8:
        raise ValueError("Le mot de passe doit faire au moins 8 caractères")
    if db.query(User).filter(User.email == email).first() is not None:
        raise ValueError(f"Un compte existe déjà avec l'email {email}")

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        platform_role="admin",
        can_use_dsi_mode=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Step 4: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_admin_bootstrap.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Implémenter le script CLI `scripts/create_admin.py`**

```python
# scripts/create_admin.py
"""Crée le tout premier compte admin de la plateforme.

Usage : python scripts/create_admin.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from api.admin_bootstrap import create_admin_account  # noqa: E402
from api.db import SessionLocal  # noqa: E402


def main() -> None:
    email = input("Email admin : ").strip()
    display_name = input("Nom affiché : ").strip()
    password = getpass.getpass("Mot de passe (8 caractères min.) : ")
    confirm = getpass.getpass("Confirmer : ")

    if password != confirm:
        print("Les mots de passe ne correspondent pas.")
        sys.exit(1)

    db = SessionLocal()
    try:
        create_admin_account(db, email, display_name, password)
    except ValueError as e:
        print(f"Erreur : {e}")
        sys.exit(1)
    finally:
        db.close()

    print(f"Compte admin créé : {email}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Commit**

```bash
git add api/admin_bootstrap.py scripts/create_admin.py tests/api/test_admin_bootstrap.py
git commit -m "feat(api): bootstrap CLI du premier compte admin"
```

---

## Task 8: Helper de dérivation du mode d'accès + vérification finale

**Files:**
- Modify: `src/security/access_mode.py`
- Modify: `tests/security/test_access_mode.py`

**Interfaces:**
- Consumes: `api.models.User.can_use_dsi_mode` (bool, conceptuellement — pas d'import direct pour éviter un couplage `src/` → `api/`)
- Produces: `src.security.access_mode.access_mode_for_user(can_use_dsi_mode: bool) -> str`

**Note :** ce helper prend un `bool` en paramètre, pas un objet `User` — `src/` ne doit pas dépendre de `api/` (sens de dépendance : `api/` peut dépendre de `src/`, jamais l'inverse, pour que la logique métier RAG/linter reste indépendante de la couche web). C'est la future route API (`/auth/login`, chantier historique de sessions) qui appellera `access_mode_for_user(user.can_use_dsi_mode)` avant de passer le résultat à `ask_mispl(access_mode=...)`.

- [ ] **Step 1: Écrire le test**

Ajouter à `tests/security/test_access_mode.py` :

```python
from src.security.access_mode import access_mode_for_user


class TestAccessModeForUser:
    def test_dsi_flag_true_gives_dsi_mode(self):
        assert access_mode_for_user(True) == MODE_DSI

    def test_dsi_flag_false_gives_technicien_mode(self):
        assert access_mode_for_user(False) == MODE_TECHNICIEN
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/security/test_access_mode.py -v`
Expected: FAIL avec `ImportError: cannot import name 'access_mode_for_user'`

- [ ] **Step 3: Ajouter le helper dans `src/security/access_mode.py`**

Ajouter à la fin du fichier, après `enforce_access_mode` :

```python
def access_mode_for_user(can_use_dsi_mode: bool) -> str:
    """
    Dérive le mode de génération depuis l'attribut de compte can_use_dsi_mode.

    Remplace, pour la future API de comptes, le mécanisme historique de mot
    de passe DSI partagé (verify_dsi_password ci-dessus). Ce dernier reste en
    place pour l'instant : app.py (Streamlit, toujours en production) en
    dépend encore, et sa migration est un chantier séparé.
    """
    return MODE_DSI if can_use_dsi_mode else MODE_TECHNICIEN
```

- [ ] **Step 4: Lancer le test, vérifier le succès**

Run: `pytest tests/security/test_access_mode.py -v`
Expected: PASS (tous les tests, y compris les 2 nouveaux)

- [ ] **Step 5: Lancer la suite de tests complète**

Run: `pytest tests/ -v`
Expected: PASS — tous les tests existants (linter, DLP, cache, RAG) + tous les nouveaux tests `tests/api/*` (Tasks 1-7)

- [ ] **Step 6: Commit**

```bash
git add src/security/access_mode.py tests/security/test_access_mode.py
git commit -m "feat(security): access_mode_for_user() — dérive le mode depuis un compte, sans coupler src/ à api/"
```

---

## Récapitulatif — ce que ce plan ne couvre PAS

Rappel du périmètre de la spec, pour éviter toute confusion lors de la reprise du travail :
- Pas d'interface graphique admin (les routes `/admin/*` se testent via Swagger `/docs` ou `httpx`/`curl`)
- Pas de migration de `app.py` — Streamlit continue d'utiliser l'ancien mécanisme de mot de passe DSI partagé jusqu'au chantier de migration frontend
- Pas d'historique de sessions de chat, pas de quotas, pas de dashboard analytics — chantiers suivants, dépendant de celui-ci mais non traités ici
