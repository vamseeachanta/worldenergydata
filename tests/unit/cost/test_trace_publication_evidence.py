"""Publication evidence fixtures are test-only assertions, never sourced facts."""

import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, replace

import pytest

from worldenergydata.cost.timeseries.portfolio_trace import (
    TABLES,
    build_portfolio_trace,
    canonical_events,
    write_trace_outputs,
)


def _trace(**changes):
    row = dict(
        PROJECT="Synthetic example",
        STATEMENT_DATE="2020",
        KIND="sanction_estimate",
        CURRENCY="USD",
        VALUE_MM="100",
        PROVENANCE="trade_press",
        CONFIDENCE="high",
        SOURCE_URL="https://example.org/disclosure",
        ACCESSED_DATE="2024-01-01",
    )
    row.update(changes)
    tables = {name: [] for name in TABLES}
    tables[TABLES[3]] = [row]
    return build_portfolio_trace(tables=tables)


def _annotation(trace, **changes):
    event = trace.events[0]
    annotation = dict(
        event_id=event.event_id,
        source_table_sha256=trace.input_sha256[event.source_table],
        source_url=event.source_fields["SOURCE_URL"],
        publication_date="2021-02",
        date_precision="month",
        source_locator=dict(
            url="https://example.org/disclosure#dateline",
            location="Publication dateline",
            quoted_text="Test-only publication date: February 2021",
        ),
    )
    annotation.update(changes)
    return annotation


def _apply(trace, annotations):
    # Import inside the helper so every new behavior has separate red evidence.
    from worldenergydata.cost.timeseries.publication_evidence import (
        apply_publication_evidence,
    )

    payload = json.dumps(annotations).encode()
    return apply_publication_evidence(trace, payload)


@pytest.mark.parametrize(
    "text,precision,end",
    [
        ("2021", "year", "2021-12-31"),
        ("2021-02", "month", "2021-02-28"),
        ("2021-02-03", "day", "2021-02-03"),
    ],
)
def test_precision_provenance_and_unchanged_cost_identity(text, precision, end):
    trace = _trace()
    item = _annotation(trace, publication_date=text, date_precision=precision)
    result = _apply(trace, [item])
    before, after = trace.events[0], result.events[0]
    assert before.source_available_date is None
    assert "PUBLICATION_EVIDENCE" not in before.source_fields
    assert after.source_available_date.label == text
    assert after.source_available_date.precision == precision
    assert after.source_available_date.end.isoformat() == end
    assert after.historical_feature_eligible
    assert after.confidence == "low"
    assert after.bound_qualification == result.consistency_status == "NOT_EVALUATED"
    for field in asdict(before).keys() - {"source_available_date", "source_fields"}:
        assert getattr(after, field) == getattr(before, field)
    assert after.source_fields == {
        **before.source_fields,
        "PUBLICATION_EVIDENCE": json.dumps(item, sort_keys=True),
    }
    assert (
        result.input_sha256["publication_evidence"]
        == hashlib.sha256(json.dumps([item]).encode()).hexdigest()
    )


def test_unknown_and_unannotated_dates_do_not_infer_availability():
    trace = _trace()
    assert not trace.events[0].historical_feature_eligible
    assert canonical_events(_apply(trace, [])) == canonical_events(trace)
    result = _apply(
        trace, [_annotation(trace, publication_date=None, date_precision="unknown")]
    )
    assert not result.events[0].historical_feature_eligible
    assert result.events[0].source_available_date is None
    assert "PUBLICATION_EVIDENCE" in result.events[0].source_fields


def test_identical_duplicates_and_reapplication_are_idempotent():
    trace = _trace()
    item = _annotation(trace)
    result = _apply(trace, [item, item])
    assert result == _apply(result, [item, item])
    assert canonical_events(result) == canonical_events(_apply(trace, [item]))


def test_conflicting_duplicates_fail_without_mutating_snapshot():
    trace = _trace()
    with pytest.raises(ValueError, match="conflicting"):
        _apply(
            trace, [_annotation(trace), _annotation(trace, publication_date="2022-02")]
        )
    assert trace.events[0].source_available_date is None
    assert "PUBLICATION_EVIDENCE" not in trace.events[0].source_fields


@pytest.mark.parametrize(
    "changes",
    [
        {"source_table_sha256": "0" * 64},
        {"event_id": "unknown"},
        {"source_url": "https://example.org/other"},
        {"source_table_sha256": "not-a-digest"},
        {"publication_date": "2021-02-30", "date_precision": "day"},
        {"publication_date": "2021-02", "date_precision": "day"},
        {"publication_date": "2021-2"},
        {"publication_date": None},
        {"date_precision": "unknown"},
        {"currency": "EUR"},
    ],
)
def test_invalid_or_mismatched_annotation_fails(changes):
    trace = _trace()
    with pytest.raises(ValueError):
        _apply(trace, [_annotation(trace, **changes)])


@pytest.mark.parametrize(
    "locator",
    [
        "https://example.org",
        {},
        {"url": "javascript:alert(1)", "location": "Dateline", "quoted_text": "2021"},
        {"url": "https://[invalid", "location": "Dateline", "quoted_text": "2021"},
        {"url": "https://example.org", "location": " ", "quoted_text": "2021"},
        {"url": "https://example.org", "location": "Dateline", "quoted_text": ""},
    ],
)
def test_malformed_locator_fails(locator):
    trace = _trace()
    with pytest.raises(ValueError):
        _apply(trace, [_annotation(trace, source_locator=locator)])


