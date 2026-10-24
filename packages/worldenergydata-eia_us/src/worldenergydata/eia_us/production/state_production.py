"""Monthly crude + NGL production by US state (EIA-914 / state series).

EIA series format: PET.MCRFP{XX}2.M  where XX = two-letter state code.
Input units must be declared; rates are integrated over each calendar month.

Major producing states covered:
  TX, ND, NM, CO, AK, WY, OK, CA, WV, OH, PA, LA
"""

import logging
from typing import Any

import pandas as pd

from .measurement import (
    RATE,
    VOLUME,
    annual_volumes,
    declared_unit,
    monthly_period,
    number_or_missing,
)

logger = logging.getLogger(__name__)

# Two-letter codes for the 12 major crude-producing states
MAJOR_PRODUCING_STATES: list[str] = [
    "TX",  # Permian / Eagle Ford
    "ND",  # Bakken
    "NM",  # Permian (NM side) / San Juan
    "CO",  # DJ Basin (Niobrara)
    "AK",  # North Slope
    "WY",  # Powder River Basin
    "OK",  # Anadarko / SCOOP-STACK
    "CA",  # San Joaquin
    "WV",  # Appalachian
    "OH",  # Utica / Marcellus
    "PA",  # Marcellus
    "LA",  # Haynesville / GoM associated
]


def STATE_SERIES_ID(state_code: str) -> str:
    """Return EIA series ID for monthly crude production in a given state.

    Args:
        state_code: Two-letter US state abbreviation (case-insensitive).

    Returns:
        EIA series ID string e.g. 'PET.MCRFPTX2.M'.
    """
    code = state_code.upper().strip()
    return f"PET.MCRFP{code}2.M"


class StateProductionLoader:
    """Load and normalise EIA state-level monthly crude production data."""

    def load(
        self,
        records: list[dict[str, Any]],
        state: str,
    ) -> pd.DataFrame:
        """Convert raw EIA API records to normalised state production DataFrame.

        Args:
            records: List of dicts with 'period', 'value', 'unit' keys,
                     as returned by EIAApiClient.parse_series_response().
            state: Two-letter state code (stored uppercase in output).

        Returns:
            DataFrame with columns: state, year, month, crude_bbl.
            Empty DataFrame (same columns) if records is empty.
        """
        cols = [
            "state",
            "year",
            "month",
            "crude_bbl",
            "value_missing",
            "unit",
            "basis",
            "input_unit",
            "input_basis",
        ]
        rows = []
        for rec in records:
            unit, scale, basis = declared_unit(rec)
            year, month, days = monthly_period(rec.get("period"))
            value = number_or_missing(rec.get("value"))
            # NIST SP 811 (2008), sections 4 and 7.11: scale, then q * time.
            volume = number_or_missing(value * scale * (days if basis == RATE else 1))
            rows.append(
                {
                    "state": state.upper().strip(),
                    "year": year,
                    "month": month,
                    "crude_bbl": volume,
                    "value_missing": pd.isna(value),
                    "unit": "bbl",
                    "basis": VOLUME,
                    "input_unit": unit,
                    "input_basis": basis,
                }
            )
        return pd.DataFrame(rows, columns=cols)

    def annual_total(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return calendar-year bbl; missing months make the total unknown.

        ``reported_crude_bbl`` is a partial subtotal, not an annual estimate.
        ``crude_missing_months`` enumerates absent and null calendar months.
        """
        if not df.empty and (
            not df["unit"].eq("bbl").all() or not df["basis"].eq(VOLUME).all()
        ):
            raise ValueError("Annual aggregation requires monthly volume unit/basis")
        return annual_volumes(df, "state", ["crude_bbl"])

    def filter_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Return rows for a specific calendar year."""
        return df[df["year"] == year].copy()

    def filter_state(self, df: pd.DataFrame, state_code: str) -> pd.DataFrame:
        """Return rows for a specific state (case-insensitive)."""
        return df[df["state"] == state_code.upper().strip()].copy()
