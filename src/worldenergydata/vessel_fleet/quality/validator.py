"""Cross-field validation rules for vessel fleet data."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single vessel record."""

    vessel_name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_drilling_rig(record: dict[str, Any]) -> ValidationResult:
    """Validate a drilling rig record with cross-field rules."""
    name = record.get("VESSEL_NAME", "UNKNOWN")
    result = ValidationResult(vessel_name=name)

    rig_type = record.get("RIG_TYPE")
    water_depth = record.get("WATER_DEPTH_RATING_FT")
    dp_class = record.get("DP_CLASS")
    year_built = record.get("YEAR_BUILT")
    displacement = record.get("DISPLACEMENT_TONNES")
    record.get("IS_OFFSHORE")

    # Jackups should not have DP > 1 (most are moored)
    if rig_type == "jack_up" and dp_class is not None and dp_class > 1:
        result.warnings.append(f"Jack-up with DP class {dp_class} is unusual")

    # Onshore/land rigs should not have displacement
    if rig_type == "land_rig" and displacement is not None:
        result.warnings.append("Land rig should not have displacement")

    # Water depth range check
    if water_depth is not None:
        if water_depth < 0:
            result.errors.append(f"Negative water depth: {water_depth}")
        elif water_depth > 40000:
            result.errors.append(f"Water depth > 40,000 ft: {water_depth}")

    # Year built range
    if year_built is not None:
        if year_built < 1950:
            result.warnings.append(f"Year built before 1950: {year_built}")
        elif year_built > 2030:
            result.errors.append(f"Year built in future: {year_built}")

    # IMO format
    imo = record.get("IMO_NUMBER")
    if imo and (not imo.isdigit() or len(imo) != 7):
        result.errors.append(f"Invalid IMO number format: {imo}")

    return result


def validate_construction_vessel(record: dict[str, Any]) -> ValidationResult:
    """Validate a construction vessel record."""
    name = record.get("VESSEL_NAME", "UNKNOWN")
    result = ValidationResult(vessel_name=name)

    crane_cap = record.get("MAIN_CRANE_CAPACITY_T")
    water_depth = record.get("WATER_DEPTH_RATING_M")
    year_built = record.get("YEAR_BUILT")

    # Crane capacity sanity (largest is Sleipnir at ~10,000t each, dual)
    if crane_cap is not None and crane_cap > 25000:
        result.warnings.append(f"Crane capacity > 25,000t: {crane_cap}")

    # Water depth range
    if water_depth is not None:
        if water_depth < 0:
            result.errors.append(f"Negative water depth: {water_depth}")
        elif water_depth > 5000:
            result.warnings.append(f"Water depth > 5,000m: {water_depth}")

    # Year built
    if year_built is not None:
        if year_built < 1950:
            result.warnings.append(f"Year built before 1950: {year_built}")
        elif year_built > 2030:
            result.errors.append(f"Year built in future: {year_built}")

    # IMO format
    imo = record.get("IMO_NUMBER")
    if imo and (not imo.isdigit() or len(imo) != 7):
        result.errors.append(f"Invalid IMO number format: {imo}")

    return result


def validate_fleet(
    records: list[dict[str, Any]],
    vessel_category: str = "drilling_rig",
) -> list[ValidationResult]:
    """Validate a fleet of records. Returns list of results."""
    validate_fn = (
        validate_drilling_rig
        if vessel_category == "drilling_rig"
        else validate_construction_vessel
    )
    results = [validate_fn(r) for r in records]

    valid = sum(1 for r in results if r.is_valid)
    logger.info(
        "Validation: %d/%d records valid (%d errors, %d warnings)",
        valid,
        len(results),
        sum(len(r.errors) for r in results),
        sum(len(r.warnings) for r in results),
    )
    return results
