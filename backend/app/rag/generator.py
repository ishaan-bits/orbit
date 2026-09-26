"""Answer generation with Gemini 2.5 Flash, grounded in retrieved context."""

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger("orbit.rag.generator")

MODEL_NAME = "gemini-3.8-flash"
REQUEST_TIMEOUT = 60.0

SYSTEM_PROMPT = (
    "You are Orbit, an enterprise knowledge assistant for the Orbit knowledge base.\n"
    "Rules you must always follow:\n"
    "- Answer ONLY from the provided context. Do not use outside knowledge.\n"
    "- Never hallucinate. Do not invent facts, names, dates or numbers.\n"
    "- If the context does not contain the answer, explicitly say that the "
    "information was not found in the knowledge base.\n"
    "- Cite the source of every claim inline as (filename, page N).\n"
    "- Respond in Markdown."
)


class GenerationError(Exception):
    """Gemini could not produce an answer."""


@dataclass
class Passage:
    """A reranked chunk handed to the model, with its citation label."""

    label: int
    filename: str
    page: int
    text: str


def build_user_prompt(query: str, passages: list[Passage]) -> str:
    blocks = [
        f"[{passage.label}] {passage.filename} — page {passage.page}\n{passage.text}"
        for passage in passages
    ]
    context = "\n\n".join(blocks) if blocks else "(no context)"
    return f"Context:\n{context}\n\nQuestion: {query}"


def generate_answer(query: str, passages: list[Passage]) -> str:
    """Return the full Markdown answer for ``query``."""
    _require_key()
    data = _post_json(_payload(query, passages))
    text = _extract_text(data)
    if not text:
        raise GenerationError("Gemini returned an empty response")
    return text


def stream_answer(query: str, passages: list[Passage]) -> Iterator[str]:
    """Yield the answer for ``query`` incrementally as it is generated."""
    _require_key()
    for data in _post_sse(_payload(query, passages)):
        piece = _extract_text(data)
        if piece:
            yield piece


def _require_key() -> None:
    if not settings.gemini_api_key:
        raise GenerationError("GEMINI_API_KEY is not configured")


def _payload(query: str, passages: list[Passage]) -> dict:
    return {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [
            {"role": "user", "parts": [{"text": build_user_prompt(query, passages)}]}
        ],
    }


def _headers() -> dict:
    return {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }


def _post_json(payload: dict) -> dict:
    url = f"{settings.gemini_base_url}/models/{MODEL_NAME}:generateContent"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(url, headers=_headers(), json=payload)
    except httpx.HTTPError as exc:
        raise GenerationError(f"Could not reach Gemini: {exc}") from exc
    if response.status_code != 200:
        raise GenerationError(_error_message(response))
    return response.json()


def _post_sse(payload: dict) -> Iterator[dict]:
    url = f"{settings.gemini_base_url}/models/{MODEL_NAME}:streamGenerateContent"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            with client.stream(
                "POST",
                url,
                headers=_headers(),
                params={"alt": "sse"},
                json=payload,
            ) as response:
                if response.status_code != 200:
                    response.read()
                    raise GenerationError(_error_message(response))
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if not chunk:
                        continue
                    try:
                        yield json.loads(chunk)
                    except json.JSONDecodeError:
                        logger.debug("rag.gemini.skip_unparseable_sse_chunk")
    except httpx.HTTPError as exc:
        raise GenerationError(f"Could not reach Gemini: {exc}") from exc


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    return "".join(part.get("text", "") for part in parts)


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        message = ((body.get("error") or {}).get("message")) or ""
        if message:
            return f"Gemini error: {message}"
    except ValueError:
        pass
    return f"Gemini error (HTTP {response.status_code})"
