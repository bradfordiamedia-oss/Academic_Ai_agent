"""Render our own generated report markdown (headings, bullets, inline bold)
into a downloadable PDF. Targeted at the exact structure _build_report_markdown()
produces in thesis_evaluator.py / exam_grader.py - not a general markdown parser.
"""
from __future__ import annotations

from fpdf import FPDF

_BODY_SIZE = 11
_H1_SIZE = 18
_H2_SIZE = 14
_LINE_HEIGHT = 7


def markdown_to_pdf_bytes(markdown_text: str, title: str) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_title(_sanitize(title))
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=18, top=18, right=18)
    pdf.add_page()
    pdf.set_font("Helvetica", size=_BODY_SIZE)

    for raw_line in markdown_text.split("\n"):
        line = _sanitize(raw_line.rstrip())

        if not line.strip():
            pdf.ln(_LINE_HEIGHT / 2)
            continue

        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", _H1_SIZE)
            pdf.multi_cell(0, _H1_SIZE * 0.6, line[2:])
            pdf.set_font("Helvetica", size=_BODY_SIZE)
            pdf.ln(2)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", _H2_SIZE)
            pdf.multi_cell(0, _H2_SIZE * 0.6, line[3:])
            pdf.set_font("Helvetica", size=_BODY_SIZE)
            pdf.ln(1)
        elif line.startswith("- "):
            pdf.set_x(pdf.l_margin + 5)
            _write_inline_bold(pdf, f"-  {line[2:]}")
        else:
            _write_inline_bold(pdf, line)

    return bytes(pdf.output())


def _write_inline_bold(pdf: FPDF, text: str) -> None:
    """Render one line, toggling bold for **marker** segments."""
    segments = text.split("**")
    for i, segment in enumerate(segments):
        if not segment:
            continue
        pdf.set_font("Helvetica", "B" if i % 2 == 1 else "", _BODY_SIZE)
        pdf.write(_LINE_HEIGHT, segment)
    pdf.set_font("Helvetica", size=_BODY_SIZE)
    pdf.ln(_LINE_HEIGHT)


_UNICODE_ASCII_FALLBACKS = {
    "‘": "'", "’": "'",  # smart single quotes
    "“": '"', "”": '"',  # smart double quotes
    "–": "-", "—": "-",  # en/em dash
    "…": "...",  # ellipsis
    "•": "-",  # bullet
    " ": " ",  # non-breaking space
}


def _sanitize(text: str) -> str:
    """Core PDF fonts only support Latin-1. Normalize common "smart" typography
    (which real LLM output uses constantly) to plain ASCII first, so readable
    text doesn't collapse into '?' - then fall back to '?' only for anything
    genuinely outside Latin-1 (e.g. non-Latin scripts, emoji)."""
    for unicode_char, ascii_fallback in _UNICODE_ASCII_FALLBACKS.items():
        text = text.replace(unicode_char, ascii_fallback)
    return text.encode("latin-1", errors="replace").decode("latin-1")
