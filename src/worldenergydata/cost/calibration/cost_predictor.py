"""
ABOUTME: Multivariate cost predictor using linear regression on sanctioned-project data.
ABOUTME: Features: water depth, well depth, region, rig type, year, HPHT, subsea type.

Design decisions
----------------
- **Linear regression first** — interpretable and auditable for engineering use.
  A gradient-boosted model is a Phase 3 enhancement once dataset reaches >100 rows.
- **Log-transform of target** — cost_usd_mm spans 3 orders of magnitude; log scale
  stabilises variance and gives multiplicative (percentage) error semantics.
- **Bootstrap confidence intervals** — 200-sample bootstrap gives CI without
  parametric assumptions; fast enough on <200 data points.
- **Inflation adjustment** — applied at fit time; costs are scaled to a common
  base year (2020) using a fixed upstream CAPEX escalation factor of 3% per year.
  This is a simplification of the IHS CERA UCCI; replace with real index data
  when available in Phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

from worldenergydata.cost.data_collection.calibration_schema import CostDataPoint


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_YEAR = 2020
_ESCALATION_RATE = 0.03  # 3 % per year — simplified upstream CAPEX escalation
_BOOTSTRAP_SAMPLES = 200
_CI_PERCENTILE_LOW = 5.0
_CI_PERCENTILE_HIGH = 95.0
_MIN_RECORDS_FOR_FIT = 5


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------


@dataclass
class PredictionResult:
    """Cost prediction with confidence interval.

    Attributes
    ----------
    cost_usd_mm:
        Point estimate of cost in USD millions.
    ci_lower_usd_mm:
        Lower bound of the 90 % confidence interval (USD MM).
    ci_upper_usd_mm:
        Upper bound of the 90 % confidence interval (USD MM).
    source_record_count:
        Number of training records used to fit the model.
    """

    cost_usd_mm: float
    ci_lower_usd_mm: float
    ci_upper_usd_mm: float
    source_record_count: int


# ---------------------------------------------------------------------------
# Feature helpers
# ---------------------------------------------------------------------------


def _inflate_to_base(cost_usd_mm: float, year: int) -> float:
    """Adjust a cost figure to the base year using a fixed escalation rate.

    Parameters
    ----------
    cost_usd_mm:
        Reported cost in USD MM.
    year:
        Year of FID / sanction.

    Returns
    -------
    float
        Inflation-adjusted cost in USD MM (base year = _BASE_YEAR).
    """
    delta = _BASE_YEAR - year
    return cost_usd_mm * ((1.0 + _ESCALATION_RATE) ** delta)


def _extract_features(records: list[CostDataPoint]) -> tuple[np.ndarray, list[str]]:
    """Build feature matrix from a list of CostDataPoint records.

    Returns
    -------
    tuple[np.ndarray, list[str]]
        (X matrix of shape (n_samples, n_features), list of raw feature dicts)
    """
    rows = []
    for rec in records:
        rows.append(
            {
                "water_depth_m": rec.water_depth_m,
                "well_depth_m": rec.well_depth_m if rec.well_depth_m is not None else 0.0,
                "year_sanction": float(rec.year_sanction),
                "hpht": 1.0 if rec.hpht else 0.0,
                "subsea": rec.subsea.value,
                "region": rec.region,
                "rig_type": rec.rig_type.value,
                "water_depth_band": rec.water_depth_band.value,
            }
        )
    return rows


def _build_pipeline() -> Pipeline:
    """Construct the sklearn preprocessing + linear regression pipeline."""
    numeric_features = ["water_depth_m", "well_depth_m", "year_sanction", "hpht"]
    categorical_features = ["subsea", "region", "rig_type", "water_depth_band"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_features,
            ),
        ]
    )
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", LinearRegression()),
        ]
    )


def _dicts_to_array(rows: list[dict]) -> "pd.DataFrame":  # noqa: F821
    """Convert list of feature dicts to a DataFrame for sklearn."""
    import pandas as pd

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CostPredictor
# ---------------------------------------------------------------------------


class CostPredictor:
    """Multivariate linear regression cost predictor.

    Usage
    -----
    >>> from worldenergydata.cost.data_collection.public_dataset import load_public_dataset
    >>> predictor = CostPredictor()
    >>> predictor.fit(load_public_dataset())
    >>> result = predictor.predict(some_record)
    >>> print(result.cost_usd_mm, result.ci_lower_usd_mm, result.ci_upper_usd_mm)
    """

    def __init__(self) -> None:
        self._pipeline: Optional[Pipeline] = None
        self._train_records: list[CostDataPoint] = []
        self._feature_names_out: list[str] = []
        self._n_train: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def is_fitted(self) -> bool:
        """Return True if the model has been trained."""
        return self._pipeline is not None

    @property
    def feature_names(self) -> list[str]:
        """Return ordered list of feature names used by the fitted model."""
        self._assert_fitted()
        return list(self._feature_names_out)

    @property
    def coefficients(self) -> list[float]:
        """Return linear regression coefficients in feature_names order."""
        self._assert_fitted()
        regressor = self._pipeline.named_steps["regressor"]
        return list(regressor.coef_)

    def fit(self, records: list[CostDataPoint]) -> "CostPredictor":
        """Train the cost prediction model on sanctioned-project records.

        Parameters
        ----------
        records:
            List of CostDataPoint instances.  Minimum _MIN_RECORDS_FOR_FIT.

        Returns
        -------
        CostPredictor
            self — for chaining.

        Raises
        ------
        ValueError
            If fewer than _MIN_RECORDS_FOR_FIT records are supplied.
        """
        if len(records) < _MIN_RECORDS_FOR_FIT:
            raise ValueError(
                f"CostPredictor requires at least {_MIN_RECORDS_FOR_FIT} records "
                f"to fit; received {len(records)}."
            )

        self._train_records = list(records)
        self._n_train = len(records)

        X_dicts = _extract_features(records)
        X_df = _dicts_to_array(X_dicts)

        # Log-transform target: stabilise variance across the cost range
        y_raw = np.array(
            [_inflate_to_base(r.cost_usd_mm, r.year_sanction) for r in records]
        )
        y = np.log(y_raw)

        pipeline = _build_pipeline()
        pipeline.fit(X_df, y)
        self._pipeline = pipeline

        # Extract feature names after fitting
        preprocessor = pipeline.named_steps["preprocessor"]
        num_names = ["water_depth_m", "well_depth_m", "year_sanction", "hpht"]
        cat_encoder = preprocessor.named_transformers_["cat"]
        cat_names = list(cat_encoder.get_feature_names_out(
            ["subsea", "region", "rig_type", "water_depth_band"]
        ))
        self._feature_names_out = num_names + cat_names

        return self

    def predict(self, record: CostDataPoint) -> PredictionResult:
        """Predict cost for a single record with a 90 % bootstrap CI.

        Parameters
        ----------
        record:
            A CostDataPoint (does not need to be in training set).

        Returns
        -------
        PredictionResult

        Raises
        ------
        RuntimeError
            If the model has not been fitted.
        """
        self._assert_fitted()
        point_estimate = self._predict_single_log(record)

        # Bootstrap CI: resample training set, refit, predict
        ci_lower, ci_upper = self._bootstrap_ci(record)

        return PredictionResult(
            cost_usd_mm=point_estimate,
            ci_lower_usd_mm=ci_lower,
            ci_upper_usd_mm=ci_upper,
            source_record_count=self._n_train,
        )

    def predict_batch(self, records: list[CostDataPoint]) -> list[PredictionResult]:
        """Predict costs for a list of records (point estimates only).

        Parameters
        ----------
        records:
            List of CostDataPoint instances.

        Returns
        -------
        list[PredictionResult]
        """
        return [self.predict(r) for r in records]

    def training_r2_score(self, records: list[CostDataPoint]) -> float:
        """Compute R² of the fitted model on the supplied records.

        Parameters
        ----------
        records:
            Records to score against.

        Returns
        -------
        float
            R² in [-inf, 1.0]; 1.0 = perfect fit.
        """
        self._assert_fitted()
        X_dicts = _extract_features(records)
        X_df = _dicts_to_array(X_dicts)
        y_raw = np.array(
            [_inflate_to_base(r.cost_usd_mm, r.year_sanction) for r in records]
        )
        y = np.log(y_raw)
        return float(self._pipeline.score(X_df, y))

    def cross_validate(
        self, records: list[CostDataPoint], cv: int = 5
    ) -> dict[str, float]:
        """Run k-fold cross-validation and return mean/std R² scores.

        Parameters
        ----------
        records:
            Full dataset to cross-validate on.
        cv:
            Number of folds (default 5).

        Returns
        -------
        dict with keys 'mean_r2' and 'std_r2'.
        """
        X_dicts = _extract_features(records)
        X_df = _dicts_to_array(X_dicts)
        y_raw = np.array(
            [_inflate_to_base(r.cost_usd_mm, r.year_sanction) for r in records]
        )
        y = np.log(y_raw)

        pipeline = _build_pipeline()
        scores = cross_val_score(pipeline, X_df, y, cv=cv, scoring="r2")
        return {
            "mean_r2": float(np.mean(scores)),
            "std_r2": float(np.std(scores)),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_fitted(self) -> None:
        """Raise RuntimeError if model is not yet fitted."""
        if self._pipeline is None:
            raise RuntimeError(
                "CostPredictor is not fitted. Call fit() before predict()."
            )

    def _predict_single_log(self, record: CostDataPoint) -> float:
        """Return point-estimate cost_usd_mm for one record."""
        X_dicts = _extract_features([record])
        X_df = _dicts_to_array(X_dicts)
        log_pred = self._pipeline.predict(X_df)[0]
        # Reverse log transform, then reverse inflation adjustment back to
        # the record's own year (so the prediction is in nominal USD MM).
        cost_base_year = float(np.exp(log_pred))
        delta = record.year_sanction - _BASE_YEAR
        return cost_base_year * ((1.0 + _ESCALATION_RATE) ** delta)

    def _bootstrap_ci(
        self, record: CostDataPoint
    ) -> tuple[float, float]:
        """Estimate 90 % CI via bootstrap resampling of training data."""
        rng = np.random.default_rng(seed=42)
        bootstrap_preds: list[float] = []

        X_dicts = _extract_features(self._train_records)
        X_df = _dicts_to_array(X_dicts)
        y_raw = np.array(
            [_inflate_to_base(r.cost_usd_mm, r.year_sanction)
             for r in self._train_records]
        )
        y = np.log(y_raw)
        n = len(self._train_records)

        X_query_dicts = _extract_features([record])
        X_query_df = _dicts_to_array(X_query_dicts)

        for _ in range(_BOOTSTRAP_SAMPLES):
            idx = rng.integers(0, n, size=n)
            X_boot = X_df.iloc[idx]
            y_boot = y[idx]
            pipe = _build_pipeline()
            try:
                pipe.fit(X_boot, y_boot)
                log_pred = pipe.predict(X_query_df)[0]
                cost_base = float(np.exp(log_pred))
                delta = record.year_sanction - _BASE_YEAR
                bootstrap_preds.append(cost_base * ((1.0 + _ESCALATION_RATE) ** delta))
            except Exception:
                # Some bootstrap samples may be degenerate; skip them
                continue

        if len(bootstrap_preds) < 10:
            # Fall back to ±50 % when bootstrap fails (sparse data)
            point = self._predict_single_log(record)
            return point * 0.5, point * 1.5

        low = float(np.percentile(bootstrap_preds, _CI_PERCENTILE_LOW))
        high = float(np.percentile(bootstrap_preds, _CI_PERCENTILE_HIGH))
        return low, high
