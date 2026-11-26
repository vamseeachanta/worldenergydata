"""Offline structural inspection of the UNMIG wide-month concession CSV.

Schema basis: docs/data/eu-tail-source-assessment.json, italy_unmig header.
Numeric tokens remain source text; structure does not establish field readiness.
"""

import csv
import hashlib
import io
import re

from worldenergydata.source_assessment import SourceCapabilities, assess_source

HEADER = (
    "Minerale;Anno;Ub;Titolo;Operatore;Regione;Gennaio;Febbraio;Marzo;Aprile;"
    "Maggio;Giugno;Luglio;Agosto;Settembre;Ottobre;Novembre;Dicembre;Totale"
).split(";")
MONTHS = HEADER[6:18]


def inspect_csv(data: bytes, *, expected_sha256: str, max_bytes: int) -> dict:
    """Inspect all records after byte-cap and expected-digest verification.

    Raise ValueError on malformed bytes, schema or records; no partial valid
    report is returned. Locations are physical CSV line numbers (header = 1).
    Duplicate identities use all six context cells, without normalization.
    Only exactly empty month cells count as empty; whitespace remains a token.
    Every month and total token is retained without numeric interpretation.
    The caller owns acquisition, provenance, retention and intended-use checks.
    """
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    if not isinstance(data, bytes):
        raise ValueError("data must be bytes")
    if len(data) > max_bytes:
        raise ValueError("input exceeds byte cap")
    if not isinstance(expected_sha256, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", expected_sha256
    ):
        raise ValueError("expected digest must be SHA-256 hexadecimal")
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256.lower():
        raise ValueError("input digest mismatch")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("input is not UTF-8") from error

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
    identities: dict[tuple[str, ...], list[int]] = {}
    numeric_rows = []
    years = []
    minerals = set()
    empty_months = dict.fromkeys(MONTHS, 0)
    row_start = 1
    try:
        header = next(reader, None)
        if header != HEADER:
            raise ValueError("row 1: header differs from the expected schema")
        while True:
            row_start = reader.line_num + 1
            record = next(reader, None)
            if record is None:
                break
            if len(record) != len(HEADER):
                raise ValueError(f"row {row_start}: width must be 19 columns")
            if any("\x00" in cell for cell in record):
                raise ValueError(f"row {row_start}: null character in record")
            if not re.fullmatch(r"[0-9]{4}", record[1]) or record[1] == "0000":
                raise ValueError(f"row {row_start}: year must be four calendar digits")
            if not record[0].strip() or not record[3].strip():
                raise ValueError(f"row {row_start}: required mineral or title is empty")
            years.append(int(record[1]))
            minerals.add(record[0])
            identities.setdefault(tuple(record[:6]), []).append(row_start)
            for name, token in zip(MONTHS, record[6:18]):
                empty_months[name] += token == ""
            numeric_rows.append(
                {
                    "row": row_start,
                    "line_end": reader.line_num,
                    "months": record[6:18],
                    "total": record[18],
                }
            )
    except csv.Error as error:
        raise ValueError(f"row {row_start}: malformed CSV") from error
    if not numeric_rows:
        raise ValueError("no data records")

    assessment = assess_source(
        SourceCapabilities(
            production_granularity="concession",
            production_frequency="monthly",
            production_verified=True,
            field_metadata="absent",
            reuse="unspecified",
        )
    )
    return {
        "sha256": digest,
        "byte_count": len(data),
        "header": list(HEADER),
        "structural_status": "VALID",
        "row_count": len(numeric_rows),
        "year_range": [min(years), max(years)],
        "mineral_categories": sorted(minerals),
        "empty_month_counts": empty_months,
        "duplicates": [
            {"identity": list(identity), "rows": rows}
            for identity, rows in identities.items()
            if len(rows) > 1
        ],
        "raw_numeric_rows": numeric_rows,
        "granularity": "concession",
        "numeric_interpretation": "NOT_EVALUATED",
        "decision": assessment.decision,
        "fdas_production": assessment.fdas_production,
    }
