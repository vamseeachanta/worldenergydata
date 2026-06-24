# ABOUTME: Excel parser for Baker Hughes rig count data (WRK-1190).
# ABOUTME: Handles pivot table (detailed metadata) and summary (state counts) formats.

"""Baker Hughes rig count Excel loaders.

Two formats:
  - Pivot table: per-rig-record with full metadata (basin, county, trajectory, depth)
  - Summary: wide-format state x date counts, melted to long format
"""

import logging
from pathlib import Path
from typing import Optional, Union

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


def load_pivot_table(
    path: Union[str, Path],
    *,
    country: Optional[str] = None,
    basin: Optional[str] = None,
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
    """
    df = pd.read_excel(path, sheet_name=sheet_name)
    df = df.rename(columns=_PIVOT_COLUMN_MAP)

    df["date"] = pd.to_datetime(df["date"])
    df["rig_count"] = (
        pd.to_numeric(df["rig_count"], errors="coerce").fillna(0).astype(int)
    )
    df["well_depth_ft"] = pd.to_numeric(df["well_depth_ft"], errors="coerce")
    df["water_depth_ft"] = pd.to_numeric(df["water_depth_ft"], errors="coerce")

    if country is not None:
        df = df[df["country"] == country].copy()
    if basin is not None:
        df = df[df["basin"] == basin].copy()

    logger.info("Loaded pivot table: %d records from %s", len(df), path)
    return df.reset_index(drop=True)


def load_summary(
    path: Union[str, Path],
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
    """
    df = pd.read_excel(path, sheet_name=sheet_name)

    state_col = df.columns[0]
    date_cols = [c for c in df.columns if c != state_col]

    melted = df.melt(
        id_vars=[state_col],
        value_vars=date_cols,
        var_name="date",
        value_name="rig_count",
    )
    melted = melted.rename(columns={state_col: "state"})
    melted["date"] = pd.to_datetime(melted["date"])
    melted["rig_count"] = (
        pd.to_numeric(melted["rig_count"], errors="coerce").fillna(0).astype(int)
    )

    logger.info("Loaded summary: %d records from %s", len(melted), path)
    return melted.reset_index(drop=True)
