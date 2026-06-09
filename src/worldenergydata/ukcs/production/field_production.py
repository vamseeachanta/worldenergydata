"""Monthly and annual UKCS field production loader with unit conversions.

NSTA CSV columns (raw):
  FieldName, Year, Month,
  OilProduction (Thousand Tonnes),
  GasProduction (MMscf),
  WaterProduction (Thousand Tonnes)

Unit conversions applied on load:
  Oil / Water: thousand tonnes → bbl  (1 tonne ≈ 7.33 bbl)
  Gas:         MMscf → Mcf            (1 MMscf = 1000 Mcf)
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
            field, year, month, oil_bbl, gas_mcf, water_bbl
        """
        if raw.empty:
            return pd.DataFrame(
                columns=["field", "year", "month", "oil_bbl", "gas_mcf", "water_bbl"]
            )

        result = pd.DataFrame()
        result["field"] = (
            _column(raw, _RAW_FIELD_COL, _PPRS_FIELD_COL).str.upper().str.strip()
        )
        result["year"] = _column(raw, _RAW_YEAR_COL, _PPRS_YEAR_COL).astype(int)
        result["month"] = _column(raw, _RAW_MONTH_COL, _PPRS_MONTH_COL).astype(int)

        if _RAW_OIL_COL in raw.columns:
            # Legacy fixture: thousand tonnes → bbl
            result["oil_bbl"] = raw[_RAW_OIL_COL].fillna(0.0) * 1000.0 * TONNES_TO_BBL
        else:
            # Current PPRS schema: tonnes → bbl
            result["oil_bbl"] = raw[_PPRS_OIL_TONNES_COL].fillna(0.0) * TONNES_TO_BBL

        if _RAW_GAS_COL in raw.columns:
            # Legacy fixture: MMscf → Mcf
            result["gas_mcf"] = raw[_RAW_GAS_COL].fillna(0.0) * MMSCF_TO_MCF
        else:
            # Current PPRS schema: associated + dry gas KSm3 → Mcf
            gas_ksm3 = raw.get(_PPRS_ASSOC_GAS_KSM3_COL, 0.0).fillna(0.0)
            gas_ksm3 += raw.get(_PPRS_DRY_GAS_KSM3_COL, 0.0).fillna(0.0)
            result["gas_mcf"] = gas_ksm3 * GasUnits.SM3_TO_SCF

        if _RAW_WATER_COL in raw.columns:
            # Legacy fixture: thousand tonnes → bbl
            result["water_bbl"] = (
                raw[_RAW_WATER_COL].fillna(0.0) * 1000.0 * TONNES_TO_BBL
            )
        else:
            # Current PPRS schema: m3 → bbl
            result["water_bbl"] = (
                raw[_PPRS_WATER_M3_COL].fillna(0.0) * WaterUnits.M3_TO_BBL
            )

        return result.reset_index(drop=True)

    def filter_field(self, df: pd.DataFrame, field_name: str) -> pd.DataFrame:
        """Return rows for a specific field (case-insensitive)."""
        return df[df["field"] == field_name.upper().strip()].copy()

    def filter_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Return rows for a specific calendar year."""
        return df[df["year"] == year].copy()

    def annual_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sum monthly records to annual totals per field.

        Returns
        -------
        pd.DataFrame
            Columns: field, year, oil_bbl, gas_mcf, water_bbl
        """
        if df.empty:
            return pd.DataFrame(
                columns=["field", "year", "oil_bbl", "gas_mcf", "water_bbl"]
            )

        numeric = ["oil_bbl", "gas_mcf", "water_bbl"]
        annual = df.groupby(["field", "year"])[numeric].sum().reset_index()
        return annual


def _column(raw: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in raw.columns:
            return raw[name]
    raise KeyError(names[0])
