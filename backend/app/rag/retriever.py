"""Hybrid retrieval: dense vectors + BM25 merged with Reciprocal Rank Fusion."""

import logging
from dataclasses import dataclass
from typing import Optional

from app.rag import bm25, embedder, vectordb

logger = logging.getLogger("orbit.rag.retriever")

RRF_K = 60
DEFAULT_TOP_K = 10
_CORPUS_CACHE_LIMIT = 32

# Cache key: (collection object identity, chunk count) -> (index, candidates)
_corpus_cache: dict[tuple[int, int], tuple[bm25.BM25Index, dict[str, "Candidate"]]] = {}


@dataclass
class Candidate:
    id: str
    text: str
    document_id: str
    filename: str
    page: int
    chunk_index: int


def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list[Candidate]:
    """Return the top ``top_k`` chunks for ``query`` via hybrid fusion."""
    collection = vectordb.get_collection()
    if collection.count() == 0:
        return []

    dense = _dense_candidates(collection, query, top_k)
    sparse = _sparse_candidates(collection, query, top_k)
    return _rrf_merge(dense, sparse, top_k)


def _dense_candidates(collection, query: str, top_k: int) -> list[Candidate]:
    try:
        vector = embedder.encode_texts([query])
    except Exception:  # noqa: BLE001 - dense side must not break the query
        logger.warning("rag.retrieval.dense_failed", exc_info=True)
        return []
    if not vector:
        return []

    try:
        result = collection.query(
            query_embeddings=vector,
            n_results=top_k,
            include=["documents", "metadatas"],
        )
    except Exception:  # noqa: BLE001 - fall back to lexical-only ranking
        logger.warning("rag.retrieval.chroma_query_failed", exc_info=True)
        return []

    ids = result.get("ids") or [[]]
    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    return [
        _candidate(chunk_id, text, metadata)
        for chunk_id, text, metadata in zip(ids[0], documents[0], metadatas[0])
    ]


def _sparse_candidates(collection, query: str, top_k: int) -> list[Candidate]:
    index, candidates = _get_corpus(collection)
    return [
        candidates[chunk_id]
        for chunk_id, _score in index.search(query, top_k)
        if chunk_id in candidates
    ]


def _get_corpus(collection) -> tuple[bm25.BM25Index, dict[str, Candidate]]:
    """Return the cached BM25 index + candidate map for the current corpus."""
    count = collection.count()
    key = (id(collection), count)
    cached = _corpus_cache.get(key)
    if cached is not None:
        return cached

    data = collection.get(include=["documents", "metadatas"])
    ids = data.get("ids") or []
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []
    candidates = {
        chunk_id: _candidate(chunk_id, text, metadata)
        for chunk_id, text, metadata in zip(ids, documents, metadatas)
    }
    built = (
        bm25.build_index(ids, documents),
        candidates,
    )
    if len(_corpus_cache) >= _CORPUS_CACHE_LIMIT:
        _corpus_cache.clear()
    _corpus_cache[key] = built
    return built


def _candidate(chunk_id: str, text: str, metadata: Optional[dict]) -> Candidate:
    metadata = metadata or {}
    document_id = str(metadata.get("document_id", chunk_id.split(":")[0]))
    filename = str(metadata.get("filename", ""))
    page = int(metadata.get("page", 1))
    chunk_index = int(metadata.get("chunk_index", 0))
    return Candidate(
        id=chunk_id,
        text=text or "",
        document_id=document_id,
        filename=filename,
        page=page,
        chunk_index=chunk_index,
    )


def _rrf_merge(
    dense: list[Candidate],
    sparse: list[Candidate],
    top_k: int,
) -> list[Candidate]:
    """Reciprocal Rank Fusion: score = sum over rankings of 1 / (k + rank)."""
    scores: dict[str, float] = {}
    payloads: dict[str, Candidate] = {}

    for ranking in (dense, sparse):
        for rank, candidate in enumerate(ranking, start=1):
            scores[candidate.id] = scores.get(candidate.id, 0.0) + 1.0 / (RRF_K + rank)
            payloads[candidate.id] = candidate

    ordered = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
    return [payloads[chunk_id] for chunk_id in ordered[:top_k]]


def clear_corpus_cache() -> None:
    """Drop the BM25 cache (tests only)."""
    _corpus_cache.clear()
