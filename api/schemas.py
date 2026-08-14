"""Schémas Pydantic — requêtes et réponses de l'API."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: int
    email: str
    display_name: str
    platform_role: str
    can_use_dsi_mode: bool

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    platform_role: str
    can_use_dsi_mode: bool
    is_active: bool

    model_config = {"from_attributes": True}


class CreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str
    platform_role: str
    can_use_dsi_mode: bool = False


class CreateUserResponse(UserOut):
    temporary_password: str


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    platform_role: str | None = None
    can_use_dsi_mode: bool | None = None
    is_active: bool | None = None


class ResetPasswordResponse(BaseModel):
    temporary_password: str


class RevokeSessionsResponse(BaseModel):
    revoked: int
