"""Routes d'authentification : login, logout, utilisateur courant, changement
de mot de passe."""

from __future__ import annotations

import datetime
import os
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DBSession

from api import audit
from api.auth import AuthError, authenticate_user, register_failed_attempt
from api.db import get_db
from api.dependencies import SESSION_COOKIE_NAME, get_authenticated_user
from api.models import User
from api.schemas import ChangePasswordRequest, LoginRequest, MeResponse
from api.security import hash_password, password_policy_errors, verify_password
from api.session_store import (
    SESSION_TTL_HOURS,
    create_session,
    revoke_all_sessions_for_user,
    revoke_session,
)

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

    user, error = authenticate_user(db, payload.email, payload.password, source_ip=client_ip)
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
    user: User = Depends(get_authenticated_user),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        revoke_session(db, token)
    audit.record_event(
        db, audit.LOGOUT, actor_user_id=user.id, target_user_id=user.id,
        source_ip=request.client.host if request.client else None,
    )
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"detail": "déconnecté"}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_authenticated_user)):
    # get_authenticated_user (et non get_current_user) : le frontend doit
    # pouvoir lire must_change_password pour rediriger vers le changement.
    return user


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    """Remplace le mot de passe de l'utilisateur connecté.

    Exige le mot de passe actuel (y compris temporaire) : un cookie de session
    volé ne suffit pas à s'approprier le compte. Un mauvais mot de passe
    actuel compte comme un échec de connexion (verrouillage). Toutes les
    AUTRES sessions du compte sont révoquées ; la session courante reste
    valide. Aucune réponse ni aucun journal ne contient de mot de passe."""
    client_ip = request.client.host if request.client else None
    now = datetime.datetime.utcnow()
    if user.locked_until is not None and user.locked_until > now:
        # Compte verrouillé par des échecs répétés : aucune vérification, pour
        # qu'un cookie volé ne permette pas de poursuivre la recherche du
        # mot de passe actuel.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_current_password")
    if not verify_password(payload.current_password, user.password_hash):
        register_failed_attempt(db, user, now, client_ip)
        audit.record_event(
            db, audit.PASSWORD_CHANGE_FAILED, actor_user_id=user.id, target_user_id=user.id,
            source_ip=client_ip, detail="bad_current_password",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_current_password")

    errors = password_policy_errors(payload.new_password, email=user.email, display_name=user.display_name)
    if payload.new_password == payload.current_password:
        errors.append("Le nouveau mot de passe doit être différent de l'actuel.")
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=" ".join(errors))

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()

    current_token = request.cookies.get(SESSION_COOKIE_NAME)
    revoke_all_sessions_for_user(db, user.id, except_token=current_token)
    audit.record_event(
        db, audit.PASSWORD_CHANGED, actor_user_id=user.id, target_user_id=user.id, source_ip=client_ip,
    )
    return {"detail": "Mot de passe modifié"}
