"""Check the committed snapshot independently of the download pipeline."""

import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

RELEASE = (
    Path(__file__).resolve().parents[4] / "data/modules/bsee/jackup_liftboat_activity"
)


@pytest.fixture(scope="module")
def snapshot():
    manifest = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    compressed = (RELEASE / manifest["table"]["file"]).read_bytes()
    raw = gzip.decompress(compressed)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    return manifest, compressed, raw, reader.fieldnames, list(reader)


def test_release_manifest_digests_and_size_limit(snapshot):
    manifest, compressed, raw, _, rows = snapshot
    assert hashlib.sha256(compressed).hexdigest() == manifest["table"]["sha256"]
    assert hashlib.sha256(raw).hexdigest() == manifest["table"]["uncompressed_sha256"]
    assert len(compressed) == manifest["table"]["size_bytes"] <= 1_000_000
    assert len(raw) == manifest["table"]["uncompressed_size_bytes"]
    assert (
        len(rows) == manifest["table"]["rows"] == manifest["counts"]["output_records"]
    )
    assert manifest["counts"]["input_records"] == len(rows) + sum(
        manifest["counts"]["excluded"].values()
    )


def test_release_schema_and_bsee_rig_filter(snapshot):
    manifest, _, _, fields, rows = snapshot
    assert fields == [
        "activity_id",
        "api_well_number",
        "rig_name",
        "rig_id",
        "rig_type",
        "area_code",
        "block_number",
        "water_depth_ft",
        "borehole_water_depth_ft",
        "spud_date",
        "release_date",
        "activity_start_date",
        "activity_end_date",
        "operator",
        "rig_type_check",
        "type_check_types",
        "type_check_apd_ids",
        "type_check_rig_ids",
        "deep_water_flag",
        "quality_flags",
    ]
    assert fields == manifest["table"]["columns"]
    assert {r["rig_type"] for r in rows} == {"JU", "LB"}
    assert len({r["activity_id"] for r in rows}) == len(rows)
    assert all(re.fullmatch(r"\d{12}", r["api_well_number"]) for r in rows)
    assert all(None not in r and None not in r.values() for r in rows)
    assert all("CONTACT" not in field and "PHONE" not in field for field in fields)


def test_years_and_type_cross_check_counts(snapshot):
    manifest, _, _, _, rows = snapshot
    years = Counter(date.fromisoformat(r["activity_start_date"]).year for r in rows)
    assert set(years) == set(range(1997, 2026))
    assert {str(y): n for y, n in years.items()} == manifest["counts"][
        "records_per_year"
    ]
    assert (
        dict(Counter(r["rig_type_check"] for r in rows))
        == manifest["counts"]["rig_type_checks"]
    )
    for row in rows:
        assert row["rig_type_check"] in {"agree", "conflict", "unavailable"}
        has_evidence = bool(row["type_check_apd_ids"] or row["type_check_rig_ids"])
        assert has_evidence == (row["rig_type_check"] != "unavailable")


def test_published_depth_flags_retain_implausible_values(snapshot):
    manifest, _, _, _, rows = snapshot
    flagged = 0
    for row in rows:
        depths = [row["water_depth_ft"], row["borehole_water_depth_ft"]]
        if any(value and Decimal(value) > 500 for value in depths):
            flagged += 1
            assert row["deep_water_flag"] == "true"
            assert "depth_above_500_ft" in row["quality_flags"].split("|")
        elif not all(depths):
            assert row["deep_water_flag"] == "unknown"
        else:
            assert row["deep_water_flag"] == "false"
    assert flagged > 0
    assert flagged == manifest["counts"]["deep_water_records"]


def test_release_dates_are_explicitly_unavailable_and_8831_records_are_audited(
    snapshot,
):
    manifest, _, _, _, rows = snapshot
    assert all(r["release_date"] == "" for r in rows)
    assert all(
        "release_date_unavailable" in r["quality_flags"].split("|") for r in rows
    )
    audit = manifest["counts"]["source_8831_ft_record_audit"]
    assert len(audit) == 9
    assert all(
        r["water_depth_ft"] == "8831" and r["disposition"] == "unmatched_rig_name"
        for r in audit
    )
    assert not {r["activity_id"] for r in audit} & {r["activity_id"] for r in rows}


def test_provenance_has_only_bsee_urls_relative_blobs_and_daily_refresh(snapshot):
    manifest = snapshot[0]
    expected = {
        "eWellWARRawData.zip",
        "BoreholeRawData.zip",
        "rigidlistdelimit.zip",
        "eWellAPDRawData.zip",
        "eWellEORRawData.zip",
        "eWellAPMRawData.zip",
    }
    assert {r["file"] for r in manifest["sources"]} == expected
    for source in manifest["sources"]:
        assert source["url"].startswith("https://www.data.bsee.gov/")
        assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
        assert source["archive_path"] == (
            f"blobs/sha256/{source['sha256'][:2]}/{source['sha256']}.zip"
        )
        assert source["retrieved_at_utc"][:10] == manifest["retrieval_date"]
    assert date.fromisoformat(manifest["next_refresh_date"]) == (
        date.fromisoformat(manifest["retrieval_date"]) + timedelta(days=1)
    )
