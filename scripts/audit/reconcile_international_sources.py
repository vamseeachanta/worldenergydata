"""Compare international implementation evidence, refresh metadata and local storage.

Issue #917 (2026): implementation completion is independent of materialization.
Only explicitly enumerated paths are inspected; no country client is imported.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def _relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Evidence paths must be nonempty relative paths")
    return path


def _materialization(data_root: Path | None, relative: Path) -> str:
    if data_root is None:
        return "NOT_EVALUATED"
    try:
        if data_root.is_symlink() or not data_root.is_dir():
            return "NOT_EVALUATED"
        target = data_root
        for part in relative.parts:
            target = target / part
            if target.is_symlink():
                return "unavailable"
        # stat rather than exists keeps permission errors distinct from absence.
        try:
            target.stat()
        except FileNotFoundError:
            return "not_observed"
        if not target.is_dir():
            return "unavailable"
        manifest = target / "manifest.json"
        if manifest.is_symlink():
            return "unavailable"
        return "manifest_present" if manifest.is_file() else "directory_only"
    except OSError:
        return "unavailable"


def reconcile(project_root: Path, data_root: Path | None = None) -> dict[str, Any]:
    """Return a read-only comparison, without treating presence as acceptance.

    The issue-state register is dated evidence, not a live GitHub query. A caller
    must supply an accessible data root to make storage observations. Paths in
    the result remain relative, including when the caller uses external storage.
    """
    register = json.loads(
        (project_root / "data/international-source-reconciliation.json").read_text()
    )
    contract = json.loads(
        (project_root / "data/source-refresh-acceptance-contract.json").read_text()
    )
    config = yaml.safe_load(
        (project_root / "config/scheduler/scheduler_config.yml").read_text()
    )
    jobs = {job["name"]: job for job in config.get("jobs", [])}
    contract_rows = {row["module_id"]: row for row in contract["sources"]}
    rows = []
    for source in register["sources"]:
        module_id = source["module_id"]
        data_path = _relative_path(source["data_path"])
        evidence_paths = [_relative_path(p) for p in source["capability_evidence"]]
        evidence_present = bool(evidence_paths) and all(
            (project_root / path).is_file() for path in evidence_paths
        )
        findings = []
        if not evidence_present:
            findings.append("missing_capability_evidence")
        job_name = source["scheduler_job"]
        job = jobs.get(job_name)
        row = contract_rows.get(module_id)
        if job_name:
            if job is None:
                findings.append("missing_scheduler_job")
            elif job.get("output_dir") != (Path("data") / data_path).as_posix():
                findings.append("scheduler_output_mismatch")
            if row is None:
                findings.append("missing_contract_source")
        if row is not None:
            if (row["scheduler_job"] or "none") != (job_name or "none"):
                findings.append("contract_scheduler_mismatch")
            if row["data_location"] != (Path("data") / data_path).as_posix():
                findings.append("contract_data_location_mismatch")
            if job is not None and row["scheduler_output_dir"] != job.get("output_dir"):
                findings.append("contract_output_mismatch")
            blocker = row["blocker_issue"]
            if register["issue_states"].get(blocker) == "CLOSED":
                findings.append(f"closed_blocker:{blocker}")
        rows.append(
            {
                "module_id": module_id,
                "capability_evidence_present": evidence_present,
                "implementation_issues": source["implementation_issues"],
                "contract_status": "listed" if row is not None else "not_listed",
                "freshness_status": row["freshness_status"] if row else None,
                "scheduler_job": job_name,
                "scheduler_enabled": job.get("enabled", False) if job else None,
                "data_path": data_path.as_posix(),
                "materialization_status": _materialization(data_root, data_path),
                "findings": findings,
            }
        )
    return {"issue_states_observed_on": register["observed_on"], "sources": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--data-root", type=Path, help="Explicit data root; no download"
    )
    args = parser.parse_args(argv)
    try:
        report = reconcile(args.project_root, args.data_root)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        parser.exit(
            status=1, message="Reconciliation inputs are unavailable or invalid\n"
        )
    print(json.dumps(report, indent=2))
    return int(any(row["findings"] for row in report["sources"]))


if __name__ == "__main__":
    raise SystemExit(main())
