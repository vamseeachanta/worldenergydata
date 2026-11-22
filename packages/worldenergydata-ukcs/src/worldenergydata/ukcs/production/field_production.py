"""Monthly and annual UKCS field production loader with unit conversions.

NSTA CSV columns (raw):
  FieldName, Year, Month,
  OilProduction (Thousand Tonnes),
  GasProduction (MMscf),
  WaterProduction (Thousand Tonnes)

Unit conversions applied on load:
  Oil / Water: thousand tonnes → bbl  (1 tonne ≈ 7.33 bbl)
  Gas:         MMscf → Mcf            (1 MMscf = 1000 Mcf)

PPRS volume fields are mapped separately; missing measurements remain NaN.
See docs/ukcs-production-components.html for source coverage and limitations.
"""

import logging

import pandas as pd

from worldenergydata.common.units import GasUnits, OilUnits, WaterUnits

logger = logging.getLogger(__name__)

# Backward-compatible module-level aliases (sourced from common.units)
# 1 tonne of crude oil ≈ 7.33 barrels
TONNES_TO_BBL: float = OilUnits.TONNE_TO_BBL
# 1 MMscf = 1000 Mcf
MMSCF_TO_MCF: float = GasUnits.MMSCF_TO_MCF

_RAW_OIL_COL = "OilProduction (Thousand Tonnes)"
_RAW_GAS_COL = "GasProduction (MMscf)"
_RAW_WATER_COL = "WaterProduction (Thousand Tonnes)"
_RAW_FIELD_COL = "FieldName"
_RAW_YEAR_COL = "Year"
_RAW_MONTH_COL = "Month"

_PPRS_FIELD_COL = "FIELDNAME"
_PPRS_YEAR_COL = "PERIODYR"
_PPRS_MONTH_COL = "PERIODMNTH"
_PPRS_OIL_TONNES_COL = "OILPRODMAS"
_PPRS_ASSOC_GAS_KSM3_COL = "AGASPROKSM"
_PPRS_DRY_GAS_KSM3_COL = "DGASPROKSM"
_PPRS_WATER_M3_COL = "WATPRODVOL"

# NSTA PPRS FeatureServer layer 0 field aliases, retrieved 2026-10-20:
# GCONDVOL is gas condensate (m3), not NGL or a mass/daily-rate measurement.
# NIST SP 811 Appendix B.8 (web edition 2016), petroleum-barrel and cubic-foot
# entries: inverse m3 factors, rounded in common.units. ksm3 to Mcf cancels
# the thousand prefixes. Injection, flaring and venting are separate streams.
_PPRS_COMPONENTS = {
    "condensate_bbl": ("GCONDVOL", OilUnits.M3_TO_BBL),
    "associated_gas_mcf": (_PPRS_ASSOC_GAS_KSM3_COL, GasUnits.SM3_TO_SCF),
    "dry_gas_mcf": (_PPRS_DRY_GAS_KSM3_COL, GasUnits.SM3_TO_SCF),
    "gas_injected_mcf": ("GASINJVOL", GasUnits.SM3_TO_SCF),
    "water_injected_bbl": ("INJWATVOL", WaterUnits.M3_TO_BBL),
    "water_reinjected_bbl": ("REINJWATVO", WaterUnits.M3_TO_BBL),
    "gas_flared_mcf": ("GASFLARVOL", GasUnits.SM3_TO_SCF),
    "gas_vented_mcf": ("GASVENTVOL", GasUnits.SM3_TO_SCF),
}
_VOLUME_COLUMNS = ["oil_bbl", "gas_mcf", "water_bbl", *_PPRS_COMPONENTS, "ngl_bbl"]


