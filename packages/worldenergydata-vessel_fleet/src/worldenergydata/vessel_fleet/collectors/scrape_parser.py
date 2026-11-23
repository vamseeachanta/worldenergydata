"""Parse Puppeteer scrape JSON data for Noble and Seadrill.

Extracts rig data from the ``rawHtml`` text content and ``links`` array
produced by the Puppeteer fleet-page scraper, then maps to
DrillingRigSchema-compatible dicts with UPPERCASE column names.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Water depth classification thresholds (feet)
# ---------------------------------------------------------------------------
_JACKUP_MAX_FT = 500.0
_DRILLSHIP_MIN_FT = 10000.0


def classify_rig_type_by_water_depth(water_depth_ft: float) -> str:
    """Classify rig type by water depth rating.

    <=500 ft  -> jack_up
    500-10000 -> semi_submersible
    >=10000   -> drillship
    """
    if water_depth_ft <= _JACKUP_MAX_FT:
        return "jack_up"
    if water_depth_ft >= _DRILLSHIP_MIN_FT:
        return "drillship"
    return "semi_submersible"


def parse_water_depth_string(value: Optional[str]) -> Optional[float]:
    """Parse water depth strings like '12,000 ft' to float.

    Handles commas, 'ft', 'ft.' suffixes, and extra whitespace.
    Returns None for non-numeric or empty inputs.
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    # Strip unit suffixes
    s = re.sub(r"\s*(ft\.?|feet)\s*$", "", s, flags=re.IGNORECASE).strip()
    # Remove commas
    s = s.replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Noble Corporation parser
# ---------------------------------------------------------------------------
# Noble rawHtml pattern per rig (observed structure):
# "{RigName}Rig Summary {Design} Currently in {Location} {WD} ft Water Depth
#  Available: {Date} Download Summary PDF"
_NOBLE_RIG_PATTERN = re.compile(
    r"(?P<name>[A-Z][A-Za-z ]+?)"  # Rig name (starts with uppercase)
    r"Rig Summary\s+"  # Separator
    r"(?P<design>.+?)\s+"  # Design class
    r"Currently in\s+(?P<location>.+?)\s+"  # Location
    r"(?P<wd>[\d,]+)\s*ft\s+Water Depth\s*"  # Water depth
    r"Available:\s*(?P<avail>[^\s]+(?:\s+[^\s]+)?)\s+"  # Availability
    r"Download Summary PDF"  # Trailer
)


def _extract_noble_pdf_links(links: list[dict[str, str]]) -> dict[str, str]:
    """Build a mapping from rig name to spec PDF URL.

    Noble links alternate: Rig Summary (detail page), Download Summary PDF.
    We extract the PDF links and associate them with the preceding rig page URL
    to derive the rig name.
    """
    pdf_map: dict[str, str] = {}
    # Fleet detail page URLs contain the rig name slug
    # e.g. .../fleet-details/2024/Ocean-Apex/default.aspx
    rig_detail_re = re.compile(r"/fleet-details/\d{4}/([^/]+)/default\.aspx$")

    pending_name: Optional[str] = None
    for link in links:
        href = link.get("href", "")
        text = link.get("text", "")

        if text == "Rig Summary":
            match = rig_detail_re.search(href)
            if match:
                slug = match.group(1)
                # Convert slug to name: "Ocean-Apex" -> "Ocean Apex"
                pending_name = slug.replace("-", " ").strip()
        elif text == "Download Summary PDF" and pending_name:
            pdf_map[pending_name] = href
            pending_name = None

    return pdf_map


def _normalize_noble_name(raw_name: str) -> str:
    """Normalize rig name extracted from rawHtml.

    Handles variations like 'Noble Resolve ' (trailing space) and
    'Noble Gerry de Souza' (multi-word).
    """
    return raw_name.strip()


