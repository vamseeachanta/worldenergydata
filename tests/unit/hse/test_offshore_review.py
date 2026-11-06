"""Offline review preparation; all records and dates are synthetic.

Policy basis: issue 1325, Acceptance (2026-10-17): three pilot authorities,
50 events and independent review of 10% of canonical records. Test arithmetic
is written out below and does not derive expected counts from the implementation.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.import_offshore_hse import main
from worldenergydata.hse.importers.offshore_importer import OffshoreImporter
from worldenergydata.hse.offshore import ReviewReceipt, text_values
from worldenergydata.hse.offshore_review import (
    build_review_worklist,
    collection_readiness,
)


def synthetic_packet(index=0, authorities=("bsee",)):
    """Use distinct installations so no date/name match merges these records."""
    event_id = f"synthetic-{index:02d}"
    event = {
        "event_id": event_id,
        "event_date": "2024-02-01",
        "country": "GB",
        "basin_or_area": "synthetic basin",
        "installation_name": f"synthetic installation {index}",
        "operation": "lifting",
        "equipment": ["hoist"],
        "failure_mode": "not established",
        "failure_summary": "synthetic event for software testing",
    }
    hosts = {
        "bsee": "www.bsee.gov",
        "uk_hse": "www.hse.gov.uk",
        "opred": "itportal.energysecurity.gov.uk",
    }
    sources = [
        {
            "event_id": event_id,
            "source": authority,
            "source_ref": f"synthetic-{index}",
            "title": "synthetic report",
            "doc_type": "investigation report",
            "issue_date": "2024-02-02",
            "status": "synthetic",
            "url": f"https://{hosts[authority]}/synthetic",
            "access_date": "2024-02-03",
            "licence": "synthetic metadata only",
            "evidence_level": "regulator",
            "access_status": "public",
        }
        for authority in authorities
    ]
    payload = {"events": [event], "sources": sources}
    return dict(payload, reviewed_text=sorted(set(text_values(payload))))


def receipt(importer, reviewed_ids):
    """A test attestation; no independent source review is represented."""
    return {
        "verdict": "pass",
        "reviewer_role": "independent_agent",
        "reviewed_event_ids": reviewed_ids,
        "dataset_sha256": importer.content_digest(),
    }


def populated(importer, count=1):
    importer.ingest(synthetic_packet(authorities=("bsee", "uk_hse", "opred")))
    importer.approve_pilot("synthetic-00", receipt(importer, ["synthetic-00"]))
    for index in range(1, count):
        importer.ingest(synthetic_packet(index), stage="candidate")


def complete_indexes():
    return {
        "hse": {
            "complete": True,
            "records": [
                {
                    "record_id": "synthetic-existing",
                    "event_date": "2024-02-01",
                    "country": "US",
                    "installation_name": "synthetic other installation",
                }
            ],
        },
        "marine_safety": {"complete": True, "records": []},
    }


def test_empty_readiness_distinguishes_missing_evidence_from_zero(tmp_path):
    """Zero records cannot meet 50; an absent pilot has no source count."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    before = importer.database.read_bytes()
    result = collection_readiness(importer)
    assert result["canonical_event_count"] == 0
    assert result["required_review_count"] == 0
    assert result["checks"]["minimum_events"]["status"] == "FAIL"
    assert result["checks"]["pilot_public_sources"]["status"] == "NOT_EVALUATED"
    assert result["checks"]["pilot_public_sources"]["observed"] is None
    assert result["checks"]["pilot_review"]["status"] == "NOT_EVALUATED"
    assert result["ready_for_bulk_review"] is False
    assert result["bulk_admitted"] is False
    assert importer.database.read_bytes() == before


