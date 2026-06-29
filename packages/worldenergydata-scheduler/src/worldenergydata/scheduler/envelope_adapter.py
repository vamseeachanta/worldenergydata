# ABOUTME: Map scheduler JobResult -> shared ResultEnvelope (workspace-hub#3286).
# ABOUTME: provenance.data_as_of comes from the job's _metadata.json["last_refresh"].

"""Adapt a scheduler :class:`JobResult` to the shared
:class:`assetutilities.workflow_api.ResultEnvelope` (workspace-hub#3282).

Scheduler jobs are NETWORK refreshes -> non-deterministic, so the adapter keeps
``determinism`` honest (``result_hash=None``, ``reproducible=None``) rather than
fabricating a hash. ``provenance.data_as_of`` is read from the job's
``_metadata.json["last_refresh"]`` (the freshness timestamp
``write_refresh_metadata`` stamps); ``None`` when the file is absent/unreadable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from worldenergydata.scheduler.jobs.base import JobResult

# JobResult.status -> ResultEnvelope.status
_STATUS_MAP = {"success": "ok", "skipped": "ok", "failure": "error"}


def _read_last_refresh(metadata_path: Optional[Any]) -> Optional[str]:
    """Return ``_metadata.json["last_refresh"]`` or ``None`` if absent/unreadable."""
    if metadata_path is None:
        return None
    path = Path(metadata_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data.get("last_refresh")


def job_result_to_envelope(
    result: "JobResult",
    *,
    metadata_path: Optional[Any] = None,
    input_hash_value: Optional[str] = None,
):
    """Map a :class:`JobResult` to a :class:`ResultEnvelope`.

    success -> ok, skipped -> ok (+ "job skipped" warning), failure -> error.
    Carries ``records_updated`` + timing in ``result``; populates
    ``provenance.data_as_of`` from ``_metadata.json``; ``determinism`` stays
    honestly ``None`` (network refresh).
    """
    from assetutilities.workflow_api import ResultEnvelope, make_provenance

    warnings = []
    if result.status == "skipped":
        warnings.append("job skipped (disabled)")
    if result.error_msg:
        warnings.append(result.error_msg)

    data_as_of = _read_last_refresh(metadata_path)
    duration_s = (result.end_time - result.start_time).total_seconds()

    return ResultEnvelope(
        workflow_id=result.job_name,
        status=_STATUS_MAP.get(result.status, "error"),
        result={
            "records_updated": result.records_updated,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "duration_s": duration_s,
            "retryable": result.retryable,
        },
        provenance=make_provenance(
            input_hash_value,
            package_name="worldenergydata",
            data_as_of=data_as_of,
        ),
        determinism={"result_hash": None, "reproducible": None},
        confidence=None,
        warnings=warnings,
    )
