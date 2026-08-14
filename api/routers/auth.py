"""Routes d'authentification : login, logout, utilisateur courant."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DBSession

from api.auth import AuthError, authenticate_user
from api.db import get_db
from api.dependencies import SESSION_COOKIE_NAME, get_current_user
from api.models import User
from api.schemas import LoginRequest, MeResponse
from api.session_store import SESSION_TTL_HOURS, create_session, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])

# True en production (HTTPS obligatoire) ; désactivé dans les tests (TestClient
# tourne sur http://testserver, cf. tests/api/conftest.py).
COOKIE_SECURE = True


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, response: Response, db: DBSession = Depends(get_db)):
    user, error = authenticate_user(db, payload.email, payload.password)
    if error is not None:
        code = status.HTTP_423_LOCKED if error == AuthError.ACCOUNT_LOCKED else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=code, detail=error.value)

    token = create_session(db, user)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        max_age=SESSION_TTL_HOURS * 3600,
    )
    return user


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        revoke_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"detail": "déconnecté"}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return user
