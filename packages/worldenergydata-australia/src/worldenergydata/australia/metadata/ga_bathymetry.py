"""Offline GA AusBathyTopo point-evidence adapter; no raster or network access.

Caller-supplied samples are assertions about extracted source data, not verified
retrievals. No digest is authenticated here. Retain the source bytes externally
and verify their digest before use. Results are screening estimates, not survey
water depths; field linkage remains explicit in well_enrichment.
"""

from __future__ import annotations

import copy
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict

from .well_enrichment import _measured_depth

# AusBathyTopo 250m (Australia) 2023: https://doi.org/10.26186/148758
SPECIFICATION_URL = (
    "https://knowledge.dea.ga.gov.au/data/external-data/ga-ausbathytopo-250m/"
)
# GA/DEA AusBathyTopo (2023), Specifications: product information and band table.
PRODUCT = "ga_ausbathytopo250m_2023"
NODATA = -32767
WGS84 = 4326


def _position(record: Dict[str, Any]) -> tuple[float, float]:
    sr = record.get("spatial_reference")
    if not isinstance(sr, dict) or sr.get("wkid") != WGS84:
        raise ValueError("position requires WGS84; transformation is not performed")
    values = []
    # EPSG:4326 geographic latitude/longitude domains (degrees), linked from the
    # GA/DEA 2023 product-information table at SPECIFICATION_URL.
    for key, limit in (("latitude", 90), ("longitude", 180)):
        value = record.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or abs(value) > limit
        ):
            raise ValueError("invalid position")
        values.append(float(value))
    return values[0], values[1]


def _validate_evidence(point: Dict[str, Any]) -> None:
    if (
        point.get("product") != PRODUCT
        or point.get("unit") != "m"
        or point.get("vertical_datum") != "MSL"
    ):
        raise ValueError("unqualified product, unit or vertical datum")
    digest = point.get("source_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("source SHA-256 required")
    timestamp = point.get("retrieved_at_utc")
    try:
        instant = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("retrieval timestamp required") from exc
    if instant.utcoffset() != timedelta(0):
        raise ValueError("retrieval timestamp requires UTC")
    _position(point)


def normalize_bathymetry_point(point: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an explicitly extracted 2023 height_depth point in metres.

    The point coordinates describe the extraction query, not a nearby cell
    centre. No interpolation, coordinate transformation or datum conversion is
    performed. Marine classification requires a caller-supplied source reference;
    elevation alone cannot establish it. Invalid extraction evidence raises;
    land/unknown classification, shoreline and NoData are NOT_EVALUATED.
    """
    _validate_evidence(point)
    if "height_depth" not in point:
        raise ValueError("height_depth band value required")
    elevation = point["height_depth"]
    if elevation is not None and (
        isinstance(elevation, bool)
        or not isinstance(elevation, (int, float))
        or not math.isfinite(elevation)
    ):
        raise ValueError("height_depth must be finite or null")
    # GA/DEA 2023 band table: metres relative to MSL, NoData=NODATA.
    # Depth below MSL is 0 - elevation at an explicitly qualified marine point.
    # Dry land may also lie below MSL. Zero is the datum origin, not a tolerance.
    qualification = point.get("marine_qualification")
    marine = (
        isinstance(qualification, dict)
        and qualification.get("classification") == "marine"
        and isinstance(qualification.get("source"), str)
        and bool(qualification["source"].strip())
    )
    submerged = (
        marine and elevation is not None and elevation != NODATA and elevation < 0
    )
    reason = "" if submerged else "missing, NoData or non-submerged elevation"
    if not marine:
        reason = "marine classification with source reference required"
    return {
        "status": "EVALUATED" if submerged else "NOT_EVALUATED",
        "reason": reason,
        "water_depth": -float(elevation) if submerged else None,
        "water_depth_unit": "m",
        "water_depth_datum": "MSL",
        "water_depth_origin": "bathymetry",
        "provenance": {
            **copy.deepcopy(point),
            "source_url": SPECIFICATION_URL,
            "attribution": "Geoscience Australia, AusBathyTopo (Australia) 2023",
            "licence": "CC-BY-4.0",
            "qualification": "caller-supplied grid estimate; source digest unverified",
        },
    }


def enrich_well_from_bathymetry(
    well: Dict[str, Any], point: Dict[str, Any]
) -> Dict[str, Any]:
    """Return a copy with an estimated depth only at the exact query position.

    Qualified existing well depths take priority. Raw NOPTA GDA94 positions
    cannot be passed as WGS84 without a separately established transformation.
    NoData preserves the original well; normalize separately for its reason.
    """
    normalized = normalize_bathymetry_point(point)
    if _position(well) != _position(point):
        raise ValueError("well position differs from sample query position")
    result = copy.deepcopy(well)
    if _measured_depth(well) is not None or normalized["status"] != "EVALUATED":
        return result
    for key in (
        "water_depth",
        "water_depth_unit",
        "water_depth_datum",
        "water_depth_origin",
    ):
        result[key] = normalized[key]
    result["bathymetry_provenance"] = normalized["provenance"]
    return result
