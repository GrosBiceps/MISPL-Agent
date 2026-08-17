"""Routes admin : création/gestion des comptes techniciens."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import require_admin
from api.models import UsageDaily, User
from api.schemas import (
    AdminUserOut,
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordResponse,
    RevokeSessionsResponse,
    UpdateUserRequest,
    UsageDayOut,
    UserOut,
)
from api.security import generate_temp_password, hash_password
from api.session_store import revoke_all_sessions_for_user

router = APIRouter(prefix="/admin", tags=["admin"])


def _count_active_admins(db: DBSession) -> int:
    return (
        db.query(User)
        .filter(User.platform_role == "admin", User.is_active.is_(True))
        .count()
    )


def _get_user_or_404(db: DBSession, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user


@router.post("/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if payload.platform_role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="platform_role doit être 'admin' ou 'user'")

    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    temp_password = generate_temp_password()
    user = User(
        email=email,
        password_hash=hash_password(temp_password),
        display_name=payload.display_name,
        platform_role=payload.platform_role,
        can_use_dsi_mode=payload.can_use_dsi_mode,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return CreateUserResponse(
        **UserOut.model_validate(user).model_dump(), temporary_password=temp_password
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)):
    users = db.query(User).order_by(User.id).all()

    cutoff = datetime.datetime.utcnow().date() - datetime.timedelta(days=30)
    rows = (
        db.query(
            UsageDaily.user_id,
            func.sum(UsageDaily.prompt_tokens + UsageDaily.completion_tokens).label("total_tokens"),
            func.max(UsageDaily.date).label("last_active"),
        )
        .filter(UsageDaily.date >= cutoff)
        .group_by(UsageDaily.user_id)
        .all()
    )
    usage_by_user = {r.user_id: (r.total_tokens or 0, r.last_active) for r in rows}

    result = []
    for u in users:
        total_tokens, last_active = usage_by_user.get(u.id, (0, None))
        result.append(
            AdminUserOut(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                platform_role=u.platform_role,
                can_use_dsi_mode=u.can_use_dsi_mode,
                is_active=u.is_active,
                total_tokens_30d=total_tokens,
                last_active_at=last_active,
            )
        )
    return result


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = _get_user_or_404(db, user_id)

    if payload.platform_role is not None and payload.platform_role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="platform_role doit être 'admin' ou 'user'")

    would_demote = (
        payload.platform_role is not None
        and payload.platform_role != "admin"
        and user.platform_role == "admin"
    )
    would_deactivate = payload.is_active is False and user.platform_role == "admin"
    if (would_demote or would_deactivate) and _count_active_admins(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de désactiver/rétrograder le dernier administrateur actif",
        )

    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.platform_role is not None:
        user.platform_role = payload.platform_role
    if payload.can_use_dsi_mode is not None:
        user.can_use_dsi_mode = payload.can_use_dsi_mode
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    user_id: int, db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    user = _get_user_or_404(db, user_id)
    temp_password = generate_temp_password()
    user.password_hash = hash_password(temp_password)
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    revoke_all_sessions_for_user(db, user_id)
    return ResetPasswordResponse(temporary_password=temp_password)


@router.post("/users/{user_id}/revoke-sessions", response_model=RevokeSessionsResponse)
def revoke_sessions(
    user_id: int, db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)
):
    _get_user_or_404(db, user_id)
    count = revoke_all_sessions_for_user(db, user_id)
    return RevokeSessionsResponse(revoked=count)


@router.get("/users/{user_id}/usage-daily", response_model=list[UsageDayOut])
def get_usage_daily(
    user_id: int,
    days: int = 30,
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    _get_user_or_404(db, user_id)

    today = datetime.datetime.utcnow().date()
    start = today - datetime.timedelta(days=days - 1)
    rows = (
        db.query(UsageDaily)
        .filter(UsageDaily.user_id == user_id, UsageDaily.date >= start)
        .all()
    )
    by_date = {r.date: r for r in rows}

    result = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        row = by_date.get(d)
        result.append(
            UsageDayOut(
                date=d,
                prompt_tokens=row.prompt_tokens if row else 0,
                completion_tokens=row.completion_tokens if row else 0,
                request_count=row.request_count if row else 0,
            )
        )
    return result
