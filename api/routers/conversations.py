"""Routes de gestion des conversations persistées — historique de chat par compte."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import get_current_user
from api.models import Conversation, User
from api.ownership import get_owned_conversation_or_404
from api.schemas import ConversationDetailOut, ConversationSummaryOut, MessageOut, SourceOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummaryOut])
def list_conversations(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)
):
    conversation = get_owned_conversation_or_404(db, conversation_id, user.id)
    messages = [
        MessageOut(
            role=m.role,
            content=m.content,
            sources=[SourceOut(**s) for s in json.loads(m.sources_json)] if m.sources_json else None,
            created_at=m.created_at,
        )
        for m in conversation.messages
    ]
    return ConversationDetailOut(id=conversation.id, title=conversation.title, messages=messages)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)
):
    conversation = get_owned_conversation_or_404(db, conversation_id, user.id)
    db.delete(conversation)
    db.commit()
    return {"detail": "Conversation supprimée"}
