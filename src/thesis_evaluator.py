"""Feature 1: examine a thesis against its assessment guidelines and produce a
"Detailed Feedback" report (rubric marks, integrity findings, evidence quotes,
fix list).

The model supplies judgement and evidence only. Everything checkable is done
here in code: contributions and the weighted total, the grading-scale band,
page numbers, and verification that every quote really appears in the thesis.
"""
from __future__ import annotations

import re
from bisect import bisect_right

from src import report_template as tpl
from src.llm_client import call_json

PAGE_MARKER = re.compile(r"\[\[Page (\d+)\]\]")

_SYSTEM_TEMPLATE = """You are an experienced university thesis examiner writing a DETAILED FEEDBACK report.
You receive the official assessment guidelines (usually containing a marking rubric) and the
submitted thesis text. Compare the thesis with the rubric, mark each criterion, and back every
judgement with evidence from the thesis.

The thesis text may contain lines like [[Page 12]]. They only mark PDF pages for the system and
are not part of the thesis. Never quote them and never state page numbers yourself - the system
adds verified page numbers to your quotes.

STEP 1 - RUBRIC
Use the criteria and percentage weights of the marking rubric in the guidelines (the guidelines
may be OCR text with a garbled table). If they contain no readable rubric or weights, use this
default rubric:
{{RUBRIC}}
Weights must add up to 100.

STEP 2 - MARKS
Give each criterion a whole-number mark from 0 to 100, calibrated to this European scale, where
60 is already a very good mark and 90+ is rare:
{{SCALE}}
Weight issues by severity; do not average every deviation equally:
- Minor or cosmetic gaps (a few formatting slips, small inconsistencies) cost only a few points.
- Fundamental gaps (a required section missing, far outside a REQUIRED word count, no real method
  or analysis, results that cannot be trusted) weigh heavily on the criteria they affect.
- Integrity problems visible in the text keep the affected criteria low (usually Methodology,
  Data Analysis, Conclusion, Citations): tables that contradict the prose or each other,
  identical or copied result rows, a method still written in the future tense in a finished
  thesis, a scale described one way and reported another, a name or title that differs between
  cover, declaration and certificate, in-text citations missing from the reference list or the
  reverse.
- Judge only what the thesis says - never the author's name, nationality or institution.
A thesis with a sound core and only minor gaps should score in the 70s-80s on those criteria.

LEVEL: mark to the standard of the programme level given in SUBMISSION FACTS. A doctoral thesis
must show an original contribution, a replicable method and trustworthy data; do not apply
master's-level leniency.

SEVERITY OF INTEGRITY FINDINGS: label each finding "critical", "major" or "minor".
- critical = made-up or unsafe data (means or values outside the stated scale, identical or copied
  result rows, demographic or result tables the data cannot support), a method still written in
  the future tense in a finished thesis, or a different person's name on the declaration or
  certificate.
- major = other contradictions between text and tables, missing ethics approval for human
  participants, in-text citations missing from the reference list or the reverse.
- minor = everything else.
In "affects" list the numbers of the rubric criteria a finding damages (for example Methodology,
Data Analysis, Conclusion, Citations). The system caps affected criteria at 40 for a critical
finding and 60 for a major one, so mark all other criteria on their own merits.

CALIBRATION EXAMPLE - the university's own marking of a doctoral thesis with critical integrity
problems (method still in the future tense, a stated 5-point scale contradicted by means above 5,
identical result rows for a direct path and a mediation path, a different person's name on the
certificate): Topic 80, Abstract 80, Rationale 80, Literature Review 50 (mostly summarises), Methodology
40, Data Analysis 20, Conclusion 30, Organization 60, Grammar 40, Citations 40, giving a weighted
total of 44 and a fail. Well-written opening sections can score 80 even when the results are unsafe.

STEP 3 - EVIDENCE
- Copy every quote EXACTLY from the thesis text, on one line, at most 60 words. To join separate
  parts of one passage use " ... ". Never quote the guidelines. If you cannot find an exact quote
  for a point, leave the quote out instead of paraphrasing it.
- For each quote give "section": the heading or number it sits under (for example
  "Section 1.4 Key Research Question", "Table 18 Hypotheses testing", "Abstract").
- Never invent figures, tables, references or quotes. Report only what can be checked in the
  supplied text.
- You cannot check whether a cited work really exists, a Turnitin similarity score, or raw data
  files, and you must never claim you did.
- REFERENCES: your own knowledge ends before today's date (given in SUBMISSION FACTS), so recent
  publication years are never evidence of a problem. Never call a reference fabricated, fake or
  impossible, never accuse the student of misconduct, and never treat any year up to today's year
  as suspicious. You may flag only: (a) a reference dated later than a submission date that is
  printed in the thesis, stated as a factual inconsistency to check; (b) in-text citations missing
  from the reference list or the reverse; (c) incomplete reference entries. Always tell the
  student to verify such points against the sources.
- SUPPORTING FILES: when summaries of data or model files are supplied, cross-check them with
  the thesis (case counts, scale ranges, means) and report mismatches as findings or "checks".
  State them as facts from the files - they cannot be quoted - and claim no check beyond what
  the summaries show (for example, you cannot re-run the analysis).
- ACKNOWLEDGED ISSUES: before saying the thesis fails to state, explain or disclose something,
  search the thesis for it. If the thesis already says it (in a note, a limitations section or an
  interpretation paragraph), credit that and report only what is still wrong - for example a
  table label that still contradicts the text.
- UNFINISHED TEXT: if a thesis presented as final still contains notes addressed to the author,
  revision notes or placeholders (for example "the author should insert ..."), report that as an
  integrity finding and quote one such note.
- Use the word count and page count from SUBMISSION FACTS. Do not guess lengths. The word count
  covers the whole file (front matter, references, appendices and tables), so the body text is
  shorter: describe a word-limit breach as "about", ask the student to confirm the body-text
  count, and call it a fundamental breach only if even a 20% deduction still leaves it outside
  the limit.

OUTPUT
Respond with ONLY one JSON object (no prose outside it) of this shape:
{
  "student_name": "<name on the cover/declaration, or empty string>",
  "student_id": "<only if printed in the thesis, else empty string>",
  "module": "<module name/code only if printed in the thesis, else empty string>",
  "thesis_title": "<exact title>",
  "programme_level": "Doctoral" | "Master's" | "Bachelor's" | "",
  "rubric_name": "<name of the rubric / assessment brief, e.g. Doctorate Thesis Assessment Brief>",
  "criteria": [
    {
      "name": "<criterion name>",
      "weight": <percent>,
      "mark": <integer 0-100>,
      "why": "<2-3 sentences: why this mark>",
      "strength": "<1-2 sentences>",
      "quotes": [{"text": "<exact quote>", "section": "<where it sits>"}],
      "holds_down": "<2-3 sentences: what holds the mark down and the concrete fix>",
      "checks": ["<specific fact verified in the text, optional, at most 4>"]
    }
  ],
  "integrity_findings": [
    {"title": "<short title>", "severity": "critical" | "major" | "minor",
     "affects": [<criterion numbers>], "detail": "<2-3 sentences>",
     "quotes": [{"text": "<exact quote>", "section": "<where it sits>"}]}
  ],
  "fix_list": ["<concrete action, most important first>"]
}
Write plainly and directly to the student ("You state ..."). Use 0-2 quotes per criterion and 0-6
integrity findings (an empty list if there are none). "checks" must hold only specific facts with
numbers or locations that you verified in the text (for example "Table 13 means run from 4.43 to
5.75 although the text states a 1-5 scale"); never write yes/no checklist items, and use an empty
list when there is nothing specific. "fix_list" has 6-10 distinct actions, most important first,
each naming the chapter, section or table to change; never repeat an action. The output must be
valid, strict JSON: escape double quotes inside strings as \\" and never put a raw line break
inside a string.
"""

