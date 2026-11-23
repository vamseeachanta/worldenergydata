"""Vectorized lifecycle aggregation for field-development metrics."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from worldenergydata.texas_rrc.field_development._metrics_helpers import ensure_columns


def aggregate_lifecycle(
    lifecycle: pd.DataFrame,
    field_keys: Sequence[str],
    input_columns: list[str],
    empty_frame: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate well-level lifecycle rows into field-level metrics."""
    if lifecycle.empty:
        return empty_frame
    frame = lifecycle.copy()
    ensure_columns(frame, input_columns)
    keys = list(field_keys)
    selected_columns = list(dict.fromkeys(keys + input_columns))
    working = frame.loc[:, selected_columns].copy()
    _add_lifecycle_aggregation_columns(working)
    grouped = working.groupby(keys, sort=True, dropna=True)
    counts = grouped.size()
    if counts.empty:
        return empty_frame
    result = pd.DataFrame(index=counts.index)
    result["well_count"] = counts
    result["lifecycle_field_name"] = grouped["_field_name_value"].first()
    result["active_well_count"] = grouped["_active_well"].sum()
    result["plugged_well_count"] = grouped["_plugged_well"].sum()
    result["permit_count"] = grouped["_permit_present"].sum()
    result["completion_count"] = grouped["_completion_present"].sum()
    result["horizontal_well_count"] = grouped["_horizontal_well"].sum()
    result["directional_well_count"] = grouped["_directional_well"].sum()
    result["median_permit_to_completion_days"] = grouped[
        "_permit_to_completion_days"
    ].median()
    result["completion_dates"] = grouped["_completion_date_value"].agg(
        _completion_dates
    )
    result["lifecycle_lease_count"] = grouped["_lease_number_value"].nunique(
        dropna=True
    )
    result["lifecycle_operator_count"] = grouped["_operator_number_value"].nunique(
        dropna=True
    )
    return result.reset_index()


def _add_lifecycle_aggregation_columns(frame: pd.DataFrame) -> None:
    status = frame["well_status"].astype("string").str.upper()
    profile = _profile_text(frame)
    completion_dates = pd.to_datetime(frame["completion_date"], errors="coerce")
    permit_dates = pd.to_datetime(frame["permit_issued_date"], errors="coerce")
    permit_to_completion = (completion_dates - permit_dates).dt.days

    frame["_field_name_value"] = _value_series(frame["field_name"])
    frame["_lease_number_value"] = _value_series(frame["lease_number"])
    frame["_operator_number_value"] = _value_series(frame["operator_number"])
    frame["_active_well"] = status.str.contains(
        "PRODUCING|ACTIVE|FLOWING|SHUT IN",
        regex=True,
        na=False,
    )
    frame["_plugged_well"] = status.str.contains("PLUG", regex=False, na=False)
    frame["_permit_present"] = _present(frame["permit_number"])
    frame["_completion_present"] = _present(frame["completion_date"])
    frame["_horizontal_well"] = profile.str.contains(
        "HORIZONTAL", regex=False, na=False
    ) | profile.str.contains(r"(?:^|\s)HZ", regex=True, na=False)
    frame["_directional_well"] = profile.str.contains(
        "DIRECTIONAL", regex=False, na=False
    ) | profile.str.contains(r"(?:^|\s)DIR", regex=True, na=False)
    frame["_permit_to_completion_days"] = permit_to_completion.where(
        permit_to_completion >= 0
    )
    frame["_completion_date_value"] = completion_dates


def _profile_text(frame: pd.DataFrame) -> pd.Series:
    profile = frame["wellbore_profile"].astype("string").fillna("")
    well_type = frame["well_type"].astype("string").fillna("")
    return (profile + " " + well_type).str.upper()


def _present(values: pd.Series) -> pd.Series:
    text = values.astype("string")
    return text.notna() & text.ne("")


def _value_series(values: pd.Series) -> pd.Series:
    text = values.astype("string")
    return text.where(_present(values), pd.NA)


def _completion_dates(values: pd.Series) -> tuple[pd.Timestamp, ...]:
    return tuple(value for value in values if not pd.isna(value))


__all__ = ["aggregate_lifecycle"]
