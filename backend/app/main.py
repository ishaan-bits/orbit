import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

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
from app.services.storage import get_uploads_dir

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


def _ensure_storage_dirs() -> None:
    """Create storage directories (persistent disk) before the app starts.

    Covers `/var/data`, `/var/data/uploads` and `/var/data/chroma` on Render;
    locally it is a no-op on the already-present relative paths. Failures are
    logged but never block startup.
    """
    candidates: set[Path] = set()
    if settings.environment == "production":
        candidates.add(Path("/var/data"))
    chroma_path = Path(settings.chroma_path)
    if not chroma_path.is_absolute():
        chroma_path = Path(__file__).resolve().parents[1] / chroma_path
    candidates.add(chroma_path)
    raw_url = settings.database_url
    if raw_url.startswith("sqlite:///"):
        raw_path = raw_url[len("sqlite:///") :]
        if raw_path not in {"", ":memory:"} and "://" not in raw_path:
            database_path = Path(raw_path)
            if not database_path.is_absolute():
                database_path = Path.cwd() / database_path
            candidates.add(database_path.parent)
    for path in sorted(candidates):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.warning("storage.mkdir_failed", extra={"path": str(path)})
    try:
        get_uploads_dir()
    except OSError:
        logger.warning("storage.uploads_mkdir_failed")


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
    _ensure_storage_dirs()
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
