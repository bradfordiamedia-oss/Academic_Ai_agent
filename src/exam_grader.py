"""Feature 2: grade a student's answer sheet against questions + answer key."""
from __future__ import annotations

from src.llm_client import call_json

SYSTEM_PROMPT = """You are a fair, consistent exam grader.
You are given the exam questions, the official answer key (with marks per
question if stated), and one student's submitted answers. Grade each
question, award partial credit where the student's answer is partially
correct, and compute a total score.

You must respond with ONLY a single JSON object (no prose outside it) with
this exact shape:
{
  "total_score": <number>,
  "max_score": <number>,
  "percentage": <number 0-100>,
  "passed": <boolean>,
  "question_breakdown": [
    {
      "question_number": "<id>",
      "marks_awarded": <number>,
      "marks_possible": <number>,
      "verdict": "Correct" | "Partially Correct" | "Incorrect",
      "feedback": "<short explanation>"
    }
  ],
  "overall_feedback": "<2-4 sentence summary for the student>",
  "full_report_markdown": "<complete standalone markdown report combining all of the above into readable sections with headings>"
}

If marks per question are not specified in the answer key, assume each
question is worth equal marks summing to 100. "passed" should reflect the
passing threshold given to you in the user message.

The output must be valid, strict JSON: escape every literal newline inside a
string as \\n (never a raw line break), and escape any double quotes inside
string values as \\". This applies especially to "full_report_markdown",
which is long - make sure every line break in it is written as \\n.
"""

USER_PROMPT_TEMPLATE = """EXAM QUESTIONS:
---
{questions}
---

OFFICIAL ANSWER KEY:
---
{answer_key}
---

STUDENT'S SUBMITTED ANSWERS:
---
{student_answers}
---

Passing threshold: {passing_threshold}% of total marks.

Grade the student's submission and respond with the JSON object described in
your instructions."""


def grade_exam(
    questions_text: str,
    answer_key_text: str,
    student_answers_text: str,
    passing_threshold: int = 50,
) -> dict:
    prompt = USER_PROMPT_TEMPLATE.format(
        questions=questions_text.strip(),
        answer_key=answer_key_text.strip(),
        student_answers=student_answers_text.strip(),
        passing_threshold=passing_threshold,
    )
    return call_json(SYSTEM_PROMPT, prompt)
