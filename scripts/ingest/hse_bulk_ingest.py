#!/usr/bin/env python3
"""Inventory OSHA fragments before bulk deduplication (no ingest yet).

The bulk source directory must be available locally. Point --raw-dir at the
directory holding the DOL fragments, choose one --table, and point --index-db at
a NEW SQLite file on scratch storage. Redirect stdout to retain the JSON
inventory. For example:

    python scripts/ingest/hse_bulk_ingest.py --raw-dir data/modules/hse/raw/osha \
        --index-db scratch/osha-profile.sqlite > scratch/osha-profile.json

Exactly one table is profiled per run, so totals never mix tables. Fragment
names must match the table exactly (osha_violation<N>.csv for the default
violation table) and are processed in numeric suffix order. Candidate keys and
date columns come from the catalogued fragment schemas; see TABLES.

Rows are streamed; exact row and candidate-key signatures are indexed on disk.
All columns and original string values participate in exact row identity;
column order does not. Keys use exact strings, without numeric conversion or
trimming. Repeated keys can have different payloads and are NOT safe deletion
candidates. Overlap counts include each occurrence seen in an earlier fragment.
Missing key values and non-ISO dates are counted explicitly, never inferred.
A fragment without the key or date columns reports those metrics as null and is
listed at top level; key totals are null when any fragment lacks the key.
Fragments are decoded as latin-1 by default, as the repository's OSHA acquirer
and importer read DOL files; a UTF-8 byte-order mark needs --encoding utf-8-sig.
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

# Key and date columns come from the catalogued fragment schemas in
# data/catalog/data-catalog.yml: osha_violation0..13 (activity_nr, citation_id,
# ..., issuance_date, ...), osha_violation_event0..11 (activity_nr, citation_id,
# ..., hist_date, ...) and osha_violation_gen_duty_std0..2 (activity_nr,
# citation_id, line_nr, line_text, load_dt). activity_nr is the inspection
# number and citation_id the citation within it, so a violation-table key is
# expected to occur once; history events and general-duty text lines refer to a
# citation and are expected to repeat it. load_dt is a load stamp, not an event
# date, so the general-duty table has no date column.
TABLES = {
    "violation": {
        "pattern": re.compile(r"osha_violation([0-9]+)\.csv"),
        "key": ("activity_nr", "citation_id"),
        "date": "issuance_date",
        "key_repeats_expected": False,
    },
    "violation_event": {
        "pattern": re.compile(r"osha_violation_event([0-9]+)\.csv"),
        "key": ("activity_nr", "citation_id"),
        "date": "hist_date",
        "key_repeats_expected": True,
    },
    "violation_gen_duty_std": {
        "pattern": re.compile(r"osha_violation_gen_duty_std([0-9]+)\.csv"),
        "key": ("activity_nr", "citation_id"),
        "date": None,
        "key_repeats_expected": True,
    },
}
ENCODINGS = ("latin-1", "utf-8", "utf-8-sig")
_KEY_METRICS = (
    "keyed_rows",
    "unkeyed_rows",
    "duplicate_candidate_keys",
    "overlap_candidate_keys",
)
_DATE_METRICS = ("missing_dates", "invalid_dates")
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
        item["missing_dates"] += 1
        return
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Expected ISO calendar date")
        date.fromisoformat(value)
    except ValueError:
        item["invalid_dates"] += 1
        return
    low, high = item["date_min"], item["date_max"]
    item["date_min"] = min(low, value) if low else value
    item["date_max"] = max(high, value) if high else value


def _select_fragments(raw_dir, pattern):
    """Return exact table fragments in numeric suffix order (name breaks ties)."""
    matches = []
    for path in raw_dir.iterdir() if raw_dir.is_dir() else ():
        match = pattern.fullmatch(path.name)
        if match and path.is_file():
            matches.append((int(match.group(1)), path.name, path))
    return [path for _, _, path in sorted(matches)]


def _profile_file(path, index, file_number, spec, encoding):
    before = path.stat()
    item = dict.fromkeys(
        ("rows", "duplicate_rows", "overlap_rows", *_KEY_METRICS, *_DATE_METRICS),
        0,
    )
    item.update(name=path.name, date_min=None, date_max=None)
    key_columns, date_column = spec["key"], spec["date"]
    with path.open("rb") as source:
        reader = _DigestReader(source)
        with io.TextIOWrapper(
            io.BufferedReader(reader), encoding=encoding, newline=""
        ) as stream:
            rows = csv.reader(stream, strict=True)
            columns = next(rows, [])
            if (
                not columns
                or any(not c.strip() for c in columns)
                or len(set(columns)) != len(columns)
            ):
                raise ValueError(f"Invalid header in fragment {file_number + 1}")
            if columns[0].startswith("ï»¿"):
                raise ValueError(
                    f"Fragment {file_number + 1} starts with a UTF-8 byte-order "
                    "mark; rerun with --encoding utf-8-sig"
                )
            item["columns"] = columns
            item["missing_key_columns"] = [c for c in key_columns if c not in columns]
            has_key = not item["missing_key_columns"]
            has_date = date_column is not None and date_column in columns
            item["date_column_present"] = has_date
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
                if has_date:
                    _observe_date(item, row[date_column])
                if not has_key:
                    continue
                key = [row[column] for column in key_columns]
                if all(value.strip() for value in key):
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
    # An absent column is reported as absent (null), not as zero observations.
    if not has_key:
        item.update(dict.fromkeys(_KEY_METRICS))
    if not has_date:
        item.update(dict.fromkeys(_DATE_METRICS))
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"Fragment {file_number + 1} changed during profiling")
    return item


def profile_fragments(
    raw_dir: Path, index_db: Path, table: str = "violation", encoding: str = "latin-1"
) -> dict:
    """Return a deterministic inventory; propagate input and storage failures.

    Zero counts mean observed zero records; null means the column is absent.
    Missing columns remain visible in each file's schema report. Empty,
    duplicate or unnamed headers and malformed records fail the run, so partial
    inventories cannot masquerade as complete.
    """
    if table not in TABLES:
        raise ValueError(f"Unknown OSHA table {table!r}; choose from {sorted(TABLES)}")
    if encoding not in ENCODINGS:
        raise ValueError(f"Unsupported encoding {encoding!r}; choose from {ENCODINGS}")
    spec = TABLES[table]
    paths = _select_fragments(raw_dir, spec["pattern"])
    if not paths:
        raise FileNotFoundError(f"No OSHA {table} fragments found")
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
                    files.append(_profile_file(path, index, number, spec, encoding))
            except csv.Error as error:
                raise ValueError(
                    f"Malformed CSV record in fragment {number + 1}"
                ) from error
        missing_key = [item["name"] for item in files if item["missing_key_columns"]]
        missing_date = [
            item["name"]
            for item in files
            if spec["date"] is not None and not item["date_column_present"]
        ]
        total = {
            name: sum(item[name] for item in files)
            for name in ("rows", "duplicate_rows")
        }
        # A key total over only some fragments is not comparable, so it is null.
        for name in ("keyed_rows", "unkeyed_rows", "duplicate_candidate_keys"):
            total[name] = None if missing_key else sum(item[name] for item in files)
        inventory = {
            "index_db": index_db.name,
            "index_complete": True,
            "table": table,
            "encoding": encoding,
            "candidate_key": list(spec["key"]),
            "key_repeats_expected": spec["key_repeats_expected"],
            "date_column": spec["date"],
            "files_missing_key_columns": missing_key,
            "files_missing_date_column": missing_date,
            "files": files,
            **total,
            "unique_rows": total["rows"] - total["duplicate_rows"],
            "unique_candidate_keys": (
                None
                if missing_key
                else total["keyed_rows"] - total["duplicate_candidate_keys"]
            ),
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
    parser.add_argument("--table", choices=sorted(TABLES), default="violation")
    parser.add_argument("--encoding", choices=ENCODINGS, default="latin-1")
    args = parser.parse_args()
    # No error is swallowed: failures exit nonzero without a success inventory.
    inventory = profile_fragments(
        args.raw_dir, args.index_db, table=args.table, encoding=args.encoding
    )
    print(json.dumps(inventory, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
