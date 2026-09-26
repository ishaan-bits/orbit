"""Indexing pipeline: parse -> chunk -> embed -> store, with status tracking."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import Session

from app.models.knowledge import Document, DocumentChunk, DocumentStatus
from app.rag import embedder, vectordb
from app.rag.chunker import Chunk, chunk_pages
from app.rag.parser import parse_file

logger = logging.getLogger("orbit.rag.indexer")

PROGRESS_STARTED = 10
PROGRESS_PARSED = 30
PROGRESS_CHUNKED = 50
PROGRESS_EMBEDDED = 80
PROGRESS_STORED = 100


class IndexingError(Exception):
    """Expected pipeline failure (missing file, no text, ...)."""


@dataclass
class IndexingResult:
    document_id: str
    status: str
    progress: int
    chunk_count: int
    error: Optional[str] = None


def index_document(
    db: Session, document: Document, uploads_dir: Path
) -> IndexingResult:
    """Run the full indexing pipeline for a document. Never raises."""
    progress = 0
    document.status = DocumentStatus.PROCESSING
    document.index_error = None
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        file_path = uploads_dir / document.stored_filename
        if not file_path.is_file():
            raise IndexingError("Stored file is missing from disk")

        pages = parse_file(file_path)
        progress = PROGRESS_PARSED

        chunks = chunk_pages(pages)
        if not chunks:
            raise IndexingError("No text could be extracted from the document")
        progress = PROGRESS_CHUNKED

        vectors = embedder.encode_texts([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise IndexingError("Embedding count did not match chunk count")
        progress = PROGRESS_EMBEDDED

        _store(db, document, chunks, vectors)
        progress = PROGRESS_STORED
    except Exception as exc:  # noqa: BLE001 - graceful failure is the contract
        logger.error(
            "rag.indexing.failed",
            extra={
                "document_id": document.id,
                "error": str(exc),
                "progress": progress,
            },
            exc_info=True,
        )
        return _mark_failed(db, document, str(exc), progress)

    logger.info(
        "rag.indexing.completed",
        extra={
            "document_id": document.id,
            "chunk_count": len(chunks),
            "page_count": len(pages),
        },
    )
    return IndexingResult(
        document_id=document.id,
        status=DocumentStatus.INDEXED,
        progress=PROGRESS_STORED,
        chunk_count=len(chunks),
    )


def _store(
    db: Session,
    document: Document,
    chunks: list[Chunk],
    vectors: list[list[float]],
) -> None:
    collection = vectordb.get_collection()
    vectordb.delete_document_vectors(collection, document.id)
    vectordb.upsert_chunks(
        collection,
        ids=[f"{document.id}:{chunk.chunk_index}" for chunk in chunks],
        embeddings=vectors,
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {
                "document_id": document.id,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "filename": document.original_filename,
            }
            for chunk in chunks
        ],
    )

    db.execute(
        sql_delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
    )
    db.add_all(
        DocumentChunk(
            document_id=document.id,
            chunk_index=chunk.chunk_index,
            page=chunk.page,
            char_count=len(chunk.text),
        )
        for chunk in chunks
    )
    document.status = DocumentStatus.INDEXED
    document.chunk_count = len(chunks)
    document.index_error = None
    db.add(document)
    db.commit()
    db.refresh(document)


def _mark_failed(
    db: Session,
    document: Document,
    error: str,
    progress: int,
) -> IndexingResult:
    """Roll back partial work and record the failure. Never raises."""
    db.rollback()
    try:
        db.execute(
            sql_delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        document.status = DocumentStatus.FAILED
        document.chunk_count = 0
        document.index_error = error[:500]
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:  # noqa: BLE001 - last-resort cleanup
        logger.exception(
            "rag.indexing.failed_cleanup", extra={"document_id": document.id}
        )
        db.rollback()

    try:
        vectordb.delete_document_vectors(vectordb.get_collection(), document.id)
    except Exception:  # noqa: BLE001 - best-effort vector cleanup
        logger.warning(
            "rag.indexing.vector_cleanup_failed",
            extra={"document_id": document.id},
            exc_info=True,
        )

    return IndexingResult(
        document_id=document.id,
        status=DocumentStatus.FAILED,
        progress=progress,
        chunk_count=0,
        error=error[:500],
    )
