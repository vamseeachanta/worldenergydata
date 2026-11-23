# ABOUTME: Marine safety data query API — thin wrappers over existing analysis layer.
# ABOUTME: Provides IncidentsQuery for cross-database incident search and analytics.

"""Marine safety incident query API.

Thin wrappers over the existing :class:`CrossDatabaseAnalyzer` that provide a
clean, discoverable interface for programmatic consumers.

Usage::

    import worldenergydata as wed

    # Query marine safety incidents
    df = wed.marine_safety_api.incidents.query(source="maib", year=2022)
    df = wed.marine_safety_api.incidents.query(
        vessel_type="tanker", start_year=2020, end_year=2023
    )

    # Get trend analysis
    trends = wed.marine_safety_api.incidents.trends(df)

    # Get top incident types
    top = wed.marine_safety_api.incidents.top_types(df, n=5)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.common.query_api import FilterSpec, TypedQuery


class IncidentsQuery(TypedQuery):
    """Query marine safety incidents across multiple databases.

    Wraps :class:`~worldenergydata.marine_safety.cross_database.CrossDatabaseAnalyzer`
    with a simpler, filter-oriented interface. Uses built-in synthetic data
    by default; pass ``importer_config`` for live data.

    Re-expressed on :class:`~worldenergydata.common.query_api.TypedQuery`
    (workspace-hub#3286): the singular/plural collapse + single-year shorthand
    are now declared via ``filters`` and handled by the base ``_normalize``;
    behavior is byte-for-byte preserved (see
    ``tests/marine_safety/test_api_on_base.py``).

    Examples
    --------
    >>> from worldenergydata.marine_safety.api import IncidentsQuery
    >>> iq = IncidentsQuery()
    >>> df = iq.query(source="maib")
    >>> df = iq.query(vessel_type="tanker", start_year=2020)
    """

    query_id = "marine_safety.incidents"
    filters = [
        FilterSpec("sources", "source", "list"),
        FilterSpec("vessel_types", "vessel_type", "list"),
        FilterSpec("incident_types", "incident_type", "list"),
        FilterSpec("regions", "region", "list"),
        FilterSpec("years", None, "year"),
    ]
    result_columns = [
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

    def __init__(
        self,
        importer_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the incidents query interface.

        Parameters
        ----------
        importer_config : dict, optional
            Configuration for live data importers. Keys are source names
            (``"maib"``, ``"imo"``, ``"tsb"``); values are dicts of
            importer kwargs. When not provided, the analyzer uses
            built-in synthetic/sample data.

            Example::

                IncidentsQuery(importer_config={
                    "maib": {"occurrences_file": Path("maib.csv")},
                })
        """
        from worldenergydata.marine_safety.cross_database import (
            CrossDatabaseAnalyzer,
        )

        self._analyzer = CrossDatabaseAnalyzer(importer_config=importer_config)

    def query(
        self,
        *,
        source: Optional[str] = None,
        sources: Optional[List[str]] = None,
        year: Optional[int] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        vessel_type: Optional[str] = None,
        vessel_types: Optional[List[str]] = None,
        incident_type: Optional[str] = None,
        incident_types: Optional[List[str]] = None,
        region: Optional[str] = None,
        regions: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Query marine safety incidents with optional filters.

        All filters are combined with AND logic. Omitting all filters
        returns the full dataset.

        Parameters
        ----------
        source : str, optional
            Single source to filter on (e.g. ``"maib"``, ``"imo"``,
            ``"emsa"``, ``"tsb"``).
        sources : list of str, optional
            Multiple sources to include.
        year : int, optional
            Single year to filter on (shorthand for start_year=end_year=year).
        start_year : int, optional
            Earliest year to include (inclusive).
        end_year : int, optional
            Latest year to include (inclusive).
        vessel_type : str, optional
            Single vessel type (e.g. ``"tanker"``, ``"fishing"``).
        vessel_types : list of str, optional
            Multiple vessel types.
        incident_type : str, optional
            Single incident type (e.g. ``"collision"``, ``"grounding"``).
        incident_types : list of str, optional
            Multiple incident types.
        region : str, optional
            Single region (e.g. ``"north_sea"``, ``"atlantic"``).
        regions : list of str, optional
            Multiple regions.
        **kwargs
            Reserved for future filter parameters.

        Returns
        -------
        pd.DataFrame
            Incidents matching the filters with columns: ``source``,
            ``incident_id``, ``date``, ``incident_type``, ``vessel_type``,
            ``region``, ``fatalities``, ``injuries``, ``severity``,
            ``description``.

        Examples
        --------
        >>> iq = IncidentsQuery()
        >>> df = iq.query(source="maib", year=2022)
        >>> df = iq.query(vessel_type="tanker", start_year=2020, end_year=2023)
        >>> df = iq.query(incident_types=["collision", "grounding"])
        """
        # Keep an explicit-keyword signature (existing tests introspect it) but
        # delegate the singular/plural + year normalization to the shared base.
        return self._execute(
            self._normalize(
                source=source,
                sources=sources,
                year=year,
                start_year=start_year,
                end_year=end_year,
                vessel_type=vessel_type,
                vessel_types=vessel_types,
                incident_type=incident_type,
                incident_types=incident_types,
                region=region,
                regions=regions,
                **kwargs,
            )
        )

    def _execute(self, normalized: Dict[str, Any]) -> pd.DataFrame:
        """Run the cross-database incident query from a normalized filter dict."""
        from worldenergydata.marine_safety.cross_database import (
            CrossDatabaseQuery,
        )

        q = CrossDatabaseQuery(
            sources=normalized["sources"] or ["maib", "imo", "emsa", "tsb"],
            incident_types=normalized["incident_types"],
            vessel_types=normalized["vessel_types"],
            start_year=normalized["start_year"],
            end_year=normalized["end_year"],
            regions=normalized["regions"],
        )

        result = self._analyzer.query(q)
        return result.data

    def trends(self, data: pd.DataFrame) -> pd.DataFrame:
        """Year-over-year incident counts by source and incident type.

        Parameters
        ----------
        data : pd.DataFrame
            Incident data (typically from :meth:`query`).

        Returns
        -------
        pd.DataFrame
            Columns: ``year``, ``source``, ``incident_type``, ``count``.

        Examples
        --------
        >>> iq = IncidentsQuery()
        >>> df = iq.query()
        >>> trends = iq.trends(df)
        """
        return self._analyzer.trend_analysis(data)

    def top_types(self, data: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """Top-n incident types by total count across all sources.

        Parameters
        ----------
        data : pd.DataFrame
            Incident data (typically from :meth:`query`).
        n : int, default 10
            Number of top types to return.

        Returns
        -------
        pd.DataFrame
            Columns: ``incident_type``, ``count``. Sorted descending.

        Examples
        --------
        >>> iq = IncidentsQuery()
        >>> df = iq.query()
        >>> top5 = iq.top_types(df, n=5)
        """
        return self._analyzer.top_incident_types(data, n=n)

    def correlations(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Compute cross-source correlation metrics.

        Parameters
        ----------
        data : pd.DataFrame
            Incident data (typically from :meth:`query`).

        Returns
        -------
        dict
            Keys: ``incident_type_severity``, ``vessel_type_region``,
            ``source_overlap_rate``, ``trend_yoy``.

        Examples
        --------
        >>> iq = IncidentsQuery()
        >>> df = iq.query()
        >>> corr = iq.correlations(df)
        >>> print(f"Overlap rate: {corr['source_overlap_rate']:.1%}")
        """
        return self._analyzer.correlations(data)

    def risk_hotspots(self, data: pd.DataFrame) -> pd.DataFrame:
        """Region x incident_type occurrence count matrix.

        Parameters
        ----------
        data : pd.DataFrame
            Incident data (typically from :meth:`query`).

        Returns
        -------
        pd.DataFrame
            Indexed by region with incident_type columns. Cell values
            are incident counts.

        Examples
        --------
        >>> iq = IncidentsQuery()
        >>> df = iq.query()
        >>> hotspots = iq.risk_hotspots(df)
        """
        return self._analyzer.risk_hotspots(data)


# Module-level singleton instance for convenience attribute access
incidents = IncidentsQuery()
