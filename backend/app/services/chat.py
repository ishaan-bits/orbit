"""Chat conversation persistence for the AI Workspace."""

import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatConversation, ChatMessage
from app.services.errors import ConversationNotFoundError
from app.services.storage import utcnow


def get_conversation(db: Session, conversation_id: str) -> ChatConversation:
    conversation = db.get(ChatConversation, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    return conversation


def create_conversation(
    db: Session, title: str, user_id: Optional[str] = None
) -> ChatConversation:
    conversation = ChatConversation(title=title[:200], user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def append_message(
    db: Session,
    conversation: ChatConversation,
    role: str,
    content: str,
    sources: Optional[list[dict]] = None,
) -> ChatMessage:
    message = ChatMessage(
        conversation_id=conversation.id,
        role=role,
        content=content,
        sources=json.dumps(sources) if sources is not None else None,
    )
    conversation.updated_at = utcnow()
    db.add(conversation)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_conversations(
    db: Session, user_id: str, limit: int = 100
) -> list[ChatConversation]:
    statement = (
        select(ChatConversation)
        .where(ChatConversation.user_id == user_id)
        .order_by(
            ChatConversation.updated_at.desc(), ChatConversation.created_at.desc()
        )
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def parse_sources(raw: Optional[str]) -> Optional[list[dict]]:
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, list) else None
