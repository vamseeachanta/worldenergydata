# ABOUTME: Cross-database marine safety incident analysis combining MAIB, IMO, EMSA, TSB.
# ABOUTME: Unified query, correlation analysis, and trend identification across 4 authorities.

"""
Cross-database marine safety incident correlation analysis.

Provides a unified query interface and analytical layer across four major
marine safety investigation authorities: MAIB (UK), IMO (international),
EMSA (European), and TSB (Canada). Uses built-in synthetic incident data
spanning 2015-2024 to support correlation and trend studies without
requiring live database access.

Public API
----------
- CrossDatabaseQuery  — filter parameters
- CrossDatabaseResult — query output (data, counts, correlations)
- CrossDatabaseAnalyzer — query, correlations, trend_analysis, top_incident_types,
                          risk_hotspots
"""

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from worldenergydata.marine_safety._cross_database_data import (
    SEVERITY_SCORES,
    SYNTHETIC_INCIDENTS,
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CrossDatabaseQuery:
    """Parameters for querying the cross-database incident store.

    All fields are optional; omitting them returns the full dataset.
    Multiple filters are combined with AND logic.
    """

    sources: list[str] = field(
        default_factory=lambda: ["maib", "imo", "emsa", "tsb"]
    )
    incident_types: Optional[list[str]] = None
    vessel_types: Optional[list[str]] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    regions: Optional[list[str]] = None


@dataclass
class CrossDatabaseResult:
    """Result of a cross-database query."""

    data: pd.DataFrame
    query: CrossDatabaseQuery
    total_incidents: int
    by_source: dict
    correlations: dict


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class CrossDatabaseAnalyzer:
    """
    Unified query and analysis layer over MAIB, IMO, EMSA, and TSB incident
    datasets.

    All methods are stateless — pass the same ``CrossDatabaseAnalyzer``
    instance across multiple queries without concern for shared state.
    """

    # Canonical column order for result DataFrames
    SCHEMA_COLUMNS: list[str] = [
        "source",
        "incident_id",
        "date",
        "incident_type",
        "vessel_type",
        "region",
        "fatalities",
        "injuries",
        "severity",
        "description",
    ]

    def _load_base(self) -> pd.DataFrame:
        """Load synthetic dataset and add derived columns."""
        df = pd.DataFrame(SYNTHETIC_INCIDENTS)
        df["year"] = pd.to_datetime(df["date"]).dt.year
        df["severity_score"] = df["severity"].map(SEVERITY_SCORES)
        return df

    def query(self, q: CrossDatabaseQuery) -> CrossDatabaseResult:
        """
        Execute a cross-database query with optional filters.

        Parameters
        ----------
        q:
            Query parameters.  Default ``CrossDatabaseQuery()`` returns all
            incidents from all four sources.

        Returns
        -------
        CrossDatabaseResult
            ``data`` contains only the canonical schema columns.
            ``by_source`` counts reflect the *filtered* dataset.
        """
        df = self._load_base()

        if q.sources:
            df = df[df["source"].isin(q.sources)]
        if q.incident_types:
            df = df[df["incident_type"].isin(q.incident_types)]
        if q.vessel_types:
            df = df[df["vessel_type"].isin(q.vessel_types)]
        if q.start_year is not None:
            df = df[df["year"] >= q.start_year]
        if q.end_year is not None:
            df = df[df["year"] <= q.end_year]
        if q.regions:
            df = df[df["region"].isin(q.regions)]

        df = df.reset_index(drop=True)

        by_source: dict = {}
        for src in q.sources or df["source"].unique().tolist():
            by_source[src] = int((df["source"] == src).sum())

        return CrossDatabaseResult(
            data=df[self.SCHEMA_COLUMNS].copy(),
            query=q,
            total_incidents=len(df),
            by_source=by_source,
            correlations={},
        )

    def correlations(self, data: pd.DataFrame) -> dict:
        """
        Compute cross-source correlation metrics.

        Parameters
        ----------
        data:
            DataFrame in the unified schema (typically ``result.data``).

        Returns
        -------
        dict with keys:
          ``incident_type_severity``
              DataFrame — mean severity score (1–5) per incident type.
          ``vessel_type_region``
              DataFrame — vessel_type × region occurrence count matrix.
          ``source_overlap_rate``
              float — share of type/year/region groups reported by 2+ sources.
          ``trend_yoy``
              DataFrame — year-over-year totals by source.
        """
        df = data.copy()
        df["year"] = pd.to_datetime(df["date"]).dt.year
        df["severity_score"] = df["severity"].map(SEVERITY_SCORES)

        # Incident type vs mean severity score
        type_sev = (
            df.groupby("incident_type")["severity_score"]
            .mean()
            .reset_index()
            .rename(columns={"severity_score": "mean_severity_score"})
            .sort_values("mean_severity_score", ascending=False)
        )

        # Vessel type × region occurrence matrix
        vt_region = (
            df.groupby(["vessel_type", "region"])
            .size()
            .unstack(fill_value=0)
        )

        # Source overlap rate — groups where 2+ sources report the same
        # incident_type / year / region combination
        overlap_key = ["incident_type", "year", "region"]
        grouped = df.groupby(overlap_key)["source"].nunique()
        overlap_count = int((grouped >= 2).sum())
        total_groups = len(grouped)
        overlap_rate = (
            overlap_count / total_groups if total_groups > 0 else 0.0
        )

        # Year-over-year totals by source
        trend = (
            df.groupby(["year", "source"])
            .size()
            .reset_index(name="count")
            .sort_values(["year", "source"])
        )

        return {
            "incident_type_severity": type_sev,
            "vessel_type_region": vt_region,
            "source_overlap_rate": float(overlap_rate),
            "trend_yoy": trend,
        }

    def trend_analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Year-over-year incident counts by source and incident type.

        Returns
        -------
        DataFrame with columns: year, source, incident_type, count.
        """
        df = data.copy()
        df["year"] = pd.to_datetime(df["date"]).dt.year
        return (
            df.groupby(["year", "source", "incident_type"])
            .size()
            .reset_index(name="count")
            .sort_values(["year", "source", "incident_type"])
        )

    def top_incident_types(
        self, data: pd.DataFrame, n: int = 10
    ) -> pd.DataFrame:
        """
        Top-n incident types by total count across all sources.

        Returns
        -------
        DataFrame with columns: incident_type, count.
        Rows are sorted descending by count.
        """
        return (
            data.groupby("incident_type")
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .head(n)
            .reset_index(drop=True)
        )

    def risk_hotspots(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Region × incident_type occurrence count matrix.

        Returns
        -------
        DataFrame indexed by region with incident_type columns.
        Cell values are incident counts (int, zero-filled).
        """
        return (
            data.groupby(["region", "incident_type"])
            .size()
            .unstack(fill_value=0)
        )
