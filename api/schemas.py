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
