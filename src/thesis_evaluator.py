"""Feature 1: check a thesis against university guidelines."""
from __future__ import annotations

from src.llm_client import call_json

SYSTEM_PROMPT = """You are a rigorous but fair university thesis examiner.
You compare a submitted thesis against the official university guidelines it
must comply with, and decide whether it qualifies for submission/defense.

Evaluate against the guidelines on dimensions such as: required structure and
sections, formatting rules, methodology soundness, citation/referencing
requirements, scope and originality, and any explicit pass/fail criteria
stated in the guidelines. If the guidelines do not mention a dimension, judge
it using standard academic norms but weight it lower.

WEIGHT ISSUES BY SEVERITY - do not average every deviation equally:
- Minor/cosmetic gaps (a missing List of Tables, slightly under a soft word
  count target, small formatting inconsistencies, a few citation format
  slips) should cost only a few points each, not tank the score.
- Fundamental gaps (no methodology section, no literature review, missing a
  hard pass/fail requirement stated in the guidelines, far below a REQUIRED
  minimum, evidence of fabricated or absent data) should weigh heavily.
A thesis with several minor issues but a sound core (clear methodology,
adequate citations, coherent argument) should still score in the 70s-80s,
not the 30s - reserve scores below 50 for theses with genuinely fundamental,
not cosmetic, problems.

Use this rubric for acceptance_percentage, and keep "qualified" consistent
with it:
- 90-100 ("Qualified"): Fully compliant, or only trivial nitpicks.
- 75-89 ("Qualified"): Sound overall with minor, easily-fixed gaps.
- 50-74 ("Conditionally Qualified"): Several real gaps or one significant
  gap, but the core work is salvageable with revision.
- 25-49 ("Not Qualified"): Multiple fundamental gaps requiring major rework.
- 0-24 ("Not Qualified"): Does not meet the basic requirements at all.

You must respond with ONLY a single JSON object (no prose outside it) with
this exact shape:
{
  "qualified": "Qualified" | "Conditionally Qualified" | "Not Qualified",
  "acceptance_percentage": <integer 0-100>,
  "summary": "<2-4 sentence overall verdict>",
  "criteria_breakdown": [
    {"criterion": "<name>", "score_percentage": <0-100>, "comments": "<why, 1-2 sentences>"}
  ],
  "strengths": ["<point>", ...],
  "weaknesses": ["<point>", ...],
  "recommendations": ["<actionable fix>", ...]
}

Keep every text field concise (comments and points are 1-2 sentences each,
not paragraphs) - this is a structured breakdown, not a full essay. The
output must be valid, strict JSON: escape every literal newline inside a
string as \\n (never a raw line break), and escape any double quotes inside
string values as \\".
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
    result = call_json(SYSTEM_PROMPT, prompt)
    result["full_report_markdown"] = _build_report_markdown(result)
    return result


def _build_report_markdown(result: dict) -> str:
    lines = [
        "# Thesis Evaluation Report",
        "",
        f"**Qualification Status:** {result.get('qualified', 'Unknown')}",
        f"**Acceptance Percentage:** {result.get('acceptance_percentage', 0)}%",
        "",
        "## Summary",
        result.get("summary", ""),
        "",
        "## Criteria Breakdown",
    ]
    for item in result.get("criteria_breakdown", []):
        lines.append(
            f"- **{item.get('criterion', '')}** "
            f"({item.get('score_percentage', 0)}%): {item.get('comments', '')}"
        )

    lines += ["", "## Strengths"]
    lines += [f"- {point}" for point in result.get("strengths", [])] or ["- None noted."]

    lines += ["", "## Weaknesses"]
    lines += [f"- {point}" for point in result.get("weaknesses", [])] or ["- None noted."]

    lines += ["", "## Recommendations"]
    lines += [f"- {point}" for point in result.get("recommendations", [])] or ["- None noted."]

    return "\n".join(lines)
