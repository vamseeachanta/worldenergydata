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
    assert next(r for r in atlas["2023sands"] if r["SN_FORMSAND"] == "4921")[
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
            "name": "Fixture field",
            "region": "US Gulf of Mexico",
            "play": None,
            "block": "MC26",
        }
    ]
    registry_path = tmp_path / "fields.yml"
    registry_path.write_text(
        "fields:\n  - canonical_id: fixture_mc026\n    display_name: Fixture field\n"
    )
    result = attribute_fields(
        load_atlas(FIXTURES, SCHEMA),
        roster,
        load_fields(registry_path),
        {"fixture_mc026": "MC026"},
        public_field_rows=[
            {
                "BOEM_FIELD": "MC026",
                "FIELD_NAME": "Fixture field",
                "_source": "public fixture table",
            }
        ],
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


def test_code_match_requires_independent_public_confirmation(tmp_path):
    registry_path = tmp_path / "fields.yml"
    registry_path.write_text(
        "fields:\n  - canonical_id: fixture_mc026\n    display_name: Fixture field\n"
    )
    roster = [
        {
            "name": "Fixture field",
            "region": "US Gulf of Mexico",
            "play": None,
            "block": "MC26",
        }
    ]
    result = attribute_fields(
        load_atlas(FIXTURES, SCHEMA),
        roster,
        load_fields(registry_path),
        {"fixture_mc026": "MC026"},
    )[0]
    assert result["status"] == "ambiguous"
    assert result["plays"]
    assert result["join_basis"] == "unconfirmed_boem_field"
    assert result["evidence"]["code_match"]["value"] is True
    assert result["evidence"]["name_match"]["value"] == "not-available"
    assert "unverified_field_identity" in result["qualifiers"]


def test_confirmed_multiple_plays_stay_ambiguous(tmp_path):
    registry_path = tmp_path / "fields.yml"
    registry_path.write_text(
        "fields:\n  - canonical_id: fixture_gc254\n    display_name: Fixture field\n"
    )
    roster = [
        {
            "name": "Fixture field",
            "region": "US Gulf of Mexico",
            "play": None,
            "block": "GC254",
        }
    ]
    result = attribute_fields(
        load_atlas(FIXTURES, SCHEMA),
        roster,
        load_fields(registry_path),
        {"fixture_gc254": "GC254"},
        public_field_rows=[
            {
                "BOEM_FIELD": "GC254",
                "FIELD_NAME": "Fixture field",
                "_source": "public fixture table",
            }
        ],
    )[0]
    assert result["status"] == "ambiguous"
    assert "multiple_plays" in result["qualifiers"]
    assert len(result["plays"]) == 3


def test_code_shaped_block_is_not_second_confirmation(tmp_path):
    registry_path = tmp_path / "fields.yml"
    registry_path.write_text(
        "fields:\n  - canonical_id: fixture_mc026\n    display_name: Fixture field\n"
        "    bsee:\n      leases: [G12345]\n      area_blocks: [MC026]\n"
    )
    roster = [
        {
            "name": "Fixture field",
            "region": "US Gulf of Mexico",
            "play": None,
            "block": "MC26",
        }
    ]
    result = attribute_fields(
        load_atlas(FIXTURES, SCHEMA),
        roster,
        load_fields(registry_path),
        {"fixture_mc026": "MC026"},
        public_field_rows=[
            {
                "BOEM_FIELD": "MC026",
                "LEASE_NUMBER": "G12345",
                "AREA_BLOCK": "MC026",
                "_source": "public fixture table",
            }
        ],
    )[0]
    assert result["status"] == "ambiguous"
    assert result["evidence"]["lease_block_match"]["value"] is False


def test_xref_confirms_independent_lease_block_and_pins_source(tmp_path):
    from worldenergydata.bsee.atlas import public_xref_evidence

    registry_path = tmp_path / "fields.yml"
    registry_path.write_text(
        "fields:\n  - canonical_id: fixture_mc026\n    display_name: Fixture field\n"
        "    bsee:\n      leases: [G12345]\n      area_blocks: [MC027]\n"
    )
    registry = load_fields(registry_path)
    xref = [
        {
            "BOEM_FIELD": "MC026",
            "LEASE": "G12345",
            "AREA_CODE": "MC",
            "BLOCK_NUMBER": "27",
        }
    ]
    codes, public_rows = public_xref_evidence(xref, registry)
    assert codes == {"fixture_mc026": "MC026"}
    result = attribute_fields(
        load_atlas(FIXTURES, SCHEMA),
        [{"name": "Fixture field", "region": "US Gulf of Mexico", "play": None}],
        registry,
        codes,
        public_rows,
    )[0]
    assert result["status"] == "attributed"
    assert result["evidence"]["lease_block_match"]["value"] is True
    assert (
        "2023xref_oper-comp" in result["evidence"]["lease_block_match"]["source_field"]
    )
    # Conflicting field-code rows must not invent a unique crosswalk.
    codes, _ = public_xref_evidence(
        xref + [{**xref[0], "BOEM_FIELD": "MC028"}], registry
    )
    assert codes == {}


def test_committed_lookup_exports_match_manifest_and_schema():
    import hashlib
    import json

    directory = SCHEMA.parent
    manifest = json.loads((directory / "manifest.json").read_text())
    records = {record["file"]: record for record in manifest["files"]}
    for table in ("2023plays", "2023chronozones"):
        path = directory / f"{table}.csv"
        record = records[path.name]
        assert path.stat().st_size == record["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        assert len(load_table(path, table, SCHEMA)) == manifest["row_counts"][table]
