"""Embedding providers: Gemini API (Render) or local BAAI/bge-small (dev).

``settings.embedding_provider`` selects the backend:

* ``gemini``  -- ``gemini-embedding-001`` over HTTP. Used on Render where
  loading torch would push the 512MB instance over its limit. On failure it
  falls back to the local model only when ``embedding_fallback == "local"``
  (the dev default); production sets ``EMBEDDING_FALLBACK=none`` so the
  error surfaces instead of OOM-crashing the process.
* ``local``   -- ``BAAI/bge-small-en-v1.5`` via SentenceTransformers, a
  process-wide singleton loaded on first use (the default everywhere).

Both paths keep the public contract of :func:`encode_texts`: one
L2-normalizable vector per input text, embedded in batches of at most
:data:`INDEX_EMBED_BATCH_SIZE` inputs.
"""

import logging
import os
import threading

import httpx

from app.core.config import settings

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = 32

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_OUTPUT_DIM = 768
GEMINI_TIMEOUT = 30.0
# Maximum texts sent to the embedding backend per request (<=16 per spec).
INDEX_EMBED_BATCH_SIZE = 16

# Keep torch's CPU pools small: Render's 512MB instance cannot afford
# default OpenMP/MKL thread arenas (overridable via environment).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logger = logging.getLogger("orbit.rag.embedder")

_model = None
_lock = threading.Lock()


class EmbeddingProviderError(Exception):
    """The remote embedding provider rejected or failed a request."""


def encode_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts, returning one vector per input (batched, <=16/request)."""
    if not texts:
        return []
    if settings.embedding_provider == "gemini":
        try:
            return _encode_gemini(texts)
        except Exception as exc:  # noqa: BLE001 - availability over failure
            if not _local_fallback_allowed():
                logger.error(
                    "embedder.gemini_failed_no_fallback",
                    extra={"error": str(exc)},
                )
                raise
            logger.warning(
                "embedder.gemini_failed_falling_back_local",
                extra={"error": str(exc)},
            )
    return _encode_local(texts)


def _local_fallback_allowed() -> bool:
    """Dev convenience only: production never loads torch (512MB Render).

    The gemini failure is propagated instead so the document records a
    clean ``index_error`` rather than the OOM killer restarting the app.
    """
    return (
        settings.embedding_fallback == "local"
        and settings.environment != "production"
    )


def _encode_local(texts: list[str]) -> list[list[float]]:
    model = get_model()
    vectors = model.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return [vector.tolist() for vector in vectors]


def _encode_gemini(texts: list[str]) -> list[list[float]]:
    """Embed via the Gemini API in batches of INDEX_EMBED_BATCH_SIZE."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), INDEX_EMBED_BATCH_SIZE):
        chunk = texts[start : start + INDEX_EMBED_BATCH_SIZE]
        vectors.extend(_post_gemini_embeddings(chunk))
    return vectors


def _post_gemini_embeddings(chunk: list[str]) -> list[list[float]]:
    if not settings.gemini_api_key:
        raise EmbeddingProviderError("GEMINI_API_KEY is not configured")

    url = (
        f"{settings.gemini_base_url}/models/"
        f"{GEMINI_EMBEDDING_MODEL}:batchEmbedContents"
    )
    payload = {
        "requests": [
            {
                "model": f"models/{GEMINI_EMBEDDING_MODEL}",
                "content": {"parts": [{"text": text}]},
                "outputDimensionality": GEMINI_OUTPUT_DIM,
            }
            for text in chunk
        ]
    }
    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=GEMINI_TIMEOUT) as client:
            response = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise EmbeddingProviderError(
            f"Gemini embedding request failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise EmbeddingProviderError(
            f"Gemini embedding failed with HTTP {response.status_code}: "
            f"{response.text[:200]}"
        )

    data = response.json()
    values = [
        item.get("values") or []
        for item in data.get("embeddings", [])
    ]
    if len(values) != len(chunk) or any(not row for row in values):
        raise EmbeddingProviderError(
            f"Gemini returned {len(values)} embeddings for {len(chunk)} texts"
        )
    return values


def get_model():
    """Return the singleton SentenceTransformer, loading it on first call."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME)
                _limit_torch_threads()
    return _model


def _limit_torch_threads() -> None:
    """Keep torch's intra/inter-op pools at one thread (RSS guard)."""
    try:
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:  # pragma: no cover - already-initialized pools etc.
        pass


def local_model_loaded() -> bool:
    """True once the SentenceTransformer singleton has been loaded."""
    return _model is not None


def reset_model_for_tests() -> None:
    """Drop the cached model (tests only)."""
    global _model
    with _lock:
        _model = None
