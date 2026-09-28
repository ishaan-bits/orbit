import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.memory import rss_mb
from app.db.session import get_db
from app.rag import embedder
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger("orbit.api.health")


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)) -> HealthResponse:
    checks = {"database": "up"}
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "down"
        logger.exception("health.database_unreachable")

    status = "ok" if all(v == "up" for v in checks.values()) else "degraded"

    return HealthResponse(
        status=status,
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks,
        rss_mb=rss_mb(),
        embedding_provider=settings.embedding_provider,
        embedding_fallback=settings.embedding_fallback,
        gemini_key_configured=bool(settings.gemini_api_key),
        local_model_loaded=embedder.local_model_loaded(),
    )
