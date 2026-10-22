"""Canada C-NLOER offshore per-field monthly production loader (#719).

Parses the C-NLOER (Canada-Newfoundland and Labrador Offshore Energy Regulator,
formerly C-NLOPB) per-field monthly production PDFs
(https://www.cnloer.ca/information/statistics/) into the unified loader columns
(field_name/year/month/oil_bbl/gas_mcf/water_bbl).

Real C-NLOER layout (codex-verified 2026-07-04): one PDF per field
(``{h,he,n,t,w}pro.pdf``), monthly rows with oil/gas/water in BOTH metric and
imperial. Some fields carry per-reservoir subrows that must be summed to a field
monthly total; North Amethyst has no per-month ``Total`` row (sum reservoirs);
Hibernia/Hebron carry explicit ``Total`` rows. ``mpro.pdf`` is the ALL-FIELD
monthly total (not a field) and is rejected.

Licence: C-NLOER PDFs are public regulator disclosures but NOT open-licensed
(no OGL). Raw PDFs are NOT committed to the repo; the live-fetch lane caches them
to a gitignored directory. The committed fixture is a small LABELED-SYNTHETIC
sample (``source="cnloer_fixture_synthetic"``) so no licence-restricted data
enters git. See ``_metadata.json`` / ``LICENCE_NOTE``.

The ``pdftotext`` I/O is a thin wrapper; the testable core is
``parse_cnloer_production_text`` (a pure text->DataFrame transform), so it
unit-tests without a committed binary PDF or poppler.

Issue: https://github.com/vamseeachanta/worldenergydata/issues/719
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from importlib.resources import files
from math import isfinite
from pathlib import Path
from typing import List, Optional

import pandas as pd

from worldenergydata.common.units import GasUnits, OilUnits, WaterUnits

# --- documented conversion constants (prefer source imperial columns) -------
# Oil/water: metric m3 -> barrels (API MPMS Ch. 11).
M3_TO_BBL = OilUnits.SM3_TO_BBL  # 6.2898 bbl/m3
WATER_M3_TO_BBL = WaterUnits.M3_TO_BBL
# Gas: C-NLOER reports 10^3 m3 (thousand m3) and MMscf. 10^3 m3 -> Mcf via
# 1 m3 = 35.3147 scf: 1e3 m3 = 35 314.7 scf = 35.3147 Mcf.
E3M3_TO_MCF = GasUnits.SM3_TO_SCF  # 35.3147 (1e3 m3 -> Mcf)
MMSCF_TO_MCF = GasUnits.MMSCF_TO_MCF  # 1000.0

# C-NLOER field code -> canonical field name (PDF stem ``{code}pro.pdf``).
FIELD_CODES = {
    "h": "Hibernia",
    "he": "Hebron",
    "n": "North Amethyst",
    "t": "Terra Nova",
    "w": "White Rose",
}
# ``m``pro / off_prod are ALL-FIELD totals reports, NOT a field (guard).
_TOTALS_STEMS = {"m", "off_prod", "mpro"}

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_DATA_ROOT = files("worldenergydata.canada").joinpath("data/cnlopb")
DEFAULT_FIXTURE_CSV = _DATA_ROOT.joinpath("cnlopb_offshore_sample.csv")
DEFAULT_METADATA_JSON = _DATA_ROOT.joinpath("_metadata.json")


class CnloerParseError(ValueError):
    """Raised when a C-NLOER production text cannot be parsed."""


def _month_to_int(token: str) -> Optional[int]:
    return _MONTHS.get(str(token).strip().lower())


def parse_cnloer_production_text(text: str, *, field_name: str) -> pd.DataFrame:
    """Pure transform: ``pdftotext -layout`` output for one field -> long rows.

    Expects whitespace-delimited monthly lines of the form::

        <Month> <Year> <oil_m3> <oil_bbl> <gas_e3m3> <gas_MMscf> <water_m3> <water_bbl>

    Per-reservoir subrows (same Month/Year repeated) are summed to a single
    field monthly total. Rows with a non-parseable month or too few numeric
    values (blank future months, headers) are dropped. Prefers the source
    imperial columns (bbl / MMscf); converts the metric columns otherwise.

    Returns ``[field_name, year, month, oil_bbl, gas_mcf, water_bbl]`` -- one row
    per (year, month). ``condensate_bbl`` is intentionally absent (C-NLOER
    publishes no condensate column; the adapter sets it NaN).
    """
    field_stem = str(field_name).strip().lower()
    if field_stem in _TOTALS_STEMS:
        raise CnloerParseError(
            f"{field_name!r} is an all-field totals report (mpro), not a field"
        )

    rows: dict = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        month = _month_to_int(parts[0])
        if month is None:
            continue
        nums: List[float] = []
        for tok in parts[1:]:
            t = tok.replace(",", "")
            if re.fullmatch(r"-?\d+(?:\.\d+)?", t):
                nums.append(float(t))
        # need at least Year + oil + gas + water
        if len(nums) < 4:
            continue
        year = int(nums[0])
        if year <= 0:
            continue
        oil_bbl, gas_mcf, water_bbl = _extract_volumes(nums[1:])
        acc = rows.setdefault((year, month), [0.0, 0.0, 0.0])
        acc[0] += oil_bbl
        acc[1] += gas_mcf
        acc[2] += water_bbl

    if not rows:
        raise CnloerParseError(f"no monthly production rows parsed for {field_name!r}")

    out = pd.DataFrame(
        [
            {
                "field_name": str(field_name).strip(),
                "year": year,
                "month": month,
                "oil_bbl": acc[0],
                "gas_mcf": acc[1],
                "water_bbl": acc[2],
            }
            for (year, month), acc in sorted(rows.items())
        ]
    )
    return out.reset_index(drop=True)


def _extract_volumes(vals: List[float]) -> tuple:
    """Map a row's value columns (after Year) to (oil_bbl, gas_mcf, water_bbl).

    Layout is disambiguated by COUNT, not fixed index — a full C-NLOER row
    carries BOTH units interleaved (6 cols: oil_m3, oil_bbl, gas_e3m3,
    gas_MMscf, water_m3, water_bbl), so the source imperial columns are used
    directly. A metric-only row (3 cols: oil_m3, gas_e3m3, water_m3) is
    converted. Index-based "prefer imperial" is ambiguous when the imperial
    columns are absent, so dispatch on the column count instead.
    """
    n = len(vals)
    if n >= 6:  # both units present -> use source imperial columns
        return (vals[1], vals[3] * MMSCF_TO_MCF, vals[5])
    if n >= 3:  # metric only -> convert
        return (
            vals[0] * M3_TO_BBL,
            vals[1] * E3M3_TO_MCF,
            vals[2] * WATER_M3_TO_BBL,
        )
    return (0.0, 0.0, 0.0)


class _ModalTables(HTMLParser):
    """Collect cells from the five production modals, tolerating th/td endings."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = {}
        self._divs = []
        self._modal = None
        self._table = False
        self._row = None
        self._cell = None
        self._annotation = False

    def close(self):
        super().close()
        if self._modal is not None or self._table:
            raise CnloerParseError("incomplete production modal or table")

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            self._divs.append(self._modal)
            identifier = attrs.get("id", "")
            if identifier in {"pshf97", "pshf98", "pshf99", "pshf00", "pshf01"}:
                if identifier in self.tables:
                    raise CnloerParseError("duplicate production modal")
                if self._modal is not None:
                    raise CnloerParseError("incomplete production modal")
                self._modal = identifier
                self.tables[identifier] = []
        if self._modal and tag == "table":
            if self._table or self.tables[self._modal]:
                raise CnloerParseError("multiple production tables in modal")
            self._table = True
        # Unit exponents are header content; superscripts in data rows are annotations.
        if self._table and tag == "sup" and len(self.tables[self._modal]) >= 4:
            self._annotation = True
        if self._table and tag == "tr":
            if self._row is not None:
                raise CnloerParseError("incomplete production row")
            self._row = []
        if self._table and tag in {"td", "th"}:
            if self._cell is not None or self._row is None:
                raise CnloerParseError("incomplete production cell or row")
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None and not self._annotation:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag == "sup":
            self._annotation = False
        if tag in {"td", "th"} and self._cell is not None:
            if self._row is not None:
                self._row.append("".join(self._cell).strip())
            self._cell = None
            self._annotation = False
        if tag == "tr" and self._row is not None:
            if self._cell is not None:
                raise CnloerParseError("incomplete production cell")
            self.tables[self._modal].append(self._row)
            self._row = None
        if tag == "table":
            if self._row is not None:
                raise CnloerParseError("incomplete production row")
            self._table = False
        if tag == "div" and self._divs:
            if self._table and self._divs[-1] != self._modal:
                raise CnloerParseError("incomplete production table")
            self._modal = self._divs.pop()


