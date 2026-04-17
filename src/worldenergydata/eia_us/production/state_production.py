"""Monthly crude + NGL production by US state (EIA-914 / state series).

EIA series format: PET.MCRFP{XX}2.M  where XX = two-letter state code.
Unit in API: Thousand Barrels (Mbbl) — converted to barrels (bbl) on load.

Major producing states covered:
  TX, ND, NM, CO, AK, WY, OK, CA, WV, OH, PA, LA
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Two-letter codes for the 12 major crude-producing states
MAJOR_PRODUCING_STATES: List[str] = [
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


def STATE_SERIES_ID(state_code: str) -> str:  # noqa: N802
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

    # Thousand Barrels → Barrels
    _KBBL_TO_BBL: float = 1_000.0

    def load(
        self,
        records: List[Dict[str, Any]],
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
        _cols = ["state", "year", "month", "crude_bbl"]

        if not records:
            return pd.DataFrame(columns=_cols)

        rows = []
        state_upper = state.upper().strip()
        for rec in records:
            period = rec.get("period", "")
            try:
                year, month = int(period[:4]), int(period[5:7])
            except (ValueError, IndexError):
                logger.warning("Skipping record with unparseable period: %s", period)
                continue

            raw_value = rec.get("value")
            if raw_value is None:
                crude_bbl = None
            else:
                crude_bbl = float(raw_value) * self._KBBL_TO_BBL

            rows.append(
                {
                    "state": state_upper,
                    "year": year,
                    "month": month,
                    "crude_bbl": crude_bbl,
                }
            )

        if not rows:
            return pd.DataFrame(columns=_cols)

        return pd.DataFrame(rows)[_cols].reset_index(drop=True)

    def annual_total(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate monthly records to annual totals per state.

        Returns:
            DataFrame with columns: state, year, crude_bbl.
        """
        if df.empty:
            return pd.DataFrame(columns=["state", "year", "crude_bbl"])

        return df.groupby(["state", "year"])["crude_bbl"].sum().reset_index()

    def filter_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Return rows for a specific calendar year."""
        return df[df["year"] == year].copy()

    def filter_state(self, df: pd.DataFrame, state_code: str) -> pd.DataFrame:
        """Return rows for a specific state (case-insensitive)."""
        return df[df["state"] == state_code.upper().strip()].copy()
