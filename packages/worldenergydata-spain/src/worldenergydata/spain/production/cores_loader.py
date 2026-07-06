"""Spain CORES per-field monthly production loader (#763a — ingest).

Parses the CORES "Indigenous Crude Oil / Natural Gas Production" workbooks
(https://www.cores.es/en/estadisticas) into the unified loader columns
(field_name/year/month/oil_bbl OR gas_mcf).

Real CORES layout (codex-verified 2026-07-04): WIDE, long-in-time —
  Year | Month | <field cols…> | Grand total
one row per (year, month); Spanish month names in the ES tab, English in the EN
export; annual ``Total``/``total`` rows and no-year tail rows are interleaved.
OIL unit = metric TONNES; GAS unit = GWh (energy).

The read_excel I/O is a thin wrapper; the testable core is ``parse_cores_frame``
(pure DataFrame transform: filter → melt → convert), so it unit-tests without a
committed binary fixture.
"""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, Optional, cast

import pandas as pd

from worldenergydata.spain.production.cores_density import (
    CoresDensityCoverageError,
    CoresOilConversionAudit,
)

# --- documented conversion constants (review B1) ---------------------------
# Oil: metric tonnes of crude → barrels. Default ~34° API light crude
# (7.33 bbl/tonne). Per-field density/API override is a follow-on; Ayoluengo
# crude is heavier, so this default is explicitly approximate.
TONNES_TO_BBL = 7.33
# Gas: GWh (energy) → Mcf. Via HHV ~1037 Btu/scf: 1 Mcf ≈ 1.037 MMBtu ≈
# 3.039e-4 GWh → 1 GWh ≈ 3290 Mcf.
GWH_TO_MCF = 3290.0

_MONTHS = {
    # Spanish
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    # English (EN export)
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
}

# Non-field columns present in the workbooks.
_YEAR_COLS = {"año", "year"}
_MONTH_COLS = {"mes", "month"}
_TOTAL_COLS = {"grand total", "total general"}
_DATA_ROOT = files("worldenergydata.spain").joinpath("data/cores")
DEFAULT_FIXTURE_CSV = _DATA_ROOT.joinpath("ayoluengo_oil_sample.csv")
DEFAULT_METADATA_JSON = _DATA_ROOT.joinpath("_metadata.json")


class CoresParseError(ValueError):
    """Raised when a CORES frame cannot be parsed."""


def _month_to_int(m: object) -> Optional[int]:
    return _MONTHS.get(str(m).strip().lower())


def parse_cores_frame(
    raw: pd.DataFrame,
    *,
    product: str,
    oil_conversion_audit: CoresOilConversionAudit | None = None,
) -> pd.DataFrame:
    """Pure transform: wide CORES frame → long loader rows.

    Args:
        raw: workbook rows with a year col (Año/Year), a month col (Mes/Month),
            per-field value columns, and a grand-total column.
        product: ``"oil"`` (tonnes→bbl → ``oil_bbl``) or ``"gas"`` (GWh→Mcf →
            ``gas_mcf``).
        oil_conversion_audit: optional cited/defaulted oil conversion audit.

    Returns:
        DataFrame ``[field_name, year, month, <oil_bbl|gas_mcf>]`` — only real
        monthly rows (annual ``Total`` rows and no-year tail rows dropped), only
        non-null field values.
    """
    if product not in ("oil", "gas"):
        raise CoresParseError(f"product must be 'oil'|'gas', got {product!r}")

    year_col, month_col, field_cols = _frame_columns(raw)
    monthly = _monthly_rows(raw, year_col, month_col)
    long = _melt_field_values(monthly, field_cols)
    return _parsed_output(long, product, oil_conversion_audit)


def _frame_columns(raw: pd.DataFrame) -> tuple[Any, Any, list[Any]]:
    cols = {str(c).strip().lower(): c for c in raw.columns}
    year_col = next((cols[c] for c in _YEAR_COLS if c in cols), None)
    month_col = next((cols[c] for c in _MONTH_COLS if c in cols), None)
    if year_col is None or month_col is None:
        raise CoresParseError(f"missing Year/Month columns; have {list(raw.columns)}")
    field_cols = [c for c in raw.columns if _is_field_column(c)]
    if not field_cols:
        raise CoresParseError("no field columns found")
    return year_col, month_col, field_cols


