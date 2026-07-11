"""Create a bounded, public-safe inventory of Landman data roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_EVIDENCE = (
    "texas_rrc",
    "kansas_kgs",
    "oklahoma_occ",
    "colorado_ecmc",
    "pressure_screen",
    "hse",
    "bsee",
    "spain_cores",
    "kaggle_rogii",
    "frontierdeepwater",
    "tiny_placeholders",
    "private_legacy",
)
DENY_NAMES = {"private", "legacy", "client", "confidential", "proprietary"}
ROW_KEYS = {
    "evidence_key",
    "root_path",
    "root_owner",
    "status",
    "quarantined",
    "geography",
    "source_authority",
    "source_url",
    "representative_evidence",
    "artifact_sha256",
    "size_bytes",
    "observed_at",
    "landman_relevance",
    "limitations",
}


def _evidence_key(name: str) -> str:
    lowered = name.lower().replace("-", "_")
    aliases = {
        "texas": "texas_rrc",
        "kansas": "kansas_kgs",
        "oklahoma": "oklahoma_occ",
        "colorado": "colorado_ecmc",
        "legacy": "private_legacy",
        "private": "private_legacy",
    }
    return aliases.get(lowered, lowered or "unknown_root")


def _quarantined(path: Path) -> bool:
    return any(part.lower() in DENY_NAMES for part in path.parts)


def _row(
    key: str,
    path: str,
    observed_at: str,
    status: str,
    quarantined: bool,
    *,
    warning: str = "",
) -> dict[str, Any]:
    return {
        "evidence_key": key,
        "root_path": path,
        "root_owner": "redacted",
        "status": status,
        "quarantined": quarantined,
        "geography": "unknown",
        "source_authority": "unknown",
        "source_url": None,
        "representative_evidence": [],
        "artifact_sha256": None,
        "size_bytes": None,
        "observed_at": observed_at,
        "landman_relevance": [],
        "limitations": [warning] if warning else [],
    }


def scan_inventory(
    root: Path,
    *,
    max_depth: int = 2,
    max_entries: int = 500,
    timeout_seconds: int = 10,
    observed_at: str,
) -> dict[str, Any]:
    root = Path(root)
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    candidates: list[Path] = []
    if root.exists():
        for parent in sorted(
            (
                item
                for item in root.iterdir()
                if item.is_dir() and not item.is_symlink()
            ),
            key=lambda p: p.name,
        ):
            data = parent / "data"
            if data.is_dir() and not data.is_symlink():
                candidates.append(data)
    if len(candidates) > max_entries:
        warnings.append(f"entry limit reached: {max_entries}")
        candidates = candidates[:max_entries]
    for path in candidates:
        key = _evidence_key(path.parent.name)
        quarantined = _quarantined(path)
        if quarantined:
            rows.append(
                _row(
                    key or "private_legacy",
                    str(path),
                    observed_at,
                    "private/legacy",
                    True,
                    warning="quarantined; child traversal suppressed",
                )
            )
            continue
        row = _row(key, str(path), observed_at, "downloaded", False)
        manifest = path / "manifest.json"
        if manifest.is_file() and manifest.stat().st_size <= 1_000_000:
            content = manifest.read_bytes()
            row["artifact_sha256"] = hashlib.sha256(content).hexdigest()
            row["size_bytes"] = len(content)
            row["representative_evidence"] = ["manifest.json"]
            try:
                metadata = json.loads(content)
                row["source_url"] = (
                    metadata.get("source_url")
                    if isinstance(metadata.get("source_url"), str)
                    else None
                )
            except json.JSONDecodeError:
                row["limitations"].append("manifest.json is not valid JSON")
        rows.append(row)
    present = {row["evidence_key"] for row in rows if row["evidence_key"]}
    for key in REQUIRED_EVIDENCE:
        if key not in present:
            rows.append(
                _row(
                    key,
                    "unavailable",
                    observed_at,
                    "missing",
                    False,
                    warning="no bounded root observed",
                )
            )
    rows.sort(key=lambda row: (row["evidence_key"], row["root_path"]))
    return {
        "schema_version": "1.0",
        "scan_policy": {
            "max_depth": max_depth,
            "max_entries": max_entries,
            "timeout_seconds": timeout_seconds,
        },
        "observed_at": observed_at,
        "coverage_warnings": warnings,
        "rows": rows,
    }


def write_inventory(document: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "landman-data-root-inventory.json"
    markdown_path = output_dir / "landman-data-root-inventory.md"
    json_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Landman Data Root Inventory",
        "",
        f"Observed at: `{document['observed_at']}`",
        "",
        "| Evidence | Root | Status | Quarantined |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {row['evidence_key']} | {row['root_path']} | {row['status']} | {row['quarantined']} |"
        for row in document["rows"]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-entries", type=int, default=500)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args()
    write_inventory(
        scan_inventory(
            args.root,
            max_depth=args.max_depth,
            max_entries=args.max_entries,
            timeout_seconds=args.timeout_seconds,
            observed_at=args.observed_at,
        ),
        args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
