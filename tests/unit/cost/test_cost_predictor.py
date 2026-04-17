"""
ABOUTME: Tests for CostPredictor multivariate linear regression model.
ABOUTME: Verifies training, prediction, cross-validation, and feature importance.
"""

from __future__ import annotations

import numpy as np
import pytest

from worldenergydata.cost.calibration.cost_predictor import (
    CostPredictor,
    PredictionResult,
)
from worldenergydata.cost.data_collection.calibration_schema import (
    ActivityType,
    Confidence,
    CostDataPoint,
    CostType,
    RigType,
    SubseaType,
    WaterDepthBand,
    WellDepthBand,
)
from worldenergydata.cost.data_collection.public_dataset import load_public_dataset

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def public_dataset() -> list[CostDataPoint]:
    """Load and return the full public dataset."""
    return load_public_dataset()


@pytest.fixture(scope="module")
def trained_predictor(public_dataset) -> CostPredictor:
    """Return a CostPredictor fitted on the full public dataset."""
    predictor = CostPredictor()
    predictor.fit(public_dataset)
    return predictor


# ---------------------------------------------------------------------------
# Instantiation tests
# ---------------------------------------------------------------------------


class TestCostPredictorInstantiation:
    """CostPredictor initialises correctly before fitting."""

    def test_predictor_instantiates(self):
        """CostPredictor() creates an instance without error."""
        predictor = CostPredictor()
        assert predictor is not None

    def test_predictor_not_fitted_initially(self):
        """is_fitted returns False before calling fit()."""
        predictor = CostPredictor()
        assert predictor.is_fitted is False

    def test_predict_before_fit_raises(self):
        """Calling predict before fit raises RuntimeError."""
        predictor = CostPredictor()
        record = load_public_dataset()[0]
        with pytest.raises(RuntimeError, match="not fitted"):
            predictor.predict(record)


# ---------------------------------------------------------------------------
# Training tests
# ---------------------------------------------------------------------------


class TestCostPredictorFit:
    """CostPredictor.fit() trains on CostDataPoint list."""

    def test_fit_on_public_dataset_succeeds(self, public_dataset):
        """fit() runs without exception on the public dataset."""
        predictor = CostPredictor()
        predictor.fit(public_dataset)
        assert predictor.is_fitted is True

    def test_fit_requires_at_least_five_records(self):
        """fit() with fewer than 5 records raises ValueError."""
        tiny = load_public_dataset()[:3]
        predictor = CostPredictor()
        with pytest.raises(ValueError, match="at least"):
            predictor.fit(tiny)

    def test_training_r2_non_negative(self, trained_predictor, public_dataset):
        """Training R² should be >= 0 (model explains at least some variance)."""
        score = trained_predictor.training_r2_score(public_dataset)
        assert score >= 0.0


# ---------------------------------------------------------------------------
# Prediction tests
# ---------------------------------------------------------------------------


class TestCostPredictorPredict:
    """CostPredictor.predict() returns PredictionResult with expected fields."""

    def test_predict_returns_prediction_result(self, trained_predictor, public_dataset):
        """predict() returns a PredictionResult instance."""
        result = trained_predictor.predict(public_dataset[0])
        assert isinstance(result, PredictionResult)

    def test_prediction_cost_positive(self, trained_predictor, public_dataset):
        """Predicted cost_usd_mm should be > 0."""
        result = trained_predictor.predict(public_dataset[0])
        assert result.cost_usd_mm > 0.0

    def test_prediction_includes_confidence_interval(
        self, trained_predictor, public_dataset
    ):
        """PredictionResult includes lower and upper confidence bounds."""
        result = trained_predictor.predict(public_dataset[0])
        assert result.ci_lower_usd_mm is not None
        assert result.ci_upper_usd_mm is not None
        assert result.ci_lower_usd_mm <= result.cost_usd_mm <= result.ci_upper_usd_mm

    def test_predict_batch_returns_list(self, trained_predictor, public_dataset):
        """predict_batch() returns a list of PredictionResult of correct length."""
        subset = public_dataset[:5]
        results = trained_predictor.predict_batch(subset)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_deeper_water_predicts_higher_cost(self, trained_predictor, public_dataset):
        """Ultra-deep water record from dataset predicts higher cost than a shallow record.

        Compares the Liza Phase 1 (ultra-deep, West Africa, $3.2B) prediction against
        the Solveig Phase 1 (shallow NCS, $400M) prediction.  Both are in-sample records
        so the model should reproduce the broad ordering from the training data.
        """
        # Find shallow and deep records from the public dataset
        shallow = next(
            r
            for r in public_dataset
            if r.water_depth_band == WaterDepthBand.SHALLOW and r.cost_usd_mm < 1000.0
        )
        deep = next(
            r
            for r in public_dataset
            if r.water_depth_band == WaterDepthBand.ULTRA_DEEP
            and r.cost_usd_mm > 3000.0
        )

        shallow_pred = trained_predictor.predict(shallow)
        deep_pred = trained_predictor.predict(deep)
        # Deep ultra-large project should predict a higher cost than
        # the small shallow project — both in-sample.
        assert deep_pred.cost_usd_mm > shallow_pred.cost_usd_mm


# ---------------------------------------------------------------------------
# Feature importance tests
# ---------------------------------------------------------------------------


class TestCostPredictorFeatureImportance:
    """CostPredictor exposes feature coefficients/names after fitting."""

    def test_feature_names_not_empty(self, trained_predictor):
        """feature_names returns a non-empty list after fitting."""
        names = trained_predictor.feature_names
        assert isinstance(names, list)
        assert len(names) > 0

    def test_coefficients_length_matches_features(self, trained_predictor):
        """Length of coefficients matches length of feature_names."""
        names = trained_predictor.feature_names
        coefs = trained_predictor.coefficients
        assert len(coefs) == len(names)


# ---------------------------------------------------------------------------
# Cross-validation test
# ---------------------------------------------------------------------------


class TestCostPredictorCrossValidation:
    """cross_validate() returns meaningful scores."""

    def test_cross_validate_returns_scores(self, public_dataset):
        """cross_validate() returns a dict with mean and std R² scores."""
        predictor = CostPredictor()
        scores = predictor.cross_validate(public_dataset, cv=3)
        assert "mean_r2" in scores
        assert "std_r2" in scores
        assert isinstance(scores["mean_r2"], float)
        assert isinstance(scores["std_r2"], float)

    def test_cross_validate_r2_in_valid_range(self, public_dataset):
        """Cross-validated R² should be <= 1.0."""
        predictor = CostPredictor()
        scores = predictor.cross_validate(public_dataset, cv=3)
        assert scores["mean_r2"] <= 1.0
