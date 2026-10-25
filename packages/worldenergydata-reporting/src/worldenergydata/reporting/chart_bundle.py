"""Typed, provenance-bearing JSON/CSV chart bundles.

``None`` is the only missing input value: callers explicitly declare the
``missing_values="null"`` policy, producing JSON null and CSV blanks. NaN and
infinity are rejected, not treated as missing. Series and drawn limits share
the chart's quantity and unit. Limit citations describe each drawn marker;
the library does not supply engineering or regulatory limits.

``write_chart_bundle(chart, json_path)`` validates and serializes the entire
payload before touching either output. ``validate_chart_bundle(json_path)``
reads both files and checks their provenance, columns, row counts and values.
File-system failures can interrupt a write; pairwise atomicity is not promised.
CSV fields must fit the active ``csv.field_size_limit()`` in decoded characters,
including column names. Configure that process-wide limit before constructing,
writing or reading bundles, and keep it unchanged during those operations.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

Number = int | float
XValue = str | Number | None

# RFC 3339 sections 5.6/5.7: qualified calendar dates and UTC timestamps.
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_UTC = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)",
    re.ASCII,
)
# FIPS 180-4, SHA-256: 256 bits / 4 bits per hexadecimal digit = 64 digits.
_SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)
_CSV_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.csv", re.ASCII)


@dataclass(frozen=True)
class ChartSource:
    """Source identity and full calendar date (YYYY-MM-DD)."""

    name: str
    url: str
    date: str


@dataclass(frozen=True)
class ChartSeries:
    """A named numeric series aligned with the x values."""

    name: str
    values: tuple[Number | None, ...]


@dataclass(frozen=True)
class DrawnLimit:
    """A numeric marker in the chart's unit, with its own citation."""

    label: str
    value: Number
    citation: str


@dataclass(frozen=True)
class ChartBundle:
    """Chart schema; use from_dict for validation and immutable sequences.

    The digest identifies the upstream input bytes. Their authenticity and
    availability cannot be established from the chart files alone.
    """

    chart_id: str
    headline: str
    quantity: str
    unit: str
    x_variable: str
    x_values: tuple[XValue, ...]
    series: tuple[ChartSeries, ...]
    source: ChartSource
    retrieved_at: str
    input_sha256: str
    limits: tuple[DrawnLimit, ...]
    csv_name: str
    missing_values: Literal["null"]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ChartBundle:
        """Validate a complete payload without silently coercing its values."""
        if not isinstance(payload, dict):
            raise ValueError("Chart payload must be an object")
        data = dict(payload)
        try:
            data["source"] = _record(ChartSource, data["source"])
            data["x_values"] = tuple(_sequence(data["x_values"], "x_values"))
            data["series"] = tuple(
                replace(
                    series,
                    values=tuple(_sequence(series.values, "series values")),
                )
                for series in (
                    _record(ChartSeries, item)
                    for item in _sequence(data["series"], "series")
                )
            )
            data["limits"] = tuple(
                _record(DrawnLimit, item)
                for item in _sequence(data["limits"], "limits")
            )
            chart = cls(**data)
        except (KeyError, TypeError) as exc:
            raise ValueError("Missing or unknown chart schema field") from exc
        _validate(chart)
        return chart


def _record(record_type, value):
    if not isinstance(value, dict):
        raise ValueError(f"{record_type.__name__} must be an object")
    return record_type(**value)


def _sequence(value, field):
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    return value


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonblank text")


def _number(value, field):
    # RFC 8259 section 6 excludes NaN and Infinity. bool is not a chart number.
    if type(value) not in (int, float) or (
        isinstance(value, float) and not math.isfinite(value)
    ):
        raise ValueError(f"{field} must be a finite number")


def _validate_provenance(chart):
    source = chart.source
    for field in ("name", "url", "date"):
        _text(getattr(source, field), f"source.{field}")
    try:
        url = urlsplit(source.url)
        if url.scheme not in ("http", "https") or not url.hostname:
            raise ValueError("source.url must be an HTTP(S) URL")
        if not _DATE.fullmatch(source.date):
            raise ValueError("source.date must be YYYY-MM-DD")
        date.fromisoformat(source.date)
        if not _UTC.fullmatch(chart.retrieved_at):
            raise ValueError("retrieved_at must be a qualified UTC timestamp")
        timestamp = datetime.fromisoformat(chart.retrieved_at.replace("Z", "+00:00"))
        # RFC 3339 section 4.2: UTC has a zero offset.
        if timestamp.utcoffset() != timedelta(0):
            raise ValueError("retrieved_at must be UTC")
    except ValueError as exc:
        raise ValueError(f"Invalid chart provenance: {exc}") from exc
    if not _SHA256.fullmatch(chart.input_sha256):
        raise ValueError("input_sha256 must contain exactly 64 lowercase hex digits")


