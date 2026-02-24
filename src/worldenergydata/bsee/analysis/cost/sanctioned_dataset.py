# ABOUTME: WRK-171 sanctioned project dataset builder and synthetic data generator.
# ABOUTME: Provides schema validation, inflation adjustment, and 120+ record synthetic dataset.

"""Sanctioned project cost dataset builder (WRK-171).

Implements:
- ``synthetic_dataset(n_records, seed)`` — reproducible test data with >=100 records
- ``inflation_adjust(df, base_year)`` — CPI-like escalation to a common year
- ``validate_schema(df)`` — check required columns and value constraints
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    CostType,
    RigType,
    WaterDepthBand,
    WellDepthBand,
    classify_water_depth_band,
    classify_well_depth_band,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = [
    "project_name",
    "region",
    "water_depth_m",
    "water_depth_band",
    "well_depth_m",
    "well_depth_band",
    "operator",
    "year_sanction",
    "year_drilling",
    "rig_type",
    "activity_type",
    "hpht",
    "subsea",
    "cost_usd_mm",
    "cost_type",
    "source",
    "confidence",
]

# Approximate annual CPI / upstream cost index escalation relative to 2022 base
# Source: BLS CPI + IHS CERA upstream proxy; simplified linear for implementation
_INFLATION_INDEX: dict[int, float] = {
    2005: 0.62,
    2006: 0.65,
    2007: 0.68,
    2008: 0.75,
    2009: 0.71,
    2010: 0.74,
    2011: 0.79,
    2012: 0.82,
    2013: 0.84,
    2014: 0.86,
    2015: 0.80,
    2016: 0.78,
    2017: 0.80,
    2018: 0.85,
    2019: 0.87,
    2020: 0.86,
    2021: 0.91,
    2022: 1.00,
    2023: 1.07,
    2024: 1.12,
    2025: 1.15,
}

_VALID_REGIONS = ["gom", "north_sea", "brazil", "west_africa", "asia_pacific"]

_OPERATORS_BY_REGION: dict[str, list[str]] = {
    "gom": ["Shell", "BP", "Chevron", "ExxonMobil", "Murphy", "LLOG", "Hess"],
    "north_sea": ["Equinor", "BP", "Shell", "TotalEnergies", "Aker BP"],
    "brazil": ["Petrobras", "TotalEnergies", "Shell", "BP"],
    "west_africa": ["Shell", "TotalEnergies", "ExxonMobil", "Chevron", "BP"],
    "asia_pacific": ["Woodside", "Shell", "Chevron", "ConocoPhillips"],
}


class SanctionedProjectDataset:
    """Builder for the sanctioned project cost calibration dataset.

    Provides synthetic data generation, inflation adjustment, and schema validation.
    Real data population from web-scraping / document parsing is handled by separate
    data-collection scripts; this class owns the schema and validation logic.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthetic_dataset(self, n_records: int = 120, seed: int = 42) -> pd.DataFrame:
        """Generate a reproducible synthetic sanctioned-project cost dataset.

        Produces records across 5 regions, multiple depth bands, activity types,
        and operators. Costs are drawn from region/depth-specific distributions
        calibrated against published industry benchmarks.

        Args:
            n_records: Number of records to generate (minimum 100 recommended).
            seed: RNG seed for reproducibility.

        Returns:
            DataFrame with REQUIRED_COLUMNS columns and n_records rows.
        """
        rng = np.random.default_rng(seed)
        rows = []

        region_weights = [0.30, 0.25, 0.20, 0.15, 0.10]  # matches _VALID_REGIONS order
        regions = rng.choice(
            _VALID_REGIONS, size=n_records, p=region_weights
        )

        for i, region in enumerate(regions):
            row = self._generate_record(rng, region, i)
            rows.append(row)

        df = pd.DataFrame(rows)
        return df

    def inflation_adjust(self, df: pd.DataFrame, base_year: int = 2022) -> pd.DataFrame:
        """Add ``cost_usd_mm_real`` column — cost inflated to base_year USD.

        Uses the internal ``_INFLATION_INDEX`` table.  Years outside the table
        are clamped to the nearest available year.

        Args:
            df: DataFrame with ``cost_usd_mm`` and ``year_drilling`` columns.
            base_year: Reference year for real values.

        Returns:
            Copy of df with additional ``cost_usd_mm_real`` column.
        """
        base_index = self._get_inflation_index(base_year)
        result = df.copy()
        result["cost_usd_mm_real"] = result.apply(
            lambda row: row["cost_usd_mm"]
            * base_index
            / self._get_inflation_index(int(row["year_drilling"])),
            axis=1,
        )
        return result

    def validate_schema(self, df: pd.DataFrame) -> List[str]:
        """Validate a DataFrame against the sanctioned project schema.

        Args:
            df: DataFrame to validate.

        Returns:
            List of error strings (empty list means valid).
        """
        errors: List[str] = []

        if df.empty:
            errors.append("DataFrame is empty")
            return errors

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        for col in missing:
            errors.append(f"Missing required column: {col}")

        if "cost_usd_mm" in df.columns:
            if (df["cost_usd_mm"] <= 0).any():
                errors.append(
                    "cost_usd_mm contains non-positive values"
                )

        if "water_depth_m" in df.columns:
            if (df["water_depth_m"] < 0).any():
                errors.append("water_depth_m contains negative values")

        return errors

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_record(self, rng: np.random.Generator, region: str, idx: int) -> dict:
        """Generate a single synthetic record for the given region."""
        operators = _OPERATORS_BY_REGION.get(region, ["Generic Operator"])
        operator = str(rng.choice(operators))

        year_sanction = int(rng.integers(2010, 2023))
        year_drilling = int(year_sanction + rng.integers(1, 4))

        water_depth_m, well_depth_m, rig_type, activity_type, cost_usd_mm = (
            self._sample_depth_and_cost(rng, region)
        )

        hpht = bool(well_depth_m > 6000.0 and rng.random() < 0.4)
        subsea = water_depth_m > 50.0

        water_band = classify_water_depth_band(water_depth_m)
        well_band = classify_well_depth_band(well_depth_m)

        if hpht:
            cost_usd_mm *= float(rng.uniform(1.1, 1.4))

        confidence = ConfidenceLevel.HIGH if rng.random() < 0.4 else (
            ConfidenceLevel.MEDIUM if rng.random() < 0.6 else ConfidenceLevel.LOW
        )

        return {
            "project_name": f"Project_{region.upper()}_{idx:04d}",
            "region": region,
            "water_depth_m": round(float(water_depth_m), 1),
            "water_depth_band": water_band.value,
            "well_depth_m": round(float(well_depth_m), 1),
            "well_depth_band": well_band.value,
            "operator": operator,
            "year_sanction": year_sanction,
            "year_drilling": year_drilling,
            "rig_type": rig_type.value,
            "activity_type": activity_type.value,
            "hpht": hpht,
            "subsea": subsea,
            "cost_usd_mm": round(float(cost_usd_mm), 2),
            "cost_type": CostType.WELL_COST.value,
            "source": f"Synthetic_{year_drilling}",
            "confidence": confidence.value,
        }

    @staticmethod
    def _sample_depth_and_cost(
        rng: np.random.Generator, region: str
    ) -> tuple[float, float, RigType, ActivityType, float]:
        """Sample water depth, well depth, rig type, activity type, and cost."""
        # Water depth distribution varies by region
        if region == "gom":
            water_depth_m = float(rng.choice(
                [rng.uniform(50, 300), rng.uniform(300, 1524),
                 rng.uniform(1524, 3048), rng.uniform(3048, 3600)],
                p=[0.20, 0.25, 0.35, 0.20],
            ))
        elif region == "brazil":
            water_depth_m = float(rng.choice(
                [rng.uniform(100, 500), rng.uniform(500, 1524),
                 rng.uniform(1524, 3000), rng.uniform(3000, 3500)],
                p=[0.10, 0.20, 0.45, 0.25],
            ))
        elif region == "north_sea":
            water_depth_m = float(rng.choice(
                [rng.uniform(50, 300), rng.uniform(300, 1524),
                 rng.uniform(1524, 2000), rng.uniform(2000, 2500)],
                p=[0.35, 0.35, 0.20, 0.10],
            ))
        else:
            water_depth_m = float(rng.choice(
                [rng.uniform(50, 300), rng.uniform(300, 1524),
                 rng.uniform(1524, 2500)],
                p=[0.25, 0.40, 0.35],
            ))

        # Well depth: deeper in deeper water
        if water_depth_m > 1524:
            well_depth_m = float(rng.uniform(4000, 9500))
        elif water_depth_m > 300:
            well_depth_m = float(rng.uniform(3000, 7000))
        else:
            well_depth_m = float(rng.uniform(1000, 5000))

        # Rig type from water depth
        if water_depth_m < 150:
            rig_type = RigType.JACK_UP
        elif water_depth_m < 1000:
            rig_type = RigType.SEMI_SUB
        else:
            rig_type = RigType.DRILLSHIP

        # Activity type — use integer index to avoid numpy returning numpy.str_
        _activity_choices = [
            ActivityType.DRILLING,
            ActivityType.COMPLETION,
            ActivityType.INTERVENTION,
        ]
        activity_idx = int(
            rng.choice(len(_activity_choices), p=[0.55, 0.35, 0.10])
        )
        activity_type = _activity_choices[activity_idx]

        # Cost based on depth/region
        base_day_rate = _proxy_day_rate(water_depth_m, region)
        if activity_type == ActivityType.DRILLING:
            days = float(rng.uniform(30, 180))
            cost_usd_mm = base_day_rate * days / 1_000_000
        elif activity_type == ActivityType.COMPLETION:
            days = float(rng.uniform(20, 90))
            cost_usd_mm = base_day_rate * 0.65 * days / 1_000_000
        else:
            days = float(rng.uniform(5, 30))
            cost_usd_mm = base_day_rate * 0.25 * days / 1_000_000

        # Add noise
        cost_usd_mm *= float(rng.uniform(0.8, 1.4))
        cost_usd_mm = max(cost_usd_mm, 0.5)

        return water_depth_m, well_depth_m, rig_type, activity_type, cost_usd_mm

    @staticmethod
    def _get_inflation_index(year: int) -> float:
        """Return CPI index for year, clamping to table bounds."""
        if year in _INFLATION_INDEX:
            return _INFLATION_INDEX[year]
        min_year = min(_INFLATION_INDEX.keys())
        max_year = max(_INFLATION_INDEX.keys())
        if year < min_year:
            return _INFLATION_INDEX[min_year]
        return _INFLATION_INDEX[max_year]


def _proxy_day_rate(water_depth_m: float, region: str) -> float:
    """Rough proxy day rate (USD/day) for synthetic cost generation."""
    # Base deepwater rate by region
    region_mult = {
        "gom": 1.00,
        "north_sea": 1.25,
        "brazil": 1.05,
        "west_africa": 0.95,
        "asia_pacific": 0.90,
    }.get(region, 1.00)

    if water_depth_m <= 300:
        base = 100_000
    elif water_depth_m <= 1524:
        base = 260_000
    elif water_depth_m <= 3048:
        base = 450_000
    else:
        base = 540_000

    return base * region_mult
