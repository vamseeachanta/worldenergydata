"""Bridge from curated vessel_fleet parquet to legacy BSEE rig_fleet format.

Converts the expanded curated drilling rigs DataFrame (with columns like
VESSEL_NAME, RIG_DESIGN, DATA_SOURCE_URL) into a DataFrame compatible with
the legacy RigFleetSchema used by ``RigFleetLoader``.

The conversion:
1. Fills RIG_NAME from VESSEL_NAME where RIG_NAME is null.
2. Drops rows where both RIG_NAME and VESSEL_NAME are null.
3. Selects only columns defined in the legacy RigFleetSchema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd

# Columns matching RigFleetSchema fields — the legacy BSEE rig fleet format.
LEGACY_COLUMNS: list[str] = [
    "RIG_NAME",
    "RIG_TYPE",
    "RIG_STATUS",
    "OWNER",
    "OPERATOR",
    "IMO_NUMBER",
    "FLAG_STATE",
    "WATER_DEPTH_RATING_FT",
    "DRILLING_DEPTH_RATING_FT",
    "MAX_WATER_DEPTH_FT",
    "LOA_M",
    "BEAM_M",
    "DISPLACEMENT_TONNES",
    "MOONPOOL_DIAMETER_M",
    "DP_CLASS",
    "YEAR_BUILT",
    "WELLS_DRILLED_COUNT",
    "LAST_WAR_DATE",
    "FIRST_WAR_DATE",
    "LAST_AREA_CODE",
    "LAST_BLOCK_NUMBER",
    "DATA_SOURCE",
    "IS_OFFSHORE",
]


def convert_curated_to_rig_fleet(
    curated: Union[pd.DataFrame, Path],
) -> pd.DataFrame:
    """Convert curated drilling rigs data to legacy rig fleet format.

    Args:
        curated: Either a pandas DataFrame of curated data, or a Path
            to a parquet file that will be read.

    Returns:
        DataFrame with only legacy RigFleetSchema-compatible columns.
        Every row has a non-null RIG_NAME.
    """
    if isinstance(curated, (str, Path)):
        df = pd.read_parquet(Path(curated))
    else:
        df = curated.copy()

    # Ensure all legacy columns exist (fill missing as NaN)
    for col in LEGACY_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Fill RIG_NAME from VESSEL_NAME where RIG_NAME is missing
    if "VESSEL_NAME" in df.columns:
        mask = df["RIG_NAME"].isna() | (df["RIG_NAME"].astype(str).str.strip() == "")
        df.loc[mask, "RIG_NAME"] = df.loc[mask, "VESSEL_NAME"]

    # Drop rows where RIG_NAME is still null after fallback
    df = df.dropna(subset=["RIG_NAME"])
    df = df[df["RIG_NAME"].astype(str).str.strip() != ""]

    result = df[LEGACY_COLUMNS].copy()
    result = result.reset_index(drop=True)

    return result
