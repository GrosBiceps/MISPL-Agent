"""Schémas Pydantic — requêtes et réponses de l'API."""

from __future__ import annotations

from typing import Literal

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


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    lab_context: str | None = None
    conversation_history: list[ChatHistoryMessage] | None = None


class SourceOut(BaseModel):
    function_name: str
    source: str
    score: float
    exact_match: bool


class ChatResponse(BaseModel):
    response: str | None
    sources: list[SourceOut]
    blocked: bool
    dlp_alerts: list[str]
