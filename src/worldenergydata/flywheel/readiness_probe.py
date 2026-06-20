# ABOUTME: Read-only source-readiness probe for well-operations flywheel runs (#451).
# ABOUTME: Checks local BSEE/FDAS inputs (presence, freshness, non-stub size); never fetches/writes.
"""Read-only source-readiness probe for well-operations runs.

Issue #451. Before a well-operations insight run, this probe inspects the
*local filesystem* for the data sources a run needs and reports, per source,
whether it is ``available`` / ``stale`` / ``missing`` (plus ``blocked`` and
``reference_data``), together with an overall go / no-go.

Design constraints (from #451):

* **Read-only.** The probe only stats / reads local files. It never fetches
  from a network and never writes data. Refreshing is someone else's job
  (scheduler / refresh scripts referenced in the issue).
* **Reuse the #462 acceptance contract enums** rather than inventing new
  status vocabularies. Freshness and completeness status strings are validated
  against ``data/source-refresh-acceptance-contract.json``.
* **Light import.** This module imports only the stdlib so it can be imported
  and tested without the heavy ``worldenergydata`` root ``__init__``.

#450 (workflow-run manifest) is a light dependency. As of this slice the #450
manifest contract is **not present** in the repo, so we define a minimal,
self-contained interface here:

* :class:`SourceReadiness` - per-source readiness record, JSON-serialisable.
* :class:`ReadinessReport` - overall go/no-go plus per-source records and a
  ``well_operation_entities`` map; :meth:`ReadinessReport.to_manifest_fragment`
  emits the dict a #450 manifest can embed under ``source_readiness``.

When #450 lands, replace ``to_manifest_fragment`` with the real contract
serialisation; the field names here are chosen to map cleanly onto the #462
contract row fields (``freshness_status``, ``completeness_status``,
``data_location``, ``blocker_issue``, ...).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

# --------------------------------------------------------------------------- #
# #462 acceptance-contract enums (reused, not reinvented).
# These mirror data/source-refresh-acceptance-contract.json. We keep a literal
# fallback so the probe still works when the contract file is absent, but when
# it is present we cross-check the values against it.
# --------------------------------------------------------------------------- #

FRESHNESS_STATUS_VALUES = (
    "fresh",
    "stale",
    "missing",
    "blocked",
    "unknown",
    "reference_data",
    "not_applicable",
)
COMPLETENESS_STATUS_VALUES = (
    "full",
    "sample",
    "empty",
    "missing",
    "runtime_fetched",
    "reference_data",
    "blocked",
    "unknown",
    "not_applicable",
)

# Default location of the #462 contract relative to the repo root.
DEFAULT_CONTRACT_RELPATH = "data/source-refresh-acceptance-contract.json"

# A file at or below this size is treated as a stub / placeholder rather than
# real data (e.g. a 0-byte LFS pointer or an empty export).
DEFAULT_STUB_MAX_BYTES = 1


def load_contract_enums(contract_path: Optional[Path]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return ``(freshness_values, completeness_values)`` from the #462 contract.

    Falls back to the module-level literals when the contract file is missing
    or unreadable. Read-only: only opens the file for reading.
    """
    if contract_path is not None and contract_path.is_file():
        try:
            data = json.loads(contract_path.read_text())
        except (ValueError, OSError):
            return FRESHNESS_STATUS_VALUES, COMPLETENESS_STATUS_VALUES
        fresh = tuple(data.get("freshness_status_values") or FRESHNESS_STATUS_VALUES)
        comp = tuple(data.get("completeness_status_values") or COMPLETENESS_STATUS_VALUES)
        return fresh, comp
    return FRESHNESS_STATUS_VALUES, COMPLETENESS_STATUS_VALUES


# --------------------------------------------------------------------------- #
# Requirement + result data model (minimal #450-manifest interface).
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RequiredSource:
    """One source a well-operations run needs.

    Attributes:
        module_id: Canonical #462 module id (e.g. ``"bsee"``, ``"fdas"``).
        data_location: Directory (relative to ``repo_root``) holding the data.
        required_paths: Files (relative to ``data_location``) that must be
            present and non-stub for the source to be ``available``. If empty,
            the probe treats *any* non-stub file under ``data_location`` as
            satisfying presence.
        ttl_days: Freshness window. A present source whose newest required file
            is older than this is ``stale``. ``None`` means freshness is not
            enforced (treated as ``reference_data`` when present).
        well_operation_entities: Well-ops entities this source feeds (well,
            borehole, lease, field, operator, completion, production_interval,
            activity). Surfaced in the report for #451 entity mapping.
        blocker_issue: Open ingest/refresh issue blocking this source, or
            ``None``. A blocker forces ``freshness_status="blocked"`` and a
            no-go contribution regardless of files on disk.
        stub_max_bytes: Files at or below this size count as stubs.
    """

    module_id: str
    data_location: str
    required_paths: Sequence[str] = field(default_factory=tuple)
    ttl_days: Optional[float] = None
    well_operation_entities: Sequence[str] = field(default_factory=tuple)
    blocker_issue: Optional[str] = None
    stub_max_bytes: int = DEFAULT_STUB_MAX_BYTES