def parse_noble_scrape(json_path: Path) -> list[dict[str, Any]]:
    """Parse Noble Corporation scrape JSON into vessel fleet records.

    Reads the JSON file, extracts rig data from the ``rawHtml`` text,
    and matches each rig with its spec PDF link from the ``links`` array.

    Returns a list of dicts with DrillingRigSchema-compatible field names.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Noble scrape file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_html = data.get("rawHtml", "")
    links = data.get("links", [])

    if not raw_html:
        return []

    # Build PDF link mapping
    pdf_links = _extract_noble_pdf_links(links)

    # Parse rig entries from rawHtml
    records: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for match in _NOBLE_RIG_PATTERN.finditer(raw_html):
        name = _normalize_noble_name(match.group("name"))
        if name in seen_names:
            continue
        seen_names.add(name)

        design = match.group("design").strip()
        wd_str = match.group("wd").strip()
        water_depth = parse_water_depth_string(wd_str)

        # Classify rig type by water depth
        rig_type = None
        if water_depth is not None:
            rig_type = classify_rig_type_by_water_depth(water_depth)

        # Find matching PDF link
        pdf_url = _match_pdf_link(name, pdf_links)

        record: dict[str, Any] = {
            "VESSEL_NAME": name,
            "VESSEL_CATEGORY": "drilling_rig",
            "OWNER": "Noble Corporation plc",
            "DATA_SOURCE": "contractor_fleet_page",
            "RIG_DESIGN": design,
        }

        if water_depth is not None:
            record["WATER_DEPTH_RATING_FT"] = water_depth
        if rig_type is not None:
            record["RIG_TYPE"] = rig_type
        if pdf_url:
            record["DATA_SOURCE_URL"] = pdf_url

        records.append(record)

    logger.info("Parsed %d Noble rigs from scrape JSON", len(records))
    return records


def _strip_owner_prefix(name: str) -> str:
    """Strip owner-style prefixes from rig names for matching.

    Noble fleet has historical naming: URL slugs may use 'Ocean',
    'Maersk', or 'Noble', while rawHtml may use a different prefix.
    Strip to the core identifier for fuzzy matching.
    """
    prefixes = ("noble ", "ocean ", "maersk ")
    lower = name.lower().strip()
    for prefix in prefixes:
        if lower.startswith(prefix):
            return name[len(prefix) :].strip()
    return name.strip()


def _match_pdf_link(
    rig_name: str,
    pdf_links: dict[str, str],
) -> Optional[str]:
    """Match a rig name to its PDF URL from the extracted links.

    Handles naming differences between rawHtml and URL slugs. Noble
    URLs may use legacy prefixes (Ocean, Maersk) while the page text
    uses current names (Noble). Matches on the core rig identifier.
    """
    # Direct match
    if rig_name in pdf_links:
        return pdf_links[rig_name]

    # Case-insensitive match
    normalized = rig_name.lower().strip()
    for slug_name, url in pdf_links.items():
        if slug_name.lower().strip() == normalized:
            return url

    # Strip owner prefixes and match on core name
    core = _strip_owner_prefix(rig_name).lower()
    for slug_name, url in pdf_links.items():
        slug_core = _strip_owner_prefix(slug_name).lower()
        if core == slug_core:
            return url

    # Partial match: one core name contains the other
    for slug_name, url in pdf_links.items():
        slug_core = _strip_owner_prefix(slug_name).lower()
        if core in slug_core or slug_core in core:
            return url

    # Last resort: match rig name against the PDF filename itself
    # Handles renamed rigs where URL slug differs from current name
    name_parts = core.replace(" ", "-").lower()
    for slug_name, url in pdf_links.items():
        filename = url.rsplit("/", 1)[-1].lower()
        if name_parts in filename:
            return url

    return None


# ---------------------------------------------------------------------------
# Seadrill parser
# ---------------------------------------------------------------------------
# Seadrill rawHtml pattern per rig:
# "{RigName} TYPE {Type}AVAILABILITY {Date}OWNERSHIP {Owner} Technical Sheet"
_SEADRILL_RIG_PATTERN = re.compile(
    r"(?P<name>[A-Z][A-Za-z ]+?)\s+"
    r"TYPE\s+(?P<type>[A-Za-z -]+?)"
    r"AVAILABILITY\s+(?P<avail>[A-Za-z0-9 ]+?)"
    r"OWNERSHIP\s+(?P<owner>[A-Za-z .]+?)\s+"
    r"Technical Sheet"
)

# Seadrill type label -> normalized rig type
_SEADRILL_TYPE_MAP: dict[str, str] = {
    "drillship": "drillship",
    "semi-submersible": "semi_submersible",
    "jack-up": "jack_up",
}


def _extract_seadrill_tech_sheet_links(
    links: list[dict[str, str]],
) -> list[str]:
    """Extract Technical Sheet PDF URLs in order from links."""
    return [
        link["href"]
        for link in links
        if link.get("text") == "Technical Sheet"
        and link.get("href", "").endswith(".pdf")
    ]


def _normalize_seadrill_rig_type(raw_type: str) -> str:
    """Normalize Seadrill rig type labels.

    E.g., 'Semi-submersible' -> 'semi_submersible',
          'Drillship ' -> 'drillship'.
    """
    cleaned = raw_type.strip().lower()
    return _SEADRILL_TYPE_MAP.get(cleaned, cleaned.replace("-", "_"))


def parse_seadrill_scrape(json_path: Path) -> list[dict[str, Any]]:
    """Parse Seadrill scrape JSON into vessel fleet records.

    Reads the JSON file, extracts rig data from the ``rawHtml`` text,
    and matches each rig with its Technical Sheet PDF link.

    Returns a list of dicts with DrillingRigSchema-compatible field names.
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Seadrill scrape file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_html = data.get("rawHtml", "")
    links = data.get("links", [])

    if not raw_html:
        return []

    # Extract tech sheet URLs in order
    tech_sheet_urls = _extract_seadrill_tech_sheet_links(links)

    # Parse rig entries from rawHtml
    records: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    url_idx = 0
    for match in _SEADRILL_RIG_PATTERN.finditer(raw_html):
        name = match.group("name").strip()
        tech_url = tech_sheet_urls[url_idx] if url_idx < len(tech_sheet_urls) else None
        url_idx += 1
        if name in seen_names:
            continue
        seen_names.add(name)

        raw_type = match.group("type").strip()
        owner = match.group("owner").strip()
        rig_type = _normalize_seadrill_rig_type(raw_type)

        record: dict[str, Any] = {
            "VESSEL_NAME": name,
            "VESSEL_CATEGORY": "drilling_rig",
            "OWNER": owner,
            "DATA_SOURCE": "contractor_fleet_page",
            "RIG_TYPE": rig_type,
        }

        if tech_url:
            record["DATA_SOURCE_URL"] = tech_url

        records.append(record)

    logger.info("Parsed %d Seadrill rigs from scrape JSON", len(records))
    return records
