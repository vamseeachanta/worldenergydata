# ABOUTME: MetoceanHarmonizer — standardises variable names, units, and time to hourly UTC grid.
# ABOUTME: Converts client-specific observation dicts into a unified long-format DataFrame.

"""
MetoceanHarmonizer

Converts observations from each metocean client into a unified long-format
DataFrame with columns: timestamp, parameter, value, source, unit.

Standard parameter names:
    Hs            — significant wave height (m)
    Tp            — peak / dominant wave period (s)
    Tm            — mean wave period (s)
    wind_speed    — wind speed (m/s)
    wind_dir      — wind direction (degrees, from)
    current_speed — ocean current speed (m/s)
    current_dir   — ocean current direction (degrees)

Time alignment:
    - Continuous variables (Hs, wind_speed, …): linear interpolation to hourly grid
    - Directional variables (wind_dir, current_dir): nearest-neighbour
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

# Directional parameters — use nearest-neighbour interpolation
_DIRECTIONAL_PARAMS = {"wind_dir", "current_dir", "wave_dir"}

# Mapping from client attribute name → (standard_name, unit)
_NDBC_MAP: Dict[str, tuple[str, str]] = {
    "wave_height_m": ("Hs", "m"),
    "dominant_wave_period_s": ("Tp", "s"),
    "average_wave_period_s": ("Tm", "s"),
    "wave_direction_deg": ("wave_dir", "deg"),
    "wind_speed_ms": ("wind_speed", "m/s"),
    "wind_direction_deg": ("wind_dir", "deg"),
    "sea_surface_temp_c": ("sst", "degC"),
    "current_speed_ms": ("current_speed", "m/s"),
}

_OPEN_METEO_MAP: Dict[str, tuple[str, str]] = {
    "wave_height_m": ("Hs", "m"),
    "wave_period_s": ("Tp", "s"),
    "wave_direction_deg": ("wave_dir", "deg"),
    "wind_speed_ms": ("wind_speed", "m/s"),
    "wind_direction_deg": ("wind_dir", "deg"),
    "current_speed_ms": ("current_speed", "m/s"),
    "current_direction_deg": ("current_dir", "deg"),
    "sea_surface_temp_c": ("sst", "degC"),
}

_MET_NORWAY_MAP: Dict[str, tuple[str, str]] = {
    "wave_height_m": ("Hs", "m"),
    "wave_period_s": ("Tp", "s"),
    "wave_direction_deg": ("wave_dir", "deg"),
    "wind_speed_ms": ("wind_speed", "m/s"),
    "wind_direction_deg": ("wind_dir", "deg"),
    "current_speed_ms": ("current_speed", "m/s"),
    "current_direction_deg": ("current_dir", "deg"),
    "sea_surface_temp_c": ("sst", "degC"),
}

_COOPS_WATER_LEVEL_MAP: Dict[str, tuple[str, str]] = {
    "water_level_m": ("water_level", "m"),
}

_COOPS_CURRENT_MAP: Dict[str, tuple[str, str]] = {
    "speed_ms": ("current_speed", "m/s"),
    "direction_deg": ("current_dir", "deg"),
}

_ERDDAP_MAP: Dict[str, tuple[str, str]] = {
    "wave_height_m": ("Hs", "m"),
    "wave_period_s": ("Tp", "s"),
    "wave_direction_deg": ("wave_dir", "deg"),
    "wind_speed_ms": ("wind_speed", "m/s"),
    "wind_direction_deg": ("wind_dir", "deg"),
    "current_speed_ms": ("current_speed", "m/s"),
    "current_direction_deg": ("current_dir", "deg"),
    "sea_surface_temp_c": ("sst", "degC"),
}

_EMPTY_DF_COLUMNS = ["timestamp", "parameter", "value", "source", "unit"]


class MetoceanHarmonizer:
    """
    Converts raw client observation dicts into a unified long-format DataFrame.

    Each row in the output DataFrame represents a single parameter measurement:
        timestamp  — pandas Timestamp (UTC-normalised)
        parameter  — standard name (Hs, Tp, wind_speed, …)
        value      — numeric value
        source     — data source label (ndbc, open_meteo, …)
        unit       — physical unit string

    Example:
        h = MetoceanHarmonizer()
        df = h.harmonize_ndbc(ndbc_obs_list)
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_long(
        self,
        obs_list: List[Dict[str, Any]],
        time_key: str,
        attr_map: Dict[str, tuple[str, str]],
        source_label: str,
    ) -> pd.DataFrame:
        """
        Convert a list of observation dicts to long-format DataFrame.

        Args:
            obs_list:     List of observation dicts (attribute → value)
            time_key:     Key in each dict that holds the timestamp
            attr_map:     Mapping of dict key → (standard_param_name, unit)
            source_label: Source identifier string (e.g. "ndbc")

        Returns:
            Long-format DataFrame with columns: timestamp, parameter, value, source, unit
        """
        rows: List[Dict[str, Any]] = []

        for obs in obs_list:
            raw_ts = obs.get(time_key)
            if raw_ts is None:
                continue
            ts = pd.Timestamp(raw_ts).tz_localize(None)  # normalise to naive UTC

            for attr, (param, unit) in attr_map.items():
                val = obs.get(attr)
                if val is None:
                    continue
                try:
                    numeric = float(val)
                except (TypeError, ValueError):
                    continue
                rows.append(
                    {
                        "timestamp": ts,
                        "parameter": param,
                        "value": numeric,
                        "source": source_label,
                        "unit": unit,
                    }
                )

        if not rows:
            return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)

        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    # ------------------------------------------------------------------
    # Public harmonisation methods
    # ------------------------------------------------------------------

    def harmonize_ndbc(self, observations: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Harmonize NDBC NDBCObservation dicts into long-format DataFrame.

        Args:
            observations: List of dicts with NDBC observation attributes

        Returns:
            Long-format DataFrame
        """
        return self._to_long(
            observations,
            time_key="observation_time",
            attr_map=_NDBC_MAP,
            source_label="ndbc",
        )

    def harmonize_open_meteo(self, observations: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Harmonize OpenMeteoForecast dicts into long-format DataFrame.

        Args:
            observations: List of dicts with OpenMeteo forecast attributes

        Returns:
            Long-format DataFrame
        """
        return self._to_long(
            observations,
            time_key="forecast_time",
            attr_map=_OPEN_METEO_MAP,
            source_label="open_meteo",
        )

    def harmonize_met_norway(self, observations: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Harmonize MetNorwayForecast dicts into long-format DataFrame.

        Args:
            observations: List of dicts with MET Norway forecast attributes

        Returns:
            Long-format DataFrame
        """
        return self._to_long(
            observations,
            time_key="forecast_time",
            attr_map=_MET_NORWAY_MAP,
            source_label="met_norway",
        )

    def harmonize_coops_water_level(
        self, observations: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Harmonize CO-OPS water level dicts into long-format DataFrame.

        Args:
            observations: List of dicts with CO-OPS water level attributes

        Returns:
            Long-format DataFrame
        """
        return self._to_long(
            observations,
            time_key="observation_time",
            attr_map=_COOPS_WATER_LEVEL_MAP,
            source_label="coops",
        )

    def harmonize_coops_current(
        self, observations: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Harmonize CO-OPS current dicts into long-format DataFrame.

        Args:
            observations: List of dicts with CO-OPS current attributes

        Returns:
            Long-format DataFrame
        """
        return self._to_long(
            observations,
            time_key="observation_time",
            attr_map=_COOPS_CURRENT_MAP,
            source_label="coops",
        )

    def harmonize_erddap(self, observations: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Harmonize ERDDAP observation dicts into long-format DataFrame.

        Args:
            observations: List of dicts with ERDDAP observation attributes

        Returns:
            Long-format DataFrame
        """
        return self._to_long(
            observations,
            time_key="observation_time",
            attr_map=_ERDDAP_MAP,
            source_label="erddap",
        )

    # ------------------------------------------------------------------
    # Time-grid alignment
    # ------------------------------------------------------------------

    def align_to_hourly_grid(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Resample a long-format DataFrame to an hourly UTC time grid.

        Continuous parameters (Hs, wind_speed, …) are linearly interpolated.
        Directional parameters (wind_dir, current_dir, wave_dir) use
        nearest-neighbour to avoid circular-mean artefacts.

        Args:
            df: Long-format DataFrame (must have: timestamp, parameter, value, source, unit)

        Returns:
            Aligned long-format DataFrame on hourly grid
        """
        if df.empty:
            return df.copy()

        required = {"timestamp", "parameter", "value", "source", "unit"}
        if not required.issubset(df.columns):
            return df.copy()

        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        aligned_parts: List[pd.DataFrame] = []

        for (param, source, unit), grp in df.groupby(
            ["parameter", "source", "unit"], sort=False
        ):
            grp = grp.set_index("timestamp").sort_index()
            series = grp["value"]

            # Build hourly target grid spanning the data range
            t_min = series.index.min().floor("h")
            t_max = series.index.max().ceil("h")
            hourly_idx = pd.date_range(t_min, t_max, freq="h")

            # Reindex to hourly + original points combined, then resample
            # De-duplicate before reindexing to avoid "duplicate labels" error
            series = series[~series.index.duplicated(keep="first")]
            combined_idx = series.index.union(hourly_idx)
            series_reindexed = series.reindex(combined_idx)

            if param in _DIRECTIONAL_PARAMS:
                # Nearest-neighbour: forward-fill then backward-fill
                filled = series_reindexed.ffill().bfill()
            else:
                # Linear interpolation for continuous variables
                filled = series_reindexed.interpolate(method="linear")

            # Keep only the hourly grid points
            hourly_series = filled.reindex(hourly_idx)

            part = pd.DataFrame(
                {
                    "timestamp": hourly_idx,
                    "parameter": param,
                    "value": hourly_series.values,
                    "source": source,
                    "unit": unit,
                }
            )
            part = part.dropna(subset=["value"])
            aligned_parts.append(part)

        if not aligned_parts:
            return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)

        result = pd.concat(aligned_parts, ignore_index=True)
        result["timestamp"] = pd.to_datetime(result["timestamp"])
        return result

    def merge_sources(self, dataframes: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Concatenate harmonised DataFrames from multiple sources.

        Args:
            dataframes: List of long-format DataFrames to merge

        Returns:
            Merged long-format DataFrame; empty DataFrame if input is empty
        """
        non_empty = [df for df in dataframes if df is not None and not df.empty]
        if not non_empty:
            return pd.DataFrame(columns=_EMPTY_DF_COLUMNS)
        return pd.concat(non_empty, ignore_index=True)
