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
from concurrent.futures import ThreadPoolExecutor

from src import report_template as tpl
from src.llm_client import call_json
from src.universities import get_university
from src.reference_check import check_references

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
If the rubric has levels (for example 5 = excellent, 3-4 = good, 1-2 = developing, 0 = not met),
give "level" for each criterion: a number from 0 to 5 in steps of 0.5, chosen by reading the level
descriptors literally against the evidence. In "why" name the descriptor words that decide the
level. The system turns the level into a mark (level x 20), so do not also give a percentage. If
the rubric has no levels, give "mark" as a whole number from 0 to 100 instead. Marks follow this
European scale, where 60 is already a very good mark and 90+ is rare:
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

MARKING ANCHORS (read the rubric descriptors literally; length and effort do not raise a level):
- Literature Review: level 4 or more needs sources that are "compared and questioned, not only
  summed up". A chapter that mostly describes one source after another, however long and however
  many sources it lists, is level 2.5 to 3. Say which descriptor words you applied.
- Organization: level 4 needs a "strong and well controlled" structure. When the same results,
  definitions or interpretations are restated in full in more than one chapter, the flow is heavy:
  level 3. SYSTEM-DETECTED SIGNALS may list restated passages - check them.
- Grammar and Punctuation: level 4 means "a few" errors. Numbers in the prose that contradict
  each other or the tables (counts and percentages that do not agree, a stated majority that the
  figures do not show), mixed British and American spelling and repeated wording slips count as
  errors; several of them mean level 2 to 2.5.
- Do not raise a criterion because the topic is interesting or the thesis is long.

INTEGRITY FIRST: doctoral integrity comes before everything else. Made-up or simulated data, notes
to the author left in the text, a method written in the future tense in a finished thesis, and
references that cannot be checked are integrity failures. Go through this checklist and report
only what you actually find:
1. Names: the candidate's name on the cover, declaration and certificate must match.
2. Tense: the method chapter must report what was done. Wording such as "will be collected" or
   "will consist of" in a finished thesis is a failure - quote two examples.
3. Scale: values, means or ranges outside the stated scale (for example means above 5 on a 1-5
   scale, or a data file whose range differs from the instrument described).
4. Copied rows: result tables where different hypotheses or paths share identical statistics.
5. Prose against tables: counts, percentages or effect sizes in the text that contradict a table.
6. Data support: demographic or result tables that no supplied data file can support.
7. Notes to the author or revision notes left in the text.
8. References: in-text citations missing from the reference list or the reverse, and incomplete
   entries.
Label each finding "critical", "major" or "minor":
- critical = items 1, 2, 3, 4 and 7, and any made-up or simulated data.
- major = items 5, 6 and 8, other contradictions between text and tables, and missing ethics
  documentation for human participants.
- minor = everything else.
Critical findings are integrity failures: the system limits Criteria 6 and 7 (Data Analysis and
Conclusion) and every criterion you list in "affects" to 40, and a thesis with an integrity failure
cannot pass whatever its total. Major findings limit the criteria in "affects" to 60. In "affects"
list the numbers of the criteria a finding damages (for example Methodology, Data Analysis,
Conclusion, Citations). Mark every other criterion on its own merits.

{{CALIBRATION}}

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
  as suspicious. You may flag only: (a) a reference dated later than the submission date printed on
  the cover (see SUBMISSION FACTS; if none is printed, never raise this), stated as a factual
  inconsistency to check; (b) in-text citations missing
  from the reference list or the reverse; (c) incomplete reference entries. Always tell the
  student to verify such points against the sources.
- NO ACCUSATIONS: never write fabricated, fabrication, falsified, forged or made-up about the
  student's data, results or references, and never speculate about intent. Describe the symptom
  (copied rows, impossible values) and say the results cannot be trusted until they are checked
  against the original output.
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
- Use the word count and page count from SUBMISSION FACTS. Do not guess lengths. If the guidelines
  say the total word count of the thesis is used, compare the figure directly with the stated
  minimum or range. Otherwise the figure covers the whole file (front matter, references, appendices,
  tables), so the body text is shorter: say "about" and ask the student to confirm the body-text
  count.
