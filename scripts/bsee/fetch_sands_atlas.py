#!/usr/bin/env python3
"""Fetch/export the 2023 Atlas or derive roster candidates from retained exports."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from worldenergydata.bsee.atlas import attribute_fields, load_atlas
from worldenergydata.bsee.atlas_fetch import fetch_atlas
from worldenergydata.common.fields_registry import load_fields


def verify_retained_files(directory: Path, manifest: dict) -> None:
    records = manifest.get("files", [])
    names = [record.get("file") for record in records]
    if any(
        not isinstance(name, str)
        or not name
        or "/" in name
        or "\\" in name
        or name in (".", "..")
        for name in names
    ):
        raise ValueError("manifest files must be safe basenames")
    if len(set(names)) != len(names):
        raise ValueError("manifest contains duplicate file records")
    if not {"2023sands.csv", "2023plays.csv", "2023chronozones.csv"}.issubset(names):
        raise ValueError("manifest must pin every consumed table")
    for record in records:
        path = directory / record["file"]
        if (
            path.stat().st_size != record["size_bytes"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]
        ):
            raise ValueError("retained source digest/size differs from manifest")


def parse_args(root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.environ.get("BSEE_ATLAS_DATA_DIR"))
    parser.add_argument(
        "--reuse", action="store_true", help="offline: use retained CSV exports"
    )
    parser.add_argument("--mdb-export", default="mdb-export")
    parser.add_argument(
        "--output", type=Path, default=root / "data/modules/bsee/atlas/2023"
    )
    args = parser.parse_args()
    if not args.data_dir:
        parser.error(
            "set BSEE_ATLAS_DATA_DIR or --data-dir to an external data directory"
        )
    directory = Path(args.data_dir).resolve()
    if directory.is_relative_to(root):
        parser.error("raw data directory must be outside the repository")
    return args


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    args = parse_args(root)
    directory = Path(args.data_dir).resolve()
    schema = root / "data/modules/bsee/atlas/2023/schema.json"
    manifest = (
        json.loads((directory / "manifest.json").read_text())
        if args.reuse
        else fetch_atlas(directory, schema, args.mdb_export)
    )
    verify_retained_files(directory, manifest)
    roster_path = root / "reports/field-atlas/_roster.json"
    registry_path = root / "config/fields.yml"
    results = attribute_fields(
        load_atlas(directory, schema),
        json.loads(roster_path.read_text()),
        load_fields(registry_path),
    )
    output = {
        "edition": 2023,
        "manifest": "manifest.json",
        "criteria_version": 1,
        "input_sha256": {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (roster_path, registry_path, schema)
        },
        "counts": {
            status: sum(r["status"] == status for r in results)
            for status in ("attributed", "ambiguous", "unmatched")
        },
        "fields": results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (args.output / "field_attribution.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(json.dumps({"null_play_fields": len(results), "counts": output["counts"]}))


if __name__ == "__main__":
    main()
