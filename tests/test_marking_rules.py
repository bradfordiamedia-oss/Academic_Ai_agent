"""Offline checks for the deterministic marking rules (no network, no API).

Run:  python tests/test_marking_rules.py     (or: pytest tests)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import thesis_evaluator as te  # noqa: E402
from src.reference_check import is_journal_article, split_entries  # noqa: E402

NAMES = [
    "Topic, Research Question and Thesis Statement", "Abstract", "Research Rationale", "Literature Review",
    "Methodology / Research Design", "Data Analysis and Presentation of Results/Findings",
    "Conclusion, Implications and Recommendations", "Organization", "Grammar and Punctuation",
    "Citations and References",
]


def criteria(marks):
    return [{"name": n, "mark": m, "weight": w} for n, m, w in zip(NAMES, marks, [5, 5, 5, 20, 20, 20, 10, 5, 5, 5])]


def finding(severity, affects):
    return {"title": "x", "severity": severity, "affects": affects, "detail": "", "quotes": []}


def marks(cs):
    return [c["mark"] for c in cs]


def test_unsafe_results_hold_data_at_20_and_conclusion_at_30():
    cs = criteria([80, 80, 80, 70, 70, 70, 70, 80, 70, 70])
    te._apply_integrity_caps(cs, [finding("critical", [5])])  # model says: damages Data Analysis (6th)
    assert marks(cs)[5] == 20 and marks(cs)[6] == 30


def test_other_critical_findings_only_hold_results_at_40():
    cs = criteria([80, 80, 80, 70, 70, 70, 70, 80, 70, 70])
    te._apply_integrity_caps(cs, [finding("critical", [0, 1, 2])])  # e.g. a name mismatch
    assert marks(cs)[:3] == [80, 80, 80], "front-matter criteria must not be capped"
    assert marks(cs)[5] == 40 and marks(cs)[6] == 40


def test_major_finding_caps_at_60_and_only_method_data_conclusion_citations():
    cs = criteria([80, 80, 80, 70, 90, 70, 70, 80, 70, 70])
    te._apply_integrity_caps(cs, [finding("major", [0, 4])])
    assert marks(cs)[0] == 80 and marks(cs)[4] == 60


def ref(share, articles=40):
    n = round(articles * share)
    return {"available": True, "articles": articles, "matched": articles - n,
            "unconfirmed": [f"Author{i}, A. (2024). Some title number {i}. Journal, 1(1), 1-2." for i in range(n)],
            "unconfirmed_share": n / articles}


def test_many_unconfirmed_references_limit_citations_and_literature():
    cs, fs = criteria([80, 80, 80, 70, 70, 70, 70, 80, 70, 70]), []
    caps = te._apply_reference_check(cs, fs, ref(0.31))
    assert fs and fs[0]["severity"] == "major"
    assert "not proof" in fs[0]["detail"] and "fabricat" not in fs[0]["detail"].lower()
    assert marks(cs)[3] == 50 and marks(cs)[9] == 40 and len(caps) == 2


def test_some_unconfirmed_references_only_raise_a_finding():
    cs, fs = criteria([80, 80, 80, 70, 70, 70, 70, 80, 70, 70]), []
    assert te._apply_reference_check(cs, fs, ref(0.20)) == []
    assert len(fs) == 1 and marks(cs)[3] == 70 and marks(cs)[9] == 70


def test_few_or_unavailable_reference_results_change_nothing():
    for result in (ref(0.05), None, {"available": False, "reason": "Crossref could not be reached"}, ref(0.5, 6)):
        cs, fs = criteria([80] * 10), []
        assert te._apply_reference_check(cs, fs, result) == [] and fs == []


def test_reference_date_claim_needs_a_later_printed_year():
    claim = {"title": "References dated after submission",
             "detail": "References dated 2026 appear after the thesis submission date of 4 November 2026"}
    assert te._unsupported_reference_date_claim(claim, 2026) is True
    assert te._unsupported_reference_date_claim(claim, None) is True
    later = {"title": "References dated after submission", "detail": "A 2027 reference follows the submission date of April 2026"}
    assert te._unsupported_reference_date_claim(later, 2026) is False


def test_reference_list_is_split_and_books_are_not_treated_as_articles():
    text = (
        "Introduction\n\nReferences\n"
        "Barney, J. (1991). Firm resources and sustained competitive advantage. Journal of\n"
        "Management, 17(1), 99-120.\n"
        "[[Page 5]]\n"
        "Creswell, J. W. (2018). Research design (5th ed.). SAGE Publications.\n"
        "Hair, J. F. (2011). PLS-SEM: Indeed a silver bullet. Journal of Marketing Theory and\n"
        "Practice, 19(2), 139-152.\n"
        "\nAppendix A\nSurvey\n"
    )
    entries = split_entries(__import__("src.reference_check", fromlist=["x"]).find_reference_section(text))
    assert len(entries) == 3, entries
    assert [is_journal_article(e) for e in entries] == [True, False, True]


def test_university_marks_reproduce_44_with_levels():
    levels = [4, 4, 4, 2.5, 2, 1, 1.5, 3, 2, 2]
    cs = criteria([int(v * 20) for v in levels])
    total = sum(c["mark"] * c["weight"] / 100 for c in cs)
    assert int(total + 0.5) == 44


def test_eiu_profile_matches_the_format_that_was_saved():
    from src.universities import choices, get_university
    eiu = get_university("eiu")
    assert eiu.pass_mark == 50 and eiu.strict_integrity and eiu.scale_name == "ECTS"
    assert [w for _, w in eiu.rubric] == [5, 5, 5, 20, 20, 20, 10, 5, 5, 5]
    assert eiu.band_for(45)["label"] == "Unsatisfactory (Fail)" and eiu.band_for(80)["label"] == "Distinction"
    assert eiu.next_band_up(45) == "Satisfactory" and eiu.next_band_up(95) is None
    assert eiu.header_image.exists() and eiu.footer_image.exists()
    assert ("eiu", "EIU-Paris (European International University)") in choices()
    assert get_university(None).key == "eiu" and get_university("unknown").key == "eiu"


def test_prompt_is_built_from_the_profile():
    prompt = te.build_system_prompt(__import__("src.universities", fromlist=["x"]).get_university("eiu"))
    assert "Abstract (5%)" in prompt and "90-100: Higher Distinction" in prompt
    assert "CALIBRATION EXAMPLE" in prompt and "{{" not in prompt


def test_non_strict_university_lists_findings_but_changes_no_marks():
    from dataclasses import replace
    from src.universities import get_university
    lenient = replace(get_university("eiu"), key="x", strict_integrity=False)
    raw = {"criteria": [{"name": n, "weight": w, "level": 4} for n, w in __import__("src.universities", fromlist=["x"]).get_university("eiu").rubric],
           "integrity_findings": [{"title": "t", "severity": "critical", "affects": [6], "detail": "d"}]}
    res = te._finalize(raw, "text", te._submission_facts("text"), "", "", "", "doctoral", None, lenient)
    assert res["overall_mark"] == 80 and not res["integrity_failure"] and res["caps"] == []
    assert res["integrity_findings"] and res["university"] == "x"


def test_azteca_profile_never_shows_eiu_wording():
    import io
    import pdfplumber
    from src.feedback_pdf import build_feedback_pdf
    from src.universities import choices, get_university
    az = get_university("azteca")
    assert az.key == "azteca" and "azteca" in dict(choices())
    assert sum(w for _, w in az.rubric) == 100 and not az.strict_integrity and az.scale_note
    prompt = te.build_system_prompt(az)
    assert "EIU" not in prompt and "cannot pass whatever" not in prompt and "{{" not in prompt
    raw = {"criteria": [{"name": n, "weight": w, "level": 3} for n, w in az.rubric],
           "integrity_findings": [{"title": "t", "severity": "critical", "affects": [5], "detail": "d"}]}
    res = te._finalize(raw, "text", te._submission_facts("text"), "", "", "", "doctoral", None, az)
    assert res["overall_mark"] == 60 and res["passed"] and res["integrity_failure"] is False
    with pdfplumber.open(io.BytesIO(build_feedback_pdf(res))) as pdf:
        text = chr(10).join(page.extract_text() or "" for page in pdf.pages)
    assert "EIU" not in text and "Azteca University Grading Scale" in text and "provisional" in text


def test_lincoln_profile_never_shows_other_university_names():
    import io
    import pdfplumber
    from src.feedback_pdf import build_feedback_pdf
    from src.universities import choices, get_university
    lin = get_university("lincoln")
    assert lin.key == "lincoln" and "lincoln" in dict(choices())
    assert sum(w for _, w in lin.rubric) == 100 and not lin.strict_integrity and lin.scale_note
    prompt = te.build_system_prompt(lin)
    assert "EIU" not in prompt and "Azteca" not in prompt and "{{" not in prompt
    raw = {"criteria": [{"name": n, "weight": w, "level": 3} for n, w in lin.rubric], "integrity_findings": []}
    res = te._finalize(raw, "text", te._submission_facts("text"), "", "", "", "doctoral", None, lin)
    assert res["overall_mark"] == 60 and res["university"] == "lincoln"
    with pdfplumber.open(io.BytesIO(build_feedback_pdf(res))) as pdf:
        text = chr(10).join(page.extract_text() or "" for page in pdf.pages)
    assert "EIU" not in text and "Azteca" not in text and "Lincoln University Grading Scale" in text


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print("FAIL", name, "-", repr(exc))
    sys.exit(1 if failed else 0)
