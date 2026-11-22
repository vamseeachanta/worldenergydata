"""Read the USWTDB 3.2 CSV geometry subset without network access."""

import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass
from typing import Optional, Tuple, Union

RELEASE = "3.2 (2020-10-14)"
IDENTIFIERS = ("case_id", "faa_ors", "faa_asn", "usgs_pr_id", "eia_id")
MEASUREMENTS = ("t_cap", "t_hh", "t_rd", "t_rsa", "t_ttlh", "xlong", "ylat")
INTEGER = re.compile(r"[0-9]+")
DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


@dataclass(frozen=True)
class USWTDBTurbine:
    """Source field names; kW, meters, square meters and NAD83 decimal degrees."""

    case_id: str
    faa_ors: Optional[str]
    faa_asn: Optional[str]
    usgs_pr_id: Optional[str]
    eia_id: Optional[str]
    t_cap: Optional[int]
    t_hh: Optional[float]
    t_rd: Optional[float]
    t_rsa: Optional[float]
    t_ttlh: Optional[float]
    xlong: float
    ylat: float


@dataclass(frozen=True)
class USWTDBData:
    """Ordered records and provenance for the exact supplied CSV bytes."""

    release: str
    source_sha256: str
    turbines: Tuple[USWTDBTurbine, ...]


def _number(text: str, field: str, line: int) -> Optional[Union[int, float]]:
    required = field in ("xlong", "ylat")
    if text == "" and not required:
        return None
    pattern = INTEGER if field == "t_cap" else DECIMAL
    if not pattern.fullmatch(text):
        raise ValueError(f"line {line}: invalid {field}")
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"line {line}: non-finite {field}")
    if field == "xlong":
        valid = -180 <= value <= 180
    elif field == "ylat":
        valid = -90 <= value <= 90
    else:
        valid = value >= 0
    if not valid:
        raise ValueError(f"line {line}: out-of-range {field}")
    return int(text) if field == "t_cap" else value


def load_uswtdb_csv(source: bytes) -> USWTDBData:
    """Load local UTF-8 CSV bytes matching the release 3.2 field contract.

    All supported headers are required; other columns are not exposed. Only
    empty optional cells mean missing. Invalid CSV, duplicate IDs, malformed
    numbers and non-finite values raise ValueError without returning partial data.
    No values are inferred, converted between units or fetched remotely.
    See docs/data/uswtdb.md for the supported schema and provenance limits.
    """
    reader = csv.reader(
        io.StringIO(source.decode("utf-8-sig"), newline=""), strict=True
    )
    turbines = []
    seen = set()
    try:
        header = next(reader, [])
        if len(header) != len(set(header)) or not set(
            IDENTIFIERS + MEASUREMENTS
        ).issubset(header):
            raise ValueError("invalid CSV header: require unique supported columns")
        for cells in reader:
            line = reader.line_num
            if len(cells) != len(header):
                raise ValueError(f"line {line}: inconsistent column count")
            row = dict(zip(header, cells))
            for field in ("case_id", "usgs_pr_id", "eia_id"):
                if (field == "case_id" or row[field] != "") and not INTEGER.fullmatch(
                    row[field]
                ):
                    raise ValueError(f"line {line}: invalid {field}")
            if row["case_id"] in seen:
                raise ValueError(f"line {line}: duplicate case_id")
            seen.add(row["case_id"])
            values = {field: row[field] or None for field in IDENTIFIERS}
            values.update(
                {field: _number(row[field], field, line) for field in MEASUREMENTS}
            )
            turbines.append(USWTDBTurbine(**values))
    except csv.Error as error:
        raise ValueError(f"line {reader.line_num}: malformed CSV") from error
    if not turbines:
        raise ValueError("CSV contains no turbine records")
    return USWTDBData(RELEASE, hashlib.sha256(source).hexdigest(), tuple(turbines))
