# ABOUTME: Unit tests for decommissioning cost model calibration from BSEE removal records.
# ABOUTME: Covers synthetic data, regression fit, calibration result, fitted factors, and from_calibration.

"""Unit tests for worldenergydata.decommissioning.cost_calibration."""

import pytest
import pandas as pd
import numpy as np

from worldenergydata.decommissioning.cost_calibration import (
    CalibrationFit,
    CalibrationResult,
    CostModelCalibration,
)
from worldenergydata.decommissioning.cost_model import (
    _COST_FACTORS,
    DecommissioningCostEstimator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def calibrator() -> CostModelCalibration:
    return CostModelCalibration()


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    return CostModelCalibration.synthetic_removal_dataframe(n_records=100)


@pytest.fixture()
def fitted_calibrator(synthetic_df) -> CostModelCalibration:
    cal = CostModelCalibration()
    cal.fit(synthetic_df)
    return cal


# ---------------------------------------------------------------------------
# TestSyntheticDataFrame
# ---------------------------------------------------------------------------


class TestSyntheticDataFrame:
    def test_shape_has_correct_columns(self, synthetic_df):
        expected_cols = {
            "asset_type",
            "water_depth_m",
            "weight_tonnes",
            "cost_musd",
            "year",
            "operator",
        }
        assert expected_cols.issubset(set(synthetic_df.columns))

    def test_shape_has_requested_rows(self):
        df = CostModelCalibration.synthetic_removal_dataframe(n_records=50)
        assert len(df) == 50

    def test_asset_types_are_valid(self, synthetic_df):
        valid = {"jacket", "well_p_and_a", "subsea_tree", "pipeline_km", "fpso"}
        assert set(synthetic_df["asset_type"].unique()).issubset(valid)

    def test_costs_are_positive(self, synthetic_df):
        assert (synthetic_df["cost_musd"] > 0).all()

    def test_seeded_rng_is_reproducible(self):
        df1 = CostModelCalibration.synthetic_removal_dataframe(n_records=30)
        df2 = CostModelCalibration.synthetic_removal_dataframe(n_records=30)
        pd.testing.assert_frame_equal(df1, df2)


# ---------------------------------------------------------------------------
# TestFit
# ---------------------------------------------------------------------------


class TestFit:
    def test_fit_is_chainable(self, calibrator, synthetic_df):
        result = calibrator.fit(synthetic_df)
        assert result is calibrator

    def test_fitted_flag_set_after_fit(self, calibrator, synthetic_df):
        calibrator.fit(synthetic_df)
        assert calibrator._fitted is True

    def test_fit_empty_df_does_not_raise(self, calibrator):
        empty = pd.DataFrame(
            columns=["asset_type", "water_depth_m", "weight_tonnes", "cost_musd", "year"]
        )
        calibrator.fit(empty)
        assert calibrator._fitted is True

    def test_fit_missing_columns_raises_value_error(self, calibrator):
        bad_df = pd.DataFrame({"asset_type": ["jacket"], "cost_musd": [5.0]})
        with pytest.raises(ValueError, match="missing required columns"):
            calibrator.fit(bad_df)

    def test_calibration_result_raises_before_fit(self, calibrator):
        with pytest.raises(RuntimeError, match="fit\\(\\) must be called"):
            calibrator.calibration_result()

    def test_fitted_factors_raises_before_fit(self, calibrator):
        with pytest.raises(RuntimeError, match="fit\\(\\) must be called"):
            calibrator.fitted_factors()


# ---------------------------------------------------------------------------
# TestCalibrationResult
# ---------------------------------------------------------------------------


class TestCalibrationResult:
    def test_result_is_calibration_result_type(self, fitted_calibrator):
        result = fitted_calibrator.calibration_result()
        assert isinstance(result, CalibrationResult)

    def test_fits_are_calibration_fit_instances(self, fitted_calibrator):
        result = fitted_calibrator.calibration_result()
        assert all(isinstance(f, CalibrationFit) for f in result.fits)

    def test_rmse_non_negative(self, fitted_calibrator):
        result = fitted_calibrator.calibration_result()
        for f in result.fits:
            assert f.rmse_musd >= 0.0, f"Negative RMSE for {f.asset_type}"

    def test_r_squared_in_valid_range(self, fitted_calibrator):
        result = fitted_calibrator.calibration_result()
        for f in result.fits:
            assert -1.0 <= f.r_squared <= 1.0, (
                f"r_squared out of range for {f.asset_type}: {f.r_squared}"
            )

    def test_to_dataframe_returns_dataframe(self, fitted_calibrator):
        result = fitted_calibrator.calibration_result()
        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)

    def test_to_dataframe_has_expected_columns(self, fitted_calibrator):
        result = fitted_calibrator.calibration_result()
        df = result.to_dataframe()
        expected_cols = {
            "asset_type",
            "n_records",
            "base_musd_fitted",
            "base_musd_baseline",
            "rmse_musd",
            "r_squared",
            "confidence",
            "data_driven",
        }
        assert expected_cols.issubset(set(df.columns))


