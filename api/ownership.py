"""Vérifications de propriété partagées entre routers — évite la duplication
d'une même règle d'autorisation dans plusieurs fichiers (risque de dérive si
l'un est modifié sans l'autre)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DBSession

from api.models import Conversation


def get_owned_conversation_or_404(db: DBSession, conversation_id: int, user_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return conversation
