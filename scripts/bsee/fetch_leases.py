#!/usr/bin/env python3
"""Fetch or curate the public BSEE lease snapshot; raw storage is caller-owned."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

from worldenergydata.bsee.lease_fetch import fetch_bundle
from worldenergydata.bsee.lease_ingest import (
    curate,
    load_table,
    poster_leases,
    registry_check,
)
from worldenergydata.common.fields_registry import load_fields


def write_json(path: Path, value: Any) -> dict[str, Any]:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    if json.loads(path.read_text()) != value:
        raise OSError("Derived JSON readback mismatch")
    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def saved_tables(raw_dir: Path, output: Path, schema: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads((output / "source_manifest.json").read_text())
    expected = {record["file"]: record for record in manifest["files"]}
    tables = {}
    for kind, spec in schema["tables"].items():
        path = raw_dir / spec["archive"]
        record = expected[path.name]
        if (
            hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]
            or path.stat().st_size != record["size_bytes"]
        ):
            raise ValueError("Saved package does not match source manifest")
        tables[kind] = load_table(path, spec)
    return tables


def save_extract(
    output: Path,
    schema_path: Path,
    tables: dict[str, Any],
    leases: list[str],
    result: dict[str, Any],
) -> None:
    artifacts = [
        write_json(output / f"{name}.json", rows) for name, rows in result.items()
    ]
    artifacts.append(
        {
            "file": "source_schema.json",
            "sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
            "size_bytes": schema_path.stat().st_size,
        }
    )
    summary = {
        "source_row_counts": {kind: len(rows) for kind, rows in tables.items()},
        "target_leases": len(leases),
        "leases_ingested": len(result["leases"]),
        "registry_resolved": sum(
            row["field_id"] is not None for row in result["registry"]
        ),
        "unresolved": [row for row in result["registry"] if row["reason"]],
        "source_missing": result["missing"],
        "artifacts": artifacts,
        "source_manifest_sha256": hashlib.sha256(
            (output / "source_manifest.json").read_bytes()
        ).hexdigest(),
    }
    write_json(output / "extract_manifest.json", summary)
    print(
        json.dumps({key: value for key, value in summary.items() if key != "artifacts"})
    )


def prepare_schema(output: Path) -> tuple[Path, dict[str, Any]]:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "data/modules/bsee/leases/source_schema.json"
    )
    schema = json.loads(schema_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    target_schema = output / "source_schema.json"
    if schema_path.resolve() != target_schema.resolve():
        shutil.copyfile(schema_path, target_schema)
        if target_schema.read_bytes() != schema_path.read_bytes():
            raise OSError("Schema copy readback mismatch")
    schema_path = target_schema
    return schema_path, schema


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path, default=os.environ.get("BSEE_LEASE_RAW_DIR")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/modules/bsee/leases")
    )
    parser.add_argument("--registry", type=Path, default=Path("config/fields.yml"))
    parser.add_argument(
        "--from-saved",
        action="store_true",
        help="Curate verified saved packages offline",
    )
    args = parser.parse_args()
    if args.raw_dir is None:
        parser.error("Set BSEE_LEASE_RAW_DIR or --raw-dir to external data storage")
    output = args.output_dir
    schema_path, schema = prepare_schema(output)
    if not args.from_saved:
        records = fetch_bundle(schema, args.raw_dir)
        write_json(
            output / "source_manifest.json",
            {
                "source_id": "bsee-data-center",
                "owner_repo": "worldenergydata",
                "files": records,
            },
        )
    tables = saved_tables(args.raw_dir, output, schema)
    registry = load_fields(args.registry)
    leases = poster_leases(registry)
    result = curate(tables, leases)
    result["registry"] = registry_check(leases, registry)
    save_extract(output, schema_path, tables, leases, result)


if __name__ == "__main__":
    main()
