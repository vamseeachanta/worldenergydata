"""Reproduce retained survey rows from a pinned public archive and catalog.

Catalog order and structural completeness determine selection; computed path
errors are not used. Original numeric fields and archive row order are retained.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import zipfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "data/modules/bsee/directional_survey_validation"
NUMERIC_FIELDS = (1, 2, 3, 5, 6, 8, 9, 10, 11, 12)


def digest(path):
    """Hash a file without loading the archive into memory."""
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _catalog_apis(catalog):
    """Yield identifiers in held-catalog order, preserving the selection basis."""
    with Path(catalog).open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            number = Decimal(row["API_WELL_NUMBER"])
            if not number.is_finite() or number != number.to_integral_value():
                raise ValueError("Invalid catalog API identifier")
            yield str(int(number))


def _survey_rows(archive, member, api12):
    """Read the candidate's original rows and convert only line endings to LF."""
    rows = []
    identifier = api12.encode("ascii")
    with archive.open(member) as stream:
        for raw in stream:
            if raw.partition(b",")[0].strip().strip(b'"') == identifier:
                rows.append(raw.rstrip(b"\r\n") + b"\n")
    return rows


def _complete_unique_survey(rows):
    """Apply the same completeness and unique-depth checks as the record loader."""
    if len(rows) < 2:
        return False
    depths = set()
    for raw in rows:
        fields = next(csv.reader([raw.decode("utf-8")]))
        if len(fields) != 13:
            return False
        if fields[4].strip() not in ("N", "S") or fields[7].strip() not in ("E", "W"):
            return False
        try:
            numbers = {i: float(fields[i]) for i in NUMERIC_FIELDS}
        except ValueError:
            return False
        if not all(math.isfinite(value) for value in numbers.values()):
            return False
        if numbers[3] in depths:
            return False
        depths.add(numbers[3])
    return True


def extract(archive_path, catalog_path, source_path, output_path):
    """Verify provenance, select the first qualifying survey and verify its bytes."""
    source = json.loads(Path(source_path).read_text(encoding="utf-8"))
    for path, key in (
        (archive_path, "archive_sha256"),
        (catalog_path, "held_catalog_sha256"),
    ):
        if digest(path) != source[key]:
            raise ValueError(f"{key} digest mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        for api12 in _catalog_apis(catalog_path):
            rows = _survey_rows(archive, source["archive_member"], api12)
            if _complete_unique_survey(rows):
                break
        else:
            raise ValueError("No complete, unique-depth catalog survey found")
    if api12 != source["api12"] or len(rows) != source["record_count"]:
        raise ValueError("Selected survey differs from the recorded API or row count")
    retained = b"".join(rows)
    if hashlib.sha256(retained).hexdigest() != source["data_sha256"]:
        raise ValueError("Retained data digest mismatch")
    output = Path(output_path)
    if output.resolve() in {
        Path(path).resolve() for path in (archive_path, catalog_path, source_path)
    }:
        raise ValueError("Output must not replace a provenance input")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(retained)
    if digest(output) != source["data_sha256"]:
        raise ValueError("Written data digest mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument(
        "--catalog", type=Path, default=ROOT / "data/modules/bsee/current/wells/well_data.csv"
    )
    parser.add_argument("--source", type=Path, default=INPUTS / "source.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    extract(args.archive, args.catalog, args.source, args.output)


if __name__ == "__main__":
    main()
