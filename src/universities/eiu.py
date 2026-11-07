"""European International University (EIU-Paris) - Doctorate Thesis Detailed Feedback.

This is the format the EIU sample report uses: Bradford letterhead, student details,
weighted marks, integrity findings, criterion feedback with quotes and sources, a
fix list and the EIU ECTS grading scale. Copy this file to add another university.
"""
from src.universities import ASSETS_DIR, University

RUBRIC = (
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
)

SCALE = (
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
)

CALIBRATION = """CALIBRATION EXAMPLE - the university's own marking of a doctoral thesis with critical integrity
problems (method still in the future tense, a stated 5-point scale contradicted by means above 5,
identical result rows for a direct path and a mediation path, a different person's name on the
certificate): Topic level 4, Abstract 4, Rationale 4, Literature Review 2.5 (mostly summarises),
Methodology 2, Data Analysis 1, Conclusion 1.5, Organization 3, Grammar 2, Citations 2, giving a
weighted total of 44 and a fail. Well-written opening sections can reach level 4 even when the
results are unsafe."""

PROFILE = University(
    key="eiu",
    name="EIU-Paris (European International University)",
    short="EIU-Paris",
    issued_by="Bradford International Alliance",
    header_image=ASSETS_DIR / "report_header.png",
    footer_image=ASSETS_DIR / "report_footer.png",
    rubric=RUBRIC,
    scale=SCALE,
    pass_mark=50,
    scale_name="ECTS",
    calibration=CALIBRATION,
    strict_integrity=True,
)
