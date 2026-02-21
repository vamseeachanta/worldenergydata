"""
ABOUTME: Data-driven calibration of decommissioning cost model constants.
ABOUTME: Fits parametric cost factors against BSEE platform removal records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from worldenergydata.decommissioning.cost_model import (
    _COST_FACTORS,
    DecommissioningCostEstimator,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CALIBRATION_ASSET_TYPES = {
    "jacket",
    "well_p_and_a",
    "subsea_tree",
    "pipeline_km",
    "fpso",
}

_REQUIRED_COLUMNS = {"asset_type", "water_depth_m", "weight_tonnes", "cost_musd", "year"}

# Blend weight: fitted vs baseline for base_musd
_FIT_BLEND_WEIGHT = 0.7

# Clamp range for fitted factors relative to baseline
_CLAMP_MIN_FACTOR = 0.5
_CLAMP_MAX_FACTOR = 2.0

MIN_RECORDS_FOR_REGRESSION = 3


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CalibrationFit:
    """Fit result for a single asset type."""

    asset_type: str
    n_records: int
    base_musd_fitted: float
    base_musd_baseline: float
    rmse_musd: float
    r_squared: float
    confidence: str   # "high" (n>=20), "medium" (n>=5), "low" (n<5)
    data_driven: bool


@dataclass
class CalibrationResult:
    """Aggregate result from CostModelCalibration.fit()."""

    asset_type: str
    total_records: int
    years_covered: float
    fits: list[CalibrationFit] = field(default_factory=list)
    coverage_pct: float = 0.0

    def to_dataframe(self) -> pd.DataFrame:
        """Return DataFrame with one row per CalibrationFit."""
        rows = [
            {
                "asset_type": f.asset_type,
                "n_records": f.n_records,
                "base_musd_fitted": f.base_musd_fitted,
                "base_musd_baseline": f.base_musd_baseline,
                "rmse_musd": f.rmse_musd,
                "r_squared": f.r_squared,
                "confidence": f.confidence,
                "data_driven": f.data_driven,
            }
            for f in self.fits
        ]
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Calibrator
# ---------------------------------------------------------------------------


class CostModelCalibration:
    """Fit parametric decommissioning cost constants to historical removal records.

    Usage::

        cal = CostModelCalibration()
        cal.fit(removal_df)
        estimator = DecommissioningCostEstimator.from_calibration(cal)
    """

    def __init__(self) -> None:
        self._fitted = False
        self._fitted_cost_factors: dict[str, dict] = {}
        self._result: Optional[CalibrationResult] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, removal_df: pd.DataFrame) -> "CostModelCalibration":
        """Fit calibration from historical removal records DataFrame.

        Expected columns: asset_type, water_depth_m, weight_tonnes, cost_musd, year.

        For each asset_type with >= 3 records:
          - Simple linear regression: cost_musd ~ base + per_tonne * weight + per_m * depth
          - If insufficient records: keep baseline constants
          - Blend: 0.7 * fitted_base + 0.3 * baseline_base (for base_musd only)
          - All fitted factors clamped to [0.5x, 2.0x] of baseline

        Returns:
            Self (chainable).
        """
        if removal_df.empty:
            self._fitted = True
            self._fitted_cost_factors = {k: dict(v) for k, v in _COST_FACTORS.items()}
            self._result = CalibrationResult(
                asset_type="all",
                total_records=0,
                years_covered=0.0,
                fits=self._build_fallback_fits(),
                coverage_pct=0.0,
            )
            return self

        missing = _REQUIRED_COLUMNS - set(removal_df.columns)
        if missing:
            raise ValueError(
                f"removal_df missing required columns: {sorted(missing)}"
            )

        years_covered = self._compute_years_covered(removal_df)
        total_records = len(removal_df)

        fits: list[CalibrationFit] = []
        updated_factors: dict[str, dict] = {k: dict(v) for k, v in _COST_FACTORS.items()}

        for asset_type in _CALIBRATION_ASSET_TYPES:
            subset = removal_df[removal_df["asset_type"] == asset_type].copy()
            fit = self._fit_asset_type(asset_type, subset, updated_factors)
            fits.append(fit)
            # Update in-memory factors with blended values
            if fit.data_driven:
                updated_factors[asset_type] = dict(_COST_FACTORS.get(asset_type, {}))
                updated_factors[asset_type]["base_musd"] = fit.base_musd_fitted

        # Cover types not in calibration set (spar, tlp) unchanged
        for atype in _COST_FACTORS:
            if atype not in updated_factors:
                updated_factors[atype] = dict(_COST_FACTORS[atype])

        self._fitted_cost_factors = updated_factors

        data_driven_count = sum(1 for f in fits if f.data_driven)
        coverage_pct = (
            (data_driven_count / len(_CALIBRATION_ASSET_TYPES)) * 100.0
            if _CALIBRATION_ASSET_TYPES
            else 0.0
        )

        self._result = CalibrationResult(
            asset_type="all",
            total_records=total_records,
            years_covered=years_covered,
            fits=fits,
            coverage_pct=coverage_pct,
        )
        self._fitted = True
        return self

    def calibration_result(self) -> CalibrationResult:
        """Return calibration result. Raises RuntimeError if fit() not called."""
        if not self._fitted:
            raise RuntimeError(
                "CostModelCalibration.fit() must be called before calibration_result()."
            )
        return self._result  # type: ignore[return-value]

    def fitted_factors(self) -> dict:
        """Return updated _COST_FACTORS dict with calibrated values.

        Raises:
            RuntimeError: If fit() has not been called.
        """
        if not self._fitted:
            raise RuntimeError(
                "CostModelCalibration.fit() must be called before fitted_factors()."
            )
        return self._fitted_cost_factors

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def synthetic_removal_dataframe(n_records: int = 100) -> pd.DataFrame:
        """Generate GoM-pattern platform removal records for testing.

        Columns: asset_type, water_depth_m, weight_tonnes, cost_musd, year, operator.
        Uses seeded rng(42).

        Args:
            n_records: Number of records to generate.

        Returns:
            DataFrame with realistic decommissioning removal records.
        """
        rng = np.random.default_rng(42)

        asset_types = ["jacket", "well_p_and_a", "subsea_tree", "pipeline_km", "fpso"]
        asset_weights = [0.40, 0.30, 0.15, 0.10, 0.05]

        operators = ["Shell", "BP", "Chevron", "ExxonMobil", "ConocoPhillips"]
        years = rng.integers(2010, 2024, size=n_records)

        chosen_types = rng.choice(asset_types, size=n_records, p=asset_weights)

        depths = np.zeros(n_records)
        weights = np.zeros(n_records)
        costs = np.zeros(n_records)

        for i, atype in enumerate(chosen_types):
            if atype == "jacket":
                depths[i] = rng.uniform(20, 200)
                weights[i] = rng.uniform(100, 2000)
                costs[i] = rng.uniform(3, 15)
            elif atype == "well_p_and_a":
                depths[i] = rng.uniform(1000, 5000)
                weights[i] = 0.0
                costs[i] = rng.uniform(8, 25)
            elif atype == "subsea_tree":
                depths[i] = rng.uniform(200, 2000)
                weights[i] = rng.uniform(10, 50)
                costs[i] = rng.uniform(1.5, 4)
            elif atype == "pipeline_km":
                depths[i] = rng.uniform(50, 300)
                weights[i] = 0.0
                costs[i] = rng.uniform(0.3, 1.5)
            else:  # fpso
                depths[i] = rng.uniform(100, 1500)
                weights[i] = rng.uniform(10000, 50000)
                costs[i] = rng.uniform(50, 200)

        return pd.DataFrame(
            {
                "asset_type": chosen_types,
                "water_depth_m": depths,
                "weight_tonnes": weights,
                "cost_musd": costs,
                "year": years.astype(int),
                "operator": rng.choice(operators, size=n_records),
            }
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fit_asset_type(
        self,
        asset_type: str,
        subset: pd.DataFrame,
        current_factors: dict[str, dict],
    ) -> CalibrationFit:
        """Fit linear regression for one asset type; fall back to baseline if < 3 records."""
        baseline_factors = _COST_FACTORS.get(asset_type, {})
        baseline_base = float(baseline_factors.get("base_musd", 1.0))
        n = len(subset)

        if n < MIN_RECORDS_FOR_REGRESSION:
            return CalibrationFit(
                asset_type=asset_type,
                n_records=n,
                base_musd_fitted=baseline_base,
                base_musd_baseline=baseline_base,
                rmse_musd=0.0,
                r_squared=0.0,
                confidence="low",
                data_driven=False,
            )

        # Build design matrix: [1, weight_tonnes, water_depth_m]
        X = np.column_stack([
            np.ones(n),
            subset["weight_tonnes"].to_numpy(dtype=float),
            subset["water_depth_m"].to_numpy(dtype=float),
        ])
        y = subset["cost_musd"].to_numpy(dtype=float)

        # Least-squares regression (ignoring rank warnings)
        coeffs, residuals, rank, _ = np.linalg.lstsq(X, y, rcond=None)

        fitted_base_raw = float(coeffs[0])

        # Clamp fitted base to [0.5x, 2.0x] of baseline
        low_clamp = baseline_base * _CLAMP_MIN_FACTOR
        high_clamp = baseline_base * _CLAMP_MAX_FACTOR
        fitted_base_clamped = float(np.clip(fitted_base_raw, low_clamp, high_clamp))

        # Blend with baseline
        blended_base = (
            _FIT_BLEND_WEIGHT * fitted_base_clamped
            + (1.0 - _FIT_BLEND_WEIGHT) * baseline_base
        )

        # Compute RMSE and R²
        y_hat = X @ coeffs
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        rmse = float(np.sqrt(ss_res / n))
        r_squared = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        r_squared = float(np.clip(r_squared, -1.0, 1.0))

        confidence: str
        if n >= 20:
            confidence = "high"
        elif n >= 5:
            confidence = "medium"
        else:
            confidence = "low"

        return CalibrationFit(
            asset_type=asset_type,
            n_records=n,
            base_musd_fitted=round(blended_base, 6),
            base_musd_baseline=baseline_base,
            rmse_musd=round(rmse, 6),
            r_squared=round(r_squared, 6),
            confidence=confidence,
            data_driven=True,
        )

    def _build_fallback_fits(self) -> list[CalibrationFit]:
        """Build fully baseline fits (used when DataFrame is empty)."""
        fits = []
        for asset_type in _CALIBRATION_ASSET_TYPES:
            baseline_base = float(_COST_FACTORS.get(asset_type, {}).get("base_musd", 1.0))
            fits.append(
                CalibrationFit(
                    asset_type=asset_type,
                    n_records=0,
                    base_musd_fitted=baseline_base,
                    base_musd_baseline=baseline_base,
                    rmse_musd=0.0,
                    r_squared=0.0,
                    confidence="low",
                    data_driven=False,
                )
            )
        return fits

    @staticmethod
    def _compute_years_covered(df: pd.DataFrame) -> float:
        """Compute years span from 'year' column."""
        if "year" not in df.columns or df.empty:
            return 1.0
        years = pd.to_numeric(df["year"], errors="coerce").dropna()
        if years.empty:
            return 1.0
        return float(max(years.max() - years.min(), 1.0))
