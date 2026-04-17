"""Per-vessel completeness scoring for fleet data quality."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Core fields that should be populated for a complete record
_DRILLING_RIG_CORE_FIELDS: tuple[str, ...] = (
    "VESSEL_NAME",
    "RIG_TYPE",
    "OWNER",
    "WATER_DEPTH_RATING_FT",
    "DRILLING_DEPTH_RATING_FT",
    "YEAR_BUILT",
    "DP_CLASS",
    "LOA_M",
    "BEAM_M",
    "IMO_NUMBER",
)

_CONSTRUCTION_VESSEL_CORE_FIELDS: tuple[str, ...] = (
    "VESSEL_NAME",
    "VESSEL_TYPE",
    "OWNER",
    "YEAR_BUILT",
    "LOA_M",
    "BEAM_M",
    "DP_CLASS",
    "IMO_NUMBER",
    "MAIN_CRANE_CAPACITY_T",
    "QUARTERS_CAPACITY",
)


def completeness_score(
    record: dict[str, Any],
    core_fields: tuple[str, ...],
) -> float:
    """Calculate completeness score (0.0 to 1.0) for a record.

    Score = (number of non-None core fields) / (total core fields)
    """
    if not core_fields:
        return 0.0
    filled = sum(1 for f in core_fields if record.get(f) is not None)
    return filled / len(core_fields)


def fleet_completeness_report(
    records: list[dict[str, Any]],
    vessel_category: str = "drilling_rig",
) -> dict[str, Any]:
    """Generate a completeness report for a fleet.

    Returns a dict with per-field and aggregate statistics.
    """
    core_fields = (
        _DRILLING_RIG_CORE_FIELDS
        if vessel_category == "drilling_rig"
        else _CONSTRUCTION_VESSEL_CORE_FIELDS
    )

    if not records:
        return {
            "total_records": 0,
            "avg_completeness": 0.0,
            "field_coverage": {},
        }

    scores = [completeness_score(r, core_fields) for r in records]

    field_coverage: dict[str, float] = {}
    for field_name in core_fields:
        filled = sum(1 for r in records if r.get(field_name) is not None)
        field_coverage[field_name] = filled / len(records)

    avg = sum(scores) / len(scores) if scores else 0.0

    report = {
        "total_records": len(records),
        "avg_completeness": round(avg, 4),
        "min_completeness": round(min(scores), 4) if scores else 0.0,
        "max_completeness": round(max(scores), 4) if scores else 0.0,
        "field_coverage": {k: round(v, 4) for k, v in field_coverage.items()},
    }

    logger.info(
        "Completeness: %d records, avg %.1f%%, min %.1f%%, max %.1f%%",
        len(records),
        avg * 100,
        report["min_completeness"] * 100,
        report["max_completeness"] * 100,
    )

    return report
