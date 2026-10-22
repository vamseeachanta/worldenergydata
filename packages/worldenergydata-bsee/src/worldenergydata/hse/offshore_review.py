"""Read-only readiness diagnostics and evidence-bound offshore review worklists.

This module prepares work for a reviewer. It neither performs source review nor
creates an approval receipt, and never turns a missing check into a pass.
"""

from __future__ import annotations

import hashlib
import json
import re

from pydantic import ValidationError

from worldenergydata.hse.offshore import ReviewReceipt, SourceDocument

# Collection policy, not engineering coefficients: issue 1325 (2026-10-17),
# Acceptance items 2, 3 and 6. Ten percent is one record per ten, rounded up.
# https://github.com/vamseeachanta/worldenergydata/issues/1325
PILOT_AUTHORITIES = 3
MINIMUM_EVENTS = 50
REVIEW_DENOMINATOR = 10
CRITERIA = "worldenergydata issue 1325, Acceptance (2026-10-17)"


def _snapshot(importer):
    """Read all evidence and its digest within the same SQLite transaction."""
    with importer.connect() as db:
        db.execute("BEGIN")
        events = {
            row[0]: json.loads(row[1])
            for row in db.execute(
                "SELECT event_id,payload FROM events ORDER BY event_id"
            )
        }
        links = [
            {
                "event_id": row[0],
                "module": row[1],
                "record_id": row[2],
                "identity": json.loads(row[3]),
                "annotations": json.loads(row[4]),
            }
            for row in db.execute(
                "SELECT * FROM external_links ORDER BY event_id,module,record_id"
            )
        ]
        sources = [
            json.loads(row[0])
            for row in db.execute(
                "SELECT payload FROM sources ORDER BY source,source_ref"
            )
        ]
        gates = {
            row[0]: json.loads(row[1])
            for row in db.execute("SELECT name,payload FROM gates ORDER BY name")
        }
        return {
            "events": events,
            "links": links,
            "sources": sources,
            "gates": gates,
            "digest": importer.content_digest(db),
            "ids": sorted(set(events) | {link["event_id"] for link in links}),
        }


def _required_reviews(count):
    # Integer ceiling of count / 10; policy citation is above, not a risk model.
    return (count + REVIEW_DENOMINATOR - 1) // REVIEW_DENOMINATOR


def _pilot_id(snapshot):
    gate = snapshot["gates"].get("pilot", {})
    if gate:
        return gate.get("pilot_event_id")
    return snapshot["ids"][0] if len(snapshot["ids"]) == 1 else None


def _receipt_valid(review, snapshot, *, current):
    try:
        receipt = ReviewReceipt.model_validate(review)
    except ValidationError:
        return False
    return set(receipt.reviewed_event_ids) <= set(snapshot["ids"]) and (
        not current or receipt.dataset_sha256 == snapshot["digest"]
    )


def _index_row_valid(row):
    # Digest representation follows ReviewReceipt in hse/offshore.py; counts
    # describe rows, so a missing, fractional or negative count is not evidence.
    return (
        isinstance(row, dict)
        and set(row) == {"complete", "record_count", "sha256"}
        and row["complete"] is True
        and type(row["record_count"]) is int
        and row["record_count"] >= 0
        and isinstance(row["sha256"], str)
        and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
    )


def _index_status(snapshot):
    gate = snapshot["gates"].get("existing_indexes")
    if gate is None:
        return "NOT_EVALUATED"
    indexes = gate.get("indexes", {})
    valid = (
        gate.get("dataset_sha256") == snapshot["digest"]
        and isinstance(indexes, dict)
        and set(indexes) == {"hse", "marine_safety"}
        and all(_index_row_valid(row) for row in indexes.values())
        and indexes["hse"].get("record_count", 0) > 0
    )
    return "PASS" if valid else "FAIL"


def _pilot_checks(snapshot):
    pilot_id = _pilot_id(snapshot)
    public_count = (
        len(
            {
                source["source"]
                for source in snapshot["sources"]
                if source["event_id"] == pilot_id
                and source["access_status"] == "public"
            }
        )
        if pilot_id in snapshot["ids"]
        else None
    )
    pilot_gate = snapshot["gates"].get("pilot")
    pilot_review = "NOT_EVALUATED"
    if pilot_gate is not None:
        pilot_review = (
            "PASS"
            if _receipt_valid(pilot_gate.get("review"), snapshot, current=False)
            and pilot_id in pilot_gate["review"]["reviewed_event_ids"]
            else "FAIL"
        )
    return {
        "pilot_public_sources": {
            "status": (
                "NOT_EVALUATED"
                if public_count is None
                else "PASS" if public_count >= PILOT_AUTHORITIES else "FAIL"
            ),
            "observed": public_count,
            "required": PILOT_AUTHORITIES,
        },
        "pilot_review": {"status": pilot_review},
    }


