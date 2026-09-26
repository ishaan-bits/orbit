"""Recording and aggregation for the Enterprise Analytics dashboard."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsEvent
from app.schemas.analytics import (
    DailyPoint,
    DailyResponse,
    OverviewResponse,
    RecentSearchesResponse,
    RecentSearchItem,
    TopDocumentItem,
    TopDocumentsResponse,
    TopQueriesResponse,
    TopQueryItem,
)

logger = logging.getLogger("orbit.services.analytics")

DEFAULT_TOP_LIMIT = 10
DEFAULT_DAILY_DAYS = 14


def record_query(
    db: Session,
    *,
    user_id: Optional[str],
    query: str,
    latency_ms: int,
    success: bool,
    document_names: list[str],
) -> None:
    """Persist one query event. Never raises: analytics must not break chat."""
    try:
        event = AnalyticsEvent(
            user_id=user_id,
            query=query,
            latency_ms=max(0, int(round(latency_ms))),
            success=success,
            retrieved_documents=len(document_names),
            retrieved_document_names=document_names,
        )
        db.add(event)
        db.commit()
    except Exception:  # noqa: BLE001 - analytics failures must stay invisible
        logger.exception("analytics.record_failed")
        db.rollback()


def get_overview(db: Session) -> OverviewResponse:
    row = db.execute(
        select(
            func.count(AnalyticsEvent.id),
            func.coalesce(
                func.sum(case((AnalyticsEvent.success.is_(True), 1), else_=0)), 0
            ),
            func.coalesce(func.avg(AnalyticsEvent.latency_ms), 0),
            func.coalesce(func.sum(AnalyticsEvent.retrieved_documents), 0),
            func.count(func.distinct(AnalyticsEvent.user_id)),
        )
    ).one()
    total, successful, avg_latency, retrieved_total, unique_users = row
    total = int(total)
    successful = int(successful)
    return OverviewResponse(
        total_queries=total,
        successful_queries=successful,
        failed_queries=total - successful,
        success_rate=round(100.0 * successful / total, 1) if total else 0.0,
        avg_latency_ms=int(round(float(avg_latency))),
        retrieved_documents_total=int(retrieved_total),
        unique_users=int(unique_users),
    )


def get_daily(db: Session, days: int = DEFAULT_DAILY_DAYS) -> DailyResponse:
    """One bucket per UTC day, oldest first, zero-filled for quiet days."""
    rows = db.execute(
        select(
            func.date(AnalyticsEvent.created_at).label("day"),
            func.count(AnalyticsEvent.id),
            func.coalesce(
                func.sum(case((AnalyticsEvent.success.is_(True), 1), else_=0)), 0
            ),
            func.coalesce(func.avg(AnalyticsEvent.latency_ms), 0),
        ).group_by("day")
    ).all()
    by_day = {
        str(day): {
            "queries": int(count),
            "successful": int(successful),
            "avg_latency_ms": int(round(float(avg_latency))),
        }
        for day, count, successful, avg_latency in rows
    }

    today = datetime.now(timezone.utc).date()
    points: list[DailyPoint] = []
    for offset in range(days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        stats = by_day.get(day, {"queries": 0, "successful": 0, "avg_latency_ms": 0})
        points.append(
            DailyPoint(
                date=day,
                queries=stats["queries"],
                successful=stats["successful"],
                failed=stats["queries"] - stats["successful"],
                avg_latency_ms=stats["avg_latency_ms"],
            )
        )
    return DailyResponse(days=points)


def get_top_documents(
    db: Session, limit: int = DEFAULT_TOP_LIMIT
) -> TopDocumentsResponse:
    names = db.execute(
        select(AnalyticsEvent.retrieved_document_names).order_by(
            AnalyticsEvent.created_at.desc()
        )
    ).all()
    counts: dict[str, int] = {}
    for (event_names,) in names:
        for name in set(event_names or []):  # count each document once per query
            counts[name] = counts.get(name, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return TopDocumentsResponse(
        documents=[
            TopDocumentItem(document=document, count=count)
            for document, count in ordered
        ]
    )


def get_top_queries(db: Session, limit: int = DEFAULT_TOP_LIMIT) -> TopQueriesResponse:
    rows = db.execute(
        select(AnalyticsEvent.query, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.query)
        .order_by(func.count(AnalyticsEvent.id).desc(), AnalyticsEvent.query)
        .limit(limit)
    ).all()
    return TopQueriesResponse(
        queries=[TopQueryItem(query=query, count=int(count)) for query, count in rows]
    )


def get_recent(db: Session, limit: int = DEFAULT_TOP_LIMIT) -> RecentSearchesResponse:
    rows = db.execute(
        select(AnalyticsEvent)
        .order_by(AnalyticsEvent.created_at.desc(), AnalyticsEvent.id.desc())
        .limit(limit)
    ).scalars()
    return RecentSearchesResponse(
        searches=[
            RecentSearchItem(
                id=event.id,
                query=event.query,
                success=event.success,
                latency_ms=event.latency_ms,
                retrieved_documents=event.retrieved_documents,
                created_at=event.created_at,
            )
            for event in rows
        ]
    )
