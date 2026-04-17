# ABOUTME: Unit tests for WRK-171 multivariate cost prediction model.
# ABOUTME: Covers linear regression training, cross-validation, proxy comparison,
# ABOUTME: and confidence interval generation.

"""Unit tests for worldenergydata.bsee.analysis.cost.cost_calibration."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.cost.cost_calibration import (
    CalibrationReport,
    MultivariateCalibration,
)
from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    WaterDepthBand,
    WellDepthBand,
)
from worldenergydata.bsee.analysis.cost.sanctioned_dataset import (
    SanctionedProjectDataset,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def calibrator() -> MultivariateCalibration:
    return MultivariateCalibration()


@pytest.fixture()
def training_df() -> pd.DataFrame:
    return SanctionedProjectDataset().synthetic_dataset(n_records=150, seed=42)


@pytest.fixture()
def fitted_calibrator(calibrator, training_df) -> MultivariateCalibration:
    calibrator.fit(training_df)
    return calibrator


# ---------------------------------------------------------------------------
# TestFit
# ---------------------------------------------------------------------------


class TestFit:
    def test_fit_returns_self(self, calibrator, training_df):
        result = calibrator.fit(training_df)
        assert result is calibrator

    def test_fitted_flag_set_after_fit(self, calibrator, training_df):
        calibrator.fit(training_df)
        assert calibrator.is_fitted

    def test_predict_raises_before_fit(self, calibrator):
        with pytest.raises(RuntimeError, match="fit\\(\\)"):
            calibrator.predict(
                region="gom",
                water_depth_m=1500.0,
                well_depth_m=8000.0,
                activity_type=ActivityType.DRILLING,
                year=2022,
            )

    def test_fit_empty_dataframe_raises_value_error(self, calibrator):
        with pytest.raises(ValueError, match="empty"):
            calibrator.fit(pd.DataFrame())

    def test_fit_missing_column_raises_value_error(self, calibrator):
        bad_df = pd.DataFrame({"region": ["gom"], "cost_usd_mm": [100.0]})
        with pytest.raises(ValueError, match="missing"):
            calibrator.fit(bad_df)


# ---------------------------------------------------------------------------
# TestPredict
# ---------------------------------------------------------------------------


class TestPredict:
    def test_predict_returns_positive_float(self, fitted_calibrator):
        result = fitted_calibrator.predict(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        assert isinstance(result, float)
        assert result > 0.0

    def test_deepwater_more_expensive_than_shallow(self, fitted_calibrator):
        shallow = fitted_calibrator.predict(
            region="gom",
            water_depth_m=100.0,
            well_depth_m=3000.0,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        deep = fitted_calibrator.predict(
            region="gom",
            water_depth_m=2000.0,
            well_depth_m=9000.0,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        assert deep > shallow

    def test_predict_with_confidence_interval_returns_tuple(self, fitted_calibrator):
        point, lower, upper = fitted_calibrator.predict_with_ci(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            activity_type=ActivityType.DRILLING,
            year=2022,
        )
        assert lower <= point <= upper

    def test_hpht_premium_in_prediction(self, fitted_calibrator):
        standard = fitted_calibrator.predict(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            activity_type=ActivityType.DRILLING,
            year=2022,
            hpht=False,
        )
        hpht = fitted_calibrator.predict(
            region="gom",
            water_depth_m=1500.0,
            well_depth_m=8000.0,
            activity_type=ActivityType.DRILLING,
            year=2022,
            hpht=True,
        )
        assert hpht >= standard


# ---------------------------------------------------------------------------
# TestCalibrationReport
# ---------------------------------------------------------------------------


class TestCalibrationReport:
    def test_report_raises_before_fit(self, calibrator):
        with pytest.raises(RuntimeError, match="fit\\(\\)"):
            calibrator.calibration_report()

    def test_report_is_calibration_report_type(self, fitted_calibrator):
        report = fitted_calibrator.calibration_report()
        assert isinstance(report, CalibrationReport)

    def test_report_rmse_non_negative(self, fitted_calibrator):
        report = fitted_calibrator.calibration_report()
        assert report.rmse_usd_mm >= 0.0

    def test_report_r_squared_in_range(self, fitted_calibrator):
        report = fitted_calibrator.calibration_report()
        assert -1.0 <= report.r_squared <= 1.0

    def test_report_n_records_matches_training(self, fitted_calibrator, training_df):
        report = fitted_calibrator.calibration_report()
        assert report.n_training_records == len(training_df)

    def test_report_to_dataframe_has_rows(self, fitted_calibrator):
        report = fitted_calibrator.calibration_report()
        df = report.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_proxy_comparison_has_bias_pct(self, fitted_calibrator):
        report = fitted_calibrator.calibration_report()
        comparisons = report.proxy_comparisons
        assert len(comparisons) > 0
        for comp in comparisons:
            assert hasattr(comp, "bias_pct")
            assert isinstance(comp.bias_pct, float)


# ---------------------------------------------------------------------------
# TestValidationMetrics
# ---------------------------------------------------------------------------


class TestValidationMetrics:
    def test_cross_validation_returns_metrics_dict(self, calibrator, training_df):
        metrics = calibrator.cross_validate(training_df, n_folds=3)
        assert isinstance(metrics, dict)
        assert "rmse_mean" in metrics
        assert "rmse_std" in metrics
        assert "r2_mean" in metrics

    def test_rmse_mean_positive(self, calibrator, training_df):
        metrics = calibrator.cross_validate(training_df, n_folds=3)
        assert metrics["rmse_mean"] > 0.0

    def test_feature_importance_after_fit(self, fitted_calibrator):
        importance = fitted_calibrator.feature_importance()
        assert isinstance(importance, dict)
        assert len(importance) > 0
