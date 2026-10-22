# ABOUTME: Excel parser for Baker Hughes rig count data (WRK-1190).
# ABOUTME: Handles pivot table (detailed metadata) and summary (state counts) formats.

"""Baker Hughes rig count Excel loaders.

Two formats:
  - Pivot table: per-rig-record with full metadata (basin, county, trajectory, depth)
  - Summary: wide-format state x date counts, melted to long format
"""

import logging
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Column mapping: Baker Hughes Excel → standardized output
_PIVOT_COLUMN_MAP = {
    "PublishDate": "date",
    "Country": "country",
    "StateProvince": "state",
    "County": "county",
    "BasinName": "basin",
    "DrillFor": "drill_for",
    "Location": "location",
    "Trajectory": "trajectory",
    "WellType": "well_type",
    "WellDepth": "well_depth_ft",
    "WaterDepth": "water_depth_ft",
    "RigCount": "rig_count",
}

# Input-domain contract: issue #1335 (2026), pack section 12. No calibrated
# coefficients: these sets enumerate source fields, not engineering limits.
_PIVOT_REQUIRED = ("PublishDate", "RigCount")
_PIVOT_OPTIONAL = tuple(c for c in _PIVOT_COLUMN_MAP if c not in _PIVOT_REQUIRED)


class SchemaError(ValueError):
    """Rejected workbook schema with structured diagnostics."""

    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__(f"Workbook schema rejected: {diagnostics}")


def _pivot_schema(df):
    diagnostics = {
        "missing_required": [c for c in _PIVOT_REQUIRED if c not in df],
        "unexpected": [str(c) for c in df if c not in _PIVOT_COLUMN_MAP],
        "duplicate": [str(c) for c in df.columns[df.columns.duplicated()]],
    }
    if any(diagnostics.values()):
        raise SchemaError(diagnostics)
    missing = [c for c in _PIVOT_OPTIONAL if c not in df]
    return {
        "status": "incomplete" if missing else "complete",
        "missing_optional": missing,
    }


