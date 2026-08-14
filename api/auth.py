"""Authentification par mot de passe avec verrouillage anti-bruteforce."""

from __future__ import annotations

import datetime
from enum import Enum

from sqlalchemy.orm import Session as DBSession

from api.models import User
from api.security import hash_password, verify_password

LOCK_THRESHOLD = 5
LOCK_DURATION_MINUTES = 15

# Hash Argon2 factice constant, généré une seule fois au chargement du module
# (pas à chaque appel) : sert à égaliser le temps de réponse entre un email
# inconnu/inactif et un mauvais mot de passe, pour empêcher un attaquant de
# déduire l'existence d'un compte par mesure de latence (Argon2 prend
# plusieurs dizaines de ms, contrairement à un retour immédiat).
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")


class AuthError(Enum):
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"


def authenticate_user(
    db: DBSession, email: str, password: str
) -> tuple[User | None, AuthError | None]:
    now = datetime.datetime.utcnow()
    email = email.lower().strip()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()

    if user is None:
        # Email inconnu OU compte inactif : on appelle quand même verify_password
        # sur un hash factice pour que le temps de réponse soit indistinguable
        # d'un mauvais mot de passe (cf. commentaire _DUMMY_HASH ci-dessus).
        verify_password(password, _DUMMY_HASH)
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
