#!/usr/bin/env python3
"""Fetch or verify a retained public source, then curate lease-attributed counts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from worldenergydata.bsee.borehole_status import (
    LAYOUT_URL,
    STATUS_URL,
    aggregate_status,
    source_schema,
)
from worldenergydata.bsee.borehole_status_fetch import (
    SOURCE_URL,
    TERMS_URL,
    fetch_file,
    load_archive,
)
from worldenergydata.common.fields_registry import load_fields

SOURCES = (
    ("5010delimit.zip", SOURCE_URL),
    ("borehole_layout.html", LAYOUT_URL),
    ("borehole_codes.html", STATUS_URL),
    ("disclaimer.html", TERMS_URL),
)


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    if json.loads(path.read_text(encoding="utf-8")) != value:
        raise OSError("Generated JSON readback differs")


def file_digest(path: Path, storage: str) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "file": path.name,
        "storage": storage,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def obtain_source(raw_dir: Path, reuse: bool) -> dict[str, Any]:
    manifest_path = raw_dir / "source_manifest.json"
    manifest: dict[str, Any]
    if reuse:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        raw_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "source_id": "bsee-data-center",
            "owner": "worldenergydata",
            "files": [],
        }
        try:
            for name, url in SOURCES:
                manifest["files"].append(fetch_file(url, raw_dir / name))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
            manifest["failure"] = {"type": type(error).__name__}
            if isinstance(error, HTTPError):
                manifest["refusal"] = {
                    "http_status": error.code,
                    "source_url": error.url,
                }
            write_json(manifest_path, manifest)
            raise
        write_json(manifest_path, manifest)
    verify_provenance(raw_dir, manifest)
    return manifest


def verify_provenance(raw_dir: Path, manifest: dict[str, Any]) -> None:
    names = [record["file"] for record in manifest["files"]]
    if (
        "failure" in manifest
        or "refusal" in manifest
        or len(names) != len(SOURCES)
        or set(names) != set(dict(SOURCES))
    ):
        raise ValueError(
            "Incomplete or failed source provenance; choose a new source snapshot"
        )
    known = dict(SOURCES)
    for record in manifest["files"]:
        name = record["file"]
        if name not in known or record["source_url"] != known[name]:
            raise ValueError("Unrecognized source identity")
        raw = (raw_dir / name).read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != record["sha256"]
            or len(raw) != record["size_bytes"]
        ):
            raise ValueError("Source digest/size mismatch")
    if not any(r["file"] == "5010delimit.zip" for r in manifest["files"]):
        raise ValueError("Missing borehole source provenance")


def write_unmatched(raw_dir: Path, records: list[dict[str, Any]]) -> Path:
    path = raw_dir / "unmatched.csv"
    columns = [
        "api12",
        "bottom_lease",
        "surface_lease",
        "field_id",
        "status_code",
        "status_date",
        "status_meaning",
        "reason",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    expected = buffer.getvalue().encode("utf-8")
    if path.exists():
        if path.read_bytes() != expected:
            raise ValueError(
                "Retained unmatched output differs; choose a new raw directory"
            )
    else:
        with path.open("xb") as stream:
            stream.write(expected)
    with path.open(newline="", encoding="utf-8") as stream:
        if sum(1 for _ in csv.DictReader(stream)) != len(records):
            raise OSError("Unmatched CSV readback count differs")
    return path


def unmatched_groups(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = Counter((r["reason"], r["bottom_lease"]) for r in records)
    return [
        {"reason": reason, "bottom_lease": lease, "borehole_count": count}
        for (reason, lease), count in sorted(grouped.items())
    ]


def write_snapshot(
    raw_dir: Path, output: Path, registry_path: Path, provenance: dict[str, Any]
) -> dict[str, Any]:
    registry_bytes = registry_path.read_bytes()
    result = aggregate_status(
        load_archive(raw_dir / "5010delimit.zip"), load_fields(registry_path)
    )
    attributed, unmatched = result.pop("attributed"), result.pop("unmatched")
    source_record = next(
        r for r in provenance["files"] if r["file"] == "5010delimit.zip"
    )
    result["source_retrieved_at_utc"] = source_record["retrieved_at_utc"]
    result["source_sha256"] = source_record["sha256"]
    result["registry_sha256"] = hashlib.sha256(registry_bytes).hexdigest()
    groups = unmatched_groups(unmatched)
    retained = write_unmatched(raw_dir, unmatched)
    output.mkdir(parents=True, exist_ok=False)
    values = {
        "summary.json": result,
        "attributed.json": attributed,
        "unmatched_by_lease.json": groups,
        "schema.json": source_schema(),
        "source_manifest.json": provenance,
    }
    outputs = []
    for name, value in values.items():
        path = output / name
        write_json(path, value)
        outputs.append(file_digest(path, "curated_directory"))
    outputs.append(file_digest(retained, "external_raw_directory"))
    write_json(
        output / "extract_manifest.json",
        {
            "version": 1,
            "source_id": "bsee-data-center",
            "owner": "worldenergydata",
            "registry": "config/fields.yml",
            "registry_sha256": result["registry_sha256"],
            "source_sha256": source_record["sha256"],
            "outputs": outputs,
            "retention": (
                "Raw inputs and per-borehole unmatched CSV remain in configured "
                "external raw directory; curated outputs are committed."
            ),
        },
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir", type=Path, default=os.environ.get("BSEE_BOREHOLE_RAW_DIR")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=Path("config/fields.yml"))
    parser.add_argument(
        "--reuse-manifest", action="store_true", help="Offline digest-verified reuse"
    )
    args = parser.parse_args()
    if args.raw_dir is None:
        parser.error("Set BSEE_BOREHOLE_RAW_DIR or --raw-dir to external data storage")
    raw_dir, output = args.raw_dir.resolve(), args.output_dir.resolve()
    repo = Path(__file__).resolve().parents[2]
    if raw_dir == repo or repo in raw_dir.parents:
        parser.error("Raw storage must be outside the repository")
    if output.exists():
        parser.error("Output already exists; choose a new snapshot directory")
    provenance = obtain_source(raw_dir, args.reuse_manifest)
    result = write_snapshot(raw_dir, output, args.registry, provenance)
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("source_boreholes", "joined_boreholes", "unmatched_counts")
            }
        )
    )


if __name__ == "__main__":
    main()
