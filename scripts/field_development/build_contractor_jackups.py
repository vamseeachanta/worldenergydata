"""Map a supplied public contractor specification CSV to the jackup table.

The input digest must be supplied explicitly. Existing output is never read.
Only source fields with an established counterpart in the table are mapped.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

SOURCE_COLUMNS = (
    "rig",
    "owner",
    "design",
    "year",
    "max_water_depth_m",
    "leg_count",
    "leg_type",
    "leg_length_m",
    "leg_spacing_long_m",
    "leg_spacing_trans_m",
    "spudcan_diameter_m",
    "hull_length_m",
    "hull_breadth_m",
    "hull_depth_m",
    "lightship_t",
    "variable_load_t",
    "preload_per_leg_t",
    "drilling_depth_m",
    "source_url",
    "accessed",
)
OUTPUT_COLUMNS = (
    "RIG_NAME",
    "RIG_DESIGN_MODEL",
    "YEAR_DELIVERED",
    "COUNTRY_BUILT",
    "CLASSIFICATION_SOCIETY",
    "MAX_WATER_DEPTH_RATING_FT",
    "MIN_WATER_DEPTH_FT",
    "OVERALL_LEG_LENGTH_FT",
    "SPUD_CAN_DIAMETER_FT",
    "MAX_DRILLING_DEPTH_FT",
    "QUARTERS_CAPACITY",
    "OVERALL_HULL_LENGTH_FT",
    "DERRICK_RATING_KIPS",
    "DRAWWORKS_HP",
    "BOP_OPERATING_PRESSURE_KSI",
    "source_url",
)
LENGTH_FIELDS = {
    "MAX_WATER_DEPTH_RATING_FT": "max_water_depth_m",
    "OVERALL_LEG_LENGTH_FT": "leg_length_m",
    "SPUD_CAN_DIAMETER_FT": "spudcan_diameter_m",
    "MAX_DRILLING_DEPTH_FT": "drilling_depth_m",
    "OVERALL_HULL_LENGTH_FT": "hull_length_m",
}


def metres_to_feet(value: str) -> str:
    """Retain blanks and express positive metre values to one decimal foot."""
    if not value:
        return ""
    try:
        number = Decimal(value)
        if not number.is_finite() or number <= 0:
            raise ValueError("Length must be finite and positive")
        # NIST SP 811, 2008 edition, Appendix B.6, "U.S. survey foot and mile".
        # https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors
        # The international-foot definition is exact; half-up rounding is local policy.
        return str((number / Decimal("0.3048")).quantize(Decimal("0.1"), ROUND_HALF_UP))
    except InvalidOperation as error:
        raise ValueError("Invalid length") from error


def validate_source_row(row: dict[str, str], seen: set[str], line: int) -> None:
    """Reject malformed rows without including source values in diagnostics."""
    if None in row or any(value is None for value in row.values()):
        raise ValueError(f"Row {line}: wrong cell count")
    name = row["rig"].strip().casefold()
    if not name:
        raise ValueError(f"Row {line}: missing rig")
    if name in seen:
        raise ValueError(f"Row {line}: duplicate rig")
    seen.add(name)
    urls = row["source_url"].split(";")
    for url in urls:
        parsed = urlsplit(url.strip())
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError(f"Row {line}: invalid source_url")
    try:
        date.fromisoformat(row["accessed"])
    except ValueError as error:
        raise ValueError(f"Row {line}: invalid accessed date") from error
    year = row["year"]
    if year and (len(year) != 4 or not year.isascii() or not year.isdigit()):
        raise ValueError(f"Row {line}: invalid year")


def build_csv(source: bytes) -> bytes:
    """Build solely from the supplied collection, including missing values."""
    reader = csv.DictReader(io.StringIO(source.decode("utf-8"), newline=""))
    if reader.fieldnames != list(SOURCE_COLUMNS):
        raise ValueError("Unexpected contractor input schema")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    seen: set[str] = set()
    for line, row in enumerate(reader, start=2):
        validate_source_row(row, seen, line)
        output = dict.fromkeys(OUTPUT_COLUMNS, "")
        output.update(
            RIG_NAME=row["rig"],
            RIG_DESIGN_MODEL=row["design"],
            YEAR_DELIVERED=row["year"],
            source_url=row["source_url"],
        )
        for target, original in LENGTH_FIELDS.items():
            try:
                output[target] = metres_to_feet(row[original])
            except ValueError as error:
                raise ValueError(f"Row {line}: invalid {original}") from error
        writer.writerow(output)
    if not seen:
        raise ValueError("Empty contractor collection")
    return stream.getvalue().encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args(argv)
    import sys

    source_dir = (
        Path(__file__).resolve().parents[2] / "src/worldenergydata/field_development"
    )
    sys.path.insert(0, str(source_dir))
    from data_availability import require_available_source

    require_available_source(args.output)
    if args.source.resolve() == args.output.resolve():
        raise ValueError("Input and output must be distinct")
    raw = args.source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.source_sha256:
        raise ValueError("Contractor input digest mismatch")
    result = build_csv(raw)
    args.output.write_bytes(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
