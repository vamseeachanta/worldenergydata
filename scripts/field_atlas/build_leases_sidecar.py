#!/usr/bin/env python3
"""Opt-in offline lease sidecar export; no download or site publication.

Supply --snapshot-dir, --registry, one or more --field canonical ids and
--output. The destination must be new and outside source directories.
Current records retain their source group/aliquot identity and percentage units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from worldenergydata.common.fields_registry import load_fields, normalize_lease

LEASE_KEYS = ("area_block", "status", "effective_date", "royalty_system")
PANEL_KEYS = (
    "expiration_date",
    "expected_expiration_date",
    "expiration_reason",
    "current_owners",
    "current_operators",
    "owner_reason",
    "operator_reason",
    "surface_area",
    "surface_area_unit_code",
)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _json(content):
    value = json.loads(content, object_pairs_hook=_unique)
    json.dumps(value, allow_nan=False)  # Reject NaN, infinity and overflow.
    return value


def _sha(content):
    return hashlib.sha256(content).hexdigest()


def _index(rows, registry):
    result = {}
    for row in rows:
        key = normalize_lease(row["lease_num"])
        if key in result or registry.by_lease(key) is None:
            raise ValueError("Ambiguous or unregistered snapshot lease")
        result[key] = row
    return result


def export_leases(
    snapshot: Path, registry_path: Path, field_ids: list[str], output: Path
):
    """Verify snapshot bytes, join by canonical lease id, and write strict JSON.

    Missing source rows produce null attributes with explicit dispositions.
    Inconsistent manifests or identities fail before the destination is opened.
    Existing destinations are always rejected, including symbolic links.
    """
    root = Path(__file__).resolve().parents[2]
    destination = output.resolve()
    source_roots = [snapshot.resolve()] + [
        root / name
        for name in "src packages config data scripts tests .git .claude .agents".split()
    ]
    if destination == registry_path.resolve() or any(
        destination.is_relative_to(path) for path in source_roots
    ):
        raise ValueError("Source directories cannot contain export output")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Export destination already exists")
    names = (
        "extract_manifest.json",
        "source_manifest.json",
        "leases.json",
        "panel_values.json",
    )
    contents = {name: (snapshot / name).read_bytes() for name in names}
    extract = _json(contents["extract_manifest.json"])
    artifacts = _unique((row["file"], row) for row in extract["artifacts"])
    if _sha(contents["source_manifest.json"]) != extract["source_manifest_sha256"]:
        raise ValueError("Source manifest digest mismatch")
    for name in ("leases.json", "panel_values.json"):
        record = artifacts[name]
        if (
            _sha(contents[name]) != record["sha256"]
            or len(contents[name]) != record["size_bytes"]
        ):
            raise ValueError("Snapshot digest or size mismatch")
    source = _json(contents["source_manifest.json"])
    if not source["files"]:
        raise ValueError("Source references are missing")
    for reference in source["files"]:
        for key in ("source_url", "retrieved_at_utc", "sha256", "terms"):
            if not reference[key]:
                raise ValueError("Source reference is incomplete")
    registry_bytes = registry_path.read_bytes()
    registry = load_fields(registry_path)
    if registry_path.read_bytes() != registry_bytes:
        raise ValueError("Registry changed during export")
    leases = _index(_json(contents["leases.json"]), registry)
    panels = _index(_json(contents["panel_values.json"]), registry)
    fields = {}
    if not field_ids:
        raise ValueError("At least one canonical field is required")
    for field_id in sorted(set(field_ids)):
        field = registry.by_id(field_id)
        if field is None:
            raise ValueError("Unknown canonical field")
        keys = [normalize_lease(number) for number in field.leases]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate normalized registry lease")
        rows = []
        for key in sorted(keys):
            if registry.by_lease(key) != field_id:
                raise ValueError("Lease resolves to a different field")
            row = {
                "lease_num": key,
                "missing": {},
                "operator_of_record_history": None,
                "history_reason": "Snapshot supplies current records, not operator-of-record history",
            }
            for name, index, attributes in (
                ("leases.json", leases, LEASE_KEYS),
                ("panel_values.json", panels, PANEL_KEYS),
            ):
                original = index.get(key)
                row.update(
                    {
                        attr: original[attr] if original is not None else None
                        for attr in attributes
                    }
                )
                if original is None:
                    row["missing"][name] = "Lease absent from snapshot table"
            row["area_block_source"] = (
                "leases.json:area_block" if key in leases else None
            )
            for collection in ("current_owners", "current_operators"):
                if "panel_values.json" not in row["missing"] and not isinstance(
                    row[collection], list
                ):
                    raise ValueError("Current records must be source lists")
                for record in row[collection] or []:
                    if normalize_lease(record["LEASE_NUMBER"]) != key:
                        raise ValueError("Current record belongs to a different lease")
            rows.append(row)
        fields[field_id] = {"leases": rows}
    result = {
        "schema_version": 1,
        "fields": fields,
        "metadata": {
            "input_sha256": {
                **{name: _sha(content) for name, content in contents.items()},
                "registry": _sha(registry_bytes),
            },
            "source_references": source["files"],
            "source_updated_at": None,
            "source_date_reason": "Retrieval timestamps are observations, not source-update dates",
            "working_interest_unit": "percent (0-100)",
            "limitations": "Public research snapshot; errors may exist. Not a legal document or for navigational use. Legal title and current interests are not established. Names are at retrieval, not reconstructed historically; no interests are aggregated.",
        },
    }
    serialized = json.dumps(result, allow_nan=False, sort_keys=True, indent=2) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    if _json(output.read_bytes()) != result:
        raise OSError("Export readback mismatch")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--field", required=True, action="append")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    export_leases(args.snapshot_dir, args.registry, args.field, args.output)


if __name__ == "__main__":
    main()