def _date_header(header):
    """Select full dates only; pandas 2.3.3 to_datetime, explicit format."""
    if isinstance(header, (datetime, date)):
        parsed = pd.Timestamp(header)
        if pd.isna(parsed) or parsed.tzinfo is not None or parsed != parsed.normalize():
            raise ValueError("Date header must be a timezone-naive calendar date")
        return parsed
    if isinstance(header, str):
        for pattern, fmt in (
            (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
            (r"\d{1,2}/\d{1,2}/\d{4}", "%m/%d/%Y"),
        ):
            if re.fullmatch(pattern, header):
                return pd.to_datetime(header, format=fmt, errors="raise")
    raise ValueError("Not a supported date header")


def _summary_schema(df):
    diagnostics = {}
    if df.columns.empty or df.columns[0] != "State":
        diagnostics["identifier"] = "First column must be State"
    if len(df.columns) < 2:
        diagnostics["missing_required"] = (["State"] if df.columns.empty else []) + [
            "date header"
        ]
    duplicates = [str(c) for c in df.columns[df.columns.duplicated()]]
    if duplicates:
        diagnostics["duplicate"] = duplicates
    dates = []
    invalid = []
    for header in df.columns[1:]:
        try:
            dates.append(_date_header(header))
        except (ValueError, TypeError, OverflowError):
            invalid.append(str(header))
    if invalid:
        diagnostics["invalid_date_headers"] = invalid
    if len(set(dates)) != len(dates):
        diagnostics["duplicate_dates"] = "Headers identify the same calendar date"
    if diagnostics:
        raise SchemaError(diagnostics)
    return dates


def load_pivot_table(
    path: str | Path,
    *,
    country: str | None = None,
    basin: str | None = None,
    sheet_name: str = "Pivot Table",
) -> pd.DataFrame:
    """Load Baker Hughes NA pivot table Excel into a standardized DataFrame.

    Args:
        path: Path to the pivot table Excel file.
        country: Filter to a specific country (e.g. 'UNITED STATES').
        basin: Filter to a specific basin (e.g. 'PERMIAN').
        sheet_name: Excel sheet name to read.

    Returns:
        DataFrame with standardized columns: date, country, state, county,
        basin, drill_for, location, trajectory, well_type, well_depth_ft,
        water_depth_ft, rig_count.

    Schema contract (issue #1335; pack section 12):

    ==================== ===================================================
    Field class          Source headers / rule
    ==================== ===================================================
    Required             PublishDate, RigCount
    Optional             Country, StateProvince, County, BasinName, DrillFor,
                         Location, Trajectory, WellType, WellDepth, WaterDepth
    Unexpected/duplicate Rejected with SchemaError.diagnostics
    Missing optional     Listed in df.attrs['schema']; no columns invented
    ==================== ===================================================

    ``attrs['ingestion']`` reports loaded/matched/no_match/empty_input and
    source null-dimension counts. Filters are exact comparisons; filtering
    an absent column raises ValueError with absent_dimension.
    """
    df = pd.read_excel(path, sheet_name=sheet_name)
    schema = _pivot_schema(df)
    df = df.rename(columns=_PIVOT_COLUMN_MAP)

    df["date"] = pd.to_datetime(df["date"])
    df["rig_count"] = (
        pd.to_numeric(df["rig_count"], errors="coerce").fillna(0).astype(int)
    )
    for column in ("well_depth_ft", "water_depth_ft"):
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    input_rows = len(df)
    filters = {
        key: value
        for key, value in (("country", country), ("basin", basin))
        if value is not None
    }
    for dimension in filters:
        if dimension not in df:
            raise ValueError(f"absent_dimension: {dimension}")
    null_dimensions = {
        c: int(df[c].isna().sum()) for c in ("country", "basin", "state") if c in df
    }

    if country is not None:
        df = df[df["country"] == country].copy()
    if basin is not None:
        df = df[df["basin"] == basin].copy()

    logger.info("Loaded pivot table: %d records from %s", len(df), path)
    df = df.reset_index(drop=True)
    df.attrs["schema"] = schema
    df.attrs["ingestion"] = {
        "status": (
            "empty_input"
            if not input_rows
            else (
                "no_match"
                if filters and df.empty
                else "matched" if filters else "loaded"
            )
        ),
        "input_rows": input_rows,
        "output_rows": len(df),
        "filters": filters,
        "null_dimensions": null_dimensions,
    }
    return df


def load_summary(
    path: str | Path,
    *,
    sheet_name: str = "Rigs by State",
) -> pd.DataFrame:
    """Load Baker Hughes summary (rigs by state) Excel into long format.

    The summary Excel has states as rows and dates as columns. This function
    melts the wide format into long format with columns: state, date, rig_count.

    Args:
        path: Path to the summary Excel file.
        sheet_name: Excel sheet name to read.

    Returns:
        DataFrame with columns: state, date, rig_count.

    Schema contract (issue #1335; pack section 12):

    =================== ====================================================
    Field class         Source headers / rule
    =================== ====================================================
    Required identifier State, in the first column (case sensitive)
    Required dates      At least one: YYYY-MM-DD, M/D/YYYY (month first), or
                        Excel datetime/date at midnight, timezone naive
    Optional columns    None
    Extra/non-date      Rejected; no totals/notes columns silently melted
    Duplicate dates     Rejected, including differently formatted equivalents
    =================== ====================================================
    """
    df = pd.read_excel(path, sheet_name=sheet_name)
    dates = _summary_schema(df)

    state_col = df.columns[0]
    date_cols = [c for c in df.columns if c != state_col]

    melted = df.melt(
        id_vars=[state_col],
        value_vars=date_cols,
        var_name="date",
        value_name="rig_count",
    )
    melted = melted.rename(columns={state_col: "state"})
    date_map = dict(zip(date_cols, dates))
    melted["date"] = pd.to_datetime(melted["date"].map(date_map))
    melted["rig_count"] = (
        pd.to_numeric(melted["rig_count"], errors="coerce").fillna(0).astype(int)
    )

    logger.info("Loaded summary: %d records from %s", len(melted), path)
    melted = melted.reset_index(drop=True)
    melted.attrs["schema"] = {"status": "complete", "missing_optional": []}
    melted.attrs["ingestion"] = {
        "status": "empty_input" if df.empty else "loaded",
        "input_rows": len(df),
        "output_rows": len(melted),
        "filters": {},
        "null_dimensions": {"state": int(df[state_col].isna().sum())},
    }
    return melted
