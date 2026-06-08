#!/usr/bin/env python3
"""Build a module-level data freshness scorecard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _module_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("modules", []):
        module_id = entry.get("id")
        if module_id:
            records[module_id] = entry
    return records


def _catalog_modules(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    modules = catalog.get("modules", {})
    return modules if isinstance(modules, dict) else {}


def _freshness_status(
    catalog_status: str,
    dataset_count: int,
    metadata: dict[str, Any],
    scheduler_manifest: dict[str, Any],
    report_date: str,
) -> str:
    if scheduler_manifest:
        last_success = _parse_datetime(scheduler_manifest.get("last_success_ts"))
        interval_days = int(scheduler_manifest.get("refresh_interval_days") or 7)
        report_dt = _parse_datetime(f"{report_date}T00:00:00+00:00")
        if last_success and report_dt:
            age_days = (report_dt - last_success).days
            return "fresh" if age_days <= interval_days else "stale"
        return "unknown"

    if catalog_status == "empty":
        return "empty"
    if catalog_status == "sample":
        return "sample"
    if dataset_count == 0 and not metadata:
        return "missing"
    if catalog_status in {"runtime_fetched", "unknown"}:
        return "unknown"
    return catalog_status or "unknown"


def build_scorecard(project_root: Path, report_date: str | None = None) -> dict[str, Any]:
    """Build a module-keyed freshness scorecard from local catalog artifacts."""
    report_date = report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    module_manifest = _module_records(_load_yaml(project_root / "module-manifest.yaml"))
    catalog_modules = _catalog_modules(_load_yaml(project_root / "data" / "catalog.yaml"))
    module_ids = sorted(set(module_manifest) | set(catalog_modules))

    modules: dict[str, dict[str, Any]] = {}
    for module_id in module_ids:
        manifest_entry = module_manifest.get(module_id, {})
        catalog_entry = catalog_modules.get(module_id, {})
        module_dir = project_root / "data" / "modules" / module_id
        metadata = _load_json(module_dir / "_metadata.json")
        scheduler_manifest = _load_json(module_dir / "manifest.json")
        datasets = catalog_entry.get("datasets", []) or []
        dataset_count = len(datasets)
        record_count = metadata.get("record_count")
        if record_count is None:
            record_count = sum(int(ds.get("row_count") or 0) for ds in datasets)
        catalog_status = manifest_entry.get("catalog_status", "unknown")

        modules[module_id] = {
            "module": module_id,
            "catalog_status": catalog_status,
            "freshness_status": _freshness_status(
                catalog_status,
                dataset_count,
                metadata,
                scheduler_manifest,
                report_date,
            ),
            "in_scheduler": bool(manifest_entry.get("in_scheduler", False)),
            "public_cli": bool(manifest_entry.get("public_cli", False)),
            "dataset_count": dataset_count,
            "record_count": record_count,
            "last_refresh": metadata.get("last_refresh"),
            "scheduler_last_success_ts": scheduler_manifest.get("last_success_ts"),
            "refresh_interval_days": scheduler_manifest.get("refresh_interval_days"),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_date": report_date,
        "module_count": len(modules),
        "modules": modules,
    }


def write_markdown(scorecard: dict[str, Any], output_path: Path) -> None:
    """Write a Markdown scorecard report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Data Freshness Scorecard — {scorecard['report_date']}",
        "",
        "| Module | Catalog Status | Freshness | Datasets | Records | Last Refresh | Scheduler Success |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for module_id, entry in sorted(scorecard["modules"].items()):
        lines.append(
            "| {module} | {catalog_status} | {freshness_status} | {dataset_count} | "
            "{record_count} | {last_refresh} | {scheduler_last_success_ts} |".format(
                module=module_id,
                catalog_status=entry["catalog_status"],
                freshness_status=entry["freshness_status"],
                dataset_count=entry["dataset_count"],
                record_count=entry["record_count"],
                last_refresh=entry.get("last_refresh") or "",
                scheduler_last_success_ts=entry.get("scheduler_last_success_ts") or "",
            )
        )
    output_path.write_text("\n".join(lines) + "\n")


def _default_report_path(project_root: Path, report_date: str) -> Path:
    return project_root / "docs" / "reports" / f"data-freshness-scorecard-{report_date}.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--report-output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--max-unknown", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_root = args.project_root.resolve()
    scorecard = build_scorecard(project_root, report_date=args.date)

    json_output = args.json_output or project_root / "data" / "freshness-scorecard.json"
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(scorecard, indent=2) + "\n")

    report_output = args.report_output or _default_report_path(project_root, args.date)
    write_markdown(scorecard, report_output)

    if args.check:
        unknown_count = sum(
            1
            for entry in scorecard["modules"].values()
            if entry["freshness_status"] == "unknown"
        )
        if unknown_count > args.max_unknown:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
