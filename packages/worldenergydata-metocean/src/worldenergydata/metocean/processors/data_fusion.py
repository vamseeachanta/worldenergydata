# ABOUTME: Multi-source data fusion for metocean observations from NDBC, CO-OPS, Open-Meteo.
# ABOUTME: Merges observations by time/location with quality weighting and gap filling.

"""
Multi-Source Data Fusion for Metocean Observations

Merges observations from multiple sources (NDBC, CO-OPS, Open-Meteo, etc.)
for the same location and time, with quality weighting and gap filling.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from worldenergydata.metocean.constants import DataSource, QualityFlag
from worldenergydata.metocean.processors.data_harmonizer import (
    HarmonizedObservation,
)


@dataclass
class FusedObservation:
    """
    Fused observation combining data from multiple sources.

    Each parameter tracks its source and confidence level.

    Attributes:
        observation_time: UTC timestamp of the fused observation
        latitude: Location latitude (decimal degrees)
        longitude: Location longitude (decimal degrees)
        wave_height_m: Fused significant wave height (meters)
        wave_height_source: Source of wave height value
        wave_height_confidence: Confidence level (0-1)
        wave_period_s: Fused dominant wave period (seconds)
        wave_period_source: Source of wave period value
        wave_period_confidence: Confidence level (0-1)
        wave_direction_deg: Fused mean wave direction (degrees)
        wave_direction_source: Source of wave direction value
        wave_direction_confidence: Confidence level (0-1)
        wind_speed_ms: Fused wind speed (m/s)
        wind_speed_source: Source of wind speed value
        wind_speed_confidence: Confidence level (0-1)
        wind_direction_deg: Fused wind direction (degrees)
        wind_direction_source: Source of wind direction value
        wind_direction_confidence: Confidence level (0-1)
        sea_surface_temp_c: Fused sea surface temperature (Celsius)
        sea_surface_temp_source: Source of SST value
        sea_surface_temp_confidence: Confidence level (0-1)
        current_speed_ms: Fused current speed (m/s)
        current_speed_source: Source of current speed value
        current_speed_confidence: Confidence level (0-1)
        current_direction_deg: Fused current direction (degrees)
        current_direction_source: Source of current direction value
        current_direction_confidence: Confidence level (0-1)
        water_level_m: Fused water level/tide (meters)
        water_level_source: Source of water level value
        water_level_confidence: Confidence level (0-1)
        pressure_hpa: Fused atmospheric pressure (hPa)
        pressure_source: Source of pressure value
        pressure_confidence: Confidence level (0-1)
        sources_used: List of data sources contributing to this observation
        station_ids: Mapping of source to station ID
        quality_flag: Overall quality flag for fused observation
    """

    observation_time: datetime
    latitude: float
    longitude: float

    # Wave parameters with source tracking
    wave_height_m: Optional[float] = None
    wave_height_source: Optional[DataSource] = None
    wave_height_confidence: float = 0.0

    wave_period_s: Optional[float] = None
    wave_period_source: Optional[DataSource] = None
    wave_period_confidence: float = 0.0

    wave_direction_deg: Optional[float] = None
    wave_direction_source: Optional[DataSource] = None
    wave_direction_confidence: float = 0.0

    # Wind parameters with source tracking
    wind_speed_ms: Optional[float] = None
    wind_speed_source: Optional[DataSource] = None
    wind_speed_confidence: float = 0.0

    wind_direction_deg: Optional[float] = None
    wind_direction_source: Optional[DataSource] = None
    wind_direction_confidence: float = 0.0

    # Temperature with source tracking
    sea_surface_temp_c: Optional[float] = None
    sea_surface_temp_source: Optional[DataSource] = None
    sea_surface_temp_confidence: float = 0.0

    # Current parameters with source tracking
    current_speed_ms: Optional[float] = None
    current_speed_source: Optional[DataSource] = None
    current_speed_confidence: float = 0.0

    current_direction_deg: Optional[float] = None
    current_direction_source: Optional[DataSource] = None
    current_direction_confidence: float = 0.0

    # Water level with source tracking
    water_level_m: Optional[float] = None
    water_level_source: Optional[DataSource] = None
    water_level_confidence: float = 0.0

    # Pressure with source tracking
    pressure_hpa: Optional[float] = None
    pressure_source: Optional[DataSource] = None
    pressure_confidence: float = 0.0

    # Metadata
    sources_used: List[DataSource] = field(default_factory=list)
    station_ids: Dict[DataSource, str] = field(default_factory=dict)
    quality_flag: QualityFlag = QualityFlag.GOOD

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for database storage or serialization.

        Returns:
            Dictionary representation with ISO format timestamps and enum values
        """
        return {
            "observation_time": self.observation_time.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "wave_height_m": self.wave_height_m,
            "wave_height_source": (
                self.wave_height_source.value if self.wave_height_source else None
            ),
            "wave_height_confidence": self.wave_height_confidence,
            "wave_period_s": self.wave_period_s,
            "wave_period_source": (
                self.wave_period_source.value if self.wave_period_source else None
            ),
            "wave_period_confidence": self.wave_period_confidence,
            "wave_direction_deg": self.wave_direction_deg,
            "wave_direction_source": (
                self.wave_direction_source.value if self.wave_direction_source else None
            ),
            "wave_direction_confidence": self.wave_direction_confidence,
            "wind_speed_ms": self.wind_speed_ms,
            "wind_speed_source": (
                self.wind_speed_source.value if self.wind_speed_source else None
            ),
            "wind_speed_confidence": self.wind_speed_confidence,
            "wind_direction_deg": self.wind_direction_deg,
            "wind_direction_source": (
                self.wind_direction_source.value if self.wind_direction_source else None
            ),
            "wind_direction_confidence": self.wind_direction_confidence,
            "sea_surface_temp_c": self.sea_surface_temp_c,
            "sea_surface_temp_source": (
                self.sea_surface_temp_source.value
                if self.sea_surface_temp_source
                else None
            ),
            "sea_surface_temp_confidence": self.sea_surface_temp_confidence,
            "current_speed_ms": self.current_speed_ms,
            "current_speed_source": (
                self.current_speed_source.value if self.current_speed_source else None
            ),
            "current_speed_confidence": self.current_speed_confidence,
            "current_direction_deg": self.current_direction_deg,
            "current_direction_source": (
                self.current_direction_source.value
                if self.current_direction_source
                else None
            ),
            "current_direction_confidence": self.current_direction_confidence,
            "water_level_m": self.water_level_m,
            "water_level_source": (
                self.water_level_source.value if self.water_level_source else None
            ),
            "water_level_confidence": self.water_level_confidence,
            "pressure_hpa": self.pressure_hpa,
            "pressure_source": (
                self.pressure_source.value if self.pressure_source else None
            ),
            "pressure_confidence": self.pressure_confidence,
            "sources_used": [s.value for s in self.sources_used],
            "station_ids": {k.value: v for k, v in self.station_ids.items()},
            "quality_flag": self.quality_flag.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FusedObservation":
        """
        Create from dictionary (e.g., from database or JSON).

        Args:
            data: Dictionary with fused observation data

        Returns:
            FusedObservation instance
        """
        obs_time = data.get("observation_time")
        if isinstance(obs_time, str):
            obs_time = datetime.fromisoformat(obs_time)

        def parse_source(value: Any) -> Optional[DataSource]:
            if value is None:
                return None
            if isinstance(value, str):
                return DataSource(value)
            return value

        sources_used = [
            DataSource(s) if isinstance(s, str) else s
            for s in data.get("sources_used", [])
        ]

        station_ids_raw = data.get("station_ids", {})
        station_ids = {
            (DataSource(k) if isinstance(k, str) else k): v
            for k, v in station_ids_raw.items()
        }

        quality_flag = data.get("quality_flag", "good")
        if isinstance(quality_flag, str):
            quality_flag = QualityFlag(quality_flag)

        return cls(
            observation_time=obs_time,
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            wave_height_m=data.get("wave_height_m"),
            wave_height_source=parse_source(data.get("wave_height_source")),
            wave_height_confidence=data.get("wave_height_confidence", 0.0),
            wave_period_s=data.get("wave_period_s"),
            wave_period_source=parse_source(data.get("wave_period_source")),
            wave_period_confidence=data.get("wave_period_confidence", 0.0),
            wave_direction_deg=data.get("wave_direction_deg"),
            wave_direction_source=parse_source(data.get("wave_direction_source")),
            wave_direction_confidence=data.get("wave_direction_confidence", 0.0),
            wind_speed_ms=data.get("wind_speed_ms"),
            wind_speed_source=parse_source(data.get("wind_speed_source")),
            wind_speed_confidence=data.get("wind_speed_confidence", 0.0),
            wind_direction_deg=data.get("wind_direction_deg"),
            wind_direction_source=parse_source(data.get("wind_direction_source")),
            wind_direction_confidence=data.get("wind_direction_confidence", 0.0),
            sea_surface_temp_c=data.get("sea_surface_temp_c"),
            sea_surface_temp_source=parse_source(data.get("sea_surface_temp_source")),
            sea_surface_temp_confidence=data.get("sea_surface_temp_confidence", 0.0),
            current_speed_ms=data.get("current_speed_ms"),
            current_speed_source=parse_source(data.get("current_speed_source")),
            current_speed_confidence=data.get("current_speed_confidence", 0.0),
            current_direction_deg=data.get("current_direction_deg"),
            current_direction_source=parse_source(data.get("current_direction_source")),
            current_direction_confidence=data.get("current_direction_confidence", 0.0),
            water_level_m=data.get("water_level_m"),
            water_level_source=parse_source(data.get("water_level_source")),
            water_level_confidence=data.get("water_level_confidence", 0.0),
            pressure_hpa=data.get("pressure_hpa"),
            pressure_source=parse_source(data.get("pressure_source")),
            pressure_confidence=data.get("pressure_confidence", 0.0),
            sources_used=sources_used,
            station_ids=station_ids,
            quality_flag=quality_flag,
        )


@dataclass
class SourceWeight:
    """
    Weight configuration for a data source.

    Attributes:
        source: Data source identifier
        base_weight: Default weight for all parameters (0-1)
        wave_weight: Weight for wave parameters (0-1)
        wind_weight: Weight for wind parameters (0-1)
        current_weight: Weight for current parameters (0-1)
        temperature_weight: Weight for temperature parameters (0-1)
        water_level_weight: Weight for water level parameters (0-1)
        pressure_weight: Weight for pressure parameters (0-1)
    """

    source: DataSource
    base_weight: float = 1.0
    wave_weight: float = 1.0
    wind_weight: float = 1.0
    current_weight: float = 1.0
    temperature_weight: float = 1.0
    water_level_weight: float = 1.0
    pressure_weight: float = 1.0


class DataFusion:
    """
    Multi-source data fusion engine.

    Merges observations from multiple data sources (NDBC, CO-OPS, Open-Meteo, etc.)
    using configurable fusion strategies.

    Fusion Strategies:
        - best_available: Use highest weighted source for each parameter
        - quality_weighted: Weighted average based on source quality and reliability
        - nearest_time: Use observation closest to target time
        - average: Simple average of all sources

    Example usage:
        fusion = DataFusion()

        # Fuse observations at a specific time
        fused = fusion.fuse_by_time(observations, target_time)

        # Create regular time series from irregular observations
        series = fusion.fuse_time_series(
            observations, start, end,
            interval=timedelta(hours=1)
        )

        # Fill gaps in time series
        filled = fusion.fill_gaps(observations, max_gap=timedelta(hours=6))

    Attributes:
        weights: Dictionary mapping DataSource to SourceWeight configuration
        time_tolerance: Maximum time difference for matching observations
        distance_tolerance_km: Maximum distance for spatial matching
    """

    # Default source weights based on data quality and reliability
    DEFAULT_WEIGHTS: Dict[DataSource, SourceWeight] = {
        DataSource.NDBC: SourceWeight(
            source=DataSource.NDBC,
            base_weight=1.0,  # In-situ buoy - highest quality
            wave_weight=1.0,
            wind_weight=1.0,
            temperature_weight=1.0,
        ),
        DataSource.COOPS: SourceWeight(
            source=DataSource.COOPS,
            base_weight=1.0,  # In-situ tide gauge
            water_level_weight=1.0,  # Specialized for water level
            current_weight=0.9,
        ),
        DataSource.OPEN_METEO: SourceWeight(
            source=DataSource.OPEN_METEO,
            base_weight=0.7,  # Model data - lower than in-situ
            wave_weight=0.7,
            wind_weight=0.7,
            current_weight=0.6,
        ),
        DataSource.MET_NORWAY: SourceWeight(
            source=DataSource.MET_NORWAY,
            base_weight=0.8,  # High quality model
            wave_weight=0.8,
            wind_weight=0.85,
        ),
        DataSource.ERDDAP: SourceWeight(
            source=DataSource.ERDDAP,
            base_weight=0.9,  # Often in-situ data
        ),
    }

    # Time tolerance for matching observations
    DEFAULT_TIME_TOLERANCE: timedelta = timedelta(hours=1)

    # Distance tolerance for spatial matching (in km)
    DEFAULT_DISTANCE_TOLERANCE_KM: float = 50.0

    # Parameter to weight attribute mapping
    PARAMETER_WEIGHT_MAP: Dict[str, str] = {
        "wave_height_m": "wave_weight",
        "wave_period_s": "wave_weight",
        "wave_direction_deg": "wave_weight",
        "wind_speed_ms": "wind_weight",
        "wind_direction_deg": "wind_weight",
        "sea_surface_temp_c": "temperature_weight",
        "current_speed_ms": "current_weight",
        "current_direction_deg": "current_weight",
        "water_level_m": "water_level_weight",
        "pressure_hpa": "pressure_weight",
    }

    # Parameter to source attribute name mapping
    PARAMETER_SOURCE_ATTR_MAP: Dict[str, str] = {
        "wave_height_m": "wave_height_source",
        "wave_period_s": "wave_period_source",
        "wave_direction_deg": "wave_direction_source",
        "wind_speed_ms": "wind_speed_source",
        "wind_direction_deg": "wind_direction_source",
        "sea_surface_temp_c": "sea_surface_temp_source",
        "current_speed_ms": "current_speed_source",
        "current_direction_deg": "current_direction_source",
        "water_level_m": "water_level_source",
        "pressure_hpa": "pressure_source",
    }

    # Parameter to confidence attribute name mapping
    PARAMETER_CONFIDENCE_ATTR_MAP: Dict[str, str] = {
        "wave_height_m": "wave_height_confidence",
        "wave_period_s": "wave_period_confidence",
        "wave_direction_deg": "wave_direction_confidence",
        "wind_speed_ms": "wind_speed_confidence",
        "wind_direction_deg": "wind_direction_confidence",
        "sea_surface_temp_c": "sea_surface_temp_confidence",
        "current_speed_ms": "current_speed_confidence",
        "current_direction_deg": "current_direction_confidence",
        "water_level_m": "water_level_confidence",
        "pressure_hpa": "pressure_confidence",
    }

    def __init__(
        self,
        weights: Optional[Dict[DataSource, SourceWeight]] = None,
        time_tolerance: timedelta = DEFAULT_TIME_TOLERANCE,
        distance_tolerance_km: float = DEFAULT_DISTANCE_TOLERANCE_KM,
    ):
        """
        Initialize the data fusion engine.

        Args:
            weights: Custom source weight configuration. If None, uses DEFAULT_WEIGHTS
            time_tolerance: Maximum time difference for matching observations
            distance_tolerance_km: Maximum distance for spatial matching
        """
        self.weights = weights if weights is not None else self.DEFAULT_WEIGHTS.copy()
        self.time_tolerance = time_tolerance
        self.distance_tolerance_km = distance_tolerance_km

    def fuse_by_time(
        self,
        observations: List[HarmonizedObservation],
        target_time: datetime,
        strategy: str = "best_available",
    ) -> Optional[FusedObservation]:
        """
        Fuse observations near a target time.

        Args:
            observations: List of harmonized observations from multiple sources
            target_time: Target timestamp to match
            strategy: Fusion strategy (best_available, average, quality_weighted)

        Returns:
            FusedObservation or None if no data available within time tolerance

        Raises:
            ValueError: If unknown fusion strategy is specified
        """
        # Filter observations within time tolerance
        nearby = [
            obs
            for obs in observations
            if abs((obs.observation_time - target_time).total_seconds())
            <= self.time_tolerance.total_seconds()
        ]

        if not nearby:
            return None

        # Calculate representative location from observations with valid coordinates
        obs_with_lat = [o for o in nearby if o.latitude is not None]
        obs_with_lon = [o for o in nearby if o.longitude is not None]

        lat = (
            sum(o.latitude for o in obs_with_lat) / len(obs_with_lat)
            if obs_with_lat
            else 0.0
        )
        lon = (
            sum(o.longitude for o in obs_with_lon) / len(obs_with_lon)
            if obs_with_lon
            else 0.0
        )

        fused = FusedObservation(
            observation_time=target_time,
            latitude=lat,
            longitude=lon,
        )

        # Collect sources and station IDs
        fused.sources_used = list(set(o.source for o in nearby))
        fused.station_ids = {
            o.source: o.station_id for o in nearby if o.station_id is not None
        }

        # Fuse each parameter
        for param_name, weight_attr in self.PARAMETER_WEIGHT_MAP.items():
            value, source, confidence = self._fuse_parameter(
                nearby, param_name, weight_attr, strategy
            )
            setattr(fused, param_name, value)
            setattr(fused, self.PARAMETER_SOURCE_ATTR_MAP[param_name], source)
            setattr(fused, self.PARAMETER_CONFIDENCE_ATTR_MAP[param_name], confidence)

        return fused

    def _fuse_parameter(
        self,
        observations: List[HarmonizedObservation],
        param_name: str,
        weight_attr: str,
        strategy: str,
    ) -> Tuple[Optional[float], Optional[DataSource], float]:
        """
        Fuse a single parameter from multiple observations.

        Args:
            observations: List of observations to fuse
            param_name: Name of the parameter attribute
            weight_attr: Name of the weight attribute on SourceWeight
            strategy: Fusion strategy to use

        Returns:
            Tuple of (value, source, confidence)

        Raises:
            ValueError: If unknown fusion strategy is specified
        """
        # Collect values with source and weight
        values: List[Tuple[float, DataSource, float]] = []
        for obs in observations:
            value = getattr(obs, param_name, None)
            if value is not None:
                source_weight = self.weights.get(
                    obs.source, SourceWeight(obs.source, base_weight=0.5)
                )
                weight = getattr(source_weight, weight_attr, source_weight.base_weight)
                values.append((value, obs.source, weight))

        if not values:
            return None, None, 0.0

        if strategy == "best_available":
            # Use highest weighted source
            best = max(values, key=lambda x: x[2])
            return best[0], best[1], best[2]

        elif strategy == "average":
            # Simple average
            avg = sum(v[0] for v in values) / len(values)
            sources = list(set(v[1] for v in values))
            confidence = sum(v[2] for v in values) / len(values)
            return (
                avg,
                sources[0] if len(sources) == 1 else DataSource.OTHER,
                confidence,
            )

        elif strategy == "quality_weighted":
            # Weighted average
            total_weight = sum(v[2] for v in values)
            if total_weight == 0:
                return values[0][0], values[0][1], 0.5

            weighted_sum = sum(v[0] * v[2] for v in values)
            avg = weighted_sum / total_weight

            # Source is the highest weighted one
            best_source = max(values, key=lambda x: x[2])[1]
            confidence = total_weight / len(values)

            return avg, best_source, confidence

        else:
            raise ValueError(f"Unknown fusion strategy: {strategy}")

    def fuse_time_series(
        self,
        observations: List[HarmonizedObservation],
        start_time: datetime,
        end_time: datetime,
        interval: timedelta = timedelta(hours=1),
        strategy: str = "best_available",
    ) -> List[FusedObservation]:
        """
        Create fused time series at regular intervals.

        Args:
            observations: All observations from multiple sources
            start_time: Start of the time range
            end_time: End of the time range
            interval: Time step between fused observations
            strategy: Fusion strategy

        Returns:
            List of FusedObservation at regular intervals
        """
        fused_series: List[FusedObservation] = []
        current_time = start_time

        while current_time <= end_time:
            fused = self.fuse_by_time(observations, current_time, strategy)
            if fused:
                fused_series.append(fused)
            current_time += interval

        return fused_series

    def fill_gaps(
        self,
        observations: List[HarmonizedObservation],
        max_gap: timedelta = timedelta(hours=6),
        method: str = "linear",
    ) -> List[HarmonizedObservation]:
        """
        Fill gaps in observation time series.

        Args:
            observations: Sorted list of observations
            max_gap: Maximum gap to fill
            method: Interpolation method (linear, forward, backward)

        Returns:
            List with gaps filled by interpolated observations
        """
        if len(observations) < 2:
            return list(observations)

        # Sort by time
        sorted_obs = sorted(observations, key=lambda x: x.observation_time)
        filled: List[HarmonizedObservation] = [sorted_obs[0]]

        for i in range(1, len(sorted_obs)):
            prev = sorted_obs[i - 1]
            curr = sorted_obs[i]
            gap = curr.observation_time - prev.observation_time

            if gap > timedelta(hours=1) and gap <= max_gap:
                # Fill gap with interpolated values
                n_steps = int(gap.total_seconds() / 3600)
                for step in range(1, n_steps):
                    interp_time = prev.observation_time + timedelta(hours=step)
                    interp_obs = self._interpolate(prev, curr, interp_time, method)
                    if interp_obs:
                        filled.append(interp_obs)

            filled.append(curr)

        return filled

    def _interpolate(
        self,
        prev: HarmonizedObservation,
        curr: HarmonizedObservation,
        target_time: datetime,
        method: str,
    ) -> Optional[HarmonizedObservation]:
        """
        Interpolate between two observations.

        Args:
            prev: Previous observation
            curr: Current observation
            target_time: Time for interpolated observation
            method: Interpolation method (forward, linear, backward)

        Returns:
            Interpolated HarmonizedObservation or None
        """
        if method == "forward":
            # Use previous value
            interp = HarmonizedObservation(
                source=prev.source,
                observation_time=target_time,
                latitude=prev.latitude,
                longitude=prev.longitude,
                station_id=prev.station_id,
            )
            # Copy all parameters from prev
            for attr in [
                "wave_height_m",
                "wave_period_s",
                "wind_speed_ms",
                "sea_surface_temp_c",
                "water_level_m",
                "pressure_hpa",
            ]:
                setattr(interp, attr, getattr(prev, attr, None))
            interp.quality_flag = QualityFlag.SUSPECT  # Mark as interpolated
            return interp

        elif method == "backward":
            # Use next value
            interp = HarmonizedObservation(
                source=curr.source,
                observation_time=target_time,
                latitude=curr.latitude,
                longitude=curr.longitude,
                station_id=curr.station_id,
            )
            # Copy all parameters from curr
            for attr in [
                "wave_height_m",
                "wave_period_s",
                "wind_speed_ms",
                "sea_surface_temp_c",
                "water_level_m",
                "pressure_hpa",
            ]:
                setattr(interp, attr, getattr(curr, attr, None))
            interp.quality_flag = QualityFlag.SUSPECT
            return interp

        elif method == "linear":
            # Linear interpolation
            total_seconds = (
                curr.observation_time - prev.observation_time
            ).total_seconds()
            elapsed_seconds = (target_time - prev.observation_time).total_seconds()
            ratio = elapsed_seconds / total_seconds if total_seconds > 0 else 0

            interp = HarmonizedObservation(
                source=prev.source,
                observation_time=target_time,
                latitude=prev.latitude,
                longitude=prev.longitude,
                station_id=prev.station_id,
            )

            # Interpolate numeric parameters
            for attr in [
                "wave_height_m",
                "wave_period_s",
                "wind_speed_ms",
                "sea_surface_temp_c",
                "water_level_m",
                "pressure_hpa",
            ]:
                prev_val = getattr(prev, attr, None)
                curr_val = getattr(curr, attr, None)
                if prev_val is not None and curr_val is not None:
                    interp_val = prev_val + ratio * (curr_val - prev_val)
                    setattr(interp, attr, interp_val)

            interp.quality_flag = QualityFlag.SUSPECT
            return interp

        return None

    def fuse_by_location(
        self,
        observations: List[HarmonizedObservation],
        target_lat: float,
        target_lon: float,
        strategy: str = "best_available",
    ) -> Optional[FusedObservation]:
        """
        Fuse observations near a target location.

        Args:
            observations: List of harmonized observations from multiple sources
            target_lat: Target latitude (decimal degrees)
            target_lon: Target longitude (decimal degrees)
            strategy: Fusion strategy (best_available, average, quality_weighted)

        Returns:
            FusedObservation or None if no data available within distance tolerance
        """
        # Filter observations within distance tolerance
        nearby = [
            obs
            for obs in observations
            if obs.latitude is not None
            and obs.longitude is not None
            and self.haversine_distance(
                target_lat, target_lon, obs.latitude, obs.longitude
            )
            <= self.distance_tolerance_km
        ]

        if not nearby:
            return None

        # Use the most recent observation time
        latest_time = max(obs.observation_time for obs in nearby)

        fused = FusedObservation(
            observation_time=latest_time,
            latitude=target_lat,
            longitude=target_lon,
        )

        # Collect sources and station IDs
        fused.sources_used = list(set(o.source for o in nearby))
        fused.station_ids = {
            o.source: o.station_id for o in nearby if o.station_id is not None
        }

        # Fuse each parameter
        for param_name, weight_attr in self.PARAMETER_WEIGHT_MAP.items():
            value, source, confidence = self._fuse_parameter(
                nearby, param_name, weight_attr, strategy
            )
            setattr(fused, param_name, value)
            setattr(fused, self.PARAMETER_SOURCE_ATTR_MAP[param_name], source)
            setattr(fused, self.PARAMETER_CONFIDENCE_ATTR_MAP[param_name], confidence)

        return fused

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Args:
            lat1: Latitude of first point (decimal degrees)
            lon1: Longitude of first point (decimal degrees)
            lat2: Latitude of second point (decimal degrees)
            lon2: Longitude of second point (decimal degrees)

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
