"""Route de chat — encapsule ask_mispl() derrière l'authentification de compte."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.models import User
from api.schemas import ChatRequest, ChatResponse, SourceOut
from src.agent.mispl_agent import ask_mispl
from src.security.access_mode import access_mode_for_user
from src.security.dlp import dlp_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
def ask(payload: ChatRequest, user: User = Depends(get_current_user)):
    question_enriched = payload.question
    if payload.lab_context:
        question_enriched = f"[Contexte labo: {payload.lab_context.strip()}]\n\n{payload.question}"

    blocked, dlp_alerts = dlp_check(question_enriched)
    if blocked:
        return ChatResponse(response=None, sources=[], blocked=True, dlp_alerts=dlp_alerts)

    access_mode = access_mode_for_user(user.can_use_dsi_mode)

    try:
        response_text, docs = ask_mispl(
            question_enriched,
            access_mode=access_mode,
            save_session=True,
        )
    except Exception:
        logger.exception("Erreur lors de l'appel ask_mispl")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporairement indisponible — réessayez dans quelques instants.",
        )

    sources = [
        SourceOut(
            function_name=d.get("function_name", ""),
            source=d.get("source", ""),
            score=round(d.get("score", 0), 3),
            exact_match=d.get("exact_match", False),
        )
        for d in docs
    ]

    return ChatResponse(response=response_text, sources=sources, blocked=False, dlp_alerts=[])
