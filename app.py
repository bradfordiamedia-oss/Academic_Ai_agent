"""Academic Agent - Streamlit app.

Two tools:
1. Thesis Qualification Checker - upload university guidelines + a thesis,
   get a qualification verdict, acceptance percentage, and a full report.
2. Exam Auto-Grader - upload questions, an answer key, and a student's
   answers, get a score, pass/fail, and per-question feedback.
"""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.document_parser import extract_text
from src.exam_grader import grade_exam
from src.feedback_pdf import build_feedback_pdf
from src.pdf_export import markdown_to_pdf_bytes
from src.thesis_evaluator import evaluate_thesis
from src.ui import inject_theme, render_gauge, render_header, require_login

load_dotenv()

ICON_PATH = Path(__file__).resolve().parent / "assets" / "bradford_icon.png"
st.set_page_config(page_title="Bradford Academic Agent", page_icon=str(ICON_PATH), layout="wide")

require_login()
inject_theme()
render_header("Academic Agent")

tool_choice = st.sidebar.radio(
    "Choose a tool",
    ["🎓 Thesis Qualification Checker", "📝 Exam Auto-Grader"],
)
tool = tool_choice.split(" ", 1)[1]


@st.cache_data(show_spinner=False)
def _extract_cached(file_bytes: bytes, filename: str, page_markers: bool = False) -> str:
    return extract_text(file_bytes, filename, page_markers)


@st.cache_data(show_spinner="Writing the detailed feedback report (this can take a minute)...")
def _evaluate_thesis_cached(
    guidelines_text: str, thesis_text: str, student_name: str, student_id: str, module: str
) -> dict:
    return evaluate_thesis(guidelines_text, thesis_text, student_name, student_id, module)


def _file_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-") or "Thesis"


@st.cache_data(show_spinner="Grading submission...")
def _grade_exam_cached(
    questions_text: str, answer_key_text: str, student_answers_text: str, passing_threshold: int
) -> dict:
    return grade_exam(questions_text, answer_key_text, student_answers_text, passing_threshold)


def _read_one(uploaded, page_markers: bool = False) -> str | None:
    try:
        with st.spinner(f"Reading {uploaded.name}..."):
            text = _extract_cached(uploaded.getvalue(), uploaded.name, page_markers)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the user
        st.error(f"Couldn't read {uploaded.name}: {exc}")
        return None
    if not text.strip():
        st.warning(
            f"No extractable text found in **{uploaded.name}**. If this is a "
            "scanned PDF (a photo/image of text rather than real text), this app "
            "can't read it directly — try a text-based export, or run it through "
            "OCR first."
        )
        return None
    return text


def _read_upload(label: str, key: str, page_markers: bool = False):
    uploaded = st.file_uploader(label, type=["pdf", "docx", "txt", "md"], key=key)
    if uploaded is None:
        return None
    return _read_one(uploaded, page_markers)


def _read_uploads_multi(label: str, key: str):
    """Like _read_upload, but accepts several files and combines them into one
    document (e.g. a multi-page answer sheet scanned as separate files)."""
    uploaded_files = st.file_uploader(
        label, type=["pdf", "docx", "txt", "md"], key=key, accept_multiple_files=True
    )
    if not uploaded_files:
        return None
    parts = []
    for uploaded in uploaded_files:
        text = _read_one(uploaded)
        if text is None:
            return None
        parts.append(f"--- {uploaded.name} ---\n{text}")
    return "\n\n".join(parts)


if tool == "Thesis Qualification Checker":
    st.header("Thesis Qualification Checker")
    st.write(
        "Upload your university's thesis guidelines (with its marking rubric) and the thesis. "
        "The agent marks every rubric criterion, flags integrity problems, backs each point with "
        "verified quotes and page numbers, and produces a Detailed Feedback report you can "
        "download as a PDF."
    )

    col1, col2 = st.columns(2)
    with col1:
        guidelines_text = _read_upload("University guidelines", "guidelines")
    with col2:
        thesis_text = _read_upload("Thesis document", "thesis", page_markers=True)

    with st.expander("Report details (optional)"):
        st.caption("Leave blank to use what the agent finds on the thesis cover page.")
        dcol1, dcol2, dcol3 = st.columns(3)
        student_name = dcol1.text_input("Student name")
        student_id = dcol2.text_input("ID number")
        module = dcol3.text_input("Module name / code")

    if st.button("Evaluate Thesis", type="primary", disabled=not (guidelines_text and thesis_text)):
        try:
            result = _evaluate_thesis_cached(
                guidelines_text, thesis_text, student_name.strip(), student_id.strip(), module.strip()
            )
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user
            st.error(f"Evaluation failed: {exc}")
            st.exception(exc)
        else:
            gcol, vcol = st.columns([1, 1])
            with gcol:
                render_gauge(result["overall_mark"], "Overall mark")
            with vcol:
                st.metric("Classification", result["classification"])
                st.download_button(
                    "Download Detailed Feedback (PDF)",
                    data=build_feedback_pdf(result),
                    file_name=f"{_file_slug(result['student']['name'])}_Detailed-Feedback.pdf",
                    mime="application/pdf",
                    on_click="ignore",
                    type="primary",
                )
            if result["quotes_dropped"]:
                st.caption(
                    f"{result['quotes_dropped']} quote(s) proposed by the model could not be found in "
                    "the thesis text and were left out of the report."
                )

            st.subheader("Full Report")
            st.markdown(result["full_report_markdown"])

else:
    st.header("Exam Auto-Grader")
    st.write(
        "Upload the exam questions, the official answer key, and a student's "
        "submitted answers. The agent scores the submission and reports "
        "pass/fail against your chosen threshold."
    )

    passing_threshold = st.slider("Passing threshold (%)", 0, 100, 50)

    col1, col2, col3 = st.columns(3)
    with col1:
        questions_text = _read_upload("Exam questions", "questions")
    with col2:
        answer_key_text = _read_upload("Official answer key", "answer_key")
    with col3:
        student_answers_text = _read_uploads_multi("Student's answers", "student_answers")

    ready = bool(questions_text and answer_key_text and student_answers_text)
    if st.button("Grade Submission", type="primary", disabled=not ready):
        try:
            result = _grade_exam_cached(
                questions_text, answer_key_text, student_answers_text, passing_threshold
            )
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user
            st.error(f"Grading failed: {exc}")
            st.exception(exc)
        else:
            gcol, scol, rcol = st.columns([1, 1, 1])
            with gcol:
                render_gauge(result.get("percentage", 0), "Score")
            with scol:
                st.metric("Score", f"{result.get('total_score')} / {result.get('max_score')}")
            with rcol:
                st.metric("Result", "Passed" if result.get("passed") else "Failed")

            st.subheader("Full Report")
            report_md = result.get("full_report_markdown", "")
            st.markdown(report_md)

            st.download_button(
                "Download report (PDF)",
                data=markdown_to_pdf_bytes(report_md, "Exam Grading Report"),
                file_name="exam_grading_report.pdf",
                mime="application/pdf",
                on_click="ignore",
            )
