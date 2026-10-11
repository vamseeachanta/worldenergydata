#!/usr/bin/env python3
"""Fetch/export the 2023 Atlas or derive roster candidates from retained exports."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

from worldenergydata.bsee.atlas import (
    attribute_fields,
    load_atlas,
    public_xref_evidence,
)
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


def manifest_differences(committed: dict, run: dict) -> list[str]:
    """Compare observed source identity and content, ignoring retrieval times."""
    differences = []
    expected = {record["file"]: record for record in committed.get("files", [])}
    actual = {record["file"]: record for record in run.get("files", [])}
    if set(expected) != set(actual):
        differences.append(
            f"file set: missing={sorted(set(expected) - set(actual))}; "
            f"added={sorted(set(actual) - set(expected))}"
        )
    for name in sorted(set(expected) & set(actual)):
        for key in ("source_url", "sha256", "size_bytes"):
            if expected[name].get(key) != actual[name].get(key):
                differences.append(
                    f"{name} {key}: committed={expected[name].get(key)!r}; "
                    f"run={actual[name].get(key)!r}"
                )
    if committed.get("row_counts") != run.get("row_counts"):
        differences.append(
            f"row_counts: committed={committed.get('row_counts')!r}; "
            f"run={run.get('row_counts')!r}"
        )
    return differences


def check_or_update_manifest(path: Path, manifest: dict, update: bool) -> None:
    """Only an explicit update will replace the committed provenance."""
    if update:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        return
    if not path.exists():
        print("manifest difference: committed manifest is missing")
        raise SystemExit(1)
    differences = manifest_differences(json.loads(path.read_text()), manifest)
    for difference in differences:
        print(f"manifest difference: {difference}")
    if differences:
        raise SystemExit(1)
    print("manifest stable fields match")


def parse_args(root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.environ.get("BSEE_ATLAS_DATA_DIR"))
    parser.add_argument(
        "--reuse", action="store_true", help="offline: use retained CSV exports"
    )
    parser.add_argument("--mdb-export", default="mdb-export")
    parser.add_argument(
        "--update-manifest",
        action="store_true",
        help="explicitly replace the committed manifest with this run's manifest",
    )
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
    check_or_update_manifest(
        args.output / "manifest.json", manifest, args.update_manifest
    )
    roster_path = root / "reports/field-atlas/_roster.json"
    registry_path = root / "config/fields.yml"
    registry = load_fields(registry_path)
    xref_path = directory / "2023xref_oper-comp.csv"
    codes, public_rows = {}, []
    if xref_path.exists():
        if "2023xref_oper-comp.csv" not in {r["file"] for r in manifest["files"]}:
            raise ValueError("manifest must pin consumed public identity table")
        with xref_path.open(newline="", encoding="utf-8-sig") as stream:
            codes, public_rows = public_xref_evidence(
                list(csv.DictReader(stream)), registry
            )
    results = attribute_fields(
        load_atlas(directory, schema),
        json.loads(roster_path.read_text()),
        registry,
        codes,
        public_rows,
    )
    output = attribution_output(root, roster_path, registry_path, schema, results)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "field_attribution.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(json.dumps({"null_play_fields": len(results), "counts": output["counts"]}))


def attribution_output(
    root: Path,
    roster_path: Path,
    registry_path: Path,
    schema: Path,
    results: list[dict],
) -> dict:
    output = {
        "edition": 2023,
        "manifest": "manifest.json",
        "criteria_version": 2,
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
    return output


if __name__ == "__main__":
    main()
