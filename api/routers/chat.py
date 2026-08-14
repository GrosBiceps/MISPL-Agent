"""Route de chat — encapsule ask_mispl() derrière l'authentification de compte."""

from __future__ import annotations

import logging
import uuid

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

    history_text = "\n".join(m.content for m in (payload.conversation_history or []))
    blocked, dlp_alerts = dlp_check(f"{question_enriched}\n{history_text}" if history_text else question_enriched)
    if blocked:
        logger.warning(f"[DLP] Message bloqué — patterns: {dlp_alerts}")
        return ChatResponse(response=None, sources=[], blocked=True, dlp_alerts=dlp_alerts)

    access_mode = access_mode_for_user(user.can_use_dsi_mode)

    history = (
        [{"role": m.role, "content": m.content} for m in payload.conversation_history]
        if payload.conversation_history
        else None
    )

    try:
        response_text, docs = ask_mispl(
            question_enriched,
            access_mode=access_mode,
            save_session=True,
            conversation_history=history,
        )
    except Exception:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[{error_id}] Erreur ask_mispl", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service temporairement indisponible — réessayez dans quelques instants. (Référence : {error_id})",
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

    return ChatResponse(response=response_text, sources=sources, blocked=False, dlp_alerts=dlp_alerts)
