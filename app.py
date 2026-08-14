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

load_dotenv()

st.set_page_config(page_title="Academic Agent", page_icon="🎓", layout="wide")
st.title("🎓 Academic Agent")

tool = st.sidebar.radio(
    "Choose a tool",
    ["Thesis Qualification Checker", "Exam Auto-Grader"],
)


def _read_upload(label: str, key: str):
    uploaded = st.file_uploader(label, type=["pdf", "docx", "txt", "md"], key=key)
    if uploaded is None:
        return None
    return extract_text(uploaded.getvalue(), uploaded.name)


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
        with st.spinner("Evaluating thesis against guidelines..."):
            try:
                result = evaluate_thesis(guidelines_text, thesis_text)
            except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                st.error(f"Evaluation failed: {exc}")
            else:
                verdict = result.get("qualified", "Unknown")
                pct = result.get("acceptance_percentage", 0)

                m1, m2 = st.columns(2)
                m1.metric("Verdict", verdict)
                m2.metric("Acceptance", f"{pct}%")

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
        student_answers_text = _read_upload("Student's answers", "student_answers")

    ready = bool(questions_text and answer_key_text and student_answers_text)
    if st.button("Grade Submission", type="primary", disabled=not ready):
        with st.spinner("Grading submission..."):
            try:
                result = grade_exam(
                    questions_text,
                    answer_key_text,
                    student_answers_text,
                    passing_threshold=passing_threshold,
                )
            except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                st.error(f"Grading failed: {exc}")
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Score", f"{result.get('total_score')} / {result.get('max_score')}")
                m2.metric("Percentage", f"{result.get('percentage')}%")
                m3.metric("Result", "Passed" if result.get("passed") else "Failed")

                st.subheader("Full Report")
                report_md = result.get("full_report_markdown", "")
                st.markdown(report_md)

                st.download_button(
                    "Download report (Markdown)",
                    data=report_md,
                    file_name="exam_grading_report.md",
                    mime="text/markdown",
                )
