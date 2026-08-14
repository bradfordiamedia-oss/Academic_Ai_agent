"""Feature 1: check a thesis against university guidelines."""
from __future__ import annotations

from src.llm_client import call_json

SYSTEM_PROMPT = """You are a strict, experienced university thesis examiner.
You compare a submitted thesis against the official university guidelines it
must comply with, and decide whether it qualifies for submission/defense.

Evaluate against the guidelines on dimensions such as: required structure and
sections, formatting rules, methodology soundness, citation/referencing
requirements, scope and originality, and any explicit pass/fail criteria
stated in the guidelines. If the guidelines do not mention a dimension, judge
it using standard academic norms but weight it lower.

You must respond with ONLY a single JSON object (no prose outside it) with
this exact shape:
{
  "qualified": "Qualified" | "Conditionally Qualified" | "Not Qualified",
  "acceptance_percentage": <integer 0-100>,
  "summary": "<2-4 sentence overall verdict>",
  "criteria_breakdown": [
    {"criterion": "<name>", "score_percentage": <0-100>, "comments": "<why>"}
  ],
  "strengths": ["<point>", ...],
  "weaknesses": ["<point>", ...],
  "recommendations": ["<actionable fix>", ...],
  "full_report_markdown": "<complete standalone markdown report combining all of the above into readable sections with headings>"
}

The output must be valid, strict JSON: escape every literal newline inside a
string as \\n (never a raw line break), and escape any double quotes inside
string values as \\". This applies especially to "full_report_markdown",
which is long - make sure every line break in it is written as \\n.
"""

USER_PROMPT_TEMPLATE = """UNIVERSITY GUIDELINES:
---
{guidelines}
---

SUBMITTED THESIS:
---
{thesis}
---

Evaluate the thesis against the guidelines and respond with the JSON object
described in your instructions."""


def evaluate_thesis(guidelines_text: str, thesis_text: str) -> dict:
    prompt = USER_PROMPT_TEMPLATE.format(
        guidelines=guidelines_text.strip(),
        thesis=thesis_text.strip(),
    )
    return call_json(SYSTEM_PROMPT, prompt)
