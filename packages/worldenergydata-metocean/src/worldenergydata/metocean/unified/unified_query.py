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
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from typing import Any

import pandas as pd

from worldenergydata.metocean.unified.coverage import MetoceanCoverage
from worldenergydata.metocean.unified.harmonizer import MetoceanHarmonizer

logger = logging.getLogger(__name__)

# Default parameters to query when none are specified
_DEFAULT_PARAMETERS = ("Hs", "Tp", "wind_speed", "current_speed")

# Native units are the existing client dataclass contract (clients/*.py).
PARAMETER_UNITS = {
    "Hs": "m",
    "Tp": "s",
    "Tm": "s",
    "wave_dir": "deg",
    "wind_speed": "m/s",
    "wind_dir": "deg",
    "current_speed": "m/s",
    "current_dir": "deg",
    "sst": "degC",
    "water_level": "m",
}
SOURCES = ("ndbc", "coops", "met_norway", "open_meteo", "erddap", "era5", "cmems")


class SourceNotEvaluated(RuntimeError):
    """A source needs explicit dataset or adapter configuration."""


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

    def __post_init__(self) -> None:
        # RFC 5870 (2010), sections 3.3 and 3.4.2: angular coordinate bounds.
        if not isfinite(self.lat) or not -90 <= self.lat <= 90:
            raise ValueError("latitude must be finite and between -90 and 90")
        if not isfinite(self.lon) or not -180 <= self.lon <= 180:
            raise ValueError("longitude must be finite and between -180 and 180")
        # Naive timestamps are interpreted as UTC, as in existing clients.
        self.start_date = (
            pd.to_datetime(self.start_date, utc=True).tz_localize(None).to_pydatetime()
        )
        self.end_date = (
            pd.to_datetime(self.end_date, utc=True).tz_localize(None).to_pydatetime()
        )
        if pd.isna(self.start_date) or pd.isna(self.end_date):
            raise ValueError("dates must be valid timestamps")
        if self.start_date > self.end_date:
            raise ValueError("start date must not follow end date")
        self.parameters = tuple(self.parameters)
        if not self.parameters or set(self.parameters) - PARAMETER_UNITS.keys():
            raise ValueError("parameters must be nonempty standard parameter names")


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
    sources_used: list[str]
    coverage_gaps: list[dict[str, Any]] = field(default_factory=list)
    source_status: dict[str, str] = field(default_factory=dict)


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

    def __init__(
        self,
        max_workers: int = 4,
        *,
        source_fetchers: (
            Mapping[str, Callable[[MetoceanQuery], pd.DataFrame]] | None
        ) = None,
        erddap_dataset: str | None = None,
        erddap_bbox: tuple | None = None,
    ) -> None:
        """Configure optional adapters returning the documented long-table schema.

        ERA5/CMEMS adapters own authenticated SDK access and dataset-specific
        decoding; they must return the native units in PARAMETER_UNITS.
        No credentials are read by this aggregation layer. Worker count is a
        scheduling choice, not an engineering coefficient or acceptance limit.
        """
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self._coverage = MetoceanCoverage()
        self._harmonizer = MetoceanHarmonizer()
        self._max_workers = max_workers
        self._source_fetchers = dict(source_fetchers or {})
        if set(self._source_fetchers) - set(SOURCES):
            raise ValueError("unknown source adapter")
        if erddap_bbox is not None:
            # RFC 5870 (2010), section 3.4.2; ordering is the ERDDAP
            # client fetch_tabledap bbox contract, not a coverage threshold.
            if len(erddap_bbox) != 4:
                raise ValueError("ERDDAP bounds require four coordinates")
            west, east, south, north = erddap_bbox
            if not all(isfinite(v) for v in erddap_bbox) or not (
                -180 <= west <= east <= 180 and -90 <= south <= north <= 90
            ):
                raise ValueError("ERDDAP bounds must be ordered valid coordinates")
        self._erddap_dataset = erddap_dataset
        self._erddap_bbox = erddap_bbox

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
            4. Filter and merge observations without interpolation
            5. Detect coverage gaps
            6. Return MetoceanResult

        Args:
            q: MetoceanQuery with location, time range, and parameters

        Returns:
            MetoceanResult containing merged data and metadata
        """
        selected_sources = self._coverage.get_clients(q.lat, q.lon)
        logger.info(f"Query ({q.lat}, {q.lon}): selected sources {selected_sources}")

        source_dataframes: dict[str, pd.DataFrame] = {}
        status = {}
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self._fetch_from_source, src, q): src
                for src in selected_sources
            }
            for future in as_completed(futures):
                src = futures[future]
                error = future.exception()
                if isinstance(error, SourceNotEvaluated):
                    status[src] = "NOT_EVALUATED"
                    continue
                if error is not None:
                    # Never publish exception bodies: SDK errors can carry credentials.
                    logger.warning("Source %s failed", src)
                    status[src] = "FAILED"
                    continue
                try:
                    df = self._filter_data(future.result(), q, src)
                except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                    logger.warning("Source %s returned invalid observations", src)
                    status[src] = "FAILED"
                    continue
                source_dataframes[src] = df
                status[src] = "EMPTY" if df.empty else "OK"

        # Preserve actual observation times: no interpolation across missing data.
        merged = self._harmonizer.merge_sources(
            [
                source_dataframes[src]
                for src in selected_sources
                if src in source_dataframes
            ]
        )
        if not merged.empty:
            merged = merged.sort_values(
                ["source", "timestamp", "parameter"]
            ).reset_index(drop=True)
        sources_used = sorted(merged["source"].unique().tolist())
        return MetoceanResult(
            query=q,
            data=merged,
            sources_used=sources_used,
            coverage_gaps=self._detect_gaps(merged, q),
            source_status={src: status[src] for src in selected_sources},
        )

    def _filter_data(
        self, df: pd.DataFrame, q: MetoceanQuery, source: str
    ) -> pd.DataFrame:
        """Enforce UTC, finite values, requested units, and inclusive bounds."""
        df = df.copy()
        if not {"timestamp", "parameter", "value", "source", "unit"}.issubset(df):
            raise ValueError("adapter must return the long-table schema")
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], utc=True, errors="coerce", format="mixed"
        )
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df[
            df["timestamp"].between(
                pd.Timestamp(q.start_date, tz="UTC"), pd.Timestamp(q.end_date, tz="UTC")
            )
            & df["parameter"].isin(q.parameters)
            & df["value"].map(isfinite)
        ].copy()
        if (
            not df.empty
            and not df["unit"].eq(df["parameter"].map(PARAMETER_UNITS)).all()
        ):
            raise ValueError(
                "adapter units do not match the standard parameter contract"
            )
        df["source"] = source
        # Keep the existing naive-UTC output schema for exporters and dashboard.
        df["timestamp"] = df["timestamp"].dt.tz_localize(None)
        return df

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
        if source_name in self._source_fetchers:
            return self._source_fetchers[source_name](query)
        if source_name in {"era5", "cmems"}:
            raise SourceNotEvaluated("explicit SDK adapter required")
        methods = {
            "ndbc": self._fetch_ndbc,
            "coops": self._fetch_coops,
            "open_meteo": self._fetch_open_meteo,
            "met_norway": self._fetch_met_norway,
            "erddap": self._fetch_erddap,
        }
        return methods[source_name](query)

    # ------------------------------------------------------------------
    # Source-specific fetch helpers (each isolates one client)
    # ------------------------------------------------------------------

    def _fetch_ndbc(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from NDBC client and harmonise."""
        from worldenergydata.metocean.clients.ndbc_client import NDBCClient

        # Find the nearest NDBC buoy by fetching station list and picking closest
        with NDBCClient() as client:
            stations_result = client.fetch_stations()
            _validate_fetch_result(stations_result)
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

        obs_dicts = _observation_dicts(result)
        return self._harmonizer.harmonize_ndbc(obs_dicts)

    def _fetch_coops(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from CO-OPS client and harmonise."""
        from worldenergydata.metocean.clients.coops_client import COOPSClient

        with COOPSClient() as client:
            stations_result = client.fetch_stations()
            _validate_fetch_result(stations_result)
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

            parts = []
            if {"current_speed", "current_dir"}.intersection(query.parameters):
                result = client.fetch_currents(
                    station_id=station["station_id"],
                    start_date=query.start_date,
                    end_date=query.end_date,
                )
                obs_dicts = _observation_dicts(result)
                parts.append(self._harmonizer.harmonize_coops_current(obs_dicts))
            if "water_level" in query.parameters:
                result = client.fetch_water_level(
                    station_id=station["station_id"],
                    start_date=query.start_date,
                    end_date=query.end_date,
                )
                obs_dicts = _observation_dicts(result)
                parts.append(self._harmonizer.harmonize_coops_water_level(obs_dicts))
            return self._harmonizer.merge_sources(parts)

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

        obs_dicts = _observation_dicts(result)
        return self._harmonizer.harmonize_open_meteo(obs_dicts)

    def _fetch_met_norway(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from Met Norway client and harmonise."""
        from worldenergydata.metocean.clients.met_norway_client import MetNorwayClient

        with MetNorwayClient() as client:
            result = client.fetch_combined_forecast(
                latitude=query.lat,
                longitude=query.lon,
            )

        obs_dicts = _observation_dicts(result)
        return self._harmonizer.harmonize_met_norway(obs_dicts)

    def _fetch_erddap(self, query: MetoceanQuery) -> pd.DataFrame:
        """Fetch from ERDDAP client and harmonise (global fallback)."""
        from worldenergydata.metocean.clients.erddap_client import ERDDAPClient

        if not self._erddap_dataset or self._erddap_bbox is None:
            raise SourceNotEvaluated("explicit ERDDAP dataset and bounds required")
        with ERDDAPClient(server="ioos") as client:
            result = client.fetch_tabledap(
                dataset_id=self._erddap_dataset,
                start_time=query.start_date,
                end_time=query.end_date,
                bbox=self._erddap_bbox,
            )

        obs_dicts = _observation_dicts(result)
        return self._harmonizer.harmonize_erddap(obs_dicts)

    # ------------------------------------------------------------------
    # Gap detection
    # ------------------------------------------------------------------

    def _detect_gaps(
        self, df: pd.DataFrame, query: MetoceanQuery
    ) -> list[dict[str, Any]]:
        """
        Identify time periods or parameters with no data coverage.

        Args:
            df:    Merged harmonised DataFrame
            query: Original query

        Returns:
            List of gap descriptors, each with keys:
                parameter, start, end, sources_missing
        """
        gaps: list[dict[str, Any]] = []

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


def _validate_fetch_result(result) -> None:
    """Reject native fetch errors without exposing upstream diagnostics."""
    if getattr(result, "had_errors", False) or getattr(result, "error_messages", None):
        raise RuntimeError("source client reported a fetch error")


def _observation_dicts(result) -> list[dict[str, Any]]:
    """Do not turn explicit client failures into apparent absence of data."""
    _validate_fetch_result(result)
    return [vars(obs) if hasattr(obs, "__dict__") else obs for obs in result.data]


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
) -> dict[str, Any] | None:
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

    result: dict[str, Any] = {}
    for attr in [id_attr, lat_attr, lon_attr]:
        result[attr] = getattr(best, attr, None)
    return result


# Make Optional importable from this module (used in type hints above)
