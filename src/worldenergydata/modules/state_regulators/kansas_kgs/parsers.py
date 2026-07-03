"""Parsers for the two KGS bulk files (formats verified 2026-07-02).

Both files are quoted CSV. The proration file carries a known defect: the
header row wrapped during KGS's export, leaving a stray continuation
fragment (``RES","DIFFERENT","COEFF"``) on line 2 that must be skipped.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

PRORATION_COLUMNS = [
    "WELL_KID",
    "LEASE",
    "API_NUMBER",
    "OPERATOR",
    "TOWNSHIP",
    "TWN_DIR",
    "RANGE",
    "RANGE_DIR",
    "SECTION",
    "LATITUDE",
    "LONGITUDE",
    "YEAR",
    "ACREAGE",
    "SHUT_IN_PRESS",
    "WORKING_PRES",
    "DAILY_RATE",
    "OPEN_FLOW",
    "ADJ_DELIVER",
    "WATER_PROD",
    "METER_PRES",
    "DIFFERENT",
    "COEFF",
]

PRORATION_NUMERIC = [
    "LATITUDE",
    "LONGITUDE",
    "YEAR",
    "ACREAGE",
    "SHUT_IN_PRESS",
    "WORKING_PRES",
    "DAILY_RATE",
    "OPEN_FLOW",
    "ADJ_DELIVER",
    "WATER_PROD",
    "METER_PRES",
    "DIFFERENT",
    "COEFF",
]

WELLS_NUMERIC = ["LATITUDE", "LONGITUDE", "ELEVATION", "DEPTH"]
WELLS_DATES = ["PERMIT", "SPUD", "COMPLETION", "PLUGGING", "MODIFIED"]


def _is_header_continuation(line: str) -> bool:
    """The wrapped header fragment starts mid-token, e.g. ``RES","DIFFERENT...``."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith('"')


def read_proration_pressures(path: str | Path) -> pd.DataFrame:
    """Read kansas_proration_pressures.txt into a typed DataFrame.

    Skips the header row and any wrapped-header continuation lines, then
    parses the quoted data rows against the fixed 22-column schema.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    data_start = 1
    while data_start < len(lines) and _is_header_continuation(lines[data_start]):
        data_start += 1
    frame = pd.read_csv(
        io.StringIO("".join(lines[data_start:])),
        header=None,
        names=PRORATION_COLUMNS,
        dtype=str,
        quotechar='"',
        skipinitialspace=True,
    )
    for column in PRORATION_NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["YEAR"] = frame["YEAR"].astype("Int64")
    return frame


def read_wells_master(
    path: str | Path, zip_member: str = "ks_wells.txt"
) -> pd.DataFrame:
    """Read ks_wells.zip (or an extracted ks_wells.txt) into a typed DataFrame."""
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive, archive.open(zip_member) as member:
            frame = pd.read_csv(member, dtype=str, quotechar='"')
    else:
        frame = pd.read_csv(path, dtype=str, quotechar='"')
    for column in WELLS_NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in WELLS_DATES:
        frame[column] = pd.to_datetime(
            frame[column], format="%d-%b-%Y", errors="coerce"
        )
    return frame