SYSTEM_PROMPT = _SYSTEM_TEMPLATE.replace("{{RUBRIC}}", tpl.rubric_text_for_prompt()).replace(
    "{{SCALE}}", tpl.scale_text_for_prompt()
)

USER_PROMPT_TEMPLATE = """ASSESSMENT GUIDELINES:
---
{guidelines}
---

SUBMISSION FACTS (computed by the system):
- Today's date: {today}
- Programme level: {level}
- Document type: {label}
- Word count (whole file, including front matter and references): about {words}
- Pages: {pages}

SUBMITTED THESIS:
---
{thesis}
---
{supporting_block}
Write the detailed feedback JSON described in your instructions."""

SUPPORTING_BLOCK = """
SUPPORTING FILES SUBMITTED WITH THE THESIS (summaries computed by the system):
---
{supporting}
---
"""

_EMPTY_VALUES = {"", "unknown", "n/a", "na", "none", "not stated", "not provided", "not specified"}


def evaluate_thesis(
    guidelines_text: str,
    thesis_text: str,
    student_name: str = "",
    student_id: str = "",
    module: str = "",
    supporting: str = "",
    supporting_names: tuple = (),
    level: str = "",
) -> dict:
    facts = _submission_facts(thesis_text)
    known_level = _level_word(level) or detect_level(thesis_text, guidelines_text)
    prompt = USER_PROMPT_TEMPLATE.format(
        guidelines=guidelines_text.strip(),
        today=tpl.format_date(),
        level=known_level or "not stated - judge it from the thesis cover page and the guidelines",
        label=facts["label"],
        words=f"{facts['words']:,}",
        pages=facts["pages"] if facts["pages"] else "not available (not a PDF)",
        thesis=thesis_text.strip(),
        supporting_block=SUPPORTING_BLOCK.format(supporting=supporting.strip()) if supporting.strip() else "",
    )
    raw = call_json(SYSTEM_PROMPT, prompt)
    result = _finalize(raw, thesis_text, facts, student_name, student_id, module, known_level)
    result["supporting_names"] = list(supporting_names)
    result["full_report_markdown"] = _build_report_markdown(result)
    return result


