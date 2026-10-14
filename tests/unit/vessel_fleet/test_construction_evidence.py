"""Offline contracts for sourced construction identities and crane ratings."""

import copy
import csv
import hashlib
import json
from pathlib import Path

import pytest

from worldenergydata.vessel_fleet import construction_evidence as ce


@pytest.fixture
def bundle():
    return ce.load_evidence()


def test_every_legacy_row_has_an_explicit_disposition(bundle):
    with (ce.DATA_DIR / "construction_vessels.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        names = [row["VESSEL_NAME"] for row in csv.DictReader(stream)]
    assert [row["vessel_name"] for row in bundle["vessels"]] == names
    assert all(row["provenance"] for row in bundle["vessels"])
    assert all(row["hull_model"] == "none" for row in bundle["vessels"])
    ce.validate_evidence(bundle)


def test_unresolved_candidates_are_not_accepted_identities(bundle):
    row = next(row for row in bundle["vessels"] if row["vessel_name"] == "HERCULES")
    assert row["identity_status"] == "unresolved"
    assert row["candidates"]
    assert row["imo"] is None
    assert row["current_name"] is None
    assert row["status"] is None


def test_worked_lookup_uses_sourced_method_tension_pairs(bundle):
    rows = ce.find_pipelay(" S-LAY ", 1050, bundle=bundle)
    assert {row["vessel_name"] for row in rows} == {
        "PIONEERING SPIRIT", "SOLITAIRE"
    }
    assert ce.find_pipelay("s-lay", 2000, bundle=bundle)[0]["vessel_name"] == "PIONEERING SPIRIT"
    assert ce.find_pipelay("s-lay", 2001, bundle=bundle) == []
    assert all(row["matched_capability"]["source_id"] for row in rows)


def test_multiple_lay_methods_do_not_share_tension(bundle):
    slay = ce.find_pipelay("s-lay", 600, bundle=bundle)
    jlay = ce.find_pipelay("j-lay", 937, bundle=bundle)
    assert "SEVEN BOREALIS" in {row["vessel_name"] for row in slay}
    assert "SEVEN BOREALIS" in {row["vessel_name"] for row in jlay}
    assert "SEVEN BOREALIS" not in {
        row["vessel_name"] for row in ce.find_pipelay("s-lay", 937, bundle=bundle)
    }


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, "1050"])
def test_lookup_rejects_invalid_tension(value, bundle):
    with pytest.raises(ValueError):
        ce.find_pipelay("s-lay", value, bundle=bundle)


def test_lookup_rejects_unknown_method(bundle):
    with pytest.raises(ValueError):
        ce.find_pipelay("unknown", 600, bundle=bundle)


def test_lookup_returns_detached_records(bundle):
    result = ce.find_pipelay("s-lay", 2000, bundle=bundle)
    result[0]["matched_capability"]["tension_t"] = 0
    assert ce.find_pipelay("s-lay", 2000, bundle=bundle)


def test_crane_ratings_preserve_points_intervals_and_per_crane_basis(bundle):
    sleipnir = [r for r in bundle["cranes"] if r["vessel_name"] == "SLEIPNIR"]
    main = [r for r in sleipnir if "main hoist" in r["crane"]]
    assert [(r["capacity_t"], r["radius_min_m"], r["radius_max_m"]) for r in main] == [
        (10000, 27, 48), (7000, 62, 62), (4000, 82, 82)
    ]
    assert all("per crane" in r["crane"] for r in main)
    assert [r["radius_kind"] for r in main] == ["interval", "point", "point"]


def test_historical_status_is_not_inferred_from_fleet_listing(bundle):
    rows = {r["vessel_name"]: r for r in bundle["vessels"]}
    assert rows["JUMBO JAVELIN"]["status"] is None
    assert rows["HAPPY BUCCANEER"]["status"] is None
    assert rows["HERMOD"]["status"]["value"] == "scrapped"


