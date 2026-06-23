"""Coordinate transformation utilities for wellpath calculations.

This module provides functions for converting between local coordinate systems
(North/East offsets) and geographic coordinates (latitude/longitude).
"""

from __future__ import annotations

import math


def north2lat(north: float, latitude: float) -> float:
    """Convert northing offset to latitude.

    Converts a northing value (meters north from surface location) to a
    new latitude value, accounting for the curvature of the Earth.

    Args:
        north: Northing offset in meters from surface location.
        latitude: Surface latitude in decimal degrees.

    Returns:
        New latitude in decimal degrees.

    Note:
        The formula accounts for Earth's curvature using an approximation
        based on the input latitude. Results are wrapped to stay within
        valid latitude ranges (-90 to 90 degrees).
    """
    lat_p: float = math.sqrt(latitude**2)
    new_lat: float = latitude + (north / (110574 + (lat_p * 12.44)))

    if latitude >= 0 and new_lat >= 90:
        return 180 - new_lat
    elif latitude <= 0 and new_lat <= -90:
        return -180 - new_lat
    else:
        return new_lat


def east2lon(east: float, latitude: float, longitude: float) -> float:
    """Convert easting offset to longitude.

    Converts an easting value (meters east from surface location) to a
    new longitude value, accounting for the latitude-dependent spacing
    of longitude lines.

    Args:
        east: Easting offset in meters from surface location.
        latitude: Surface latitude in decimal degrees.
        longitude: Surface longitude in decimal degrees.

    Returns:
        New longitude in decimal degrees.

    Note:
        The formula uses the cosine of latitude to account for the
        convergence of longitude lines toward the poles. Results are
        wrapped to stay within valid longitude ranges (-180 to 180 degrees).
    """
    new_lon: float = longitude + ((east * math.cos(math.radians(latitude))) / 111120)

    if new_lon >= 180:
        return -360 + new_lon
    elif new_lon <= -180:
        return 360 + new_lon
    else:
        return new_lon


def calculate_geographic_position(
    north: float,
    east: float,
    tvd: float,
    surface_lat: float,
    surface_lon: float,
    surface_alt: float,
) -> tuple[float, float, float]:
    """Calculate geographic position from local coordinates.

    Converts local North/East/TVD coordinates relative to a surface
    location into geographic latitude, longitude, and altitude.

    Args:
        north: Northing offset in meters.
        east: Easting offset in meters.
        tvd: True Vertical Depth in meters.
        surface_lat: Surface latitude in decimal degrees.
        surface_lon: Surface longitude in decimal degrees.
        surface_alt: Surface altitude in meters above sea level.

    Returns:
        Tuple of (latitude, longitude, altitude) in decimal degrees
        and meters respectively.
    """
    latitude = north2lat(north, surface_lat)
    longitude = east2lon(east, surface_lat, surface_lon)
    altitude = surface_alt - tvd

    return latitude, longitude, altitude
