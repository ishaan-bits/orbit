"""Document parsing: extract text page by page, preserving page numbers."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from app.core.memory import log_rss


class ParsingError(Exception):
    """Raised when a document cannot be parsed."""


@dataclass
class Page:
    """A single page of extracted text. Page numbers are 1-based."""

    page_number: int
    text: str


_TEXT_SUFFIXES = {".txt", ".md"}


def iter_file_pages(path: Path) -> Iterator[Page]:
    """Lazily yield pages of ``path`` one at a time.

    PDFs stream page-by-page with PyMuPDF so the whole document text is
    never held in memory. DOCX and plain text files yield a single page.
    Raises ``ParsingError`` on the first iteration for unusable files.
    """
    if not path.is_file():
        raise ParsingError(f"File not found: {path.name}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        yield from _iter_pdf_pages(path)
        return

    try:
        if suffix == ".docx":
            yield from _parse_docx(path)
        elif suffix in _TEXT_SUFFIXES:
            yield from _parse_text(path)
        else:
            raise ParsingError(f"Unsupported file type: {suffix or '(none)'}")
    except ParsingError:
        raise
    except Exception as exc:
        detail = str(exc).replace(str(path), path.name)
        raise ParsingError(f"Failed to parse {path.name}: {detail}") from exc


def parse_file(path: Path) -> list[Page]:
    """Parse ``path`` into an ordered list of pages.

    Convenience wrapper over :func:`iter_file_pages` for callers that
    genuinely need the full list (small files, tests).
    """
    return list(iter_file_pages(path))


def _iter_pdf_pages(path: Path) -> Iterator[Page]:
    import pymupdf

    try:
        with pymupdf.open(path) as doc:
            if doc.page_count == 0:
                raise ParsingError(f"PDF has no pages: {path.name}")
            log_rss("pdf_loaded")
            for index in range(doc.page_count):
                page = doc.load_page(index)
                text = page.get_text("text") or ""
                yield Page(page_number=index + 1, text=_clean(text))
                del page, text
    except ParsingError:
        raise
    except Exception as exc:
        detail = str(exc).replace(str(path), path.name)
        raise ParsingError(f"Failed to read PDF {path.name}: {detail}") from exc


def _parse_docx(path: Path) -> list[Page]:
    from docx import Document as DocxDocument

    document = DocxDocument(str(path))
    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    return [Page(page_number=1, text=_clean("\n".join(paragraphs)))]


def _parse_text(path: Path) -> list[Page]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return [Page(page_number=1, text=_clean(raw))]


def _clean(text: str) -> str:
    """Normalize whitespace runs without losing paragraph breaks."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if line:
            cleaned.append(line)
        elif cleaned and cleaned[-1] != "":
            cleaned.append("")
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned)
