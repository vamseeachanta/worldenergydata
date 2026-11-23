# ABOUTME: Data harmonizer for converting source-specific formats to standardized format.
# ABOUTME: Handles NDBC, CO-OPS, and Open-Meteo data conversion with optional quality checks.

"""
Data Harmonizer for Metocean Observations

Converts data from different sources to a standardized format.
All measurements are converted to SI units:
- Heights/depths: meters
- Speeds: m/s
- Temperatures: Celsius
- Pressure: hPa
- Directions: degrees (0-360)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from worldenergydata.metocean.clients.ndbc_client import NDBCObservation
from worldenergydata.metocean.constants import DataSource, QualityFlag
from worldenergydata.metocean.processors.quality_filter import QualityFilter
from worldenergydata.metocean.processors.unit_converter import (
    LengthUnit,
    UnitConverter,
)


@dataclass
class HarmonizedObservation:
    """
    Standardized observation format across all sources.

    All measurements in SI units:
    - Heights/depths: meters
    - Speeds: m/s
    - Temperatures: Celsius
    - Pressure: hPa
    - Directions: degrees (0-360)

    Attributes:
        source: Data source identifier
        observation_time: UTC timestamp of the observation
        latitude: Station latitude (decimal degrees)
        longitude: Station longitude (decimal degrees)
        station_id: Station/buoy identifier
        wave_height_m: Significant wave height (meters)
        wave_period_s: Dominant wave period (seconds)
        wave_direction_deg: Mean wave direction (degrees from)
        wind_speed_ms: Wind speed (m/s)
        wind_direction_deg: Wind direction (degrees from)
        wind_gust_ms: Wind gust speed (m/s)
        current_speed_ms: Current speed (m/s)
        current_direction_deg: Current direction (degrees)
        sea_surface_temp_c: Sea surface temperature (Celsius)
        air_temp_c: Air temperature (Celsius)
        water_level_m: Water level/tide (meters)
        pressure_hpa: Atmospheric pressure (hPa)
        quality_flag: Overall quality flag
        quality_issues: List of quality issues found
    """

    source: DataSource
    observation_time: datetime

    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    station_id: Optional[str] = None

    # Wave parameters
    wave_height_m: Optional[float] = None
    wave_period_s: Optional[float] = None
    wave_direction_deg: Optional[float] = None

    # Wind parameters
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_gust_ms: Optional[float] = None

    # Current parameters
    current_speed_ms: Optional[float] = None
    current_direction_deg: Optional[float] = None

    # Other measurements
    sea_surface_temp_c: Optional[float] = None
    air_temp_c: Optional[float] = None
    water_level_m: Optional[float] = None
    pressure_hpa: Optional[float] = None

    # Quality
    quality_flag: QualityFlag = QualityFlag.GOOD
    quality_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for database storage or serialization.

        Returns:
            Dictionary representation with ISO format timestamps
        """
        return {
            "source": self.source.value,
            "observation_time": self.observation_time.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "station_id": self.station_id,
            "wave_height_m": self.wave_height_m,
            "wave_period_s": self.wave_period_s,
            "wave_direction_deg": self.wave_direction_deg,
            "wind_speed_ms": self.wind_speed_ms,
            "wind_direction_deg": self.wind_direction_deg,
            "wind_gust_ms": self.wind_gust_ms,
            "current_speed_ms": self.current_speed_ms,
            "current_direction_deg": self.current_direction_deg,
            "sea_surface_temp_c": self.sea_surface_temp_c,
            "air_temp_c": self.air_temp_c,
            "water_level_m": self.water_level_m,
            "pressure_hpa": self.pressure_hpa,
            "quality_flag": self.quality_flag.value,
            "quality_issues": self.quality_issues,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HarmonizedObservation":
        """
        Create from dictionary (e.g., from database or JSON).

        Args:
            data: Dictionary with observation data

        Returns:
            HarmonizedObservation instance
        """
        obs_time = data.get("observation_time")
        if isinstance(obs_time, str):
            obs_time = datetime.fromisoformat(obs_time)

        source = data.get("source")
        if isinstance(source, str):
            source = DataSource(source)

        quality_flag = data.get("quality_flag", "good")
        if isinstance(quality_flag, str):
            quality_flag = QualityFlag(quality_flag)

        return cls(
            source=source,
            observation_time=obs_time,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            station_id=data.get("station_id"),
            wave_height_m=data.get("wave_height_m"),
            wave_period_s=data.get("wave_period_s"),
            wave_direction_deg=data.get("wave_direction_deg"),
            wind_speed_ms=data.get("wind_speed_ms"),
            wind_direction_deg=data.get("wind_direction_deg"),
            wind_gust_ms=data.get("wind_gust_ms"),
            current_speed_ms=data.get("current_speed_ms"),
            current_direction_deg=data.get("current_direction_deg"),
            sea_surface_temp_c=data.get("sea_surface_temp_c"),
            air_temp_c=data.get("air_temp_c"),
            water_level_m=data.get("water_level_m"),
            pressure_hpa=data.get("pressure_hpa"),
            quality_flag=quality_flag,
            quality_issues=data.get("quality_issues", []),
        )

    def has_wave_data(self) -> bool:
        """Check if observation contains wave data."""
        return any(
            v is not None
            for v in [self.wave_height_m, self.wave_period_s, self.wave_direction_deg]
        )

    def has_wind_data(self) -> bool:
        """Check if observation contains wind data."""
        return any(
            v is not None
            for v in [self.wind_speed_ms, self.wind_direction_deg, self.wind_gust_ms]
        )

    def has_current_data(self) -> bool:
        """Check if observation contains current data."""
        return any(
            v is not None for v in [self.current_speed_ms, self.current_direction_deg]
        )


# Type aliases for source-specific observation types (for forward compatibility)
COOPSWaterLevel = Any  # Will be defined in coops_client.py
COOPSCurrent = Any  # Will be defined in coops_client.py
OpenMeteoForecast = Any  # Will be defined in open_meteo_client.py


class DataHarmonizer:
    """
    Harmonizes data from different metocean sources.

    Handles:
    - Unit conversions (NDBC uses various units)
    - Field name mapping
    - Quality flag standardization
    - Missing value handling

    Example usage:
        harmonizer = DataHarmonizer(apply_quality_checks=True)

        # Convert NDBC observation
        ndbc_obs = client.fetch_realtime("41001").data[0]
        harmonized = harmonizer.harmonize_ndbc(ndbc_obs)

        # Batch conversion
        observations = harmonizer.harmonize_batch(
            ndbc_observations, DataSource.NDBC
        )
    """

    def __init__(self, apply_quality_checks: bool = True):
        """
        Initialize harmonizer.

        Args:
            apply_quality_checks: Whether to apply quality checks during
                harmonization (default True)
        """
        self.apply_quality_checks = apply_quality_checks

    def harmonize_ndbc(
        self,
        observation: NDBCObservation,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> HarmonizedObservation:
        """
        Convert NDBC observation to harmonized format.

        NDBC data is already in SI units, so minimal conversion needed.
        Water level needs conversion from feet to meters.

        Args:
            observation: NDBCObservation from NDBC client
            latitude: Optional latitude (if known from station metadata)
            longitude: Optional longitude (if known from station metadata)

        Returns:
            HarmonizedObservation with standardized fields
        """
        # Convert water level from feet to meters if present
        water_level_m = None
        if observation.water_level_ft is not None:
            water_level_m = UnitConverter.length_to_m(
                observation.water_level_ft, LengthUnit.FT
            )

        # Normalize directions
        wind_dir = UnitConverter.normalize_direction(observation.wind_direction_deg)
        wave_dir = UnitConverter.normalize_direction(observation.wave_direction_deg)

        harmonized = HarmonizedObservation(
            source=DataSource.NDBC,
            observation_time=observation.observation_time,
            station_id=observation.station_id,
            latitude=latitude,
            longitude=longitude,
            wave_height_m=observation.wave_height_m,
            wave_period_s=observation.dominant_wave_period_s,
            wave_direction_deg=wave_dir,
            wind_speed_ms=observation.wind_speed_ms,
            wind_direction_deg=wind_dir,
            wind_gust_ms=observation.wind_gust_ms,
            sea_surface_temp_c=observation.sea_surface_temp_c,
            air_temp_c=observation.air_temp_c,
            pressure_hpa=observation.pressure_hpa,
            water_level_m=water_level_m,
        )

        if self.apply_quality_checks:
            self._apply_quality_checks(harmonized)

        return harmonized

    def harmonize_coops_water_level(
        self,
        observation: Any,
    ) -> HarmonizedObservation:
        """
        Convert CO-OPS water level observation to harmonized format.

        CO-OPS provides water level data in meters.

        Args:
            observation: COOPSWaterLevel from CO-OPS client

        Returns:
            HarmonizedObservation with water level data
        """
        # Extract fields based on expected COOPSWaterLevel structure
        obs_time = getattr(observation, "observation_time", None)
        station_id = getattr(observation, "station_id", None)
        water_level = getattr(observation, "water_level_m", None)
        latitude = getattr(observation, "latitude", None)
        longitude = getattr(observation, "longitude", None)

        harmonized = HarmonizedObservation(
            source=DataSource.COOPS,
            observation_time=obs_time,
            station_id=station_id,
            latitude=latitude,
            longitude=longitude,
            water_level_m=water_level,
        )

        if self.apply_quality_checks:
            self._apply_quality_checks(harmonized)

        return harmonized

    def harmonize_coops_current(
        self,
        observation: Any,
    ) -> HarmonizedObservation:
        """
        Convert CO-OPS current observation to harmonized format.

        CO-OPS provides current speed in knots and direction in degrees.

        Args:
            observation: COOPSCurrent from CO-OPS client

        Returns:
            HarmonizedObservation with current data
        """
        # Extract and convert fields
        obs_time = getattr(observation, "observation_time", None)
        station_id = getattr(observation, "station_id", None)
        latitude = getattr(observation, "latitude", None)
        longitude = getattr(observation, "longitude", None)

        # Current speed may already be in m/s or need conversion
        current_speed = getattr(observation, "current_speed_ms", None)
        current_dir = getattr(observation, "current_direction_deg", None)

        # Normalize direction
        if current_dir is not None:
            current_dir = UnitConverter.normalize_direction(current_dir)

        harmonized = HarmonizedObservation(
            source=DataSource.COOPS,
            observation_time=obs_time,
            station_id=station_id,
            latitude=latitude,
            longitude=longitude,
            current_speed_ms=current_speed,
            current_direction_deg=current_dir,
        )

        if self.apply_quality_checks:
            self._apply_quality_checks(harmonized)

        return harmonized

    def harmonize_open_meteo(
        self,
        forecast: Any,
    ) -> HarmonizedObservation:
        """
        Convert Open-Meteo marine forecast to harmonized format.

        Open-Meteo provides data in SI units.

        Args:
            forecast: OpenMeteoForecast from Open-Meteo client

        Returns:
            HarmonizedObservation with forecast data
        """
        # Extract fields based on expected OpenMeteoForecast structure
        forecast_time = getattr(forecast, "forecast_time", None)
        latitude = getattr(forecast, "latitude", None)
        longitude = getattr(forecast, "longitude", None)

        wave_height = getattr(forecast, "wave_height_m", None)
        wave_period = getattr(forecast, "wave_period_s", None)
        wave_dir = getattr(forecast, "wave_direction_deg", None)

        current_speed = getattr(forecast, "current_speed_ms", None)
        current_dir = getattr(forecast, "current_direction_deg", None)

        wind_speed = getattr(forecast, "wind_speed_ms", None)
        wind_dir = getattr(forecast, "wind_direction_deg", None)

        # Normalize directions
        wave_dir = UnitConverter.normalize_direction(wave_dir)
        current_dir = UnitConverter.normalize_direction(current_dir)
        wind_dir = UnitConverter.normalize_direction(wind_dir)

        harmonized = HarmonizedObservation(
            source=DataSource.OPEN_METEO,
            observation_time=forecast_time,
            latitude=latitude,
            longitude=longitude,
            wave_height_m=wave_height,
            wave_period_s=wave_period,
            wave_direction_deg=wave_dir,
            current_speed_ms=current_speed,
            current_direction_deg=current_dir,
            wind_speed_ms=wind_speed,
            wind_direction_deg=wind_dir,
        )

        if self.apply_quality_checks:
            self._apply_quality_checks(harmonized)

        return harmonized

    def _apply_quality_checks(self, observation: HarmonizedObservation) -> None:
        """
        Apply quality checks and update observation flags.

        Args:
            observation: HarmonizedObservation to validate (modified in place)
        """
        flag, issues = QualityFilter.validate_observation(
            wave_height=observation.wave_height_m,
            wave_period=observation.wave_period_s,
            wave_direction=observation.wave_direction_deg,
            wind_speed=observation.wind_speed_ms,
            wind_direction=observation.wind_direction_deg,
            current_speed=observation.current_speed_ms,
            current_direction=observation.current_direction_deg,
            sea_surface_temp=observation.sea_surface_temp_c,
            pressure=observation.pressure_hpa,
            water_level=observation.water_level_m,
        )

        observation.quality_flag = flag
        observation.quality_issues = issues

    def harmonize_batch(
        self,
        observations: List[Any],
        source: DataSource,
        station_coords: Optional[Dict[str, tuple]] = None,
    ) -> List[HarmonizedObservation]:
        """
        Harmonize a batch of observations from a source.

        Args:
            observations: List of source-specific observations
            source: Data source type
            station_coords: Optional dict mapping station_id to (lat, lon)

        Returns:
            List of HarmonizedObservation objects

        Raises:
            ValueError: If no harmonizer exists for the source
        """
        harmonized: List[HarmonizedObservation] = []

        for obs in observations:
            try:
                if source == DataSource.NDBC:
                    lat, lon = None, None
                    if station_coords:
                        station_id = getattr(obs, "station_id", None)
                        if station_id and station_id in station_coords:
                            lat, lon = station_coords[station_id]
                    harmonized.append(self.harmonize_ndbc(obs, lat, lon))

                elif source == DataSource.COOPS:
                    # Determine if water level or current based on attributes
                    if hasattr(obs, "water_level_m"):
                        harmonized.append(self.harmonize_coops_water_level(obs))
                    elif hasattr(obs, "current_speed_ms"):
                        harmonized.append(self.harmonize_coops_current(obs))

                elif source == DataSource.OPEN_METEO:
                    harmonized.append(self.harmonize_open_meteo(obs))

                else:
                    raise ValueError(f"No harmonizer for source: {source}")

            except Exception:
                # Skip observations that fail to harmonize
                continue

        return harmonized

    def merge_observations(
        self,
        observations: List[HarmonizedObservation],
        time_tolerance_minutes: int = 30,
    ) -> List[HarmonizedObservation]:
        """
        Merge observations from different sources at similar times/locations.

        Combines observations that are within the time tolerance and at the
        same station or location to create a more complete record.

        Args:
            observations: List of harmonized observations
            time_tolerance_minutes: Maximum time difference to merge

        Returns:
            List of merged observations
        """
        if not observations:
            return []

        # Sort by time
        sorted_obs = sorted(observations, key=lambda x: x.observation_time)

        merged: List[HarmonizedObservation] = []
        current_group: List[HarmonizedObservation] = [sorted_obs[0]]

        for obs in sorted_obs[1:]:
            # Check if observation should be merged with current group
            time_diff = abs(
                (
                    obs.observation_time - current_group[0].observation_time
                ).total_seconds()
            )
            time_diff_minutes = time_diff / 60

            same_location = (
                obs.station_id == current_group[0].station_id
                if obs.station_id
                else (
                    obs.latitude == current_group[0].latitude
                    and obs.longitude == current_group[0].longitude
                )
            )

            if time_diff_minutes <= time_tolerance_minutes and same_location:
                current_group.append(obs)
            else:
                # Merge current group and start new one
                merged.append(self._merge_group(current_group))
                current_group = [obs]

        # Don't forget last group
        if current_group:
            merged.append(self._merge_group(current_group))

        return merged

    def _merge_group(
        self, observations: List[HarmonizedObservation]
    ) -> HarmonizedObservation:
        """
        Merge a group of observations into a single observation.

        Takes the first non-None value for each field, preferring certain
        sources over others.

        Args:
            observations: List of observations to merge

        Returns:
            Single merged observation
        """
        if len(observations) == 1:
            return observations[0]

        # Source preference order
        source_priority = {
            DataSource.NDBC: 1,  # Prefer buoy data
            DataSource.COOPS: 2,  # Then tides/currents
            DataSource.OPEN_METEO: 3,  # Then forecast
        }

        # Sort by source priority
        sorted_obs = sorted(
            observations, key=lambda x: source_priority.get(x.source, 99)
        )

        # Start with first (highest priority) observation
        merged = HarmonizedObservation(
            source=sorted_obs[0].source,
            observation_time=sorted_obs[0].observation_time,
            station_id=sorted_obs[0].station_id,
            latitude=sorted_obs[0].latitude,
            longitude=sorted_obs[0].longitude,
        )

        # Fill in missing values from other observations
        for obs in sorted_obs:
            if merged.wave_height_m is None:
                merged.wave_height_m = obs.wave_height_m
            if merged.wave_period_s is None:
                merged.wave_period_s = obs.wave_period_s
            if merged.wave_direction_deg is None:
                merged.wave_direction_deg = obs.wave_direction_deg
            if merged.wind_speed_ms is None:
                merged.wind_speed_ms = obs.wind_speed_ms
            if merged.wind_direction_deg is None:
                merged.wind_direction_deg = obs.wind_direction_deg
            if merged.wind_gust_ms is None:
                merged.wind_gust_ms = obs.wind_gust_ms
            if merged.current_speed_ms is None:
                merged.current_speed_ms = obs.current_speed_ms
            if merged.current_direction_deg is None:
                merged.current_direction_deg = obs.current_direction_deg
            if merged.sea_surface_temp_c is None:
                merged.sea_surface_temp_c = obs.sea_surface_temp_c
            if merged.air_temp_c is None:
                merged.air_temp_c = obs.air_temp_c
            if merged.water_level_m is None:
                merged.water_level_m = obs.water_level_m
            if merged.pressure_hpa is None:
                merged.pressure_hpa = obs.pressure_hpa

        # Re-run quality checks on merged data
        if self.apply_quality_checks:
            self._apply_quality_checks(merged)

        return merged
