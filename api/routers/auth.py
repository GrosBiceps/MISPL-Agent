"""Routes d'authentification : login, logout, utilisateur courant."""

from __future__ import annotations

import os
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DBSession

from api.auth import AuthError, authenticate_user
from api.db import get_db
from api.dependencies import SESSION_COOKIE_NAME, get_current_user
from api.models import User
from api.schemas import LoginRequest, MeResponse
from api.session_store import SESSION_TTL_HOURS, create_session, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])

# True en production (HTTPS obligatoire). Configurable via variable d'env pour
# les déploiements internes derrière un reverse proxy non-TLS ; désactivé par
# défaut aussi dans les tests via TestClient (cf. tests/api/conftest.py, qui
# tourne sur http://testserver où le flag Secure n'a de toute façon aucun effet
# observable côté test).
COOKIE_SECURE = os.environ.get("MISPL_COOKIE_SECURE", "true").strip().lower() not in ("false", "0", "no")

# Limite de tentatives de connexion par IP, distincte du verrouillage par compte
# (LOCK_THRESHOLD dans api/auth.py). Le verrouillage par compte protège un
# compte connu contre le bruteforce ciblé ; cette limite protège le serveur
# contre le credential-stuffing distribué sur de nombreux comptes différents
# depuis une même source, qui resterait sous le seuil par-compte.
_LOGIN_RATE_LIMIT = 10
_LOGIN_RATE_WINDOW_SECONDS = 300
_login_attempts: dict[str, list[float]] = {}
_login_attempts_lock = threading.Lock()


def _check_login_rate_limit(rate_limit_key: str) -> None:
    now = time.monotonic()
    with _login_attempts_lock:
        attempts = [t for t in _login_attempts.get(rate_limit_key, []) if now - t < _LOGIN_RATE_WINDOW_SECONDS]
        if len(attempts) >= _LOGIN_RATE_LIMIT:
            _login_attempts[rate_limit_key] = attempts
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too_many_login_attempts",
            )
        attempts.append(now)
        _login_attempts[rate_limit_key] = attempts


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DBSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    # Clé (IP, email) plutôt qu'IP seule : derrière un reverse proxy/NAT interne,
    # plusieurs comptes/utilisateurs légitimes peuvent partager la même IP visible
    # — une clé IP seule ferait qu'un utilisateur en échec verrouille tous les
    # autres. La limite reste pleinement efficace contre le credential-stuffing
    # ciblant UN compte donné depuis une source donnée.
    rate_limit_key = f"{client_ip}:{payload.email.lower().strip()}"
    _check_login_rate_limit(rate_limit_key)

    user, error = authenticate_user(db, payload.email, payload.password)
    if error is not None:
        # Code et message volontairement identiques pour ACCOUNT_LOCKED et
        # INVALID_CREDENTIALS : les différencier (401 vs 423) permettrait à un
        # attaquant de confirmer qu'un email correspond à un compte actif en
        # observant le code passer de 401 à 423 après plusieurs échecs
        # (énumération de comptes). Le verrouillage reste appliqué en interne
        # par authenticate_user — seule la réponse HTTP est indistincte.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=AuthError.INVALID_CREDENTIALS.value)

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
