from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_SQLITE_PREFIX = "sqlite:///"


def _ensure_sqlite_directory(url: str) -> None:
    if not url.startswith(_SQLITE_PREFIX):
        return
    raw_path = url[len(_SQLITE_PREFIX) :]
    if raw_path in {"", ":memory:"} or "://" in raw_path:
        return
    database_path = Path(raw_path)
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)


def _build_engine():
    _ensure_sqlite_directory(settings.database_url)
    connect_args = (
        {"check_same_thread": False}
        if settings.database_url.startswith(_SQLITE_PREFIX)
        else {}
    )
    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
