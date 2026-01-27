# ABOUTME: Exports utility functions for geospatial and validation operations.
# ABOUTME: Provides coordinates, distance calculations, and input validators.
"""
Utility modules for the Metocean module.

Provides geospatial utilities and validation functions for
coordinate handling, distance calculations, and input validation.
"""

from .coordinates import (
    EARTH_RADIUS_KM,
    BoundingBox,
    bbox_contains,
    bbox_expand,
    bearing_between,
    create_grid_points,
    destination_point,
    find_nearest_station,
    haversine_distance,
    normalize_longitude,
)
from .validators import (
    validate_bbox,
    validate_coordinates,
    validate_datetime_range,
    validate_parameters,
    validate_positive_number,
    validate_station_id,
)

__all__ = [
    # Coordinates
    "BoundingBox",
    "haversine_distance",
    "bbox_contains",
    "bbox_expand",
    "find_nearest_station",
    "create_grid_points",
    "normalize_longitude",
    "bearing_between",
    "destination_point",
    "EARTH_RADIUS_KM",
    # Validators
    "validate_coordinates",
    "validate_bbox",
    "validate_datetime_range",
    "validate_station_id",
    "validate_parameters",
    "validate_positive_number",
]