def _is_field_column(column: object) -> bool:
    return str(column).strip().lower() not in (_YEAR_COLS | _MONTH_COLS | _TOTAL_COLS)


def _monthly_rows(raw: pd.DataFrame, year_col: Any, month_col: Any) -> pd.DataFrame:
    df = raw.copy()
    df["_year"] = pd.to_numeric(df[year_col], errors="coerce")
    df = df[df["_year"].notna() & (df["_year"] > 0)]
    df["_month"] = df[month_col].map(_month_to_int)
    return df[df["_month"].notna()]


def _melt_field_values(df: pd.DataFrame, field_cols: list[Any]) -> pd.DataFrame:
    long = df.melt(
        id_vars=["_year", "_month"],
        value_vars=field_cols,
        var_name="field_name",
        value_name="_val",
    )
    long["_val"] = pd.to_numeric(long["_val"], errors="coerce")
    return long[long["_val"].notna()]


def _parsed_output(
    long: pd.DataFrame,
    product: str,
    oil_conversion_audit: CoresOilConversionAudit | None,
) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "field_name": long["field_name"].astype(str).str.strip().values,
            "year": long["_year"].astype(int).values,
            "month": long["_month"].astype(int).values,
            _value_column(product): (
                long["_val"] * _conversion_factor(long, product, oil_conversion_audit)
            )
            .astype(float)
            .values,
        }
    )
    return out.reset_index(drop=True)


def _value_column(product: str) -> str:
    return "oil_bbl" if product == "oil" else "gas_mcf"


def _conversion_factor(
    long: pd.DataFrame,
    product: str,
    oil_conversion_audit: CoresOilConversionAudit | None,
) -> float | pd.Series:
    if product == "gas":
        return GWH_TO_MCF
    if oil_conversion_audit is None:
        return TONNES_TO_BBL
    try:
        return long["field_name"].map(oil_conversion_audit.bbl_per_tonne_for_field)
    except CoresDensityCoverageError as exc:
        raise CoresParseError(str(exc)) from exc


class CoresProductionLoader:
    """Reads a CORES XLSX (or an injected frame) → long loader rows.

    Dependency-injected ``raw_frame`` (a pre-read DataFrame) is used for tests;
    otherwise ``path`` is read via ``pd.read_excel`` with CORES' default
    production-sheet header row (row 6, ``header_row=5``).
    """

    def __init__(
        self,
        *,
        product: str,
        path: Optional[Path] = None,
        raw_frame: Optional[pd.DataFrame] = None,
        header_row: int = 5,
        sheet_name: Any = 0,
        oil_conversion_audit: CoresOilConversionAudit | None = None,
    ) -> None:
        self.product = product
        self._path = path
        self._raw = raw_frame
        self._header_row = header_row
        self._sheet_name = sheet_name
        self._oil_conversion_audit = oil_conversion_audit

    def load(self) -> pd.DataFrame:
        raw = (
            self._raw
            if self._raw is not None
            else pd.read_excel(
                self._path,
                sheet_name=self._sheet_name,
                header=self._header_row,
            )
        )
        return parse_cores_frame(
            raw,
            product=self.product,
            oil_conversion_audit=self._oil_conversion_audit,
        )


class CoresFixtureProductionLoader:
    """Loader facade over the committed direct-source Ayoluengo fixture."""

    def __init__(
        self,
        *,
        path: Any = DEFAULT_FIXTURE_CSV,
        metadata_path: Any = DEFAULT_METADATA_JSON,
    ) -> None:
        self._path = path
        self._metadata_path = metadata_path

    def load_all_production(self) -> pd.DataFrame:
        return pd.read_csv(self._path)

    def load_field_production(self, field_name: str) -> pd.DataFrame:
        frame = self.load_all_production()
        mask = frame["field_name"].astype(str).str.lower() == field_name.lower()
        return frame[mask].copy()

    def metadata(self) -> dict[str, Any]:
        with self._metadata_path.open(encoding="utf-8") as fh:
            return cast(dict[str, Any], json.load(fh))
