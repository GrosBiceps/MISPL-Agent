"""Tests des modèles ORM users/sessions — DB en mémoire, sans FastAPI."""

import datetime

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
