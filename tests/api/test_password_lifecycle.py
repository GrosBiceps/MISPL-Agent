"""Cycle de vie des mots de passe (lot A, 2026-09-24) : paramètres Argon2id,
re-hachage transparent, politique, mot de passe temporaire à changer, absence
de toute fuite du mot de passe en clair (base, réponses, audit)."""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from argon2 import PasswordHasher, Type
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import api.auth as auth_module
from api.auth import LOCK_THRESHOLD, authenticate_user
from api.db import Base, upgrade_schema
from api.models import AuditEvent, User, UserSession
from api.security import (
    ARGON2_HASH_LEN,
    ARGON2_MEMORY_COST_KIB,
    ARGON2_PARALLELISM,
    ARGON2_SALT_LEN,
    ARGON2_TIME_COST,
    hash_password,
    needs_rehash,
    password_policy_errors,
    verify_password,
)

ADMIN_PASSWORD = "AdminMdp1!Solide"
NEW_PASSWORD = "Nouveau-Secret-2026!"


def _b64(s: str) -> bytes:
    return base64.b64decode(s + "=" * (-len(s) % 4))


def _weak_hash(password: str) -> str:
    return PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID).hash(password)


def make_admin(db_session_factory, email="admin@labo.fr"):
    db = db_session_factory()
    user = User(
        email=email, password_hash=hash_password(ADMIN_PASSWORD),
        display_name="Admin", platform_role="admin", can_use_dsi_mode=True, is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()
    return user


def login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def create_user_via_admin(client, db_session_factory, email="tech@labo.fr"):
    make_admin(db_session_factory)
    assert login(client, "admin@labo.fr", ADMIN_PASSWORD).status_code == 200
    resp = client.post("/admin/users", json={
        "email": email, "display_name": "Tech Labo", "platform_role": "user", "can_use_dsi_mode": False,
    })
    assert resp.status_code == 201
    client.post("/auth/logout")
    return resp.json()


def all_text_in_db(db) -> str:
    """Concatène toutes les valeurs de toutes les tables (recherche de fuite)."""
    chunks = []
    for table in Base.metadata.sorted_tables:
        for row in db.execute(table.select()).fetchall():
            chunks.extend(str(v) for v in row)
    return "\n".join(chunks)


# ── Paramètres Argon2id ────────────────────────────────────────────────────────

class TestArgon2Parameters:
    def test_hash_is_argon2id_with_pinned_parameters(self):
        h = hash_password("MotDePasseRobuste1!")
        parts = h.split("$")
        assert parts[1] == "argon2id"
        assert parts[2] == "v=19"
        assert parts[3] == f"m={ARGON2_MEMORY_COST_KIB},t={ARGON2_TIME_COST},p={ARGON2_PARALLELISM}"
        assert len(_b64(parts[4])) == ARGON2_SALT_LEN == 16
        assert len(_b64(parts[5])) == ARGON2_HASH_LEN == 32

    def test_parameters_meet_owasp_minimum(self):
        # OWASP Password Storage Cheat Sheet : m >= 19 Mio, t >= 2, p >= 1.
        assert ARGON2_MEMORY_COST_KIB >= 19 * 1024
        assert ARGON2_TIME_COST >= 2
        assert ARGON2_PARALLELISM >= 1

    def test_hash_never_contains_plaintext(self):
        pwd = "MotDePasseRobuste1!"
        assert pwd not in hash_password(pwd)

    def test_needs_rehash(self):
        assert needs_rehash(hash_password("x" * 12)) is False
        assert needs_rehash(_weak_hash("x" * 12)) is True
        assert needs_rehash("pas-un-hash") is True
        # Variante argon2i (non id) : à recalculer.
        assert needs_rehash(PasswordHasher(type=Type.I).hash("x")) is True

    def test_verify_never_raises(self):
        assert verify_password("x", "") is False
        assert verify_password("x", "$argon2id$v=19$m=65536,t=3,p=4$AAAA$BBBB") is False


# ── Re-hachage transparent à la connexion ────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class TestTransparentRehash:
    def test_weak_hash_upgraded_on_successful_login(self):
        db = make_session()
        db.add(User(email="tech@labo.fr", password_hash=_weak_hash("MotDePasseRobuste1!"),
                    display_name="Tech", platform_role="user", is_active=True))
        db.commit()
        user, error = authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        assert error is None
        assert needs_rehash(user.password_hash) is False
        assert verify_password("MotDePasseRobuste1!", user.password_hash)
        events = [e.event for e in db.query(AuditEvent).all()]
        assert "password_rehashed" in events

    def test_no_rehash_on_failed_login(self):
        db = make_session()
        weak = _weak_hash("MotDePasseRobuste1!")
        db.add(User(email="tech@labo.fr", password_hash=weak,
                    display_name="Tech", platform_role="user", is_active=True))
        db.commit()
        authenticate_user(db, "tech@labo.fr", "mauvais")
        assert db.query(User).one().password_hash == weak

    def test_current_hash_left_untouched(self):
        db = make_session()
        h = hash_password("MotDePasseRobuste1!")
        db.add(User(email="tech@labo.fr", password_hash=h,
                    display_name="Tech", platform_role="user", is_active=True))
        db.commit()
        user, _ = authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        assert user.password_hash == h

    def test_locked_account_still_pays_argon2_cost(self, monkeypatch):
        """Égalisation temporelle : le chemin « compte verrouillé » appelle
        verify_password comme les autres chemins d'échec."""
        db = make_session()
        db.add(User(email="tech@labo.fr", password_hash=hash_password("MotDePasseRobuste1!"),
                    display_name="Tech", platform_role="user", is_active=True))
        db.commit()
        for _ in range(LOCK_THRESHOLD):
            authenticate_user(db, "tech@labo.fr", "mauvais")
        calls = []
        real = auth_module.verify_password
        monkeypatch.setattr(auth_module, "verify_password", lambda p, h: calls.append(1) or real(p, h))
        _, error = authenticate_user(db, "tech@labo.fr", "MotDePasseRobuste1!")
        assert error is auth_module.AuthError.ACCOUNT_LOCKED
        assert calls == [1]


# ── Politique ─────────────────────────────────────────────────────────────────

class TestPasswordPolicy:
    @pytest.mark.parametrize("pwd", ["Court1!", "toutminuscule", "motdepasse123", "aaaaaaaaaaaaaaaaaa"])
    def test_rejected(self, pwd):
        assert password_policy_errors(pwd)

    @pytest.mark.parametrize("pwd", ["Labo-Hemato-42", "cheval batterie agrafe correcte"])
    def test_accepted(self, pwd):
        assert password_policy_errors(pwd) == []

    def test_contains_identifier_rejected(self):
        assert password_policy_errors("Dupont-2026-Labo!", email="jean.dupont@labo.fr", display_name="Jean Dupont")

    def test_too_long_rejected(self):
        assert password_policy_errors("Aa1!" * 70)

    def test_messages_never_echo_password(self):
        pwd = "motdepasse123"
        assert all(pwd not in m for m in password_policy_errors(pwd))


# ── Mot de passe temporaire : changement obligatoire ───────────────────────────────

class TestForcedPasswordChange:
    def test_created_user_must_change_password(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        assert body["must_change_password"] is True
        assert login(client, "tech@labo.fr", body["temporary_password"]).status_code == 200
        me = client.get("/auth/me")
        assert me.status_code == 200 and me.json()["must_change_password"] is True
        resp = client.get("/conversations")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "password_change_required"
        assert client.post("/chat/ask", json={"question": "Substr"}).status_code == 403

    def test_temp_password_never_stored_in_clear(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        db = db_session_factory()
        assert body["temporary_password"] not in all_text_in_db(db)

    def test_change_password_success(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        login(client, "tech@labo.fr", body["temporary_password"])
        resp = client.post("/auth/change-password", json={
            "current_password": body["temporary_password"], "new_password": NEW_PASSWORD,
        })
        assert resp.status_code == 200
        assert NEW_PASSWORD not in resp.text
        assert client.get("/conversations").status_code == 200
        assert client.get("/auth/me").json()["must_change_password"] is False
        client.post("/auth/logout")
        assert login(client, "tech@labo.fr", body["temporary_password"]).status_code == 401
        assert login(client, "tech@labo.fr", NEW_PASSWORD).status_code == 200
        db = db_session_factory()
        text_dump = all_text_in_db(db)
        assert NEW_PASSWORD not in text_dump
        assert body["temporary_password"] not in text_dump

    def test_change_password_revokes_other_sessions_only(self, client, db_session_factory):
        from fastapi.testclient import TestClient
        from api.main import app

        body = create_user_via_admin(client, db_session_factory)
        other = TestClient(app)
        assert login(other, "tech@labo.fr", body["temporary_password"]).status_code == 200
        login(client, "tech@labo.fr", body["temporary_password"])
        client.post("/auth/change-password", json={
            "current_password": body["temporary_password"], "new_password": NEW_PASSWORD,
        })
        assert client.get("/auth/me").status_code == 200
        assert other.get("/auth/me").status_code == 401

    def test_wrong_current_password_rejected_and_counted(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        login(client, "tech@labo.fr", body["temporary_password"])
        resp = client.post("/auth/change-password", json={
            "current_password": "pas-le-bon", "new_password": NEW_PASSWORD,
        })
        assert resp.status_code == 400
        db = db_session_factory()
        assert db.query(User).filter(User.email == "tech@labo.fr").one().failed_login_count == 1

    def test_locked_account_cannot_change_password(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        login(client, "tech@labo.fr", body["temporary_password"])
        for _ in range(LOCK_THRESHOLD):
            client.post("/auth/change-password", json={"current_password": "x", "new_password": NEW_PASSWORD})
        resp = client.post("/auth/change-password", json={
            "current_password": body["temporary_password"], "new_password": NEW_PASSWORD,
        })
        assert resp.status_code == 400

    def test_weak_new_password_rejected_without_echo(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        login(client, "tech@labo.fr", body["temporary_password"])
        resp = client.post("/auth/change-password", json={
            "current_password": body["temporary_password"], "new_password": "faible",
        })
        assert resp.status_code == 422
        assert "faible" not in resp.text
        assert body["temporary_password"] not in resp.text

    def test_same_password_rejected(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        login(client, "tech@labo.fr", body["temporary_password"])
        resp = client.post("/auth/change-password", json={
            "current_password": body["temporary_password"], "new_password": body["temporary_password"],
        })
        assert resp.status_code == 422

    def test_admin_reset_forces_change_again(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        login(client, "tech@labo.fr", body["temporary_password"])
        client.post("/auth/change-password", json={
            "current_password": body["temporary_password"], "new_password": NEW_PASSWORD,
        })
        client.post("/auth/logout")
        login(client, "admin@labo.fr", ADMIN_PASSWORD)
        resp = client.post(f"/admin/users/{body['id']}/reset-password")
        assert resp.status_code == 200
        client.post("/auth/logout")
        login(client, "tech@labo.fr", resp.json()["temporary_password"])
        assert client.get("/conversations").status_code == 403

    def test_change_password_requires_session(self, client, db_session_factory):
        resp = client.post("/auth/change-password", json={"current_password": "a", "new_password": NEW_PASSWORD})
        assert resp.status_code == 401


# ── Absence de fuite dans les réponses et le journal d'audit ───────────────────────

class TestNoPasswordLeak:
    def test_validation_error_does_not_echo_password(self, client, db_session_factory):
        secret = "S3cret-" + "x" * 300
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": secret})
        assert resp.status_code == 422
        assert "S3cret-" not in resp.text

    def test_validation_error_keeps_message(self, client, db_session_factory):
        resp = client.post("/auth/login", json={"email": "pas-un-email", "password": "x"})
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail and "msg" in detail[0] and "input" not in detail[0]

    def test_api_responses_not_cacheable(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        assert body  # la création a réussi
        login(client, "admin@labo.fr", ADMIN_PASSWORD)
        resp = client.post(f"/admin/users/{body['id']}/reset-password")
        assert resp.headers.get("Cache-Control") == "no-store"
        assert client.get("/auth/me").headers.get("Cache-Control") == "no-store"

    def test_audit_trail_records_events_without_secrets(self, client, db_session_factory):
        body = create_user_via_admin(client, db_session_factory)
        login(client, "tech@labo.fr", "mauvais-mot-de-passe")
        login(client, "tech@labo.fr", body["temporary_password"])
        client.post("/auth/change-password", json={
            "current_password": body["temporary_password"], "new_password": NEW_PASSWORD,
        })
        db = db_session_factory()
        events = [e.event for e in db.query(AuditEvent).order_by(AuditEvent.id).all()]
        for expected in ("login_success", "admin_user_created", "logout", "login_failure", "password_changed"):
            assert expected in events
        dump = "\n".join(
            f"{e.event}|{e.detail}|{e.source_ip}" for e in db.query(AuditEvent).all()
        )
        for secret in (ADMIN_PASSWORD, body["temporary_password"], NEW_PASSWORD, "mauvais-mot-de-passe"):
            assert secret not in dump
        tokens = [s.token for s in db.query(UserSession).all()]
        assert all(t not in dump for t in tokens)


# ── Migration de schéma non destructive ────────────────────────────────────────

class TestSchemaUpgrade:
    def test_adds_missing_column_and_keeps_rows(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL, password_hash VARCHAR NOT NULL, "
                "display_name VARCHAR NOT NULL, platform_role VARCHAR NOT NULL, can_use_dsi_mode BOOLEAN NOT NULL, "
                "is_active BOOLEAN NOT NULL, failed_login_count INTEGER NOT NULL, locked_until DATETIME, "
                "created_at DATETIME NOT NULL, last_login_at DATETIME)"
            ))
            conn.execute(text(
                "INSERT INTO users VALUES (1, 'a@labo.fr', 'h', 'A', 'admin', 1, 1, 0, NULL, '2026-01-01', NULL)"
            ))
        added = upgrade_schema(engine)
        assert added == ["users.must_change_password"]
        cols = {c["name"] for c in inspect(engine).get_columns("users")}
        assert "must_change_password" in cols
        assert "audit_events" in inspect(engine).get_table_names()
        db = sessionmaker(bind=engine)()
        user = db.query(User).one()
        assert user.must_change_password is False and user.email == "a@labo.fr"
        assert upgrade_schema(engine) == []  # idempotent


class TestCorsOrigins:
    def test_wildcard_refused(self):
        from api.main import parse_frontend_origins
        with pytest.raises(ValueError):
            parse_frontend_origins("http://localhost:3000,*")

    def test_list_parsed(self):
        from api.main import parse_frontend_origins
        assert parse_frontend_origins(" http://a:3000 , https://b ") == ["http://a:3000", "https://b"]
