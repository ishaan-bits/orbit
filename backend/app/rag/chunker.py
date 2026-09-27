"""Recursive character splitting into ~500-token chunks with 100-token overlap.

Tokens are approximated as ``CHARS_PER_TOKEN`` characters (English prose is
~4 chars/token), so the defaults are 2000 chars per chunk and 400 chars of
overlap. Chunks never span pages: every chunk carries the page it came from
and the global, ordered ``chunk_index`` of the document.
"""

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

from app.rag.parser import Page

CHUNK_SIZE_TOKENS = 500
OVERLAP_TOKENS = 100
CHARS_PER_TOKEN = 4

CHUNK_SIZE_CHARS = CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN

_SEPARATORS: Sequence[str] = ("\n\n", "\n", ". ", " ", "")


@dataclass
class Chunk:
    text: str
    page: int
    chunk_index: int


def iter_chunks(
    pages: Iterable[Page], start_index: int = 0
) -> Iterator[Chunk]:
    """Yield chunks incrementally with a running document-wide index.

    Pages must arrive in ascending page order (streaming parsers do);
    ``start_index`` continues numbering across separate calls. Nothing
    beyond the current page is ever held in memory.
    """
    next_index = start_index
    for page in pages:
        if not page.text.strip():
            continue
        for piece in _split_with_overlap(page.text):
            yield Chunk(
                text=piece,
                page=page.page_number,
                chunk_index=next_index,
            )
            next_index += 1


def chunk_pages(pages: Iterable[Page]) -> list[Chunk]:
    """Split pages into ordered chunks, preserving page metadata."""
    ordered_pages = sorted(pages, key=lambda p: p.page_number)
    return list(iter_chunks(ordered_pages))


def _split_with_overlap(
    text: str,
    size: int = CHUNK_SIZE_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[str]:
    """Merge split parts into chunks, seeding each new chunk with the tail
    of its predecessor so neighbouring chunks share ``overlap`` characters."""
    parts = _recursive_split(text, size)
    if not parts:
        return []

    chunks: list[str] = []
    buffer = ""
    for part in parts:
        if buffer and len(buffer) + len(part) > size:
            chunks.append(buffer)
            seeded = _seed(buffer, part, overlap)
            buffer = seeded if len(seeded) <= size else part
        else:
            buffer += part
    if buffer.strip():
        chunks.append(buffer)
    return chunks


def _seed(previous: str, part: str, overlap: int) -> str:
    """Start the next chunk with a word-aligned tail of the previous one."""
    if overlap <= 0:
        return part
    tail = previous[-overlap:]
    space = tail.find(" ")
    if 0 <= space < len(tail) - 1:
        tail = tail[space + 1 :]
    if part.startswith(tail):
        return part
    return tail + part


def _recursive_split(
    text: str, size: int, separators: Sequence[str] = _SEPARATORS
) -> list[str]:
    if len(text) <= size:
        return [text] if text.strip() else []

    separator = next((s for s in separators if s and s in text), None)
    if separator is None:
        return [
            text[i : i + size]
            for i in range(0, len(text), size)
            if text[i : i + size].strip()
        ]

    parts: list[str] = []
    splits = text.split(separator)
    for index, piece in enumerate(splits):
        if index < len(splits) - 1:
            piece += separator
        if not piece.strip():
            continue
        if len(piece) <= size:
            parts.append(piece)
        else:
            parts.extend(_recursive_split(piece, size, separators))
    return parts
