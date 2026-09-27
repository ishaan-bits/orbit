"""Streaming indexing pipeline: parse -> chunk -> embed -> store per batch.

Built for Render's 512MB instance: pages are consumed lazily, chunks are
embedded in batches of at most :data:`INDEX_BATCH_SIZE` and written to
Chroma immediately. No document-sized list (pages, chunks, embeddings) is
ever materialized, and each batch's temporaries are dropped with a forced
``gc.collect()``. Every stage logs RSS via ``[MEM] <stage> <rss>MB``.
"""

import gc
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import Session

from app.core.memory import log_rss, rss_mb
from app.models.knowledge import Document, DocumentChunk, DocumentStatus
from app.rag import embedder, vectordb
from app.rag.chunker import Chunk, iter_chunks
from app.rag.parser import iter_file_pages

logger = logging.getLogger("orbit.rag.indexer")

PROGRESS_STARTED = 10
PROGRESS_PARSED = 30
PROGRESS_CHUNKED = 50
PROGRESS_EMBEDDED = 80
PROGRESS_STORED = 100

# Maximum chunks embedded and persisted per batch (bounded memory).
INDEX_BATCH_SIZE = 16


class IndexingError(Exception):
    """Expected pipeline failure (missing file, no text, ...)."""


@dataclass
class IndexingResult:
    document_id: str
    status: str
    progress: int
    chunk_count: int
    error: Optional[str] = None
    peak_rss_mb: Optional[int] = None


def index_document(
    db: Session, document: Document, uploads_dir: Path
) -> IndexingResult:
    """Run the streaming indexing pipeline for a document. Never raises."""
    progress = PROGRESS_STARTED
    peak = rss_mb()
    document.status = DocumentStatus.PROCESSING
    document.index_error = None
    db.add(document)
    db.commit()
    db.refresh(document)

    chunk_count = 0
    try:
        file_path = uploads_dir / document.stored_filename
        if not file_path.is_file():
            raise IndexingError("Stored file is missing from disk")

        collection = vectordb.get_collection()
        # Clear any previous attempt up front; batches append from here.
        vectordb.delete_document_vectors(collection, document.id)
        db.execute(
            sql_delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )
        db.commit()

        page_count = 0
        first_page_seen = False
        first_flush_done = False
        batch: list[Chunk] = []

        for page in iter_file_pages(file_path):
            page_count += 1
            if not first_page_seen:
                first_page_seen = True
                progress = PROGRESS_PARSED
            peak = max(peak, log_rss("page_extracted"))

            for chunk in iter_chunks(
                [page], start_index=chunk_count + len(batch)
            ):
                batch.append(chunk)
                if len(batch) >= INDEX_BATCH_SIZE:
                    if not first_flush_done:
                        first_flush_done = True
                        progress = PROGRESS_CHUNKED
                    _flush_batch(db, document, collection, batch)
                    chunk_count += len(batch)
                    batch = []  # drop the temporary batch list
                    gc.collect()
                    peak = max(peak, rss_mb())

        peak = max(peak, log_rss("chunked"))
        if batch:
            if not first_flush_done:
                progress = PROGRESS_CHUNKED
            _flush_batch(db, document, collection, batch)
            chunk_count += len(batch)
            batch = []
            gc.collect()
            peak = max(peak, rss_mb())

        if chunk_count == 0:
            raise IndexingError("No text could be extracted from the document")
        progress = PROGRESS_EMBEDDED

        document.status = DocumentStatus.INDEXED
        document.chunk_count = chunk_count
        document.index_error = None
        db.add(document)
        db.commit()
        db.refresh(document)
        progress = PROGRESS_STORED
        peak = max(peak, log_rss("completed"))
    except Exception as exc:  # noqa: BLE001 - graceful failure is the contract
        peak = max(peak, rss_mb())
        logger.error(
            "rag.indexing.failed",
            extra={
                "document_id": document.id,
                "error": str(exc),
                "progress": progress,
                "peak_rss_mb": peak,
            },
            exc_info=True,
        )
        return _mark_failed(db, document, str(exc), progress, peak)

    logger.info(
        "rag.indexing.completed",
        extra={
            "document_id": document.id,
            "chunk_count": chunk_count,
            "page_count": page_count,
            "peak_rss_mb": peak,
        },
    )
    return IndexingResult(
        document_id=document.id,
        status=DocumentStatus.INDEXED,
        progress=PROGRESS_STORED,
        chunk_count=chunk_count,
        peak_rss_mb=peak,
    )


def _flush_batch(
    db: Session,
    document: Document,
    collection,
    batch: list[Chunk],
) -> None:
    """Embed one batch (<= INDEX_BATCH_SIZE chunks) and persist it now."""
    texts = [chunk.text for chunk in batch]
    log_rss("chunk_batch")

    vectors = embedder.encode_texts(texts)
    if len(vectors) != len(batch):
        raise IndexingError("Embedding count did not match chunk count")

    vectordb.upsert_chunks(
        collection,
        ids=[f"{document.id}:{chunk.chunk_index}" for chunk in batch],
        embeddings=vectors,
        documents=texts,
        metadatas=[
            {
                "document_id": document.id,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "filename": document.original_filename,
            }
            for chunk in batch
        ],
    )
    db.add_all(
        DocumentChunk(
            document_id=document.id,
            chunk_index=chunk.chunk_index,
            page=chunk.page,
            char_count=len(chunk.text),
        )
        for chunk in batch
    )
    db.commit()

    del texts, vectors  # release batch references before the gc pass
    log_rss("embeddings_written")


def _mark_failed(
    db: Session,
    document: Document,
    error: str,
    progress: int,
    peak: int,
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
        peak_rss_mb=peak,
    )
