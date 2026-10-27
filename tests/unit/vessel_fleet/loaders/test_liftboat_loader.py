"""Liftboat evidence, identity and offline loading contracts."""

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from worldenergydata.vessel_fleet.loaders.liftboat_loader import (
    INCIDENT_FIELDS,
    TABLE_FIELDS,
    VESSEL_FIELDS,
    LiftboatLoader,
)


@pytest.fixture
def database(tmp_path):
    source = LiftboatLoader().data_dir
    for path in source.iterdir():
        if path.is_file():
            (tmp_path / path.name).write_bytes(path.read_bytes())
    return tmp_path


def rewrite(directory, table, edit):
    path = directory / table
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        rows = list(reader)
    edit(rows)
    with path.open("w", newline="\n", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    manifest["tables"][table]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["tables"][table]["row_count"] = len(rows)
    (directory / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8", newline="\n"
    )


def test_packaged_database_and_public_api():
    from worldenergydata.vessel_fleet import LiftboatLoader as PublicLoader

    loader = PublicLoader()
    vessels = loader.load()
    incidents = loader.load_incidents()
    assert len(vessels) >= 50
    assert len(incidents) >= 4
    assert len({row["liftboat_id"] for row in vessels}) == len(vessels)
    assert len({row["vessel_name"] for row in vessels}) == len(vessels)
    assert all(row["vessel_name"] for row in vessels)
    assert any(row["agency"] == "BSEE" for row in incidents)
    assert any(row["agency"] == "NTSB" for row in incidents)
    assert set(VESSEL_FIELDS) <= vessels[0].keys()
    assert set(INCIDENT_FIELDS) <= incidents[0].keys()


def test_historical_records_use_neutral_labels_and_consistent_keys():
    loader = LiftboatLoader()
    seed_ids = {row["liftboat_id"] for row in loader.load_seed_crosswalk()}
    historical = [row for row in loader.load() if row["liftboat_id"] not in seed_ids]
    assert len(historical) == 2
    for index, row in enumerate(historical, 1):
        assert row["liftboat_id"] == f"lb-historical-{index}", "use a neutral key"
        assert row["vessel_name"] == f"HISTORICAL RECORD {index}", "use a neutral label"
        records = loader.incidents_for(row["liftboat_id"])
        assert len(records) == 1
        assert records[0]["incident_id"] == f"ntsb-historical-{index}"
        assert records[0]["vessel_name"] == row["vessel_name"]
        assert row["vessel_name_confidence"] == "medium"
    coverage = loader.manifest["coverage"]
    assert coverage["named_vessels"] == 72
    assert coverage["anonymized_historical_records"] == 2
    assert len(loader.load()) == 74


def test_seed_crosswalk_is_complete_and_preserves_ambiguous_labels():
    loader = LiftboatLoader()
    seed_path = Path(__file__).resolve().parents[4] / loader.manifest["seed"]["path"]
    with seed_path.open(newline="", encoding="utf-8") as stream:
        seed = [row for row in csv.DictReader(stream) if row["RIG_TYPE"] == "lift_boat"]
    crosswalk = loader.load_seed_crosswalk()
    assert {row["seed_name"] for row in crosswalk} == {row["RIG_NAME"] for row in seed}
    assert len(crosswalk) == len(seed) == 158
    generic = next(row for row in crosswalk if row["seed_name"] == "LIFT BOAT")
    assert generic["liftboat_id"] == ""
    assert generic["resolution"] == "unresolved"
    assert loader.get_by_name("LIFT BOAT") is None
    assert (
        hashlib.sha256(seed_path.read_bytes()).hexdigest()
        == loader.manifest["seed"]["sha256"]
    )


def test_reported_rename_and_casualty_are_linked_without_fuzzy_matching():
    loader = LiftboatLoader()
    vessel = loader.get_by_name("  seacor power  ")
    assert vessel["imo_number"] == "8765682"
    assert vessel["leg_length_ft"] == "265"
    assert vessel["leg_count"] == "3"
    assert vessel["year_built"] == "2002"
    assert loader.get_by_name("DIXIE ENDEAVOR LIFT BOAT") == vessel
    assert loader.get_by_name("SEACOR POWR") is None
    records = loader.incidents_for(vessel["liftboat_id"])
    assert len(records) == 1
    assert records[0]["incident_date"] == "2021-04-13"
    assert records[0]["fatalities"] == "13"
    assert records[0]["missing_presumed_dead"] == "7"
    assert records[0]["injuries"] == "4"
    assert records[0]["phase"] == "transit"


def test_unknown_values_are_empty_and_do_not_inherit_generic_hulls():
    loader = LiftboatLoader()
    assert all(row["variable_deck_load_lb"] == "" for row in loader.load())
    ram = loader.get_by_name("RAM VII")
    assert ram["water_depth_rating_ft"] == "90"
    assert ram["deck_area_sq_ft"] == "2500"
    assert ram["deck_cargo_capacity_lb"] == "140000"
    assert ram["class_society"] == ""  # USCG is a regulator, not a class society.
    alert = next(row for row in loader.load_incidents() if row["agency"] == "BSEE")
    assert alert["liftboat_id"] == alert["vessel_name"] == ""
    assert alert["incident_date"] == alert["fatalities"] == alert["phase"] == ""
    assert alert["report_date"] == "2025-04-03"
    assert alert["injuries"] == "2"


def test_every_observation_has_resolvable_source_and_confidence():
    loader = LiftboatLoader()
    for table, fields in TABLE_FIELDS.items():
        for row in loader.tables[table]:
            for field in fields:
                value = row[field]
                source = row[field + "_source"]
                confidence = row[field + "_confidence"]
                if value:
                    assert source.partition("#")[0] in loader.manifest["sources"]
                    assert confidence in {"high", "medium", "low"}
                else:
                    assert source == confidence == ""


@pytest.mark.parametrize(
    "field,value",
    [
        ("vessel_name_source", ""),
        ("vessel_name_confidence", "certain"),
        ("vessel_name_source", "unknown#page=1"),
        ("leg_count", "-1"),
        ("leg_count", "2.5"),
        ("leg_length_ft", "nan"),
        ("leg_length_ft", "inf"),
        ("leg_length_ft", "0"),
        ("year_built", "two thousand"),
        ("imo_number", "123"),
    ],
)
def test_invalid_observations_rejected(database, field, value):
    def edit(rows):
        row = next(row for row in rows if row["vessel_name"] == "SEACOR POWER")
        row[field] = value

    rewrite(database, "liftboats.csv", edit)
    with pytest.raises(ValueError):
        LiftboatLoader(database).load()


@pytest.mark.parametrize(
    "field,value,accepted",
    [
        ("leg_count", "2", False),
        ("leg_count", "3", True),
        ("leg_count", "4", True),
        ("leg_count", "5", False),
        ("year_built", "1799", False),
        ("year_built", "1800", True),
        ("year_built", "2030", True),
        ("year_built", "2031", False),
    ],
)
def test_documented_import_policy_boundaries(
    database, monkeypatch, field, value, accepted
):
    class CatalogDate(date):
        @classmethod
        def today(cls):
            return cls(2030, 6, 15)

    monkeypatch.setattr(
        "worldenergydata.vessel_fleet.loaders.liftboat_loader.date", CatalogDate
    )

    # Literal bounds come from LIFTBOATS.md, Import policy: adjacent values
    # bracket 3/4 legs and 1800/current year independently of implementation.
    def edit(rows):
        rows[0][field] = value
        rows[0][field + "_source"] = "seed"
        rows[0][field + "_confidence"] = "low"

    rewrite(database, "liftboats.csv", edit)
    loader = LiftboatLoader(database)
    if accepted:
        assert loader.load()[0][field] == value
    else:
        with pytest.raises(ValueError, match=field):
            loader.load()


def test_provenance_without_value_rejected(database):
    def edit(rows):
        rows[0]["builder"] = ""
        rows[0]["builder_source"] = "seed"
        rows[0]["builder_confidence"] = "low"

    rewrite(database, "liftboats.csv", edit)
    with pytest.raises(ValueError, match="empty"):
        LiftboatLoader(database).load()


@pytest.mark.parametrize("table", list(TABLE_FIELDS))
def test_duplicate_keys_rejected(database, table):
    rewrite(database, table, lambda rows: rows.append(dict(rows[0])))
    with pytest.raises(ValueError, match="duplicate"):
        LiftboatLoader(database).load()


def test_duplicate_vessel_names_rejected(database):
    def edit(rows):
        rows[1]["vessel_name"] = "  " + rows[0]["vessel_name"].lower() + "  "

    rewrite(database, "liftboats.csv", edit)
    with pytest.raises(ValueError, match="duplicate"):
        LiftboatLoader(database).load()


@pytest.mark.parametrize("table", ["incidents.csv", "seed_crosswalk.csv"])
def test_dangling_foreign_keys_rejected(database, table):
    rewrite(database, table, lambda rows: rows[0].update(liftboat_id="absent"))
    with pytest.raises(ValueError, match="foreign key"):
        LiftboatLoader(database).load()


def test_incident_cannot_link_to_a_different_known_vessel(database):
    rewrite(
        database, "incidents.csv", lambda rows: rows[0].update(liftboat_id="lb-ram-vii")
    )
    with pytest.raises(ValueError, match="identity"):
        LiftboatLoader(database).load()


def test_known_incident_name_requires_its_foreign_key(database):
    rewrite(database, "incidents.csv", lambda rows: rows[0].update(liftboat_id=""))
    with pytest.raises(ValueError, match="identity"):
        LiftboatLoader(database).load()


def test_repeated_event_with_new_key_is_rejected(database):
    def edit(rows):
        row = dict(rows[0], incident_id="duplicate-event")
        rows.append(row)

    rewrite(database, "incidents.csv", edit)
    with pytest.raises(ValueError, match="duplicate"):
        LiftboatLoader(database).load()


def test_offline_load_outside_repository(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert LiftboatLoader().get_by_name("RAM VII")["leg_length_ft"] == "145"


@pytest.mark.parametrize(
    "field,value",
    [("phase", "sailing"), ("incident_date", "2021-02-30"), ("injuries", "-1")],
)
def test_incident_schema_rejected(database, field, value):
    rewrite(database, "incidents.csv", lambda rows: rows[0].update({field: value}))
    with pytest.raises(ValueError):
        LiftboatLoader(database).load()


def test_corrupt_bytes_rejected_before_parsing(database):
    path = database / "liftboats.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest"):
        LiftboatLoader(database).load()


def test_malformed_csv_rejected_even_with_updated_digest(database):
    path = database / "liftboats.csv"
    path.write_bytes(path.read_bytes() + b"bad,row\n")
    manifest = json.loads((database / "manifest.json").read_text(encoding="utf-8"))
    manifest["tables"]["liftboats.csv"]["sha256"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    (database / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8", newline="\n"
    )
    with pytest.raises(ValueError, match="width"):
        LiftboatLoader(database).load()


def test_returned_rows_do_not_mutate_cached_evidence():
    loader = LiftboatLoader()
    rows = loader.load()
    rows[0]["vessel_name"] = "CHANGED"
    assert loader.load()[0]["vessel_name"] != "CHANGED"
