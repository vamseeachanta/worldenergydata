# ABOUTME: Normalizes raw SubseaIQ scraped records to canonical field names.
# ABOUTME: Issue #1861 — preprocessing step before benchmark analysis.
"""
worldenergydata.subseaiq.analytics.normalize
=============================================

Maps variant field names from raw SubseaIQ scrapes to the canonical schema
expected by :mod:`digitalmodel.field_development.benchmarks`.

Raw SubseaIQ data may use inconsistent field names across different scrape
runs (e.g. ``"Water Depth (m)"`` vs ``"water_depth"`` vs ``"depth_m"``).
This module standardises them to a single dict schema.

Usage
-----
>>> from worldenergydata.subseaiq.analytics.normalize import normalize_project
>>> raw = {"Project Name": "Perdido", "Water Depth (m)": 2438, "Host Type": "Spar"}
>>> clean = normalize_project(raw)
>>> clean["name"]
'Perdido'
>>> clean["water_depth_m"]
2438.0
"""

from __future__ import annotations

from typing import Optional


# Mapping: canonical_key -> list of raw key variants (checked in order)
_FIELD_ALIASES: dict[str, list[str]] = {
    "name": ["name", "Project Name", "project_name", "field_name", "Field Name"],
    "operator": ["operator", "Operator", "company", "Company"],
    "water_depth_m": [
        "water_depth_m", "Water Depth (m)", "water_depth", "depth_m",
        "Water_Depth_m", "waterDepth",
    ],
    "concept_type": [
        "concept_type", "Host Type", "host_type", "Concept", "concept",
        "facility_type", "Facility Type",
    ],
    "tieback_distance_km": [
        "tieback_distance_km", "Tieback Distance (km)", "tieback_km",
        "tieback_distance", "Tieback_Distance_km",
    ],
    "num_wells": ["num_wells", "Wells", "wells", "Number of Wells", "well_count"],
    "num_trees": ["num_trees", "Trees", "trees", "Number of Trees", "tree_count"],
    "num_manifolds": [
        "num_manifolds", "Manifolds", "manifolds",
        "Number of Manifolds", "manifold_count",
    ],
    "fluid_type": ["fluid_type", "Fluid Type", "fluid", "Fluid"],
    "region": ["region", "Region", "basin", "Basin", "area", "Area"],
    "flowline_diameter_in": [
        "flowline_diameter_in", "Flowline Diameter (in)", "flowline_diameter",
        "Flowline_Diameter_in", "flowlineDiameter",
    ],
    "flowline_material": [
        "flowline_material", "Flowline Material", "flowline_mat",
        "Flowline_Material", "flowlineMaterial",
    ],
    "layout_type": [
        "layout_type", "Layout Type", "layout", "Layout",
        "subsea_layout", "Subsea Layout",
    ],
}


def normalize_project(raw: dict) -> dict:
    """Map a single raw SubseaIQ record to the canonical schema.

    Parameters
    ----------
    raw : dict
        A single project dict with potentially non-standard keys.

    Returns
    -------
    dict
        Dict with canonical keys (``name``, ``water_depth_m``, etc.).
        Missing fields are set to ``None``.

    Raises
    ------
    KeyError
        If no variant of the ``name`` field is found.
    """
    result: dict[str, object] = {}
    for canonical, aliases in _FIELD_ALIASES.items():
        val = _first_match(raw, aliases)
        if canonical == "name" and val is None:
            raise KeyError(
                f"No name field found in record. "
                f"Tried: {aliases}. Keys present: {list(raw.keys())}"
            )
        if val is not None and canonical in ("water_depth_m", "tieback_distance_km", "flowline_diameter_in"):
            val = _safe_float(val)
        elif val is not None and canonical in ("num_wells", "num_trees", "num_manifolds"):
            val = _safe_int(val)
        result[canonical] = val
    return result


def normalize_projects(raw_records: list[dict]) -> list[dict]:
    """Normalize a batch of raw SubseaIQ records.

    Parameters
    ----------
    raw_records : list[dict]
        Raw project dicts.

    Returns
    -------
    list[dict]
        Normalized dicts ready for :func:`benchmarks.load_projects`.
    """
    return [normalize_project(r) for r in raw_records]


def _first_match(d: dict, keys: list[str]) -> Optional[object]:
    """Return the value of the first matching key, or None."""
    for k in keys:
        if k in d:
            return d[k]
    return None


def _safe_float(val: object) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_int(val: object) -> Optional[int]:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None
