"""University profiles: everything that differs from one university to the next.

A profile holds the default marking rubric, pass mark and grading scale, the
letterhead images, the wording of the closing note and an optional calibration
example for the model. The evaluator and the PDF builder read only from the
profile they are given, so adding a university means adding ONE file here (copy
`eiu.py`) and listing it below. See ADDING_A_UNIVERSITY.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


@dataclass(frozen=True)
class University:
    key: str  # short id used in code and file names, e.g. "eiu"
    name: str  # name shown in the app's dropdown
    short: str  # used in headings, e.g. "5. EIU-Paris Grading Scale (ECTS)"
    issued_by: str  # who the feedback is prepared for (closing note)
    header_image: Path  # full-width page header
    footer_image: Path  # full-width page footer
    rubric: tuple  # ((criterion, weight %), ...) used when the guidelines have no readable rubric
    scale: tuple  # grading bands, best first: {"label","min","max","meaning"}
    pass_mark: int = 50
    scale_name: str = "ECTS"  # shown in "5. <short> Grading Scale (<scale_name>)"
    calibration: str = ""  # optional worked example of this university's marking (model prompt)
    # EIU treats integrity failures (future-tense method, inconsistent data, copied rows...) as a
    # fail whatever the total. Turn off for universities whose rules do not say so.
    strict_integrity: bool = True
    # Printed under the grading scale. Use it when the scale or rubric is provisional.
    scale_note: str = ""
    # Used in place of the integrity paragraph of the prompt when strict_integrity is False.
    lenient_integrity_text: str = (
        "Integrity findings are reported with their severity and explained, but the system does not change "
        "any mark for them and they do not decide pass or fail. Mark every criterion on its own evidence. "
        'In "affects" list the numbers of the criteria a finding damages.'
    )

    # -- helpers used by the evaluator and the PDF builder ------------------
    def rubric_text(self) -> str:
        return "\n".join(f"{i}. {name} ({weight}%)" for i, (name, weight) in enumerate(self.rubric, 1))

    def scale_text(self) -> str:
        return "\n".join(f"- {b['min']}-{b['max']}: {b['label']}" for b in self.scale)

    def band_for(self, mark: int) -> dict:
        for band in self.scale:
            if band["min"] <= mark <= band["max"]:
                return band
        return self.scale[-1]

    def next_band_up(self, mark: int) -> str | None:
        index = next((i for i, b in enumerate(self.scale) if b["min"] <= mark <= b["max"]), None)
        return None if index in (None, 0) else self.scale[index - 1]["label"]


from src.universities import azteca, eiu, lincoln  # noqa: E402  (after the class, which they import)

UNIVERSITIES: dict[str, University] = {p.key: p for p in (eiu.PROFILE, azteca.PROFILE, lincoln.PROFILE)}
DEFAULT_KEY = "eiu"


def get_university(key: str | None) -> University:
    return UNIVERSITIES.get((key or "").lower(), UNIVERSITIES[DEFAULT_KEY])


def choices() -> list[tuple[str, str]]:
    """[(key, display name)] for the app's dropdown."""
    return [(p.key, p.name) for p in UNIVERSITIES.values()]
