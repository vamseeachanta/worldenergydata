#!/usr/bin/env python3
"""Inventory OSHA fragments before bulk deduplication (no ingest yet).

The bulk source directory must be available locally. Point --raw-dir at the
directory containing osha_violation*.csv, and --index-db at a NEW SQLite file
on scratch storage. Redirect stdout to retain the JSON inventory. For example:

    python scripts/ingest/hse_bulk_ingest.py --raw-dir data/modules/hse/raw/osha \
        --index-db scratch/osha-profile.sqlite > scratch/osha-profile.json

Rows are streamed; exact row and candidate-key signatures are indexed on disk.
All columns and original string values participate in exact row identity;
column order does not. Candidate keys use the plan's violation_id,
establishment_id and citation_date, without numeric conversion or trimming.
Repeated keys can have different payloads and are NOT safe deletion candidates.
Overlap counts include each occurrence seen in an earlier sorted fragment.
Missing key fields and non-ISO dates are counted explicitly, never inferred.
No NAICS filtering, Parquet, catalog or database ingestion is performed here.
The index is retained and cannot be reused or overwritten by another run.
Readers must require SELECT complete FROM meta to return a single row of 1;
a missing table or any other result means the index is incomplete. Failed runs
can retain signatures from earlier fragments. A zero-byte fragment fails the
whole run; a header-only fragment is valid and contributes zero rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

CANDIDATE_KEY = ("violation_id", "establishment_id", "citation_date")
_STATEMENTS = {
    "exact_rows": (
        "CREATE TABLE exact_rows (signature TEXT PRIMARY KEY, first_file INTEGER) WITHOUT ROWID",
        "INSERT OR IGNORE INTO exact_rows VALUES (?, ?)",
        "SELECT first_file FROM exact_rows WHERE signature = ?",
    ),
    "candidate_keys": (
        "CREATE TABLE candidate_keys "
        "(signature TEXT PRIMARY KEY, first_file INTEGER) WITHOUT ROWID",
        "INSERT OR IGNORE INTO candidate_keys VALUES (?, ?)",
        "SELECT first_file FROM candidate_keys WHERE signature = ?",
    ),
}


class _DigestReader(io.RawIOBase):
    """Hash the source bytes consumed by the CSV parser in the same pass."""

    def __init__(self, source):
        self.source = source
        self.digest = hashlib.sha256()
        self.size = 0

    def readable(self):
        return True

    def readinto(self, buffer):
        count = self.source.readinto(buffer)
        self.digest.update(memoryview(buffer)[:count])
        self.size += count
        return count


def _observe_signature(index, table, signature, file_number):
    _, insert, select = _STATEMENTS[table]
    inserted = index.execute(insert, (signature, file_number)).rowcount
    if inserted:
        return 0, 0
    first_file = index.execute(select, (signature,)).fetchone()[0]
    return 1, int(first_file != file_number)


def _observe_date(item, value):
    if not value:
        item["missing_citation_dates"] += 1
        return
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Expected ISO calendar date")
        date.fromisoformat(value)
    except ValueError:
        item["invalid_citation_dates"] += 1
        return
    low, high = item["citation_date_min"], item["citation_date_max"]
    item["citation_date_min"] = min(low, value) if low else value
    item["citation_date_max"] = max(high, value) if high else value


def _profile_file(path, index, file_number):
    before = path.stat()
    item = dict.fromkeys(
        (
            "rows",
            "duplicate_rows",
            "overlap_rows",
            "keyed_rows",
            "unkeyed_rows",
            "duplicate_candidate_keys",
            "overlap_candidate_keys",
            "missing_citation_dates",
            "invalid_citation_dates",
        ),
        0,
    )
    item.update(name=path.name, citation_date_min=None, citation_date_max=None)
    with path.open("rb") as source:
        reader = _DigestReader(source)
        with io.TextIOWrapper(
            io.BufferedReader(reader), encoding="utf-8-sig", newline=""
        ) as stream:
            rows = csv.reader(stream, strict=True)
            columns = next(rows, [])
            if (
                not columns
                or any(not c.strip() for c in columns)
                or len(set(columns)) != len(columns)
            ):
                raise ValueError(f"Invalid header in fragment {file_number + 1}")
            item["columns"] = columns
            item["missing_key_columns"] = [c for c in CANDIDATE_KEY if c not in columns]
            for values in rows:
                if len(values) != len(columns):
                    raise ValueError(
                        f"Malformed record in fragment {file_number + 1}, CSV line {rows.line_num}"
                    )
                row = dict(zip(columns, values))
                signature = json.dumps(row, sort_keys=True, separators=(",", ":"))
                duplicate, overlap = _observe_signature(
                    index, "exact_rows", signature, file_number
                )
                item["rows"] += 1
                item["duplicate_rows"] += duplicate
                item["overlap_rows"] += overlap
                _observe_date(item, row.get("citation_date"))
                key = [row.get(column) for column in CANDIDATE_KEY]
                if all(value is not None and value.strip() for value in key):
                    duplicate, overlap = _observe_signature(
                        index, "candidate_keys", json.dumps(key), file_number
                    )
                    item["keyed_rows"] += 1
                    item["duplicate_candidate_keys"] += duplicate
                    item["overlap_candidate_keys"] += overlap
                else:
                    item["unkeyed_rows"] += 1
        item["sha256"] = reader.digest.hexdigest()
        item["bytes"] = reader.size
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"Fragment {file_number + 1} changed during profiling")
    return item


def profile_fragments(raw_dir: Path, index_db: Path) -> dict:
    """Return a deterministic inventory; propagate input and storage failures.

    Zero counts mean observed zero records. Missing columns remain visible in
    each file's schema report. Empty, duplicate or unnamed headers and malformed
    records fail the run, so partial inventories cannot masquerade as complete.
    """
    paths = sorted(raw_dir.glob("osha_violation*.csv"))
    if not paths:
        raise FileNotFoundError("No OSHA violation fragments found")
    # Exclusive creation prevents a mistaken scratch path from replacing data.
    with index_db.open("xb"):
        pass
    index = sqlite3.connect(index_db)
    try:
        # Bound SQLite's page cache to approximately 8 MiB; signatures stay on disk.
        index.execute("PRAGMA cache_size = -8192")
        with index:
            for create, _, _ in _STATEMENTS.values():
                index.execute(create)
            index.execute("CREATE TABLE meta (complete INTEGER NOT NULL)")
            index.execute("INSERT INTO meta VALUES (?)", (0,))
        files = []
        for number, path in enumerate(paths):
            try:
                with index:
                    files.append(_profile_file(path, index, number))
            except csv.Error as error:
                raise ValueError(
                    f"Malformed CSV record in fragment {number + 1}"
                ) from error
        total = {
            name: sum(item[name] for item in files)
            for name in (
                "rows",
                "duplicate_rows",
                "keyed_rows",
                "unkeyed_rows",
                "duplicate_candidate_keys",
            )
        }
        inventory = {
            "candidate_key": list(CANDIDATE_KEY),
            "files": files,
            **total,
            "unique_rows": total["rows"] - total["duplicate_rows"],
            "unique_candidate_keys": total["keyed_rows"]
            - total["duplicate_candidate_keys"],
        }
        with index:
            index.execute("UPDATE meta SET complete = ?", (1,))
        return inventory
    finally:
        index.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--index-db", type=Path, required=True)
    args = parser.parse_args()
    # No error is swallowed: failures exit nonzero without a success inventory.
    inventory = profile_fragments(args.raw_dir, args.index_db)
    print(json.dumps(inventory, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
