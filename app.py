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
from src.support_files import describe_support_file
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


@st.cache_data(show_spinner=False)
def _describe_cached(file_bytes: bytes, filename: str) -> str:
    return describe_support_file(file_bytes, filename)


@st.cache_data(show_spinner="Writing the detailed feedback report (this can take a minute)...")
def _evaluate_thesis_cached(
    guidelines_text: str,
    thesis_text: str,
    student_name: str,
    student_id: str,
    module: str,
    supporting: str,
    supporting_names: tuple,
    level: str,
) -> dict:
    return evaluate_thesis(
        guidelines_text, thesis_text, student_name, student_id, module, supporting, supporting_names, level
    )


def _explain_api_error(exc: Exception) -> str | None:
    """Plain-language message for account-level API problems (not code bugs)."""
    text = str(exc)
    if "credit balance is too low" in text:
        return (
            "The Anthropic API account has run out of credits, so nothing can be evaluated right now. "
            "Add credits under Plans & Billing in the Anthropic Console, then try again."
        )
    if "usage limits" in text:
        return (
            "The Anthropic API usage limit for this account has been reached. Raise the limit in the "
            "Anthropic Console (Settings > Limits) or wait for it to reset, then try again."
        )
    if "API key is invalid" in text or "authentication_error" in text:
        return "The Anthropic API key is invalid or was revoked. Update ANTHROPIC_API_KEY in the app's Secrets."
    return None


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
        message = str(exc)
        if uploaded.name.lower().endswith(".pdf") and any(
            hint in message for hint in ("Root object", "PDF", "EOF", "xref", "Stream")
        ):
            st.error(
                f"**{uploaded.name}** ({len(uploaded.getvalue()) / 1024:.1f} KB) isn't a valid PDF. It may be "
                "corrupted, cut off during download, empty, or a different file type renamed to .pdf. "
                "Please re-download or re-export it and upload it again."
            )
        else:
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


THESIS_FILE_TYPES = ["pdf", "docx", "txt", "md", "csv", "xlsx", "ok", "settings", "splsm", "json"]
MAX_THESIS_FILES = 10


def _read_thesis_files(label: str, key: str):
    """Up to 10 files: the thesis itself (PDF/DOCX) plus any data/model files
    (e.g. SmartPLS .txt/.ok/.settings/.splsm, CSV, Excel). Returns
    (thesis_text, supporting_summaries, supporting_names)."""
    files = st.file_uploader(
        label, type=THESIS_FILE_TYPES, key=key, accept_multiple_files=True,
        help=f"Up to {MAX_THESIS_FILES} files: the thesis (PDF or DOCX) plus any data or model files.",
    )
    if not files:
        return None, "", ()
    if len(files) > MAX_THESIS_FILES:
        st.error(f"Please upload at most {MAX_THESIS_FILES} files (you added {len(files)}).")
        return None, "", ()
    mains = [f for f in files if f.name.lower().endswith((".pdf", ".docx"))]
    if not mains:
        st.warning("Include the thesis itself (a PDF or DOCX) among the files.")
        return None, "", ()

    single_pdf = len(mains) == 1 and mains[0].name.lower().endswith(".pdf")
    parts = []
    for main in mains:
        text = _read_one(main, page_markers=single_pdf)
        if text is None:
            return None, "", ()
        parts.append(text if len(mains) == 1 else f"=== {main.name} ===\n{text}")

    others = [f for f in files if f not in mains]
    summaries = [_describe_cached(f.getvalue(), f.name) for f in others]
    return "\n\n".join(parts), "\n\n".join(summaries), tuple(f.name for f in others)


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
        thesis_text, supporting_text, supporting_names = _read_thesis_files(
            "Thesis document (+ up to 9 data/model files)", "thesis"
        )

    with st.expander("Report details (optional)"):
        st.caption("Leave blank to use what the agent finds on the thesis cover page.")
        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        student_name = dcol1.text_input("Student name")
        student_id = dcol2.text_input("ID number")
        module = dcol3.text_input("Module name / code")
        level_choice = dcol4.selectbox(
            "Programme level", ["Auto-detect", "Doctoral", "Master's", "Bachelor's"],
            help="Auto-detect reads the thesis cover page. Choose a level to override it.",
        )

    if st.button("Evaluate Thesis", type="primary", disabled=not (guidelines_text and thesis_text)):
        try:
            result = _evaluate_thesis_cached(
                guidelines_text, thesis_text, student_name.strip(), student_id.strip(), module.strip(),
                supporting_text, supporting_names,
                "" if level_choice == "Auto-detect" else level_choice,
            )
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user
            friendly = _explain_api_error(exc)
            if friendly:
                st.error(friendly)
            else:
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
            if result.get("outcome_note"):
                st.warning(result["outcome_note"])
            if result.get("findings_dropped"):
                st.caption(
                    f"{result['findings_dropped']} finding(s) were removed because the thesis text cannot support them."
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
            friendly = _explain_api_error(exc)
            if friendly:
                st.error(friendly)
            else:
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
