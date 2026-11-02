"""Render a thesis "Detailed Feedback" result (see thesis_evaluator) as a branded PDF."""
from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace

from src import report_template as tpl

NAVY = (11, 29, 58)
GOLD = (201, 154, 46)
TEXT = (30, 32, 38)
MUTED = (85, 90, 100)
RED = (142, 29, 42)
GREEN = (28, 110, 62)
WHITE = (255, 255, 255)
LABEL_FILL = (238, 241, 246)
ROW_ALT = (236, 241, 248)
TOTAL_FILL = (251, 229, 229)
BORDER = (170, 176, 188)

BODY = 9.2
LINE = 4.8
NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


class _FeedbackPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.set_margins(16, 40, 16)
        self.set_auto_page_break(True, margin=28)
        self.add_font("DejaVu", "", str(tpl.FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(tpl.FONT_DIR / "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", str(tpl.FONT_DIR / "DejaVuSans-Oblique.ttf"))
        self._body()

    # ---- page furniture (letterhead on every page, as in the sample)

    def header(self) -> None:
        inst = tpl.INSTITUTION
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 32, style="F")
        self.set_fill_color(*GOLD)
        self.rect(0, 32, 210, 0.9, style="F")
        self.set_fill_color(*WHITE)
        self.rect(10, 4.5, 60, 23, style="F", round_corners=True, corner_radius=2)
        if tpl.LOGO_PATH.exists():
            self.image(str(tpl.LOGO_PATH), x=12, y=7.2, w=56)
        self.set_text_color(*WHITE)
        self.set_font("DejaVu", "B", 9.5)
        self.set_xy(76, 6.5)
        self.cell(118, 5, inst["name"], align="R")
        self.set_font("DejaVu", "", 7.3)
        y = 12.3
        for line in inst["header_lines"]:
            self.set_xy(76, y)
            self.cell(118, 4, line, align="R")
            y += 4.4
        self._body()
        self.set_y(self.t_margin)

    def footer(self) -> None:
        lines = tpl.INSTITUTION["footer_lines"]
        self.set_draw_color(*GOLD)
        self.set_line_width(0.4)
        self.line(16, 273, 194, 273)
        self.set_y(274.5)
        self.set_font("DejaVu", "", 7.3)
        for i, line in enumerate(lines):
            self.set_text_color(*(TEXT if i == 0 else NAVY))
            self.cell(0, 3.6, line, align="C", **NEXT_LINE)
        self._body()

    # ---- text helpers

    def _body(self) -> None:
        self.set_font("DejaVu", "", BODY)
        self.set_text_color(*TEXT)

    def _keep_with_next(self, height: float) -> None:
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()

    def h1(self, text: str) -> None:
        self._keep_with_next(28)
        self.ln(3)
        self.set_font("DejaVu", "B", 12.5)
        self.set_text_color(*NAVY)
        self.multi_cell(0, 6.5, text, **NEXT_LINE)
        self.ln(1.2)
        self._body()

    def h2(self, text: str, size: float = 10.5) -> None:
        self._keep_with_next(34)
        self.ln(2.2)
        self.set_font("DejaVu", "B", size)
        self.set_text_color(*NAVY)
        self.multi_cell(0, 5.6, text, **NEXT_LINE)
        self.ln(0.8)
        self._body()

    def para(self, text: str, indent: float = 0, size: float = BODY, italic: bool = False,
             color=TEXT, after: float = 1.4, align: str = "J", line: float = LINE) -> None:
        if not text:
            return
        self.set_font("DejaVu", "I" if italic else "", size)
        self.set_text_color(*color)
        self.set_x(self.l_margin + indent)
        self.multi_cell(0, line, text, align=align, **NEXT_LINE)
        self.ln(after)
        self._body()

    def quote(self, quote: dict) -> None:
        self._keep_with_next(20)
        self.para(f'"{quote["text"]}"', indent=3, size=8.4, italic=True, color=(55, 58, 66),
                  after=0.5, align="L", line=4.3)
        self.para(f"Source: {quote['source']}", size=7.9, color=MUTED, after=1.8, align="L", line=4.1)

    def bullet(self, text: str, marker: str = "•", indent: float = 3, width: float = 4.5) -> None:
        self._keep_with_next(LINE * 2)
        self._body()
        self.set_x(self.l_margin + indent)
        self.cell(width, LINE, marker)
        self.multi_cell(0, LINE, text, align="J", **NEXT_LINE)
        self.ln(0.7)

    # ---- tables

    def info_table(self, rows: list[tuple]) -> None:
        self.set_draw_color(*BORDER)
        self.set_line_width(0.2)
        with self.table(col_widths=(40, 138), first_row_as_headings=False, line_height=5.0,
                        padding=1.3, borders_layout="ALL", text_align="LEFT") as table:
            for label, value, style in rows:
                row = table.row()
                row.cell(label, style=FontFace(fill_color=LABEL_FILL))
                row.cell(value, style=style)

    def marks_table(self, criteria: list[dict], total: float, overall: int) -> None:
        self.set_draw_color(*BORDER)
        self.set_line_width(0.2)
        head = FontFace(emphasis="BOLD", color=WHITE, fill_color=NAVY)
        with self.table(col_widths=(11, 96, 22, 22, 27), line_height=4.8, padding=1.1,
                        borders_layout="ALL", headings_style=head,
                        text_align=("CENTER", "LEFT", "CENTER", "CENTER", "CENTER")) as table:
            header = table.row()
            for title in ("No.", "Criterion", "Weight", "Mark", "Contribution"):
                header.cell(title)
            for i, c in enumerate(criteria, 1):
                style = FontFace(fill_color=ROW_ALT if i % 2 == 0 else WHITE)
                row = table.row()
                for value in (str(i), c["name"], f"{c['weight']:g}%", f"{c['mark']}%", f"{c['contribution']:.1f}"):
                    row.cell(value, style=style)
            bold = FontFace(emphasis="BOLD", fill_color=TOTAL_FILL)
            row = table.row()
            for value in ("", "Weighted total", "100%", f"{overall}%", f"{total:.1f}"):
                row.cell(value, style=bold)

    def scale_table(self, rows: list[dict]) -> None:
        self.set_draw_color(*BORDER)
        self.set_line_width(0.2)
        head = FontFace(emphasis="BOLD", color=WHITE, fill_color=NAVY)
        with self.table(col_widths=(46, 34, 98), line_height=4.8, padding=1.2, borders_layout="ALL",
                        headings_style=head, text_align="LEFT") as table:
            header = table.row()
            for title in ("Classification", "Mark range", "Meaning for this thesis"):
                header.cell(title)
            for row_data in rows:
                style = FontFace(emphasis="BOLD" if row_data["current"] else None,
                                 fill_color=TOTAL_FILL if row_data["current"] else WHITE)
                row = table.row()
                row.cell(row_data["label"], style=style)
                row.cell(row_data["range"], style=style)
                row.cell(row_data["meaning"], style=style)


def _document_word(source_label: str) -> str:
    return "thesis PDF" if "PDF" in source_label else "thesis document"


def _next_band_label(mark: int) -> str | None:
    index = next((i for i, band in enumerate(tpl.DEFAULT_SCALE) if band["min"] <= mark <= band["max"]), None)
    if index is None or index == 0:
        return None
    return tpl.DEFAULT_SCALE[index - 1]["label"]


def _holds_down_label(mark: int) -> str:
    if mark >= tpl.PASS_MARK:
        higher = _next_band_label(mark)
        if higher:
            return f"What holds the mark below {higher}."
        return "What would protect this mark."
    return "What holds the mark down."


def build_feedback_pdf(result: dict) -> bytes:
    inst = tpl.INSTITUTION
    student = result["student"]
    criteria = result["criteria"]
    passed = result["passed"]

    pdf = _FeedbackPDF()
    pdf.set_title(f"{result['report_title'].title()} - {student['name'] or 'Thesis'}")
    pdf.set_author("Bradford Academic Agent")
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 14)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, result["report_title"], align="C", **NEXT_LINE)
    pdf.set_font("DejaVu", "", 8.8)
    pdf.set_text_color(*TEXT)
    pdf.cell(0, 5, inst["subtitle"], align="C", **NEXT_LINE)
    pdf.ln(4)
    pdf._body()

    bold = FontFace(emphasis="BOLD")
    plain = FontFace()
    pdf.info_table(
        [
            ("Student Name", student["name"] or "Not provided", bold),
            ("ID Number", student["id"] or "Not provided", bold),
            ("Module Name / Code", student["module"] or "Not provided", bold),
            ("Thesis Title", student["title"] or "Not stated in the thesis", plain),
            ("Date of Feedback", result["date"], bold),
            ("Overall Mark", f"{result['overall_mark']}% | {result['classification']}",
             FontFace(emphasis="BOLD", color=GREEN if passed else RED)),
        ]
    )
    pdf.ln(3.5)

    supporting = result.get("supporting_names") or []
    if supporting:
        scope = (
            "Checks were made on the submitted text, the assessment guidelines and summaries of the "
            f"supporting files you submitted ({', '.join(supporting)}). The analysis was not re-run, and "
            "whether cited works exist and similarity (Turnitin) results were not checked."
        )
    else:
        scope = (
            "Checks were made on the submitted text and the assessment guidelines only: whether cited works "
            "exist, similarity (Turnitin) results and any raw data files were not checked."
        )
    pdf.para(
        f"This report explains each mark on the {result['rubric_name']} rubric. Marks use the European "
        f"Credit Transfer and Accumulation System (ECTS) scale of {inst['short']}. Quotes are taken from "
        f"your submitted {_document_word(result['source_label'])} and were checked against its text. "
        + scope
    )

    # 1. Summary of marks
    pdf.h1("1. Summary of Marks")
    pdf.marks_table(criteria, result["total"], result["overall_mark"])
    pdf.ln(2.5)
    pdf.set_font("DejaVu", "B", 10.5)
    pdf.set_text_color(*(GREEN if passed else RED))
    pdf.cell(0, 6, f"Classification: {result['classification']}", align="C", **NEXT_LINE)
    pdf._body()
    first = criteria[0]
    note = (
        f"Contribution = Mark x Weight / 100. Example: Criterion 1 is {first['mark']}% x {first['weight']:g} / 100 = "
        f"{first['contribution']:.1f}. The {len(criteria)} contributions add to {result['total']:.1f}, "
        f"which gives the overall mark of {result['overall_mark']}%."
    )
    if result["weights_normalized"]:
        note += " The weights stated in the guidelines did not add up to 100 and were scaled proportionally."
    pdf.para(note, size=8, color=MUTED, align="L", line=4.2)

    # 2. Integrity findings
    pdf.h1("2. Integrity Findings")
    findings = result["integrity_findings"]
    if findings:
        pdf.para(
            "Academic integrity comes first. The findings below apply across the criteria they affect, "
            "and serious ones keep those criteria low and can lead to a fail."
        )
        for i, finding in enumerate(findings, 1):
            pdf.h2(f"2.{i} {finding['title']}", size=10)
            pdf.para(finding["detail"])
            for quote in finding["quotes"]:
                pdf.quote(quote)
    else:
        pdf.para("No integrity problems were found in the submitted text.")

    # 3. Criterion by criterion
    pdf.h1("3. Criterion-by-Criterion Feedback")
    for i, c in enumerate(criteria, 1):
        pdf.h2(f"Criterion {i}. {c['name']} - {c['mark']}% (Weight {c['weight']:g}%)")
        pdf.para(f"Why {c['mark']}%. {c['why']}" if c["why"] else "")
        pdf.para(f"Strength. {c['strength']}" if c["strength"] else "")
        for quote in c["quotes"]:
            pdf.quote(quote)
        if c["checks"]:
            pdf.para("What was checked.", after=0.6)
            for check in c["checks"]:
                pdf.bullet(check)
        if c["holds_down"]:
            pdf.para(f"{_holds_down_label(c['mark'])} {c['holds_down']}")

    # 4. Fix list
    pdf.h1("4. What to Fix to Reach a Pass" if not passed else "4. Recommended Improvements")
    if passed:
        pdf.para(
            f"This thesis reaches the pass mark of {result['pass_mark']}%. The items below would raise it "
            "further, in order of importance."
        )
    else:
        pdf.para(
            f"A pass on this thesis needs a clean integrity base and a weighted total of at least "
            f"{result['pass_mark']}%. Do the items below in order. Resubmit the full package together."
        )
    for i, item in enumerate(result["fix_list"], 1):
        pdf.bullet(item, marker=f"{i}.", indent=2, width=7)

    # 5. Grading scale
    pdf.h1(f"5. {inst['short']} Grading Scale (ECTS)")
    pdf.scale_table(result["scale"])
    pdf.ln(2.5)
    pdf.set_font("DejaVu", "B", BODY)
    pdf.cell(0, 6, f"Your current band: {result['overall_mark']}%.", **NEXT_LINE)
    pdf._body()
    pdf.ln(1.5)
    pdf.para(
        f"Draft feedback prepared with the Bradford Academic Agent on {result['date']} from the submitted "
        f"thesis text and the assessment guidelines, for {inst['issued_by']}. The marks are indicative "
        "until the examiner confirms them on the formal marking sheet.",
        size=8, color=MUTED, align="L", line=4.2,
    )

    return bytes(pdf.output())
