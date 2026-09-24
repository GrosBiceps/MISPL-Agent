"""Authentification par mot de passe avec verrouillage anti-bruteforce,
re-hachage transparent et journal d'audit."""

from __future__ import annotations

import datetime
from enum import Enum

from sqlalchemy.orm import Session as DBSession

from api import audit
from api.models import User
from api.security import hash_password, needs_rehash, verify_password

LOCK_THRESHOLD = 5
LOCK_DURATION_MINUTES = 15

# Hash Argon2 factice constant, généré une seule fois au chargement du module
# (pas à chaque appel) : sert à égaliser le temps de réponse entre un email
# inconnu/inactif, un compte verrouillé et un mauvais mot de passe, pour
# empêcher un attaquant de déduire l'existence ou l'état d'un compte par
# mesure de latence (Argon2 prend plusieurs dizaines de ms, contrairement à
# un retour immédiat).
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")


class AuthError(Enum):
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"


def register_failed_attempt(db: DBSession, user: User, now: datetime.datetime, source_ip: str | None) -> None:
    """Incrémente le compteur d'échecs et verrouille le compte au seuil.
    Partagé entre la connexion et le changement de mot de passe (un mauvais
    mot de passe actuel compte comme une tentative de connexion ratée)."""
    user.failed_login_count += 1
    locked_now = user.failed_login_count >= LOCK_THRESHOLD
    if locked_now:
        user.locked_until = now + datetime.timedelta(minutes=LOCK_DURATION_MINUTES)
    db.commit()
    if locked_now:
        audit.record_event(db, audit.ACCOUNT_LOCKED, target_user_id=user.id, source_ip=source_ip)


def authenticate_user(
    db: DBSession, email: str, password: str, source_ip: str | None = None
) -> tuple[User | None, AuthError | None]:
    now = datetime.datetime.utcnow()
    email = email.lower().strip()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()

    if user is None:
        # Email inconnu OU compte inactif : on appelle quand même verify_password
        # sur un hash factice pour que le temps de réponse soit indistinguable
        # d'un mauvais mot de passe (cf. commentaire _DUMMY_HASH ci-dessus).
        verify_password(password, _DUMMY_HASH)
        audit.record_event(db, audit.LOGIN_FAILURE, source_ip=source_ip, detail="unknown_or_inactive")
        return None, AuthError.INVALID_CREDENTIALS

    if user.locked_until is not None and user.locked_until > now:
        # Même coût qu'une vraie vérification : un retour immédiat révélerait
        # par la latence qu'un compte existe et qu'il est verrouillé.
        verify_password(password, _DUMMY_HASH)
        audit.record_event(db, audit.LOGIN_FAILURE, target_user_id=user.id, source_ip=source_ip, detail="locked")
        return None, AuthError.ACCOUNT_LOCKED

    if not verify_password(password, user.password_hash):
        register_failed_attempt(db, user, now, source_ip)
        audit.record_event(db, audit.LOGIN_FAILURE, target_user_id=user.id, source_ip=source_ip, detail="bad_password")
        return None, AuthError.INVALID_CREDENTIALS

    # Re-hachage transparent : la connexion réussie est le seul moment où le
    # mot de passe en clair est disponible. Si les paramètres Argon2id ont été
    # renforcés depuis le dernier hachage (ou si le hachage n'est pas Argon2id),
    # on le recalcule avec la configuration courante.
    rehashed = False
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        rehashed = True

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.commit()
    if rehashed:
        audit.record_event(db, audit.PASSWORD_REHASHED, actor_user_id=user.id, target_user_id=user.id, source_ip=source_ip)
    audit.record_event(db, audit.LOGIN_SUCCESS, actor_user_id=user.id, target_user_id=user.id, source_ip=source_ip)
    return user, None
