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

# Deux niveaux de limite de tentatives de connexion, distincts du verrouillage
# par compte (LOCK_THRESHOLD dans api/auth.py) :
#   1. par (IP, email) : protège un compte ciblé contre le bruteforce, sans
#      verrouiller les autres utilisateurs partageant la même IP visible
#      (reverse proxy/NAT interne) — une clé IP seule ferait qu'un utilisateur
#      en échec verrouille tous les autres.
#   2. par IP seule, seuil plus permissif : la limite (1) seule ne détecte
#      JAMAIS le credential-stuffing qui fait tourner de nombreux emails
#      différents depuis une même source, puisque chaque email obtient son
#      propre compartiment neuf — ce niveau plafonne le volume total de
#      tentatives par source, tous comptes confondus (cf. audit sécurité).
_LOGIN_RATE_LIMIT_PER_ACCOUNT = 10
_LOGIN_RATE_LIMIT_PER_IP = 30
_LOGIN_RATE_WINDOW_SECONDS = 300
_login_attempts: dict[str, list[float]] = {}
_login_attempts_by_ip: dict[str, list[float]] = {}
_login_attempts_lock = threading.Lock()


def _prune_and_record(store: dict[str, list[float]], key: str, limit: int, now: float) -> bool:
    """Purge les tentatives hors fenêtre, enregistre la tentative courante, et
    retourne True si la limite est dépassée pour cette clé.

    Purge également, à cette même occasion, toute AUTRE clé du dict dont
    toutes les tentatives sont désormais hors fenêtre : sans ça, une clé
    (IP, ou IP:email) qui atteint puis abandonne son quota reste indéfiniment
    en mémoire — plus personne ne la retouche jamais pour déclencher son
    propre nettoyage. Ce balayage reste peu coûteux (dicts de taille modeste,
    fenêtre de quelques minutes) et ne modifie pas la logique de comptage."""
    attempts = [t for t in store.get(key, []) if now - t < _LOGIN_RATE_WINDOW_SECONDS]
    if len(attempts) >= limit:
        store[key] = attempts
        result = True
    else:
        attempts.append(now)
        store[key] = attempts
        result = False

    for other_key in [
        k for k, timestamps in store.items()
        if k != key and all(now - t >= _LOGIN_RATE_WINDOW_SECONDS for t in timestamps)
    ]:
        del store[other_key]

    return result


def _check_login_rate_limit(client_ip: str, email: str) -> None:
    now = time.monotonic()
    with _login_attempts_lock:
        rate_limit_key = f"{client_ip}:{email}"
        over_account_limit = _prune_and_record(_login_attempts, rate_limit_key, _LOGIN_RATE_LIMIT_PER_ACCOUNT, now)
        over_ip_limit = _prune_and_record(_login_attempts_by_ip, client_ip, _LOGIN_RATE_LIMIT_PER_IP, now)
    if over_account_limit or over_ip_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too_many_login_attempts",
        )


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DBSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip, payload.email.lower().strip())

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