def _modal_number(cell: str) -> str:
    """Validate nonnegative source numbers with space or comma grouping."""
    value = cell.strip().replace("\xa0", " ")
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:[ ,]\d{3})+)(?:\.\d+)?", value):
        raise CnloerParseError("malformed monthly production value")
    normalized = value.replace(" ", "").replace(",", "")
    if not isfinite(float(normalized)):
        raise CnloerParseError("nonfinite monthly production value")
    return normalized


def _validate_modal_headers(rows, year):
    if len(rows) < 4 or rows[1] != ["Oil", "Gas", "Water"]:
        raise CnloerParseError("unexpected production columns")
    # C-NLOER Statistical Information, pshf97–pshf01 header rows,
    # https://www.cnloer.ca/information/statistics/ (opened 2026-10-19).
    grouping = [" ".join(cell.split()) for cell in rows[0][2:]]
    details = [" ".join(cell.split()) for cell in rows[3]]
    if grouping != ["Production", "Amendment Date*"] or details != ["Monthly Details"]:
        raise CnloerParseError("unexpected production section header")
    if [re.sub(r"\s+", "", c) for c in rows[2]] != ["m3", "103m3", "m3"]:
        raise CnloerParseError("unsupported production units")
    expected_header = ["Year", "Month"] if year < 2000 else ["Year/Month", "Reservoir"]
    headers = rows[0][:2]
    if year == 2000 and headers == ["Year/Month", "Reservoir**"]:
        headers = ["Year/Month", "Reservoir"]
    if headers != expected_header:
        raise CnloerParseError("unexpected production period columns")


