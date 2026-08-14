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
