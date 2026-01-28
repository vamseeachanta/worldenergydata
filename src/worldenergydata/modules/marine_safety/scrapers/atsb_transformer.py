# ABOUTME: Data transformation logic for ATSB marine investigation scraper.
# ABOUTME: Transforms raw scraped data into standardized investigation format.

"""
ATSB Data Transformer

Transforms raw ATSB investigation data into standardized format.
"""

from datetime import datetime
from typing import Any, Dict

from worldenergydata.modules.marine_safety.constants import (
    DataSource,
    IncidentStatus,
    IncidentType,
)
from worldenergydata.modules.marine_safety.scrapers.atsb_extractor import (
    normalize_australian_state,
)


def transform_investigation(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform raw investigation data into standardized format.

    Args:
        raw_data: Raw investigation data from scraping

    Returns:
        Standardized investigation dictionary
    """
    atsb_id = raw_data.get("atsb_id", "")

    # Parse location into components
    location_text = raw_data.get("location", "")
    city = None
    state = None

    if location_text:
        # Try to extract state from location
        parts = location_text.split(",")
        if len(parts) >= 2:
            city = parts[0].strip()
            state_part = parts[-1].strip()
            state = normalize_australian_state(state_part)
        else:
            city = location_text

    # Use details state if available
    if raw_data.get("state"):
        state = raw_data["state"]

    # Build location dict
    location = {
        "latitude": raw_data.get("latitude"),
        "longitude": raw_data.get("longitude"),
        "city": city,
        "state": state,
        "country": "Australia",
        "description": location_text,
    }

    # Build vessel dict
    vessel = {
        "name": raw_data.get("vessel_name"),
        "type": raw_data.get("vessel_type"),
        "flag": raw_data.get("flag_state"),
        "gross_tonnage": raw_data.get("gross_tonnage"),
    }

    # Build casualties dict
    casualties = {
        "fatalities": raw_data.get("fatalities", 0),
        "injuries": raw_data.get("injuries", 0),
        "missing": 0,
    }

    # Build report URL
    report_url = raw_data.get("report_url")

    return {
        "source": DataSource.ATSB.value,
        "source_id": atsb_id,
        "event_date": (
            raw_data.get("occurrence_date").isoformat()
            if raw_data.get("occurrence_date")
            else None
        ),
        "incident_type": raw_data.get("incident_type", IncidentType.OTHER.value),
        "status": raw_data.get("status", IncidentStatus.REPORTED.value),
        "title": raw_data.get("title", ""),
        "description": raw_data.get("description", ""),
        "location": location,
        "vessel": vessel,
        "casualties": casualties,
        "probable_cause": raw_data.get("probable_cause"),
        "report_url": report_url,
        "pdf_url": raw_data.get("pdf_url"),
        "pdf_path": (
            str(raw_data.get("pdf_path")) if raw_data.get("pdf_path") else None
        ),
        "scraped_at": datetime.utcnow().isoformat(),
        "raw_data": raw_data,
    }
