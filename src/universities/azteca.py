"""Azteca University (Universidad Azteca) - Graduate Thesis feedback.

Source: "Azteca University Graduate Thesis Template - Guide Only (DA-ST-18)". That document
sets the thesis STRUCTURE (introduction, literature review, research design, results,
analysis, conclusions, bibliography) and APA verb-tense rules, but it does not contain a
marking rubric, weights, a grading scale or a pass mark. Until Azteca supplies those:

* the default rubric below follows the template's chapters (it is used only when the
  uploaded guidelines contain no readable rubric),
* the grading scale and pass mark are a provisional ECTS-style scale, and the report says so,
* EIU's "integrity failure = fail" rule is NOT applied (Azteca's template does not state it);
  integrity findings are listed but change no marks.

Replace RUBRIC, SCALE and PASS_MARK with Azteca's own and set `scale_note=""` when the
official marking scheme is available.
"""
from src.universities import ASSETS_DIR, University

RUBRIC = (
    ("Introduction: Background, Context and Purposes", 10),
    ("Abstract and Keywords", 5),
    ("Literature Review", 20),
    ("Methodology and Research Design", 20),
    ("Results and Data Analysis", 20),
    ("Conclusions and Recommendations", 10),
    ("Organization and Template Compliance", 5),
    ("Grammar, Style and APA Verb Tenses", 5),
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
    key="azteca",
    name="Azteca University (Universidad Azteca)",
    short="Azteca University",
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
        "Note: the Azteca thesis template (DA-ST-18) defines the thesis structure but not a marking rubric "
        "or grading scale. The criteria weights (when the guidelines give none), the bands above and the "
        "pass mark of 50% are provisional and must be confirmed against Azteca's official marking scheme."
    ),
)