@pytest.mark.parametrize("defect", [
    "missing_provenance", "duplicate_name", "duplicate_imo", "bad_imo",
    "unknown_source", "missing_locator", "missing_quote", "negative_capacity",
    "reversed_radius", "nonfinite_tension", "plot_value", "bad_source_digest",
    "missing_source_date", "missing_record", "unknown_hull", "unresolved_fact",
])
def test_invalid_evidence_fails_closed(bundle, defect):
    row = next(row for row in bundle["vessels"] if row["imo"])
    rating = bundle["cranes"][0]
    if defect == "missing_provenance":
        bundle["vessels"][0]["provenance"] = ""
    elif defect == "duplicate_name":
        bundle["vessels"].append(copy.deepcopy(row))
    elif defect == "duplicate_imo":
        other = bundle["vessels"][0]
        other["imo"] = copy.deepcopy(row["imo"])
    elif defect == "bad_imo":
        row["imo"]["value"] = "bad"
    elif defect == "unknown_source":
        row["imo"]["source_id"] = "missing"
    elif defect == "missing_locator":
        row["imo"]["locator"] = ""
    elif defect == "missing_quote":
        row["imo"]["quote_key"] = "missing"
    elif defect == "negative_capacity":
        rating["capacity_t"] = -1
    elif defect == "reversed_radius":
        rating["radius_min_m"] = rating["radius_max_m"] + 1
    elif defect == "nonfinite_tension":
        next(r for r in bundle["vessels"] if r["pipelay"])["pipelay"][0]["tension_t"] = float("nan")
    elif defect == "plot_value":
        rating["evidence_kind"] = "plot"
    elif defect == "bad_source_digest":
        next(iter(bundle["sources"].values()))["sha256"] = "invalid"
    elif defect == "missing_source_date":
        next(iter(bundle["sources"].values()))["retrieved_at"] = ""
    elif defect == "missing_record":
        bundle["vessels"].pop()
    elif defect == "unknown_hull":
        row["hull_model"] = "../unknown.obj"
    elif defect == "unresolved_fact":
        row["identity_status"] = "unresolved"
    with pytest.raises(ValueError):
        ce.validate_evidence(bundle)


def test_export_is_deterministic_and_read_back(bundle, tmp_path):
    ce.ingest_evidence(bundle, tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    ce.ingest_evidence(bundle, tmp_path)
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert ce.load_evidence(tmp_path) == bundle
    manifest = json.loads((tmp_path / ce.MANIFEST_NAME).read_text(encoding="utf-8"))
    for name, entry in manifest["files"].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == entry["sha256"]
        assert b"\r" not in (tmp_path / name).read_bytes()
    with (tmp_path / ce.CRANE_NAME).open(encoding="utf-8", newline="") as stream:
        ratings = list(csv.DictReader(stream))
    assert len(ratings) == len(bundle["cranes"])
    assert all(row["capacity_t"] and row["radius_max_m"] and row["source_url"] for row in ratings)


def test_tampered_output_is_rejected(bundle, tmp_path):
    ce.ingest_evidence(bundle, tmp_path)
    path = tmp_path / ce.CRANE_NAME
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="digest"):
        ce.load_evidence(tmp_path)


def test_invalid_ingest_creates_no_output(bundle, tmp_path):
    bundle["vessels"].pop()
    destination = tmp_path / "output"
    with pytest.raises(ValueError):
        ce.ingest_evidence(bundle, destination)
    assert not destination.exists()


def test_imo_must_occur_in_its_cited_quote(bundle):
    row = next(row for row in bundle["vessels"] if row["imo"])
    row["imo"]["value"] = row["imo"]["value"][:-1] + "0"
    with pytest.raises(ValueError, match="quotation"):
        ce.validate_evidence(bundle)


def test_manifest_unit_drift_is_rejected(bundle, tmp_path):
    ce.ingest_evidence(bundle, tmp_path)
    path = tmp_path / ce.MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["units"]["capacity_t"] = "short tons"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="units"):
        ce.load_evidence(tmp_path)
