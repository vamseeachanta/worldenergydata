"""Check the committed snapshot independently of the download pipeline."""

import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

RELEASE = (
    Path(__file__).resolve().parents[4] / "data/modules/bsee/jackup_liftboat_activity"
)
REBUILD_COMMAND = (
    "Rebuild with scripts/bsee/build_jackup_activity.py "
    "--raw-dir RAW --reuse-manifest MANIFEST --output-dir OUTPUT"
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
    assert (
        hashlib.sha256(compressed).hexdigest() == manifest["table"]["sha256"]
    ), REBUILD_COMMAND
    assert (
        hashlib.sha256(raw).hexdigest() == manifest["table"]["uncompressed_sha256"]
    ), REBUILD_COMMAND
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


def test_provenance_has_only_bsee_urls_relative_blobs_and_manual_refresh(snapshot):
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
    assert "next_refresh_date" not in manifest
    assert manifest["refresh_basis"]["cadence"] == "manual"
    assert manifest["refresh_basis"]["source_cadence"] == "daily"


def test_release_exposes_identifiers_instead_of_rig_names(snapshot):
    manifest, _, _, fields, rows = snapshot
    from scripts.bsee.build_jackup_activity import data_card

    assert manifest["schema_version"] == 2
    assert date.fromisoformat(manifest["publication_date"])
    assert (RELEASE / "data_card.html").read_text(encoding="utf-8") == data_card(
        manifest
    )
    assert "rig_name" not in fields
    assert all(row["rig_id"] for row in rows)
    audit = manifest["counts"]["source_8831_ft_record_audit"]
    assert all("rig_name" not in record for record in audit)
    assert all(
        re.fullmatch(
            r"(?:bsee-rig:.+|name-sha256:[0-9a-f]{64})", record["rig_reference"]
        )
        for record in audit
    )
    assert all(record["registry_evidence"] == [] for record in audit)


def test_published_identity_and_date_disclosures_match_table(snapshot):
    manifest, _, _, _, rows = snapshot
    card = (RELEASE / "data_card.html").read_text(encoding="utf-8")
    for code, label in [("JU", "Jack-up"), ("LB", "Liftboat")]:
        group = [r for r in rows if r["rig_type"] == code]
        checks = {
            s: sum(r["rig_type_check"] == s for r in group)
            for s in ("agree", "conflict", "unavailable")
        }
        generic = sum(
            "generic_rig_identity" in r["quality_flags"].split("|") for r in group
        )
        distinct = len({r["rig_id"] for r in group})
        first = min(r["activity_start_date"][:4] for r in group)
        assert manifest["counts"]["identity_by_rig_type"][code] == {
            "records": len(group),
            "distinct_ids": distinct,
            "generic_identity_records": generic,
            "secondary_evidence": checks,
            "first_report_year": int(first),
        }
        assert (
            f"{label}: {len(group):,} reports; {distinct:,} distinct IDs; "
            f"{generic:,} generic-identity reports; secondary evidence "
            f"agree {checks['agree']:,}, conflict {checks['conflict']:,}, "
            f"unavailable {checks['unavailable']:,}; first report year {first}."
        ) in card
    first = min(r["activity_start_date"] for r in rows)
    last = max(r["activity_start_date"] for r in rows)
    assert manifest["counts"]["report_start_range"] == {"first": first, "last": last}
    assert f"First report-start date: {first}; last report-start date: {last}." in card
    assert "Rows begin in October 1997" in card
    preceding = sum(
        bool(
            r["spud_date"]
            and r["activity_end_date"]
            and r["spud_date"] > r["activity_end_date"]
        )
        for r in rows
    )
    assert manifest["counts"]["reports_preceding_spud"] == preceding
    assert f"{preceding:,} reports end before the borehole spud date." in card
