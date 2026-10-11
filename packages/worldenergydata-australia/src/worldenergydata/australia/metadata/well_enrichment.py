"""Explicit per-well field enrichment; names and title polygons are not links."""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Optional


def _measured_depth(well: Dict[str, Any]) -> Optional[float]:
    value, unit = well.get("water_depth"), well.get("water_depth_unit")
    datum = well.get("water_depth_datum")
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0
            or not isinstance(datum, str) or not datum.strip()):
        return None
    if unit not in {"m", "ft"}:
        return None
    return float(value) * (0.3048 if unit == "ft" else 1)


def enrich_field_metadata(
    field_meta: Dict[str, Any], wells: Iterable[Dict[str, Any]]
) -> Dict[str, Any]:
    """Select a caller-linked representative well, preserving fallback values.

    No averaging or automatic field-name matching is performed. Coordinates are
    retained with their datum in this metadata; FieldConcept has no coordinate
    fields. A measured depth is eligible only with a known unit and datum.
    """
    meta = dict(field_meta)
    name = meta.get("field_name", meta.get("field"))
    identifier = meta.get("well_identifier")
    linked = isinstance(name, str) and bool(name.strip())
    matches = [well for well in wells if linked and identifier and
               well.get("well_identifier") == identifier and well.get("field_name") == name]
    if len(matches) > 1:
        raise ValueError("ambiguous representative well")
    depth = meta.get("water_depth_m")
    if isinstance(depth, (int, float)) and not math.isfinite(depth):
        depth = None
    meta["water_depth_m"] = depth
    origins = _fallback_origins(meta, depth)
    if matches:
        well = matches[0]
        measured = _measured_depth(well)
        if measured is not None:
            meta["water_depth_m"] = measured
            meta["water_depth_datum"] = well["water_depth_datum"]
            origins["water_depth_m"] = "measured"
        if _has_coordinates(well):
            meta.update(latitude=well["latitude"], longitude=well["longitude"],
                        spatial_reference=well["spatial_reference"])
            origins["coordinates"] = "measured"
    meta["value_origins"] = origins
    source = meta.get("enrichment_source_base", meta.get("source", "datavic"))
    meta["enrichment_source_base"] = source
    meta["source"] = source + "; " + ", ".join(f"{key}={value}" for key, value in origins.items())
    return meta


def _has_coordinates(well: Dict[str, Any]) -> bool:
    lat, lon = well.get("latitude"), well.get("longitude")
    sr = well.get("spatial_reference")
    return bool(sr and sr.get("wkid") == 4283 and isinstance(lat, (int, float)) and
                isinstance(lon, (int, float)) and not isinstance(lat, bool) and
                not isinstance(lon, bool) and math.isfinite(lat) and math.isfinite(lon) and
                abs(lat) <= 90 and abs(lon) <= 180)


def _fallback_origins(meta: Dict[str, Any], depth: Any) -> Dict[str, str]:
    previous = meta.get("value_origins", {})
    datum = meta.get("water_depth_datum")
    measured_depth = (previous.get("water_depth_m") == "measured" and
                      isinstance(datum, str) and bool(datum.strip()))
    depth_origin = "measured" if measured_depth else "default"
    coordinates = "measured" if previous.get("coordinates") == "measured" else "default"
    return {"water_depth_m": depth_origin if depth is not None else "missing",
            "coordinates": coordinates if _has_coordinates(meta) else "missing"}
