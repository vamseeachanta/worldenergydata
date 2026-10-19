"""Local CNSOER legacy gas/water tables, with no implicit sales-gas conversion.

Source layout: CNSOER monthly production reports, January 2025 archive,
total-production tables (SOURCE_URLS below; inspected 2026-10-19). Gas is
reported as *Gas Equivalent Volume*, in thousand cubic metres per month;
water is cubic metres per month. Neither oil nor condensate is inferred.

The source terms restrict reproduction and commercial use:
https://cnsoer.ca/website-terms-of-use (inspected 2026-10-19).
This module downloads nothing, persists nothing and includes no source data.
Only supplied local PDF bytes or extracted text are consumed. The input digest
identifies supplied bytes; it does not authenticate their regulator origin.
"""

from __future__ import annotations

import hashlib
import math
import re
import subprocess
import unicodedata
from pathlib import Path

import pandas as pd

SOURCE_URLS = {
    "sable": (
        "https://cdn.cnsoer.ca/sites/default/files/2025-01/"
        "soep_monthly_production_report_0.pdf"
    ),
    "deep_panuke": (
        "https://cdn.cnsoer.ca/sites/default/files/2025-01/"
        "dp_monthly_production_report_0.pdf"
    ),
}
# Source: January 2025 archived reports, TOTAL PRODUCTION date columns,
# first and final monthly rows. These bounds also resolve two-digit years.
_REPORTS = {
    "sable": ("Sable", "1999-12", "2018-12"),
    "deep_panuke": ("Deep Panuke", "2013-08", "2018-05"),
}
# Source: the same archived report's field-total table titles. Well-level
# tables are deliberately excluded so totals and their components cannot mix.
_SABLE_SECTIONS = {
    "THEBAUD TOTAL PRODUCTION": "Thebaud",
    "VENTURE TOTAL PRODUCTION": "Venture",
    "NORTH TRIUMPH TOTAL PRODUCTION": "North Triumph",
    "ALMA TOTAL PRODUCTION": "Alma",
    "SOUTH VENTURE TOTAL PRODUCTION": "South Venture",
}
_MONTHS = {
    name: number
    for number, name in enumerate(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        start=1,
    )
}
_NUMBER = r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?"
# Source: January 2025 archived Sable total table, November 2014 row, has a
# trailing backtick. Accept only that annotation, never extra numeric columns.
_ROW = re.compile(rf"([A-Za-z]{{3}})-(\d{{2}})\s+({_NUMBER})\s+({_NUMBER})(?:\s+`)?")


class CnsoerParseError(ValueError):
    """Supplied content does not match a supported total-production table."""


def _section_lines(text: str, section: str) -> list[str]:
    """Select total-table pages without consuming field or well components."""
    result = []
    selected = False
    for page in text.split("\f"):
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        if not lines or lines[0] != section:
            continue
        selected = True
        # Source: January 2025 archive, table header and units immediately
        # below each total-production title. NFKC normalizes superscripts.
        headers = [
            re.sub(r"\s+", "", unicodedata.normalize("NFKC", line)).lower()
            for line in lines[1:3]
        ]
        if headers != [
            "dategasequivalentvolumewatervolume",
            "(103m3/month)(m3/month)",
        ]:
            raise CnsoerParseError("unexpected total-production columns or units")
        result.extend(lines[3:])
    if not selected or not result:
        raise CnsoerParseError("selected section has no monthly production rows")
    return result


def _parse_row(line: str, years: dict[str, int], first: str, last: str) -> dict:
    match = _ROW.fullmatch(line)
    if match is None:
        raise CnsoerParseError("malformed monthly production row")
    month_name, short_year, gas, water = match.groups()
    if month_name not in _MONTHS or short_year not in years:
        raise CnsoerParseError("monthly production date outside report bounds")
    year, month = years[short_year], _MONTHS[month_name]
    period = f"{year:04d}-{month:02d}"
    if not first <= period <= last:
        raise CnsoerParseError("monthly production date outside report bounds")
    gas, water = float(gas.replace(",", "")), float(water.replace(",", ""))
    if not all(math.isfinite(value) for value in (gas, water)):
        raise CnsoerParseError("nonfinite monthly production value")
    return {
        "year": year,
        "month": month,
        "gas_equivalent_e3m3": gas,
        "water_m3": water,
    }


