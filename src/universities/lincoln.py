"""Lincoln University - Doctorate thesis feedback.

Source: "Guidelines for writing thesis paper" (Final Thesis Guideline - Doctorate). It sets the
thesis FORMAT (150-180 pages, 12 pt, 1.5 spacing, A4), the required chapters, the 10-15%
similarity allowance and the grounds for rejecting a thesis (not original, incorrect data,
insufficient discussion and analysis, typographical errors, improper presentation, mismatch
between the problem and the methodology). It does not contain a marking rubric, weights, a
grading scale or a pass mark. Until Lincoln supplies those:

* the default rubric below follows the required chapters (used only when the uploaded
  guidelines contain no readable rubric),
* the grading scale and pass mark are a provisional scale, and the report says so,
* no "integrity failure = fail" rule is applied (the guideline lists grounds for rejection
  but not a marking rule); findings are listed and change no marks.

Replace RUBRIC, SCALE and PASS_MARK with Lincoln's own and set `scale_note=""` when the
official marking scheme is available.
"""
from src.universities import ASSETS_DIR, University

RUBRIC = (
    ("Introduction, Scope and Objectives of the Study", 10),
    ("Abstract, Preface and Front Matter", 5),
    ("Review of Literature", 20),
    ("Research Methodology and Research Instrument", 20),
    ("Findings, Discussion and Data Analysis", 20),
    ("Suggestions, Recommendations and Limitations", 10),
    ("Organization and Format Compliance", 5),
    ("Grammar, Spelling and Presentation", 5),
    ("Bibliography and Citations", 5),
)

SCALE = (
    {"label": "Distinction", "min": 80, "max": 100, "meaning": "Outstanding {level} work."},
    {"label": "Merit", "min": 70, "max": 79, "meaning": "Clear pass at a high level."},
    {"label": "Good", "min": 60, "max": 69, "meaning": "Solid pass."},
    {"label": "Pass", "min": 50, "max": 59, "meaning": "Minimum pass band."},
    {"label": "Unsatisfactory (Fail)", "min": 0, "max": 49, "meaning": ""},
)

PROFILE = University(
    key="lincoln",
    name="Lincoln University",
    short="Lincoln University",
    issued_by="Bradford International Alliance",
    header_image=ASSETS_DIR / "report_header.png",
    footer_image=ASSETS_DIR / "report_footer.png",
    rubric=RUBRIC,
    scale=SCALE,
    pass_mark=50,
    scale_name="provisional",
    calibration="",
    strict_integrity=False,
    scale_note=(
        "Note: the Lincoln thesis guideline defines the thesis format, required chapters and grounds for "
        "rejection but not a marking rubric or grading scale. The criteria weights (when the guidelines "
        "give none), the bands above and the pass mark of 50% are provisional and must be confirmed "
        "against Lincoln's official marking scheme."
    ),
)
