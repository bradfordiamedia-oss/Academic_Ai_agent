"""Check a thesis reference list against Crossref (free, no key).

The university's marking sheet treats "references that cannot be checked" as an
integrity matter. This module finds the reference list, splits it into entries
and looks each one up in Crossref. An entry counts as *matched* when the best
Crossref hit has (almost) the same title and the same first author.

Important limits, so the result is worded carefully everywhere it is used:
* Crossref does not hold every real source (many books, reports, theses, web
  pages and conference items are missing), so "not matched" means "could not be
  confirmed automatically", never "fake".
* If the lookup fails (no network, Crossref down) the check reports itself as
  unavailable and nothing is concluded.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

CROSSREF = "https://api.crossref.org/works"
_YEAR = re.compile(r"\((\d{4})[a-z]?(?:,[^)]*)?\)")
_ENTRY_START = re.compile(r"^[A-Z][^\s,]*(?:[ \-][A-Za-z'’\-]+){0,3},\s(?:[A-Z]\.[ \-]?)+")
_PAGE_MARK = re.compile(r"^\[\[Page \d+\]\]\s*$")
_STOP = {"the", "of", "and", "in", "on", "for", "a", "an", "to", "with", "by", "from", "at", "as", "is", "are"}


def find_reference_section(text: str) -> str:
    """Text after the last 'References' heading, up to an Appendix heading."""
    heads = list(re.finditer(r"(?im)^\s*(?:chapter\s+\w+\s*[:.\-]?\s*)?(?:references|bibliography)\s*$", text))
    if not heads:
        return ""
    section = text[heads[-1].end():]
    end = re.search(r"(?im)^\s*appendi(?:x|ces)\b.*$", section)
    return section[: end.start()] if end else section


def split_entries(section: str) -> list[str]:
    """Split an APA reference list into one string per entry."""
    entries: list[str] = []
    current = ""
    for raw in section.splitlines():
        line = raw.strip()
        if not line or _PAGE_MARK.match(line):
            continue
        if _ENTRY_START.match(line) and (not current or _YEAR.search(current) and current.rstrip().endswith((".", ")", "*"))
                                         or re.search(r"\d\.$", current)):
            if current:
                entries.append(current.strip())
            current = line
        else:
            current = f"{current} {line}".strip()
    if current:
        entries.append(current.strip())
    return [e for e in entries if _YEAR.search(e)]


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1]


def _first_surname(entry: str) -> str:
    return re.split(r",", entry, 1)[0].strip().lower()


def _lookup(entry: str, session: requests.Session) -> dict:
    year = int(_YEAR.search(entry).group(1))
    result = {"entry": entry, "year": year, "status": "unmatched", "doi": None}
    items = None
    for attempt in range(4):
        try:
            r = session.get(
                CROSSREF,
                params={"query.bibliographic": entry[:300], "rows": 3, "select": "DOI,title,issued,author"},
                timeout=20,
            )
            if r.status_code == 429:  # public pool: one request at a time, back off and retry
                time.sleep(float(r.headers.get("Retry-After", 2)) + attempt)
                continue
            if r.status_code != 200:
                break
            items = r.json()["message"]["items"]
            break
        except Exception:  # noqa: BLE001 - network problems must not break the report
            time.sleep(1)
    if items is None:
        result["status"] = "error"
        return result

    entry_tokens = set(_tokens(entry))
    surname = _first_surname(entry)
    for item in items:
        title = " ".join(item.get("title") or [])
        t_tokens = _tokens(title)
        if len(t_tokens) < 3:
            continue
        overlap = sum(1 for w in t_tokens if w in entry_tokens) / len(t_tokens)
        authors = " ".join(a.get("family", "") for a in item.get("author", [])).lower()
        first_family = (item.get("author") or [{}])[0].get("family", "").lower()
        author_ok = bool(first_family) and (first_family in surname or surname in first_family or surname in authors)
        issued = (item.get("issued", {}).get("date-parts") or [[None]])[0][0]
        year_ok = issued is None or abs(issued - year) <= 1
        if overlap >= 0.8 and author_ok and year_ok:
            result.update(status="matched", doi=item.get("DOI"))
            return result
    return result


_NOT_ARTICLE = re.compile(
    r"\(\s*(?:\d+(?:st|nd|rd|th)\s+)?eds?\.?\s*\)|\bdoctoral dissertation\b|\bmaster'?s thesis\b|\bavailable at\b|"
    r"\bretrieved from\b|\bhttps?://(?!doi\.org)|\bproceedings\b|\bconference\b|\bworking paper\b|\bpress\b\.?$|"
    r"\b(?:publications?|publishers?|sage|wiley|pearson|mcgraw-hill|routledge|springer|oxford university press|"
    r"cambridge university press|harvard business (?:school )?press|igi global|gmbh)\b\.?$",
    re.I,
)
_VOLUME = re.compile(r"\*?\b\d{1,3}\*?\s*\(\d{1,3}\)|,\s*\*\d+\*")


def is_journal_article(entry: str) -> bool:
    """Journal-style entry: has volume/issue and is not obviously a book, thesis,
    conference paper or web page. Crossref covers articles well and the rest badly."""
    return bool(_VOLUME.search(entry)) and not _NOT_ARTICLE.search(entry.strip())


def check_references(thesis_text: str, max_entries: int = 250) -> dict:
    """Look up the journal-article references in Crossref.

    {"available": bool, "articles": n, "matched": n, "unconfirmed": [entry,...],
     "unconfirmed_share": 0-1, "entries": n_total}
    """
    entries = split_entries(find_reference_section(thesis_text))[:max_entries]
    if len(entries) < 5:
        return {"available": False, "reason": "no reference list found", "entries": len(entries)}
    articles = [e for e in dict.fromkeys(entries) if is_journal_article(e)]
    if len(articles) < 5:
        return {"available": False, "reason": "too few journal references to check", "entries": len(entries)}
    session = requests.Session()
    session.headers["User-Agent"] = "BradfordAcademicAgent/1.0 (reference format check)"

    def run(entry: str) -> dict:
        result = _lookup(entry, session)
        time.sleep(0.2)
        return result

    # Two at a time: Crossref's public pool rate-limits harder than that.
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, articles))
    checked = [r for r in results if r["status"] != "error"]
    if len(checked) < len(results) * 0.7:
        return {"available": False, "reason": "Crossref could not be reached", "entries": len(entries)}
    matched = [r for r in checked if r["status"] == "matched"]
    unconfirmed = [r["entry"] for r in checked if r["status"] == "unmatched"]
    return {
        "available": True,
        "entries": len(entries),
        "articles": len(checked),
        "matched": len(matched),
        "unconfirmed": unconfirmed,
        "unconfirmed_share": len(unconfirmed) / len(checked),
    }
