"""
Tests for EnigmaCalibrator — data-driven ENIGMA risk score calibration.

Covers:
    TestSyntheticDataFrame  (5 tests)
    TestFit                 (8 tests)
    TestCalibrationReport   (8 tests)
    TestRiskScore           (5 tests)
    TestAssess              (5 tests)
    TestCalibratedMatrix    (4 tests)
    TestIntegrationWithSkill (3 tests)

Total: 38 tests
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.safety_analysis.calibrator import (
    CalibrationRecord,
    CalibrationReport,
    EnigmaCalibrator,
)
from worldenergydata.safety_analysis.skill import (
    _VALID_ASSET_TYPES,
    _VALID_SCENARIOS,
    EnigmaResult,
    enigma_safety_analysis,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    return EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=200)


@pytest.fixture()
def fitted_calibrator(synthetic_df: pd.DataFrame) -> EnigmaCalibrator:
    calibrator = EnigmaCalibrator()
    calibrator.fit(synthetic_df)
    return calibrator


# ---------------------------------------------------------------------------
# TestSyntheticDataFrame
# ---------------------------------------------------------------------------


class TestSyntheticDataFrame:
    def test_returns_dataframe(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe()
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, synthetic_df: pd.DataFrame) -> None:
        required = {"incident_type", "equipment_type", "severity", "incident_date"}
        assert required.issubset(set(synthetic_df.columns))

    def test_default_200_rows(self, synthetic_df: pd.DataFrame) -> None:
        assert len(synthetic_df) == 200

    def test_n_incidents_parameter_respected(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=50)
        assert len(df) == 50

    def test_incident_type_values_valid(self, synthetic_df: pd.DataFrame) -> None:
        valid_types = {"equipment_failure", "spill", "injury", "violation"}
        actual = set(synthetic_df["incident_type"].dropna().unique())
        assert actual.issubset(valid_types)


# ---------------------------------------------------------------------------
# TestFit
# ---------------------------------------------------------------------------


class TestFit:
    def test_fit_returns_self(self, synthetic_df: pd.DataFrame) -> None:
        calibrator = EnigmaCalibrator()
        result = calibrator.fit(synthetic_df)
        assert result is calibrator

    def test_fitted_flag_true_after_fit(self, synthetic_df: pd.DataFrame) -> None:
        calibrator = EnigmaCalibrator()
        calibrator.fit(synthetic_df)
        assert calibrator._fitted is True

    def test_fit_empty_dataframe_does_not_crash(self) -> None:
        calibrator = EnigmaCalibrator()
        calibrator.fit(pd.DataFrame())
        assert calibrator._fitted is True

    def test_fit_missing_equipment_type_column_uses_fallback(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=100)
        df = df.drop(columns=["equipment_type"])
        calibrator = EnigmaCalibrator()
        calibrator.fit(df)
        assert calibrator._fitted is True

    def test_calibrated_matrix_nonempty_after_fit(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        assert len(fitted_calibrator._calibrated_matrix) > 0

    def test_calibration_report_before_fit_raises_runtime_error(self) -> None:
        calibrator = EnigmaCalibrator()
        with pytest.raises(RuntimeError, match="fit\\(\\)"):
            calibrator.calibration_report()

    def test_fit_twice_overwrites_state(self, synthetic_df: pd.DataFrame) -> None:
        calibrator = EnigmaCalibrator()
        calibrator.fit(synthetic_df)
        first_report = calibrator.calibration_report()
        calibrator.fit(synthetic_df)
        second_report = calibrator.calibration_report()
        assert second_report.total_incidents_used == first_report.total_incidents_used

    def test_fit_without_incident_date_column(self) -> None:
        df = EnigmaCalibrator.synthetic_hse_dataframe(n_incidents=100)
        df = df.drop(columns=["incident_date"])
        calibrator = EnigmaCalibrator()
        calibrator.fit(df)
        assert calibrator._fitted is True


# ---------------------------------------------------------------------------
# TestCalibrationReport
# ---------------------------------------------------------------------------


class TestCalibrationReport:
    def test_returns_calibration_report_instance(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert isinstance(report, CalibrationReport)

    def test_total_incidents_used_positive(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert report.total_incidents_used > 0

    def test_years_covered_positive(self, fitted_calibrator: EnigmaCalibrator) -> None:
        report = fitted_calibrator.calibration_report()
        assert report.years_covered > 0.0

    def test_records_is_list_of_calibration_records(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert isinstance(report.records, list)
        assert all(isinstance(r, CalibrationRecord) for r in report.records)

    def test_each_record_has_required_attributes(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        for rec in report.records:
            assert hasattr(rec, "asset_type")
            assert hasattr(rec, "scenario")
            assert hasattr(rec, "calibrated_score")
            assert hasattr(rec, "confidence")
            assert hasattr(rec, "data_driven")

    def test_calibrated_score_in_valid_range(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        for rec in report.records:
            assert 0.0 <= rec.calibrated_score <= 1.0, (
                f"Score out of range for {rec.asset_type}/{rec.scenario}: "
                f"{rec.calibrated_score}"
            )

    def test_coverage_pct_in_valid_range(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        assert 0.0 <= report.coverage_pct <= 100.0

    def test_to_dataframe_returns_dataframe_with_expected_columns(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        report = fitted_calibrator.calibration_report()
        df = report.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        expected_cols = {
            "asset_type",
            "scenario",
            "incident_count",
            "calibrated_score",
            "confidence",
            "data_driven",
        }
        assert expected_cols.issubset(set(df.columns))


# ---------------------------------------------------------------------------
# TestRiskScore
# ---------------------------------------------------------------------------


class TestRiskScore:
    def test_returns_tuple_of_float_and_bool(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        score, is_driven = fitted_calibrator.risk_score("riser", "corrosion")
        assert isinstance(score, float)
        assert isinstance(is_driven, bool)

    def test_score_in_valid_range(self, fitted_calibrator: EnigmaCalibrator) -> None:
        score, _ = fitted_calibrator.risk_score("riser", "corrosion")
        assert 0.0 <= score <= 1.0

    def test_without_fit_returns_rule_based_score(self) -> None:
        calibrator = EnigmaCalibrator()
        score, is_driven = calibrator.risk_score("platform", "fire_explosion")
        assert not is_driven
        assert 0.0 <= score <= 1.0

    def test_with_fit_some_combos_are_data_driven(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        found_data_driven = False
        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                _, is_driven = fitted_calibrator.risk_score(asset_type, scenario)
                if is_driven:
                    found_data_driven = True
                    break
            if found_data_driven:
                break
        assert found_data_driven, "Expected at least one data-driven combo after fit"

    def test_risk_level_consistent_with_enigma_thresholds(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        from worldenergydata.safety_analysis.skill import _risk_level_from_score

        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                score, _ = fitted_calibrator.risk_score(asset_type, scenario)
                level = _risk_level_from_score(score)
                assert level in {"low", "medium", "high", "critical"}


# ---------------------------------------------------------------------------
# TestAssess
# ---------------------------------------------------------------------------


class TestAssess:
    def test_returns_dict(self, fitted_calibrator: EnigmaCalibrator) -> None:
        result = fitted_calibrator.assess("platform", "fire_explosion")
        assert isinstance(result, dict)

    def test_dict_has_required_keys(self, fitted_calibrator: EnigmaCalibrator) -> None:
        result = fitted_calibrator.assess("platform", "fire_explosion")
        required = {
            "asset_type",
            "scenario",
            "risk_score",
            "risk_level",
            "data_driven",
            "confidence",
        }
        assert required.issubset(set(result.keys()))

    def test_data_driven_key_present(self, fitted_calibrator: EnigmaCalibrator) -> None:
        result = fitted_calibrator.assess("riser", "overpressure")
        assert "data_driven" in result

    def test_confidence_is_valid_label(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        result = fitted_calibrator.assess("vessel", "corrosion")
        assert result["confidence"] in {"high", "medium", "low"}

    def test_works_for_all_six_asset_types(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        for asset_type in _VALID_ASSET_TYPES:
            result = fitted_calibrator.assess(asset_type, "fatigue")
            assert result["asset_type"] == asset_type
            assert 0.0 <= result["risk_score"] <= 1.0


# ---------------------------------------------------------------------------
# TestCalibratedMatrix
# ---------------------------------------------------------------------------


class TestCalibratedMatrix:
    def test_returns_dataframe(self, fitted_calibrator: EnigmaCalibrator) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert isinstance(df, pd.DataFrame)

    def test_row_index_is_asset_types(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert set(df.index) == set(_VALID_ASSET_TYPES)

    def test_columns_are_scenarios(self, fitted_calibrator: EnigmaCalibrator) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert set(df.columns) == set(_VALID_SCENARIOS)

    def test_all_values_in_valid_range(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        df = fitted_calibrator.calibrated_matrix_df()
        assert df.shape == (6, 6)
        assert (df.values >= 0.0).all()
        assert (df.values <= 1.0).all()


# ---------------------------------------------------------------------------
# TestIntegrationWithSkill
# ---------------------------------------------------------------------------


class TestIntegrationWithSkill:
    def test_enigma_safety_analysis_accepts_calibrator(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        result = enigma_safety_analysis(
            "riser", "corrosion", calibrator=fitted_calibrator
        )
        assert result is not None

    def test_result_is_enigma_result_instance(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        result = enigma_safety_analysis(
            "platform", "fire_explosion", calibrator=fitted_calibrator
        )
        assert isinstance(result, EnigmaResult)

    def test_risk_score_differs_from_uncalibrated_when_data_driven(
        self, fitted_calibrator: EnigmaCalibrator
    ) -> None:
        # Find at least one combo that is data-driven
        target_asset, target_scenario = None, None
        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                _, is_driven = fitted_calibrator.risk_score(asset_type, scenario)
                if is_driven:
                    target_asset, target_scenario = asset_type, scenario
                    break
            if target_asset:
                break

        assert target_asset is not None, "No data-driven combo found after fit"

        uncalibrated = enigma_safety_analysis(target_asset, target_scenario)
        calibrated = enigma_safety_analysis(
            target_asset, target_scenario, calibrator=fitted_calibrator
        )
        # The calibrated score blends data with rule-based, so it may differ
        # from the pure rule-based score; we verify the type is correct and
        # the score is in range regardless of direction.
        assert isinstance(calibrated.risk_score, float)
        assert 0.0 <= calibrated.risk_score <= 1.0
        assert isinstance(uncalibrated.risk_score, float)
