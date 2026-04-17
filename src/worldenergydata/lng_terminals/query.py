"""
ABOUTME: Queryable interface for global LNG terminal dataset.
ABOUTME: LngTerminalQuery + LngTerminalClient for agent-callable access.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from worldenergydata.lng_terminals._dataset import TERMINALS

# ---------------------------------------------------------------------------
# Query dataclasses
# ---------------------------------------------------------------------------


@dataclass
class LngTerminalQuery:
    """Filter parameters for querying the LNG terminal dataset.

    All fields are optional.  Omitting a field returns all values for that
    dimension.  List fields use OR semantics within the field and AND
    semantics across fields.

    Attributes:
        region: Geographic regions to include (e.g. ["asia_pacific", "europe"]).
        country: ISO-2 country codes or full names (e.g. ["US", "AU"]).
        terminal_type: Terminal function types (e.g. ["import", "export"]).
        status: Lifecycle statuses (e.g. ["operational", "under_construction"]).
        min_capacity_mtpa: Lower bound on nameplate capacity (MTPA, inclusive).
        max_capacity_mtpa: Upper bound on nameplate capacity (MTPA, inclusive).
    """

    region: Optional[list[str]] = None
    country: Optional[list[str]] = None
    terminal_type: Optional[list[str]] = None
    status: Optional[list[str]] = None
    min_capacity_mtpa: Optional[float] = None
    max_capacity_mtpa: Optional[float] = None


@dataclass
class LngTerminalResult:
    """Result of an LNG terminal query.

    Attributes:
        data: Filtered DataFrame with all terminal columns.
        query: The original query used to produce this result.
        total_count: Number of matching terminals.
        total_capacity_mtpa: Sum of capacity_mtpa across matching terminals.
    """

    data: pd.DataFrame
    query: LngTerminalQuery
    total_count: int
    total_capacity_mtpa: float


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LngTerminalClient:
    """Agent-callable client for the built-in global LNG terminal dataset.

    The dataset is loaded once at construction time from the module-level
    TERMINALS constant in _dataset.py.  All query operations are in-memory
    pandas operations; no network calls are made.

    Columns present in every result DataFrame:
        terminal_name, country, region, type, status, capacity_mtpa,
        operator, year_commissioned, latitude, longitude, source.
    """

    def __init__(self) -> None:
        self._df: pd.DataFrame = pd.DataFrame(TERMINALS)

    def query(self, q: LngTerminalQuery) -> LngTerminalResult:
        """Return terminals matching the supplied filter.

        Args:
            q: Query filter parameters.

        Returns:
            LngTerminalResult with filtered DataFrame and capacity summary.
        """
        mask = pd.Series([True] * len(self._df), index=self._df.index)

        if q.region:
            lower = [r.lower() for r in q.region]
            mask &= self._df["region"].str.lower().isin(lower)

        if q.country:
            lower = [c.lower() for c in q.country]
            mask &= self._df["country"].str.lower().isin(lower)

        if q.terminal_type:
            lower = [t.lower() for t in q.terminal_type]
            mask &= self._df["type"].str.lower().isin(lower)

        if q.status:
            lower = [s.lower() for s in q.status]
            mask &= self._df["status"].str.lower().isin(lower)

        if q.min_capacity_mtpa is not None:
            mask &= self._df["capacity_mtpa"] >= q.min_capacity_mtpa

        if q.max_capacity_mtpa is not None:
            mask &= self._df["capacity_mtpa"] <= q.max_capacity_mtpa

        filtered = self._df[mask].reset_index(drop=True)
        total_cap = float(filtered["capacity_mtpa"].sum())

        return LngTerminalResult(
            data=filtered,
            query=q,
            total_count=len(filtered),
            total_capacity_mtpa=total_cap,
        )

    def list_regions(self) -> list[str]:
        """Return all distinct region values present in the dataset."""
        return sorted(self._df["region"].dropna().unique().tolist())

    def list_countries(self) -> list[str]:
        """Return all distinct country values present in the dataset."""
        return sorted(self._df["country"].dropna().unique().tolist())

    def summary_by_region(self) -> pd.DataFrame:
        """Aggregate terminal count and total capacity by region.

        Returns:
            DataFrame with columns: region, count, total_capacity_mtpa.
        """
        return (
            self._df.groupby("region")
            .agg(
                count=("terminal_name", "count"),
                total_capacity_mtpa=("capacity_mtpa", "sum"),
            )
            .reset_index()
        )
