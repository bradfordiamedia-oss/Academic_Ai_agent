"""Helpers shared by every university's Detailed Feedback report.

University-specific content (rubric, grading scale, pass mark, letterhead) lives
in `src/universities/`.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONT_DIR = ASSETS_DIR / "fonts"


def format_date(d: date | None = None) -> str:
    d = d or date.today()
    return f"{d.day} {d:%B %Y}"


def band_range_text(band: dict) -> str:
    if band["min"] == 0:
        return f"{band['max']}% and below"
    return f"{band['min']}-{band['max']}%"


def band_meaning(band: dict, level_word: str) -> str:
    text = band["meaning"].replace("{level}", level_word)
    return " ".join(text.split())
