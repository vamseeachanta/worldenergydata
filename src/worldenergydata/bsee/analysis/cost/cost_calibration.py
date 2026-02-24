# ABOUTME: WRK-171 multivariate cost prediction model for sanctioned project benchmarking.
# ABOUTME: Linear regression baseline with interaction terms, k-fold CV, and proxy comparison.

"""Multivariate cost prediction model (WRK-171).

Implements:
- ``MultivariateCalibration.fit(df)`` — train on sanctioned project dataset
- ``MultivariateCalibration.predict(...)`` — point prediction (USD MM)
- ``MultivariateCalibration.predict_with_ci(...)`` — prediction with bootstrap CI
- ``MultivariateCalibration.cross_validate(df, n_folds)`` — k-fold CV metrics
- ``MultivariateCalibration.calibration_report()`` — CalibrationReport with proxy comparison

The baseline model is an OLS linear regression with encoded categorical features
(region, water_depth_band, activity_type, hpht, subsea) and numeric features
(water_depth_m, well_depth_m, year_drilling).  Interpretability is non-negotiable
per WRK-171 notes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    CalibrationComparison,
    ConfidenceLevel,
    WaterDepthBand,
    classify_water_depth_band,
)
from worldenergydata.bsee.analysis.cost.sanctioned_dataset import REQUIRED_COLUMNS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BOOTSTRAP_SAMPLES = 200
_DEFAULT_CI_ALPHA = 0.10  # 90% CI

_REQUIRED_FIT_COLUMNS = {
    "region",
    "water_depth_m",
    "well_depth_m",
    "activity_type",
    "hpht",
    "cost_usd_mm",
    "year_drilling",
}

# Proxy rates (USD/day) used as baseline for comparison; from day_rates.yml 2022 values
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

_PROXY_REGIONS = list(_PROXY_RATES_2022.keys())


# ---------------------------------------------------------------------------
# CalibrationReport
# ---------------------------------------------------------------------------


@dataclass
class CalibrationReport:
    """Summary of MultivariateCalibration training and proxy comparison."""

    n_training_records: int
    rmse_usd_mm: float
    r_squared: float
    features_used: list[str]
    proxy_comparisons: list[CalibrationComparison] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Return a DataFrame summarising proxy comparison results."""
        if not self.proxy_comparisons:
            return pd.DataFrame()
        rows = []
        for comp in self.proxy_comparisons:
            rows.append(
                {
                    "region": comp.region,
                    "water_depth_band": comp.water_depth_band.value,
                    "activity_type": comp.activity_type.value,
                    "proxy_rate_usd_day": comp.proxy_rate_usd_day,
                    "calibrated_rate_usd_day": comp.calibrated_rate_usd_day,
                    "bias_pct": round(comp.bias_pct, 2),
                    "n_data_points": comp.n_data_points,
                    "rmse_usd_mm": comp.rmse_usd_mm,
                    "confidence": comp.confidence.value,
                }
            )
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# MultivariateCalibration
# ---------------------------------------------------------------------------


