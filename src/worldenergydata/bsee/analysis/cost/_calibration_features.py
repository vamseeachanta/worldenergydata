# ABOUTME: WRK-171 internal feature engineering and proxy rate constants for cost calibration.
# ABOUTME: Extracted from cost_calibration.py to keep file length under 400 lines.

"""Internal feature engineering for MultivariateCalibration (WRK-171).

Not part of the public API — import from cost_calibration.py instead.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    WaterDepthBand,
    classify_water_depth_band,
)

# ---------------------------------------------------------------------------
# Proxy rate constants (USD/day, 2022 baseline from day_rates.yml)
# ---------------------------------------------------------------------------

_PROXY_RATES_2022: dict[str, dict[str, float]] = {
    "gom": {
        "drilling__shallow": 110_000,
        "drilling__mid": 270_000,
        "drilling__deep": 440_000,
        "drilling__ultra_deep": 520_000,
        "completion__shallow": 75_000,
        "completion__mid": 115_000,
        "completion__deep": 175_000,
        "completion__ultra_deep": 210_000,
    },
    "north_sea": {
        "drilling__shallow": 130_000,
        "drilling__mid": 330_000,
        "drilling__deep": 490_000,
        "drilling__ultra_deep": 575_000,
        "completion__shallow": 92_000,
        "completion__mid": 140_000,
        "completion__deep": 205_000,
        "completion__ultra_deep": 248_000,
    },
    "brazil": {
        "drilling__shallow": 100_000,
        "drilling__mid": 248_000,
        "drilling__deep": 415_000,
        "drilling__ultra_deep": 492_000,
        "completion__shallow": 70_000,
        "completion__mid": 105_000,
        "completion__deep": 160_000,
        "completion__ultra_deep": 193_000,
    },
    "west_africa": {
        "drilling__shallow": 90_000,
        "drilling__mid": 224_000,
        "drilling__deep": 374_000,
        "drilling__ultra_deep": 445_000,
        "completion__shallow": 63_000,
        "completion__mid": 94_000,
        "completion__deep": 143_000,
        "completion__ultra_deep": 174_000,
    },
    "asia_pacific": {
        "drilling__shallow": 83_000,
        "drilling__mid": 204_000,
        "drilling__deep": 345_000,
        "drilling__ultra_deep": 410_000,
        "completion__shallow": 58_000,
        "completion__mid": 87_000,
        "completion__deep": 132_000,
        "completion__ultra_deep": 160_000,
    },
}

PROXY_REGIONS = list(_PROXY_RATES_2022.keys())

# ---------------------------------------------------------------------------
# Required training columns
# ---------------------------------------------------------------------------

REQUIRED_FIT_COLUMNS = {
    "region",
    "water_depth_m",
    "well_depth_m",
    "activity_type",
    "hpht",
    "cost_usd_mm",
    "year_drilling",
}


# ---------------------------------------------------------------------------
# Feature matrix builder
# ---------------------------------------------------------------------------


def build_feature_matrix(
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Construct design matrix X and target y from a sanctioned-project DataFrame.

    Encodes:
    - Numeric: water_depth_m, well_depth_m, year_drilling, hpht, subsea
    - One-hot: region, activity_type, water_depth_band
    - Interaction: region x hpht

    Args:
        df: DataFrame with at least REQUIRED_FIT_COLUMNS columns.

    Returns:
        (X, y, feature_names) tuple.
    """
    regions_all = sorted(PROXY_REGIONS)
    activities_all = sorted(a.value for a in ActivityType)
    bands_all = sorted(b.value for b in WaterDepthBand)

    rows: list[list[float]] = []
    y_vals: list[float] = []

    for _, row in df.iterrows():
        features: list[float] = [1.0]  # intercept

        # Numeric features
        features.append(float(row.get("water_depth_m", 0.0)))
        features.append(float(row.get("well_depth_m", 0.0)))
        features.append(float(row.get("year_drilling", 2020)))
        features.append(1.0 if row.get("hpht", False) else 0.0)
        features.append(1.0 if row.get("subsea", True) else 0.0)

        # One-hot: region
        region = str(row.get("region", "gom")).lower()
        for r in regions_all:
            features.append(1.0 if region == r else 0.0)

        # One-hot: activity_type
        act = str(row.get("activity_type", "drilling")).lower()
        for a in activities_all:
            features.append(1.0 if act == a else 0.0)

        # One-hot: water_depth_band
        band = classify_water_depth_band(
            float(row.get("water_depth_m", 0.0))
        ).value
        for b in bands_all:
            features.append(1.0 if band == b else 0.0)

        # Interaction: region x hpht
        hpht_flag = 1.0 if row.get("hpht", False) else 0.0
        for r in regions_all:
            features.append((1.0 if region == r else 0.0) * hpht_flag)

        rows.append(features)
        y_vals.append(float(row.get("cost_usd_mm", 0.0)))

    feature_names: list[str] = (
        ["intercept", "water_depth_m", "well_depth_m", "year_drilling",
         "hpht", "subsea"]
        + [f"region_{r}" for r in regions_all]
        + [f"activity_{a}" for a in activities_all]
        + [f"band_{b}" for b in bands_all]
        + [f"region_hpht_{r}" for r in regions_all]
    )

    X = np.array(rows, dtype=float)
    y = np.array(y_vals, dtype=float)
    return X, y, feature_names
