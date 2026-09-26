import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.api.routes import (
    analytics,
    auth,
    chat,
    documents,
    folders,
    health,
    permissions,
)
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.models.auth import User
from app.services.auth import ensure_rbac_seed
from app.services.demo_seed import ensure_demo_seed, should_seed_demo

setup_logging(level="DEBUG" if settings.debug else "INFO")
logger = logging.getLogger("orbit")


def _seed_rbac() -> None:
    """Seed default roles on startup (idempotent; migrations also seed)."""
    db = SessionLocal()
    try:
        ensure_rbac_seed(db)
    except Exception:  # noqa: BLE001 - never block startup on seeding
        logger.exception("rbac.seed_failed")
    finally:
        db.close()


def _seed_demo() -> None:
    """Seed the NovaTech demo tenant when enabled (idempotent)."""
    db = SessionLocal()
    try:
        ensure_demo_seed(db)
    except Exception:  # noqa: BLE001 - never block startup on seeding
        logger.exception("demo_seed.failed")
    finally:
        db.close()


def _demo_seed_enabled() -> bool:
    """Honor SEED_DEMO tri-state; when unset, seed only into an empty database."""
    if settings.seed_demo is not None:
        return settings.seed_demo
    db = SessionLocal()
    try:
        user_count = db.scalar(select(func.count()).select_from(User)) or 0
    except Exception:  # noqa: BLE001 - missing table means migrations not run
        logger.exception("demo_seed.check_failed")
        return False
    finally:
        db.close()
    return should_seed_demo(None, user_count)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "service.starting",
        extra={
            "service": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
        },
    )
    _seed_rbac()
    if _demo_seed_enabled():
        _seed_demo()
    yield
    logger.info("service.stopping", extra={"service": settings.app_name})


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Orbit platform API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(folders.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(permissions.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