@dataclass
class SourceReadiness:
    """Per-source readiness outcome. JSON-serialisable via :meth:`to_dict`."""

    module_id: str
    data_location: str
    state: str  # "available" | "stale" | "missing" | "blocked"
    freshness_status: str  # #462 freshness enum
    completeness_status: str  # #462 completeness enum
    is_go: bool
    well_operation_entities: tuple[str, ...]
    blocker_issue: Optional[str]
    newest_mtime_iso: Optional[str]
    age_days: Optional[float]
    present_paths: tuple[str, ...]
    missing_paths: tuple[str, ...]
    stub_paths: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "data_location": self.data_location,
            "state": self.state,
            "freshness_status": self.freshness_status,
            "completeness_status": self.completeness_status,
            "is_go": self.is_go,
            "well_operation_entities": list(self.well_operation_entities),
            "blocker_issue": self.blocker_issue,
            "newest_mtime_iso": self.newest_mtime_iso,
            "age_days": self.age_days,
            "present_paths": list(self.present_paths),
            "missing_paths": list(self.missing_paths),
            "stub_paths": list(self.stub_paths),
            "reason": self.reason,
        }


@dataclass
class ReadinessReport:
    """Overall readiness for a well-operations run."""

    overall_go: bool
    sources: list[SourceReadiness]
    generated_at_iso: str

    @property
    def well_operation_entities(self) -> dict[str, list[str]]:
        """Map well-ops entity -> module_ids that can currently supply it.

        Only ``available`` (go) sources contribute, so this answers
        "which entities can this run populate today".
        """
        mapping: dict[str, list[str]] = {}
        for src in self.sources:
            if not src.is_go:
                continue
            for entity in src.well_operation_entities:
                mapping.setdefault(entity, []).append(src.module_id)
        return mapping

    @property
    def blocking_sources(self) -> list[str]:
        return [s.module_id for s in self.sources if not s.is_go]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_go": self.overall_go,
            "generated_at": self.generated_at_iso,
            "sources": [s.to_dict() for s in self.sources],
            "well_operation_entities": self.well_operation_entities,
            "blocking_sources": self.blocking_sources,
        }

    def to_manifest_fragment(self) -> dict[str, Any]:
        """Emit the dict a #450 workflow-run manifest embeds.

        #450's contract is not yet in the repo; this is the minimal,
        self-contained shape it can consume under a ``source_readiness`` key.
        """
        return {"source_readiness": self.to_dict()}


# --------------------------------------------------------------------------- #
# The probe.
# --------------------------------------------------------------------------- #


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _candidate_files(base: Path) -> list[Path]:
    return [p for p in base.rglob("*") if p.is_file()]


def probe_source(
    req: RequiredSource,
    repo_root: Path,
    *,
    now: Optional[float] = None,
) -> SourceReadiness:
    """Probe one required source. Pure read-only over the local FS."""
    now = time.time() if now is None else now
    base = (repo_root / req.data_location).resolve()
    entities = tuple(req.well_operation_entities)

    # 1) Hard blocker from a pending ingest/refresh issue wins outright.
    if req.blocker_issue:
        return SourceReadiness(
            module_id=req.module_id,
            data_location=req.data_location,
            state="blocked",
            freshness_status="blocked",
            completeness_status="blocked",
            is_go=False,
            well_operation_entities=entities,
            blocker_issue=req.blocker_issue,
            newest_mtime_iso=None,
            age_days=None,
            present_paths=(),
            missing_paths=tuple(req.required_paths),
            stub_paths=(),
            reason=f"blocked by issue {req.blocker_issue}",
        )

    # 2) Resolve the set of files to evaluate.
    present: list[str] = []
    missing: list[str] = []
    stub: list[str] = []
    real_files: list[Path] = []

    if req.required_paths:
        for rel in req.required_paths:
            fp = base / rel
            if not fp.is_file():
                missing.append(rel)
                continue
            if fp.stat().st_size <= req.stub_max_bytes:
                stub.append(rel)
                continue
            present.append(rel)
            real_files.append(fp)
    else:
        # No explicit file list: any non-stub file under the dir counts.
        if base.is_dir():
            for fp in _candidate_files(base):
                rel = str(fp.relative_to(base))
                if fp.stat().st_size <= req.stub_max_bytes:
                    stub.append(rel)
                else:
                    present.append(rel)
                    real_files.append(fp)
        if not real_files and not stub:
            missing.append("<any file>")

    # 3) MISSING: nothing real present.
    if not real_files:
        # Distinguish "files exist but are stubs" (still missing/empty data)
        # from "nothing on disk".
        comp = "empty" if stub else "missing"
        reason = (
            "required files present but stub-sized"
            if stub
            else "no data files present"
        )
        return SourceReadiness(
            module_id=req.module_id,
            data_location=req.data_location,
            state="missing",
            freshness_status="missing",
            completeness_status=comp,
            is_go=False,
            well_operation_entities=entities,
            blocker_issue=None,
            newest_mtime_iso=None,
            age_days=None,
            present_paths=tuple(present),
            missing_paths=tuple(missing),
            stub_paths=tuple(stub),
            reason=reason,
        )

    # 4) Present: compute freshness from newest real file mtime.
    newest_mtime = max(fp.stat().st_mtime for fp in real_files)
    age_days = (now - newest_mtime) / 86400.0
    newest_iso = _iso(newest_mtime)

    # A missing *required* member means partial data -> sample completeness.
    completeness = "sample" if missing else "full"

    if req.ttl_days is None:
        # Freshness not enforced: treat present data as reference_data (fresh
        # enough by definition) but still GO.
        return SourceReadiness(
            module_id=req.module_id,
            data_location=req.data_location,
            state="available",
            freshness_status="reference_data",
            completeness_status=completeness,
            is_go=True,
            well_operation_entities=entities,
            blocker_issue=None,
            newest_mtime_iso=newest_iso,
            age_days=round(age_days, 4),
            present_paths=tuple(present),
            missing_paths=tuple(missing),
            stub_paths=tuple(stub),
            reason="present; freshness not enforced (ttl_days=None)",
        )

    if age_days > req.ttl_days:
        return SourceReadiness(
            module_id=req.module_id,
            data_location=req.data_location,
            state="stale",
            freshness_status="stale",
            completeness_status=completeness,
            is_go=False,
            well_operation_entities=entities,
            blocker_issue=None,
            newest_mtime_iso=newest_iso,
            age_days=round(age_days, 4),
            present_paths=tuple(present),
            missing_paths=tuple(missing),
            stub_paths=tuple(stub),
            reason=f"newest file {age_days:.2f}d old > ttl {req.ttl_days}d",
        )

    return SourceReadiness(
        module_id=req.module_id,
        data_location=req.data_location,
        state="available",
        freshness_status="fresh",
        completeness_status=completeness,
        is_go=True,
        well_operation_entities=entities,
        blocker_issue=None,
        newest_mtime_iso=newest_iso,
        age_days=round(age_days, 4),
        present_paths=tuple(present),
        missing_paths=tuple(missing),
        stub_paths=tuple(stub),
        reason=f"present and fresh ({age_days:.2f}d <= ttl {req.ttl_days}d)",
    )


