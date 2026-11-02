"""Letterhead, grading scale and default rubric for the Detailed Feedback report.

Everything institution-specific lives here, so the issuing institution's
wording can be changed without touching the evaluator or the PDF renderer.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "eiu_logo.png"
FONT_DIR = ASSETS_DIR / "fonts"

INSTITUTION = {
    "name": "EUROPEAN INTERNATIONAL UNIVERSITY (EIU-Paris)",
    "short": "EIU-Paris",
    "subtitle": "European International University (EIU-Paris) | Paris, France",
    "header_lines": [
        "Paris, France | Établissement d'Enseignement Supérieur Privé",
        "UAI 0756213W",
        "ACBSP Accredited | QS Stars 5/5 | ASIC Premier Institution",
        "BrandLaureate Best Brand 2025 | CEOWORLD Top 50 for 2025",
    ],
    "footer_lines": [
        "59 Rue Lamarck, 75018 Paris, France | https://eiu.ac | info@eiu.ac | WhatsApp: +33 6 13 92 62 64",
        "Our ACBSP-accredited MBA is listed at #=92 in the QS Full-time MBA Rankings: Europe 2027 (global band #301+).",
        "Source: https://www.topuniversities.com/mba-rankings/europe",
    ],
    "issued_by": "European International University, EIU-Paris, 59 Rue Lamarck, 75018 Paris, France",
}

# (criterion name, weight %) - used only when the uploaded guidelines do not
# state a readable marking rubric. This is the EIU Doctorate Thesis rubric.
DEFAULT_RUBRIC = [
    ("Topic, Research Question and Thesis Statement", 5),
    ("Abstract", 5),
    ("Research Rationale", 5),
    ("Literature Review", 20),
    ("Methodology / Research Design", 20),
    ("Data Analysis and Presentation of Results/Findings", 20),
    ("Conclusion, Implications and Recommendations", 10),
    ("Organization", 5),
    ("Grammar and Punctuation", 5),
    ("Citations and References", 5),
]

PASS_MARK = 50

# ECTS-style scale. "{level}" is replaced with e.g. "doctoral" (or dropped).
DEFAULT_SCALE = [
    {"label": "Higher Distinction", "min": 90, "max": 100, "meaning": "Rare. Outstanding {level} work."},
    {"label": "Distinction", "min": 80, "max": 89, "meaning": "Strong {level} standard."},
    {"label": "First Division", "min": 70, "max": 79, "meaning": "Clear pass at a high level."},
    {
        "label": "Second Division",
        "min": 60,
        "max": 69,
        "meaning": "Solid pass. 60% is already very good under this European scale.",
    },
    {"label": "Satisfactory", "min": 50, "max": 59, "meaning": "Minimum pass band."},
    {"label": "Unsatisfactory (Fail)", "min": 0, "max": 49, "meaning": ""},
]


def format_date(d: date | None = None) -> str:
    d = d or date.today()
    return f"{d.day} {d:%B %Y}"


def scale_text_for_prompt() -> str:
    return "\n".join(
        f"- {band['min']}-{band['max']}: {band['label']}" for band in DEFAULT_SCALE
    )


def rubric_text_for_prompt() -> str:
    return "\n".join(f"{i}. {name} ({weight}%)" for i, (name, weight) in enumerate(DEFAULT_RUBRIC, 1))


def band_for(mark: int) -> dict:
    for band in DEFAULT_SCALE:
        if band["min"] <= mark <= band["max"]:
            return band
    return DEFAULT_SCALE[-1]


def band_range_text(band: dict) -> str:
    if band["min"] == 0:
        return f"{band['max']}% and below"
    return f"{band['min']}-{band['max']}%"


def band_meaning(band: dict, level_word: str) -> str:
    text = band["meaning"].replace("{level}", level_word)
    return " ".join(text.split())
