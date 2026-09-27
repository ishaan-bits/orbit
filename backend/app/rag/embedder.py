"""Embedding providers: Gemini API (Render) or local BAAI/bge-small (dev).

``settings.embedding_provider`` selects the backend:

* ``gemini``  -- ``gemini-embedding-001`` over HTTP. Used on Render where
  loading torch would push the 512MB instance over its limit. On failure it
  falls back to the local model only when ``embedding_fallback == "local"``
  (the dev default); production sets ``EMBEDDING_FALLBACK=none`` so the
  error surfaces instead of OOM-crashing the process. HTTP 429 quota
  responses are retried with exponential backoff (1s..16s, max 5 retries)
  and never fall back; exhaustion raises :class:`EmbeddingQuotaError` so
  the document can be parked as ``pending_retry``.
* ``local``   -- ``BAAI/bge-small-en-v1.5`` via SentenceTransformers, a
  process-wide singleton loaded on first use (the default everywhere).

Both paths keep the public contract of :func:`encode_texts`: one
L2-normalizable vector per input text, embedded in batches of at most
:data:`INDEX_EMBED_BATCH_SIZE` inputs.
"""

import json
import logging
import os
import threading
import time

import httpx

from app.core.config import settings

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = 32

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
GEMINI_OUTPUT_DIM = 768
GEMINI_TIMEOUT = 30.0
# Maximum texts sent to the embedding backend per request (<=16 per spec).
INDEX_EMBED_BATCH_SIZE = 16

# HTTP 429 quota handling: exponential backoff, max 5 retries per request.
# A quota breach is a runtime condition (plan/billing), never a reason to
# load the local model or lose the uploaded document.
GEMINI_429_MAX_RETRIES = 5
GEMINI_429_BACKOFF_SECONDS = (1.0, 2.0, 4.0, 8.0, 16.0)

# Keep torch's CPU pools small: Render's 512MB instance cannot afford
# default OpenMP/MKL thread arenas (overridable via environment).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logger = logging.getLogger("orbit.rag.embedder")

_model = None
_lock = threading.Lock()


class EmbeddingProviderError(Exception):
    """The remote embedding provider rejected or failed a request."""


class EmbeddingQuotaError(EmbeddingProviderError):
    """Gemini answered HTTP 429 even after all backoff retries.

    Carries the complete response body (quota metric) and the RetryInfo
    ``retryDelay`` hint so operators can see exactly which quota tripped.
    """

    def __init__(self, message: str, body: str = "", retry_delay: str = "") -> None:
        super().__init__(message)
        self.body = body
        self.retry_delay = retry_delay


def encode_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts, returning one vector per input (batched, <=16/request)."""
    if not texts:
        return []
    if settings.embedding_provider == "gemini":
        try:
            return _encode_gemini(texts)
        except EmbeddingQuotaError:
            # A 429 is a runtime condition: propagate it everywhere so the
            # indexer can park the document as pending_retry (never torch).
            raise
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

    for attempt in range(GEMINI_429_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=GEMINI_TIMEOUT) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(
                f"Gemini embedding request failed: {exc}"
            ) from exc

        if response.status_code == 429:
            body = response.text
            retry_delay = _parse_retry_delay(body)
            if attempt >= GEMINI_429_MAX_RETRIES:
                logger.error(
                    "embedder.gemini_429_exhausted",
                    extra={
                        "attempts": attempt + 1,
                        "retry_delay": retry_delay,
                        "body": body,
                    },
                )
                raise EmbeddingQuotaError(
                    "Gemini embedding quota exceeded after "
                    f"{GEMINI_429_MAX_RETRIES} backoff retries",
                    body=body,
                    retry_delay=retry_delay,
                )
            sleep_seconds = GEMINI_429_BACKOFF_SECONDS[attempt]
            logger.warning(
                "embedder.gemini_429_backoff",
                extra={
                    "attempt": attempt + 1,
                    "sleep_seconds": sleep_seconds,
                    "retry_delay": retry_delay,
                    "body": body,
                },
            )
            _backoff_sleep(sleep_seconds)
            continue

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

    raise EmbeddingProviderError(  # pragma: no cover - loop always returns
        "Gemini embedding retries exhausted"
    )


def _backoff_sleep(seconds: float) -> None:
    """Pause between 429 retries (seamless to stub out in tests)."""
    time.sleep(seconds)


def _parse_retry_delay(body: str) -> str:
    """Extract the RetryInfo ``retryDelay`` hint from a Google error body."""
    try:
        details = json.loads(body).get("error", {}).get("details", []) or []
    except (ValueError, AttributeError, TypeError):
        return ""
    for detail in details:
        if isinstance(detail, dict) and str(detail.get("@type", "")).endswith(
            "RetryInfo"
        ):
            return str(detail.get("retryDelay", ""))
    return ""


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
