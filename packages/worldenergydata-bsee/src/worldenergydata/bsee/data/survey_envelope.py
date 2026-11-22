"""Lossless station values for one retained, headerless BSEE survey.

Schema v1 follows the 13-field dsptsdelimit column order in well_data.py.
This boundary validates storage inputs; it does not qualify trajectories.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import re
from datetime import datetime
from urllib.parse import urlsplit

COLUMNS = (
    "API_WELL_NUMBER",
    "INCL_ANG_DEG_VAL",
    "INCL_ANG_MIN_VAL",
    "SURVEY_POINT_MD",
    "WELL_N_S_CODE",
    "DIR_DEG_VAL",
    "DIR_MINS_VAL",
    "WELL_E_W_CODE",
    "SURVEY_POINT_TVD",
    "DELTA_X",
    "DELTA_Y",
    "SURF_LONGITUDE",
    "SURF_LATITUDE",
)
OPTIONAL_NUMBERS = frozenset(COLUMNS[9:])
TEXT_FIELDS = frozenset(("API_WELL_NUMBER", "WELL_N_S_CODE", "WELL_E_W_CODE"))
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def build_survey_envelope(
    raw: bytes,
    *,
    api12: str,
    source_url: str,
    retrieved_at: str,
    declared_sha256: str,
    data_kind: str,
) -> dict[str, object]:
    """Verify and parse the same immutable bytes without I/O or unit conversion.

    Identifiers must match a declared 12-digit string. Nonempty decoded CSV
    cells retain their spelling and padding; optional blank numeric cells are
    null. Numeric checks use Python float syntax (no locale/grouping handling).
    Source rows count CSV records, including records with quoted newlines.
    retrieved_at must be an explicit offset-aware ISO timestamp; no freshness
    or acquisition chronology is inferred from this caller-supplied metadata.
    """
    if not isinstance(raw, bytes):
        raise TypeError("raw must be immutable bytes")
    if not isinstance(api12, str) or not re.fullmatch(r"[0-9]{12}", api12):
        raise ValueError("api12 must be a 12-digit string")
    if not isinstance(source_url, str):
        raise ValueError("source_url must be an HTTP(S) URL")
    url = urlsplit(source_url)
    if url.scheme not in ("https", "http") or not url.hostname:
        raise ValueError("source_url must be an HTTP(S) URL")
    if data_kind not in ("source", "synthetic"):
        raise ValueError("data_kind must be source or synthetic")
    if not isinstance(retrieved_at, str) or not _TIMESTAMP.fullmatch(retrieved_at):
        raise ValueError("retrieved_at must include a time and UTC offset")
    try:
        datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("retrieved_at is not a valid timestamp") from error
    if not isinstance(declared_sha256, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", declared_sha256
    ):
        raise ValueError("A 64-hex SHA-256 digest is required")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != declared_sha256.lower():
        raise ValueError("Survey SHA-256 digest mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Survey must be UTF-8 CSV") from error
    stations = []
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        for number, row in enumerate(reader, start=1):
            if len(row) != len(COLUMNS):
                raise ValueError(f"CSV record {number} must contain 13 fields")
            values = dict(zip(COLUMNS, row))
            if values["API_WELL_NUMBER"].strip() != api12:
                raise ValueError(f"CSV record {number} has a different identifier")
            for column, allowed in (("WELL_N_S_CODE", "NS"), ("WELL_E_W_CODE", "EW")):
                if values[column].strip() not in tuple(allowed):
                    raise ValueError(f"CSV record {number} has an invalid direction")
            for column in COLUMNS:
                if column not in TEXT_FIELDS:
                    value = values[column]
                    if column in OPTIONAL_NUMBERS and not value.strip():
                        values[column] = None
                    else:
                        try:
                            finite = math.isfinite(float(value))
                        except ValueError as error:
                            raise ValueError(
                                f"CSV record {number}: {column} must be finite"
                            ) from error
                        if not finite:
                            raise ValueError(
                                f"CSV record {number}: {column} must be finite"
                            )
            stations.append({"source_row": number, "values": values})
    except csv.Error as error:
        raise ValueError(f"Malformed CSV record {len(stations) + 1}") from error
    if not stations:
        raise ValueError("Survey must contain at least one CSV record")
    return {
        "schema_version": 1,
        "source_schema": "bsee.dsptsdelimit.v1",
        "api12": api12,
        "data_kind": data_kind,
        "source": {"url": source_url, "retrieved_at": retrieved_at, "sha256": digest},
        "units": {
            "depth": "unresolved",
            "angle_degrees": "degree",
            "angle_minutes": "arcminute",
            "geographic_positions_and_differences": "degree",
        },
        "readiness": "not_qualified",
        "stations": stations,
    }
