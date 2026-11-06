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
