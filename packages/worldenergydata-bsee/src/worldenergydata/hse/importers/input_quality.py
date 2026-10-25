"""Pure, caller-configured preflight for raw incident/investigation records.

No production code set, date window, severity or disposition is inferred.
Each observed defect contributes one table row. Counts are affected source
records, once per defect per record; every member of a repeated nonmissing key
is counted as a duplicate. Overlapping totals are not mutually exclusive row
dispositions. Rules describe policy only: input records are never removed.

Field mappings use the roles ``key``, ``date``, ``code`` and ``source_row_id``.
Optional ``interval_start`` and ``interval_end`` must be supplied together;
otherwise reversed intervals remain unchecked. All mapped dates, including
explicit interval endpoints, are checked against the inclusive caller window.
Dates accept calendar date/datetime objects or strings parsed with the caller's
``date_format``. Datetimes use their supplied calendar date without conversion.
Keys and source-row ids accept nonblank strings or integers (excluding booleans).
Missing keys include null, blank and floating NaN. Codes match exact strings;
missing and nontext codes are unknown. No whitespace or case is normalized.

The table sorts defect names and uses the lexicographically smallest source-row
id (integers rendered as strings) as the example, independently of input order.
Only observed defects need rules, but every supplied rule is validated, including
unused entries. Unknown defects and dispositions fail closed before export.
"""

from __future__ import annotations

import csv
import io
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from pathlib import Path
from typing import TypedDict

_DEFECTS = frozenset(
    {
        "duplicate_key",
        "missing_key",
        "invalid_date",
        "out_of_window_date",
        "unknown_code",
        "reversed_interval",
    }
)
_DISPOSITIONS = frozenset({"kept", "dropped", "flagged"})
_REQUIRED_FIELDS = frozenset({"key", "date", "code", "source_row_id"})
_INTERVAL_FIELDS = frozenset({"interval_start", "interval_end"})
_COLUMNS = ("defect", "count", "example_source_row_id", "rule")


class QualityRow(TypedDict):
    """A defect count, a traceable example and the caller's disposition rule."""

    defect: str
    count: int
    example_source_row_id: str
    rule: str


def _validate_policy(fields, date_window, date_format, allowed_codes, rules):
    if not isinstance(fields, Mapping) or not _REQUIRED_FIELDS <= fields.keys():
        raise ValueError("fields must map key, date, code and source_row_id")
    if fields.keys() - (_REQUIRED_FIELDS | _INTERVAL_FIELDS):
        raise ValueError("Unknown field mapping role")
    if any(not isinstance(name, str) or not name.strip() for name in fields.values()):
        raise ValueError("Mapped field names must be nonblank strings")
    interval_roles = fields.keys() & _INTERVAL_FIELDS
    if interval_roles and interval_roles != _INTERVAL_FIELDS:
        raise ValueError("Supply both interval fields or neither")
    # The date window has exactly a lower and an upper calendar bound.
    if (
        not isinstance(date_window, (tuple, list))
        or len(date_window) != 2
        or any(type(bound) is not date for bound in date_window)
    ):
        raise ValueError("date_window must contain two calendar dates")
    lower, upper = date_window
    if lower > upper:
        raise ValueError("date_window lower bound must not exceed upper bound")
    if not isinstance(date_format, str) or not date_format.strip():
        raise ValueError("date_format must be a nonblank parsing format")
    if isinstance(allowed_codes, (str, bytes, Mapping)):
        raise ValueError("allowed_codes must be a collection of exact string tokens")
    try:
        codes = frozenset(allowed_codes)
    except TypeError as exc:
        raise ValueError("allowed_codes must contain string tokens") from exc
    if any(not isinstance(code, str) or not code.strip() for code in codes):
        raise ValueError("allowed_codes must contain nonblank string tokens")
    if not isinstance(rules, Mapping):
        raise ValueError("rules must map defects to dispositions")
    for defect, disposition in rules.items():
        if defect not in _DEFECTS:
            raise ValueError("Unknown defect in rules")
        if not isinstance(disposition, str) or disposition not in _DISPOSITIONS:
            raise ValueError("Disposition must be kept, dropped or flagged")
    return codes


def _missing_key(value: object) -> bool:
    return (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, float) and math.isnan(value))
    )


