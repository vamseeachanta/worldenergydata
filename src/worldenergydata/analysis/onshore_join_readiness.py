"""Bounded, read-only audits of explicitly selected onshore join inputs.

The contract and arithmetic are specified in
docs/data-sources/onshore/underwriting-joins.md. PASS refers to structural
joins only; it does not qualify pressure interpretation, rights or freshness.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# State prefixes and API widths: lifecycle/keys.py (Texas),
# tests/unit/state_regulators/test_kansas_kgs.py (Kansas source sample),
# tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py (Oklahoma
# compatibility fixtures), colorado_ecmc/parsers.py (Colorado), current
# repository contracts; full paths are in underwriting-joins.md.
# This consumer accepts full API strings only and never invents suffixes.
API_PREFIX = {"TX": "42", "KS": "15", "OK": "35", "CO": "05"}
API_WIDTHS = {10, 12, 14}
STATUSES = {
    "downloaded",
    "derived",
    "configured-only",
    "partial/error",
    "missing",
    "private/legacy",
}


def normalize_api(value: str, state: str) -> str | None:
    """Remove separator hyphens/spaces from a complete, state-qualified API."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9 -]+", value):
        return None
    digits = value.replace("-", "").replace(" ", "")
    prefix = API_PREFIX.get(state)
    if prefix is None or len(digits) not in API_WIDTHS or not digits.startswith(prefix):
        return None
    return digits


def _local(root: Path, value: str) -> Path:
    path = Path(value)
    resolved = (root / path).resolve()
    if path.is_absolute() or not resolved.is_relative_to(root.resolve()):
        raise ValueError("Expected a relative path within the supplied root")
    return resolved


def _validate(config: dict, root: Path) -> dict:
    entries = {}
    for entry in config["datasets"]:
        for name in ("id", "source_id", "source_version", "domain", "path"):
            if not isinstance(entry.get(name), str) or not entry[name].strip():
                raise ValueError(f"Nonempty {name} required")
        if entry["id"] in entries:
            raise ValueError("Dataset ids must be unique")
        if entry.get("state") not in API_PREFIX:
            raise ValueError("Unsupported state")
        if entry.get("status") not in STATUSES:
            raise ValueError("Unsupported inventory status")
        if not isinstance(entry.get("unique"), bool):
            raise TypeError("unique must be a boolean")
        keys = entry.get("keys")
        if (
            not isinstance(keys, dict)
            or not keys
            or not all(
                isinstance(k, str) and k and isinstance(v, str) and v
                for k, v in keys.items()
            )
        ):
            raise ValueError("Nonempty canonical-to-physical keys required")
        _local(root, entry["path"])
        entries[entry["id"]] = entry
    for join in config.get("joins", []):
        if join.get("left") not in entries or join.get("right") not in entries:
            raise ValueError("Join references unknown dataset")
        left, right = entries[join["left"]], entries[join["right"]]
        if left["state"] != right["state"]:
            raise ValueError("Join inputs must have the same state")
        on = join.get("on")
        if not isinstance(on, list) or not on or len(set(on)) != len(on):
            raise ValueError("Join requires distinct ordered keys")
        if any(key not in left["keys"] or key not in right["keys"] for key in on):
            raise ValueError("Join keys missing from dataset contract")
    for artifact in config.get("artifacts", []):
        _local(root, artifact["path"])
        _local(root, artifact["manifest"])
    return entries


def _read_rows(path: Path, wanted: list[str]):
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            yield reader.fieldnames or [], reader
    elif path.suffix.lower() == ".parquet":
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(path)
        selected = [name for name in wanted if name in parquet.schema_arrow.names]
        if "state" in parquet.schema_arrow.names and "state" not in selected:
            selected.append("state")
        rows = (
            row
            for batch in parquet.iter_batches(columns=selected)
            for row in batch.to_pylist()
        )
        yield parquet.schema_arrow.names, rows
    else:
        raise ValueError("Only CSV and Parquet tables are supported")


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        # Chunk size affects I/O only, not acceptance or numerical results.
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _key(row: dict, entry: dict) -> tuple | None:
    # A supplied state column is evidence, not a label to overwrite. Mixed-state
    # derived outputs require explicit per-state views before this audit.
    if "state" in row and row["state"] != entry["state"]:
        return None
    values = []
    for key, column in entry["keys"].items():
        value = row.get(column)
        # Identifiers are strings: accepting numeric values could lose zeros.
        if not isinstance(value, str) or not value.strip():
            return None
        value = value.strip()
        if key in {"api10", "api12", "api14"}:
            value = normalize_api(value, entry["state"])
            # The suffix on the canonical name defines the exact grain.
            if value is None or len(value) != int(key.removeprefix("api")):
                return None
        values.append(value)
    return (entry["state"], *values)


