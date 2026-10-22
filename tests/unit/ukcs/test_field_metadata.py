"""NSTA metadata tests with synthetic, schema-shaped observations.

Schema sources (inspected 2026-10-20): NSTA Offshore_hydrocarbon_fields_(WGS84)
and UKCS offshore petroleum wells top holes ETRS89, FeatureServer layer 0.
URLs are exported by ukcs.field_metadata. All numbers below are synthetic inputs
or independently calculated expectations, not engineering acceptance limits.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from worldenergydata.ukcs.field_concept import build_uk_field_concept
from worldenergydata.ukcs.field_metadata import enrich_ukcs_field_metadata


@pytest.fixture
def themes():
    data = json.loads(
        (Path(__file__).parent / "fixtures" / "nsta_metadata.json").read_text()
    )
    return {key: data[key] for key in ("fields", "wells")}


def test_enrichment_maps_supported_concept_fields_and_preserves_context(themes):
    """Hand calculation: median(100, 140) = (100 + 140) / 2 = 120 m.

    Startup year is the literal 2001 in the synthetic 2001/06 source string.
    Equity strings are copied, not converted into an inferred fraction or unit.
    """
    original = copy.deepcopy(themes)
    meta = enrich_ukcs_field_metadata(" example ", **themes)
    concept = build_uk_field_concept(meta)
    assert (concept.name, concept.region) == ("Example", "uk")
    assert concept.operator == "Example operator"
    assert concept.water_depth_m == 120.0
    assert concept.year_first_oil == 2001
    assert meta["field_status"] == "PRODUCING"
    assert meta["production_start_date"] == "2001/06"
    assert meta["discovery_date"] == "1990/02"
    assert meta["ownership"] == [
        {"licensee": "Example licensee", "equity_raw": "60"},
        {"licensee": "Other licensee", "equity_raw": "40"},
    ]
    assert meta["metadata_coverage"]["fdp_consent_date"] == "NOT_EVALUATED"
    assert meta["metadata_provenance"]["water_depth_m"]["method"] == "median"
    assert meta["metadata_provenance"]["water_depth_m"]["record_ids"] == [11, 12]
    assert themes == original


def test_field_depth_takes_precedence_and_provenance_is_explicit(themes):
    """Synthetic field depth 80 m is copied; well depths do not override it."""
    themes["fields"][0]["DEPTH_M"] = "80"
    meta = enrich_ukcs_field_metadata("EXAMPLE", **themes)
    assert meta["water_depth_m"] == 80.0
    evidence = meta["metadata_provenance"]["water_depth_m"]
    assert evidence["source_fields"] == ["DEPTH_M"]
    assert evidence["method"] == "source_value"
    assert len(evidence["snapshot_sha256"]) == 64


@pytest.mark.parametrize("bad_depth", [None, "", "unknown", -1, "nan", "inf", True])
def test_invalid_field_depth_uses_valid_matching_wells(themes, bad_depth):
    """Hand calculation: median(100, 140) = 120 m for each missing/invalid field."""
    themes["fields"][0]["DEPTH_M"] = bad_depth
    themes["wells"].extend(
        [
            {"TARGETFLD": "EXAMPLE", "WATDEP_M": -1},
            {"TARGETFLD": "EXAMPLE", "WATDEP_M": "nan"},
        ]
    )
    assert enrich_ukcs_field_metadata("EXAMPLE", **themes)["water_depth_m"] == 120.0


def test_sparse_metadata_remains_unknown_instead_of_zero():
    meta = enrich_ukcs_field_metadata("EXAMPLE")
    concept = build_uk_field_concept(meta)
    assert concept.water_depth_m is None
    assert concept.operator is None
    assert concept.year_first_oil is None
    assert meta["metadata_coverage"]["water_depth_m"] == "missing"
    assert meta["metadata_provenance"] == {}


def test_zero_is_valid_and_missing_name_is_rejected(themes):
    """Zero is a synthetic measured depth, distinct from missing evidence."""
    themes["fields"][0]["DEPTH_M"] = 0
    assert enrich_ukcs_field_metadata("EXAMPLE", **themes)["water_depth_m"] == 0
    for name in [None, "", "  "]:
        with pytest.raises(ValueError, match="field_name"):
            enrich_ukcs_field_metadata(name)


def test_conflicting_fields_are_rejected_instead_of_arbitrary_selection(themes):
    duplicate = dict(themes["fields"][0], CURR_OPER="Conflicting operator")
    themes["fields"].append(duplicate)
    with pytest.raises(ValueError, match="Ambiguous"):
        enrich_ukcs_field_metadata("EXAMPLE", **themes)


def test_order_does_not_change_normalized_metadata(themes):
    first = enrich_ukcs_field_metadata("EXAMPLE", **themes)
    themes["wells"].reverse()
    assert enrich_ukcs_field_metadata("EXAMPLE", **themes) == first


def test_invalid_start_date_is_not_silently_used_as_a_year(themes):
    themes["fields"][0]["PROD_DATE"] = "not a date 2001"
    concept = build_uk_field_concept(enrich_ukcs_field_metadata("EXAMPLE", **themes))
    assert concept.year_first_oil is None


def test_deterministic_screening_is_labelled_and_not_publication_ready(themes):
    from worldenergydata.ukcs.field_concept import screen_ukcs_field_metadata

    meta = enrich_ukcs_field_metadata("EXAMPLE", **themes)
    first = screen_ukcs_field_metadata(meta)
    second = screen_ukcs_field_metadata(meta)
    assert first == second
    assert first["ranked_concepts"]
    assert first["screening_label"] == "metadata_screening_only"
    assert first["recommendation_ready"] is False
    assert first["metadata_coverage"] == meta["metadata_coverage"]
    assert first["metadata_provenance"] == meta["metadata_provenance"]


def test_blank_equity_slots_do_not_become_observed_ownership():
    meta = enrich_ukcs_field_metadata(
        "EXAMPLE", fields=[{"FIELDNAME": "EXAMPLE", "CURRLIC": "", "EQUITY": " "}]
    )
    assert meta["ownership"] == []
    assert meta["metadata_coverage"]["ownership"] == "missing"


def test_sparse_screening_exposes_missing_coverage():
    from worldenergydata.ukcs.field_concept import screen_ukcs_field_metadata

    result = screen_ukcs_field_metadata({"field_name": "EXAMPLE"})
    assert result["metadata_coverage"]["water_depth_m"] == "missing"
    assert result["recommendation_ready"] is False


def test_gas_startup_is_retained_without_claiming_first_oil(themes):
    themes["fields"][0]["FIELDTYPE"] = "GAS"
    meta = enrich_ukcs_field_metadata("EXAMPLE", **themes)
    assert meta["production_start_year"] == 2001
    assert build_uk_field_concept(meta).year_first_oil is None


def test_odd_well_median_is_middle_sorted_value(themes):
    """Sorted synthetic depths [100, 140, 150] have middle value 140 m."""
    themes["wells"].append({"TARGETFLD": "EXAMPLE", "WATDEP_M": 150})
    assert enrich_ukcs_field_metadata("EXAMPLE", **themes)["water_depth_m"] == 140


def test_digest_matches_independently_serialized_source_attributes():
    """Expected bytes are written independently, with sorted keys and no spaces.

    SHA-256 is applied to that literal UTF-8 snapshot, not to output from the
    normalizer. The non-ASCII operator also checks the UTF-8 encoding contract.
    """
    row = {"FIELDNAME": "EXAMPLE", "CURR_OPER": "Opérateur", "OBJECTID": 1}
    meta = enrich_ukcs_field_metadata("EXAMPLE", fields=[row])
    expected = '[{"CURR_OPER":"Opérateur","FIELDNAME":"EXAMPLE","OBJECTID":1}]'
    digest = hashlib.sha256(expected.encode("utf-8")).hexdigest()
    assert meta["metadata_provenance"]["operator"]["snapshot_sha256"] == digest
