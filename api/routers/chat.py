"""Route de chat — encapsule ask_mispl() derrière l'authentification de compte."""

from __future__ import annotations

import datetime
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import get_current_user
from api.models import Conversation, Message, UsageDaily, User
from api.schemas import ChatRequest, ChatResponse, SourceOut
from src.agent.mispl_agent import ask_mispl
from src.security.access_mode import access_mode_for_user
from src.security.dlp import dlp_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

TITLE_MAX_LENGTH = 50


def _get_owned_conversation_or_404(db: DBSession, conversation_id: int, user_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return conversation


def _make_title(question: str) -> str:
    stripped = question.strip()
    if len(stripped) <= TITLE_MAX_LENGTH:
        return stripped
    return stripped[:TITLE_MAX_LENGTH].rstrip() + "…"


def _record_usage(db: DBSession, user_id: int, usage: dict) -> None:
    today = datetime.datetime.utcnow().date()
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    stmt = sqlite_insert(UsageDaily).values(
        user_id=user_id,
        date=today,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        request_count=1,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "date"],
        set_={
            "prompt_tokens": UsageDaily.prompt_tokens + prompt_tokens,
            "completion_tokens": UsageDaily.completion_tokens + completion_tokens,
            "request_count": UsageDaily.request_count + 1,
        },
    )
    db.execute(stmt)


@router.post("/ask", response_model=ChatResponse)
def ask(payload: ChatRequest, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = None
    if payload.conversation_id is not None:
        conversation = _get_owned_conversation_or_404(db, payload.conversation_id, user.id)

    question_enriched = payload.question
    if payload.lab_context:
        question_enriched = f"[Contexte labo: {payload.lab_context.strip()}]\n\n{payload.question}"

    history_text = "\n".join(m.content for m in (payload.conversation_history or []))
    blocked, dlp_alerts = dlp_check(f"{question_enriched}\n{history_text}" if history_text else question_enriched)
    if blocked:
        logger.warning(f"[DLP] Message bloqué — patterns: {dlp_alerts}")
        return ChatResponse(response=None, sources=[], blocked=True, dlp_alerts=dlp_alerts, conversation_id=None)

    access_mode = access_mode_for_user(user.can_use_dsi_mode)

    history = (
        [{"role": m.role, "content": m.content} for m in payload.conversation_history]
        if payload.conversation_history
        else None
    )

    usage: dict = {}
    try:
        response_text, docs = ask_mispl(
            question_enriched,
            access_mode=access_mode,
            save_session=True,
            conversation_history=history,
            usage_out=usage,
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

    if conversation is None:
        conversation = Conversation(user_id=user.id, title=_make_title(payload.question))
        db.add(conversation)
        db.flush()

    now = datetime.datetime.utcnow()
    db.add(Message(conversation_id=conversation.id, role="user", content=payload.question, created_at=now))
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text or "",
            sources_json=json.dumps([s.model_dump() for s in sources]) if sources else None,
            created_at=now,
        )
    )
    conversation.updated_at = now
    _record_usage(db, user.id, usage)
    db.commit()

    return ChatResponse(
        response=response_text,
        sources=sources,
        blocked=False,
        dlp_alerts=dlp_alerts,
        conversation_id=conversation.id,
    )
