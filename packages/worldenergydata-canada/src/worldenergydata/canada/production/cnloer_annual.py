"""Strict annual C-NLOER ``pdftotext -layout`` parsing for local use.

Layout authority: C-NLOER Statistical Information, 2026 annual field PDFs,
Monthly Details, opened 2026-10-19. Reports have six interleaved metric/imperial
columns, space-grouped integers, merged month cells and blank future months.
https://www.cnloer.ca/information/statistics/

Raw PDFs and derived volumes remain restricted pending the maintainer's licence
review. This module performs no download, persistence or public export.
"""

from __future__ import annotations

import math
import re
from datetime import datetime

import pandas as pd

from worldenergydata.canada.production.cnloer_loader import CnloerParseError
from worldenergydata.common.units import GasUnits

# Reservoir order and Total availability: cited 2026 reports, Monthly Details.
_RESERVOIRS = {
    "Hibernia": ("Hibernia", "Avalon", "Catalina", "Total"),
    "Hebron": ("Ben Nevis", "Hibernia", "Jeanne d'Arc", "Total"),
    "North Amethyst": ("Ben Nevis/Avalon", "Hibernia"),
    "Terra Nova": ("Jeanne d'Arc",),
    "White Rose": ("Ben Nevis/Avalon",),
}
# English source month labels are independent of the process calendar locale.
_MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        start=1,
    )
}
# Source unit header order; no density or metric-to-imperial factor is needed.
_UNITS = ["m³", "bbls", "10³ m³", "MMscf", "m³", "bbls"]


def _cells(line: str) -> list[str]:
    """Column gaps have at least two spaces; digit groups have one space."""
    return re.split(r"\s{2,}", line.strip())


def _volumes(cells: list[str]) -> tuple[float, float, float] | None:
    if not cells:
        return None
    if len(cells) == len(_UNITS) + 1:
        try:
            datetime.strptime(cells.pop(), "%m/%d/%Y")
        except ValueError as exc:
            raise CnloerParseError("invalid amendment date") from exc
    if len(cells) != len(_UNITS):
        raise CnloerParseError("incomplete annual production columns")
    values = []
    for cell in cells:
        if not re.fullmatch(r"(?:\d+|\d{1,3}(?: \d{3})+)", cell):
            raise CnloerParseError("malformed annual production value")
        value = float(cell.replace(" ", ""))
        if not math.isfinite(value):
            raise CnloerParseError("nonfinite annual production value")
        values.append(value)
    # Source columns: oil bbls, gas MMscf, water bbls. EIA Glossary, Mcf/MMcf
    # entries (opened 2026-10-19): million/thousand = 1000; source standard
    # conditions are retained. https://www.eia.gov/tools/glossary/index.php?id=M
    return values[1], values[3], values[5]


def _finish_month(block: dict, expected: tuple[str, ...], number: int):
    if block["reservoirs"] != list(expected) or block["month"] != number:
        raise CnloerParseError("incomplete reservoirs or unordered monthly periods")
    values = block["values"]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise CnloerParseError("partially blank monthly production")
    selected = values[-1:] if expected[-1] == "Total" else values
    oil, gas, water = (sum(value[i] for value in selected) for i in range(3))
    gas *= GasUnits.MMSCF_TO_MCF
    if not all(math.isfinite(v) for v in (oil, gas, water)):
        raise CnloerParseError("nonfinite monthly production")
    return oil, gas, water


def _monthly_blocks(lines: list[str], expected: tuple[str, ...], year: int):
    blocks, block = [], None
    for line in lines:
        if not line.strip():
            continue
        cells = _cells(line)
        if cells[0].isdigit() and (
            int(cells.pop(0)) != year or blocks or block is not None
        ):
            raise CnloerParseError("unexpected annual production year")
        month = _MONTHS.get(cells[0]) if cells else None
        if month is not None:
            cells.pop(0)
        if cells and cells[0] == expected[0]:
            if block is not None:
                blocks.append(block)
            block = {"month": None, "reservoirs": [], "values": []}
        if block is None:
            raise CnloerParseError("missing first reservoir")
        if month is not None:
            if block["month"] is not None:
                raise CnloerParseError("duplicate monthly period")
            block["month"] = month
        if cells:
            reservoir = cells.pop(0)
            block["reservoirs"].append(reservoir)
            block["values"].append(_volumes(cells))
    if block is not None:
        blocks.append(block)
    # Calendar completeness: source annual reports show all twelve month blocks,
    # including future blanks. Missing blocks cannot be treated as zero.
    if len(blocks) != len(_MONTHS):
        raise CnloerParseError("incomplete annual monthly periods")
    return blocks


def _report_lines(text: str, field_name: str, year: int) -> list[str]:
    lines = [line.replace("\xa0", " ") for line in text.splitlines()]
    title = f"{field_name} Field Monthly Production - {year}"
    if sum(line.strip() == title for line in lines) != 1:
        raise CnloerParseError("field or year does not match annual title")
    if sum(_cells(line) == _UNITS for line in lines) != 1:
        raise CnloerParseError("unsupported annual production units")
    headers = ["Year", "Reservoir", "Oil", "Gas", "Water", "Amendment Date"]
    if (
        sum(
            [cell.rstrip("*") for cell in _cells(line) if cell != "Month"] == headers
            for line in lines
        )
        != 1
    ):
        raise CnloerParseError("unsupported annual production column order")
    starts = [i for i, line in enumerate(lines) if line.strip() == "Monthly Details"]
    if len(starts) != 1:
        raise CnloerParseError("missing annual Monthly Details section")
    start = starts[0] + 1
    for end in range(start, len(lines)):
        if re.match(rf"^\s*Total\s*-?\s*{year}(?:\s|$)", lines[end]):
            # Annual summary labels can be centred after earlier summary rows,
            # as in the cited North Amethyst report. Exclude the entire summary.
            cells = _cells(lines[end])
            expected = _RESERVOIRS[field_name]
            if len(cells) > 1 and cells[1] in expected:
                for reservoir in reversed(expected[: expected.index(cells[1])]):
                    end -= 1
                    while end >= start and not lines[end].strip():
                        end -= 1
                    if end < start or _cells(lines[end])[0] != reservoir:
                        raise CnloerParseError("malformed annual summary boundary")
            return lines[start:end]
    raise CnloerParseError("missing annual total boundary")


def parse_cnloer_annual_text(text: str, *, field_name: str, year: int) -> pd.DataFrame:
    """Parse only the validated annual layout, failing on incomplete reports.

    Explicit field totals take precedence over reservoir rows. Without totals,
    imperial reservoir columns are summed. Blank future periods are omitted;
    populated zero values are retained. No freshness or reuse-rights approval
    is implied by successful parsing. Historical layouts require separate tests.
    """
    if field_name not in _RESERVOIRS:
        raise CnloerParseError("unsupported annual individual field")
    if type(year) is not int or year <= 0:
        raise CnloerParseError("annual year must be a positive integer")
    expected = _RESERVOIRS[field_name]
    blocks = _monthly_blocks(_report_lines(text, field_name, year), expected, year)
    rows, blank_seen = [], False
    for month, block in enumerate(blocks, start=1):
        volumes = _finish_month(block, expected, month)
        if volumes is None:
            blank_seen = True
            continue
        if blank_seen:
            raise CnloerParseError("populated period follows a blank period")
        rows.append((field_name, year, month, *volumes))
    if not rows:
        raise CnloerParseError("no monthly production in annual report")
    return pd.DataFrame(
        rows, columns=["field_name", "year", "month", "oil_bbl", "gas_mcf", "water_bbl"]
    )
