# ABOUTME: TDD for scheduler JobResult -> ResultEnvelope adapter (workspace-hub#3286).
# ABOUTME: status mapping, records/timing payload, data_as_of from _metadata.json, honest determinism.

"""Tests for ``worldenergydata.scheduler.envelope_adapter``."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from worldenergydata.scheduler.envelope_adapter import job_result_to_envelope
from worldenergydata.scheduler.jobs.base import JobResult


def _job(status="success", records=10, error=None, retryable=True):
    start = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 28, 12, 0, 30, tzinfo=timezone.utc)
    return JobResult(
        job_name="bsee_refresh",
        start_time=start,
        end_time=end,
        status=status,
        records_updated=records,
        error_msg=error,
        retryable=retryable,
    )


def test_envelope_adapter_success_maps_ok():
    env = job_result_to_envelope(_job(status="success", records=42))
    assert env.status == "ok"
    assert env.workflow_id == "bsee_refresh"
    assert env.result["records_updated"] == 42
    assert env.result["duration_s"] == 30.0
    assert env.warnings == []


def test_envelope_adapter_failure_maps_error():
    env = job_result_to_envelope(
        _job(status="failure", error="stale upstream URL serving HTML")
    )
    assert env.status == "error"
    assert "stale upstream URL serving HTML" in env.warnings


def test_envelope_adapter_skipped_maps_ok_with_warning():
    env = job_result_to_envelope(_job(status="skipped"))
    assert env.status == "ok"
    assert any("skip" in w.lower() for w in env.warnings)


def test_envelope_adapter_data_as_of_from_metadata(tmp_path):
    meta = tmp_path / "_metadata.json"
    meta.write_text(
        json.dumps(
            {
                "module": "bsee",
                "last_refresh": "2026-06-28T18:30:00+00:00",
                "record_count": 100,
            }
        )
    )
    env = job_result_to_envelope(_job(), metadata_path=meta)
    assert env.provenance["data_as_of"] == "2026-06-28T18:30:00+00:00"


def test_envelope_adapter_data_as_of_absent_file_is_none(tmp_path):
    env = job_result_to_envelope(_job(), metadata_path=tmp_path / "missing.json")
    assert env.provenance["data_as_of"] is None
    # also None when no path passed at all
    assert job_result_to_envelope(_job()).provenance["data_as_of"] is None


def test_envelope_adapter_determinism_none():
    env = job_result_to_envelope(_job())
    assert env.determinism["result_hash"] is None
    assert env.determinism["reproducible"] is None


def test_envelope_adapter_input_hash_passthrough():
    env = job_result_to_envelope(_job(), input_hash_value="abc123")
    assert env.provenance["input_hash"] == "abc123"
    # wed stamps its own package version
    assert env.provenance["code_version"]["package_version"] is not None
