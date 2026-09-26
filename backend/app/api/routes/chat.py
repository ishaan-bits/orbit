"""AI Workspace chat endpoints: hybrid retrieval -> rerank -> Gemini."""

import json
import logging
import time
from collections.abc import Iterator
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.rag import generator, reranker, retriever
from app.schemas.chat import (
    ChatConversationResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    ChatSource,
)
from app.services import analytics as analytics_service
from app.services import auth as auth_service
from app.services import chat as chat_service
from app.services.errors import ConversationNotFoundError

router = APIRouter(tags=["chat"])
logger = logging.getLogger("orbit.api.chat")

RETRIEVAL_TOP_K = 10
RERANK_TOP_K = 3

NO_DOCUMENTS_ANSWER = (
    "There are no indexed documents in the knowledge base yet, so I cannot "
    "answer from it. Upload and index documents in the Knowledge Base first."
)


@router.post("/chat/query", response_model=None)
def chat_query(
    payload: ChatQueryRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Union[ChatQueryResponse, StreamingResponse]:
    """Answer a question from indexed documents the caller can access.

    Returns JSON by default; sends Server-Sent Events when the client
    requests ``Accept: text/event-stream``.
    """
    started_at = time.perf_counter()
    query = payload.query
    conversation = _resolve_conversation(db, user, payload.conversation_id, query)
    chat_service.append_message(db, conversation, "user", query)

    candidates = retriever.retrieve(query, top_k=RETRIEVAL_TOP_K)
    candidates = _filter_by_access(db, user, candidates)
    best = reranker.rerank(query, candidates, top_k=RERANK_TOP_K)
    passages = [
        generator.Passage(
            label=index + 1,
            filename=candidate.filename,
            page=candidate.page,
            text=candidate.text,
        )
        for index, candidate in enumerate(best)
    ]
    sources = _collect_sources(best)

    if _wants_stream(request):
        factory = sessionmaker(
            bind=db.get_bind(), autoflush=False, expire_on_commit=False
        )
        document_names = [source.document for source in sources]
        if not passages:
            # the fixed fallback answer cannot fail: log success immediately
            analytics_service.record_query(
                db,
                user_id=user.id,
                query=query,
                latency_ms=_elapsed_ms(started_at),
                success=True,
                document_names=document_names,
            )
            return StreamingResponse(
                _fixed_stream(factory, conversation.id, NO_DOCUMENTS_ANSWER, sources),
                media_type="text/event-stream",
            )
        return StreamingResponse(
            _sse_stream(
                factory,
                conversation.id,
                query,
                passages,
                sources,
                user_id=user.id,
                started_at=started_at,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    document_names = [source.document for source in sources]
    if not passages:
        answer = NO_DOCUMENTS_ANSWER
    else:
        try:
            answer = generator.generate_answer(query, passages)
        except generator.GenerationError as error:
            analytics_service.record_query(
                db,
                user_id=user.id,
                query=query,
                latency_ms=_elapsed_ms(started_at),
                success=False,
                document_names=document_names,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)
            ) from error

    analytics_service.record_query(
        db,
        user_id=user.id,
        query=query,
        latency_ms=_elapsed_ms(started_at),
        success=True,
        document_names=document_names,
    )
    chat_service.append_message(
        db, conversation, "assistant", answer, _source_dicts(sources)
    )
    return ChatQueryResponse(
        answer=answer,
        sources=sources,
        conversation_id=conversation.id,
    )


@router.get("/chat/history", response_model=ChatHistoryResponse)
def chat_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatHistoryResponse:
    """Return the caller's conversations with messages, most recent first."""
    conversations = chat_service.list_conversations(db, user_id=user.id)
    items = [
        ChatConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[_message_response(message) for message in conversation.messages],
        )
        for conversation in conversations
    ]
    return ChatHistoryResponse(conversations=items)


def _resolve_conversation(
    db: Session, user: User, conversation_id: Optional[str], query: str
):
    if conversation_id:
        try:
            conversation = chat_service.get_conversation(db, conversation_id)
        except ConversationNotFoundError:
            conversation = None
        if conversation is None or conversation.user_id != user.id:
            # hide conversations that belong to other users
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' was not found",
            )
        return conversation
    return chat_service.create_conversation(db, title=query, user_id=user.id)