def probe_readiness(
    required_sources: Iterable[RequiredSource],
    repo_root: Path,
    *,
    now: Optional[float] = None,
    contract_path: Optional[Path] = None,
    validate_enums: bool = True,
) -> ReadinessReport:
    """Probe every required source and build an overall go/no-go report.

    Read-only. ``overall_go`` is True only when *every* required source is
    GO (available). The probe optionally cross-checks the status strings it
    emits against the #462 contract enums.
    """
    now = time.time() if now is None else now
    if contract_path is None:
        candidate = repo_root / DEFAULT_CONTRACT_RELPATH
        contract_path = candidate if candidate.is_file() else None

    results = [probe_source(req, repo_root, now=now) for req in required_sources]

    if validate_enums:
        fresh_vals, comp_vals = load_contract_enums(contract_path)
        for r in results:
            if r.freshness_status not in fresh_vals:
                raise ValueError(
                    f"{r.module_id}: freshness_status {r.freshness_status!r} "
                    f"not in #462 contract enum {fresh_vals}"
                )
            if r.completeness_status not in comp_vals:
                raise ValueError(
                    f"{r.module_id}: completeness_status {r.completeness_status!r} "
                    f"not in #462 contract enum {comp_vals}"
                )

    overall_go = bool(results) and all(r.is_go for r in results)
    return ReadinessReport(
        overall_go=overall_go,
        sources=results,
        generated_at_iso=_iso(now),
    )


# --------------------------------------------------------------------------- #
# Default well-operations requirement set (BSEE + FDAS).
# Entity names follow #451's well-operation entity list.
# --------------------------------------------------------------------------- #


def default_well_operations_sources(
    *,
    bsee_ttl_days: float = 30.0,
    fdas_ttl_days: float = 60.0,
    bsee_blocker: Optional[str] = None,
    fdas_blocker: Optional[str] = None,
) -> list[RequiredSource]:
    """Required BSEE/FDAS sources for a well-operations run.

    Paths are relative to repo root and match the local layout
    (``data/modules/bsee``, ``data/modules/fdas``). Callers may override TTLs
    or inject a known blocker issue (e.g. BSEE #267).
    """
    return [
        RequiredSource(
            module_id="bsee",
            data_location="data/modules/bsee/current/operations",
            required_paths=("well_activity_summary.csv",),
            ttl_days=bsee_ttl_days,
            well_operation_entities=(
                "well",
                "borehole",
                "lease",
                "field",
                "operator",
                "completion",
                "activity",
            ),
            blocker_issue=bsee_blocker,
        ),
        RequiredSource(
            module_id="fdas",
            data_location="data/modules/fdas/enhanced/wells",
            required_paths=("well_data_enhanced.csv",),
            ttl_days=fdas_ttl_days,
            well_operation_entities=(
                "well",
                "borehole",
                "production_interval",
            ),
            blocker_issue=fdas_blocker,
        ),
    ]
