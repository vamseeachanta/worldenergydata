# ABOUTME: Ingestion report generator for Baker Hughes data (WRK-1190).
# ABOUTME: Creates YAML-serializable dict with date range, record counts, and metadata.

"""Baker Hughes ingestion report generator."""

from copy import deepcopy
from typing import Any

import pandas as pd


def generate_report(df: pd.DataFrame, source: str) -> dict[str, Any]:
    """Generate an ingestion report dict from a loaded DataFrame.

    Args:
        df: Loaded Baker Hughes DataFrame (pivot or summary).
        source: Label for the data source ('pivot' or 'summary').

    Returns:
        Dict suitable for YAML serialization with record counts,
        observed date bounds, and available dimensions. The additive
        completeness entry describes dates, dimensions, and any loader
        diagnostics supplied in DataFrame attrs. Empty input, an absent
        date column, and missing date values are explicitly incomplete.
        Bounds are omitted when no dates are observed; partial bounds are
        retained with an incomplete status. Dates must already be parsed,
        as returned by the loaders.

        All three inventories (basins, states, countries) are assessed for
        every source label, including summary. Absent columns/bounds are
        explicitly listed in omitted_fields; undefined bounds never contain
        NaT. Complete means observed fields are populated, not independently
        qualified source data. Loader attrs are transient metadata.
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
            "bounds_status": (
                "observed" if "date" in df and df["date"].notna().any() else "undefined"
            ),
        }
    }

    if "date" in df.columns and df["date"].notna().any():
        observed_dates = df["date"].dropna()
        report["date_range"] = {
            "min": str(observed_dates.min().date()),
            "max": str(observed_dates.max().date()),
        }

    if "basin" in df.columns:
        report["basins"] = sorted(df["basin"].dropna().unique().tolist())

    if "state" in df.columns:
        report["states"] = sorted(df["state"].dropna().unique().tolist())

    if "country" in df.columns:
        report["countries"] = sorted(df["country"].dropna().unique().tolist())

    # Issue #1335, F14-F18; pack section 12: absent and null dimensions are
    # different conditions. Counts enumerate rows, with no tolerance.
    completeness = report["completeness"]
    dimensions = {}
    omitted = [] if "date_range" in report else ["date_range"]
    for column, field in (
        ("basin", "basins"),
        ("state", "states"),
        ("country", "countries"),
    ):
        missing = int(df[column].isna().sum()) if column in df else None
        dimension_reason = (
            "missing_column"
            if column not in df
            else "missing_values" if missing else None
        )
        dimensions[column] = {
            "status": (
                "undefined"
                if column not in df
                else "incomplete" if missing else "complete"
            ),
            "reason": dimension_reason,
            "missing_count": missing,
        }
        if column not in df:
            omitted.append(field)
    completeness["dimensions"] = dimensions
    completeness["omitted_fields"] = omitted
    for key in ("schema", "ingestion"):
        if key in df.attrs:
            completeness[key] = deepcopy(df.attrs[key])
    incomplete = (
        reason is not None
        or any(d["status"] != "complete" for d in dimensions.values())
        or df.attrs.get("schema", {}).get("status") == "incomplete"
        or df.attrs.get("ingestion", {}).get("status") in ("no_match", "empty_input")
    )
    completeness["status"] = "incomplete" if incomplete else "complete"

    return report
