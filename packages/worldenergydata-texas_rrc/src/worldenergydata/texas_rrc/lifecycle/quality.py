"""Quality checks for Texas RRC lifecycle spine outputs."""

from __future__ import annotations

from dataclasses import dataclass
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
    flags = pd.Series("", index=spine.index, dtype=object)
    missing_field_id = _append_flag(
        flags, _missing_mask(spine, "field_number"), "missing_field_id"
    )
    missing_lease_id = _append_flag(
        flags, _missing_mask(spine, "lease_number"), "missing_lease_id"
    )
    missing_operator_id = _append_flag(
        flags, _missing_mask(spine, "operator_number"), "missing_operator_id"
    )
    invalid_coordinates = _append_flag(
        flags, _invalid_coordinates_mask(spine), "invalid_coordinates"
    )
    impossible_dates = _append_flag(
        flags, _impossible_dates_mask(spine), "impossible_dates"
    )

    has_wellbore = _bool_mask(spine, "has_wellbore")
    has_permit = _bool_mask(spine, "has_permit")
    has_completion = _bool_mask(spine, "has_completion")
    permit_without_wellbore = _append_flag(
        flags, has_permit & ~has_wellbore, "permit_without_wellbore"
    )
    completion_without_wellbore = _append_flag(
        flags, has_completion & ~has_wellbore, "completion_without_wellbore"
    )
    wellbore_without_completion = _append_flag(
        flags, has_wellbore & ~has_completion, "wellbore_without_completion"
    )

    spine["quality_flags"] = flags
    duplicate_values = spine["api14"].duplicated().sum() if "api14" in spine else 0
    return LifecycleQualityReport(
        row_count=len(spine),
        duplicate_api14=int(duplicate_values),
        missing_field_id=missing_field_id,
        missing_lease_id=missing_lease_id,
        missing_operator_id=missing_operator_id,
        invalid_coordinates=invalid_coordinates,
        impossible_dates=impossible_dates,
        permit_without_wellbore=permit_without_wellbore,
        completion_without_wellbore=completion_without_wellbore,
        wellbore_without_completion=wellbore_without_completion,
        source_gaps=tuple(source_gaps),
    )


def _append_flag(flags: pd.Series, mask: pd.Series, flag: str) -> int:
    count = int(mask.sum())
    if count == 0:
        return 0
    existing = flags.loc[mask]
    separator = existing.ne("").map({True: "|", False: ""})
    flags.loc[mask] = existing + separator + flag
    return count


def _missing_mask(spine: pd.DataFrame, column: str) -> pd.Series:
    if column not in spine:
        return pd.Series(True, index=spine.index)
    values = spine[column].astype("string")
    return values.isna() | values.eq("")


def _invalid_coordinates_mask(spine: pd.DataFrame) -> pd.Series:
    latitude = _numeric_column(spine, "latitude")
    longitude = _numeric_column(spine, "longitude")
    has_coordinates = latitude.notna() & longitude.notna()
    in_bounds = latitude.between(25.84, 36.50) & longitude.between(-106.65, -93.51)
    return has_coordinates & ~in_bounds


def _impossible_dates_mask(spine: pd.DataFrame) -> pd.Series:
    result = pd.Series(False, index=spine.index)
    for start_column, end_column in (
        ("permit_issued_date", "spud_date"),
        ("spud_date", "completion_date"),
        ("completion_date", "plug_date"),
    ):
        start = _date_column(spine, start_column)
        end = _date_column(spine, end_column)
        result |= start.notna() & end.notna() & start.gt(end)
    return result


def _bool_mask(spine: pd.DataFrame, column: str) -> pd.Series:
    if column not in spine:
        return pd.Series(False, index=spine.index)
    return spine[column].astype("boolean").fillna(False).astype(bool)


def _numeric_column(spine: pd.DataFrame, column: str) -> pd.Series:
    if column not in spine:
        return pd.Series(pd.NA, index=spine.index, dtype="Float64")
    return pd.to_numeric(spine[column], errors="coerce")


def _date_column(spine: pd.DataFrame, column: str) -> pd.Series:
    if column not in spine:
        return pd.Series(pd.NaT, index=spine.index)
    return pd.to_datetime(spine[column], errors="coerce", format="mixed")