def _submission_facts(thesis_text: str) -> dict:
    clean = PAGE_MARKER.sub(" ", thesis_text)
    pages = len(PAGE_MARKER.findall(thesis_text))
    return {
        "label": "Thesis PDF" if pages else "Thesis document",
        "words": len(re.findall(r"\w+", clean)),
        "pages": pages or None,
    }


# ---------------------------------------------------------------- finalizing


def _finalize(
    raw: dict, thesis_text: str, facts: dict, student_name: str, student_id: str, module: str,
    known_level: str = "",
) -> dict:
    items = raw.get("criteria") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise RuntimeError(
            "The model did not return a marking rubric for this thesis. "
            "Please try again; if it keeps happening, check that the guidelines file is readable."
        )

    locator = _QuoteLocator(thesis_text)
    dropped = 0
    criteria = []
    for item in items:
        if not isinstance(item, dict) or not _s(item.get("name")):
            continue
        quotes, lost = _verify_quotes(item.get("quotes"), locator, facts, limit=2)
        dropped += lost
        criteria.append(
            {
                "name": _s(item.get("name")),
                "weight": max(_num(item.get("weight")), 0.0),
                "mark": max(0, min(100, int(round(_num(item.get("mark")))))),
                "why": _prose(item.get("why")),
                "strength": _prose(item.get("strength")),
                "quotes": quotes,
                "holds_down": _prose(item.get("holds_down")),
                "checks": [_prose(c) for c in _as_list(item.get("checks")) if _prose(c)][:5],
            }
        )
    if not criteria:
        raise RuntimeError("The model returned no usable criteria. Please try again.")

    weights_normalized = _normalize_weights(criteria)

    findings = []
    for finding in _as_list(raw.get("integrity_findings")):
        if not isinstance(finding, dict) or not _s(finding.get("title")):
            continue
        quotes, lost = _verify_quotes(finding.get("quotes"), locator, facts, limit=3)
        dropped += lost
        severity = _s(finding.get("severity")).lower()
        findings.append(
            {
                "title": _s(finding.get("title")),
                "severity": severity if severity in ("critical", "major", "minor") else "minor",
                "affects": _criterion_indexes(finding.get("affects"), criteria),
                "detail": _prose(finding.get("detail")),
                "quotes": quotes,
            }
        )
    caps = _apply_integrity_caps(criteria, findings)

    total = 0.0
    for criterion in criteria:
        criterion["contribution"] = round(criterion["mark"] * criterion["weight"] / 100, 1)
        total += criterion["contribution"]
    total = round(total, 1)
    overall = int(total + 0.5)

    level_word = known_level or _level_word(raw.get("programme_level"))
    band = tpl.band_for(overall)
    pass_mark = tpl.PASS_MARK
    scale_rows = [
        {
            "label": b["label"],
            "range": tpl.band_range_text(b),
            "meaning": tpl.band_meaning(b, level_word),
            "current": b is band,
        }
        for b in tpl.DEFAULT_SCALE
    ]

    result = {
        "student": {
            "name": _optional(student_name) or _optional(raw.get("student_name")),
            "id": _optional(student_id) or _optional(raw.get("student_id")),
            "module": _optional(module) or _optional(raw.get("module")),
            "title": _optional(raw.get("thesis_title")),
            "level_word": level_word,
        },
        "date": tpl.format_date(),
        "report_title": f"{level_word.upper()} THESIS DETAILED FEEDBACK" if level_word else "THESIS DETAILED FEEDBACK",
        "rubric_name": _optional(raw.get("rubric_name")) or "assessment brief",
        "source_label": facts["label"],
        "stats": {"words": facts["words"], "pages": facts["pages"]},
        "criteria": criteria,
        "weights_normalized": weights_normalized,
        "total": total,
        "overall_mark": overall,
        "classification": band["label"],
        "pass_mark": pass_mark,
        "passed": overall >= pass_mark,
        "integrity_findings": findings,
        "caps": caps,
        "fix_list": [_prose(x) for x in _as_list(raw.get("fix_list")) if _prose(x)][:14],
        "scale": scale_rows,
        "quotes_dropped": dropped,
    }
    # Names the rest of the app already uses.
    result["acceptance_percentage"] = overall
    result["qualified"] = band["label"]
    return result


