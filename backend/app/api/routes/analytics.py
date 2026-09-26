"""Admin-only analytics endpoints for the Enterprise Dashboard."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.schemas.analytics import (
    DailyResponse,
    OverviewResponse,
    RecentSearchesResponse,
    TopDocumentsResponse,
    TopQueriesResponse,
)
from app.services import analytics as analytics_service
from app.services import auth as auth_service

router = APIRouter(tags=["analytics"])


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Require an authenticated Admin (analytics are administrator-only)."""
    if not auth_service.is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can view analytics",
        )
    return user


@router.get("/analytics/overview", response_model=OverviewResponse)
def analytics_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> OverviewResponse:
    """Aggregate KPIs across every recorded AI query."""
    return analytics_service.get_overview(db)


@router.get("/analytics/daily", response_model=DailyResponse)
def analytics_daily(
    days: int = Query(
        default=analytics_service.DEFAULT_DAILY_DAYS,
        ge=7,
        le=90,
        description="Number of UTC days to return, oldest first",
    ),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> DailyResponse:
    """One bucket per day for the daily searches line chart."""
    return analytics_service.get_daily(db, days=days)


@router.get("/analytics/top-documents", response_model=TopDocumentsResponse)
def analytics_top_documents(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> TopDocumentsResponse:
    """Documents most often cited as answer sources."""
    return analytics_service.get_top_documents(db)


@router.get("/analytics/top-queries", response_model=TopQueriesResponse)
def analytics_top_queries(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> TopQueriesResponse:
    """Most frequently asked queries."""
    return analytics_service.get_top_queries(db)


@router.get("/analytics/recent", response_model=RecentSearchesResponse)
def analytics_recent(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> RecentSearchesResponse:
    """Newest queries first, for the recent searches table."""
    return analytics_service.get_recent(db)