def test_public_pilot_count_excludes_cached_and_repeated_authorities(tmp_path):
    """Three rows minus one cached row give two distinct public authorities."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    payload = synthetic_packet(authorities=("bsee", "uk_hse", "opred"))
    payload["sources"][-1]["access_status"] = "cached"
    payload["sources"].append(dict(payload["sources"][0], source_ref="second"))
    payload["reviewed_text"] = list(text_values(payload))
    importer.ingest(payload)
    check = collection_readiness(importer)["checks"]["pilot_public_sources"]
    assert check == {"status": "FAIL", "observed": 2, "required": 3}


@pytest.mark.parametrize(
    ("count", "expected"), [(1, 1), (9, 1), (10, 1), (11, 2), (49, 5), (50, 5), (51, 6)]
)
def test_review_rounds_up_canonical_count(tmp_path, count, expected):
    """Hand calculation: ceil(n/10) for n=1,9,10,11,49,50,51 is 1,1,1,2,5,5,6.

    Issue 1325 Acceptance requires a 10% independent sample. A fraction of a
    record is rounded upward so the selected fraction cannot fall below 10%.
    """
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    populated(importer, count)
    result = collection_readiness(importer)
    worklist = build_review_worklist(importer, stage="bulk")
    assert result["canonical_event_count"] == count
    assert result["required_review_count"] == expected
    assert len(worklist["records"]) == expected
    assert len(set(worklist["selected_event_ids"])) == expected
    assert worklist["required_review_count"] == expected
    assert result["checks"]["pilot_review"]["status"] == "PASS"


def test_readiness_requires_consumed_indexes_and_actual_bulk_receipt(tmp_path):
    """50 events meet the minimum; 10% of 50 is five checked records."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    populated(importer, 50)
    result = collection_readiness(importer)
    assert result["checks"]["minimum_events"]["status"] == "PASS"
    assert result["ready_for_bulk_review"] is False
    indexes = complete_indexes()
    importer.reconcile_existing(indexes)
    result = collection_readiness(importer)
    assert result["ready_for_bulk_review"] is True
    assert result["bulk_admitted"] is False
    worklist = build_review_worklist(importer, stage="bulk")
    importer.approve_bulk(receipt(importer, worklist["selected_event_ids"]), indexes)
    assert collection_readiness(importer)["bulk_admitted"] is True
    importer.ingest(synthetic_packet(50), stage="candidate")
    result = collection_readiness(importer)
    assert result["ready_for_bulk_review"] is False
    assert result["bulk_admitted"] is False


@pytest.mark.parametrize("gate", ["bulk", "existing_indexes"])
def test_stale_receipts_are_never_reported_as_pass(tmp_path, gate):
    """A receipt for different evidence cannot establish current acceptance."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    populated(importer, 50)
    indexes = complete_indexes()
    importer.reconcile_existing(indexes)
    importer.approve_bulk(
        receipt(importer, [f"synthetic-{i:02d}" for i in range(5)]), indexes
    )
    with importer.connect() as db:
        payload = json.loads(
            db.execute("SELECT payload FROM gates WHERE name=?", (gate,)).fetchone()[0]
        )
        target = payload["review"] if gate == "bulk" else payload
        target["dataset_sha256"] = "0" * 64
        db.execute(
            "UPDATE gates SET payload=? WHERE name=?", (json.dumps(payload), gate)
        )
    result = collection_readiness(importer)
    key = "bulk_review" if gate == "bulk" else "existing_index_reconciliation"
    assert result["checks"][key]["status"] == "FAIL"
    assert result["bulk_admitted"] is False


def test_worklist_is_repeatable_cited_and_does_not_grant_review(tmp_path):
    """One pilot event requires its complete three-source evidence packet."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    importer.ingest(synthetic_packet(authorities=("bsee", "uk_hse", "opred")))
    before = importer.database.read_bytes()
    result = build_review_worklist(importer, stage="pilot")
    assert result == build_review_worklist(importer, stage="pilot")
    assert result["dataset_sha256"] == importer.content_digest()
    assert result["selected_event_ids"] == ["synthetic-00"]
    assert result["review_status"] == "NOT_EVALUATED"
    assert "verdict" not in result
    with pytest.raises(ValidationError):
        ReviewReceipt.model_validate(result)
    record = result["records"][0]
    assert len(record["sources"]) == 3
    assert all("Licence:" in source["citation"] for source in record["sources"])
    assert record["event"]["operation"] == "lifting"
    assert importer.database.read_bytes() == before
    assert (
        collection_readiness(importer)["checks"]["pilot_review"]["status"]
        == "NOT_EVALUATED"
    )