_INTEGRITY_CAPS = {"critical": 40, "major": 60}

_DOCTORAL = re.compile(r"\b(?:doctor\s+of|doctorate|doctoral|ph\.?\s?d\b|d\.?b\.?a\b)", re.I)
_MASTERS = re.compile(r"\b(?:master\s+of|master[\'\u2019]?s|masters|m\.?sc\b|m\.?b\.?a\b|m\.?phil\b)", re.I)
_BACHELORS = re.compile(r"\b(?:bachelor|b\.?sc\b|b\.?b\.?a\b|undergraduate)", re.I)


def detect_level(thesis_text: str, guidelines_text: str = "") -> str:
    """Programme level from the thesis cover/declaration (first ~6000 characters),
    falling back to the guidelines' heading. The earliest mention wins."""
    sources = (PAGE_MARKER.sub(" ", thesis_text)[:6000], guidelines_text[:2500])
    for source in sources:
        hits = []
        for word, pattern in (("doctoral", _DOCTORAL), ("master's", _MASTERS), ("bachelor's", _BACHELORS)):
            match = pattern.search(source)
            if match:
                hits.append((match.start(), word))
        if hits:
            return min(hits)[1]
    return ""


def _criterion_indexes(affects, criteria: list[dict]) -> list[int]:
    """Zero-based criterion indexes from the model's numbers (or names)."""
    indexes = set()
    for entry in _as_list(affects):
        if isinstance(entry, (int, float)) or re.fullmatch(r"\s*\d+\s*", str(entry)):
            number = int(_num(entry))
            if 1 <= number <= len(criteria):
                indexes.add(number - 1)
        else:
            needle = _s(entry).lower()
            for i, criterion in enumerate(criteria):
                name = criterion["name"].lower()
                if needle and (needle in name or name in needle):
                    indexes.add(i)
    return sorted(indexes)


