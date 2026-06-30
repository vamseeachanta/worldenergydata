"""Quality checks for Texas RRC lifecycle spine outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

import pandas as pd


@dataclass(frozen=True)
class LifecycleQualityReport:
    """Aggregate quality counts for one lifecycle spine build."""

    row_count: int
    duplicate_api14: int
    missing_field_id: int
    missing_lease_id: int
    missing_operator_id: int
    invalid_coordinates: int
    impossible_dates: int
    permit_without_wellbore: int
    completion_without_wellbore: int
    wellbore_without_completion: int
    source_gaps: Sequence[str]


def assess_lifecycle_quality(
    spine: pd.DataFrame,
    source_gaps: Sequence[str] = (),
) -> LifecycleQualityReport:
    """Assess lifecycle spine quality and attach row-level flags."""
    row_flags = [_flags_for_row(row) for _, row in spine.iterrows()]
    spine["quality_flags"] = ["|".join(flags) for flags in row_flags]
    duplicate_values = spine["api14"].duplicated().sum() if "api14" in spine else 0
    return LifecycleQualityReport(
        row_count=len(spine),
        duplicate_api14=int(duplicate_values),
        missing_field_id=_count_flag(row_flags, "missing_field_id"),
        missing_lease_id=_count_flag(row_flags, "missing_lease_id"),
        missing_operator_id=_count_flag(row_flags, "missing_operator_id"),
        invalid_coordinates=_count_flag(row_flags, "invalid_coordinates"),
        impossible_dates=_count_flag(row_flags, "impossible_dates"),
        permit_without_wellbore=_count_flag(row_flags, "permit_without_wellbore"),
        completion_without_wellbore=_count_flag(
            row_flags, "completion_without_wellbore"
        ),
        wellbore_without_completion=_count_flag(row_flags, "wellbore_without_completion"),
        source_gaps=tuple(source_gaps),
    )


def _flags_for_row(row: pd.Series) -> list[str]:
    flags = []
    _append_missing_id_flags(row, flags)
    if _invalid_coordinates(row):
        flags.append("invalid_coordinates")
    if _impossible_dates(row):
        flags.append("impossible_dates")
    _append_source_gap_flags(row, flags)
    return flags


def _append_missing_id_flags(row: pd.Series, flags: list[str]) -> None:
    for column, flag in (
        ("field_number", "missing_field_id"),
        ("lease_number", "missing_lease_id"),
        ("operator_number", "missing_operator_id"),
    ):
        if not _has_value(row.get(column)):
            flags.append(flag)


def _append_source_gap_flags(row: pd.Series, flags: list[str]) -> None:
    has_wellbore = bool(row.get("has_wellbore"))
    if bool(row.get("has_permit")) and not has_wellbore:
        flags.append("permit_without_wellbore")
    if bool(row.get("has_completion")) and not has_wellbore:
        flags.append("completion_without_wellbore")
    if has_wellbore and not bool(row.get("has_completion")):
        flags.append("wellbore_without_completion")


def _invalid_coordinates(row: pd.Series) -> bool:
    latitude = _to_float(row.get("latitude"))
    longitude = _to_float(row.get("longitude"))
    if latitude is None or longitude is None:
        return False
    return not (25.84 <= latitude <= 36.50 and -106.65 <= longitude <= -93.51)


def _impossible_dates(row: pd.Series) -> bool:
    comparisons = (
        ("permit_issued_date", "spud_date"),
        ("spud_date", "completion_date"),
        ("completion_date", "plug_date"),
    )
    for start_column, end_column in comparisons:
        start = _to_date(row.get(start_column))
        end = _to_date(row.get(end_column))
        if start and end and start > end:
            return True
    return False


def _to_date(value) -> date | None:
    if not _has_value(value):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _to_float(value) -> float | None:
    if not _has_value(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_value(value) -> bool:
    return value is not None and value == value and str(value) != ""


def _count_flag(row_flags: list[list[str]], flag: str) -> int:
    return sum(flag in flags for flags in row_flags)
