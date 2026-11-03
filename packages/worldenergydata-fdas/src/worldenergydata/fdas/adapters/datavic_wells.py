"""Read complete local DataVic pet_wells WFS GeoJSON exports, without I/O.

Source field names: DataVic DescribeFeatureType, pet_wells, observed 2026-10-20:
https://opendata.maps.vic.gov.au/geoserver/wfs?service=WFS&version=2.0.0&request=DescribeFeatureType&typeNames=open-data-platform:pet_wells
Units and field membership are NOT established by that schema. Both require
caller evidence. rig_release_date is deliberately not a drilling duration.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

from .wells import WellRecord, require_text

# NIST, U.S. Survey Foot: Revised Unit Conversion Factors (2023 adoption),
# table row "foot (ft)", international foot metric equivalent (exact):
# https://www.nist.gov/pml/us-surveyfoot/revised-unit-conversion-factors
METRES_PER_INTERNATIONAL_FOOT = 0.3048


class DataVicInputError(ValueError):
    """A source export cannot be interpreted under the wells contract."""


@dataclass(frozen=True)
class DataVicWells:
    """Normalized records tied to the exact caller-retained export bytes."""

    wells: tuple[WellRecord, ...]
    raw_sha256: str
    source_record_ids: tuple[str, ...]


def _spud(value: str | None) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DataVicInputError("spud_date must be an ISO date or datetime")
    try:
        # Preserve the source calendar day rather than shifting to UTC.
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise ValueError("Invalid spud_date") from exc


def _unique_object(pairs: list) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise DataVicInputError(f"Duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _collection(raw: bytes) -> dict:
    obj = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(obj, dict) or obj.get("type") != "FeatureCollection":
        raise ValueError("Expected GeoJSON FeatureCollection")
    features = obj.get("features")
    if not isinstance(features, list):
        raise DataVicInputError("Missing features")
    counts = [obj.get("numberMatched"), obj.get("numberReturned")]
    if any(type(count) is not int or count != len(features) for count in counts):
        raise ValueError("Complete export with matching integer counts required")
    links = obj.get("links", [])
    if not isinstance(links, list) or any(not isinstance(link, dict) for link in links):
        raise DataVicInputError("Invalid collection links")
    if any(link.get("rel") == "next" for link in links):
        raise ValueError("Partial export has a next page")
    return obj


def _well(feature: dict, links: Mapping[str, str], unit: str | None) -> WellRecord:
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise ValueError("Expected GeoJSON Feature")
    props = feature.get("properties")
    if not isinstance(props, dict):
        raise DataVicInputError("Missing well properties")
    site_id = props.get("siteid")
    if type(site_id) is not int:
        raise ValueError("siteid must be an integer")
    identifier = str(site_id)
    if identifier not in links:
        raise ValueError(f"Missing explicit development link for siteid {identifier}")
    depth = props.get("abswaterdepth")
    if depth is not None:
        # Validate raw depth even when its unit is unknown.
        WellRecord(
            "AU", "datavic-pet-wells", identifier, links[identifier], None, depth
        )
        if unit == "ft":
            depth *= METRES_PER_INTERNATIONAL_FOOT
        elif unit is None:
            depth = None
    return WellRecord(
        "AU",
        "datavic-pet-wells",
        identifier,
        links[identifier],
        _spud(props.get("spud_date")),
        depth,
    )


def read_datavic_wells(
    raw: bytes,
    *,
    development_by_site_id: Mapping[str, str],
    water_depth_unit: str | None,
) -> DataVicWells:
    """Normalize a complete export of the caller's selected WFS query.

    The caller retains raw bytes, query URL, retrieval UTC time, source vintage,
    licence and evidence for field links and units. This is not a downloader or
    a claim of national coverage. An unknown depth unit yields None.
    """
    if water_depth_unit not in {None, "m", "ft"}:
        raise ValueError("water_depth_unit must be m, ft (international), or None")
    features = _collection(raw)["features"]
    wells, record_ids, seen = [], [], set()
    for feature in features:
        row = _well(feature, development_by_site_id, water_depth_unit)
        record_id = feature.get("id")
        require_text(record_id, "source record id")
        if row.key in seen or record_id in record_ids:
            raise ValueError("Duplicate well or source record id")
        seen.add(row.key)
        wells.append(row)
        record_ids.append(record_id)
    return DataVicWells(
        tuple(wells), hashlib.sha256(raw).hexdigest(), tuple(record_ids)
    )
