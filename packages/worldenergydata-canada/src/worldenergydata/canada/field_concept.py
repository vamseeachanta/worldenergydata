"""Canada field metadata and supplied development wells -> FieldConcept.

Explicit metadata wins over the median non-null depth of linked wells, then
legacy defaults. Source markers distinguish supplied, aggregated and assumed
depths. No live source is contacted. Coordinates and UWIs stay on the well
records because FieldConcept has no corresponding fields.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from worldenergydata.canada.development_wells import (
    DevelopmentWell,
    summarize_field_wells,
)
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    dev_system_from_water_depth_m,
    number_from,
    to_field_concept,
)
from worldenergydata.fdas.core.config import DEFAULT_ASSUMPTIONS

# Representative water depth (m) per NL offshore field (C-NLOER / public record).
# Legacy fallback only: assumed, based on previous experience; not a measured
# result of development-well enrichment. Public source validation is deferred.
CANADA_WATER_DEPTH_M = {
    "hibernia": 80.0,
    "hebron": 93.0,
    "terra nova": 95.0,
    "white rose": 120.0,
    "north amethyst": 120.0,
}

# Explicit concepts prevent shallow FPSO/subsea fields being costed as dry-tree.
# These dev_system tokens select CAPEX profiles, not literal depth ranges.
CANADA_FIELD_CONCEPT = {
    "hibernia": {
        "concept": "gbs_dry_tree",
        "dev_system": "dry",
        "source": {
            "title": "C-NLOPB Decision 90.01: Hibernia Development Plan Update",
            "year": 1990,
            "url": "https://www.cnloer.ca/information/decisions/d1990_01_en/",
        },
    },
    "hebron": {
        "concept": "gbs_dry_tree",
        "dev_system": "dry",
        "source": {
            "title": "C-NLOPB Staff Analysis: Hebron Development Plan, section 6.5.1",
            "year": 2012,
            "url": "https://www.cnlopb.ca/wp-content/uploads/news/sahebdevplan.pdf",
        },
    },
    "terra nova": {
        "concept": "fpso_subsea",
        "dev_system": "subsea15",
        "source": {
            "title": "C-NLOPB Decision 97.02: Terra Nova Development Application",
            "year": 1997,
            "url": "https://www.cnlopb.ca/wp-content/uploads/news/d97_02e.pdf",
        },
    },
    "white rose": {
        "concept": "fpso_subsea",
        "dev_system": "subsea15",
        "source": {
            "title": "C-NLOPB Decision 2001.01: White Rose Development Application",
            "year": 2001,
            "url": "https://www.cnlopb.ca/wp-content/uploads/news/d01_01.pdf",
        },
        "note": (
            "This bucket represents the original FPSO/subsea development. "
            "The West White Rose extension adds a fixed wellhead platform "
            "tied back to the SeaRose FPSO; this is not a complete facility inventory."
        ),
        "note_source": {
            "title": "NL Government: Supports Restart of West White Rose Project",
            "year": 2022,
            "url": "https://www.gov.nl.ca/releases/2022/exec/0531n03/",
        },
    },
    "north amethyst": {
        "concept": "fpso_subsea_tieback",
        "dev_system": "subsea15",
        "source": {
            "title": "C-NLOPB Decision 2008.03: North Amethyst Satellite Tie-back to SeaRose FPSO",
            "year": 2008,
            "url": "https://www.cnlopb.ca/wp-content/uploads/news/dec0803e.pdf",
        },
    },
}

_CONCEPT_DEV_SYSTEM = {
    "gbs_dry_tree": "dry",
    "fpso_subsea": "subsea15",
    "fpso_subsea_tieback": "subsea15",
}

_CANADA_MAPPING = FieldMetaMapping(
    {
        "name": FieldMapEntry("field_name"),
        "operator": FieldMapEntry("operator"),
        "region": FieldMapEntry("region"),
        "water_depth_m": FieldMapEntry("water_depth_m", number_from),
        "num_wells": FieldMapEntry("num_wells"),
        "data_source": FieldMapEntry("source"),
    }
)


def resolve_canada_dev_system(field_name: str, water_depth_m: Any) -> tuple[str, str]:
    """Resolve the economics bucket and its source using field concepts (#815).

    ``dry``, ``subsea15`` and ``subsea20`` are CashflowEngine CAPEX-profile
    buckets, not literal depth statements. Known GBS and FPSO/subsea concepts
    take precedence; unmapped fields retain the depth classifier and its
    ``unknown`` to ``subsea15`` fallback, labelled ``missing_depth_default``.
    Invalid curated concepts or bucket tokens raise ValueError rather than
    silently selecting the engine's default assumptions.
    """
    concept = CANADA_FIELD_CONCEPT.get(str(field_name).strip().lower())
    if concept is not None:
        dev_system = concept.get("dev_system")
        if (
            dev_system not in DEFAULT_ASSUMPTIONS["DEV_SYSTEM"]
            or dev_system == "default"
            or _CONCEPT_DEV_SYSTEM.get(concept.get("concept")) != dev_system
        ):
            raise ValueError("Invalid Canada field concept override")
        return dev_system, "field_concept_override"
    dev_system = dev_system_from_water_depth_m(water_depth_m)
    if dev_system == "unknown":
        return "subsea15", "missing_depth_default"
    return dev_system, "depth_classifier"


def canada_field_to_concept(
    field_meta: dict[str, Any], *, development_wells: Iterable[DevelopmentWell] = ()
):
    """Build a concept; supplied well count is inventory, not producing wells.

    Caller-supplied depth and well count take precedence over well metadata.
    Legacy depths are retained for compatibility, labelled as defaults rather
    than measurements. Inputs are not mutated and field joins are exact after
    case/whitespace normalization. Blank depth text is absent; malformed or
    nonfinite explicit depth raises ValueError before provenance is assigned.
    """
    meta = dict(field_meta)
    if "field_name" not in meta and "field" in meta:
        meta["field_name"] = meta["field"]
    meta["region"] = "canada"
    meta.setdefault("source", "cnloer")
    summary = summarize_field_wells(meta.get("field_name", ""), development_wells)
    raw_depth = meta.get("water_depth_m")
    if isinstance(raw_depth, str) and not raw_depth.strip():
        raw_depth = None
    depth = number_from(raw_depth)
    if raw_depth is not None and (depth is None or not math.isfinite(depth)):
        raise ValueError("water_depth_m must be a finite number or blank")
    meta["water_depth_m"] = depth
    depth_source = "provided"
    if meta.get("water_depth_m") is None:
        meta["water_depth_m"] = summary.water_depth_m
        depth_source = (
            "development_wells_median"
            if summary.water_depth_m is not None
            else "unknown"
        )
    if meta.get("water_depth_m") is None:
        key = str(meta.get("field_name", "")).strip().lower()
        if key in CANADA_WATER_DEPTH_M:
            meta["water_depth_m"] = CANADA_WATER_DEPTH_M[key]
            depth_source = "legacy_default"
    if meta.get("num_wells") is None and summary.num_wells:
        meta["num_wells"] = summary.num_wells
    provenance = [str(meta.get("source") or "cnloer"), f"water_depth={depth_source}"]
    if summary.sources:
        provenance.append("development_wells_inventory=" + ",".join(summary.sources))
    meta["source"] = "; ".join(provenance)
    return to_field_concept(meta, _CANADA_MAPPING)


def canada_field_meta_mapping() -> FieldMetaMapping:
    """Return the Canada C-NLOER FieldConcept mapping."""
    return _CANADA_MAPPING


def build_canada_field_concept(
    field_meta: dict[str, Any], *, development_wells: Iterable[DevelopmentWell] = ()
):
    """Alias for the #719 reference-chain terminology."""
    return canada_field_to_concept(field_meta, development_wells=development_wells)
