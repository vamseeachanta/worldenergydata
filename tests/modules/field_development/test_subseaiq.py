"""Parser and crosswalk contracts use independently constructed synthetic rows."""

import pytest

from worldenergydata.field_development import (
    ConceptType,
    FieldConcept,
    FluidType,
    bsee_block_key,
    build_bsee_crosswalk,
    crosswalk_summary,
    load_subseaiq_fields,
)
from worldenergydata.field_development.subseaiq import HOST_TYPE_MAP, key_to_code


@pytest.mark.parametrize(
    "text,key",
    [
        ("Green Canyon 123", ("GC", 123)),
        ("MC26", ("MC", 26)),
        ("GC 123", ("GC", 123)),
        ("Mississippi Canyon 108, 109", ("MC", 108)),
        ("WD030", ("WD", 30)),
        ("East Breaks 602", ("EB", 602)),
        ("Main Pass Block 123", ("MP", 123)),
        ("Galveston Area 255", ("GA", 255)),
        ("PL 218 - 6706/12", None),
        ("", None),
    ],
)
def test_public_area_code_parser(text, key):
    assert bsee_block_key(text) == key


def test_key_to_code_roundtrip():
    assert key_to_code(("GC", 123)) == "GC123"


@pytest.fixture
def sources(tmp_path):
    fields = tmp_path / "fields.csv"
    fields.write_text(
        "FIELD_ID,FIELD_NAME,COUNTRY,BLOCK,RESERVE_TYPE,WATER_DEPTH_M,US_GOM_FLAG\n"
        "1,Synthetic Alpha,US,GC123,Oil,123,Y\n"
        "2,Synthetic Beta,US,MC456,Gas,456,Y\n"
        "3,Synthetic Gamma,Norway,Unmapped region,Gas,,\n"
        "4,,US,GC123,Oil,10,Y\n"
    )
    facilities = tmp_path / "facilities.csv"
    facilities.write_text(
        "FACILITY_ID,HOST_TYPE,OPERATOR\n"
        "1,SPAR,Synthetic operator\n"
        "1,Subsea Tieback,Synthetic operator\n"
        "2,TLP,Synthetic operator\n"
    )
    return fields, facilities


def test_explicit_input_loads_typed_concepts(sources):
    fields = load_subseaiq_fields(sources[0])
    assert len(fields) == 3
    assert all(isinstance(f, FieldConcept) for f in fields)
    assert fields[0].name == "Synthetic Alpha"
    assert fields[0].water_depth_m == 123
    assert fields[0].fluid_type == FluidType.OIL
    assert fields[2].water_depth_m is None
    assert all(f.concept_type is None for f in fields)


def test_explicit_facility_enrichment_retains_tieback_priority(sources):
    fields = load_subseaiq_fields(
        sources[0], enrich_facilities=True, facilities_csv=sources[1]
    )
    assert fields[0].concept_type == ConceptType.SUBSEA_TIEBACK
    assert fields[1].concept_type == ConceptType.TLP
    assert fields[0].operator == "Synthetic operator"


def test_enrichment_cannot_fall_back_to_withheld_facilities(sources):
    with pytest.raises(RuntimeError, match="redistribution-terms review"):
        load_subseaiq_fields(sources[0], enrich_facilities=True)


def test_host_type_map_values_are_concept_types():
    assert all(isinstance(v, ConceptType) for v in HOST_TYPE_MAP.values())


def test_crosswalk_matches_explicit_synthetic_codes(sources):
    rows = build_bsee_crosswalk(["GC0123"], csv_path=sources[0])
    assert len(rows) == 2
    assert rows[0].matched and not rows[1].matched
    assert rows[0].bsee_block_key == "GC123"
    assert crosswalk_summary(rows) == {"total": 2, "matched": 1, "unparsed": 0}


def test_crosswalk_retains_unparsed_external_rows(sources):
    rows = build_bsee_crosswalk([], csv_path=sources[0], gom_only=False)
    assert len(rows) == 3
    assert rows[-1].match_type == "unparsed"
    assert not any(r.matched for r in rows)
