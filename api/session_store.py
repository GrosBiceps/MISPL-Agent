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
    now = datetime.datetime.utcnow()
    new_expiry = now + datetime.timedelta(hours=SESSION_TTL_HOURS)
    # UPDATE atomique conditionné sur l'état courant (non révoquée, non expirée) :
    # élimine le check-then-act entre la lecture de la ligne et l'écriture du
    # renouvellement glissant, cohérent avec le pattern d'upsert atomique déjà
    # utilisé pour UsageDaily (cf. api/routers/chat.py::_record_usage).
    updated = (
        db.query(UserSession)
        .filter(
            UserSession.token == token,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at >= now,
        )
        .update({"expires_at": new_expiry}, synchronize_session=False)
    )
    if updated == 0:
        db.rollback()
        return None
    row = db.get(UserSession, token)
    user = db.get(User, row.user_id) if row is not None else None
    if user is None or not user.is_active:
        db.rollback()
        return None
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
