"""Persistent ChromaDB client for document chunk vectors."""

import logging
import threading
from pathlib import Path
from typing import Optional

import chromadb

from app.core.config import settings

COLLECTION_NAME = "orbit_documents"

logger = logging.getLogger("orbit.rag.vectordb")

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_clients: dict[str, "chromadb.ClientAPI"] = {}
_collections: dict[str, "chromadb.Collection"] = {}
# Reentrant: get_collection() acquires the lock and then calls get_client().
_lock = threading.RLock()


def _resolve_path(path: Optional[str] = None) -> str:
    raw = Path(path or settings.chroma_path)
    if not raw.is_absolute():
        raw = _BACKEND_ROOT / raw
    return str(raw)


def get_client(path: Optional[str] = None) -> "chromadb.ClientAPI":
    """Return a persistent client (singleton per resolved path)."""
    resolved = _resolve_path(path)
    with _lock:
        if resolved not in _clients:
            _clients[resolved] = chromadb.PersistentClient(path=resolved)
    return _clients[resolved]


def get_collection(path: Optional[str] = None):
    """Return the ``orbit_documents`` collection (singleton per path)."""
    resolved = _resolve_path(path)
    with _lock:
        if resolved not in _collections:
            client = get_client(resolved)
            _collections[resolved] = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
    return _collections[resolved]


def upsert_chunks(
    collection,
    *,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    if not ids:
        return
    payload = {
        "ids": ids,
        "embeddings": embeddings,
        "documents": documents,
        "metadatas": metadatas,
    }
    try:
        collection.add(**payload)
    except Exception as exc:  # noqa: BLE001 - dimension repair is the contract
        if not _is_dimension_error(exc):
            raise
        logger.warning(
            "vectordb.dimension_mismatch_recreated",
            extra={"error": str(exc)},
        )
        _recreate_collection()
        get_collection().add(**payload)


def _is_dimension_error(exc: Exception) -> bool:
    return "dimension" in str(exc).lower()


def _recreate_collection() -> None:
    """Drop the collection after an embedding-dimension change.

    Called when the embedding provider switches (e.g. local 384-dim to
    Gemini 768-dim on Render): stored vectors are incompatible and the
    documents must be re-indexed.
    """
    resolved = _resolve_path()
    with _lock:
        _collections.pop(resolved, None)
        try:
            get_client(resolved).delete_collection(name=COLLECTION_NAME)
        except Exception:  # noqa: BLE001 - best-effort deletion
            logger.warning(
                "vectordb.collection_delete_failed", exc_info=True
            )
        _collections.pop(resolved, None)


def delete_document_vectors(collection, document_id: str) -> None:
    collection.delete(where={"document_id": document_id})


def count_document_vectors(collection, document_id: str) -> int:
    result = collection.get(where={"document_id": document_id}, include=[])
    return len(result.get("ids", []))
