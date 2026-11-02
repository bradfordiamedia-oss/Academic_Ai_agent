"""Compact, system-computed summaries of data/model files submitted with a thesis
(for example SmartPLS .txt/.ok/.settings/.splsm files, CSV or Excel exports)."""
from __future__ import annotations

import io
import re

TEXT_LIMIT = 3000
MAX_COLUMNS = 60
MAX_TABLE_ROWS = 20000


def describe_support_file(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xlsm")):
        rows = _xlsx_rows(file_bytes)
        if rows is None:
            return f"{filename}: spreadsheet could not be read."
        return _describe_table(filename, rows)

    text = file_bytes.decode("utf-8", errors="ignore") if _is_utf8(file_bytes) else file_bytes.decode("latin-1")
    text = text.replace("\x00", "")
    rows = _parse_table(text)
    if rows and len(rows) >= 5 and _numeric_share(rows) >= 0.8:
        return _describe_table(filename, rows)
    head = text[:TEXT_LIMIT].strip()
    more = " (truncated)" if len(text) > TEXT_LIMIT else ""
    return f"{filename}: text file, {len(text):,} characters{more}. Content:\n{head}"


def _is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _xlsx_rows(file_bytes: bytes):
    try:
        from openpyxl import load_workbook

        sheet = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True).worksheets[0]
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append(["" if v is None else str(v) for v in row])
            if len(rows) >= MAX_TABLE_ROWS:
                break
        return rows
    except Exception:  # noqa: BLE001 - unreadable file or openpyxl missing
        return None


def _parse_table(text: str) -> list[list[str]]:
    lines = [line for line in text.splitlines() if line.strip()][:MAX_TABLE_ROWS]
    if not lines:
        return []
    sample = lines[0]
    for delimiter in (";", "\t", ","):
        if delimiter in sample:
            return [[c.strip() for c in line.split(delimiter)] for line in lines]
    return [line.split() for line in lines]


def _to_float(cell: str):
    try:
        return float(cell.replace(",", ".")) if cell not in ("", "-") else None
    except ValueError:
        return None


def _numeric_share(rows: list[list[str]]) -> float:
    body = rows[1:] if rows and any(_to_float(c) is None and c for c in rows[0]) else rows
    cells = [c for row in body[:200] for c in row if c != ""]
    return sum(_to_float(c) is not None for c in cells) / len(cells) if cells else 0.0


def _describe_table(filename: str, rows: list[list[str]]) -> str:
    if not rows:
        return f"{filename}: empty table."
    has_header = any(_to_float(c) is None and c for c in rows[0])
    header = rows[0] if has_header else [f"col{i + 1}" for i in range(len(rows[0]))]
    body = rows[1:] if has_header else rows
    stats = []
    for index, name in enumerate(header[:MAX_COLUMNS]):
        values = [v for row in body if index < len(row) for v in [_to_float(row[index])] if v is not None]
        if values:
            stats.append(f"{name}: {min(values):g} / {max(values):g} / {sum(values) / len(values):.2f}")
    extra = f" (first {MAX_COLUMNS} of {len(header)} columns shown)" if len(header) > MAX_COLUMNS else ""
    return (
        f"{filename}: data table with {len(body)} cases (rows) and {len(header)} columns{extra}. "
        f"Per-column min / max / mean: " + "; ".join(stats) + "."
    )