def _apply_integrity_caps(criteria: list[dict], findings: list[dict]) -> list[dict]:
    """Integrity comes first: a critical finding limits the criteria it damages to
    40%, a major one to 60%. Returns what was capped, for the report."""
    caps = []
    for number, finding in enumerate(findings, 1):
        limit = _INTEGRITY_CAPS.get(finding["severity"])
        if limit is None:
            continue
        for index in finding["affects"]:
            criterion = criteria[index]
            if criterion["mark"] > limit:
                caps.append(
                    {
                        "criterion": index + 1,
                        "name": criterion["name"],
                        "from_mark": criterion["mark"],
                        "to_mark": limit,
                        "finding": f"2.{number}",
                        "severity": finding["severity"],
                    }
                )
                criterion["mark"] = limit
    return caps


def _normalize_weights(criteria: list[dict]) -> bool:
    total = sum(c["weight"] for c in criteria)
    if total <= 0:
        for c in criteria:
            c["weight"] = round(100 / len(criteria), 1)
        return True
    if abs(total - 100) > 0.5:
        for c in criteria:
            c["weight"] = round(c["weight"] * 100 / total, 1)
        return True
    return False


def _s(value) -> str:
    return " ".join(str(value).split()) if isinstance(value, (str, int, float)) else ""


_RANGE = r"\d+(?:\s*(?:[-–—]|to|and|,)\s*\d+)*"
_PAGE_PARENTHETICAL = re.compile(rf"\s*\((?:see |at |on )?(?:pages?|pp?\.)\s*{_RANGE}\)", re.I)
_PAGE_SUBJECT = re.compile(
    rf"\bpages?\s+{_RANGE}\s+(?=(?:states|says|notes|shows|reports|describes|confirms|acknowledges)\b)", re.I
)
_PAGE_PREPOSITION = re.compile(rf"\s+(?:on|in|at|from|see)\s+pages?\s+{_RANGE}", re.I)


def _prose(value) -> str:
    """Free text from the model, with any page numbers it wrote removed.

    The model is told not to state pages, and in practice it sometimes gets them
    wrong. Only the page on a verified quote's source line can be trusted.
    """
    text = _s(value)
    text = _PAGE_PARENTHETICAL.sub("", text)
    text = _PAGE_SUBJECT.sub("The thesis ", text)
    text = _PAGE_PREPOSITION.sub("", text)
    return _s(text)


