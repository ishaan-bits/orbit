import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings
from app.services.errors import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

logger = logging.getLogger("orbit.services.storage")

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_FILE_SIZE_MB = MAX_FILE_SIZE_BYTES // (1024 * 1024)
CHUNK_SIZE = 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/md",
    "application/octet-stream",
    "",
}


def get_uploads_dir() -> Path:
    """Resolve (and create) the uploads directory.

    Defaults to `uploads/` next to the `app` package; override with the
    `UPLOADS_DIR` setting (e.g. a mounted disk in production).
    """
    configured = settings.uploads_dir.strip()
    if configured:
        uploads_dir = Path(configured).expanduser()
    else:
        uploads_dir = Path(__file__).resolve().parents[2] / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def sanitize_filename(filename: Optional[str]) -> str:
    """Strip any client-side path components and cap the length."""
    if not filename:
        return "upload"
    name = filename.replace("\\", "/").split("/")[-1].strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return name[:255] or "upload"


def validate_file_type(filename: str, content_type: Optional[str]) -> str:
    """Validate extension and declared MIME type; return the normalised extension."""
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(filename)

    mime = (content_type or "").lower().split(";")[0].strip()
    if mime not in ALLOWED_MIME_TYPES:
        raise UnsupportedFileTypeError(filename)

    return extension


async def save_upload(
    file: UploadFile, original_filename: str, uploads_dir: Path
) -> tuple[str, int]:
    """Stream the upload to disk under a generated UUID name.

    Enforces the size limit while streaming so oversized payloads never
    accumulate in memory. Returns `(stored_filename, size_bytes)`.
    """
    extension = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid.uuid4()}{extension}"
    destination = uploads_dir / stored_filename

    size = 0
    try:
        with destination.open("wb") as handle:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_FILE_SIZE_BYTES:
                    raise FileTooLargeError(MAX_FILE_SIZE_BYTES)
                handle.write(chunk)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise

    if size == 0:
        destination.unlink(missing_ok=True)
        raise EmptyFileError()

    return stored_filename, size


def delete_stored_file(stored_filename: Optional[str], uploads_dir: Path) -> bool:
    """Remove a physical file from the uploads directory. Never raises."""
    if not stored_filename:
        return False
    try:
        (uploads_dir / stored_filename).unlink(missing_ok=True)
        return True
    except OSError:
        logger.warning(
            "storage.file_remove_failed",
            extra={"stored_filename": stored_filename},
            exc_info=True,
        )
        return False


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
