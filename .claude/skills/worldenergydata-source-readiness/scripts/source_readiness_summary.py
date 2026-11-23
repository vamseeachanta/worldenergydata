#!/usr/bin/env python3
"""Print worldenergydata source readiness and data-location summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[4]


def newest_modified(metadata: dict[str, Any]) -> str:
    values = [
        item.get("modified")
        for item in metadata.get("files", [])
        if isinstance(item, dict) and item.get("modified")
    ]
    return max(values) if values else ""


def scheduler_outputs(config: dict[str, Any]) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for job in config.get("jobs", []) or []:
        output_dir = job.get("output_dir")
        name = job.get("name", "")
        if not output_dir or not name.endswith("_refresh"):
            continue
        module = name[: -len("_refresh")]
        outputs[module] = output_dir
    return outputs


def latest_known_date(entry: dict[str, Any], metadata: dict[str, Any]) -> tuple[str, str]:
    scheduler_success = entry.get("scheduler_last_success_ts") or ""
    if scheduler_success:
        return scheduler_success, "scheduler_success"
    last_refresh = entry.get("last_refresh") or metadata.get("last_refresh") or ""
    if last_refresh:
        return last_refresh, "metadata_refresh"
    newest = newest_modified(metadata)
    if newest:
        return newest, "newest_file_modified"
    return "", ""


def build_rows(repo_root: Path) -> list[dict[str, Any]]:
    scorecard = load_json(repo_root / "data" / "freshness-scorecard.json")
    modules = scorecard.get("modules", {})
    scheduler_map = scheduler_outputs(
        load_yaml(repo_root / "config" / "scheduler" / "scheduler_config.yml")
    )

    rows: list[dict[str, Any]] = []
    for module, entry in sorted(modules.items()):
        module_dir = repo_root / "data" / "modules" / module
        metadata = load_json(module_dir / "_metadata.json")
        manifest = load_json(module_dir / "manifest.json")
        entry = dict(entry)
        if manifest and not entry.get("scheduler_last_success_ts"):
            entry["scheduler_last_success_ts"] = manifest.get("last_success_ts")
        latest, basis = latest_known_date(entry, metadata)
        rows.append(
            {
                "module": module,
                "catalog_status": entry.get("catalog_status", ""),
                "freshness_status": entry.get("freshness_status", ""),
                "latest_known_date": latest,
                "latest_date_basis": basis,
                "data_location": str(Path("data") / "modules" / module),
                "external_data_root": metadata.get("external_data_root") or "",
                "scheduler_output_dir": scheduler_map.get(module, ""),
                "datasets": entry.get("dataset_count", 0),
                "records": entry.get("record_count", metadata.get("record_count", 0)),
                "files": metadata.get("file_count", ""),
                "size": metadata.get("total_size_human", ""),
                "scheduler_last_success": entry.get("scheduler_last_success_ts") or "",
            }
        )
    return rows


def markdown(rows: list[dict[str, Any]]) -> str:
    headers = [
        "Module",
        "Status",
        "Freshness",
        "Latest Known Date",
        "Basis",
        "Data Location",
        "External Location",
        "Scheduler Output",
        "Datasets",
        "Records",
        "Files",
        "Size",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|---|---|---|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        values = [
            row["module"],
            row["catalog_status"],
            row["freshness_status"],
            row["latest_known_date"],
            row["latest_date_basis"],
            row["data_location"],
            row["external_data_root"],
            row["scheduler_output_dir"],
            str(row["datasets"]),
            str(row["records"]),
            str(row["files"]),
            row["size"],
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root_from_script())
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()

    rows = build_rows(args.repo_root.resolve())
    if args.format == "json":
        print(json.dumps(rows, indent=2))
    else:
        print(markdown(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