def _table(entry: dict, root: Path) -> tuple[dict, Counter]:
    report = {
        key: entry[key]
        for key in (
            "id",
            "source_id",
            "source_version",
            "state",
            "domain",
            "path",
            "keys",
            "unique",
        )
    }
    report.update(inventory_status=entry["status"], join_status="NOT_EVALUATED")
    counts = Counter()
    if entry["status"] not in {"downloaded", "derived"}:
        report["reason"] = "inventory_not_usable"
        return report, counts
    path = _local(root, entry["path"])
    if not path.is_file():
        report.update(inventory_status="missing", reason="file_missing")
        return report, counts
    try:
        report.update(byte_size=path.stat().st_size, sha256=_digest(path))
        for columns, rows in _read_rows(path, list(entry["keys"].values())):
            if len(set(columns)) != len(columns):
                report.update(join_status="FAIL", reason="duplicate_columns")
                return report, counts
            missing = sorted(set(entry["keys"].values()) - set(columns))
            if missing:
                report.update(
                    join_status="FAIL",
                    reason="missing_key_columns",
                    missing_columns=missing,
                )
                return report, counts
            total = invalid = malformed = 0
            for row in rows:
                total += 1
                # CSV missing/excess fields are structural defects. Parquet
                # nulls are valid values and are checked only for selected keys.
                if path.suffix.lower() == ".csv" and (
                    None in row or any(value is None for value in row.values())
                ):
                    malformed += 1
                key = _key(row, entry)
                if key is None:
                    invalid += 1
                else:
                    counts[key] += 1
            duplicates = sum(counts.values()) - len(counts)
            report.update(
                rows=total,
                invalid_key_rows=invalid,
                distinct_keys=len(counts),
                duplicate_key_rows=duplicates,
            )
            if not total:
                report["reason"] = "empty_table"
            elif malformed:
                report.update(join_status="FAIL", reason="malformed_rows")
            elif invalid or (entry["unique"] and duplicates):
                report.update(join_status="FAIL", reason="key_defects")
            else:
                report.update(join_status="PASS", reason="declared_keys_valid")
    except (ImportError, OSError, ValueError, csv.Error):
        # Exception messages can contain local paths or raw row content.
        report.update(join_status="NOT_EVALUATED", reason="table_unreadable")
        counts.clear()
    return report, counts


def _project(counts: Counter, entry: dict, on: list[str]) -> Counter:
    positions = [list(entry["keys"]).index(key) + 1 for key in on]
    result = Counter()
    for key, count in counts.items():
        result[(key[0], *(key[position] for position in positions))] += count
    return result


def _join(join: dict, entries: dict, reports: dict, profiles: dict) -> dict:
    report = {key: join[key] for key in ("left", "right", "on")}
    left_id, right_id = join["left"], join["right"]
    if any(reports[name]["join_status"] != "PASS" for name in (left_id, right_id)):
        return report | {"join_status": "NOT_EVALUATED", "reason": "input_not_passing"}
    left = _project(profiles[left_id], entries[left_id], join["on"])
    right = _project(profiles[right_id], entries[right_id], join["on"])
    # PostgreSQL 18 manual, section 7.2.1.1 Joined Tables (accessed 2026-10-20):
    # matching pairs plus one row per unmatched left row. Source and derivation
    # are linked in underwriting-joins.md; no empirical tolerance is applied.
    matched = sum(count for key, count in left.items() if key in right)
    unmatched = sum(left.values()) - matched
    inner_rows = sum(count * right[key] for key, count in left.items())
    right_duplicates = sum(count > 1 for count in right.values())
    reason = (
        "right_key_not_unique"
        if right_duplicates
        else "unmatched_left_keys" if unmatched else "many_to_one_verified"
    )
    return report | {
        "join_status": "FAIL" if right_duplicates or unmatched else "PASS",
        "matched_left_rows": matched,
        "unmatched_left_rows": unmatched,
        "inner_join_rows": inner_rows,
        "left_join_rows": inner_rows + unmatched,
        "right_duplicate_keys": right_duplicates,
        "reason": reason,
    }


def _artifact(entry: dict, root: Path) -> dict:
    path, manifest_path = _local(root, entry["path"]), _local(root, entry["manifest"])
    report = {key: entry[key] for key in ("source_id", "path", "manifest")}
    present = path.is_file() and zipfile.is_zipfile(path)
    report.update(zip_present=present, join_status="NOT_EVALUATED")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return report | {"reason": "manifest_unavailable"}
    if (
        not isinstance(manifest, dict)
        or manifest.get("source_id") != entry["source_id"]
    ):
        return report | {"reason": "manifest_source_mismatch"}
    if manifest.get("status") == "error" and present:
        return report | {"reason": "manifest_error_with_raw_zip"}
    return report | {
        "reason": (
            "raw_zip_requires_provenance_and_content_review"
            if present
            else "raw_zip_missing_or_invalid"
        )
    }


def audit(config: dict, root: Path) -> dict:
    """Audit selected files without ingestion, mutation, or row payload export.

    Memory scales with distinct keys, not table width; select bounded snapshots.
    Required source versions are supplied by the caller, not inferred from mtime.
    """
    entries = _validate(config, root)
    reports, profiles = {}, {}
    for name, entry in entries.items():
        reports[name], profiles[name] = _table(entry, root)
    return {
        "intended_use": "structural_join_audit_only",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "datasets": list(reports.values()),
        "joins": [
            _join(join, entries, reports, profiles) for join in config.get("joins", [])
        ],
        "artifacts": [_artifact(entry, root) for entry in config.get("artifacts", [])],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(json.loads(args.config.read_text(encoding="utf-8")), args.root)
    # Exclusive creation prevents an output argument from overwriting an input,
    # configuration, manifest, or earlier report.
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
