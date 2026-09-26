"""Persistent ChromaDB client for document chunk vectors."""

import threading
from pathlib import Path
from typing import Optional

import chromadb

from app.core.config import settings

COLLECTION_NAME = "orbit_documents"

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
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def delete_document_vectors(collection, document_id: str) -> None:
    collection.delete(where={"document_id": document_id})


def count_document_vectors(collection, document_id: str) -> int:
    result = collection.get(where={"document_id": document_id}, include=[])
    return len(result.get("ids", []))
