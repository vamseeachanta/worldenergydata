"""Synthetic Indiana examples; all identifiers and measurements are invented.

Hand calculation: three input wells have stems S AND S, S AND S and OTHER.
Thus S&S matches two wells. Only the first has a completion and an API
crosswalk: coverage is two matched, one with completion, one with API,
one without each. Two images join to the first permit; neither is fetched.
Depth 1200 is copied, never calculated or converted. No field value is a
published measurement. Field names follow the official service schema:
https://gisdata.in.gov/server/rest/services/Hosted/OilAndGasWells/FeatureServer
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from worldenergydata.modules.state_regulators.indiana_dnr.inventory import (
    build_inventory,
    normalize_operator,
)

EXAMPLE = Path("examples/indiana_dnr/synthetic_snapshot.json")


@pytest.fixture
def snapshot():
    return json.loads(EXAMPLE.read_text())


def inventory(snapshot, operator="S&S"):
    return build_inventory(snapshot, operator=operator)


@pytest.mark.parametrize(
    "name",
    ["S & S", "s&s llc", "S and S, Inc.", "S & S, L.L.C.", "S AND S CO LTD", "S_and_S"],
)
def test_name_variants(name):
    assert normalize_operator(name) == "S AND S"


def test_no_substring_or_empty_matching(snapshot):
    assert inventory(snapshot, "S")["wells"] == []
    with pytest.raises(ValueError, match="operator"):
        inventory(snapshot, " LLC ")


def test_well_fields_and_coverage(snapshot):
    result = inventory(snapshot)
    assert result["coverage"]["input_wells"] == 3
    assert result["coverage"]["matched_wells"] == 2
    assert result["coverage"]["with_api_number"] == 1
    assert result["coverage"]["with_completions"] == 1
    assert result["coverage"]["without_api_number"] == 1
    assert result["coverage"]["with_image_catalogue"] == 1
    first, second = result["wells"]
    assert first["permit_no"] == "0007"
    assert first["operator_of_record"] == "S & S LLC"
    assert second["operator_of_record"] == "S and S, Inc."
    assert first["api_number"] == "synthetic-api-a"
    assert second["api_number"] is None
    assert first["contract_operator"] is None
    assert first["well_status"] == "Oil"
    assert first["current_status"] == 0  # An opaque source code, not an idle judgement.
    assert first["idle_status"] == "NOT_EVALUATED"
    assert first["plugging_obligation"] == "NOT_EVALUATED"
    assert first["location"]["spatial_reference"] == {"wkid": "synthetic-crs"}
    assert first["location"]["geometry"] == {"x": 10, "y": 20}
    assert first["source_record"]["objectid"] == 1
    assert first["completion_zones"] == ["synthetic zone"]
    assert first["formation_tops"] == [{"formation": "synthetic top", "depth": 900}]
    assert first["spud_date"] is None
    assert first["completion_dates"] == ["synthetic date"]
    assert first["total_depth"] == [{"driller": 1200, "logger": None, "unit": None}]
    assert len(first["image_catalogue"]) == 2
    assert first["image_catalogue"][0]["filename"] == "synthetic.pdf"
    assert "lease" in result["production_note"].lower()
    assert result["production_granularity"] == "NOT_EVALUATED"
    assert "well-level" in result["production_note"]


def test_missing_data_remains_unknown(snapshot):
    snapshot.pop("completions")
    snapshot.pop("images")
    snapshot.pop("supplements")
    first = inventory(snapshot)["wells"][0]
    for field in ("api_number", "contract_operator", "spud_date"):
        assert first[field] is None
    for field in ("completion_zones", "formation_tops", "total_depth"):
        assert first[field] == []
    assert "api_number" in first["not_evaluated"]
    assert "images" in inventory(snapshot)["coverage"]["tables_not_supplied"]


def test_multiple_completions_preserved_and_join_by_igs(snapshot):
    other = copy.deepcopy(snapshot["completions"][0])
    other["attributes"].update(
        objectid=12, compdate="another date", totaldepthdriller=1500
    )
    snapshot["completions"].append(other)
    first, second = inventory(snapshot)["wells"]
    assert len(first["completions"]) == 2
    assert first["completion_dates"] == ["synthetic date", "another date"]
    assert second["completions"] == []


def test_supplement_requires_provenance_and_unique_key(snapshot):
    snapshot["supplements"][0].pop("source_record")
    with pytest.raises(ValueError, match="source_record"):
        inventory(snapshot)


def test_duplicate_supplement_is_not_silently_chosen(snapshot):
    snapshot["supplements"].append(copy.deepcopy(snapshot["supplements"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        inventory(snapshot)


def test_supplement_permit_mismatch_rejected(snapshot):
    snapshot["supplements"][0]["permit_no"] = "wrong"
    with pytest.raises(ValueError, match="permit"):
        inventory(snapshot)


def test_leading_zero_join_keys(snapshot):
    snapshot["wells"][0]["attributes"]["igs_id"] = "00042"
    assert inventory(snapshot)["coverage"]["with_completions"] == 1


def test_duplicate_well_identity_rejected(snapshot):
    snapshot["wells"].append(copy.deepcopy(snapshot["wells"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        inventory(snapshot)


def test_missing_identity_rejected(snapshot):
    snapshot["wells"][0]["attributes"].pop("igs_id")
    with pytest.raises(ValueError, match="igs_id"):
        inventory(snapshot)


def test_inconsistent_relationship_key_rejected(snapshot):
    snapshot["wells"][0]["attributes"]["igs_int"] = 99
    with pytest.raises(ValueError, match="relationship"):
        inventory(snapshot)


@pytest.mark.parametrize(
    "field,value",
    [("api_number", 123), ("formation_tops", "text"), ("completion_zones", "text")],
)
def test_invalid_supplement_types_rejected(snapshot, field, value):
    snapshot["supplements"][0][field] = value
    with pytest.raises(ValueError, match=field):
        inventory(snapshot)


def test_duplicate_related_record_rejected(snapshot):
    snapshot["completions"].append(copy.deepcopy(snapshot["completions"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        inventory(snapshot)


def test_arcgis_error_not_empty_inventory(snapshot):
    snapshot["wells"] = {"error": {"code": 400, "message": "failed"}}
    with pytest.raises(ValueError, match="ArcGIS"):
        inventory(snapshot)


def test_input_not_mutated(snapshot):
    original = copy.deepcopy(snapshot)
    inventory(snapshot)
    assert snapshot == original


def test_cli_worked_example(tmp_path):
    output = tmp_path / "inventory.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.modules.state_regulators.indiana_dnr",
            "--snapshot",
            str(EXAMPLE),
            "--operator",
            "S&S",
            "--output",
            str(output),
        ],
        check=True,
    )
    assert json.loads(output.read_text())["coverage"]["matched_wells"] == 2
