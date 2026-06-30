"""Build the Texas RRC API14-centered well lifecycle spine."""

from __future__ import annotations

from typing import Any

import pandas as pd

from worldenergydata.texas_rrc.lifecycle.keys import (
    derive_api10,
    normalize_api14,
    split_api14,
)
from worldenergydata.texas_rrc.lifecycle.sources import LifecycleInputFrames


SOURCE_ORDER = ("wellbore_query", "drilling_permits", "completion_data")
IDENTIFIER_COLUMNS = (
    "district",
    "field_number",
    "field_name",
    "lease_number",
    "lease_name",
    "operator_number",
    "operator_name",
)


def normalize_wellbore_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize wellbore rows for lifecycle joining."""
    return _normalize_source_frame(frame)


def normalize_permit_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize drilling permit rows for lifecycle joining."""
    return _normalize_source_frame(frame)


def normalize_completion_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize completion rows for lifecycle joining."""
    return _normalize_source_frame(frame)


def build_lifecycle_spine(inputs: LifecycleInputFrames) -> pd.DataFrame:
    """Return one lifecycle spine row per API10/API14 well identity."""
    wellbores = normalize_wellbore_frame(inputs.wellbores)
    permits = normalize_permit_frame(inputs.permits)
    completions = normalize_completion_frame(inputs.completions)

    wellbore_exact = _by_key(wellbores, "api14")
    permit_exact = _by_key(permits, "api14")
    completion_exact = _by_key(completions, "api14")
    wellbore_context = _by_key(wellbores, "api10")
    permit_context = _by_key(permits, "api10")

    api14_values = sorted(
        set(wellbore_exact) | set(permit_exact) | set(completion_exact)
    )
    records = [
        _build_record(
            api14,
            wellbore_exact.get(api14, {})
            or wellbore_context.get(derive_api10(api14), {}),
            permit_exact.get(api14, {}) or permit_context.get(derive_api10(api14), {}),
            completion_exact.get(api14, {}),
        )
        for api14 in api14_values
    ]
    result = pd.DataFrame(records)
    for column in ("has_wellbore", "has_permit", "has_completion"):
        if column in result:
            result[column] = result[column].astype(object)
    return result


def _normalize_source_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "api_number" not in frame.columns:
        return pd.DataFrame()
    result = frame.copy()
    result["api14"] = result["api_number"].apply(normalize_api14)
    result = result[result["api14"].notna()].copy()
    if result.empty:
        return result
    result["api10"] = result["api14"].apply(derive_api10)
    api_segments = result["api14"].apply(split_api14).apply(pd.Series)
    for column in (
        "county_code",
        "well_unique_number",
        "sidetrack_code",
        "completion_code",
    ):
        result[column] = api_segments[column]
    return result


def _by_key(frame: pd.DataFrame, key: str) -> dict[str, dict[str, Any]]:
    if frame.empty or key not in frame.columns:
        return {}
    rows = {}
    for value, group in frame.groupby(key, sort=True):
        if _has_value(value):
            rows[str(value)] = _most_complete_row(group).to_dict()
    return rows


def _most_complete_row(group: pd.DataFrame) -> pd.Series:
    completeness = group.apply(
        lambda row: sum(_has_value(value) for value in row), axis=1
    )
    return group.loc[completeness.idxmax()]


def _build_record(
    api14: str,
    wellbore: dict[str, Any],
    permit: dict[str, Any],
    completion: dict[str, Any],
) -> dict[str, Any]:
    api10 = derive_api10(api14)
    record = {"api14": api14, "api10": api10}
    record.update(split_api14(api14))
    record.update(_identifier_values(wellbore, completion, permit))
    record.update(_permit_values(permit))
    record.update(_lifecycle_values(wellbore, completion, permit))
    record.update(_well_values(wellbore, permit))
    record.update(_source_flags(wellbore, permit, completion))
    record["quality_flags"] = ""
    return record


def _identifier_values(*rows: dict[str, Any]) -> dict[str, Any]:
    return {column: _first_value(*rows, column=column) for column in IDENTIFIER_COLUMNS}


def _permit_values(permit: dict[str, Any]) -> dict[str, Any]:
    return {
        "permit_number": permit.get("permit_number"),
        "permit_status": permit.get("permit_status"),
        "permit_type": permit.get("permit_type"),
        "permit_issued_date": permit.get("permit_issued_date"),
        "permit_amended_date": permit.get("permit_amended_date"),
        "permit_extended_date": permit.get("permit_extended_date"),
    }


def _lifecycle_values(
    wellbore: dict[str, Any],
    completion: dict[str, Any],
    permit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "spud_date": permit.get("spud_date"),
        "completion_date": _first_value(wellbore, completion, column="completion_date"),
        "plug_date": wellbore.get("plug_date"),
    }


def _well_values(wellbore: dict[str, Any], permit: dict[str, Any]) -> dict[str, Any]:
    return {
        "well_status": wellbore.get("well_status"),
        "well_type": wellbore.get("well_type"),
        "wellbore_profile": wellbore.get("wellbore_profile"),
        "total_depth": _first_value(wellbore, permit, column="total_depth"),
        "latitude": permit.get("latitude") or wellbore.get("latitude"),
        "longitude": permit.get("longitude") or wellbore.get("longitude"),
        "coordinates_valid": None,
    }


def _source_flags(
    wellbore: dict[str, Any],
    permit: dict[str, Any],
    completion: dict[str, Any],
) -> dict[str, Any]:
    present = {
        "wellbore_query": bool(wellbore),
        "drilling_permits": bool(permit),
        "completion_data": bool(completion),
    }
    return {
        "has_wellbore": present["wellbore_query"],
        "has_permit": present["drilling_permits"],
        "has_completion": present["completion_data"],
        "source_ids": "|".join(source for source in SOURCE_ORDER if present[source]),
    }


def _first_value(*rows: dict[str, Any], column: str) -> Any:
    for row in rows:
        value = row.get(column)
        if _has_value(value):
            return value
    return None


def _has_value(value: Any) -> bool:
    return value is not None and value == value and str(value) != ""
