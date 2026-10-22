"""Parse caller-supplied CNSOER legacy gas/water PDF text without network I/O.

Sources (accessed 2026-10-19): SOEP Monthly Production Report (2019),
project/field TOTAL PRODUCTION tables; Deep Panuke Monthly Production Report
(2018), page 1. URLs are recorded below. Input must retain the page breaks
emitted by ``pdftotext -layout``. Well tables are deliberately excluded.

Volumes remain in source units: gas equivalent is NOT established as sales
gas. No conversion factor, price, fiscal term or oil volume is assumed.
Only synthetic text belongs in committed tests. Regulator data and derived
volumes require separate reproduction permission under the CNSOER terms.
"""

from __future__ import annotations

import hashlib
import math
import re

import pandas as pd

_CDN = "https://cdn.cnsoer.ca/sites/default/files/2025-01/"
SOURCE_URLS = {
    "Sable": _CDN + "soep_monthly_production_report_0.pdf",
    "Deep Panuke": _CDN + "dp_monthly_production_report_0.pdf",
}
TERMS_URL = "https://cnsoer.ca/website-terms-of-use"
LICENCE_NOTE = (
    "CNSOER Website Terms of Use, General and Disclaimer (accessed 2026-10-19): "
    "personal and non-commercial use; reproduction requires permission. "
    "Public availability does not establish permission to republish volumes."
)
# SOEP report (2019), aggregate table headings; Deep Panuke report (2018), p. 1.
_SECTIONS = {
    "Sable": "TOTAL PRODUCTION",
    "Deep Panuke": "TOTAL PRODUCTION",
    "Thebaud": "THEBAUD TOTAL PRODUCTION",
    "Venture": "VENTURE TOTAL PRODUCTION",
    "North Triumph": "NORTH TRIUMPH TOTAL PRODUCTION",
    "Alma": "ALMA TOTAL PRODUCTION",
    "South Venture": "SOUTH VENTURE TOTAL PRODUCTION",
}
# English Gregorian month order, as used by the cited monthly tables.
_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
# Source date ranges: SOEP Dec-99--Dec-18; Deep Panuke Aug-13--May-18.
# Explicit century mapping avoids the platform strptime two-digit-year pivot.
_YEARS = {"99": 1999, **{f"{y:02}": 2000 + y for y in range(19)}}
_NUMBER = re.compile(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?")


class CnsoerParseError(ValueError):
    """The selected aggregate table is absent, ambiguous or malformed."""


def _selected_lines(text: str, field_name: str) -> list[str]:
    if field_name not in _SECTIONS:
        raise CnsoerParseError("unsupported CNSOER field")
    selected = []
    for page in text.split("\f"):
        lines = [" ".join(line.split()) for line in page.splitlines() if line.strip()]
        if lines and lines[0] == _SECTIONS[field_name]:
            selected.append(lines)
    if len(selected) != 1:
        raise CnsoerParseError("expected exactly one aggregate section")
    lines = selected[0]
    # Literal source headers: both reports' aggregate tables, not well tables.
    if len(lines) < 4 or lines[1] != "Date Gas Equivalent Volume Water Volume":
        raise CnsoerParseError("missing aggregate columns or monthly rows")
    if lines[2] != "(10³M³/Month) (M³/Month)":
        raise CnsoerParseError("unsupported aggregate units")
    return lines[3:]


def _parse_row(line: str, field_name: str) -> dict:
    # SOEP Monthly Production Report (2019), aggregate Nov-14 rows: a standalone
    # trailing backtick is an annotation in pdftotext output, not a fourth value.
    if field_name != "Deep Panuke":
        line = line.removesuffix(" `")
    parts = line.split()
    if len(parts) != 3:
        raise CnsoerParseError("expected date, gas equivalent and water")
    match = re.fullmatch(r"([A-Za-z]{3})-(\d{2})", parts[0])
    if not match or match[1] not in _MONTHS or match[2] not in _YEARS:
        raise CnsoerParseError("unsupported monthly date")
    year, month = _YEARS[match[2]], _MONTHS.index(match[1]) + 1
    # Bounds are the published table extents, not engineering acceptance limits.
    first, last = (
        ((2013, 8), (2018, 5))
        if field_name == "Deep Panuke"
        else ((1999, 12), (2018, 12))
    )
    if not first <= (year, month) <= last:
        raise CnsoerParseError("monthly date outside published report extent")
    values = []
    for token in parts[1:]:
        if not _NUMBER.fullmatch(token):
            raise CnsoerParseError("invalid nonnegative production value")
        value = float(token.replace(",", ""))
        if not math.isfinite(value):
            raise CnsoerParseError("nonfinite production value")
        values.append(value)
    return dict(
        field_name=field_name,
        year=year,
        month=month,
        gas_equivalent_e3m3=values[0],
        water_m3=values[1],
    )


def parse_cnsoer_production_text(text: str, *, field_name: str) -> pd.DataFrame:
    """Read exactly one published aggregate table; retain zeros and source units.

    ``Sable`` selects the project total. The five named Sable fields select
    field totals. ``Deep Panuke`` selects its project total. Input identity is
    the caller's responsibility: the two project-total headings are identical.
    Missing months are not imputed; malformed rows and duplicates are errors.
    """
    rows = [_parse_row(line, field_name) for line in _selected_lines(text, field_name)]
    frame = pd.DataFrame(rows)
    if frame.duplicated(["year", "month"]).any():
        raise CnsoerParseError("duplicate monthly production period")
    return frame.sort_values(["year", "month"]).reset_index(drop=True)


class CnsoerProductionLoader:
    """Explicit text-only loader; never fetch, cache or publish regulator data.

    Project identity must be supplied by the caller against the source URL.
    Provenance records the digest of the extracted text, not the original PDF.
    ``load_field_production`` retains metric gas-equivalent columns and is not
    yet a drop-in unified CanadaAdapter input (sales-gas basis is unresolved).
    """

    def __init__(self, *, raw_text: str, project: str):
        if project not in SOURCE_URLS:
            raise CnsoerParseError("unsupported CNSOER project")
        self._raw_text = raw_text
        self._project = project

    def load_field_production(self, field_name: str) -> pd.DataFrame:
        if field_name not in _SECTIONS or (
            (field_name == "Deep Panuke") != (self._project == "Deep Panuke")
        ):
            raise CnsoerParseError("field does not belong to declared project")
        frame = parse_cnsoer_production_text(self._raw_text, field_name=field_name)
        frame["source"] = "canada-cnsoer"
        return frame

    def metadata(self) -> dict:
        """Return source attribution and explicit limits on input readiness."""
        return {
            "source_id": "canada-cnsoer",
            "source_url": SOURCE_URLS[self._project],
            "project": self._project,
            "input_kind": "caller_supplied_unverified_text",
            "text_sha256": hashlib.sha256(self._raw_text.encode("utf-8")).hexdigest(),
            "gas_unit": "10^3 m3/month (gas equivalent)",
            "water_unit": "m3/month",
            "terms_url": TERMS_URL,
            "LICENCE_NOTE": LICENCE_NOTE,
            "publication_status": "NOT_EVALUATED",
            "revenue_status": "NOT_EVALUATED",
            "limitations": [
                "Source identity, completeness and freshness require caller verification",
                "Gas-equivalent volume does not establish saleable gas or heat content",
                "Sales volume, price, currency and fiscal basis require explicit inputs",
                "Reproduction permission has not been established",
            ],
        }