def _bulk_status(snapshot, ready):
    bulk_gate = snapshot["gates"].get("bulk")
    bulk_review = "NOT_EVALUATED"
    if bulk_gate is not None:
        valid = _receipt_valid(bulk_gate.get("review"), snapshot, current=True)
        enough = valid and len(
            set(bulk_gate["review"]["reviewed_event_ids"])
        ) >= _required_reviews(len(snapshot["ids"]))
        coverage = snapshot["gates"].get("existing_indexes", {}).get("indexes")
        bulk_review = (
            "PASS"
            if ready and enough and bulk_gate.get("existing_coverage") == coverage
            else "FAIL"
        )
    return bulk_review


def collection_readiness(importer):
    """Describe recorded intake gates without granting or renewing acceptance.

    Pilot approval is historical: candidate intake intentionally changes the
    whole-dataset digest. The importer maintains that gate when pilot sources
    change. Bulk and reconciliation receipts must bind the current digest.
    """
    snapshot = _snapshot(importer)
    count = len(snapshot["ids"])
    checks = _pilot_checks(snapshot)
    checks["minimum_events"] = {
        "status": "PASS" if count >= MINIMUM_EVENTS else "FAIL",
        "observed": count,
        "required": MINIMUM_EVENTS,
    }
    checks["existing_index_reconciliation"] = {"status": _index_status(snapshot)}
    ready = all(check["status"] == "PASS" for check in checks.values())
    bulk_review = _bulk_status(snapshot, ready)
    checks["bulk_review"] = {"status": bulk_review}
    return {
        "schema_version": 1,
        "criteria": CRITERIA,
        "dataset_sha256": snapshot["digest"],
        "canonical_event_count": count,
        "standalone_event_count": len(snapshot["events"]),
        "external_link_count": len(snapshot["links"]),
        "source_count": len(snapshot["sources"]),
        "pilot_event_id": _pilot_id(snapshot),
        "required_review_count": _required_reviews(count),
        "checks": checks,
        "ready_for_bulk_review": ready,
        "bulk_admitted": ready and bulk_review == "PASS",
        "limitations": [
            "Recorded receipts are attestations, not authenticated source reviews.",
            "Source truth, personal-name absence and index completeness require independent review.",
            "Collection admission does not establish engineering input qualification.",
        ],
    }


def _review_records(snapshot, selected):
    records = []
    for event_id in selected:
        records.append(
            {
                "event_id": event_id,
                "event": snapshot["events"].get(event_id),
                "external_links": [
                    link for link in snapshot["links"] if link["event_id"] == event_id
                ],
                "sources": [
                    dict(
                        source, citation=SourceDocument.model_validate(source).citation
                    )
                    for source in snapshot["sources"]
                    if source["event_id"] == event_id
                ],
            }
        )
    return records


def build_review_worklist(importer, *, stage="bulk", pilot_event_id=None):
    """Select a reproducible review sample and include its complete stored evidence.

    SHA-256(dataset digest + ':' + event ID) orders the bulk sample, independently
    of insertion order. A worklist has no pass verdict and cannot be submitted
    as a ReviewReceipt. Reviewers may check more than this minimum sample.
    """
    if stage not in {"pilot", "bulk"}:
        raise ValueError("review stage must be pilot or bulk")
    snapshot = _snapshot(importer)
    if not snapshot["ids"]:
        raise ValueError("no canonical events available for review")
    if stage == "pilot":
        event_id = pilot_event_id or _pilot_id(snapshot)
        if event_id not in snapshot["ids"]:
            raise ValueError("a known pilot event ID is required")
        selected = [event_id]
    else:
        selected = sorted(
            snapshot["ids"],
            key=lambda event_id: hashlib.sha256(
                f"{snapshot['digest']}:{event_id}".encode()
            ).hexdigest(),
        )[: _required_reviews(len(snapshot["ids"]))]
    return {
        "schema_version": 1,
        "criteria": CRITERIA,
        "stage": stage,
        "dataset_sha256": snapshot["digest"],
        "sampling_method": (
            "pilot event"
            if stage == "pilot"
            else "ascending sha256(dataset_sha256:event_id)"
        ),
        "required_review_count": len(selected),
        "selected_event_ids": selected,
        "review_status": "NOT_EVALUATED",
        "records": _review_records(snapshot, selected),
    }
