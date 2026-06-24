# ABOUTME: Data validation logic for ATSB marine investigation scraper.
# ABOUTME: Validates scraped investigation data for required fields and formats.

"""
ATSB Data Validator

Validates ATSB investigation data for completeness and correctness.
"""

import re
from datetime import date, datetime
from typing import Any, Dict

from worldenergydata.marine_safety.scrapers.atsb_constants import (
    ATSB_ID_PATTERN,
)
from worldenergydata.marine_safety.utils.logger import get_logger

logger = get_logger(__name__)


def validate_investigation_data(
    data: Dict[str, Any],
    min_date: date,
) -> bool:
    """
    Validate scraped investigation data.

    Args:
        data: Dictionary containing investigation data
        min_date: Minimum valid date for investigations

    Returns:
        True if data is valid, False otherwise
    """
    atsb_id = data.get("source_id", "")

    # Required fields
    required_fields = ["source_id", "source"]
    for field in required_fields:
        if not data.get(field):
            logger.warning(f"Missing required field: {field}")
            return False

    # Validate ATSB ID format
    if atsb_id and not validate_atsb_id(atsb_id):
        logger.warning(f"Invalid ATSB ID format: {atsb_id}")
        # Don't fail validation for ID format, just warn

    # Validate date if present
    event_date = data.get("event_date")
    if event_date:
        try:
            if isinstance(event_date, str):
                parsed_date = datetime.fromisoformat(event_date).date()
            else:
                parsed_date = event_date

            if parsed_date < min_date:
                logger.warning(f"Event date {parsed_date} before min date {min_date}")
            if parsed_date > date.today():
                logger.warning(f"Event date {parsed_date} is in the future")
                return False

        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid event date format: {event_date} - {e}")

    # Validate casualties (non-negative)
    casualties = data.get("casualties", {})
    for key in ["fatalities", "injuries", "missing"]:
        value = casualties.get(key, 0)
        if isinstance(value, (int, float)) and value < 0:
            logger.warning(f"Negative casualty count for {key}: {value}")
            return False

    # Validate coordinates if present
    location = data.get("location", {})
    lat = location.get("latitude")
    lon = location.get("longitude")

    if lat is not None:
        try:
            lat = float(lat)
            if not -90 <= lat <= 90:
                logger.warning(f"Invalid latitude: {lat}")
                return False
        except (ValueError, TypeError):
            pass

    if lon is not None:
        try:
            lon = float(lon)
            if not -180 <= lon <= 180:
                logger.warning(f"Invalid longitude: {lon}")
                return False
        except (ValueError, TypeError):
            pass

    return True


def validate_atsb_id(atsb_id: str) -> bool:
    """
    Validate ATSB investigation ID format.

    Args:
        atsb_id: ATSB ID to validate

    Returns:
        True if valid format
    """
    if not atsb_id:
        return False

    clean_id = atsb_id.strip().upper()

    # Check against pattern
    if ATSB_ID_PATTERN.match(clean_id):
        return True

    # Accept more flexible patterns (e.g., MO2022001)
    if re.match(r"^(?:MO|MR)\d{7,}$", clean_id):
        return True

    return False
