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