def _filter_by_access(db: Session, user: User, candidates: list) -> list:
    """Drop retrieved chunks whose document the caller may not read.

    Access filtering is applied on top of retrieval; the RAG algorithm
    itself is unchanged.
    """
    allowed = auth_service.get_accessible_document_ids(db, user)
    if allowed is None:
        return candidates
    return [candidate for candidate in candidates if candidate.document_id in allowed]


def _message_response(message) -> ChatMessageResponse:
    raw_sources = (
        chat_service.parse_sources(message.sources)
        if message.role == "assistant"
        else None
    )
    sources = (
        [ChatSource(**item) for item in raw_sources]
        if raw_sources is not None
        else None
    )
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        sources=sources,
        created_at=message.created_at,
    )


def _collect_sources(candidates: list) -> list[ChatSource]:
    """Deduplicate citations by (document, page), preserving rank order."""
    sources: list[ChatSource] = []
    seen: set[tuple[str, int]] = set()
    for candidate in candidates:
        key = (candidate.filename, candidate.page)
        if key in seen:
            continue
        seen.add(key)
        sources.append(ChatSource(document=candidate.filename, page=candidate.page))
    return sources


def _source_dicts(sources: list[ChatSource]) -> list[dict]:
    return [source.model_dump() for source in sources]


def _wants_stream(request: Request) -> bool:
    return "text/event-stream" in request.headers.get("accept", "")


def _elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _record_stream_event(
    factory,
    user_id: Optional[str],
    query: str,
    started_at: Optional[float],
    success: bool,
    sources: list[ChatSource],
) -> None:
    """Record a streaming query outcome on a dedicated session."""
    latency = _elapsed_ms(started_at) if started_at is not None else 0
    db = factory()
    try:
        analytics_service.record_query(
            db,
            user_id=user_id,
            query=query,
            latency_ms=latency,
            success=success,
            document_names=[source.document for source in sources],
        )
    finally:
        db.close()


def _sse_event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data)}\n\n"


def _persist_assistant(
    factory, conversation_id: str, content: str, sources: list[ChatSource]
) -> None:
    db = factory()
    try:
        conversation = chat_service.get_conversation(db, conversation_id)
        chat_service.append_message(
            db, conversation, "assistant", content, _source_dicts(sources)
        )
    except Exception:  # noqa: BLE001 - never break the stream on persistence
        logger.exception(
            "chat.assistant_persist_failed", extra={"conversation_id": conversation_id}
        )
        db.rollback()
    finally:
        db.close()


def _fixed_stream(
    factory, conversation_id: str, answer: str, sources: list[ChatSource]
) -> Iterator[str]:
    """Stream the no-documents answer without calling Gemini."""
    payload = {"sources": _source_dicts(sources), "conversation_id": conversation_id}
    yield _sse_event("sources", payload)
    yield _sse_event("token", {"text": answer})
    _persist_assistant(factory, conversation_id, answer, sources)
    yield _sse_event(
        "done",
        {
            "answer": answer,
            "sources": payload["sources"],
            "conversation_id": conversation_id,
        },
    )


def _sse_stream(
    factory,
    conversation_id: str,
    query: str,
    passages,
    sources: list[ChatSource],
    user_id: Optional[str] = None,
    started_at: Optional[float] = None,
) -> Iterator[str]:
    payload = {"sources": _source_dicts(sources), "conversation_id": conversation_id}
    yield _sse_event("sources", payload)

    parts: list[str] = []
    try:
        for token in generator.stream_answer(query, passages):
            parts.append(token)
            yield _sse_event("token", {"text": token})
    except generator.GenerationError as error:
        _record_stream_event(
            factory, user_id, query, started_at, success=False, sources=sources
        )
        if parts:
            _persist_assistant(factory, conversation_id, "".join(parts), sources)
        yield _sse_event("error", {"error": str(error)})
        return
    except Exception:  # noqa: BLE001 - surface unexpected failures to the client
        logger.exception(
            "chat.stream_failed", extra={"conversation_id": conversation_id}
        )
        _record_stream_event(
            factory, user_id, query, started_at, success=False, sources=sources
        )
        if parts:
            _persist_assistant(factory, conversation_id, "".join(parts), sources)
        yield _sse_event("error", {"error": "Answer generation failed"})
        return

    answer = "".join(parts)
    _record_stream_event(
        factory, user_id, query, started_at, success=True, sources=sources
    )
    _persist_assistant(factory, conversation_id, answer, sources)
    yield _sse_event(
        "done",
        {
            "answer": answer,
            "sources": payload["sources"],
            "conversation_id": conversation_id,
        },
    )
