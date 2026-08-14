"""Text extraction for uploaded academic documents (PDF, DOCX, TXT)."""
from __future__ import annotations

import io

import pdfplumber
from docx import Document


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from an uploaded file based on its extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = _extract_pdf(file_bytes)
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


def _extract_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    text = "\n".join(text_parts)
    if text.strip():
        return text
    # No embedded text layer (likely a scanned/photographed PDF) - fall back to OCR.
    return _ocr_pdf(file_bytes)


def _ocr_pdf(file_bytes: bytes) -> str:
    try:
        import pymupdf as fitz
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""

    text_parts = []
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            for page in pdf:
                pixmap = page.get_pixmap(dpi=300)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                page_text = pytesseract.image_to_string(image)
                if page_text.strip():
                    text_parts.append(page_text)
    except Exception:
        # OCR engine (Tesseract binary) unavailable or failed - degrade gracefully.
        return ""
    return "\n".join(text_parts)


def _extract_docx(file_bytes: bytes) -> str:
    document = Document(io.BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
