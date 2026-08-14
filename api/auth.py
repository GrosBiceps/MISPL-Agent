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