def test_worklist_digest_and_rows_share_one_read_snapshot(tmp_path, monkeypatch):
    """A concurrent second source must appear in neither the old rows nor digest.

    Independent count: one original source, one added source, two after commit.
    WAL permits that writer to commit while the first read snapshot stays open.
    """
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    importer.ingest(synthetic_packet())
    with importer.connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
    before = importer.content_digest()
    writer = OffshoreImporter(importer.database)
    original_digest = importer.content_digest

    def concurrent_digest(db):
        writer.ingest(synthetic_packet(authorities=("opred",)))
        return original_digest(db)

    monkeypatch.setattr(importer, "content_digest", concurrent_digest)
    worklist = build_review_worklist(importer, stage="pilot")
    assert worklist["dataset_sha256"] == before
    assert len(worklist["records"][0]["sources"]) == 1
    assert writer.content_digest() != before
    assert (
        len(build_review_worklist(writer, stage="pilot")["records"][0]["sources"]) == 2
    )


@pytest.mark.parametrize("gate", ["pilot", "bulk"])
def test_malformed_review_receipt_is_reported_as_failure(tmp_path, gate):
    """A wrong reviewer role is not an independent-agent attestation."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    populated(importer)
    bad = receipt(importer, ["synthetic-00"])
    bad["reviewer_role"] = "not_reviewed"
    with importer.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO gates VALUES(?,?)",
            (gate, json.dumps({"pilot_event_id": "synthetic-00", "review": bad})),
        )
    assert (
        collection_readiness(importer)["checks"][f"{gate}_review"]["status"] == "FAIL"
    )


@pytest.mark.parametrize(
    "change", [{"sha256": None}, {"record_count": -1}, {"complete": "true"}]
)
def test_incomplete_index_receipt_is_never_reported_as_pass(tmp_path, change):
    """A complete-index attestation needs a digest and a nonnegative row count."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    populated(importer)
    importer.reconcile_existing(complete_indexes())
    with importer.connect() as db:
        gate = json.loads(
            db.execute(
                "SELECT payload FROM gates WHERE name='existing_indexes'"
            ).fetchone()[0]
        )
        gate["indexes"]["marine_safety"].update(change)
        db.execute(
            "UPDATE gates SET payload=? WHERE name='existing_indexes'",
            (json.dumps(gate),),
        )
    result = collection_readiness(importer)
    assert result["checks"]["existing_index_reconciliation"]["status"] == "FAIL"