class UKCSFieldProductionLoader:
    """Load and normalise UKCS field-level production data from NSTA CSVs."""

    def load(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Convert raw NSTA DataFrame to normalised production records.

        Parameters
        ----------
        raw:
            DataFrame with NSTA column names (as downloaded or mocked).

        Returns
        -------
        pd.DataFrame
            Normalised production data with columns:
            field, year, month, oil_bbl, gas_mcf, water_bbl and the separate
            PPRS component columns. ngl_bbl remains unknown: no separate NGL
            field is established by the inspected PPRS schema.
        """
        if raw.empty:
            return pd.DataFrame(columns=["field", "year", "month", *_VOLUME_COLUMNS])

        result = pd.DataFrame()
        result["field"] = (
            _column(raw, _RAW_FIELD_COL, _PPRS_FIELD_COL).str.upper().str.strip()
        )
        result["year"] = _column(raw, _RAW_YEAR_COL, _PPRS_YEAR_COL).astype(int)
        result["month"] = _column(raw, _RAW_MONTH_COL, _PPRS_MONTH_COL).astype(int)

        if _RAW_OIL_COL in raw.columns:
            # Legacy fixture: thousand tonnes → bbl
            result["oil_bbl"] = _numeric(raw, _RAW_OIL_COL) * 1000.0 * TONNES_TO_BBL
        else:
            # Current PPRS schema: tonnes → bbl
            result["oil_bbl"] = _numeric(raw, _PPRS_OIL_TONNES_COL) * TONNES_TO_BBL

        for output, (source, factor) in _PPRS_COMPONENTS.items():
            result[output] = _numeric(raw, source) * factor
        result["ngl_bbl"] = float("nan")

        if _RAW_GAS_COL in raw.columns:
            # Legacy fixture: MMscf → Mcf
            result["gas_mcf"] = _numeric(raw, _RAW_GAS_COL) * MMSCF_TO_MCF
        else:
            # Current PPRS schema: associated + dry gas KSm3 → Mcf
            result["gas_mcf"] = result["associated_gas_mcf"] + result["dry_gas_mcf"]

        if _RAW_WATER_COL in raw.columns:
            # Legacy fixture: thousand tonnes → bbl
            result["water_bbl"] = _numeric(raw, _RAW_WATER_COL) * 1000.0 * TONNES_TO_BBL
        else:
            # Current PPRS schema: m3 → bbl
            result["water_bbl"] = (
                _numeric(raw, _PPRS_WATER_M3_COL) * WaterUnits.M3_TO_BBL
            )

        return result[["field", "year", "month", *_VOLUME_COLUMNS]].reset_index(
            drop=True
        )

    def filter_field(self, df: pd.DataFrame, field_name: str) -> pd.DataFrame:
        """Return rows for a specific field (case-insensitive)."""
        return df[df["field"] == field_name.upper().strip()].copy()

    def filter_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Return rows for a specific calendar year."""
        return df[df["year"] == year].copy()

    def annual_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sum observed monthly records, preserving incomplete components.

        A null in any observed month makes that component's total unknown.
        No absent months are imputed; calendar-year completeness is not asserted.

        Returns
        -------
        pd.DataFrame
            Columns: field, year and the supplied production-component columns.
        """
        if df.empty:
            return pd.DataFrame(columns=["field", "year", *_VOLUME_COLUMNS])

        numeric = [name for name in _VOLUME_COLUMNS if name in df]
        grouped = df.groupby(["field", "year"])[numeric]
        totals = grouped.sum(min_count=1)
        complete = grouped.count().eq(grouped.size(), axis="index")
        return totals.where(complete).reset_index()


def _numeric(raw: pd.DataFrame, name: str) -> pd.Series:
    """Read a numeric measurement without interpreting missing values as zero."""
    if name not in raw:
        return pd.Series(float("nan"), index=raw.index)
    return (
        pd.to_numeric(raw[name], errors="coerce")
        .astype(float)
        .replace([float("inf"), float("-inf")], float("nan"))
    )


def _column(raw: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in raw.columns:
            return raw[name]
    raise KeyError(names[0])
