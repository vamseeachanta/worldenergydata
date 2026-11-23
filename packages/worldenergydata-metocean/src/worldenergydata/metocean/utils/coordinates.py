# ABOUTME: Geospatial utilities for coordinate transformations and distance calculations.
# ABOUTME: Provides Haversine distance, bounding box operations, and grid generation.
"""
Geospatial Utilities for Metocean Module

Provides coordinate transformations, distance calculations,
bounding box operations, and grid generation.
"""

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0


@dataclass
class BoundingBox:
    """Geographic bounding box"""

    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float

    @classmethod
    def from_tuple(cls, bbox: Tuple[float, float, float, float]) -> "BoundingBox":
        """Create from (lon_min, lon_max, lat_min, lat_max) tuple"""
        return cls(lon_min=bbox[0], lon_max=bbox[1], lat_min=bbox[2], lat_max=bbox[3])

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """Convert to tuple"""
        return (self.lon_min, self.lon_max, self.lat_min, self.lat_max)

    def contains(self, lat: float, lon: float) -> bool:
        """Check if point is within bounding box"""
        return (
            self.lat_min <= lat <= self.lat_max and self.lon_min <= lon <= self.lon_max
        )

    def expand(self, margin_km: float) -> "BoundingBox":
        """Expand bounding box by margin in km"""
        # Approximate degrees per km
        lat_margin = margin_km / 111.0  # ~111 km per degree latitude
        center_lat = (self.lat_min + self.lat_max) / 2
        lon_margin = margin_km / (111.0 * math.cos(math.radians(center_lat)))

        return BoundingBox(
            lon_min=self.lon_min - lon_margin,
            lon_max=self.lon_max + lon_margin,
            lat_min=self.lat_min - lat_margin,
            lat_max=self.lat_max + lat_margin,
        )

    @property
    def center(self) -> Tuple[float, float]:
        """Get center point (lat, lon)"""
        return (
            (self.lat_min + self.lat_max) / 2,
            (self.lon_min + self.lon_max) / 2,
        )

    @property
    def area_km2(self) -> float:
        """Approximate area in square kilometers"""
        lat_dist = haversine_distance(
            self.lat_min, self.lon_min, self.lat_max, self.lon_min
        )
        lon_dist = haversine_distance(
            self.lat_min, self.lon_min, self.lat_min, self.lon_max
        )
        return lat_dist * lon_dist


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points in km.

    Uses the Haversine formula for accuracy.

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in kilometers
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def bbox_contains(
    bbox: Tuple[float, float, float, float], lat: float, lon: float
) -> bool:
    """
    Check if a point is within a bounding box.

    Args:
        bbox: (lon_min, lon_max, lat_min, lat_max)
        lat, lon: Point coordinates

    Returns:
        True if point is within bbox
    """
    lon_min, lon_max, lat_min, lat_max = bbox
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def bbox_expand(
    bbox: Tuple[float, float, float, float], margin_km: float
) -> Tuple[float, float, float, float]:
    """
    Expand a bounding box by a margin in kilometers.

    Args:
        bbox: (lon_min, lon_max, lat_min, lat_max)
        margin_km: Margin to add in km

    Returns:
        Expanded bounding box tuple
    """
    bb = BoundingBox.from_tuple(bbox)
    expanded = bb.expand(margin_km)
    return expanded.to_tuple()


def find_nearest_station(
    lat: float,
    lon: float,
    stations: List[Any],
    lat_attr: str = "latitude",
    lon_attr: str = "longitude",
    max_distance_km: Optional[float] = None,
) -> Tuple[Optional[Any], float]:
    """
    Find the nearest station to a point.

    Args:
        lat, lon: Target coordinates
        stations: List of station objects
        lat_attr, lon_attr: Attribute names for coordinates
        max_distance_km: Maximum distance to search

    Returns:
        (nearest_station, distance_km) or (None, inf)
    """
    nearest = None
    min_distance = float("inf")

    for station in stations:
        station_lat = getattr(station, lat_attr, None)
        station_lon = getattr(station, lon_attr, None)

        if station_lat is None or station_lon is None:
            continue

        distance = haversine_distance(lat, lon, station_lat, station_lon)

        if distance < min_distance:
            if max_distance_km is None or distance <= max_distance_km:
                min_distance = distance
                nearest = station

    return nearest, min_distance


def create_grid_points(
    bbox: Tuple[float, float, float, float], resolution_km: float
) -> List[Tuple[float, float]]:
    """
    Create a regular grid of points within a bounding box.

    Args:
        bbox: (lon_min, lon_max, lat_min, lat_max)
        resolution_km: Grid spacing in km

    Returns:
        List of (lat, lon) tuples
    """
    lon_min, lon_max, lat_min, lat_max = bbox

    # Calculate degrees per resolution
    lat_step = resolution_km / 111.0
    center_lat = (lat_min + lat_max) / 2
    lon_step = resolution_km / (111.0 * math.cos(math.radians(center_lat)))

    points = []
    lat = lat_min
    while lat <= lat_max:
        lon = lon_min
        while lon <= lon_max:
            points.append((lat, lon))
            lon += lon_step
        lat += lat_step

    return points


def normalize_longitude(lon: float) -> float:
    """Normalize longitude to -180 to 180 range"""
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    return lon


def bearing_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial bearing from point 1 to point 2.

    Returns:
        Bearing in degrees (0-360)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
        lat2_rad
    ) * math.cos(dlon)

    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360


def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_km: float
) -> Tuple[float, float]:
    """
    Calculate destination point given start, bearing, and distance.

    Args:
        lat, lon: Starting coordinates
        bearing_deg: Bearing in degrees
        distance_km: Distance in km

    Returns:
        (lat, lon) of destination
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)

    angular_dist = distance_km / EARTH_RADIUS_KM

    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(angular_dist)
        + math.cos(lat_rad) * math.sin(angular_dist) * math.cos(bearing_rad)
    )

    lon2 = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_dist) * math.cos(lat_rad),
        math.cos(angular_dist) - math.sin(lat_rad) * math.sin(lat2),
    )

    return math.degrees(lat2), normalize_longitude(math.degrees(lon2))
