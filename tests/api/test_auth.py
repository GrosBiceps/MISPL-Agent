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
