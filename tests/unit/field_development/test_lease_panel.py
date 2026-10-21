"""Lease-panel contracts, with expected values read independently from sources.

BSEE Lease Data and Lease Owner layouts (retrieved 2026-10-20) define dates,
ASSIGNMENT_PCT, OWNER_GROUP_CODE and OWNER_ALIQUOT_CD. Recorded source rows:
tests/fixtures/bsee/leases/provenance.json. No percentage aggregation is valid
across partial-assignment groups; these tests compare source rows individually.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from worldenergydata.field_development.landman import (
    build_landman,
    load_lease_snapshot,
)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/modules/bsee/leases"


def panel(snapshot, leases=None):
    return build_landman(
        {},
        leases or ["OCS-G 16942"],
        ["ZZ999"],
        {},
        959,
        lease_snapshot=snapshot,
    )


def test_recorded_source_values_and_distinct_expiration():
    """Fixture: G16942, PROD, WR029, 19960901, expected 20060831.

    Lease Data has no actual expiration. Owner fixture rows carry 27.5,
    12.5 and 60.0 percent; assignment approval is 20260728. These are
    transcribed source inputs, not computed expectations.
    """
    result = panel(load_lease_snapshot(SOURCE))
    row = result["leases"][0]
    assert row["status"] == "PROD"
    assert row["per_lease_block"] == "WR029"
    assert row["effective_date"] == "1996-09-01"
    assert row["expiration_date"] is None
    assert row["expected_expiration_date"] == "2006-08-31"
    assert row["approval_date"] == ["2026-07-28"] * 3
    assert [r["ASSIGNMENT_PCT"] for r in row["per_lease_working_interest"]] == [
        27.5,
        12.5,
        60.0,
    ]
    assert "expiration_date" in row["missing"]
    assert "status" not in result["pending"]
    assert "per_lease_block" not in result["pending"]
    assert result["source"]["source_vintage"] is None
    assert result["source"]["retrieved_at_utc"]


def test_all_snapshot_leases_round_trip_and_preserve_history():
    """Each source row joins through the canonical registry, without dropping history."""
    from worldenergydata.common.fields_registry import load_fields

    snapshot = load_lease_snapshot(SOURCE)
    registry = load_fields(ROOT / "config/fields.yml")
    owners = json.loads((SOURCE / "panel_values.json").read_text())
    history = json.loads((SOURCE / "operators.json").read_text())
    for field in registry.fields:
        leases = [lease for lease in field.leases if lease in snapshot["leases"]]
        for row in panel(snapshot, leases)["leases"] if leases else []:
            assert registry.by_lease(row["lease_num"]) == field.canonical_id
            source = next(r for r in owners if r["lease_num"] == row["lease_num"])
            assert row["per_lease_working_interest"] == source["current_owners"]
            assert row["operator_of_record_history"] == [
                r for r in history if r["LEASE_NUMBER"] == row["lease_num"]
            ]


def test_unknown_lease_kept_and_registry_blocks_never_paired():
    result = panel(load_lease_snapshot(SOURCE), ["G99999"])
    row = result["leases"][0]
    assert row["lease_num"] == "G99999"
    assert row["per_lease_block"] is None
    assert "snapshot" in row["missing"]["status"]
    assert "per_lease_block" in result["pending"]
    assert "ZZ999" not in result["table_html"]


def test_group_interests_zero_and_html_are_preserved():
    """Synthetic partial assignment: zero stays zero, two groups stay two rows.

    Zero is an exact input here, not a missing-value sentinel. Group identifiers
    and aliquots are copied literally under the BSEE Lease Owner layout.
    """
    snapshot = copy.deepcopy(load_lease_snapshot(SOURCE))
    owner = snapshot["leases"]["G16942"]["current_owners"][0]
    owner.update(owner_name='<script>unsafe & "quoted"</script>', ASSIGNMENT_PCT=0.0)
    extra = dict(owner, OWNER_GROUP_CODE="other", OWNER_ALIQUOT_CD="partial")
    snapshot["leases"]["G16942"]["current_owners"] = [owner, extra]
    result = panel(snapshot)
    assert len(result["leases"][0]["per_lease_working_interest"]) == 2
    html = result["table_html"]
    assert "<script>" not in html
    assert "&lt;script&gt;unsafe &amp; &quot;quoted&quot;" in html
    assert "0.0%" in html and "other" in html and "partial" in html


def test_missing_current_owners_and_operators_keep_source_reasons():
    snapshot = copy.deepcopy(load_lease_snapshot(SOURCE))
    source = snapshot["leases"]["G16942"]
    source.update(
        current_owners=[],
        operator=[],
        owner_reason="No current owner rows in package",
        operator_reason="Company number absent from Company (All)",
    )
    result = panel(snapshot)
    row = result["leases"][0]
    assert "per_lease_working_interest" in result["pending"]
    assert row["missing"]["per_lease_working_interest"] == source["owner_reason"]
    assert row["missing"]["operator"] == source["operator_reason"]
    assert source["owner_reason"] in result["table_html"]
    assert source["operator_reason"] in result["table_html"]


def test_published_table_shows_current_designations_and_retains_source_history():
    snapshot = copy.deepcopy(load_lease_snapshot(SOURCE))
    current = {
        "operator_name": '<current & "operator">',
        "ASGN_STATUS_CODE": "C",
        "LEASE_DESIG_DATE": "2026-01-01",
        "ASGN_EFF_DATE": "2026-02-01",
        "ASGN_APRV_DATE": "2026-03-01",
    }
    former = dict(current, operator_name="Former designation", ASGN_STATUS_CODE="T")
    source = snapshot["leases"]["G16942"]
    source.update(
        operator=[current["operator_name"]],
        current_operators=[current],
        operator_of_record_history=[former, current],
    )
    result = panel(snapshot)
    assert result["leases"][0]["operator_of_record_history"] == [former, current]
    html = result["table_html"]
    assert "Former designation" not in html
    assert "Current operator designations" in html
    assert "&lt;current &amp; &quot;operator&quot;&gt;" in html
    assert "designated 2026-01-01" in html
    assert "effective 2026-02-01" in html
    assert "approved 2026-03-01" in html
    assert "full history remains in the source snapshot" in html


@pytest.mark.parametrize(
    "filename",
    ["leases.json", "panel_values.json", "operators.json", "source_manifest.json"],
)
def test_snapshot_rejects_changed_source_bytes(tmp_path, filename):
    for path in SOURCE.glob("*.json"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    path = tmp_path / filename
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest"):
        load_lease_snapshot(tmp_path)


def test_snapshot_rejects_duplicate_normalized_identifiers(tmp_path):
    for path in SOURCE.glob("*.json"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    path = tmp_path / "leases.json"
    rows = json.loads(path.read_text())
    rows.append(dict(rows[0], lease_num="OCS-G 16942"))
    path.write_text(json.dumps(rows))
    manifest_path = tmp_path / "extract_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    record = next(r for r in manifest["artifacts"] if r["file"] == path.name)
    record.update(
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        size_bytes=path.stat().st_size,
    )
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Duplicate"):
        load_lease_snapshot(tmp_path)