class MultivariateCalibration:
    """OLS linear regression cost predictor for sanctioned project data.

    Encodes categorical features (region, water_depth_band, activity_type, hpht)
    as one-hot vectors and fits ordinary least squares.  Interpretability
    is preserved: feature coefficients are accessible via ``feature_importance()``.

    Usage::

        cal = MultivariateCalibration()
        cal.fit(training_df)
        cost_mm = cal.predict(region="gom", water_depth_m=1500, ...)
        report = cal.calibration_report()
    """

    def __init__(self) -> None:
        self._fitted = False
        self._coeffs: Optional[np.ndarray] = None
        self._feature_names: list[str] = []
        self._report: Optional[CalibrationReport] = None
        self._training_df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_fitted(self) -> bool:
        """True after ``fit()`` has been called successfully."""
        return self._fitted

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame) -> "MultivariateCalibration":
        """Fit OLS regression on the sanctioned project dataset.

        Args:
            df: DataFrame with at minimum the columns in _REQUIRED_FIT_COLUMNS.

        Returns:
            Self (chainable).

        Raises:
            ValueError: If df is empty or missing required columns.
        """
        if df.empty:
            raise ValueError(
                "Cannot fit on an empty DataFrame. "
                "Provide at least one record."
            )

        missing = _REQUIRED_FIT_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"Training DataFrame missing required columns: {sorted(missing)}"
            )

        self._training_df = df.copy()
        X, y, feature_names = self._build_feature_matrix(df)
        self._feature_names = feature_names
        self._coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        self._fitted = True
        self._report = self._build_report(df, X, y)
        return self

    def predict(
        self,
        region: str,
        water_depth_m: float,
        well_depth_m: float,
        activity_type: ActivityType,
        year: int,
        hpht: bool = False,
        subsea: bool = True,
    ) -> float:
        """Predict well cost (USD MM) for the given parameters.

        Args:
            region: Region key.
            water_depth_m: Water depth in metres.
            well_depth_m: Well TVD in metres.
            activity_type: Drilling / completion / intervention.
            year: Year of drilling.
            hpht: HPHT flag.
            subsea: Subsea flag.

        Returns:
            Predicted cost in USD MM (clamped to >=0.1).

        Raises:
            RuntimeError: If fit() has not been called.
        """
        self._assert_fitted()
        x = self._encode_single(
            region=region,
            water_depth_m=water_depth_m,
            well_depth_m=well_depth_m,
            activity_type=activity_type,
            year=year,
            hpht=hpht,
            subsea=subsea,
        )
        prediction = float(x @ self._coeffs)
        return max(prediction, 0.1)

    def predict_with_ci(
        self,
        region: str,
        water_depth_m: float,
        well_depth_m: float,
        activity_type: ActivityType,
        year: int,
        hpht: bool = False,
        subsea: bool = True,
        alpha: float = _DEFAULT_CI_ALPHA,
    ) -> tuple[float, float, float]:
        """Predict with bootstrap confidence interval.

        Returns:
            Tuple of (point_estimate, lower_bound, upper_bound).
        """
        self._assert_fitted()
        point = self.predict(
            region=region,
            water_depth_m=water_depth_m,
            well_depth_m=well_depth_m,
            activity_type=activity_type,
            year=year,
            hpht=hpht,
            subsea=subsea,
        )

        # Bootstrap residuals from training data
        df = self._training_df
        assert df is not None
        X, y, _ = self._build_feature_matrix(df)
        y_hat = X @ self._coeffs
        residuals = y - y_hat

        rng = np.random.default_rng(0)
        boot_preds = []
        for _ in range(_BOOTSTRAP_SAMPLES):
            boot_residual = rng.choice(residuals)
            boot_preds.append(point + float(boot_residual))

        lower = float(np.percentile(boot_preds, alpha / 2 * 100))
        upper = float(np.percentile(boot_preds, (1 - alpha / 2) * 100))
        lower = max(lower, 0.0)
        return point, lower, upper

    def cross_validate(
        self, df: pd.DataFrame, n_folds: int = 5
    ) -> dict[str, float]:
        """K-fold cross-validation on the provided dataset.

        Args:
            df: Dataset to cross-validate on.
            n_folds: Number of folds.

        Returns:
            Dict with ``rmse_mean``, ``rmse_std``, ``r2_mean``, ``r2_std``.
        """
        if df.empty:
            raise ValueError("Cannot cross-validate on an empty DataFrame.")

        indices = np.arange(len(df))
        np.random.default_rng(42).shuffle(indices)
        fold_size = len(df) // n_folds

        rmses: list[float] = []
        r2s: list[float] = []

        for fold in range(n_folds):
            start = fold * fold_size
            end = start + fold_size if fold < n_folds - 1 else len(df)
            val_idx = indices[start:end]
            train_idx = np.concatenate([indices[:start], indices[end:]])

            train_df = df.iloc[train_idx].reset_index(drop=True)
            val_df = df.iloc[val_idx].reset_index(drop=True)

            X_tr, y_tr, _ = self._build_feature_matrix(train_df)
            X_val, y_val, _ = self._build_feature_matrix(val_df)

            coeffs, _, _, _ = np.linalg.lstsq(X_tr, y_tr, rcond=None)
            y_hat = X_val @ coeffs

            ss_res = float(np.sum((y_val - y_hat) ** 2))
            ss_tot = float(np.sum((y_val - y_val.mean()) ** 2))
            rmse = float(np.sqrt(ss_res / max(len(y_val), 1)))
            r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
            r2 = float(np.clip(r2, -1.0, 1.0))

            rmses.append(rmse)
            r2s.append(r2)

        return {
            "rmse_mean": float(np.mean(rmses)),
            "rmse_std": float(np.std(rmses)),
            "r2_mean": float(np.mean(r2s)),
            "r2_std": float(np.std(r2s)),
        }

    def feature_importance(self) -> dict[str, float]:
        """Return absolute coefficient values as feature importance proxy.

        Returns:
            Dict mapping feature name to absolute coefficient value.

        Raises:
            RuntimeError: If fit() has not been called.
        """
        self._assert_fitted()
        assert self._coeffs is not None
        return {
            name: abs(float(coef))
            for name, coef in zip(self._feature_names, self._coeffs)
        }

    def calibration_report(self) -> CalibrationReport:
        """Return the calibration report generated during fit().

        Raises:
            RuntimeError: If fit() has not been called.
        """
        self._assert_fitted()
        assert self._report is not None
        return self._report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(
                "MultivariateCalibration.fit() must be called before "
                "predict() or calibration_report()."
            )

    def _build_feature_matrix(
        self, df: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Construct design matrix X and target y from DataFrame."""
        regions_all = sorted(_PROXY_REGIONS)
        activities_all = sorted(a.value for a in ActivityType)
        bands_all = sorted(b.value for b in WaterDepthBand)

        feature_names: list[str] = ["intercept"]
        rows = []
        y_vals = []

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

        # Build feature names only on first call (rows must be non-empty)
        if rows:
            feature_names = (
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

    def _encode_single(
        self,
        region: str,
        water_depth_m: float,
        well_depth_m: float,
        activity_type: ActivityType,
        year: int,
        hpht: bool,
        subsea: bool,
    ) -> np.ndarray:
        """Encode a single prediction request to a feature vector."""
        single_row = pd.DataFrame(
            [
                {
                    "region": region,
                    "water_depth_m": water_depth_m,
                    "well_depth_m": well_depth_m,
                    "activity_type": activity_type.value,
                    "year_drilling": year,
                    "hpht": hpht,
                    "subsea": subsea,
                    "cost_usd_mm": 0.0,  # placeholder; not used
                }
            ]
        )
        X, _, _ = self._build_feature_matrix(single_row)
        return X[0]

    def _build_report(
        self, df: pd.DataFrame, X: np.ndarray, y: np.ndarray
    ) -> CalibrationReport:
        """Compute in-sample metrics and proxy comparison."""
        assert self._coeffs is not None
        y_hat = X @ self._coeffs
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        n = len(y)
        rmse = float(np.sqrt(ss_res / max(n, 1)))
        r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        r2 = float(np.clip(r2, -1.0, 1.0))

        comparisons = self._build_proxy_comparisons(df)

        return CalibrationReport(
            n_training_records=n,
            rmse_usd_mm=round(rmse, 4),
            r_squared=round(r2, 4),
            features_used=list(self._feature_names),
            proxy_comparisons=comparisons,
        )

    def _build_proxy_comparisons(
        self, df: pd.DataFrame
    ) -> list[CalibrationComparison]:
        """Build CalibrationComparison entries for all proxy rate cells."""
        comparisons: list[CalibrationComparison] = []

        for region in _PROXY_REGIONS:
            for activity in [ActivityType.DRILLING, ActivityType.COMPLETION]:
                for band in WaterDepthBand:
                    proxy_key = f"{activity.value}__{band.value}"
                    proxy_rate = _PROXY_RATES_2022.get(region, {}).get(
                        proxy_key, 0.0
                    )
                    if proxy_rate == 0.0:
                        continue

                    # Estimate calibrated day rate: infer from cost/days proxy
                    # Use mid-range depth and 60 drilling days as reference
                    mid_depths = {
                        WaterDepthBand.SHALLOW: 150.0,
                        WaterDepthBand.MID: 900.0,
                        WaterDepthBand.DEEP: 2200.0,
                        WaterDepthBand.ULTRA_DEEP: 3300.0,
                    }
                    water_m = mid_depths[band]
                    ref_days = 60.0
                    ref_cost_mm = self.predict(
                        region=region,
                        water_depth_m=water_m,
                        well_depth_m=5000.0,
                        activity_type=activity,
                        year=2022,
                    )
                    calibrated_rate = (ref_cost_mm * 1_000_000) / ref_days

                    # Count data points in this cell
                    mask = (
                        (df["region"] == region)
                        & (df["activity_type"] == activity.value)
                    )
                    n_pts = int(mask.sum())

                    # Compute RMSE for this cell
                    cell_df = df[mask]
                    if len(cell_df) > 0:
                        x_cell, y_cell, _ = self._build_feature_matrix(cell_df)
                        y_hat_cell = x_cell @ self._coeffs  # type: ignore[operator]
                        cell_rmse = float(
                            np.sqrt(
                                np.mean((y_cell - y_hat_cell) ** 2)
                            )
                        )
                    else:
                        cell_rmse = 0.0

                    confidence = (
                        ConfidenceLevel.HIGH
                        if n_pts >= 5
                        else ConfidenceLevel.MEDIUM
                        if n_pts >= 1
                        else ConfidenceLevel.LOW
                    )

                    comparisons.append(
                        CalibrationComparison(
                            region=region,
                            water_depth_band=band,
                            activity_type=activity,
                            proxy_rate_usd_day=float(proxy_rate),
                            calibrated_rate_usd_day=round(calibrated_rate, 2),
                            n_data_points=n_pts,
                            rmse_usd_mm=round(cell_rmse, 4),
                            confidence=confidence,
                        )
                    )

        return comparisons
