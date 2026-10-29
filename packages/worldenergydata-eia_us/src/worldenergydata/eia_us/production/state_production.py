"""Monthly crude + NGL production by US state (EIA-914 / state series).

EIA series format: PET.MCRFP{XX}2.M  where XX = two-letter state code.
Unit in API: Thousand Barrels (Mbbl) — converted to barrels (bbl) on load.

Major producing states covered:
  TX, ND, NM, CO, AK, WY, OK, CA, WV, OH, PA, LA
"""

import re
from datetime import date
from typing import Any, Dict, List

import pandas as pd

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

    # Definition of the documented unit: one Thousand Barrels = 1000 bbl.
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
                     'period' must be a valid Gregorian month in YYYY-MM form;
                     'unit' must be exactly 'Thousand Barrels' (a monthly volume,
                     not a daily rate). Absent or null 'value' remains unknown.
            state: Two-letter state code (stored uppercase in output).

        Returns:
            DataFrame with columns: state, year, month, crude_bbl.
            Empty DataFrame (same columns) if records is empty.

        Raises:
            ValueError: A record has an invalid 'period' or unsupported 'unit'.
                Invalid records are rejected rather than silently omitted.
        """
        _cols = ["state", "year", "month", "crude_bbl"]

        if not records:
            return pd.DataFrame(columns=_cols)

        rows = []
        state_upper = state.upper().strip()
        for rec in records:
            period = rec.get("period")
            # YYYY-MM: four year digits and two month digits; date validates
            # Gregorian calendar bounds using the first day of that month.
            if not isinstance(period, str) or not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}", period
            ):
                raise ValueError(f"Invalid period {period!r}: expected YYYY-MM")
            try:
                month_start = date.fromisoformat(f"{period}-01")
            except ValueError as error:
                raise ValueError(
                    f"Invalid period {period!r}: expected a valid calendar month"
                ) from error

            unit = rec.get("unit")
            if not isinstance(unit, str) or unit != "Thousand Barrels":
                raise ValueError(
                    f"Invalid unit {unit!r}: expected 'Thousand Barrels' monthly volume"
                )

            raw_value = rec.get("value")
            if raw_value is None:
                crude_bbl = None
            else:
                crude_bbl = float(raw_value) * self._KBBL_TO_BBL

            rows.append(
                {
                    "state": state_upper,
                    "year": month_start.year,
                    "month": month_start.month,
                    "crude_bbl": crude_bbl,
                }
            )

        return pd.DataFrame(rows)[_cols].reset_index(drop=True)

    def annual_total(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate monthly records to annual totals per state.

        Returns:
            DataFrame with columns: state, year, crude_bbl.
            An unknown quantity in any supplied row makes that state/year total
            unknown (NaN), including groups with no known quantities. True zeros
            remain zero. Totals sum monthly volumes without rate weighting.

        Only supplied rows are aggregated. An absent month is distinct from a
        supplied row with an unknown quantity; no calendar-coverage completeness
        is inferred, so a numeric result need not represent a full year.
        """
        if df.empty:
            return pd.DataFrame(columns=["state", "year", "crude_bbl"])

        return (
            df.groupby(["state", "year"])["crude_bbl"]
            .agg(lambda values: values.sum(min_count=len(values)))
            .reset_index()
        )

    def filter_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Return rows for a specific calendar year."""
        return df[df["year"] == year].copy()

    def filter_state(self, df: pd.DataFrame, state_code: str) -> pd.DataFrame:
        """Return rows for a specific state (case-insensitive)."""
        return df[df["state"] == state_code.upper().strip()].copy()
