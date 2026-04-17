"""
Tests for RiskCalibrator, RiskCalibrationReport, CalibrationRecord.
25+ tests across 5 test classes.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.well_planning.risk_calibrator import (
    HSE_TO_RISK_MAP,
    MIN_INCIDENTS_FOR_CALIBRATION,
    CalibrationRecord,
    RiskCalibrationReport,
    RiskCalibrator,
)
from worldenergydata.well_planning.risk_registry import WELL_PLANNING_RISKS

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    return RiskCalibrator.synthetic_hse_dataframe()


@pytest.fixture
def fitted_calibrator(synthetic_df: pd.DataFrame) -> RiskCalibrator:
    return RiskCalibrator().calibrate(synthetic_df)


# ---------------------------------------------------------------------------
# TestSyntheticDataFrame — 5 tests
# ---------------------------------------------------------------------------


class TestSyntheticDataFrame:
    def test_shape_default_rows(self, synthetic_df: pd.DataFrame) -> None:
        """Default n_incidents=150 produces exactly 150 rows."""
        assert len(synthetic_df) == 150

    def test_required_columns_present(self, synthetic_df: pd.DataFrame) -> None:
        """DataFrame must contain incident_type, sub_type, severity, date."""
        for col in ("incident_type", "sub_type", "severity", "date"):
            assert col in synthetic_df.columns

    def test_incident_types_valid(self, synthetic_df: pd.DataFrame) -> None:
        """All incident_type values must be keys in HSE_TO_RISK_MAP."""
        valid_types = {k[0] for k in HSE_TO_RISK_MAP.keys()}
        assert set(synthetic_df["incident_type"].unique()).issubset(valid_types)

    def test_sub_types_valid(self, synthetic_df: pd.DataFrame) -> None:
        """All sub_type values must be values (second element) in HSE_TO_RISK_MAP keys."""
        valid_sub = {k[1] for k in HSE_TO_RISK_MAP.keys()}
        assert set(synthetic_df["sub_type"].unique()).issubset(valid_sub)

    def test_custom_n_incidents(self) -> None:
        """n_incidents parameter controls row count."""
        df = RiskCalibrator.synthetic_hse_dataframe(n_incidents=75)
        assert len(df) == 75


# ---------------------------------------------------------------------------
# TestCalibrate — 6 tests
# ---------------------------------------------------------------------------


class TestCalibrate:
    def test_chainable_returns_self(self, synthetic_df: pd.DataFrame) -> None:
        """calibrate() returns the RiskCalibrator instance (chainable)."""
        cal = RiskCalibrator()
        result = cal.calibrate(synthetic_df)
        assert result is cal

    def test_fitted_flag_set_after_calibrate(self, synthetic_df: pd.DataFrame) -> None:
        """Internal _fitted flag is True after calibrate()."""
        cal = RiskCalibrator()
        assert not cal._fitted
        cal.calibrate(synthetic_df)
        assert cal._fitted

    def test_empty_dataframe_sets_fitted(self) -> None:
        """calibrate() with empty DataFrame still marks calibrator as fitted."""
        empty = pd.DataFrame(columns=["incident_type", "sub_type", "severity"])
        cal = RiskCalibrator().calibrate(empty)
        assert cal._fitted

    def test_missing_column_raises_value_error(self) -> None:
        """calibrate() raises ValueError when required columns are absent."""
        bad_df = pd.DataFrame({"incident_type": ["kick"]})
        with pytest.raises(ValueError, match="missing required columns"):
            RiskCalibrator().calibrate(bad_df)

    def test_missing_sub_type_raises_value_error(self) -> None:
        """calibrate() raises ValueError when sub_type column is absent."""
        bad_df = pd.DataFrame({"sub_type": ["pressure_control"]})
        with pytest.raises(ValueError, match="missing required columns"):
            RiskCalibrator().calibrate(bad_df)

    def test_runtime_error_before_calibrate(self) -> None:
        """calibration_report() raises RuntimeError before calibrate() is called."""
        cal = RiskCalibrator()
        with pytest.raises(RuntimeError, match="calibrate\\(\\) must be called"):
            cal.calibration_report()


# ---------------------------------------------------------------------------
# TestCalibrationReport — 6 tests
# ---------------------------------------------------------------------------


class TestCalibrationReport:
    def test_report_type(self, fitted_calibrator: RiskCalibrator) -> None:
        """calibration_report() returns a RiskCalibrationReport instance."""
        report = fitted_calibrator.calibration_report()
        assert isinstance(report, RiskCalibrationReport)

    def test_records_list_of_calibration_records(
        self, fitted_calibrator: RiskCalibrator
    ) -> None:
        """All entries in report.records are CalibrationRecord instances."""
        report = fitted_calibrator.calibration_report()
        for rec in report.records:
            assert isinstance(rec, CalibrationRecord)

    def test_events_per_year_non_negative(
        self, fitted_calibrator: RiskCalibrator
    ) -> None:
        """All events_per_year values are >= 0."""
        report = fitted_calibrator.calibration_report()
        for rec in report.records:
            assert rec.events_per_year >= 0.0

    def test_coverage_pct_between_0_and_100(
        self, fitted_calibrator: RiskCalibrator
    ) -> None:
        """coverage_pct is within [0, 100]."""
        report = fitted_calibrator.calibration_report()
        assert 0.0 <= report.coverage_pct <= 100.0

    def test_total_incidents_used_positive(
        self, fitted_calibrator: RiskCalibrator
    ) -> None:
        """total_incidents_used is > 0 when synthetic data is used."""
        report = fitted_calibrator.calibration_report()
        assert report.total_incidents_used > 0

    def test_to_dataframe_columns(self, fitted_calibrator: RiskCalibrator) -> None:
        """to_dataframe() returns a DataFrame with the expected columns."""
        df = fitted_calibrator.calibration_report().to_dataframe()
        expected_cols = {
            "risk_id",
            "category",
            "events_per_year",
            "calibrated_probability",
            "baseline_probability",
            "confidence",
            "data_driven",
        }
        assert expected_cols.issubset(set(df.columns))


# ---------------------------------------------------------------------------
# TestRiskProbability — 5 tests
# ---------------------------------------------------------------------------


class TestRiskProbability:
    def test_return_type_is_float_bool(self, fitted_calibrator: RiskCalibrator) -> None:
        """risk_probability() returns (float, bool)."""
        prob, is_data_driven = fitted_calibrator.risk_probability("OP-002")
        assert isinstance(prob, float)
        assert isinstance(is_data_driven, bool)

    def test_probability_in_range(self, fitted_calibrator: RiskCalibrator) -> None:
        """All calibrated probabilities are in [0.05, 0.95]."""
        for risk in WELL_PLANNING_RISKS:
            prob, _ = fitted_calibrator.risk_probability(risk.risk_id)
            assert (
                0.05 <= prob <= 0.95
            ), f"{risk.risk_id} probability {prob} out of range"

    def test_unfitted_fallback_returns_baseline(self) -> None:
        """Unfitted calibrator returns baseline probability and is_data_driven=False."""
        cal = RiskCalibrator()
        # OP-001 has baseline 0.6
        prob, is_data_driven = cal.risk_probability("OP-001")
        assert not is_data_driven
        assert prob == pytest.approx(0.6)

    def test_data_driven_detection(self, synthetic_df: pd.DataFrame) -> None:
        """Risks with enough incidents are flagged as data_driven=True."""
        cal = RiskCalibrator().calibrate(synthetic_df)
        any_data_driven = False
        for risk in WELL_PLANNING_RISKS:
            _, is_dd = cal.risk_probability(risk.risk_id)
            if is_dd:
                any_data_driven = True
                break
        assert (
            any_data_driven
        ), "Expected at least one data-driven risk after calibration"

    def test_unknown_risk_id_fallback(self, fitted_calibrator: RiskCalibrator) -> None:
        """Unknown risk_id returns (0.5, False) from baseline fallback."""
        prob, is_data_driven = fitted_calibrator.risk_probability("XX-999")
        assert not is_data_driven
        assert prob == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# TestCalibrateRegistry — 5 tests
# ---------------------------------------------------------------------------


class TestCalibrateRegistry:
    def test_returns_list(self, fitted_calibrator: RiskCalibrator) -> None:
        """calibrate_registry() returns a list."""
        result = fitted_calibrator.calibrate_registry()
        assert isinstance(result, list)

    def test_all_risks_present(self, fitted_calibrator: RiskCalibrator) -> None:
        """calibrate_registry() returns exactly as many risks as the registry."""
        result = fitted_calibrator.calibrate_registry()
        assert len(result) == len(WELL_PLANNING_RISKS)

    def test_all_risk_ids_present(self, fitted_calibrator: RiskCalibrator) -> None:
        """All original risk_ids appear in the calibrated list."""
        result = fitted_calibrator.calibrate_registry()
        original_ids = {r.risk_id for r in WELL_PLANNING_RISKS}
        calibrated_ids = {r.risk_id for r in result}
        assert original_ids == calibrated_ids

    def test_updated_probabilities_in_range(
        self, fitted_calibrator: RiskCalibrator
    ) -> None:
        """All updated probability values are within [0.05, 0.95]."""
        result = fitted_calibrator.calibrate_registry()
        for risk in result:
            assert (
                0.05 <= risk.probability <= 0.95
            ), f"{risk.risk_id} probability {risk.probability} out of range"

    def test_risk_score_consistent_with_probability(
        self, fitted_calibrator: RiskCalibrator
    ) -> None:
        """risk_score equals severity.value * probability (within floating tolerance)."""
        result = fitted_calibrator.calibrate_registry()
        for risk in result:
            expected_score = risk.severity.value * risk.probability
            assert risk.risk_score == pytest.approx(expected_score, abs=1e-3), (
                f"{risk.risk_id}: score {risk.risk_score} != "
                f"severity {risk.severity.value} * prob {risk.probability}"
            )
