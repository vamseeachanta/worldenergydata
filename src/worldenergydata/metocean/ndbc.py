# ABOUTME: NDBC buoy data ingestion for metocean wave scatter matrices (WRK-316).
# ABOUTME: Downloads and processes NOAA NDBC standard meteorological data.
"""
NDBC Buoy Data Ingestion — Public Facade

Provides a high-level API for NDBC buoy data ingestion including:
- NDBCClient: HTTP client with convenience methods for station lists, stdmet,
  and historical data with parquet caching.
- parse_stdmet_line: Parse a single NDBC stdmet text line into a dict.
- build_scatter_matrix: Build an Hs/Tp scatter matrix from records.
- filter_by_season: Filter a DataFrame to specific calendar months.

Example usage::

    client = NDBCClient()
    stations = client.get_station_list()
    df = client.get_stdmet("41001", year=2023, month=1)
    matrix = build_scatter_matrix(df.to_dict("records"), normalize=True)
"""

from __future__ import annotations

import io
import gzip
import logging
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from worldenergydata.metocean.clients.ndbc_client import (
    NDBCClient as _BaseNDBCClient,
    NDBCObservation,
    NDBCStation,
)
from worldenergydata.metocean.constants import NDBC_BASE_URL, NDBC_MISSING_VALUES

logger = logging.getLogger(__name__)

# Default Hs and Tp bin edges for scatter matrices
_DEFAULT_HS_BINS: List[float] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
_DEFAULT_TP_BINS: List[float] = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]

# Local cache directory for parquet files
_CACHE_DIR = pathlib.Path.home() / ".cache" / "worldenergydata" / "ndbc"


# ---------------------------------------------------------------------------
# Standalone parsing helpers
# ---------------------------------------------------------------------------

