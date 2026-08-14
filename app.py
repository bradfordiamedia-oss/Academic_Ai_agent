"""Academic Agent - Streamlit app.

Two tools:
1. Thesis Qualification Checker - upload university guidelines + a thesis,
   get a qualification verdict, acceptance percentage, and a full report.
2. Exam Auto-Grader - upload questions, an answer key, and a student's
   answers, get a score, pass/fail, and per-question feedback.
"""
from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from src.document_parser import extract_text
from src.exam_grader import grade_exam
from src.thesis_evaluator import evaluate_thesis
from src.ui import inject_theme, render_gauge, render_header, require_login

load_dotenv()

st.set_page_config(page_title="Bradford Academic Agent", page_icon="🎓", layout="wide")

require_login()
inject_theme()
render_header("Academic Agent")

tool_choice = st.sidebar.radio(
    "Choose a tool",
    ["🎓 Thesis Qualification Checker", "📝 Exam Auto-Grader"],
)
tool = tool_choice.split(" ", 1)[1]


@st.cache_data(show_spinner=False)
def _extract_cached(file_bytes: bytes, filename: str) -> str:
    return extract_text(file_bytes, filename)


@st.cache_data(show_spinner="Evaluating thesis against guidelines...")
def _evaluate_thesis_cached(guidelines_text: str, thesis_text: str) -> dict:
    return evaluate_thesis(guidelines_text, thesis_text)


@st.cache_data(show_spinner="Grading submission...")
def _grade_exam_cached(
    questions_text: str, answer_key_text: str, student_answers_text: str, passing_threshold: int
) -> dict:
    return grade_exam(questions_text, answer_key_text, student_answers_text, passing_threshold)


def _read_one(uploaded) -> str | None:
    try:
        with st.spinner(f"Reading {uploaded.name}..."):
            text = _extract_cached(uploaded.getvalue(), uploaded.name)
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


def _read_upload(label: str, key: str):
    uploaded = st.file_uploader(label, type=["pdf", "docx", "txt", "md"], key=key)
    if uploaded is None:
        return None
    return _read_one(uploaded)


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
        "Upload your university's thesis guidelines and the thesis document. "
        "The agent checks compliance and returns a qualification verdict, an "
        "acceptance percentage, and a full report."
    )

    col1, col2 = st.columns(2)
    with col1:
        guidelines_text = _read_upload("University guidelines", "guidelines")
    with col2:
        thesis_text = _read_upload("Thesis document", "thesis")

    if st.button("Evaluate Thesis", type="primary", disabled=not (guidelines_text and thesis_text)):
        try:
            result = _evaluate_thesis_cached(guidelines_text, thesis_text)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user
            st.error(f"Evaluation failed: {exc}")
            st.exception(exc)
        else:
            verdict = result.get("qualified", "Unknown")
            pct = result.get("acceptance_percentage", 0)

            gcol, vcol = st.columns([1, 1])
            with gcol:
                render_gauge(pct, "Acceptance")
            with vcol:
                st.metric("Verdict", verdict)

            st.subheader("Full Report")
            report_md = result.get("full_report_markdown", "")
            st.markdown(report_md)

            st.download_button(
                "Download report (Markdown)",
                data=report_md,
                file_name="thesis_evaluation_report.md",
                mime="text/markdown",
            )

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
                "Download report (Markdown)",
                data=report_md,
                file_name="exam_grading_report.md",
                mime="text/markdown",
            )
