"""Convert BSEE WAR fleet DataFrame to vessel_fleet format records.

Maps WAR rig fleet columns to the vessel_fleet schema, filtering
invalid entries and setting mandatory fields for downstream dedup
and fusion.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def export_war_to_vessel_fleet(war_fleet_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert WAR fleet DataFrame to vessel_fleet format records.

    Maps RIG_NAME to VESSEL_NAME (keeping both), sets DATA_SOURCE
    to ``"bsee_war"``, VESSEL_CATEGORY to ``"drilling_rig"``, and
    IS_OFFSHORE to ``True``.  Filters out rows with empty/null
    RIG_NAME or containing "NON RIG" in the name.

    Args:
        war_fleet_df: DataFrame from the WAR rig fleet loader with
            at minimum a ``RIG_NAME`` column.

    Returns:
        List of dicts suitable for ``ParquetStore.save()``.
    """
    if war_fleet_df.empty:
        return []

    if "RIG_NAME" not in war_fleet_df.columns:
        logger.error("WAR DataFrame missing RIG_NAME column")
        return []

    df = war_fleet_df.copy()

    # Filter out null/empty RIG_NAME
    mask = df["RIG_NAME"].notna() & (df["RIG_NAME"].astype(str).str.strip() != "")

    # Filter out "NON RIG" entries (e.g. "* NON RIG UNIT OPERATION")
    mask = mask & ~df["RIG_NAME"].astype(str).str.upper().str.contains(
        "NON RIG", na=False
    )

    df = df[mask].copy()

    if df.empty:
        return []

    # Ensure RIG_NAME is string type before strip
    df["RIG_NAME"] = df["RIG_NAME"].astype(str).str.strip()

    # Map RIG_NAME -> VESSEL_NAME (keep both)
    df["VESSEL_NAME"] = df["RIG_NAME"]

    # Set mandatory vessel_fleet fields
    df["DATA_SOURCE"] = "bsee_war"
    df["VESSEL_CATEGORY"] = "drilling_rig"
    df["IS_OFFSHORE"] = True

    records = df.to_dict(orient="records")
    logger.info(
        "Exported %d WAR rigs to vessel_fleet format",
        len(records),
    )
    return records