def _identity(value: object, role: str) -> str | int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"{role} must be a nonblank string or integer")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{role} must be a nonblank string or integer")
    return value


def _parse_date(value: object, date_format: str) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass
    return None


def summarize_input_quality(
    records: Iterable[Mapping[str, object]],
    *,
    fields: Mapping[str, str],
    date_window: tuple[date, date],
    date_format: str,
    allowed_codes: Iterable[str],
    rules: Mapping[str, str],
) -> list[QualityRow]:
    """Inspect supplied raw records without mutation or I/O.

    Missing/invalid source ids or unsupported key types raise rather than invent
    an example id. A single-pass iterable is supported. Malformed policy and any
    observed defect without a rule raise ValueError; no partial table is returned.
    """
    codes = _validate_policy(fields, date_window, date_format, allowed_codes, rules)
    counts: Counter[str] = Counter()
    examples: dict[str, str] = {}
    key_counts: Counter[str | int] = Counter()
    key_examples: dict[str | int, str] = {}
    date_roles = ["date"]
    if "interval_start" in fields:
        date_roles.extend(["interval_start", "interval_end"])
    lower, upper = date_window

    def record_defect(defect: str, source_id: str, count: int = 1) -> None:
        # One occurrence per affected source record, per the table contract.
        if defect not in _DEFECTS:
            raise ValueError("Unknown detected defect")
        if defect not in rules:
            raise ValueError(f"No disposition rule for {defect}")
        counts[defect] += count
        examples[defect] = min(examples.get(defect, source_id), source_id)

    for row in records:
        if not isinstance(row, Mapping):
            raise ValueError("Each source record must be a mapping")
        source_id = str(_identity(row.get(fields["source_row_id"]), "source_row_id"))
        key = row.get(fields["key"])
        if _missing_key(key):
            record_defect("missing_key", source_id)
        else:
            key = _identity(key, "key")
            key_counts[key] += 1
            key_examples[key] = min(key_examples.get(key, source_id), source_id)

        dates = {
            role: _parse_date(row.get(fields[role]), date_format) for role in date_roles
        }
        if any(value is None for value in dates.values()):
            record_defect("invalid_date", source_id)
        if any(
            value is not None and not lower <= value <= upper
            for value in dates.values()
        ):
            record_defect("out_of_window_date", source_id)
        if "interval_start" in dates:
            start, end = dates["interval_start"], dates["interval_end"]
            if start is not None and end is not None and start > end:
                record_defect("reversed_interval", source_id)

        code = row.get(fields["code"])
        if not isinstance(code, str) or code not in codes:
            record_defect("unknown_code", source_id)

    for key, count in key_counts.items():
        # More than one record sharing a key makes every member a duplicate.
        if count > 1:
            record_defect("duplicate_key", key_examples[key], count)

    return [
        QualityRow(
            defect=defect,
            count=counts[defect],
            example_source_row_id=examples[defect],
            rule=rules[defect],
        )
        for defect in sorted(counts)
    ]


def export_input_quality(
    records: Iterable[Mapping[str, object]],
    output_dir: str | Path,
    *,
    fields: Mapping[str, str],
    date_window: tuple[date, date],
    date_format: str,
    allowed_codes: Iterable[str],
    rules: Mapping[str, str],
) -> tuple[Path, Path]:
    """Write the same validated table as UTF-8 CSV and JSON in a caller directory.

    Validation and serialization finish before creating directories or touching
    existing output. Files are named input_quality.csv and input_quality.json.
    CSV counts are decimal strings; JSON counts are integers. Filesystem failures
    propagate; the two writes are not a filesystem transaction.
    """
    table = summarize_input_quality(
        records,
        fields=fields,
        date_window=date_window,
        date_format=date_format,
        allowed_codes=allowed_codes,
        rules=rules,
    )
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=_COLUMNS)
    writer.writeheader()
    writer.writerows(table)
    json_text = json.dumps(table, ensure_ascii=False, allow_nan=False) + "\n"
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "input_quality.csv"
    json_path = directory / "input_quality.json"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(csv_buffer.getvalue())
    json_path.write_text(json_text, encoding="utf-8")
    return csv_path, json_path
