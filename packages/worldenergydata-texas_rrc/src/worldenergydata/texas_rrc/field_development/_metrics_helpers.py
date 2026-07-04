"""Scalar, date, and ranking helpers for field-development metrics."""

from __future__ import annotations

from typing import Any

import pandas as pd


def median_valid_days(pairs: list[tuple[pd.Timestamp, pd.Timestamp]]) -> float | pd.NA:
    values = [(end - start).days for start, end in pairs if end >= start]
    return float(pd.Series(values).median()) if values else pd.NA


def date_pairs(
    frame: pd.DataFrame,
    start_column: str,
    end_column: str,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    pairs = []
    for _, row in frame.iterrows():
        start = to_timestamp(row.get(start_column))
        end = to_timestamp(row.get(end_column))
        if start is not None and end is not None:
            pairs.append((start, end))
    return pairs


def valid_dates(values: pd.Series) -> list[pd.Timestamp]:
    dates = [to_timestamp(value) for value in values]
    return [value for value in dates if value is not None]


def to_timestamp(value: Any) -> pd.Timestamp | None:
    if not has_value(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed


def month_start(value: Any) -> pd.Timestamp | None:
    if not has_value(value):
        return None
    parsed = pd.to_datetime(f"{value}-01", errors="coerce")
    return None if pd.isna(parsed) else parsed


def horizontal_share(row: pd.Series, well_count: int) -> float | pd.NA:
    count = int_value(row.get("horizontal_well_count"), 0)
    count += int_value(row.get("directional_well_count"), 0)
    return ratio(count, well_count)


def pdq_water_or_well_count_gap(quality: dict[str, object]) -> bool:
    gaps = quality.get("metric_gaps", [])
    return bool(set(gaps).intersection({"water_bbl", "well_count"}))


def operator_count(row: pd.Series, has_lifecycle: bool) -> float | pd.NA:
    if has_value(row.get("operator_count")):
        return number_or_na(row.get("operator_count"))
    if has_lifecycle and has_value(row.get("lifecycle_operator_count")):
        return number_or_na(row.get("lifecycle_operator_count"))
    return pd.NA


def coalesce_number(*values: Any) -> float | pd.NA:
    for value in values:
        number = number_or_na(value)
        if has_value(number):
            return number
    return pd.NA


def ratio(numerator: Any, denominator: Any) -> float | pd.NA:
    if not has_value(numerator) or not has_value(denominator):
        return pd.NA
    denominator_value = float(denominator)
    if denominator_value == 0:
        return pd.NA
    return float(numerator) / denominator_value


def rank_desc(values: pd.Series) -> pd.Series:
    return values.rank(ascending=False, method="min", na_option="bottom").astype(
        "Int64"
    )


def count_text(values: pd.Series, predicate) -> int:
    return sum(predicate(str(value).upper()) for value in values if has_value(value))


def count_values(values: pd.Series) -> int:
    return sum(has_value(value) for value in values)


def unique_count(values: pd.Series) -> int:
    return len({str(value) for value in values if has_value(value)})


def profile_text(group: pd.DataFrame) -> pd.Series:
    return group["wellbore_profile"].astype(str) + " " + group["well_type"].astype(str)


def active_status(value: str) -> bool:
    return any(
        token in value for token in ("PRODUCING", "ACTIVE", "FLOWING", "SHUT IN")
    )


def plugged_status(value: str) -> bool:
    return "PLUG" in value


def horizontal(value: str) -> bool:
    return "HORIZONTAL" in value or " HZ" in f" {value}"


def directional(value: str) -> bool:
    return "DIRECTIONAL" in value or " DIR" in f" {value}"


def first_value(values: pd.Series) -> Any:
    for value in values:
        if has_value(value):
            return value
    return pd.NA


def first_present(*values: Any) -> Any:
    for value in values:
        if has_value(value):
            return value
    return pd.NA


def number_or_na(value: Any) -> float | pd.NA:
    if not has_value(value):
        return pd.NA
    try:
        return float(value)
    except (TypeError, ValueError):
        return pd.NA


def int_value(value: Any, default: int) -> int:
    if not has_value(value):
        return default
    return int(value)


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if not has_value(value):
        return False
    return str(value).strip().upper() in {"TRUE", "T", "Y", "YES", "1"}


def value_or_na(value: Any) -> Any:
    return value if has_value(value) else pd.NA


def zero(value: Any) -> float:
    return 0.0 if not has_value(value) else float(value)


def has_value(value: Any) -> bool:
    if value is None or value is pd.NA:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return str(value) != ""


def ensure_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        if column not in frame:
            frame[column] = pd.NA
