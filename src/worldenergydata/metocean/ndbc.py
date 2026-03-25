# ABOUTME: NDBC buoy data ingestion facade (WRK-316).
# ABOUTME: Re-exports analysis helpers and provides NDBCClient with caching.
"""
NDBC Buoy Data Ingestion — Public Facade

Provides a high-level API for NDBC buoy data ingestion:
- NDBCClient: HTTP client with convenience methods and parquet caching.
- parse_stdmet_line / parse_stdmet_file: Text-format parsers.
- build_scatter_matrix: Hs/Tp scatter matrix builder.
- filter_by_season: Calendar-month filter for DataFrames.
- fit_weibull_hs: 2- or 3-parameter Weibull fit for Hs data.
- wave_rose: Directional Hs breakdown by sector.

Pure analysis functions live in :mod:`worldenergydata.metocean.ndbc_analysis`.

Example usage::

    client = NDBCClient()
    df = client.get_historical("41001", year=2023)
    matrix = build_scatter_matrix(df.to_dict("records"), normalize=True)
    params = fit_weibull_hs(df["hs"].dropna().tolist(), n_params=2)
    rose = wave_rose(df.to_dict("records"))
"""

from __future__ import annotations

import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.metocean.clients.ndbc_client import (
    NDBCClient as _BaseNDBCClient,
    NDBCObservation,
    NDBCStation,
)
from worldenergydata.metocean.constants import NDBC_BASE_URL  # noqa: F401
from worldenergydata.metocean.ndbc_analysis import (
    build_scatter_matrix,
    filter_by_season,
    fit_weibull_hs,
    parse_stdmet_file,
    parse_stdmet_line,
    wave_rose,
)

logger = logging.getLogger(__name__)

# Local cache directory for parquet files
_CACHE_DIR = pathlib.Path.home() / ".cache" / "worldenergydata" / "ndbc"


class NDBCClient(_BaseNDBCClient):
    """
    Extended NDBC client with convenience methods and parquet caching.

    Adds:
    - ``get_station_list()`` — station dicts with id, name, lat, lon.
    - ``get_stdmet(station_id, year, month)`` — DataFrame of stdmet data.
    - ``get_historical(station_id, year)`` — full-year historical DataFrame.

    Results are cached to ``~/.cache/worldenergydata/ndbc/`` as parquet files.
    """

    def get_station_list(
        self,
        bbox: Optional[tuple] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Return a list of NDBC station dicts with id, name, lat, lon.

        Args:
            bbox: Optional bounding box (lon_min, lon_max, lat_min, lat_max).
            active_only: If True, only return currently active stations.

        Returns:
            List of dicts with ``station_id``, ``name``,
            ``latitude``, ``longitude``.
        """
        result = self.fetch_stations(bbox=bbox, active_only=active_only)
        stations = []
        for s in result.data:
            entry: Dict[str, Any] = {
                "station_id": s.station_id,
                "name": s.name,
                "latitude": s.latitude,
                "longitude": s.longitude,
            }
            if s.water_depth_m is not None:
                entry["water_depth_m"] = s.water_depth_m
            if s.owner is not None:
                entry["owner"] = s.owner
            entry["station_type"] = s.station_type.value
            stations.append(entry)
        return stations

    def get_stdmet(
        self,
        station_id: str,
        year: int,
        month: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Download NDBC standard meteorological data as a DataFrame.

        Caches results as parquet to avoid repeated downloads.

        Args:
            station_id: NDBC station identifier (e.g., ``"41001"``).
            year: Year of data to retrieve.
            month: Optional month (1–12). When given, fetches historical
                   archive for that year; otherwise fetches realtime data.

        Returns:
            DataFrame with columns: ``observation_time``, ``hs``, ``dpd``,
            ``apd``, ``mwd``, ``wtmp``, ``wdir``, ``wspd``, ``gst``,
            ``pres``, ``atmp``, ``dewp``, ``vis``, ``ptdy``, ``tide``.
        """
        cache_key = f"{station_id}_{year}"
        if month is not None:
            cache_key += f"_{month:02d}"
        cache_path = _CACHE_DIR / f"{cache_key}.parquet"

        if cache_path.exists():
            logger.debug("Loading cached stdmet from %s", cache_path)
            return pd.read_parquet(cache_path)

        start = datetime(year, month or 1, 1)
        end = datetime(year, month or 12, 31, 23, 59)
        result = self.fetch_historical(station_id, start, end)
        df = self._observations_to_dataframe(result.data)

        if not df.empty:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_parquet(cache_path, index=False)
            logger.debug("Cached stdmet to %s", cache_path)

        return df

    def get_historical(
        self,
        station_id: str,
        year: int,
    ) -> pd.DataFrame:
        """
        Download full-year historical stdmet data as a DataFrame.

        Equivalent to :meth:`get_stdmet` without a month argument.

        Args:
            station_id: NDBC station identifier.
            year: Year to retrieve.

        Returns:
            DataFrame with same columns as :meth:`get_stdmet`.
        """
        return self.get_stdmet(station_id, year, month=None)

    @staticmethod
    def _observations_to_dataframe(
        observations: List[NDBCObservation],
    ) -> pd.DataFrame:
        """Convert NDBCObservation objects to a stdmet-column DataFrame."""
        if not observations:
            return pd.DataFrame()

        rows = []
        for obs in observations:
            rows.append({
                "observation_time": obs.observation_time,
                "wdir": obs.wind_direction_deg,
                "wspd": obs.wind_speed_ms,
                "gst": obs.wind_gust_ms,
                "hs": obs.wave_height_m,
                "dpd": obs.dominant_wave_period_s,
                "apd": obs.average_wave_period_s,
                "mwd": obs.wave_direction_deg,
                "pres": obs.pressure_hpa,
                "atmp": obs.air_temp_c,
                "wtmp": obs.sea_surface_temp_c,
                "dewp": obs.dew_point_c,
                "vis": obs.visibility_nm,
                "ptdy": obs.pressure_tendency_hpa,
                "tide": obs.water_level_ft,
            })
        return pd.DataFrame(rows)


__all__ = [
    "NDBCClient",
    "NDBCObservation",
    "NDBCStation",
    "build_scatter_matrix",
    "filter_by_season",
    "fit_weibull_hs",
    "parse_stdmet_file",
    "parse_stdmet_line",
    "wave_rose",
]
