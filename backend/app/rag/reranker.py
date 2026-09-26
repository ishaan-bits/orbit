"""Cross-encoding reranking with BAAI/bge-reranker-base.

The model is a process-wide singleton. If it cannot be loaded, ranking
falls back to the incoming (fusion) order so chat keeps working.
"""

import logging
import threading

from app.rag.retriever import Candidate

logger = logging.getLogger("orbit.rag.reranker")

MODEL_NAME = "BAAI/bge-reranker-base"
DEFAULT_TOP_K = 3

_model = None
_lock = threading.Lock()


def get_model():
    """Return the singleton CrossEncoder, loading it on first call."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import CrossEncoder

                _model = CrossEncoder(MODEL_NAME)
    return _model


def rerank(
    query: str, candidates: list[Candidate], top_k: int = DEFAULT_TOP_K
) -> list[Candidate]:
    """Score candidates with the cross-encoder and return the best ``top_k``."""
    if not candidates:
        return []

    try:
        model = get_model()
        scores = model.predict([(query, candidate.text) for candidate in candidates])
    except Exception:  # noqa: BLE001 - degrade to fusion order rather than fail
        logger.warning("rag.rerank.model_failed", exc_info=True)
        return candidates[:top_k]

    scored = list(zip(candidates, [float(score) for score in scores]))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [candidate for candidate, _score in scored[:top_k]]


def reset_model_for_tests() -> None:
    """Drop the cached model (tests only)."""
    global _model
    with _lock:
        _model = None
