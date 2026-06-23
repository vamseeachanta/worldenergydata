# ABOUTME: MetoceanQuery, MetoceanResult, UnifiedMetoceanClient — unified query interface.
# ABOUTME: Auto-selects clients by coverage, runs in parallel, returns harmonised DataFrame.

"""
Unified Metocean Query Interface

Provides a single interface to query multiple metocean data sources
simultaneously based on geographic coverage rules.

Usage:
    client = UnifiedMetoceanClient()
    query = MetoceanQuery(
        lat=28.5, lon=-88.5,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
    )
    result = client.query(query)
    logger.info(result.data.head())
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.metocean.unified.coverage import MetoceanCoverage
from worldenergydata.metocean.unified.harmonizer import MetoceanHarmonizer

logger = logging.getLogger(__name__)

# Default parameters to query when none are specified
_DEFAULT_PARAMETERS = ("Hs", "Tp", "wind_speed", "current_speed")

# Source priority for ordering (lower = higher priority)
_SOURCE_PRIORITY = {
    "ndbc": 0,
    "coops": 0,
    "met_norway": 1,
    "open_meteo": 2,
    "erddap": 3,
}


@dataclass
class MetoceanQuery:
    """
    Specification for a unified metocean data query.

    Attributes:
        lat:        Target latitude (decimal degrees)
        lon:        Target longitude (decimal degrees)
        start_date: Start of time range (inclusive)
        end_date:   End of time range (inclusive)
        parameters: List of standard parameter names to fetch
                    (Hs, Tp, Tm, wind_speed, wind_dir, current_speed, current_dir)
    """

    lat: float
    lon: float
    start_date: datetime
    end_date: datetime
    parameters: tuple = _DEFAULT_PARAMETERS


@dataclass
class MetoceanResult:
    """
    Result container for a unified metocean query.

    Attributes:
        query:         The original query that produced this result
        data:          Long-format DataFrame (columns: timestamp, parameter, value, source, unit)
        sources_used:  List of source names that contributed data
        coverage_gaps: List of gap descriptors (period + param with no data)
    """

    query: MetoceanQuery
    data: pd.DataFrame
    sources_used: List[str]
    coverage_gaps: List[Dict[str, Any]] = field(default_factory=list)


class UnifiedMetoceanClient:
    """
    Unified client that queries multiple metocean data sources in parallel.

    Automatically selects relevant clients based on geographic coverage,
    fetches data concurrently, harmonises variable names and units, and
    returns a single MetoceanResult with a standardised long-format DataFrame.

    Source priority: measured (NDBC, CO-OPS) > reanalysis (Met Norway) >
                     forecast (OpenMeteo) > fallback (ERDDAP)

    Example:
        client = UnifiedMetoceanClient()
        query = MetoceanQuery(lat=28.5, lon=-88.5,
                              start_date=datetime(2023,1,1),
                              end_date=datetime(2023,1,31))
        result = client.query(query)
        logger.info(result.data)
    """

    def __init__(self, max_workers: int = 5) -> None:
        """
        Initialise the unified client.

        Args:
            max_workers: Maximum number of parallel threads for data fetching
        """
        self._coverage = MetoceanCoverage()
        self._harmonizer = MetoceanHarmonizer()
        self._max_workers = max_workers

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def query(self, q: MetoceanQuery) -> MetoceanResult:
        """
        Execute a unified metocean query across all applicable sources.

        Steps:
            1. Determine which sources cover the coordinates (coverage.py)
            2. Fetch data from each source in parallel (ThreadPoolExecutor)
            3. Harmonise each result (harmonizer.py)
            4. Merge all harmonised DataFrames
            5. Detect coverage gaps
            6. Return MetoceanResult

        Args:
            q: MetoceanQuery with location, time range, and parameters

        Returns:
            MetoceanResult containing merged data and metadata
        """
        selected_sources = self._coverage.get_clients(q.lat, q.lon)
        logger.info(f"Query ({q.lat}, {q.lon}): selected sources {selected_sources}")

        # Parallel fetch
        source_dataframes: Dict[str, pd.DataFrame] = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self._fetch_from_source, src, q): src
                for src in selected_sources
            }
            for future in as_completed(futures):
                src = futures[future]
                try:
                    df = future.result()
                    source_dataframes[src] = df
                    logger.debug(f"Source {src} returned {len(df)} rows")
                except Exception as exc:
                    logger.warning(f"Source {src} failed: {exc}")
                    source_dataframes[src] = pd.DataFrame(
                        columns=["timestamp", "parameter", "value", "source", "unit"]
                    )

        # Merge and align
        all_dfs = list(source_dataframes.values())
        merged = self._harmonizer.merge_sources(all_dfs)

        if not merged.empty:
            merged = self._harmonizer.align_to_hourly_grid(merged)

        # Determine which sources actually contributed rows
        if merged.empty:
            sources_used = sorted(selected_sources)
        else:
            sources_used = sorted(merged["source"].unique().tolist())
            # Also include sources that were selected (even if they returned nothing)
            # so that coverage gap detection knows what was attempted
            for src in selected_sources:
                if src not in sources_used:
                    sources_used.append(src)
            sources_used = sorted(
                sources_used,
                key=lambda s: _SOURCE_PRIORITY.get(s, 99),
            )

        gaps = self._detect_gaps(merged, q)

        return MetoceanResult(
            query=q,
            data=merged,
            sources_used=sources_used,
            coverage_gaps=gaps,
        )

    # ------------------------------------------------------------------
    # Per-source fetch dispatch
    # ------------------------------------------------------------------

    def _fetch_from_source(
        self, source_name: str, query: MetoceanQuery
    ) -> pd.DataFrame:
        """
        Fetch and harmonise data from a single named source.

        This method is the unit-testable seam — tests can mock it to inject
        pre-built DataFrames without any HTTP calls.

        Args:
            source_name: One of 'ndbc', 'coops', 'open_meteo', 'met_norway', 'erddap'
            query:       The MetoceanQuery to execute

        Returns:
            Harmonised long-format DataFrame (may be empty)
        """
        try:
            if source_name == "ndbc":
                return self._fetch_ndbc(query)
            if source_name == "coops":
                return self._fetch_coops(query)
            if source_name == "open_meteo":
                return self._fetch_open_meteo(query)
            if source_name == "met_norway":
                return self._fetch_met_norway(query)
            if source_name == "erddap":
                return self._fetch_erddap(query)
        except Exception as exc:
            logger.warning(f"_fetch_from_source({source_name}) raised: {exc}")

        return pd.DataFrame(
            columns=["timestamp", "parameter", "value", "source", "unit"]
        )

    # ------------------------------------------------------------------
    # Source-specific fetch helpers (each isolates one client)
    # ------------------------------------------------------------------

    def _fetch_ndbc(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from NDBC client and harmonise."""
        from worldenergydata.metocean.clients.ndbc_client import NDBCClient

        # Find the nearest NDBC buoy by fetching station list and picking closest
        with NDBCClient() as client:
            stations_result = client.fetch_stations()
            station = _nearest_station(
                stations_result.data,
                query.lat,
                query.lon,
                lat_attr="latitude",
                lon_attr="longitude",
                id_attr="station_id",
            )
            if station is None:
                return pd.DataFrame(
                    columns=["timestamp", "parameter", "value", "source", "unit"]
                )

            result = client.fetch_historical(
                station_id=station["station_id"],
                start_date=query.start_date,
                end_date=query.end_date,
            )

        obs_dicts = [
            vars(obs) if hasattr(obs, "__dict__") else obs for obs in result.data
        ]
        return self._harmonizer.harmonize_ndbc(obs_dicts)

    def _fetch_coops(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from CO-OPS client and harmonise."""
        from worldenergydata.metocean.clients.coops_client import COOPSClient

        with COOPSClient() as client:
            stations_result = client.fetch_stations()
            station = _nearest_station(
                stations_result.data,
                query.lat,
                query.lon,
                lat_attr="latitude",
                lon_attr="longitude",
                id_attr="station_id",
            )
            if station is None:
                return pd.DataFrame(
                    columns=["timestamp", "parameter", "value", "source", "unit"]
                )

            # Try currents first, fall back to water level
            try:
                result = client.fetch_currents(
                    station_id=station["station_id"],
                    start_date=query.start_date,
                    end_date=query.end_date,
                )
                obs_dicts = [
                    vars(obs) if hasattr(obs, "__dict__") else obs
                    for obs in result.data
                ]
                return self._harmonizer.harmonize_coops_current(obs_dicts)
            except Exception:
                result = client.fetch_water_level(
                    station_id=station["station_id"],
                    start_date=query.start_date,
                    end_date=query.end_date,
                )
                obs_dicts = [
                    vars(obs) if hasattr(obs, "__dict__") else obs
                    for obs in result.data
                ]
                return self._harmonizer.harmonize_coops_water_level(obs_dicts)

    def _fetch_open_meteo(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from OpenMeteo client and harmonise."""
        from worldenergydata.metocean.clients.open_meteo_client import OpenMeteoClient

        with OpenMeteoClient() as client:
            result = client.fetch_historical(
                latitude=query.lat,
                longitude=query.lon,
                start_date=query.start_date,
                end_date=query.end_date,
            )

        obs_dicts = [
            vars(obs) if hasattr(obs, "__dict__") else obs for obs in result.data
        ]
        return self._harmonizer.harmonize_open_meteo(obs_dicts)

    def _fetch_met_norway(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from Met Norway client and harmonise."""
        from worldenergydata.metocean.clients.met_norway_client import MetNorwayClient

        with MetNorwayClient() as client:
            result = client.fetch_combined_forecast(
                latitude=query.lat,
                longitude=query.lon,
            )

        obs_dicts = [
            vars(obs) if hasattr(obs, "__dict__") else obs for obs in result.data
        ]
        return self._harmonizer.harmonize_met_norway(obs_dicts)

    def _fetch_erddap(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from ERDDAP client and harmonise (global fallback)."""
        from worldenergydata.metocean.clients.erddap_client import ERDDAPClient

        with ERDDAPClient(server="ioos") as client:
            result = client.fetch_tabledap(
                dataset_id="ioos_gliders",
                start_time=query.start_date,
                end_time=query.end_date,
                bbox=(query.lon - 1, query.lon + 1, query.lat - 1, query.lat + 1),
            )

        obs_dicts = [
            vars(obs) if hasattr(obs, "__dict__") else obs for obs in result.data
        ]
        return self._harmonizer.harmonize_erddap(obs_dicts)

    # ------------------------------------------------------------------
    # Gap detection
    # ------------------------------------------------------------------

    def _detect_gaps(
        self, df: pd.DataFrame, query: MetoceanQuery
    ) -> List[Dict[str, Any]]:
        """
        Identify time periods or parameters with no data coverage.

        Args:
            df:    Merged harmonised DataFrame
            query: Original query

        Returns:
            List of gap descriptors, each with keys:
                parameter, start, end, sources_missing
        """
        gaps: List[Dict[str, Any]] = []

        if df.empty:
            gaps.append(
                {
                    "parameter": "all",
                    "start": query.start_date.isoformat(),
                    "end": query.end_date.isoformat(),
                    "sources_missing": "all",
                }
            )
            return gaps

        for param in query.parameters:
            param_df = df[df["parameter"] == param]
            if param_df.empty:
                gaps.append(
                    {
                        "parameter": param,
                        "start": query.start_date.isoformat(),
                        "end": query.end_date.isoformat(),
                        "sources_missing": "all",
                    }
                )

        return gaps


# ---------------------------------------------------------------------------
# Utility: nearest station lookup
# ---------------------------------------------------------------------------


def _nearest_station(
    stations: list,
    lat: float,
    lon: float,
    lat_attr: str = "latitude",
    lon_attr: str = "longitude",
    id_attr: str = "station_id",
) -> Optional[Dict[str, Any]]:
    """
    Return the station closest to (lat, lon) as a dict, or None if empty.

    Uses simple Euclidean distance in degree-space (adequate for station
    selection; haversine not needed here).

    Args:
        stations:  List of station dataclass objects
        lat:       Target latitude
        lon:       Target longitude
        lat_attr:  Attribute name for station latitude
        lon_attr:  Attribute name for station longitude
        id_attr:   Attribute name for station identifier

    Returns:
        Dict with at least {id_attr: value} or None
    """
    if not stations:
        return None

    best = None
    best_dist = float("inf")

    for s in stations:
        s_lat = getattr(s, lat_attr, None)
        s_lon = getattr(s, lon_attr, None)
        if s_lat is None or s_lon is None:
            continue
        dist = (s_lat - lat) ** 2 + (s_lon - lon) ** 2
        if dist < best_dist:
            best_dist = dist
            best = s

    if best is None:
        return None

    result: Dict[str, Any] = {}
    for attr in [id_attr, lat_attr, lon_attr]:
        result[attr] = getattr(best, attr, None)
    return result


# Make Optional importable from this module (used in type hints above)
