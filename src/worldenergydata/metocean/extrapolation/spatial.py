# ABOUTME: Spatial assessment tools — fetch analysis, sheltering, bathymetry proxy.
# ABOUTME: Determines whether direct transfer or physics-based correction is needed.

"""
Spatial Assessment for Metocean Extrapolation

Evaluates the spatial relationship between a target location and a candidate
data source to decide whether physics-based corrections are required.
Provides simplified fetch estimation and a sheltering heuristic.
"""

import math
from dataclasses import dataclass

from worldenergydata.metocean.extrapolation.source_catalog import (
    MetoceanSource,
    NearestSourceFinder,
)

# Threshold beyond which corrections are recommended
CORRECTION_DISTANCE_KM = 50.0

# Depth ratio threshold beyond which shoaling corrections matter
CORRECTION_DEPTH_RATIO = 0.2   # 20% relative difference

# Approximate coastline proximity thresholds for sheltering heuristic
_COASTAL_LAT_BANDS = [
    # (lat_min, lat_max, lon_min, lon_max, factor)
    # Gulf of Mexico — partially enclosed basin
    (18.0, 31.0, -98.0, -80.0, 0.75),
    # North Sea — semi-enclosed
    (50.0, 62.0, -5.0, 10.0, 0.80),
    # Mediterranean proxy
    (30.0, 47.0, -5.0, 42.0, 0.70),
]


@dataclass
class SpatialContext:
    """
    Spatial relationship between a target location and a data source.

    Attributes:
        target_lat: Target latitude (degrees)
        target_lon: Target longitude (degrees)
        nearest_source: The candidate MetoceanSource
        distance_km: Great-circle distance from target to source (km)
        fetch_km: Effective wind fetch at the target (km)
        depth_ratio: target_depth / source_depth proxy; 1.0 if unknown
        sheltering_factor: 0.0 = fully sheltered, 1.0 = fully exposed
        correction_needed: True when significant spatial correction is warranted
    """

    target_lat: float
    target_lon: float
    nearest_source: MetoceanSource
    distance_km: float
    fetch_km: float
    depth_ratio: float
    sheltering_factor: float
    correction_needed: bool


class SpatialAssessor:
    """
    Assesses the spatial context between a target point and a data source.

    All methods are offline — no network access required.
    """

    def __init__(self) -> None:
        self._finder = NearestSourceFinder()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(
        self,
        target_lat: float,
        target_lon: float,
        source: MetoceanSource,
    ) -> SpatialContext:
        """
        Compute the spatial context for a (target, source) pair.

        Args:
            target_lat: Target latitude (degrees)
            target_lon: Target longitude (degrees)
            source: Candidate MetoceanSource

        Returns:
            SpatialContext dataclass with all computed fields.
        """
        distance = self._finder.distance_km(
            target_lat, target_lon, source.lat, source.lon
        )
        fetch = self.estimate_fetch(target_lat, target_lon, direction_deg=270.0)
        shelter = self.sheltering_factor(target_lat, target_lon)
        depth_ratio = self._estimate_depth_ratio(
            target_lat, target_lon, source.lat, source.lon
        )

        correction_needed = (
            distance > CORRECTION_DISTANCE_KM
            or abs(depth_ratio - 1.0) > CORRECTION_DEPTH_RATIO
        )

        return SpatialContext(
            target_lat=target_lat,
            target_lon=target_lon,
            nearest_source=source,
            distance_km=distance,
            fetch_km=fetch,
            depth_ratio=depth_ratio,
            sheltering_factor=shelter,
            correction_needed=correction_needed,
        )

    def estimate_fetch(
        self, lat: float, lon: float, direction_deg: float = 270.0
    ) -> float:
        """
        Simplified open-water fetch estimate at a location.

        Uses a heuristic based on geographic region and bearing towards
        open ocean.  No GIS data is used — this is a physics-informed
        approximation suitable for screening calculations.

        Args:
            lat: Latitude of target (degrees)
            lon: Longitude of target (degrees)
            direction_deg: Prevailing wave/wind direction (degrees from N)

        Returns:
            Effective fetch in kilometres (> 0).
        """
        # Base fetch: open-ocean assumption
        base_fetch_km = 500.0

        # Reduce fetch in semi-enclosed basins
        shelter = self.sheltering_factor(lat, lon)
        fetch = base_fetch_km * shelter

        # Additional directional adjustment: latitudinal variation
        # Higher latitudes tend to have more exposed long fetches
        lat_factor = 0.8 + 0.4 * min(abs(lat) / 60.0, 1.0)
        fetch *= lat_factor

        # Coastal proximity heuristic — if within 200 km of a typical coast
        # reduce further (the sheltering_factor already captures much of this)
        return max(fetch, 10.0)

    def sheltering_factor(self, lat: float, lon: float) -> float:
        """
        Heuristic sheltering factor for a location.

        Returns a value in [0.0, 1.0] where 1.0 = fully open ocean and
        lower values indicate sheltering by land masses or basin geometry.

        Args:
            lat: Latitude (degrees)
            lon: Longitude (degrees)

        Returns:
            Sheltering factor in [0.0, 1.0].
        """
        for lat_min, lat_max, lon_min, lon_max, factor in _COASTAL_LAT_BANDS:
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return factor

        # Open ocean default
        return 1.0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_depth_ratio(
        target_lat: float,
        target_lon: float,
        source_lat: float,
        source_lon: float,
    ) -> float:
        """
        Proxy for depth ratio using a distance-based heuristic.

        In the absence of bathymetric data, depth changes are estimated
        from the movement away from typical continental shelf breaks.
        This is intentionally conservative: returns 1.0 when depth
        information is unavailable.

        Returns:
            Depth ratio target/source (dimensionless); 1.0 = same depth.
        """
        # Latitude proxy: higher latitudes and central-ocean locations
        # tend to have deeper water.  This is a rough heuristic only.
        target_deep = _is_deep_water_proxy(target_lat, target_lon)
        source_deep = _is_deep_water_proxy(source_lat, source_lon)

        if target_deep and not source_deep:
            # Moving from shelf to deep water
            return 2.5
        if not target_deep and source_deep:
            # Moving from deep water to shelf
            return 0.4
        return 1.0


def _is_deep_water_proxy(lat: float, lon: float) -> bool:
    """
    Very coarse proxy for whether a location is likely deep water.

    Excludes known shelf regions.  Used only for depth-ratio estimation
    when no bathymetric database is available.
    """
    # Gulf of Mexico shelf (depth < 200 m band)
    if 18.0 <= lat <= 31.0 and -98.0 <= lon <= -80.0:
        # Central GoM deep water
        if 23.0 <= lat <= 28.0 and -94.0 <= lon <= -84.0:
            return True
        return False

    # North Sea / continental shelf
    if 50.0 <= lat <= 62.0 and -5.0 <= lon <= 10.0:
        return False

    # US East Coast continental shelf
    if 24.0 <= lat <= 45.0 and -78.0 <= lon <= -65.0:
        return False

    # Default: assume deep water for open ocean
    return True
