# ABOUTME: HTML parsing logic for ATSB marine investigation scraper.
# ABOUTME: Extracts investigation metadata from ATSB web pages using BeautifulSoup.

"""
ATSB HTML Parser

Parses HTML from the Australian Transport Safety Bureau website
to extract investigation metadata.
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from worldenergydata.modules.marine_safety.constants import IncidentStatus
from worldenergydata.modules.marine_safety.scrapers.atsb_constants import (
    BASE_URL,
    STATUS_MAPPING,
)
from worldenergydata.modules.marine_safety.utils.logger import get_logger

logger = get_logger(__name__)


def parse_investigation_list(
    soup: Any,
    extract_text_fn: callable,
    extract_attribute_fn: callable,
) -> List[Dict[str, Any]]:
    """
    Parse investigation listing HTML to extract investigation metadata.

    Args:
        soup: BeautifulSoup parsed HTML
        extract_text_fn: Function to extract text from elements
        extract_attribute_fn: Function to extract attributes from elements

    Returns:
        List of investigation metadata dictionaries
    """
    investigations: List[Dict[str, Any]] = []

    # Find investigation entries
    # ATSB uses various CSS classes for investigation listings
    entries = soup.select(".view-content .views-row, .investigation-item, .report-item")

    if not entries:
        # Try alternative selectors
        entries = soup.select("article, .node--type-investigation")

    for entry in entries:
        try:
            investigation = parse_investigation_entry(
                entry, extract_text_fn, extract_attribute_fn
            )
            if investigation:
                investigations.append(investigation)
        except Exception as e:
            logger.warning(f"Failed to parse investigation entry: {e}")
            continue

    return investigations


def parse_investigation_entry(
    entry: Any,
    extract_text_fn: callable,
    extract_attribute_fn: callable,
) -> Optional[Dict[str, Any]]:
    """
    Parse a single investigation entry from HTML.

    Args:
        entry: BeautifulSoup element for the investigation
        extract_text_fn: Function to extract text from elements
        extract_attribute_fn: Function to extract attributes from elements

    Returns:
        Dictionary of investigation metadata or None
    """
    # Extract ATSB ID (report number)
    atsb_id = None
    id_selectors = [
        ".field--name-field-report-number",
        ".report-number",
        ".investigation-id",
        "h2 a",
        "h3 a",
    ]
    for selector in id_selectors:
        atsb_id = extract_text_fn(entry, selector)
        if atsb_id:
            # Clean up the ID
            atsb_id = re.sub(r"[^\w-]", "", atsb_id.strip())
            break

    if not atsb_id:
        return None

    # Extract title
    title = extract_text_fn(entry, "h2, h3, .title, .field--name-title")

    # Extract report URL
    report_url = extract_attribute_fn(entry, "h2 a, h3 a, .title a", "href")
    if report_url:
        report_url = urljoin(BASE_URL, report_url)

    # Extract date
    date_str = extract_text_fn(
        entry, ".date, .field--name-field-occurrence-date, .occurrence-date"
    )
    occurrence_date = parse_date(date_str)

    # Extract location
    location = extract_text_fn(entry, ".location, .field--name-field-location")

    # Extract vessel name
    vessel_name = extract_text_fn(entry, ".vessel-name, .field--name-field-vessel-name")

    # Extract status
    status_text = extract_text_fn(
        entry, ".status, .field--name-field-investigation-status"
    )
    status = map_status(status_text)

    # Extract PDF link if available
    pdf_url = extract_attribute_fn(entry, "a[href*='.pdf'], .pdf-link a", "href")
    if pdf_url:
        pdf_url = urljoin(BASE_URL, pdf_url)

    return {
        "atsb_id": atsb_id,
        "title": title,
        "report_url": report_url,
        "occurrence_date": occurrence_date,
        "location": location,
        "vessel_name": vessel_name,
        "status": status,
        "pdf_url": pdf_url,
    }


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Parse date string in various formats.

    Args:
        date_str: Date string

    Returns:
        Parsed date or None
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try common Australian date formats
    formats = [
        "%d %B %Y",  # 15 January 2022
        "%d %b %Y",  # 15 Jan 2022
        "%d/%m/%Y",  # 15/01/2022
        "%Y-%m-%d",  # 2022-01-15
        "%B %d, %Y",  # January 15, 2022
        "%b %d, %Y",  # Jan 15, 2022
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_str}")
    return None


def map_status(status_text: Optional[str]) -> str:
    """
    Map ATSB status text to IncidentStatus enum value.

    Args:
        status_text: Status text from ATSB

    Returns:
        IncidentStatus value as string
    """
    if not status_text:
        return IncidentStatus.REPORTED.value

    status_lower = status_text.lower().strip()

    for key, value in STATUS_MAPPING.items():
        if key in status_lower:
            return value.value

    return IncidentStatus.REPORTED.value
