# ABOUTME: Ingestion report generator for Baker Hughes data (WRK-1190).
# ABOUTME: Creates YAML-serializable dict with date range, record counts, and metadata.

"""Baker Hughes ingestion report generator."""

from copy import deepcopy
from typing import Any

import pandas as pd


def _dimension_completeness(
    df: pd.DataFrame, column: str, optional: bool
) -> tuple[dict[str, Any], list | None]:
    """Enumerate observed values separately from missing metadata."""
    if column not in df.columns:
        return {
            "status": "not_applicable" if optional else "incomplete",
            "reason": (
                "not_in_summary_schema" if optional else "missing_dimension_column"
            ),
            "missing_count": None,
        }, None

    missing = df[column].isna() | df[column].map(
        lambda value: isinstance(value, str) and not value.strip()
    )
    missing_count = int(missing.sum())
    if df.index.empty:
        reason = "empty_input"
    elif missing.all():
        reason = "all_values_missing"
    elif missing_count:
        reason = "missing_values"
    else:
        reason = None
    return {
        "status": "incomplete" if reason else "complete",
        "reason": reason,
        "missing_count": missing_count,
    }, sorted(df.loc[~missing, column].unique().tolist())


def generate_report(df: pd.DataFrame, source: str) -> dict[str, Any]:
    """Generate an ingestion report dict from a loaded DataFrame.

    Args:
        df: Loaded Baker Hughes DataFrame (pivot or summary).
        source: Label for the data source ('pivot' or 'summary').

    Returns:
        Dict suitable for YAML serialization with record counts,
        observed date bounds, and available dimensions. Completeness covers
        date values, dimensions and available loader schema metadata; it
        establishes neither source accuracy nor temporal/geographic coverage.
        Only source='summary' permits absent basin/country dimensions. Empty input, an absent
        date column, and missing date values are explicitly incomplete.
        Bounds are omitted when no dates are observed; partial bounds are
        retained with an incomplete status. Dates must already be parsed,
        as returned by the loaders; nonempty unparsed dates raise ValueError.
        Schema provenance is not_evaluated for frames without loader metadata.
    """
    report: dict[str, Any] = {
        "source": source,
        "record_count": len(df),
    }

    # Issue #1335, F13/F19; knowledge pack section 11 (2026-10-19):
    # complete date coverage requires nonempty input and no missing dates.
    # Counts are direct enumeration, with no engineering acceptance limit.
    missing_count = None
    if "date" in df.columns:
        missing_count = int(df["date"].isna().sum())

    if df.index.empty:
        reason = "empty_input"
    elif "date" not in df.columns:
        reason = "missing_date_column"
    elif df["date"].isna().all():
        reason = "all_dates_missing"
    elif df["date"].isna().any():
        reason = "missing_dates"
    else:
        reason = None

    report["completeness"] = {
        "date_range": {
            "status": "incomplete" if reason else "complete",
            "reason": reason,
            "missing_count": missing_count,
        }
    }

    if "date" in df.columns and df["date"].notna().any():
        if not pd.api.types.is_datetime64_any_dtype(df["date"]):
            raise ValueError("date values must already be parsed as pandas datetimes")
        observed_dates = df["date"].dropna()
        report["date_range"] = {
            "min": str(observed_dates.min().date()),
            "max": str(observed_dates.max().date()),
        }

    dimensions = {}
    for column, output in (
        ("basin", "basins"),
        ("state", "states"),
        ("country", "countries"),
    ):
        coverage, values = _dimension_completeness(
            df, column, optional=source == "summary" and column != "state"
        )
        dimensions[output] = coverage
        if values is not None:
            report[output] = values

    schema = deepcopy(
        df.attrs.get(
            "schema_validation",
            {"status": "not_evaluated", "reason": "loader_metadata_unavailable"},
        )
    )
    report["completeness"].update({"dimensions": dimensions, "schema": schema})
    incomplete = (
        reason is not None
        or schema["status"] == "incomplete"
        or any(entry["status"] == "incomplete" for entry in dimensions.values())
    )
    report["completeness"]["status"] = "incomplete" if incomplete else "complete"

    return report
