from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; they are always stored in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000, description="User question")
    conversation_id: Optional[str] = Field(
        default=None, description="Continue an existing conversation"
    )

    @field_validator("query")
    @classmethod
    def _strip_and_reject_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Query cannot be blank")
        return cleaned


class ChatSource(BaseModel):
    document: str = Field(description="Source document filename")
    page: int = Field(description="Source page number")


class ChatQueryResponse(BaseModel):
    answer: str = Field(description="Markdown answer")
    sources: list[ChatSource] = Field(description="Cited sources")
    conversation_id: str = Field(description="Conversation this exchange belongs to")


class ChatMessageResponse(BaseModel):
    id: str = Field(description="Message identifier")
    role: str = Field(description="'user' or 'assistant'")
    content: str = Field(description="Message text (Markdown for answers)")
    sources: Optional[list[ChatSource]] = Field(
        default=None, description="Citations, for assistant messages"
    )
    created_at: datetime = Field(description="Creation timestamp (UTC)")

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> datetime:
        return _as_utc(value)


class ChatConversationResponse(BaseModel):
    id: str = Field(description="Conversation identifier")
    title: str = Field(description="Conversation title")
    created_at: datetime = Field(description="Creation timestamp (UTC)")
    updated_at: datetime = Field(description="Last activity timestamp (UTC)")
    messages: list[ChatMessageResponse] = Field(description="Messages in order")

    @field_serializer("created_at", "updated_at")
    def _serialize_datetime(self, value: datetime) -> datetime:
        return _as_utc(value)


class ChatHistoryResponse(BaseModel):
    conversations: list[ChatConversationResponse] = Field(
        description="Conversations, most recently active first"
    )
