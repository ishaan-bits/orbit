import logging
import mimetypes
from pathlib import Path
from typing import Optional, Union

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.auth import User
from app.models.knowledge import Document, DocumentStatus
from app.rag import indexer as indexer_service
from app.schemas.knowledge import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
    IndexDocumentResponse,
)
from app.services import auth as auth_service
from app.services import documents as documents_service
from app.services.errors import (
    DocumentNotFoundError,
    EmptyFileError,
    FileTooLargeError,
    FolderAccessDeniedError,
    FolderNotFoundError,
    UnsupportedFileTypeError,
)
from app.services.storage import MAX_FILE_SIZE_MB, get_uploads_dir

router = APIRouter(tags=["documents"])
logger = logging.getLogger("orbit.api.documents")


def _accessible_ids(db: Session, user: User) -> Optional[set[str]]:
    return auth_service.get_accessible_document_ids(db, user)


def _require_document_access(db: Session, user: User, document) -> None:
    if not auth_service.can_access_document(db, user, document):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not have access to this document",
        )


def _media_type(document) -> str:
    """Correct MIME type for streaming, falling back to the extension."""
    mime = (document.mime_type or "").strip().lower()
    if mime not in {"", "application/octet-stream"}:
        return mime
    guessed, _ = mimetypes.guess_type(document.original_filename)
    return guessed or "application/octet-stream"


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(
        ..., description="PDF, DOCX, TXT or Markdown file (max 25MB)"
    ),
    folder_id: Optional[str] = Form(None, description="Target folder id"),
    db: Session = Depends(get_db),
    uploads_dir: Path = Depends(get_uploads_dir),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Upload a single document. Stores the file and returns its metadata."""
    try:
        document = await documents_service.upload_document(
            db, file, folder_id, uploads_dir, user=user
        )
    except UnsupportedFileTypeError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Allowed: PDF, DOCX, TXT, Markdown.",
        ) from None
    except FileTooLargeError:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB}MB size limit.",
        ) from None
    except EmptyFileError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        ) from None
    except FolderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except FolderAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    return DocumentResponse.model_validate(document)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    folder_id: Optional[str] = Query(None, description="Filter by folder"),
    q: Optional[str] = Query(None, description="Search by filename"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentListResponse:
    """List documents the caller's role may access, filtered by folder/search."""
    items, total = documents_service.list_documents(
        db,
        folder_id=folder_id,
        query=q,
        limit=limit,
        offset=offset,
        accessible_ids=_accessible_ids(db, user),
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    """Fetch metadata for a single document."""
    try:
        document = documents_service.get_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found",
        ) from None
    _require_document_access(db, user, document)
    return DocumentResponse.model_validate(document)


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: str,
    db: Session = Depends(get_db),
    uploads_dir: Path = Depends(get_uploads_dir),
    user: User = Depends(get_current_user),
) -> FileResponse:
    """Stream the original stored file to an authorized caller.

    Requires the session JWT (HTTP-only cookie or Bearer header), enforces
    the caller's role on the document, and answers with the correct MIME
    type. The bytes are streamed from disk — nothing is exposed publicly.
    """
    try:
        document = documents_service.get_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found",
        ) from None
    _require_document_access(db, user, document)

    path = uploads_dir / document.stored_filename
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The stored file is no longer available",
        )
    return FileResponse(
        path,
        media_type=_media_type(document),
        filename=document.original_filename,
    )


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    uploads_dir: Path = Depends(get_uploads_dir),
    user: User = Depends(get_current_user),
) -> DocumentDeleteResponse:
    """Soft-delete the document record and remove the stored file."""
    try:
        document = documents_service.get_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found",
        ) from None
    _require_document_access(db, user, document)

    documents_service.delete_document(db, document, uploads_dir)
    return DocumentDeleteResponse(id=document_id, status="deleted")


def _reindex_document_background(document_id: str, uploads_dir: Path) -> None:
    """Re-run indexing for one parked document in a fresh DB session.

    Runs via BackgroundTasks after the 202 response is sent, so pending
    documents are re-indexed in place — no re-upload needed.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or document.deleted_at is not None:
            return
        indexer_service.index_document(db, document, uploads_dir)
    except Exception:  # noqa: BLE001 - background jobs must not crash the app
        logger.exception(
            "documents.retry_background_failed",
            extra={"document_id": document_id},
        )
    finally:
        db.close()


@router.post(
    "/documents/retry-pending",
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_pending_documents(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    uploads_dir: Path = Depends(get_uploads_dir),
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Queue background re-indexing for every ``pending_retry`` document.

    Used after a Gemini 429 quota burst: files and metadata were preserved
    by the indexer, so documents are re-indexed in place. Answers 202
    immediately; the work happens in the background.
    """
    items, _total = documents_service.list_documents(
        db, limit=500, accessible_ids=_accessible_ids(db, user)
    )
    pending_ids = [
        item.id for item in items if item.status == DocumentStatus.PENDING_RETRY
    ]
    for document_id in pending_ids:
        background_tasks.add_task(
            _reindex_document_background, document_id, uploads_dir
        )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": DocumentStatus.PENDING_RETRY,
            "queued": len(pending_ids),
            "document_ids": pending_ids,
        },
    )


@router.post(
    "/documents/{document_id}/index",
    response_model=IndexDocumentResponse,
)
def index_document(
    document_id: str,
    db: Session = Depends(get_db),
    uploads_dir: Path = Depends(get_uploads_dir),
    user: User = Depends(get_current_user),
) -> Union[IndexDocumentResponse, JSONResponse]:
    """Run the indexing pipeline (parse, chunk, embed, store) for a document.

    Answers 200 with the final status. When the embedding quota (HTTP 429)
    is exhausted even after backoff, answers **202** with
    ``{"status": "pending_retry"}`` — the PDF and metadata are preserved
    and the document can be re-indexed later via POST
    ``/documents/retry-pending`` (or this endpoint) without re-uploading.
    """
    try:
        document = documents_service.get_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' was not found",
        ) from None
    _require_document_access(db, user, document)

    result = indexer_service.index_document(db, document, uploads_dir)
    payload = IndexDocumentResponse(
        document_id=result.document_id,
        status=result.status,
        progress=result.progress,
        chunk_count=result.chunk_count,
        error=result.error,
        peak_rss_mb=result.peak_rss_mb,
    )
    if result.status == DocumentStatus.PENDING_RETRY:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=payload.model_dump(mode="json"),
        )
    return payload
