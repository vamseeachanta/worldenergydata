# ABOUTME: Validation functions for metocean module inputs.
# ABOUTME: Validates coordinates, dates, station IDs, and parameters.
"""
Validators for Metocean Module

Provides validation functions for coordinates, dates, station IDs,
and other input parameters.
"""

import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

from ..constants import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    DataSource,
)
from ..exceptions import InvalidDataError, ValidationError


def validate_coordinates(
    latitude: float,
    longitude: float,
    allow_none: bool = False,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Validate geographic coordinates.

    Args:
        latitude: Latitude (-90 to 90)
        longitude: Longitude (-180 to 180)
        allow_none: Allow None values

    Returns:
        Validated (latitude, longitude) tuple

    Raises:
        ValidationError: If coordinates are invalid
    """
    if allow_none and (latitude is None or longitude is None):
        return latitude, longitude

    if latitude is None or longitude is None:
        raise ValidationError(
            message="Coordinates cannot be None",
            error_code="INVALID_COORDINATES",
        )

    if not MIN_LATITUDE <= latitude <= MAX_LATITUDE:
        raise InvalidDataError(
            field="latitude",
            value=latitude,
            reason=f"Must be between {MIN_LATITUDE} and {MAX_LATITUDE}",
        )

    if not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
        raise InvalidDataError(
            field="longitude",
            value=longitude,
            reason=f"Must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}",
        )

    return float(latitude), float(longitude)


def validate_bbox(
    bbox: Tuple[float, float, float, float],
) -> Tuple[float, float, float, float]:
    """
    Validate a bounding box.

    Args:
        bbox: (lon_min, lon_max, lat_min, lat_max)

    Returns:
        Validated bbox tuple

    Raises:
        ValidationError: If bbox is invalid
    """
    if len(bbox) != 4:
        raise ValidationError(
            message="Bounding box must have 4 values",
            error_code="INVALID_BBOX",
        )

    lon_min, lon_max, lat_min, lat_max = bbox

    # Validate individual coordinates
    validate_coordinates(lat_min, lon_min)
    validate_coordinates(lat_max, lon_max)

    # Check ordering
    if lat_min > lat_max:
        raise InvalidDataError(
            field="bbox",
            value=bbox,
            reason="lat_min must be less than lat_max",
        )

    # Note: lon_min > lon_max is OK for bboxes crossing the antimeridian

    return bbox


def validate_datetime_range(
    start_date: datetime,
    end_date: datetime,
    max_range_days: Optional[int] = None,
    allow_future: bool = True,
) -> Tuple[datetime, datetime]:
    """
    Validate a date range.

    Args:
        start_date: Start datetime
        end_date: End datetime
        max_range_days: Maximum allowed range in days
        allow_future: Allow future dates

    Returns:
        Validated (start_date, end_date) tuple

    Raises:
        ValidationError: If date range is invalid
    """
    if start_date > end_date:
        raise InvalidDataError(
            field="date_range",
            value=f"{start_date} to {end_date}",
            reason="Start date must be before end date",
        )

    if not allow_future:
        now = datetime.utcnow()
        if start_date > now:
            raise InvalidDataError(
                field="start_date",
                value=start_date,
                reason="Start date cannot be in the future",
            )
        if end_date > now:
            # Clip to current time
            end_date = now

    if max_range_days:
        range_days = (end_date - start_date).days
        if range_days > max_range_days:
            raise InvalidDataError(
                field="date_range",
                value=f"{range_days} days",
                reason=f"Date range cannot exceed {max_range_days} days",
            )

    return start_date, end_date


def validate_station_id(
    station_id: str,
    source: Optional[DataSource] = None,
) -> str:
    """
    Validate a station ID format.

    Args:
        station_id: Station identifier
        source: Optional data source for format validation

    Returns:
        Validated station ID

    Raises:
        ValidationError: If station ID is invalid
    """
    if not station_id:
        raise ValidationError(
            message="Station ID cannot be empty",
            error_code="INVALID_STATION_ID",
        )

    station_id = station_id.strip().upper()

    # Source-specific validation
    if source == DataSource.NDBC:
        # NDBC station IDs are typically 4-7 alphanumeric characters
        if not re.match(r"^[A-Z0-9]{4,7}$", station_id):
            raise InvalidDataError(
                field="station_id",
                value=station_id,
                reason="NDBC station ID should be 4-7 alphanumeric characters",
            )

    elif source == DataSource.COOPS:
        # CO-OPS station IDs are 7-digit numbers
        if not re.match(r"^\d{7}$", station_id):
            raise InvalidDataError(
                field="station_id",
                value=station_id,
                reason="CO-OPS station ID should be 7 digits",
            )

    return station_id


def validate_parameters(
    parameters: List[str],
    allowed: Optional[List[str]] = None,
) -> List[str]:
    """
    Validate requested parameters.

    Args:
        parameters: List of parameter names
        allowed: Optional list of allowed parameter names

    Returns:
        Validated parameter list

    Raises:
        ValidationError: If parameters are invalid
    """
    if not parameters:
        raise ValidationError(
            message="At least one parameter must be specified",
            error_code="NO_PARAMETERS",
        )

    validated = []
    for param in parameters:
        param_lower = param.lower().strip()

        if allowed and param_lower not in [a.lower() for a in allowed]:
            raise InvalidDataError(
                field="parameter",
                value=param,
                reason=f"Not in allowed list: {allowed}",
            )

        validated.append(param_lower)

    return validated


def validate_positive_number(
    value: Any,
    field_name: str,
    allow_zero: bool = False,
) -> float:
    """
    Validate that a value is a positive number.

    Args:
        value: Value to validate
        field_name: Name of field for error messages
        allow_zero: Allow zero value

    Returns:
        Validated float value

    Raises:
        ValidationError: If value is not positive
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise InvalidDataError(
            field=field_name,
            value=value,
            reason="Must be a number",
        )

    if allow_zero:
        if num < 0:
            raise InvalidDataError(
                field=field_name,
                value=value,
                reason="Must be non-negative",
            )
    else:
        if num <= 0:
            raise InvalidDataError(
                field=field_name,
                value=value,
                reason="Must be positive",
            )

    return num