# ---------------------------------------------------------------------------
# TestFittedFactors
# ---------------------------------------------------------------------------


class TestFittedFactors:
    def test_fitted_factors_returns_dict(self, fitted_calibrator):
        factors = fitted_calibrator.fitted_factors()
        assert isinstance(factors, dict)

    def test_fitted_factors_contains_all_baseline_types(self, fitted_calibrator):
        factors = fitted_calibrator.fitted_factors()
        for atype in _COST_FACTORS:
            assert atype in factors, f"Missing asset_type: {atype}"

    def test_fitted_base_clamped_above_half_of_baseline(self, fitted_calibrator):
        factors = fitted_calibrator.fitted_factors()
        for atype, fdict in factors.items():
            if atype in _COST_FACTORS:
                baseline_base = _COST_FACTORS[atype]["base_musd"]
                fitted_base = fdict["base_musd"]
                assert fitted_base >= baseline_base * 0.5 - 1e-9, (
                    f"{atype}: fitted_base {fitted_base} below 0.5x baseline {baseline_base}"
                )

    def test_fitted_base_clamped_below_double_of_baseline(self, fitted_calibrator):
        factors = fitted_calibrator.fitted_factors()
        for atype, fdict in factors.items():
            if atype in _COST_FACTORS:
                baseline_base = _COST_FACTORS[atype]["base_musd"]
                fitted_base = fdict["base_musd"]
                assert fitted_base <= baseline_base * 2.0 + 1e-9, (
                    f"{atype}: fitted_base {fitted_base} above 2.0x baseline {baseline_base}"
                )


# ---------------------------------------------------------------------------
# TestFromCalibration
# ---------------------------------------------------------------------------


class TestFromCalibration:
    def test_from_calibration_creates_estimator(self, fitted_calibrator):
        estimator = DecommissioningCostEstimator.from_calibration(fitted_calibrator)
        assert isinstance(estimator, DecommissioningCostEstimator)

    def test_wrong_type_raises_type_error(self):
        with pytest.raises(TypeError):
            DecommissioningCostEstimator.from_calibration("not_a_calibration")  # type: ignore[arg-type]

    def test_jacket_cost_within_2x_of_baseline(self, fitted_calibrator):
        estimator = DecommissioningCostEstimator.from_calibration(fitted_calibrator)
        baseline_estimator = DecommissioningCostEstimator()
        cal_est = estimator.estimate("jacket", 100, 500, "gom")
        base_est = baseline_estimator.estimate("jacket", 100, 500, "gom")
        assert cal_est.estimated_cost_musd <= base_est.estimated_cost_musd * 2.0 + 1e-6
        assert cal_est.estimated_cost_musd >= base_est.estimated_cost_musd * 0.5 - 1e-6

    def test_well_p_and_a_cost_within_2x_of_baseline(self, fitted_calibrator):
        estimator = DecommissioningCostEstimator.from_calibration(fitted_calibrator)
        baseline_estimator = DecommissioningCostEstimator()
        cal_est = estimator.estimate("well_p_and_a", 2000, 0, "gom")
        base_est = baseline_estimator.estimate("well_p_and_a", 2000, 0, "gom")
        assert cal_est.estimated_cost_musd <= base_est.estimated_cost_musd * 2.0 + 1e-6
        assert cal_est.estimated_cost_musd >= base_est.estimated_cost_musd * 0.5 - 1e-6

    def test_calibrated_estimator_returns_positive_cost(self, fitted_calibrator):
        estimator = DecommissioningCostEstimator.from_calibration(fitted_calibrator)
        result = estimator.estimate("subsea_tree", 500, 25, "gom")
        assert result.estimated_cost_musd > 0
