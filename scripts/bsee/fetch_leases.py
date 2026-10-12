#!/usr/bin/env python3
"""Fetch or curate the public BSEE lease snapshot; raw storage is caller-owned."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from html import escape
from pathlib import Path
from typing import Any

from worldenergydata.bsee.lease_fetch import PAGE, discover_archives, fetch_bundle
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


MANIFEST_DIFFERENCE_EXIT = 2
PANEL_COLUMNS = {
    "lease_num": "Lease",
    "area_block": "Area/block",
    "status": "Status",
    "effective_date": "Lease effective date",
    "expiration_date": "Actual expiration date",
    "expected_expiration_date": "Expected expiration date",
    "current_owners": "Current owner assignment interest (%)",
}


def compare_manifest(
    previous: dict[str, Any], current: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Compare discovery links; compare all other source bytes and locations."""
    old = {row["file"]: row for row in previous["files"]}
    new = {row["file"]: row for row in current["files"]}
    differences: list[str] = []
    information: list[str] = []
    for name in sorted(old.keys() | new.keys()):
        if name not in old or name not in new:
            differences.append(f"{name}: {'added' if name in new else 'removed'}")
            continue
        discovery = name == "leasing-page.html"
        keys: tuple[str, ...] = ("source_url", "size_bytes", "sha256")
        if discovery:
            keys += ("archive_links",)
            if "archive_links" not in old[name] or "archive_links" not in new[name]:
                differences.append(f"{name}: archive_links absent")
        for key in keys:
            if old[name].get(key) != new[name].get(key):
                message = f"{name}: {key}: {old[name].get(key)} -> {new[name].get(key)}"
                if discovery and key in {"size_bytes", "sha256"}:
                    information.append(f"informational: {message}")
                else:
                    differences.append(message)
    return differences, information


def publish_manifest(
    records: list[dict[str, Any]], raw_dir: Path, output: Path, *, update: bool
) -> int:
    """Retain the run manifest; return 2 for a normal-run source difference."""
    manifest = {
        "source_id": "bsee-data-center",
        "owner_repo": "worldenergydata",
        "files": records,
    }
    write_json(raw_dir / "source_manifest.json", manifest)
    target = output / "source_manifest.json"
    differences, information = (
        compare_manifest(json.loads(target.read_text()), manifest)
        if target.exists()
        else (["No curated manifest exists"], [])
    )
    print(
        json.dumps(
            {
                "manifest_differences": differences,
                "manifest_information": information,
            }
        )
    )
    if update:
        write_json(target, manifest)
    return MANIFEST_DIFFERENCE_EXIT if differences and not update else 0


def saved_records(raw_dir: Path) -> list[dict[str, Any]]:
    """Rebuild records offline using saved provenance, validating every source."""
    manifest = json.loads((raw_dir / "source_manifest.json").read_text())
    records = []
    for entry in manifest["files"]:
        name = entry["file"]
        if Path(name).name != name:
            raise ValueError("Saved source filename must be a basename")
        path = raw_dir / name
        record = json.loads(path.with_name(name + ".provenance.json").read_text())
        content = path.read_bytes()
        if (
            record["file"] != name
            or record["size_bytes"] != len(content)
            or record["sha256"] != hashlib.sha256(content).hexdigest()
        ):
            raise ValueError("Saved source does not match provenance")
        if name == "leasing-page.html":
            if record["source_url"] != PAGE:
                raise ValueError("Saved source discovery address does not match")
            record["archive_links"] = discover_archives(content.decode("utf-8"))
        records.append(record)
    return records


def owner_lines(owners: list[dict[str, Any]]) -> str:
    """Escape each source owner independently, retaining serial and optional group."""
    lines = []
    for owner in owners:
        serial = str(owner["SN_LSE_OWNER"])
        group = owner.get("OWNER_GROUP_CODE")
        prefix = serial + (f" / group {group}" if group else "")
        name = owner.get("owner_name") or owner["owner_name_reason"]
        lines.append(escape(f"{prefix} / {name}: {owner['ASSIGNMENT_PCT']}%"))
    return "<br>".join(lines) if lines else "Not reported"


def save_panel_html(output: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Render escaped source values from the same curated retrieval."""
    html = '<!doctype html><html lang="en"><meta charset="utf-8">'
    html += "<title>Lease panel source values</title><h1>Lease panel source values</h1>"
    html += (
        "<p>Actual and expected expiration dates remain distinct. Assignment interests "
    )
    html += "are not aggregated across groups. Source disclaimer: working database, "
    html += "not a legal document.</p><table><tr>"
    html += (
        "".join(f"<th>{escape(label)}</th>" for label in PANEL_COLUMNS.values())
        + "</tr>\n"
    )
    for row in rows:
        html += "<tr>"
        for key in PANEL_COLUMNS:
            value = row.get(key)
            if key == "current_owners":
                text = owner_lines(value or [])
            else:
                text = escape(str(value) if value is not None else "Not reported")
            html += f"<td>{text}</td>"
        html += "</tr>\n"
    html += "</table><p>Table 1. Source values for future panel wiring; status and interests "
    html += "apply to the snapshot recorded in source_manifest.json.</p></html>\n"
    path = output / "panel_values.html"
    path.write_text(html, encoding="utf-8")
    content = path.read_bytes()
    if content.decode("utf-8") != html:
        raise OSError("Panel HTML readback mismatch")
    return {
        "file": path.name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
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
    by_lease = {row["lease_num"]: row for row in result["leases"]}
    artifacts.append(
        save_panel_html(
            output,
            [{**by_lease[row["lease_num"]], **row} for row in result["panel_values"]],
        )
    )
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
    parser.add_argument(
        "--update-manifest",
        action="store_true",
        help="Replace the curated manifest and extract; --from-saved uses saved provenance",
    )
    args = parser.parse_args()
    if args.raw_dir is None:
        parser.error("Set BSEE_LEASE_RAW_DIR or --raw-dir to external data storage")
    output = args.output_dir
    if args.from_saved and args.update_manifest:
        publish_manifest(saved_records(args.raw_dir), args.raw_dir, output, update=True)
    if not args.from_saved:
        schema_path = (
            Path(__file__).resolve().parents[2]
            / "data/modules/bsee/leases/source_schema.json"
        )
        schema = json.loads(schema_path.read_text())
        records = fetch_bundle(schema, args.raw_dir)
        if args.update_manifest:
            output.mkdir(parents=True, exist_ok=True)
        status = publish_manifest(
            records, args.raw_dir, output, update=args.update_manifest
        )
        if not args.update_manifest:
            raise SystemExit(status)
    schema_path, schema = prepare_schema(output)
    tables = saved_tables(args.raw_dir, output, schema)
    registry = load_fields(args.registry)
    leases = poster_leases(registry)
    result = curate(tables, leases)
    result["registry"] = registry_check(leases, registry)
    save_extract(output, schema_path, tables, leases, result)


if __name__ == "__main__":
    main()