def test_linked_event_retains_identity_annotations_and_source_evidence(tmp_path):
    """A linked canonical event counts once even if it has two module links."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    row = {
        "record_id": "synthetic-existing",
        "event_date": "2024-02-01",
        "country": "GB",
        "installation_name": "synthetic installation 0",
    }
    importer.ingest(synthetic_packet(), existing=[dict(row, module="hse")])
    importer.reconcile_existing(
        {
            "hse": {"complete": True, "records": [row]},
            "marine_safety": {"complete": True, "records": [row]},
        }
    )
    result = collection_readiness(importer)
    assert result["canonical_event_count"] == 1
    assert result["standalone_event_count"] == 0
    assert result["external_link_count"] == 2
    record = build_review_worklist(importer, stage="bulk")["records"][0]
    assert record["event"] is None
    assert len(record["external_links"]) == 2
    assert all(
        link["annotations"]["equipment"] == ["hoist"]
        for link in record["external_links"]
    )
    assert record["sources"][0]["event_id"] == "synthetic-00"


@pytest.mark.parametrize("stage", ["pilot", "bulk"])
def test_empty_worklist_is_refused(tmp_path, stage):
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    with pytest.raises(ValueError, match="no canonical events"):
        build_review_worklist(importer, stage=stage)


def test_pilot_worklist_requires_unambiguous_selection(tmp_path):
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    populated(importer, 2)
    assert build_review_worklist(importer, stage="pilot")["selected_event_ids"] == [
        "synthetic-00"
    ]
    with importer.connect() as db:
        db.execute("DELETE FROM gates WHERE name='pilot'")
    with pytest.raises(ValueError, match="pilot event"):
        build_review_worklist(importer, stage="pilot")
    assert build_review_worklist(
        importer, stage="pilot", pilot_event_id="synthetic-01"
    )["selected_event_ids"] == ["synthetic-01"]
    with pytest.raises(ValueError, match="pilot event"):
        build_review_worklist(importer, stage="pilot", pilot_event_id="unknown")


def test_worklist_rejects_unknown_stage(tmp_path):
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    with pytest.raises(ValueError, match="stage"):
        build_review_worklist(importer, stage="unknown")


def test_cli_prints_readiness_and_review_worklist(tmp_path, capsys):
    """The CLI exposes both read-only slices using the existing database root."""
    importer = OffshoreImporter(tmp_path / "modules/hse/offshore/offshore.sqlite")
    importer.ingest(synthetic_packet())
    main(["--data-root", str(tmp_path), "--readiness", "--review-worklist", "pilot"])
    result = json.loads(capsys.readouterr().out)
    assert result["readiness"]["canonical_event_count"] == 1
    assert result["review_worklist"]["selected_event_ids"] == ["synthetic-00"]


def test_read_only_importer_cannot_mutate_evidence(tmp_path):
    """Read-only review preparation cannot write or migrate an existing store."""
    importer = OffshoreImporter(tmp_path / "collection.sqlite")
    importer.ingest(synthetic_packet())
    before = importer.database.read_bytes()
    reader = OffshoreImporter(importer.database, read_only=True)
    assert collection_readiness(reader)["canonical_event_count"] == 1
    assert build_review_worklist(reader, stage="pilot")["records"]
    with (
        reader.connect() as db,
        pytest.raises(sqlite3.OperationalError, match="readonly"),
    ):
        db.execute("DELETE FROM events")
    assert importer.database.read_bytes() == before


def test_cli_intake_can_be_combined_with_read_only_reports(tmp_path, capsys):
    """Explicit intake writes one event, then both reports describe that evidence."""
    packet_path = tmp_path / "input.json"
    packet_path.write_text(json.dumps(synthetic_packet()))
    main(
        [
            "--data-root",
            str(tmp_path),
            "--packet",
            str(packet_path),
            "--readiness",
            "--review-worklist",
            "pilot",
            "--digest",
        ]
    )
    result = json.loads(capsys.readouterr().out)
    assert result["intake"]["events_added"] == 1
    assert result["readiness"]["canonical_event_count"] == 1
    assert result["dataset_sha256"] == result["review_worklist"]["dataset_sha256"]


def test_read_only_missing_database_does_not_create_parent(tmp_path):
    path = tmp_path / "absent" / "collection.sqlite"
    with pytest.raises(FileNotFoundError, match="existing collection"):
        OffshoreImporter(path, read_only=True)
    assert not path.parent.exists()


def test_cli_readiness_does_not_create_collection(tmp_path):
    """Inspecting a missing collection must expose missing evidence, not create it."""
    with pytest.raises(FileNotFoundError, match="existing collection"):
        main(["--data-root", str(tmp_path), "--readiness"])
    assert not (tmp_path / "modules").exists()


def test_worked_example_reports_duplicate_and_unmet_gates(tmp_path):
    """Two intakes of one event leave one event/source; 1/10 rounds up to 1."""
    from examples.offshore_hse_review import run_example

    result = run_example(tmp_path / "example")
    assert result["first_intake"]["events_added"] == 1
    assert result["repeat_intake"]["events_added"] == 0
    assert result["repeat_intake"]["sources_added"] == 0
    assert result["readiness"]["canonical_event_count"] == 1
    assert result["readiness"]["checks"]["pilot_public_sources"]["status"] == "FAIL"
    assert result["readiness"]["bulk_admitted"] is False
    assert result["worklist"]["selected_event_ids"] == ["example-event"]
    saved = json.loads((tmp_path / "example" / "answer.json").read_text())
    assert saved == result
    assert Path(tmp_path / "example" / "input.json").is_file()
