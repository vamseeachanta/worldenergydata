"""
Incident Aggregation and Hurt Index

Aggregate safety incidents by time period, severity, work activity,
and compute hurt indices for comparative analysis.

Aggregate safety incidents by time period, severity, and work activity
using plain pandas.
"""

from typing import Dict, List, Optional

import pandas as pd

from worldenergydata.safety_analysis.constants import SeverityLevel

DEFAULT_SEVERITY_NUMERIC = {
    SeverityLevel.NO_HURT: 0,
    SeverityLevel.MINOR: 1,
    SeverityLevel.MODERATE: 2,
    SeverityLevel.SEVERE: 3,
    SeverityLevel.FATALITY: 4,
    SeverityLevel.MULTIPLE_FATALITIES: 5,
}


def aggregate_by_severity(
    incidents: pd.DataFrame,
    severity_column: str = "actual_severity",
    count_column: str = "asset_id",
) -> pd.DataFrame:
    """
    Count incidents grouped by severity level.

    Returns DataFrame with severity and count columns.
    """
    agg = incidents.groupby(severity_column).agg({count_column: "count"}).reset_index()
    agg.columns = [severity_column, "count"]
    return agg


def aggregate_by_time(
    incidents: pd.DataFrame,
    datetime_column: str = "occurred_at",
    freq: str = "D",
    count_column: str = "asset_id",
) -> pd.DataFrame:
    """
    Count incidents per time period.

    Args:
        incidents: Incident DataFrame.
        datetime_column: Column with datetime values.
        freq: Resampling frequency (D=daily, W=weekly, MS=monthly).
        count_column: Column to count.

    Returns:
        DataFrame with datetime index and count column.
    """
    df = incidents.copy()
    df[datetime_column] = pd.to_datetime(df[datetime_column])
    df["_count"] = 1
    result = (
        df.set_index(datetime_column)
        .resample(freq)
        .agg({"_count": "sum"})
        .reset_index()
    )
    result.columns = [datetime_column, "count"]
    return result


def aggregate_by_group(
    incidents: pd.DataFrame,
    group_columns: List[str],
    count_column: str = "asset_id",
) -> pd.DataFrame:
    """
    Count incidents by arbitrary grouping columns.

    Args:
        incidents: Incident DataFrame.
        group_columns: Columns to group by.
        count_column: Column to count.

    Returns:
        DataFrame with group columns and count.
    """
    agg = incidents.groupby(group_columns).agg({count_column: "count"}).reset_index()
    agg.columns = group_columns + ["count"]
    return agg


def compute_hurt_index(
    incidents: pd.DataFrame,
    group_column: str,
    severity_column: str = "actual_severity",
    severity_numeric_map: Optional[Dict[str, int]] = None,
) -> pd.DataFrame:
    """
    Compute a hurt index (sum of numeric severity) per group.

    The hurt index is a weighted sum of incidents by severity level:
    No Hurt=0, Minor=1, Moderate=2, Severe=3, Fatality=4, Multiple=5.

    Args:
        incidents: Incident DataFrame.
        group_column: Column to group by (e.g., work_activity, asset_id).
        severity_column: Column containing severity values.
        severity_numeric_map: Custom mapping of severity labels to numeric values.

    Returns:
        DataFrame with group_column and hurt_index columns.
    """
    if severity_numeric_map is None:
        severity_numeric_map = {
            level.value: score for level, score in DEFAULT_SEVERITY_NUMERIC.items()
        }

    df = incidents.copy()
    df["_severity_numeric"] = df[severity_column].map(severity_numeric_map).fillna(0)

    result = df.groupby(group_column).agg({"_severity_numeric": "sum"}).reset_index()
    result.columns = [group_column, "hurt_index"]
    return result


def compute_time_series_hurt_index(
    incidents: pd.DataFrame,
    datetime_column: str = "occurred_at",
    severity_column: str = "actual_severity",
    potential_severity_column: Optional[str] = "potential_severity",
    freq: str = "D",
    severity_numeric_map: Optional[Dict[str, int]] = None,
) -> pd.DataFrame:
    """
    Compute daily/weekly/monthly hurt index time series.

    Returns DataFrame with datetime, actual_hurt_index, and optionally
    potential_hurt_index columns.
    """
    if severity_numeric_map is None:
        severity_numeric_map = {
            level.value: score for level, score in DEFAULT_SEVERITY_NUMERIC.items()
        }

    df = incidents.copy()
    df[datetime_column] = pd.to_datetime(df[datetime_column])
    df["_actual_numeric"] = df[severity_column].map(severity_numeric_map).fillna(0)

    result = (
        df.set_index(datetime_column)
        .resample(freq)
        .agg({"_actual_numeric": "sum"})
        .reset_index()
    )
    result.columns = [datetime_column, "actual_hurt_index"]

    if potential_severity_column and potential_severity_column in df.columns:
        df["_potential_numeric"] = (
            df[potential_severity_column].map(severity_numeric_map).fillna(0)
        )
        pot_result = (
            df.set_index(datetime_column)
            .resample(freq)
            .agg({"_potential_numeric": "sum"})
            .reset_index()
        )
        result["potential_hurt_index"] = pot_result["_potential_numeric"]

    return result
