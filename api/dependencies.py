"""Dépendances FastAPI — utilisateur courant, garde admin."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.models import User
from api.session_store import validate_session

SESSION_COOKIE_NAME = "session_token"


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié")
    user = validate_session(db, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.platform_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs")
    return user
