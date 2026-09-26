"""Document parsing: extract text page by page, preserving page numbers."""

from dataclasses import dataclass
from pathlib import Path


class ParsingError(Exception):
    """Raised when a document cannot be parsed."""


@dataclass
class Page:
    """A single page of extracted text. Page numbers are 1-based."""

    page_number: int
    text: str


_TEXT_SUFFIXES = {".txt", ".md"}


def parse_file(path: Path) -> list[Page]:
    """Parse ``path`` into an ordered list of pages.

    PDFs are parsed page-by-page with PyMuPDF (page numbers preserved).
    DOCX files have no page concept, so they yield a single page (page 1).
    Plain text/markdown files likewise yield a single page.
    """
    if not path.is_file():
        raise ParsingError(f"File not found: {path.name}")

    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return _parse_pdf(path)
        if suffix == ".docx":
            return _parse_docx(path)
        if suffix in _TEXT_SUFFIXES:
            return _parse_text(path)
    except ParsingError:
        raise
    except Exception as exc:
        detail = str(exc).replace(str(path), path.name)
        raise ParsingError(f"Failed to parse {path.name}: {detail}") from exc

    raise ParsingError(f"Unsupported file type: {suffix or '(none)'}")


def _parse_pdf(path: Path) -> list[Page]:
    import pymupdf

    pages: list[Page] = []
    try:
        with pymupdf.open(path) as doc:
            for index in range(doc.page_count):
                text = doc.load_page(index).get_text("text") or ""
                pages.append(Page(page_number=index + 1, text=_clean(text)))
    except ParsingError:
        raise
    except Exception as exc:
        detail = str(exc).replace(str(path), path.name)
        raise ParsingError(f"Failed to read PDF {path.name}: {detail}") from exc

    if not pages:
        raise ParsingError(f"PDF has no pages: {path.name}")
    return pages


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
