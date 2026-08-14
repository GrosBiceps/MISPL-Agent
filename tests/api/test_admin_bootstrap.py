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
