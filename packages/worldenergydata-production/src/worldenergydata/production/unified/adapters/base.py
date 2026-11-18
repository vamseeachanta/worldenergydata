"""Abstract base class for all regional production adapters.

Each concrete adapter wraps a specific data source (SODIR, BSEE, ANP, …)
and is responsible for returning a normalised DataFrame that conforms to
``STANDARD_COLUMNS`` defined in ``query.py``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

import pandas as pd

from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery


class AbstractProductionAdapter(ABC):
    """Interface every regional production adapter must implement.

    Class attributes:
        region (str): Canonical region key, e.g. ``"ncs"``.  Must be
            unique across all adapters registered with RegionRouter.

    All ``fetch()`` implementations must return a DataFrame whose columns
    are exactly ``STANDARD_COLUMNS`` (order does not matter, but names do).
    Missing numeric columns must be ``float`` with ``NaN`` for absent data.
    """

    region: str  # set on each concrete subclass

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def fetch(self, query: ProductionQuery) -> pd.DataFrame:
        """Return normalised production data for this region.

        Args:
            query: The caller's query.  Adapters must honour ``fields``,
                ``start``, and ``end`` where possible.

        Returns:
            DataFrame with all columns from ``STANDARD_COLUMNS``.
        """
        ...

    @abstractmethod
    def available_fields(self) -> List[str]:
        """Return the list of field names this adapter can serve."""
        ...

    @abstractmethod
    def date_range(self) -> Tuple[str, str]:
        """Return the earliest and latest periods available as ``"YYYY-MM"``."""
        ...

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    def _empty_frame(self) -> pd.DataFrame:
        """Return an empty DataFrame with the standard schema."""
        return pd.DataFrame(columns=list(STANDARD_COLUMNS))

    @staticmethod
    def _filter_by_date(
        df: pd.DataFrame,
        start: Optional[str],
        end: Optional[str],
    ) -> pd.DataFrame:
        """Apply year/month filters based on ``start`` and ``end`` strings.

        Args:
            df: DataFrame that has ``year`` (int) and ``month`` (int) columns.
            start: ``"YYYY-MM"`` inclusive lower bound, or ``None``.
            end: ``"YYYY-MM"`` inclusive upper bound, or ``None``.

        Returns:
            Filtered DataFrame (original index preserved).
        """
        if df.empty:
            return df

        period = (df["year"] * 100 + df["month"]).reset_index(drop=True)
        df = df.reset_index(drop=True)

        if start:
            y, m = start.split("-")
            period_start = int(y) * 100 + int(m)
            df = df[period >= period_start]
            period = period[period >= period_start]

        if end:
            y, m = end.split("-")
            period_end = int(y) * 100 + int(m)
            df = df[period <= period_end]

        return df

    @staticmethod
    def _filter_by_fields(
        df: pd.DataFrame,
        fields: Optional[List[str]],
    ) -> pd.DataFrame:
        """Restrict rows to the requested field names.

        Comparison is case-insensitive.

        Args:
            df: DataFrame with ``field_name`` column.
            fields: List of field names, or ``None`` to skip filtering.

        Returns:
            Filtered DataFrame.
        """
        if not fields or df.empty:
            return df

        normalised = {f.lower() for f in fields}
        mask = df["field_name"].str.lower().isin(normalised)
        return df[mask]
