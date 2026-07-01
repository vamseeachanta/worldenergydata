"""Parse official Texas RRC brace-delimited completion packet data."""

from __future__ import annotations

from datetime import date

import pandas as pd

COMPLETION_FORM_RECORDS = {"G-1", "W-2"}
FORM_COMPLETION_DATE_INDEX = {"G-1": 18, "W-2": 27}
FORM_FIELD_MAP = {
    "G-1": {
        "operator_name": 14,
        "lease_name": 24,
        "lease_number": 25,
    },
    "W-2": {
        "operator_name": 23,
        "lease_name": 33,
        "lease_number": 34,
    },
}


def looks_like_completion_packet_text(text: str) -> bool:
    """Return True for official completion packetData brace records."""
    first_line = _first_content_line(text)
    return bool(first_line and "{" in first_line)


def read_completion_packet_text(text: str) -> pd.DataFrame:
    """Read official W-2/G-1 packetData text into lifecycle completion rows."""
    rows: list[dict[str, str]] = []
    context: dict[str, str] = {}
    for raw_line in text.splitlines():
        fields = [part.strip() for part in raw_line.rstrip("\r\n").split("{")]
        record_type = fields[0] if fields else ""
        if record_type == "PACKET":
            context = _packet_context(fields)
            continue
        if record_type not in COMPLETION_FORM_RECORDS:
            continue
        row = _form_row(record_type, fields, context)
        if row:
            rows.append(row)
    return pd.DataFrame(rows)


def _first_content_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _packet_context(fields: list[str]) -> dict[str, str]:
    context = {
        "api_number": _field(fields, 6),
        "operator_number": _field(fields, 5),
        "lease_number": _field(fields, 8),
        "field_number": _field(fields, 25),
        "district": _field(fields, 27),
        "field_name": _field(fields, 29),
        "packet_completion_date": _parse_date(_field(fields, 21)),
    }
    return {key: value for key, value in context.items() if value}


def _form_row(
    record_type: str,
    fields: list[str],
    context: dict[str, str],
) -> dict[str, str]:
    row = dict(context)
    row.pop("packet_completion_date", None)
    row.update(_form_context(record_type, fields))
    row["form_type"] = record_type
    completion_date = _form_completion_date(record_type, fields, context)
    if completion_date:
        row["completion_date"] = completion_date
    if not _valid_api(row.get("api_number", "")):
        return {}
    return row


def _form_context(record_type: str, fields: list[str]) -> dict[str, str]:
    mapped = {}
    for column, index in FORM_FIELD_MAP.get(record_type, {}).items():
        value = _field(fields, index)
        if value:
            mapped[column] = value
    return mapped


def _form_completion_date(
    record_type: str,
    fields: list[str],
    context: dict[str, str],
) -> str:
    for index in (FORM_COMPLETION_DATE_INDEX[record_type], 4):
        value = _parse_date(_field(fields, index))
        if value:
            return value
    return context.get("packet_completion_date", "")


def _field(fields: list[str], index: int) -> str:
    if index >= len(fields):
        return ""
    return fields[index].strip()


def _valid_api(value: str) -> bool:
    return len(value) == 8 and value.isdigit()


def _parse_date(value: str) -> str:
    text = value.strip()
    if not text or text == "00000000":
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    if len(text) == 8 and text.isdigit():
        try:
            return date(int(text[:4]), int(text[4:6]), int(text[6:8])).isoformat()
        except ValueError:
            return ""
    if "/" in text:
        parts = text.split("/")
        if len(parts) != 3:
            return ""
        try:
            month, day, year = (int(part) for part in parts)
            return date(year, month, day).isoformat()
        except ValueError:
            return ""
    return ""


__all__ = [
    "looks_like_completion_packet_text",
    "read_completion_packet_text",
]
