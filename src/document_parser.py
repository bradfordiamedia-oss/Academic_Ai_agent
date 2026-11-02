"""Text extraction for uploaded academic documents (PDF, DOCX, TXT)."""
from __future__ import annotations

import io

import pdfplumber
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def extract_text(file_bytes: bytes, filename: str, page_markers: bool = False) -> str:
    """Extract plain text from an uploaded file based on its extension.

    With ``page_markers`` a PDF's text gets a ``[[Page N]]`` line before each
    page, so quotes can later be traced back to a real page number.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = _extract_pdf(file_bytes, page_markers)
    elif lower.endswith(".docx"):
        text = _extract_docx(file_bytes)
    elif lower.endswith(".txt") or lower.endswith(".md"):
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {filename}. Use PDF, DOCX, or TXT.")
    return _sanitize(text)


def _sanitize(text: str) -> str:
    """Strip characters that can't survive a UTF-8 round trip.

    OCR on noisy/garbled scans can occasionally produce invalid Unicode (e.g.
    lone surrogate characters from a botched byte decode somewhere upstream),
    which crashes the API request later. Scrubbing it here keeps that failure
    from ever reaching the LLM call.
    """
    return text.encode("utf-8", errors="ignore").decode("utf-8")


def _page_block(number: int, text: str, page_markers: bool) -> str:
    return f"[[Page {number}]]\n{text}" if page_markers else text


def _extract_pdf(file_bytes: bytes, page_markers: bool = False) -> str:
    text_parts = []
    has_text = False
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                has_text = True
            if page_markers or page_text:
                text_parts.append(_page_block(number, page_text or "", page_markers))
    if has_text:
        return "\n".join(text_parts)
    # No embedded text layer (likely a scanned/photographed PDF) - fall back to OCR.
    return _ocr_pdf(file_bytes, page_markers)


def _ocr_pdf(file_bytes: bytes, page_markers: bool = False) -> str:
    try:
        import pymupdf as fitz
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    text_parts = []
    has_text = False
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            for number, page in enumerate(pdf, start=1):
                pixmap = page.get_pixmap(dpi=300)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                page_text = pytesseract.image_to_string(image)
                if page_text.strip():
                    has_text = True
                if page_markers or page_text.strip():
                    text_parts.append(_page_block(number, page_text, page_markers))
    except Exception:
        # OCR engine (Tesseract binary) unavailable or failed - degrade gracefully.
        return ""
    # A doc where OCR found nothing on any page must still read as empty.
    return "\n".join(text_parts) if has_text else ""


def _extract_docx(file_bytes: bytes) -> str:
    """Paragraphs and tables, in document order (tables hold the thesis data)."""
    document = Document(io.BytesIO(file_bytes))
    lines = []
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            lines.append(Paragraph(child, document).text)
        elif tag == "tbl":
            for row in Table(child, document).rows:
                seen = set()
                cells = []
                for cell in row.cells:
                    if id(cell._tc) in seen:  # merged cells repeat the same cell
                        continue
                    seen.add(id(cell._tc))
                    cells.append(" ".join(cell.text.split()))
                lines.append(" | ".join(cells))
    return "\n".join(lines)