def _validate(chart):
    for field in (
        "chart_id",
        "headline",
        "quantity",
        "unit",
        "x_variable",
        "retrieved_at",
        "input_sha256",
        "csv_name",
    ):
        _text(getattr(chart, field), field)
    _validate_provenance(chart)
    if not _CSV_NAME.fullmatch(chart.csv_name):
        raise ValueError("csv_name must be a plain sibling .csv filename")
    if chart.missing_values != "null":
        raise ValueError("missing_values must explicitly declare 'null'")
    if not chart.x_values or not chart.series:
        raise ValueError("Chart must contain x values and at least one series")
    for value in chart.x_values:
        if isinstance(value, str):
            _text(value, "x value")
        elif value is not None:
            _number(value, "x value")
    names = {chart.x_variable}
    for series in chart.series:
        _text(series.name, "series name")
        if series.name in names:
            raise ValueError("CSV column names must be unique")
        names.add(series.name)
        if len(series.values) != len(chart.x_values):
            raise ValueError("Series lengths must match x values")
        for value in series.values:
            if value is not None:
                _number(value, "series value")
    for limit in chart.limits:
        _text(limit.label, "limit label")
        _text(limit.citation, "limit citation")
        _number(limit.value, "limit value")
    field_limit = csv.field_size_limit()
    for row in _csv_rows(chart):
        if any(len("" if value is None else str(value)) > field_limit for value in row):
            raise ValueError("CSV field size exceeds csv.field_size_limit()")


def _csv_rows(chart):
    yield [chart.x_variable, *(series.name for series in chart.series)]
    yield from zip(chart.x_values, *(series.values for series in chart.series))


def write_chart_bundle(chart: ChartBundle, json_path: str | Path) -> tuple[Path, Path]:
    """Write a validated chart and its named sibling CSV; return both paths."""
    if not isinstance(chart, ChartBundle):
        raise ValueError("chart must be a ChartBundle")
    chart = ChartBundle.from_dict(asdict(chart))
    json_path = Path(json_path)
    if json_path.suffix != ".json":
        raise ValueError("Chart path must end in .json")
    csv_path = json_path.with_name(chart.csv_name)
    json_text = json.dumps(asdict(chart), indent=2, allow_nan=False) + "\n"
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerows(_csv_rows(chart))
    csv_text = stream.getvalue()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(csv_text, encoding="utf-8", newline="")
    json_path.write_text(json_text, encoding="utf-8")
    return json_path, csv_path


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _json_float(token):
    value = float(token)
    # The model and both writers use float's shortest decimal spelling. Reject
    # rounding/underflow rather than returning a different validated value.
    if not math.isfinite(value) or Decimal(str(value)) != Decimal(token):
        raise ValueError(
            "JSON number changes value in the supported numeric representation"
        )
    return value


def _matches(cell, value):
    if value is None:
        return cell == ""
    if isinstance(value, str):
        return cell == value
    try:
        number = Decimal(cell)
        return number.is_finite() and number == Decimal(str(value))
    except InvalidOperation:
        return False


def validate_chart_bundle(json_path: str | Path) -> ChartBundle:
    """Read both files and reject any schema, provenance or table mismatch.

    Numeric cells are compared as exact decimals, with no rounding tolerance.
    Different spellings of the same number (for example, 1 and 1.0) agree.
    JSON decimals must retain their value in the returned float's decimal
    spelling and its JSON/CSV re-export; otherwise the bundle is rejected.
    """
    json_path = Path(json_path)
    try:
        text = json_path.read_text(encoding="utf-8")
        payload = json.loads(
            text, object_pairs_hook=_unique_object, parse_float=_json_float
        )
        chart = ChartBundle.from_dict(payload)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Invalid chart JSON: {exc}") from exc
    try:
        with json_path.with_name(chart.csv_name).open(
            encoding="utf-8", newline=""
        ) as stream:
            rows = list(csv.reader(stream, strict=True))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"Invalid chart CSV: {exc}") from exc
    header = [chart.x_variable, *(series.name for series in chart.series)]
    if not rows or rows[0] != header:
        raise ValueError("CSV columns do not match chart variables")
    data_rows = rows[1:]
    if len(data_rows) != len(chart.x_values):
        raise ValueError("CSV row count does not match chart values")
    expected = zip(chart.x_values, *(series.values for series in chart.series))
    for row, values in zip(data_rows, expected):
        if len(row) != len(header) or any(
            not _matches(cell, value) for cell, value in zip(row, values)
        ):
            raise ValueError("CSV values do not match chart values")
    return chart
