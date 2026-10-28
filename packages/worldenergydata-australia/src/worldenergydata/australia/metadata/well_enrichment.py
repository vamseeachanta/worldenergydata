"""Explicit per-well field enrichment; names and title polygons are not links."""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, Iterable, Optional


def _measured_depth(well: Dict[str, Any]) -> Optional[float]:
    value, unit = well.get("water_depth"), well.get("water_depth_unit")
    datum = well.get("water_depth_datum")
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or not isinstance(datum, str)
        or not datum.strip()
    ):
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
    fields. A depth is eligible only with a known unit and datum. Grid-derived depths
    retain their bathymetry origin and extraction provenance.
    """
    meta = dict(field_meta)
    name = meta.get("field_name", meta.get("field"))
    identifier = meta.get("well_identifier")
    linked = isinstance(name, str) and bool(name.strip())
    matches = [
        well
        for well in wells
        if linked
        and identifier
        and well.get("well_identifier") == identifier
        and well.get("field_name") == name
    ]
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
        grid_estimate = well.get("water_depth_origin") == "bathymetry"
        keep_measured = grid_estimate and origins["water_depth_m"] == "measured"
        if measured is not None and not keep_measured:
            meta["water_depth_m"] = measured
            meta["water_depth_datum"] = well["water_depth_datum"]
            origins["water_depth_m"] = (
                "bathymetry"
                if well.get("water_depth_origin") == "bathymetry"
                else "measured"
            )
            if origins["water_depth_m"] == "bathymetry":
                meta["bathymetry_provenance"] = copy.deepcopy(
                    well.get("bathymetry_provenance", {})
                )
            else:
                meta.pop("bathymetry_provenance", None)
        if _has_coordinates(well):
            meta.update(
                latitude=well["latitude"],
                longitude=well["longitude"],
                spatial_reference=well["spatial_reference"],
            )
            origins["coordinates"] = "measured"
    meta["value_origins"] = origins
    source = meta.get("enrichment_source_base", meta.get("source", "datavic"))
    meta["enrichment_source_base"] = source
    meta["source"] = (
        source + "; " + ", ".join(f"{key}={value}" for key, value in origins.items())
    )
    if origins["water_depth_m"] == "bathymetry":
        provenance = meta.get("bathymetry_provenance", {})
        meta["source"] += (
            f"; bathymetry_product={provenance.get('product', 'unknown')}"
            f"; source_sha256={provenance.get('source_sha256', 'unverified')}"
            "; grid estimate; source digest unverified"
        )
    return meta


def _has_coordinates(well: Dict[str, Any]) -> bool:
    lat, lon = well.get("latitude"), well.get("longitude")
    sr = well.get("spatial_reference")
    # NOPTA layer metadata (2026-10-11): EPSG:4283/GDA94. GA/DEA AusBathyTopo
    # 2023 product information: EPSG:4326/WGS84, at
    # https://knowledge.dea.ga.gov.au/data/external-data/ga-ausbathytopo-250m/
    # Both are retained in their original datum; no transformation is implied.
    return bool(
        isinstance(sr, dict)
        and sr.get("wkid") in {4283, 4326}
        and isinstance(lat, (int, float))
        and isinstance(lon, (int, float))
        and not isinstance(lat, bool)
        and not isinstance(lon, bool)
        and math.isfinite(lat)
        and math.isfinite(lon)
        and abs(lat) <= 90
        and abs(lon) <= 180
    )


def _fallback_origins(meta: Dict[str, Any], depth: Any) -> Dict[str, str]:
    previous = meta.get("value_origins", {})
    datum = meta.get("water_depth_datum")
    measured_depth = (
        previous.get("water_depth_m") in {"measured", "bathymetry"}
        and isinstance(datum, str)
        and bool(datum.strip())
    )
    depth_origin = previous["water_depth_m"] if measured_depth else "default"
    coordinates = "measured" if previous.get("coordinates") == "measured" else "default"
    return {
        "water_depth_m": depth_origin if depth is not None else "missing",
        "coordinates": coordinates if _has_coordinates(meta) else "missing",
    }