- SYSTEM-DETECTED SIGNALS: when the message lists signals found by pattern search (future-tense
  method wording, notes to the author), look at each in context before reporting it, and quote it.

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
      "level": <0-5 in steps of 0.5, when the rubric has levels>,
      "mark": <integer 0-100, only when the rubric has no levels>,
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

def build_system_prompt(profile) -> str:
    """The examiner instructions with the university's rubric, scale and calibration example."""
    template = _SYSTEM_TEMPLATE
    if not profile.strict_integrity:
        start = template.index("Critical findings are integrity failures:")
        end = template.index("Mark every other criterion on its own merits.") + len(
            "Mark every other criterion on its own merits."
        )
        template = template[:start] + profile.lenient_integrity_text + template[end:]
    return (
        template.replace("{{RUBRIC}}", profile.rubric_text())
        .replace("{{SCALE}}", profile.scale_text())
        .replace("{{CALIBRATION}}", profile.calibration.strip())
    )


SYSTEM_PROMPT = build_system_prompt(get_university(None))  # default (EIU) prompt

USER_PROMPT_TEMPLATE = """ASSESSMENT GUIDELINES:
---
{guidelines}
---

SUBMISSION FACTS (computed by the system):
- Today's date: {today}
- Programme level: {level}
- Submission date printed on the cover: {printed_date}
- Document type: {label}
- Word count (whole file, including front matter and references): about {words}
- Pages: {pages}

SUBMITTED THESIS:
---
{thesis}
---
{supporting_block}{signals_block}
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
    check_refs: bool = False,
    university: str = "eiu",
) -> dict:
    profile = get_university(university)
    facts = _submission_facts(thesis_text)
    # The online reference lookup is slow (about 1-2 minutes) and independent of the
    # model, so it runs alongside the model call.
    ref_pool = ThreadPoolExecutor(max_workers=1)
    ref_future = ref_pool.submit(check_references, thesis_text) if check_refs else None
    known_level = _level_word(level) or detect_level(thesis_text, guidelines_text)
    prompt = USER_PROMPT_TEMPLATE.format(
        guidelines=guidelines_text.strip(),
        today=tpl.format_date(),
        printed_date=_printed_date(thesis_text) or "none printed",
        level=known_level or "not stated - judge it from the thesis cover page and the guidelines",
        label=facts["label"],
        words=f"{facts['words']:,}",
        pages=facts["pages"] if facts["pages"] else "not available (not a PDF)",
        thesis=thesis_text.strip(),
        supporting_block=SUPPORTING_BLOCK.format(supporting=supporting.strip()) if supporting.strip() else "",
        signals_block=_signals_block(thesis_text),
    )
    try:
        raw = call_json(build_system_prompt(profile), prompt)
    finally:
        ref_pool.shutdown(wait=False)
    ref_check = None
    if ref_future is not None:
        try:
            ref_check = ref_future.result(timeout=300)
        except Exception:  # noqa: BLE001 - the lookup is a bonus; never fail the report over it
            ref_check = {"available": False, "reason": "the lookup did not finish"}
    result = _finalize(raw, thesis_text, facts, student_name, student_id, module, known_level, ref_check, profile)
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
    ref_check: dict | None = None,
    profile=None,
) -> dict:
    profile = profile or get_university(None)
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
                "mark": _mark_from(item),
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
    printed_year = _printed_year(thesis_text)
    kept = [f for f in findings if not _unsupported_reference_date_claim(f, printed_year)]
    findings_dropped = len(findings) - len(kept)
    findings = kept
    caps = []
    if profile.strict_integrity:
        caps = _apply_integrity_caps(criteria, findings)
        caps += _apply_reference_check(criteria, findings, ref_check)

    total = 0.0
    for criterion in criteria:
        criterion["contribution"] = round(criterion["mark"] * criterion["weight"] / 100, 1)
        total += criterion["contribution"]
    total = round(total, 1)
    overall = int(total + 0.5)

    integrity_failure = profile.strict_integrity and any(f["severity"] == "critical" for f in findings)
    level_word = known_level or _level_word(raw.get("programme_level"))
    band = profile.band_for(overall)
    pass_mark = profile.pass_mark
    scale_rows = [
        {
            "label": b["label"],
            "range": tpl.band_range_text(b),
            "meaning": tpl.band_meaning(b, level_word),
            "current": b is band,
        }
        for b in profile.scale
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
        "university": profile.key,
        "classification": band["label"],
        "pass_mark": pass_mark,
        "passed": overall >= pass_mark and not integrity_failure,
        "integrity_failure": integrity_failure,
        "outcome_note": (
            "Integrity failure: under the assessment brief this thesis cannot pass whatever its total. "
            "Expect major revisions or a fail until the critical findings are resolved."
            if integrity_failure else ""
        ),
        "integrity_findings": findings,
        "caps": caps,
        "findings_dropped": findings_dropped,
        "reference_check": {k: v for k, v in (ref_check or {}).items() if k != "unconfirmed"} or None,
        "fix_list": [_prose(x) for x in _as_list(raw.get("fix_list")) if _prose(x)][:14],
        "scale": scale_rows,
        "quotes_dropped": dropped,
    }
    # Names the rest of the app already uses.
    result["acceptance_percentage"] = overall
    result["qualified"] = band["label"]
    return result


_INTEGRITY_CAPS = {"critical": 40, "major": 60}
_CRITICAL_ALWAYS_HITS = ("data analysis", "conclusion")
# When a critical finding damages the results themselves (scale breach, copied
# statistics), the results sit at fail level (level 1) and the conclusion at 1.5.
_RESULTS_UNSAFE_FLOORS = {"data analysis": 20, "conclusion": 30}
# Integrity can only limit these. A model that says a name mismatch "affects" the
# abstract would otherwise drag down criteria the university did not touch.
_CAPPABLE = ("method", "data analysis", "conclusion", "citation", "reference")

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
        affected = {i for i in finding["affects"] if any(k in criteria[i]["name"].lower() for k in _CAPPABLE)}
        results_unsafe = finding["severity"] == "critical" and any(
            "data analysis" in criteria[i]["name"].lower() for i in affected
        )
        if finding["severity"] == "critical":
            # The brief: integrity failures keep Data Analysis and Conclusion low.
            affected |= {
                i for i, c in enumerate(criteria) if any(k in c["name"].lower() for k in _CRITICAL_ALWAYS_HITS)
            }
        for index in sorted(affected):
            criterion = criteria[index]
            cap = limit
            if results_unsafe:
                # Unsafe results: the university holds the results at fail level and the
                # conclusion, which rests on them, just above it.
                for key, floor in _RESULTS_UNSAFE_FLOORS.items():
                    if key in criterion["name"].lower():
                        cap = min(cap, floor)
            _cap_mark(caps, criterion, index, cap, f"2.{number}", finding["severity"])
    return caps


_REF_FINDING_SHARE = 0.15  # share of journal references Crossref could not confirm -> major finding
_REF_CAP_SHARE = 0.25  # ... and above this the Citations (40) and Literature (50) marks are limited
_REF_CAPS = {"citation": 40, "reference": 40, "literature": 50}


def _apply_reference_check(criteria: list[dict], findings: list[dict], ref_check: dict | None) -> list[dict]:
    """Turn the online reference lookup into a finding and, when many journal
    references cannot be confirmed, limits on Citations and Literature. The wording
    stays factual: Crossref misses some real works, so the student must verify."""
    caps: list[dict] = []
    if not ref_check or not ref_check.get("available") or ref_check.get("articles", 0) < 10:
        return caps
    share = ref_check["unconfirmed_share"]
    if share < _REF_FINDING_SHARE:
        return caps
    unconfirmed = ref_check["unconfirmed"]
    examples = "; ".join(f'"{" ".join(e.split())[:170]}"' for e in unconfirmed[:6])
    affects = [i for i, c in enumerate(criteria) if any(k in c["name"].lower() for k in _REF_CAPS)]
    findings.append(
        {
            "title": "Journal references that could not be confirmed",
            "severity": "major",
            "affects": affects,
            "detail": (
                f"{len(unconfirmed)} of {ref_check['articles']} journal-article references ({share:.0%}) could not be "
                "matched to a published work in the Crossref scholarly index when checked automatically. Crossref "
                "does not hold every real work, so this is not proof that an entry is wrong, but each one must be "
                "checked against the original source and replaced if it cannot be opened. Examples: " + examples
            ),
            "quotes": [],
        }
    )
    label = f"2.{len(findings)}"
    if share >= _REF_CAP_SHARE:
        for index in affects:
            name = criteria[index]["name"].lower()
            cap = min(v for k, v in _REF_CAPS.items() if k in name)
            _cap_mark(caps, criteria[index], index, cap, label, "major")
    return caps


def _cap_mark(caps: list, criterion: dict, index: int, cap: int, finding_label: str, severity: str) -> None:
    if criterion["mark"] > cap:
        caps.append(
            {
                "criterion": index + 1,
                "name": criterion["name"],
                "from_mark": criterion["mark"],
                "to_mark": cap,
                "finding": finding_label,
                "severity": severity,
            }
        )
        criterion["mark"] = cap


_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_COVER_DATE = re.compile(rf"\b(?:date|submitted|submission)\b[^A-Za-z0-9]{{0,8}}((?:(?:{_MONTHS})\s+)?(?:19|20)\d\d)", re.I)


def _printed_date(thesis_text: str) -> str:
    """Submission date printed on the cover, e.g. 'April 2026' ('' if none)."""
    head = " ".join(PAGE_MARKER.sub(" ", thesis_text)[:4000].split())
    match = _COVER_DATE.search(head)
    return match.group(1) if match else ""


def _printed_year(thesis_text: str):
    match = re.search(r"(?:19|20)\d\d", _printed_date(thesis_text))
    return int(match.group()) if match else None


_REF_WORDS = re.compile(r"referenc|citation|cited", re.I)
_AFTER_DATE = re.compile(r"(?:dated|published|publication)[^.]{0,80}(?:after|later|beyond)|after (?:the )?(?:thesis )?submission", re.I)


def _unsupported_reference_date_claim(finding: dict, printed_year) -> bool:
    """'References dated after the submission date' is only checkable against a
    date printed in the thesis; without one (or when the years are not later) the
    claim is dropped."""
    text = f"{finding['title']} {finding['detail']}"
    if not (_REF_WORDS.search(text) and _AFTER_DATE.search(text)):
        return False
    years = [int(y) for y in re.findall(r"\b(?:19|20)\d\d\b", text)]
    return not (printed_year and any(y > printed_year for y in years))


def _mark_from(item: dict) -> int:
    """Rubric level (0-5, x20) when the model gave one, else a 0-100 mark."""
    level = item.get("level")
    if isinstance(level, (int, float)) or (isinstance(level, str) and re.search(r"\d", level)):
        value = _num(level)
        if 0 <= value <= 5:
            return int(round(value * 20))
        if 5 < value <= 100:  # a percentage slipped into the level field
            return int(round(value))
    return max(0, min(100, int(round(_num(item.get("mark"))))))


_FUTURE_METHOD = re.compile(
    r"[^.\n]{0,110}\b(?:will be (?:collected|distributed|administered|rated|analy[sz]ed|conducted|sent|invited"
    r"|selected|recruited|measured|issued)|will (?:collect|distribute|administer|analy[sz]e|conduct|consist"
    r"|recruit|measure|issue))\b[^.\n]{0,110}",
    re.I,
)
_COACHING = re.compile(
    r"[^.\n]{0,110}\b(?:the author should|before final submission|highlighted in yellow|revision note"
    r"|coaching note|should be replaced or qualified|insert verified|to be inserted)\b[^.\n]{0,110}",
    re.I,
)


def scan_integrity_signals(thesis_text: str) -> str:
    """Pattern search for two integrity failures the brief names: a method written
    in the future tense, and notes to the author left in the text. Deterministic,
    so it does not depend on the model noticing them."""
    pieces = PAGE_MARKER.split(thesis_text)
    chunks = [(None, pieces[0])] + [(int(pieces[i]), pieces[i + 1]) for i in range(1, len(pieces) - 1, 2)]
    hits = {"future": [], "coaching": []}
    for page, chunk in chunks:
        flat = " ".join(chunk.split())
        for key, pattern in (("future", _FUTURE_METHOD), ("coaching", _COACHING)):
            hits[key] += [(page, m.group(0).strip()) for m in pattern.finditer(flat)]
    labels = {
        "future": "future-tense method wording (will be collected / will consist of ...)",
        "coaching": "notes to the author or revision notes",
    }
    lines = []
    for key in ("future", "coaching"):
        found = hits[key]
        if not found:
            continue
        pages = sorted({p for p, _ in found if p})
        where = f" on pages {pages[:12]}" if pages else ""
        examples = "; ".join((f"page {p}: " if p else "") + f'"{text[:200]}"' for p, text in found[:3])
        lines.append(f"- {labels[key]}: {len(found)} match(es){where}. Examples - {examples}")
    return "\n".join(lines)


def scan_repetition(thesis_text: str, min_sentences: int = 6) -> str:
    """Sentences that largely restate an earlier sentence on a different page
    (4-word-run overlap of at least 50%). Information for the Organization mark,
    not a penalty by itself: a summary chapter legitimately restates some results."""
    body = thesis_text[: thesis_text.rfind("\nReferences\n")] if "\nReferences\n" in thesis_text else thesis_text
    pieces = PAGE_MARKER.split(body)
    chunks = [(0, pieces[0])] + [(int(pieces[i]), pieces[i + 1]) for i in range(1, len(pieces) - 1, 2)]
    sentences = []
    front_matter = 12 if len(chunks) > 40 else 0  # cover, certificate, abstract and lists repeat by design
    for page, chunk in chunks:
        if page <= front_matter:
            continue
        flat = " ".join(chunk.split())
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", flat):
            words = re.findall(r"[a-z0-9]+", sentence.lower())
            if len(words) >= 14:
                sentences.append((page, words, sentence))
    runs = [{tuple(w[i : i + 4]) for i in range(len(w) - 3)} for _, w, _ in sentences]
    index: dict = {}
    pairs = []
    for i, grams in enumerate(runs):
        shared: dict = {}
        for gram in grams:
            for j in index.get(gram, ()):
                shared[j] = shared.get(j, 0) + 1
        for j, count in shared.items():
            if count / min(len(grams), len(runs[j])) >= 0.5 and sentences[i][0] != sentences[j][0]:
                pairs.append((j, i))
        for gram in grams:
            index.setdefault(gram, []).append(i)
    restated = {i for _, i in pairs}
    if len(restated) < min_sentences:
        return ""
    farthest = sorted(pairs, key=lambda ji: sentences[ji[1]][0] - sentences[ji[0]][0], reverse=True)
    examples = "; ".join(
        f'page {sentences[i][0]} repeats page {sentences[j][0]}: "{sentences[i][2][:110]}"' for j, i in farthest[:3]
    )
    return f"- passages restated on a different page: {len(restated)} sentence(s). Examples - {examples}"


def _signals_block(thesis_text: str) -> str:
    signals = scan_integrity_signals(thesis_text)
    repetition = scan_repetition(thesis_text)
    if repetition:
        signals = f"{signals}\n{repetition}" if signals else repetition
    if not signals:
        return ""
    return f"\nSYSTEM-DETECTED SIGNALS (pattern search; check each in context):\n---\n{signals}\n---\n"


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
        f"**Overall mark:** {result['overall_mark']}% | {result['classification']}"
        + (" | integrity failure" if result.get("integrity_failure") else ""),
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
        *([f"**{result['outcome_note']}**", ""] if result.get("outcome_note") else []),
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
