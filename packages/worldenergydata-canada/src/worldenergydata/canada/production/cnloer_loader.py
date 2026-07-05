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
from importlib.resources import files
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


class CnloerProductionLoader:
    """Reads a C-NLOER field PDF (or injected text) -> long loader rows.

    Dependency-injected ``raw_text`` (pre-extracted ``pdftotext`` output) is used
    for tests; otherwise ``path`` is read via ``pdftotext -layout``. The runtime
    download lane (fetch + gitignored cache) is a documented #719 follow-on and
    is NOT exercised in tests nor committed with cached PDFs (licence).
    """

    def __init__(
        self,
        *,
        field_name: str,
        path: Optional[Path] = None,
        raw_text: Optional[str] = None,
    ):
        self.field_name = field_name
        self._path = path
        self._raw_text = raw_text

    def load(self) -> pd.DataFrame:
        text = (
            self._raw_text
            if self._raw_text is not None
            else self._pdftotext(self._path)
        )
        return parse_cnloer_production_text(text, field_name=self.field_name)

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
