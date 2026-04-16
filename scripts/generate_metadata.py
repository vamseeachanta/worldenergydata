#!/usr/bin/env python3
"""Generate _metadata.json for each data module under data/modules/.

Scans every module directory for data files, computes row counts for CSVs
(using csv.reader, not pandas), and writes a self-documenting metadata file
that powers the ``worldenergydata status`` CLI command.

Usage:
    python3 scripts/generate_metadata.py
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Data file extensions to include in metadata
DATA_EXTENSIONS = {
    ".csv",
    ".parquet",
    ".db",
    ".json",
    ".xls",
    ".xlsx",
    ".zip",
    ".txt",
    ".bin",
    ".pkl",
    ".html",
}

# Extensions where row counting makes sense
ROW_COUNTABLE = {".csv"}

# Repo root: one level up from scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO_ROOT / "data" / "modules"


def count_csv_rows(filepath: Path) -> int:
    """Count data rows in a CSV file (excludes header).

    Uses csv.reader for lightweight counting -- no pandas dependency.
    Returns 0 on any read error.
    """
    try:
        with open(filepath, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                return 0
            return sum(1 for _ in reader)
    except Exception:
        return 0


def gather_file_info(module_dir: Path) -> list[dict]:
    """Walk *module_dir* and return metadata for every data file."""
    files = []
    for root, _dirs, filenames in os.walk(module_dir):
        for name in filenames:
            fp = Path(root) / name
            suffix = fp.suffix.lower()
            if suffix not in DATA_EXTENSIONS:
                continue
            # Skip hidden/metadata files we generate ourselves
            if name.startswith("_metadata"):
                continue
            stat = fp.stat()
            entry: dict = {
                "name": str(fp.relative_to(module_dir)),
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%d"),
            }
            if suffix in ROW_COUNTABLE:
                entry["rows"] = count_csv_rows(fp)
            files.append(entry)
    # Sort by path for deterministic output
    files.sort(key=lambda f: f["name"])
    return files


def dominant_format(files: list[dict]) -> str:
    """Return the most common file extension across *files*."""
    from collections import Counter

    if not files:
        return "none"
    exts = [Path(f["name"]).suffix.lower() for f in files]
    most_common = Counter(exts).most_common(1)
    return most_common[0][0].lstrip(".") if most_common else "mixed"


def build_metadata(module_name: str, module_dir: Path) -> dict:
    """Build the metadata dict for a single module."""
    files = gather_file_info(module_dir)

    if not files:
        return {
            "module": module_name,
            "last_refresh": None,
            "record_count": 0,
            "file_count": 0,
            "total_size_bytes": 0,
            "source_url": "",
            "format": "none",
            "note": "no data files -- run 'make data'",
            "files": [],
        }

    total_size = sum(f["size_bytes"] for f in files)
    record_count = sum(f.get("rows", 0) for f in files)

    # last_refresh = most recent file modification
    all_dates = [f["modified"] for f in files]
    last_refresh_date = max(all_dates) if all_dates else None
    # Build an ISO timestamp from the date (midnight UTC)
    last_refresh = f"{last_refresh_date}T00:00:00Z" if last_refresh_date else None

    return {
        "module": module_name,
        "last_refresh": last_refresh,
        "record_count": record_count,
        "file_count": len(files),
        "total_size_bytes": total_size,
        "source_url": "",
        "format": dominant_format(files),
        "files": files,
    }


def main() -> None:
    if not MODULES_DIR.is_dir():
        print(f"ERROR: modules directory not found: {MODULES_DIR}", file=sys.stderr)
        sys.exit(1)

    modules = sorted(p for p in MODULES_DIR.iterdir() if p.is_dir())
    print(f"Scanning {len(modules)} module(s) under {MODULES_DIR} ...")

    for module_dir in modules:
        module_name = module_dir.name
        metadata = build_metadata(module_name, module_dir)
        out_path = module_dir / "_metadata.json"
        out_path.write_text(json.dumps(metadata, indent=2) + "\n")
        fc = metadata["file_count"]
        rc = metadata["record_count"]
        print(f"  {module_name:25s}  files={fc:4d}  rows={rc:>10,}")

    print("Done.")


if __name__ == "__main__":
    main()
