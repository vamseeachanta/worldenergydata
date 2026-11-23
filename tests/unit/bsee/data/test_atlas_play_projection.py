"""Synthetic projection answers; no released roster or public association implied."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace

import pytest

from worldenergydata.bsee.atlas import attribute_fields, load_atlas
from worldenergydata.bsee.atlas_play_projection import project_plays
from worldenergydata.common.fields_registry import FieldsRegistry, load_fields

from .test_atlas import FIXTURES, SCHEMA


@pytest.fixture
def case(tmp_path):
    path = tmp_path / "fields.yml"
    path.write_text(
        "fields:\n  - canonical_id: synthetic_field\n"
        "    display_name: Synthetic field\n    aliases: [Synthetic alias]\n"
        "  - canonical_id: another_field\n    display_name: Another field\n"
    )
    registry = load_fields(path)
    atlas = {
        "2023sands": [
            {
                "_csv_row": 2,
                "SN_FORMSAND": "101",
                "SAND_NAME": "Synthetic sand",
                "BOEM_FIELD": "ZZ001",
                "PLAY_NUM": "7001",
                "PLAY_NAME": "SYN_FAN",
                "CHRONOZONE": "SYN",
            }
        ],
        "2023plays": [
            {
                "PLAY_NUMBER": "7001",
                "PLAY": "SYN_FAN",
                "PLAY_NAME_DESCRIPTION": "Synthetic fan play",
                "CHRONOZONE": "SYN",
            }
        ],
        "2023chronozones": [
            {"BOEM_CHRONOZONE": "SYN", "CHRONOZONE_DESCRIPTION": "Synthetic zone"}
        ],
    }
    result = attribute_fields(
        atlas,
        [{"name": "Synthetic field", "region": "US Gulf of Mexico", "play": None}],
        registry,
        {"synthetic_field": "ZZ001"},
        [{"BOEM_FIELD": "ZZ001", "FIELD_NAME": "Synthetic field", "_source": "xref"}],
    )[0]
    # Digests describe caller-supplied synthetic evidence, not downloaded bytes.
    sources = {
        table: {
            "source": "BSEE synthetic table",
            "version": "2023",
            "sha256": "a" * 64,
            "row_ids": rows,
        }
        for table, rows in (
            ("2023sands", [2]),
            ("2023plays", ["7001"]),
            ("2023chronozones", ["SYN"]),
            ("xref", ["alpha"]),
        )
    }
    return result, registry, sources


def project(case, existing=None):
    result, registry, sources = case
    output = project_plays([result], registry, sources, existing)
    assert output["unresolved"] == []
    return output["proposals"]["synthetic_field"]


def test_qualified_single_play_retains_identity_and_all_evidence(case):
    result, _, sources = case
    proposal = project(case)
    assert proposal == {
        "field_id": "synthetic_field",
        "play": "SYN_FAN",
        "disposition": "proposed",
        "attribution": result,
        "sources": sources,
    }


@pytest.mark.parametrize(
    "changes, disposition",
    [
        ({"status": "unmatched", "plays": []}, "unmatched"),
        ({"status": "ambiguous"}, "ambiguous"),
        ({"status": "unknown"}, "unqualified_status"),
        ({"join_basis": "unconfirmed_boem_field"}, "unconfirmed_identity"),
        ({"join_basis": "area_block_candidate"}, "unconfirmed_identity"),
        ({"qualifiers": ["missing_lookup"]}, "qualified_candidates"),
        ({"plays": []}, "no_play"),
        ({"plays": [{}, {}]}, "multiple_plays"),
        ({"plays": [{"number": "7001", "code": "SYN_FAN"}]}, "incomplete_play"),
        ({"sand_rows": []}, "incomplete_sand_evidence"),
    ],
)
def test_unqualified_results_keep_null_and_named_dispositions(
    case, changes, disposition
):
    case[0].update(changes)
    proposal = project(case)
    assert proposal["play"] is None
    assert proposal["disposition"] == disposition
    assert proposal["attribution"] == case[0]


@pytest.mark.parametrize("field_id", [None, "", "unknown_id", "Synthetic alias"])
def test_missing_or_noncanonical_identity_is_retained_separately(case, field_id):
    result, registry, sources = case
    result["field_id"] = field_id
    output = project_plays([result], registry, sources)
    assert output["proposals"] == {}
    assert len(output["unresolved"]) == 1
    assert output["unresolved"][0]["play"] is None
    assert output["unresolved"][0]["disposition"] == "unresolved_identity"
    assert output["unresolved"][0]["attribution"] == result


@pytest.mark.parametrize(
    "table, key, value",
    [
        ("2023plays", "sha256", "unknown"),
        ("2023plays", "sha256", ""),
        ("2023plays", "version", ""),
        ("2023plays", "source", ""),
        ("2023plays", "row_ids", []),
        ("2023plays", "row_ids", ["wrong"]),
        ("2023sands", "row_ids", [99]),
        ("2023chronozones", "row_ids", []),
        ("xref", "row_ids", []),
    ],
)
def test_missing_or_unbound_source_evidence_is_not_promoted(case, table, key, value):
    case[2][table][key] = value
    proposal = project(case)
    assert proposal["play"] is None
    assert proposal["disposition"] == "unavailable_source_evidence"


@pytest.mark.parametrize("table", ["2023sands", "2023plays", "2023chronozones", "xref"])
def test_missing_manifest_entry_is_explicit(case, table):
    del case[2][table]
    assert project(case)["disposition"] == "unavailable_source_evidence"
    assert project(case)["play"] is None


@pytest.mark.parametrize("key", ["code_match", "name_match"])
def test_confirmation_flags_are_checked_even_if_status_claims_attribution(case, key):
    case[0]["evidence"][key]["value"] = "true"
    assert project(case)["disposition"] == "unconfirmed_identity"
    assert project(case)["play"] is None


def test_duplicate_canonical_ids_fail_closed(case):
    result, registry, sources = case
    with pytest.raises(ValueError, match="Duplicate canonical id"):
        project_plays([result, deepcopy(result)], registry, sources)


@pytest.mark.parametrize(
    "existing, disposition",
    [("SYN_FAN", "already_populated"), ("OTHER", "existing_play_conflict")],
)
def test_existing_values_are_preserved_and_disagreement_reported(
    case, existing, disposition
):
    proposal = project(case, {"synthetic_field": existing})
    assert proposal["play"] == existing
    assert proposal["disposition"] == disposition


def test_registry_play_is_preserved_without_explicit_existing_values(case):
    result, registry, sources = case
    path_field = registry.by_id("synthetic_field")
    registry = FieldsRegistry([replace(path_field, play="OTHER")])
    proposal = project_plays([result], registry, sources)["proposals"][
        "synthetic_field"
    ]
    assert proposal["play"] == "OTHER"
    assert proposal["disposition"] == "existing_play_conflict"


def test_stable_order_and_no_input_or_output_aliasing(case):
    result, registry, sources = case
    another = deepcopy(result)
    another["field_id"] = "another_field"
    missing = {**deepcopy(result), "field_id": None}
    missing["name"] = "Unresolved synthetic field"
    inputs = [result, another, missing]
    existing = {"synthetic_field": None}
    before = json.dumps([inputs, sources, existing])
    forward = project_plays(inputs, registry, sources, existing)
    backward = project_plays(list(reversed(inputs)), registry, sources, existing)
    assert list(forward["proposals"]) == ["another_field", "synthetic_field"]
    assert json.dumps(forward) == json.dumps(backward)
    assert json.dumps([inputs, sources, existing]) == before
    forward["proposals"]["synthetic_field"]["attribution"]["plays"].clear()
    forward["proposals"]["synthetic_field"]["sources"].clear()
    assert json.dumps([inputs, sources, existing]) == before


def test_missing_source_record_is_unavailable(case):
    case[2]["2023plays"] = None
    assert project(case)["play"] is None
    assert project(case)["disposition"] == "unavailable_source_evidence"


def test_public_lookup_extract_with_synthetic_identity(case):
    _, registry, sources = case
    result = attribute_fields(
        load_atlas(FIXTURES, SCHEMA),
        [{"name": "Synthetic field", "region": "US Gulf of Mexico", "play": None}],
        registry,
        {"synthetic_field": "MC026"},
        [{"BOEM_FIELD": "MC026", "FIELD_NAME": "Synthetic field", "_source": "xref"}],
    )[0]
    for table, rows in (
        ("2023sands", [6]),
        ("2023plays", ["1982"]),
        ("2023chronozones", ["MUM"]),
    ):
        sources[table].update(
            source=f"tests/fixtures/bsee/atlas_2023/{table}.csv",
            sha256=hashlib.sha256((FIXTURES / f"{table}.csv").read_bytes()).hexdigest(),
            row_ids=rows,
        )
    proposal = project((result, registry, sources))
    assert proposal["play"] == "MUM_F2"
    assert proposal["disposition"] == "proposed"
    assert proposal["attribution"]["plays"] == [
        {
            "number": "1982",
            "code": "MUM_F2",
            "description": "Upper Middle Miocene Fan 2 Play",
        }
    ]


def test_existing_play_survives_unavailable_evidence(case):
    case[2].clear()
    proposal = project(case, {"synthetic_field": "OTHER"})
    assert proposal["play"] == "OTHER"
    assert proposal["disposition"] == "existing_play_preserved"


def test_independent_lease_confirmation_can_replace_name_confirmation(case):
    evidence = case[0]["evidence"]
    evidence["name_match"] = {"value": False, "source_field": None}
    evidence["lease_block_match"] = {
        "value": True,
        "source_field": "xref.LEASE/AREA_BLOCK",
    }
    assert project(case)["play"] == "SYN_FAN"
    assert project(case)["disposition"] == "proposed"


@pytest.mark.parametrize(
    "key, disposition",
    [
        ("field_id", "unresolved_identity"),
        ("status", "unqualified_status"),
        ("evidence", "unconfirmed_identity"),
        ("plays", "no_play"),
        ("sand_rows", "incomplete_sand_evidence"),
    ],
)
def test_missing_result_components_have_conservative_dispositions(
    case, key, disposition
):
    result, registry, sources = case
    del result[key]
    output = project_plays([result], registry, sources)
    proposal = (
        output["unresolved"][0]
        if key == "field_id"
        else output["proposals"]["synthetic_field"]
    )
    assert proposal["play"] is None
    assert proposal["disposition"] == disposition


def test_empty_input_has_no_fabricated_proposals(case):
    _, registry, sources = case
    assert project_plays([], registry, sources) == {"proposals": {}, "unresolved": []}
