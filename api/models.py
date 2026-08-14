"""Modèles ORM : comptes utilisateurs et sessions de connexion."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("platform_role IN ('admin', 'user')", name="ck_users_platform_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    platform_role: Mapped[str] = mapped_column(String, nullable=False)
    can_use_dsi_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