def parse_stdmet_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse one line from an NDBC standard meteorological text file.

    Comment lines (starting with ``#``) and lines with fewer than 5
    whitespace-separated tokens return ``None``.

    Column mapping (NDBC stdmet format):
        0: YY, 1: MM, 2: DD, 3: hh, 4: mm,
        5: WDIR, 6: WSPD, 7: GST, 8: WVHT (hs),
        9: DPD (dominant period), 10: APD (average period),
        11: MWD, 12: PRES, 13: ATMP, 14: WTMP, 15: DEWP,
        16: VIS, 17: PTDY, 18: TIDE

    Returns:
        dict with keys ``observation_time``, ``hs``, ``dpd``, ``apd``,
        ``mwd``, ``wtmp``, ``wdir``, ``wspd``, ``gst``, ``pres``,
        ``atmp``, ``dewp``, ``vis``, ``ptdy``, ``tide``; values may
        be ``None`` when the sensor reported a missing-value sentinel.
    """
    if not line or line.startswith("#"):
        return None

    parts = line.split()
    if len(parts) < 5:
        return None

    def _val(idx: int) -> Optional[float]:
        if idx >= len(parts):
            return None
        raw = parts[idx]
        if raw in NDBC_MISSING_VALUES:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = int(parts[3])
        minute = int(parts[4])
    except (ValueError, IndexError):
        return None

    # Handle 2-digit years (legacy NDBC format)
    if year < 100:
        year = 2000 + year if year < 50 else 1900 + year

    try:
        obs_time = datetime(year, month, day, hour, minute)
    except ValueError:
        return None

    return {
        "observation_time": obs_time,
        "wdir": _val(5),
        "wspd": _val(6),
        "gst": _val(7),
        "hs": _val(8),     # WVHT — significant wave height (m)
        "dpd": _val(9),    # DPD — dominant wave period (s)
        "apd": _val(10),   # APD — average wave period (s)
        "mwd": _val(11),   # MWD — mean wave direction (deg)
        "pres": _val(12),
        "atmp": _val(13),
        "wtmp": _val(14),  # Water temperature (°C)
        "dewp": _val(15),
        "vis": _val(16),
        "ptdy": _val(17),
        "tide": _val(18),
    }


# ---------------------------------------------------------------------------
# Scatter matrix
# ---------------------------------------------------------------------------

def build_scatter_matrix(
    records: Sequence[Dict[str, Any]],
    hs_bins: Optional[Sequence[float]] = None,
    tp_bins: Optional[Sequence[float]] = None,
    normalize: bool = False,
) -> np.ndarray:
    """
    Build a 2-D Hs/Tp wave scatter matrix from a sequence of record dicts.

    Each record must contain ``"hs"`` and ``"tp"`` keys (floats or None).
    Records missing either key or containing ``None`` are silently skipped.
    Records whose values fall outside the bin range are also skipped.

    Args:
        records: Sequence of dicts with ``"hs"`` and ``"tp"`` float values.
        hs_bins: Monotonically increasing bin edges for Hs (m).
                 Defaults to 0–10 m in 1 m steps.
        tp_bins: Monotonically increasing bin edges for Tp (s).
                 Defaults to 0–20 s in 2 s steps.
        normalize: If True, divide counts by the total so entries sum to 1.0.

    Returns:
        numpy.ndarray of shape ``(len(hs_bins)-1, len(tp_bins)-1)``.
        Row index corresponds to Hs bins; column index to Tp bins.
    """
    hs_edges = np.asarray(hs_bins if hs_bins is not None else _DEFAULT_HS_BINS)
    tp_edges = np.asarray(tp_bins if tp_bins is not None else _DEFAULT_TP_BINS)

    n_hs = len(hs_edges) - 1
    n_tp = len(tp_edges) - 1
    matrix = np.zeros((n_hs, n_tp), dtype=float)

    for rec in records:
        hs = rec.get("hs")
        tp = rec.get("tp")
        if hs is None or tp is None:
            continue
        try:
            hs = float(hs)
            tp = float(tp)
        except (TypeError, ValueError):
            continue

        i_hs = int(np.searchsorted(hs_edges, hs, side="right")) - 1
        i_tp = int(np.searchsorted(tp_edges, tp, side="right")) - 1

        if 0 <= i_hs < n_hs and 0 <= i_tp < n_tp:
            matrix[i_hs, i_tp] += 1.0

    if normalize:
        total = matrix.sum()
        if total > 0:
            matrix = matrix / total

    return matrix


# ---------------------------------------------------------------------------
# Seasonal filtering
# ---------------------------------------------------------------------------

def filter_by_season(
    df: pd.DataFrame,
    months: List[int],
    time_col: str = "time",
) -> pd.DataFrame:
    """
    Filter a DataFrame to rows whose timestamp falls in the given months.

    Args:
        df: DataFrame containing a datetime column.
        months: List of integer month numbers (1=January … 12=December).
        time_col: Name of the datetime column. Defaults to ``"time"``.

    Returns:
        Filtered DataFrame (copy). Returns empty DataFrame if ``months``
        is empty or no rows match.
    """
    if not months:
        return df.iloc[0:0].copy()

    mask = df[time_col].dt.month.isin(months)
    return df.loc[mask].copy()


# ---------------------------------------------------------------------------
# Extended NDBCClient facade
# ---------------------------------------------------------------------------

class NDBCClient(_BaseNDBCClient):
    """
    Extended NDBC client with convenience methods and parquet caching.

    Adds:
    - ``get_station_list()`` — returns station dicts with lat/lon.
    - ``get_stdmet(station_id, year, month)`` — downloads and caches stdmet
      data as a pandas DataFrame.
    - ``get_historical(station_id, year)`` — downloads full-year historical
      data as a DataFrame.

    Caches downloaded data to ``~/.cache/worldenergydata/ndbc/`` as parquet
    files to avoid repeated downloads.

    All other methods from the base :class:`~worldenergydata.metocean.clients
    .ndbc_client.NDBCClient` are available unchanged.
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
            List of dicts each containing at minimum:
            ``station_id``, ``name``, ``latitude``, ``longitude``.
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

        Fetches real-time data (last 45 days) when ``month`` is None,
        otherwise fetches historical data for the specified year. Results
        are cached locally as parquet files.

        Args:
            station_id: NDBC station identifier (e.g., ``"41001"``).
            year: Year of data to retrieve.
            month: Optional month (1–12). When provided, fetches the
                   historical archive for that year; otherwise fetches
                   realtime data.

        Returns:
            DataFrame with columns: ``observation_time``, ``hs``, ``dpd``,
            ``apd``, ``mwd``, ``wtmp``, ``wdir``, ``wspd``, ``gst``,
            ``pres``, ``atmp``, ``dewp``, ``vis``, ``ptdy``, ``tide``.
            Rows with no timestamp are dropped. May be empty if no data
            is available.
        """
        cache_key = f"{station_id}_{year}"
        if month is not None:
            cache_key += f"_{month:02d}"
        cache_path = _CACHE_DIR / f"{cache_key}.parquet"

        if cache_path.exists():
            logger.debug("Loading cached stdmet from %s", cache_path)
            return pd.read_parquet(cache_path)

        # Fetch via realtime or historical endpoint
        start = datetime(year, month or 1, 1)
        end = datetime(year, month or 12, 31, 23, 59)
        result = self.fetch_historical(station_id, start, end)
        df = self._observations_to_dataframe(result.data)

        # Cache if data was retrieved
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

        Equivalent to :meth:`get_stdmet` without a month argument. Caches
        the result as a parquet file.

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
        """
        Convert a list of NDBCObservation objects to a DataFrame.

        Maps dataclass attributes to the stdmet column naming convention
        used by :func:`parse_stdmet_line`.

        Args:
            observations: List of :class:`NDBCObservation` instances.

        Returns:
            pandas DataFrame; empty if the list is empty.
        """
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
    "parse_stdmet_line",
]
