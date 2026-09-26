import logging
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.knowledge import Document, Folder
from app.rag import vectordb
from app.services.auth import can_access_folder, get_general_folder
from app.services.errors import (
    DocumentNotFoundError,
    FolderAccessDeniedError,
    FolderNotFoundError,
)
from app.services.storage import (
    delete_stored_file,
    sanitize_filename,
    save_upload,
    utcnow,
    validate_file_type,
)

logger = logging.getLogger("orbit.services.documents")


async def upload_document(
    db: Session,
    file: UploadFile,
    folder_id: Optional[str],
    uploads_dir: Path,
    user=None,
) -> Document:
    """Validate, persist and register an uploaded file. No parsing happens here."""
    original_filename = sanitize_filename(file.filename)
    validate_file_type(original_filename, file.content_type)

    folder: Optional[Folder] = None
    if folder_id:
        folder = db.get(Folder, folder_id)
        if folder is None:
            raise FolderNotFoundError(folder_id)
    else:
        # every document belongs to a folder: default to the shared General folder
        folder = get_general_folder(db)

    if user is not None and folder is not None and not can_access_folder(user, folder):
        raise FolderAccessDeniedError(folder.name)

    stored_filename, size = await save_upload(file, original_filename, uploads_dir)

    document = Document(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_extension=Path(original_filename).suffix.lower().lstrip("."),
        mime_type=(file.content_type or "application/octet-stream"),
        file_size=size,
        folder_id=folder.id if folder is not None else None,
    )

    try:
        db.add(document)
        db.commit()
    except BaseException:
        db.rollback()
        delete_stored_file(stored_filename, uploads_dir)
        raise

    db.refresh(document)
    logger.info(
        "documents.uploaded",
        extra={
            "document_id": document.id,
            "file_size": size,
            "folder_id": document.folder_id,
        },
    )
    return document


def _filtered_statement(
    folder_id: Optional[str] = None,
    query: Optional[str] = None,
    accessible_ids: Optional[set[str]] = None,
):
    statement = select(Document).where(Document.deleted_at.is_(None))
    if accessible_ids is not None:
        statement = statement.where(Document.id.in_(accessible_ids))
    if folder_id:
        statement = statement.where(Document.folder_id == folder_id)
    if query:
        escaped = (
            query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        statement = statement.where(
            Document.original_filename.ilike(f"%{escaped}%", escape="\\")
        )
    return statement


def list_documents(
    db: Session,
    folder_id: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    accessible_ids: Optional[set[str]] = None,
) -> tuple[list[Document], int]:
    statement = _filtered_statement(folder_id, query, accessible_ids)

    total = db.scalar(
        select(func.count()).select_from(statement.subquery()),
    )
    rows = db.scalars(
        statement.order_by(Document.created_at.desc(), Document.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return list(rows), int(total or 0)


def get_document(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.deleted_at is not None:
        raise DocumentNotFoundError(document_id)
    return document


def delete_document(db: Session, document: Document, uploads_dir: Path) -> Document:
    """Soft-delete the database row and remove the physical file from disk."""
    document.deleted_at = utcnow()
    db.add(document)
    db.commit()
    db.refresh(document)

    delete_stored_file(document.stored_filename, uploads_dir)
    try:
        vectordb.delete_document_vectors(vectordb.get_collection(), document.id)
    except Exception:  # noqa: BLE001 - vector cleanup must never block deletion
        logger.warning(
            "documents.vector_delete_failed",
            exc_info=True,
            extra={"document_id": document.id},
        )
    logger.info(
        "documents.deleted",
        extra={
            "document_id": document.id,
            "original_filename": document.original_filename,
        },
    )
    return document