def _modal_monthly_lines(rows, year):
    _validate_modal_headers(rows, year)
    months, lines = set(), []
    current_month, reservoirs = None, []
    cumulative = False
    for cells in rows[4:]:
        if not cells:
            raise CnloerParseError("empty production row")
        if cells[0].startswith("Cumulative"):
            cumulative = True
        if cumulative:
            continue
        cells = cells.copy()
        if year < 2000 and cells[0].isdigit():
            if int(cells.pop(0)) != year:
                raise CnloerParseError("production year does not match modal")
        month = _month_to_int(cells[0])
        if year < 2000:
            if month is None or len(cells) != 5:
                raise CnloerParseError("malformed monthly production row")
            values = cells[1:4]
        else:
            if month is not None:
                if current_month is not None and reservoirs != [
                    "Hibernia",
                    "Avalon",
                    "Total",
                ]:
                    raise CnloerParseError("missing reservoir total")
                current_month, reservoirs = month, []
                cells.pop(0)
            if current_month is None or len(cells) != 5:
                raise CnloerParseError("malformed reservoir production row")
            reservoirs.append(cells[0])
            values = cells[1:4]
            # Validate subrows but select the published Total, without summing it twice.
            for value in values:
                _modal_number(value)
            if cells[0] != "Total":
                continue
            month = current_month
        if month in months:
            raise CnloerParseError("duplicate monthly production period")
        months.add(month)
        lines.append(f"{month} {year} " + " ".join(_modal_number(v) for v in values))
    if year >= 2000 and reservoirs != ["Hibernia", "Avalon", "Total"]:
        raise CnloerParseError("missing reservoir total")
    if months != set(range(1, 13)):
        raise CnloerParseError("missing monthly production period")
    return lines


