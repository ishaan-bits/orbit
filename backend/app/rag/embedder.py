"""Embedding with BAAI/bge-small-en-v1.5 via SentenceTransformers.

The model is a process-wide singleton: it is loaded once on first use and
reused for every subsequent request.
"""

import threading

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_BATCH_SIZE = 32

_model = None
_lock = threading.Lock()


def get_model():
    """Return the singleton SentenceTransformer, loading it on first call."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME)
    return _model


def encode_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts, returning one L2-normalized vector per input."""
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(
        texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return [vector.tolist() for vector in vectors]


def reset_model_for_tests() -> None:
    """Drop the cached model (tests only)."""
    global _model
    with _lock:
        _model = None