@pytest.mark.parametrize("date,precision", [("2022", "year"), (None, "unknown")])
def test_existing_publication_date_cannot_be_overwritten(date, precision):
    trace = _trace(SOURCE_PUBLISHED_DATE="2021-02")
    with pytest.raises(ValueError, match="publication date"):
        _apply(
            trace, [_annotation(trace, publication_date=date, date_precision=precision)]
        )
    assert (
        _apply(trace, [_annotation(trace)]).events[0].source_available_date.label
        == "2021-02"
    )


@pytest.mark.parametrize(
    "payload", [b"{}", b"null", b"[", b"[null]", b'[{"event_id":"a","event_id":"b"}]']
)
def test_invalid_json_shapes_and_duplicate_keys_fail(payload):
    from worldenergydata.cost.timeseries.publication_evidence import (
        apply_publication_evidence,
    )

    with pytest.raises(ValueError):
        apply_publication_evidence(_trace(), payload)


def test_annotation_provenance_cannot_be_replaced():
    trace = _trace()
    item = _annotation(trace)
    annotated = _apply(trace, [item])
    # Even equivalent dates in different input bytes require a fresh snapshot.
    with pytest.raises(ValueError, match="input digest"):
        _apply(annotated, [item, item])
    event = replace(
        trace.events[0],
        source_fields={
            **trace.events[0].source_fields,
            "PUBLICATION_EVIDENCE": "retained assertion",
        },
    )
    with pytest.raises(ValueError, match="conflicting"):
        _apply(replace(trace, events=(event,)), [item])
    with pytest.raises(ValueError, match="duplicate event"):
        _apply(replace(trace, events=trace.events * 2), [item])


def test_partial_overlay_preserves_unannotated_event_and_missing_source_fails():
    trace = _trace()
    other = replace(trace.events[0], event_id="other-event")
    trace = replace(trace, events=(*trace.events, other))
    result = _apply(trace, [_annotation(trace)])
    assert result.events[1] == other
    assert not result.events[1].historical_feature_eligible
    missing = _trace(SOURCE_URL="")
    with pytest.raises(ValueError):
        _apply(missing, [_annotation(missing)])


def test_cli_optional_overlay_deterministic_readback_and_protected_outputs(tmp_path):
    root = tmp_path / "curated"
    root.mkdir()
    snapshot = _trace()
    for table in TABLES:
        with (root / table).open("w", newline="") as stream:
            row = snapshot.events[0].source_fields
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            if table == TABLES[3]:
                writer.writerow(row)
    trace = build_portfolio_trace(root)
    item = _annotation(trace)
    overlay = tmp_path / "publication.json"
    overlay.write_text(json.dumps([item]))
    inputs = {p.name: p.read_bytes() for p in root.iterdir()}
    command = [
        sys.executable,
        "scripts/cost/build_project_cost_traces.py",
        "--data-root",
        str(root),
        "--revision",
        "3",
        "--revision-date",
        "2026-11-16",
        "--output-dir",
    ]
    plain = tmp_path / "plain"
    subprocess.run(command + [str(plain)], check=True, capture_output=True)
    expected = write_trace_outputs(
        trace, tmp_path / "library", revision="3", revision_date="2026-11-16"
    )
    assert {p.name: p.read_bytes() for p in plain.iterdir()} == {
        p.name: p.read_bytes() for p in expected
    }
    for name in ("first", "second"):
        subprocess.run(
            command + [str(tmp_path / name), "--publication-evidence", str(overlay)],
            check=True,
            capture_output=True,
        )
    first = {p.name: p.read_bytes() for p in (tmp_path / "first").iterdir()}
    assert first == {p.name: p.read_bytes() for p in (tmp_path / "second").iterdir()}
    event = json.loads(first["project_cost_events.json"])[0]
    assert event["source_available_date"]["precision"] == "month"
    assert json.loads(event["source_fields"]["PUBLICATION_EVIDENCE"]) == item
    with (tmp_path / "first" / "project_cost_events.csv").open(newline="") as stream:
        csv_event = next(csv.DictReader(stream))
    assert (
        json.loads(csv_event["source_fields"])["PUBLICATION_EVIDENCE"]
        == event["source_fields"]["PUBLICATION_EVIDENCE"]
    )
    assert b"source available: 2021-02" in first["project_cost_traces.html"]
    manifest = json.loads(first["project_trace_manifest.json"])
    assert (
        manifest["input_sha256"]["publication_evidence"]
        == hashlib.sha256(overlay.read_bytes()).hexdigest()
    )
    for name, digest in manifest["outputs"].items():
        assert hashlib.sha256(first[name]).hexdigest() == digest
    collision = subprocess.run(
        command + [str(tmp_path / "first"), "--publication-evidence", str(overlay)],
        capture_output=True,
    )
    assert collision.returncode != 0
    assert first == {p.name: p.read_bytes() for p in (tmp_path / "first").iterdir()}
    overlay.write_text(json.dumps([{**item, "source_table_sha256": "0" * 64}]))
    failed = subprocess.run(
        command + [str(tmp_path / "invalid"), "--publication-evidence", str(overlay)],
        capture_output=True,
    )
    assert failed.returncode != 0
    assert not (tmp_path / "invalid").exists()
    assert inputs == {p.name: p.read_bytes() for p in root.iterdir()}
