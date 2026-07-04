"""Norway (SODIR) field-metadata → FieldConcept normalizer (#716).

First real consumer of the F2 ``FieldMetaMapping`` (#715). Maps SODIR
``field_processor.process()`` output → a ``FieldConcept`` for concept screening.

F2's ``FieldMapEntry`` maps a SINGLE source key + transform, so country-specific
DERIVED fields are pre-computed here before the 1:1 mapping applies:
  - ``region`` is the constant ``"norway"`` — the basin priors key on
    ``"norway"``, NOT the SODIR sea-area ``main_area`` (review M1: mapping
    main_area would leave ``region_fit`` inert).
  - ``recoverable_reserves_mmboe`` combines recoverable oil (MMbbl) + gas
    (Bcf / 6) — field_processor exposes them separately (review M2). Returns
    None (field left unset) when both are absent — never a false 0.

Imports the fdas member at runtime via the shared namespace (root/members always
installed together), mirroring the established member→member pattern.

Issue: https://github.com/vamseeachanta/worldenergydata/issues/716
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    to_field_concept,
)

# ~6 Bcf of gas ≈ 1 MMboe (6:1 energy equivalence).
_GAS_BCF_PER_MMBOE = 6.0


def _combined_reserves_mmboe(processed: Dict[str, Any]) -> Optional[float]:
    """Recoverable oil (MMbbl) + gas (Bcf/6) → MMboe; None if both absent."""
    oil = processed.get("recoverable_oil_mmbbl")
    gas = processed.get("recoverable_gas_bcf")
    if oil is None and gas is None:
        return None
    return float(oil or 0.0) + float(gas or 0.0) / _GAS_BCF_PER_MMBOE


# 1:1 mapping over the pre-derived Norway meta dict (F2 FieldMetaMapping;
# validated against FieldConcept fields at construction).
_NORWAY_MAPPING = FieldMetaMapping(
    {
        "name": FieldMapEntry("field_name"),
        "operator": FieldMapEntry("operator"),
        "region": FieldMapEntry("region"),
        "water_depth_m": FieldMapEntry("water_depth_m"),
        "year_first_oil": FieldMapEntry("production_start_year"),
        "recoverable_reserves_mmboe": FieldMapEntry("recoverable_reserves_mmboe"),
        "data_source": FieldMapEntry("source"),
    }
)


def sodir_field_to_concept(processed: Dict[str, Any]):
    """Build a validated ``FieldConcept`` from SODIR ``field_processor`` output.

    Args:
        processed: a ``field_processor.process()`` record (keys ``field_name``,
            ``operator``, ``water_depth_m``, ``production_start_year``,
            ``recoverable_oil_mmbbl``, ``recoverable_gas_bcf`` …).

    Returns:
        FieldConcept (sparse — SODIR metadata populates name/operator/region/
        water depth/first oil/reserves; concept screening still works, coarse).
    """
    meta = dict(processed)
    meta["region"] = "norway"  # constant — NOT main_area (M1)
    reserves = _combined_reserves_mmboe(processed)
    if reserves is not None:
        meta["recoverable_reserves_mmboe"] = reserves
    return to_field_concept(meta, _NORWAY_MAPPING)


def norway_field_meta_mapping() -> FieldMetaMapping:
    """Return the Norway SODIR FieldConcept mapping."""
    return _NORWAY_MAPPING


def build_norway_field_concept(processed: Dict[str, Any]):
    """Alias for the #716 reference-chain terminology."""
    return sodir_field_to_concept(processed)
