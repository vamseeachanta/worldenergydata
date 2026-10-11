"""Offline validation against unmodified public Atlas table extracts."""

import csv
from pathlib import Path

import pytest

from worldenergydata.bsee.atlas import attribute_fields, load_atlas, load_table
from worldenergydata.common.fields_registry import load_fields

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = ROOT / "tests/fixtures/bsee/atlas_2023"
SCHEMA = ROOT / "data/modules/bsee/atlas/2023/schema.json"


def test_loader_schema_accepts_recorded_rows_rejects_malformed(tmp_path):
    atlas = load_atlas(FIXTURES, SCHEMA)
    assert len(atlas["2023sands"]) == 5
    assert "0582" in {r["PLAY_NUM"] for r in atlas["2023sands"]}
    assert next(r for r in atlas["2023sands"] if r["SN_FORMSAND"] == 4921)[
        "SDDATE"
    ].startswith("1968-09-30")
    with (FIXTURES / "2023sands.csv").open() as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        rows = list(reader)
    rows[0]["SN_FORMSAND"] = "not a number"
    path = tmp_path / "malformed.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="SN_FORMSAND"):
        load_table(path, "2023sands", SCHEMA)
    path.write_text("invented_column\ninvalid\n")
    with pytest.raises(ValueError, match="columns"):
        load_table(path, "2023sands", SCHEMA)


def test_known_field_candidates_have_expected_play_and_chronozone(tmp_path):
    roster = [
        {
            "name": "BOEM field MC026",
            "region": "US Gulf of Mexico",
            "play": None,
            "block": "MC26",
        }
    ]
    registry_path = tmp_path / "fields.yml"
    registry_path.write_text(
        "fields:\n  - canonical_id: fixture_mc026\n    display_name: BOEM field MC026\n"
    )
    result = attribute_fields(
        load_atlas(FIXTURES, SCHEMA),
        roster,
        load_fields(registry_path),
        {"fixture_mc026": "MC026"},
    )[0]
    assert result["plays"][0]["number"] == "1982"
    assert result["plays"][0]["code"] == "MUM_F2"
    assert result["chronozones"][0]["code"] == "MUM"
    assert result["chronozones"][0]["description"] == "Upper Middle Miocene"
    assert result["sand_rows"][0]["sand_name"]
    assert result["status"] == "attributed"
    assert result["field_id"] == "fixture_mc026"


def test_unmatched_multi_play_and_shared_block_keep_explicit_dispositions():
    roster = [
        {"name": n, "region": "US Gulf of Mexico", "play": None, "block": b}
        for n, b in [
            ("No rows", "ZZ999"),
            ("Allegheny", "GC254"),
            ("Another field", "GC254"),
        ]
    ]
    results = attribute_fields(load_atlas(FIXTURES, SCHEMA), roster, None)
    assert results[0]["status"] == "unmatched"
    assert results[0]["unmatched_reason"] == "no_sand_rows_for_area_block"
    assert results[1]["status"] == "ambiguous"
    assert "multiple_plays" in results[1]["qualifiers"]
    assert "shared_roster_block" in results[1]["qualifiers"]
    assert len(results[1]["plays"]) == 3
