"""Output normalizer — validates schema and fills coverage gaps.

The normalizer is the final step before a ProductionResult is returned to
callers.  It:

1. Verifies that every required column is present.
2. Casts numeric columns to ``float64``.
3. Fills missing (year, month) pairs per field with ``NaN`` rows so that
   callers can distinguish *no data* from *zero production*.
4. Builds the per-field summary DataFrame (peak, cumulative, avg_monthly).
5. Reports coverage gaps as a list of dicts.
"""

from __future__ import annotations

import logging
from typing import List

import pandas as pd

from worldenergydata.production.unified.query import STANDARD_COLUMNS

logger = logging.getLogger(__name__)

_NUMERIC_COLS = ("oil_bbl", "gas_mcf", "water_bbl", "condensate_bbl")
_REQUIRED_COLUMNS = set(STANDARD_COLUMNS)


class Normalizer:
    """Validate and normalise the merged production DataFrame."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def validate(self, df: pd.DataFrame) -> None:
        """Raise ``ValueError`` if required columns are missing.

        Args:
            df: Merged DataFrame from all adapters.

        Raises:
            ValueError: When one or more standard columns are absent.
        """
        present = set(df.columns)
        missing = _REQUIRED_COLUMNS - present
        if missing:
            raise ValueError(
                f"DataFrame is missing required columns: {sorted(missing)}"
            )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cast numeric columns and add missing rows as NaN.

        The function does *not* mutate the input; it returns a new
        DataFrame.

        Args:
            df: Merged adapter output that has passed ``validate()``.

        Returns:
            Normalised DataFrame sorted by region / field_name / year / month.
        """
        if df.empty:
            return df.copy()

        out = df.copy()

        for col in _NUMERIC_COLS:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")

        out = out.sort_values(["region", "field_name", "year", "month"]).reset_index(
            drop=True
        )

        return out

    def build_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute per-field aggregate statistics.

        Args:
            df: Normalised production DataFrame.

        Returns:
            DataFrame indexed by ``(region, field_name)`` with columns:
            ``peak_rate``, ``cumulative_oil_bbl``, ``avg_monthly_oil_bbl``,
            ``total_months``.
        """
        if df.empty:
            return pd.DataFrame(
                columns=[
                    "region",
                    "field_name",
                    "peak_rate",
                    "cumulative_oil_bbl",
                    "avg_monthly_oil_bbl",
                    "total_months",
                ]
            )

        grouped = df.groupby(["region", "field_name"])

        summary = pd.DataFrame(
            {
                "peak_rate": grouped["oil_bbl"].max(),
                "cumulative_oil_bbl": grouped["oil_bbl"].sum(),
                "avg_monthly_oil_bbl": grouped["oil_bbl"].mean(),
                "total_months": grouped["oil_bbl"].count(),
            }
        ).reset_index()

        return summary

    def find_coverage_gaps(self, df: pd.DataFrame) -> List[dict]:
        """Identify fields with gaps in their monthly time-series.

        A gap is defined as a missing (year, month) pair within the
        field's production period.  NaN rows are included in the gap
        count.

        Args:
            df: Normalised production DataFrame.

        Returns:
            List of dicts, one per field that has at least one gap::

                {
                    "region": "ncs",
                    "field_name": "Edvard Grieg",
                    "gap_months": 3,
                }
        """
        if df.empty:
            return []

        gaps: List[dict] = []

        for (region, field), group in df.groupby(["region", "field_name"]):
            # Build expected contiguous range
            min_period = group["year"].min() * 12 + group["month"].min()
            max_period = group["year"].max() * 12 + group["month"].max()
            expected_count = max_period - min_period + 1
            actual_count = len(group)
            gap_months = expected_count - actual_count

            if gap_months > 0:
                gaps.append(
                    {
                        "region": region,
                        "field_name": field,
                        "gap_months": gap_months,
                    }
                )

        return gaps