def parse_cnloer_production_html(html: str, *, field_name: str) -> pd.DataFrame:
    """Parse supplied Hibernia 1997–2001 modals; no source data is retained.

    Source: C-NLOER Statistical Information, pshf97–pshf01 modal tables,
    https://www.cnloer.ca/information/statistics/ (opened 2026-10-13).
    Headers specify oil/water m3 and gas thousand m3. The existing PDF
    conversions are reused. Published reservoir totals take precedence over
    subrows; cumulative rows are excluded. All twelve months are required.
    """
    if field_name != FIELD_CODES["h"]:
        raise CnloerParseError("historical HTML tables cover Hibernia only")
    parser = _ModalTables()
    parser.feed(html)
    parser.close()
    lines = []
    for year in range(1997, 2002):
        identifier = f"pshf{year % 100:02d}"
        if identifier not in parser.tables:
            raise CnloerParseError(f"missing production modal {identifier}")
        # Text parser expects a month name, followed by year and metric volumes.
        for line in _modal_monthly_lines(parser.tables[identifier], year):
            month, rest = line.split(" ", 1)
            name = next(
                name for name, number in _MONTHS.items() if number == int(month)
            )
            lines.append(f"{name} {rest}")
    out = parse_cnloer_production_text("\n".join(lines), field_name=field_name)
    volumes = out[["oil_bbl", "gas_mcf", "water_bbl"]]
    if not all(isfinite(value) for value in volumes.to_numpy().flat):
        raise CnloerParseError("nonfinite converted production volume")
    return out


class CnloerProductionLoader:
    """Reads a C-NLOER field PDF (or injected text) -> long loader rows.

    Dependency-injected ``raw_text`` (pre-extracted ``pdftotext`` output) is used
    for tests; otherwise ``path`` is read via ``pdftotext -layout``.
    Optional ``raw_html`` supplies the historical Hibernia statistics modals;
    PDF periods retain their original values on overlap. The runtime
    download path (fetch + gitignored cache) is a documented #719 follow-on and
    is NOT exercised in tests nor committed with cached PDFs (licence).
    """

    def __init__(
        self,
        *,
        field_name: str,
        path: Optional[Path] = None,
        raw_text: Optional[str] = None,
        raw_html: Optional[str] = None,
    ):
        self.field_name = field_name
        self._path = path
        self._raw_text = raw_text
        self._raw_html = raw_html

    def load(self) -> pd.DataFrame:
        historical = None
        if self._raw_html is not None:
            historical = parse_cnloer_production_html(
                self._raw_html, field_name=self.field_name
            )
            if self._raw_text is None and self._path is None:
                return historical
        text = (
            self._raw_text
            if self._raw_text is not None
            else self._pdftotext(self._path)
        )
        existing = parse_cnloer_production_text(text, field_name=self.field_name)
        if historical is None:
            return existing
        return (
            pd.concat([existing, historical], ignore_index=True)
            .drop_duplicates(["year", "month"], keep="first")
            .sort_values(["year", "month"])
            .reset_index(drop=True)
        )

    @staticmethod
    def _pdftotext(path: Optional[Path]) -> str:
        import subprocess

        if path is None:
            raise CnloerParseError("no path or raw_text provided to loader")
        return subprocess.check_output(
            ["pdftotext", "-layout", str(path), "-"], text=True
        )


class CnloerFixtureLoader:
    """Loader facade over the committed labeled-synthetic offshore fixture.

    The fixture is SYNTHETIC (not derived real C-NLOER volumes) so nothing
    licence-restricted enters git; it exists to make the DI-default adapter path
    non-empty and deterministic. Real parsing is covered by
    ``parse_cnloer_production_text`` tests over inline synthetic PDF text.
    """

    def __init__(
        self,
        *,
        path=DEFAULT_FIXTURE_CSV,
        metadata_path=DEFAULT_METADATA_JSON,
    ):
        self._path = path
        self._metadata_path = metadata_path

    def load_all_production(self) -> pd.DataFrame:
        return pd.read_csv(self._path)

    def load_field_production(self, field_name: str) -> pd.DataFrame:
        frame = self.load_all_production()
        mask = frame["field_name"].astype(str).str.lower() == field_name.lower()
        return frame[mask].copy()

    def metadata(self) -> dict:
        with self._metadata_path.open(encoding="utf-8") as fh:
            return json.load(fh)