def parse_cnsoer_production_text(
    text: str, *, report: str, section: str = "TOTAL PRODUCTION"
) -> pd.DataFrame:
    """Parse a selected total table from supplied ``pdftotext -layout`` text.

    ``report`` is ``sable`` or ``deep_panuke``; Sable additionally supports
    explicit field-total titles. Duplicate periods, malformed data and unknown
    units fail closed. Partial histories are permitted but flagged. Revenue is
    NOT_EVALUATED: neither a saleable-gas basis nor a realized price is supplied.
    Output stays in native units and is not a unified-production adapter input.
    """
    if report not in _REPORTS:
        raise CnsoerParseError("unsupported report")
    name, first, last = _REPORTS[report]
    if section != "TOTAL PRODUCTION":
        if report != "sable" or section not in _SABLE_SECTIONS:
            raise CnsoerParseError("unsupported field-total section")
        name = _SABLE_SECTIONS[section]
    years = {str(y)[-2:]: y for y in range(int(first[:4]), int(last[:4]) + 1)}
    rows = [
        _parse_row(line, years, first, last) for line in _section_lines(text, section)
    ]
    frame = pd.DataFrame(rows)
    if frame.duplicated(["year", "month"]).any():
        raise CnsoerParseError("duplicate monthly production period")
    frame.insert(0, "field_name", name)
    frame["source"] = "cnsoer"
    frame = frame.sort_values(["year", "month"]).reset_index(drop=True)
    frame.attrs = _provenance(frame, text, report, section, first, last)
    return frame


def _provenance(frame, text, report, section, first, last) -> dict:
    periods = [f"{row.year:04d}-{row.month:02d}" for row in frame.itertuples()]
    return {
        "source_url": SOURCE_URLS[report],
        "source_version": "January 2025 archive",
        "section": section,
        "units": {"gas_equivalent_e3m3": "10^3 m3/month", "water_m3": "m3/month"},
        "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "input_kind": "extracted_text",
        "history_complete": periods
        == pd.period_range(first, last, freq="M").astype(str).tolist(),
        "readiness_status": "unverified",
        "revenue_status": "NOT_EVALUATED",
        "revenue_reason": "Saleable-gas realization basis and realized price are required.",
        "rights_note": "Restricted source terms; reproduction permission is not established.",
    }


class CnsoerProductionLoader:
    """Read exactly one local PDF or supplied text; no download or cache writes.

    PDF input requires the external ``pdftotext`` executable. The hashed PDF
    bytes are also passed on stdin to the extractor, avoiding a second read.
    ``load()`` returns native-unit rows and the parser's unverified provenance.
    """

    def __init__(
        self,
        *,
        report: str,
        section: str = "TOTAL PRODUCTION",
        path: Path | None = None,
        raw_text: str | None = None,
    ):
        self.report = report
        self.section = section
        self.path = path
        self.raw_text = raw_text

    def load(self) -> pd.DataFrame:
        if (self.path is None) == (self.raw_text is None):
            raise CnsoerParseError("exactly one path or raw_text is required")
        if self.raw_text is not None:
            return parse_cnsoer_production_text(
                self.raw_text, report=self.report, section=self.section
            )
        payload = Path(self.path).read_bytes()
        text = subprocess.check_output(
            ["pdftotext", "-layout", "-", "-"], input=payload
        ).decode("utf-8")
        frame = parse_cnsoer_production_text(
            text, report=self.report, section=self.section
        )
        frame.attrs.update(
            input_sha256=hashlib.sha256(payload).hexdigest(), input_kind="pdf"
        )
        return frame
