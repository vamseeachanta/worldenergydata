# ABOUTME: Ingestion report generator for Baker Hughes data (WRK-1190).
# ABOUTME: Creates YAML-serializable dict with date range, record counts, and metadata.

"""Baker Hughes ingestion report generator."""

from typing import Any, Dict

import pandas as pd


def generate_report(df: pd.DataFrame, source: str) -> Dict[str, Any]:
    """Generate an ingestion report dict from a loaded DataFrame.

    Args:
        df: Loaded Baker Hughes DataFrame (pivot or summary).
        source: Label for the data source ('pivot' or 'summary').

    Returns:
        Dict suitable for YAML serialization with record counts,
        date range, and available dimensions.
    """
    report: Dict[str, Any] = {
        "source": source,
        "record_count": len(df),
    }

    if "date" in df.columns and len(df) > 0:
        report["date_range"] = {
            "min": str(df["date"].min().date()),
            "max": str(df["date"].max().date()),
        }

    if "basin" in df.columns:
        report["basins"] = sorted(df["basin"].dropna().unique().tolist())

    if "state" in df.columns:
        report["states"] = sorted(df["state"].dropna().unique().tolist())

    if "country" in df.columns:
        report["countries"] = sorted(df["country"].dropna().unique().tolist())

    return report