def _optional(value) -> str:
    text = _s(value)
    return "" if text.lower() in _EMPTY_VALUES else text


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _num(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else 0.0


def _level_word(value) -> str:
    text = _s(value).lower()
    if "doctor" in text:
        return "doctoral"
    if "master" in text:
        return "master's"
    if "bachelor" in text or "undergrad" in text:
        return "bachelor's"
    return ""


# ------------------------------------------------------------- quote checking


def _alnum(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower())


class _QuoteLocator:
    """Finds a quote in the thesis ignoring spacing, punctuation and line wraps,
    and reports the PDF page it starts on."""

    _SPLIT = re.compile(r"\s*(?:\[\s*\.\.\.\s*\]|\.\.\.|…)\s*")
    _MIN_FRAGMENT = 12

    def __init__(self, text: str):
        pieces = PAGE_MARKER.split(text)
        chunks = [(None, pieces[0])] + [
            (int(pieces[i]), pieces[i + 1]) for i in range(1, len(pieces) - 1, 2)
        ]
        parts, self._starts, self._pages = [], [], []
        offset = 0
        for page, chunk in chunks:
            normalized = _alnum(chunk)
            if not normalized:
                continue
            self._starts.append(offset)
            self._pages.append(page)
            parts.append(normalized)
            offset += len(normalized)
        self._norm = "".join(parts)

    def locate(self, quote: str):
        fragments = [_alnum(f) for f in self._SPLIT.split(quote)]
        fragments = [f for f in fragments if len(f) >= self._MIN_FRAGMENT]
        if not fragments:
            return False, None
        first = None
        for fragment in fragments:
            position = self._norm.find(fragment)
            if position < 0:
                return False, None
            if first is None:
                first = position
        index = bisect_right(self._starts, first) - 1
        return True, self._pages[index] if index >= 0 else None


def _verify_quotes(quotes, locator: _QuoteLocator, facts: dict, limit: int):
    verified, dropped = [], 0
    for quote in _as_list(quotes):
        if isinstance(quote, str):
            quote = {"text": quote, "section": ""}
        if not isinstance(quote, dict):
            continue
        text = _s(quote.get("text"))
        found, page = locator.locate(text) if text else (False, None)
        if not found:
            dropped += 1
            continue
        verified.append({"text": text, "source": _source_label(facts["label"], page, _s(quote.get("section")))})
    return verified[:limit], dropped


def _source_label(label: str, page, section: str) -> str:
    parts = [label]
    if page:
        parts.append(f"page {page}")
    if section:
        parts.append(section)
    return ", ".join(parts)


# ------------------------------------------------------------ on-screen report


def _build_report_markdown(result: dict) -> str:
    student = result["student"]
    level_word = student["level_word"]
    heading_prefix = f"{level_word[0].upper() + level_word[1:]} " if level_word else ""
    lines = [
        f"# {heading_prefix}Thesis Detailed Feedback",
        "",
        f"**Student:** {student['name'] or 'Not stated'}  ",
        f"**Thesis title:** {student['title'] or 'Not stated'}  ",
        f"**Date of feedback:** {result['date']}  ",
        f"**Overall mark:** {result['overall_mark']}% | {result['classification']}",
        "",
        "## 1. Summary of Marks",
        "",
        "| No. | Criterion | Weight | Mark | Contribution |",
        "|---|---|---|---|---|",
    ]
    for i, c in enumerate(result["criteria"], 1):
        lines.append(f"| {i} | {c['name']} | {c['weight']:g}% | {c['mark']}% | {c['contribution']:.1f} |")
    lines.append(f"| | **Weighted total** | 100% | **{result['overall_mark']}%** | **{result['total']:.1f}** |")
    lines += [
        "",
        f"**Classification: {result['classification']}**",
        "",
        "*Contribution = Mark x Weight / 100.*",
    ]
    if result["weights_normalized"]:
        lines.append("*The stated weights did not add up to 100 and were scaled proportionally.*")
    for cap in result["caps"]:
        lines += ["", f"*Integrity limit: Criterion {cap['criterion']} ({cap['name']}) was limited from "
                      f"{cap['from_mark']}% to {cap['to_mark']}% because of {cap['severity']} finding {cap['finding']}.*"]

    lines += ["", "## 2. Integrity Findings"]
    if result["integrity_findings"]:
        for i, finding in enumerate(result["integrity_findings"], 1):
            tag = f" ({finding['severity']})" if finding["severity"] != "minor" else ""
            lines += ["", f"### 2.{i} {finding['title']}{tag}", finding["detail"]]
            lines += _quote_lines(finding["quotes"])
    else:
        lines += ["", "No integrity problems were found in the submitted text."]

    lines += ["", "## 3. Criterion-by-Criterion Feedback"]
    for i, c in enumerate(result["criteria"], 1):
        lines += ["", f"### Criterion {i}. {c['name']} - {c['mark']}% (Weight {c['weight']:g}%)"]
        if c["why"]:
            lines += [f"**Why {c['mark']}%.** {c['why']}", ""]
        if c["strength"]:
            lines += [f"**Strength.** {c['strength']}", ""]
        lines += _quote_lines(c["quotes"])
        if c["checks"]:
            lines += [f"- {check}" for check in c["checks"]] + [""]
        if c["holds_down"]:
            lines += [f"**What holds the mark down.** {c['holds_down']}"]

    heading = "What to Fix to Reach a Pass" if not result["passed"] else "Recommended Improvements"
    lines += ["", f"## 4. {heading}"]
    lines += [f"{i}. {item}" for i, item in enumerate(result["fix_list"], 1)]

    lines += ["", "## 5. Grading Scale", "", "| Classification | Mark range | Meaning |", "|---|---|---|"]
    for row in result["scale"]:
        name = f"**{row['label']}**" if row["current"] else row["label"]
        lines.append(f"| {name} | {row['range']} | {row['meaning']} |")
    lines += ["", f"**Your current band: {result['overall_mark']}%.**"]
    return "\n".join(lines)


def _quote_lines(quotes: list[dict]) -> list[str]:
    out = []
    for quote in quotes:
        out += [f"> *\"{quote['text']}\"*", ">", f"> Source: {quote['source']}", ""]
    return out
