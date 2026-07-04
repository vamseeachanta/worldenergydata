"""Suite B — FieldConcept metadata normalizer (#715).

Verifies the B2 fix: the mapping carries per-field transform CALLABLES (not a
naive rename), so subseaiq's fluid/year/float logic and the concept-priority
reduction are preserved. Also checks the ft↔m dev-system conversion boundaries
and fail-loud on unknown target fields.
"""

import pytest

from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    dev_system_from_water_depth_m,
    fluid_from_reserve_type,
    number_from,
    reduce_concept_type,
    to_field_concept,
    year_from,
)
from worldenergydata.field_development.enums import ConceptType, FluidType
from worldenergydata.field_development.models import FieldConcept

# --- transforms preserved (no declarative-map regression) ------------------


def test_fluid_oil_primary_for_mixed():
    assert fluid_from_reserve_type("Oil and Gas") == FluidType.OIL
    assert fluid_from_reserve_type("condensate") == FluidType.CONDENSATE
    assert fluid_from_reserve_type("gas") == FluidType.GAS
    assert fluid_from_reserve_type("") is None


def test_year_regex_extraction():
    assert year_from("Production start 1996 (Q3)") == 1996
    assert year_from("2011-05-01") == 2011
    assert year_from("n/a") is None


def test_number_comma_stripped():
    assert number_from("1,270.5") == 1270.5
    assert number_from("300") == 300.0
    assert number_from(None) is None
    assert number_from("deep") is None


# --- dev-system conversion (ft vs m) ---------------------------------------


def test_dev_system_from_water_depth_boundaries():
    assert dev_system_from_water_depth_m(152) == "dry"  # 498.7 ft < 500
    assert dev_system_from_water_depth_m(1000) == "subsea15"  # 3281 ft
    assert dev_system_from_water_depth_m(1830) == "subsea20"  # 6004 ft >= 6000
    assert dev_system_from_water_depth_m(None) == "unknown"
    assert dev_system_from_water_depth_m("1,270") == "subsea15"  # comma-string coerced


def test_dev_system_vocab_is_canonical():
    vocab = {"dry", "subsea15", "subsea20", "unknown"}
    for wd in (10, 152, 900, 1830, 5000, None):
        assert dev_system_from_water_depth_m(wd) in vocab


# --- concept-priority reduction (subsea-tieback wins) ----------------------


def test_reduce_concept_type_tieback_wins():
    got = reduce_concept_type([ConceptType.SPAR, ConceptType.SUBSEA_TIEBACK])
    assert got == ConceptType.SUBSEA_TIEBACK


def test_reduce_concept_type_host_when_no_tieback():
    got = reduce_concept_type([ConceptType.FIXED_JACKET, ConceptType.SPAR])
    assert got == ConceptType.SPAR  # spar higher priority than fixed jacket


def test_reduce_concept_type_empty():
    assert reduce_concept_type([]) is None


# --- mapping + to_field_concept -------------------------------------------


def _norway_mapping():
    return FieldMetaMapping(
        {
            "name": FieldMapEntry("fldName"),
            "operator": FieldMapEntry("fldOperatorName"),
            "region": FieldMapEntry("main_area"),
            "water_depth_m": FieldMapEntry("fldWaterDepth", number_from),
            "year_first_oil": FieldMapEntry("production_start", year_from),
            "fluid_type": FieldMapEntry("reserve_type", fluid_from_reserve_type),
            "recoverable_reserves_mmboe": FieldMapEntry("reserves", number_from),
        }
    )


def test_to_field_concept_builds_valid_concept():
    meta = {
        "fldName": "Aasta Hansteen",
        "fldOperatorName": "Equinor",
        "main_area": "Norwegian Sea",
        "fldWaterDepth": "1,270",
        "production_start": "Production start 2018",
        "reserve_type": "Gas",
        "reserves": "50.0",
    }
    fc = to_field_concept(meta, _norway_mapping())
    assert isinstance(fc, FieldConcept)
    assert fc.name == "Aasta Hansteen"
    assert fc.operator == "Equinor"
    assert fc.water_depth_m == 1270.0
    assert fc.year_first_oil == 2018
    assert fc.fluid_type == FluidType.GAS
    assert fc.recoverable_reserves_mmboe == 50.0


def test_none_transform_result_dropped():
    # missing/garbage source values → field simply unset (name still required)
    meta = {"fldName": "X", "fldWaterDepth": "deep"}
    fc = to_field_concept(meta, _norway_mapping())
    assert fc.name == "X"
    assert fc.water_depth_m is None  # 'deep' → number_from None → dropped


def test_unknown_target_field_rejected_at_construction():
    with pytest.raises(ValueError, match="not on FieldConcept"):
        FieldMetaMapping({"waterdepth_m": FieldMapEntry("x")})  # typo


def test_missing_name_fails_validation():
    from pydantic import ValidationError

    mapping = FieldMetaMapping({"operator": FieldMapEntry("op")})
    with pytest.raises(ValidationError):
        to_field_concept({"op": "Equinor"}, mapping)  # no name → invalid
