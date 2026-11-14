"""Regressions for quality input validation and degenerate statistics."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.well_data_verification.quality import (
    DataQualityFramework,
    OutlierDetector,
    QualityConfig,
)


@pytest.mark.parametrize("data", [pd.DataFrame(), pd.DataFrame(columns=["oil_volume"])])
def test_empty_framework_input_is_invalid(data):
    result = DataQualityFramework().run_quality_checks(data)

    assert not result.is_valid
    assert result.errors
    assert result.metadata["quality_score"] == 0.0


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_framework_input_fails_without_optional_checks(value):
    framework = DataQualityFramework(
        QualityConfig(enable_completeness_check=False, enable_outlier_detection=False)
    )
    result = framework.run_quality_checks(pd.DataFrame({"measurement": [1.0, value]}))

    assert not result.is_valid
    assert any(
        error.field == "measurement" and error.message for error in result.errors
    )
    assert result.metadata["quality_score"] == 0.0


def test_nullable_measurements_report_missing_values():
    data = pd.DataFrame({"oil_volume": pd.Series([1.0, pd.NA], dtype="Float64")})

    result = DataQualityFramework().run_quality_checks(data)

    assert not result.is_valid
    assert any(error.field == "oil_volume" for error in result.errors)
    assert result.metadata["quality_score"] == 0.0


@pytest.mark.parametrize("column", ["oil_volume", "gas_volume"])
def test_known_measurements_require_numeric_values(column):
    result = DataQualityFramework().run_quality_checks(
        pd.DataFrame({column: ["invalid", "measurement"]})
    )

    assert not result.is_valid
    assert any(error.field == column for error in result.errors)


def test_text_labels_are_not_coerced_into_measurements():
    data = pd.DataFrame(
        {"oil_volume": [10.0, 12.0, 15.0], "label": ["inf", "NaN", "unknown"]}
    )

    result = DataQualityFramework().run_quality_checks(data)

    assert result.is_valid
    assert not result.warnings
    assert result.metadata["quality_score"] == 1.0


def test_constant_framework_measurements_have_no_outliers():
    result = DataQualityFramework().run_quality_checks(
        pd.DataFrame({"oil_volume": [10.0, 10.0, 10.0]})
    )

    assert result.is_valid
    assert not result.warnings
    assert result.metadata["quality_score"] == 1.0


@pytest.mark.parametrize("value", [0.0, 10.0])
def test_constant_series_has_no_zscore_outliers(value):
    result = OutlierDetector().detect_outliers_zscore(
        pd.DataFrame({"measurement": [value, value, value]}), "measurement"
    )

    assert result.is_valid
    assert not result.warnings


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_zscore_rejects_nonfinite_measurements(value):
    result = OutlierDetector().detect_outliers_zscore(
        pd.DataFrame({"measurement": [1.0, value, 3.0]}), "measurement"
    )

    assert not result.is_valid
    assert any(
        error.field == "measurement" and error.message for error in result.errors
    )


def test_zscore_rejects_label_columns():
    result = OutlierDetector().detect_outliers_zscore(
        pd.DataFrame({"label": ["first", "second", "third"]}), "label"
    )

    assert not result.is_valid
    assert result.errors


@pytest.mark.parametrize("threshold, count", [(3.0, 1), (5.0, 0)])
def test_zscore_preserves_threshold_and_detects_an_extreme_value(threshold, count):
    # For twenty equal values and one extreme value, its z-score is sqrt(20).
    result = OutlierDetector().detect_outliers_zscore(
        pd.DataFrame({"measurement": [10.0] * 20 + [1000.0]}),
        "measurement",
        threshold=threshold,
    )

    assert result.is_valid
    assert len(result.warnings) == count
    if count:
        assert result.warnings[0].row_index == 20


@pytest.mark.parametrize("threshold", [0.0, -1.0, np.nan, np.inf])
def test_zscore_rejects_invalid_thresholds(threshold):
    result = OutlierDetector().detect_outliers_zscore(
        pd.DataFrame({"measurement": [1.0, 2.0, 3.0]}),
        "measurement",
        threshold=threshold,
    )

    assert not result.is_valid
    assert result.errors


@pytest.mark.parametrize("method", ["iqr", "multivariate"])
@pytest.mark.parametrize("value", [np.nan, np.inf])
def test_public_detectors_reject_nonfinite_measurements(method, value):
    detector = OutlierDetector()
    data = pd.DataFrame(
        {"first": [1.0, value, 3.0, 4.0, 5.0], "second": [2.0, 1.0, 4.0, 2.0, 6.0]}
    )
    result = (
        detector.detect_outliers_iqr(data, "first")
        if method == "iqr"
        else detector.detect_multivariate_outliers(data, ["first", "second"])
    )

    assert not result.is_valid
    assert any(error.field == "first" and error.message for error in result.errors)


@pytest.mark.parametrize("method", ["iqr", "multivariate"])
def test_public_detectors_reject_empty_measurements(method):
    detector = OutlierDetector()
    data = pd.DataFrame({"first": pd.Series(dtype=float)})
    result = (
        detector.detect_outliers_iqr(data, "first")
        if method == "iqr"
        else detector.detect_multivariate_outliers(data, ["first"])
    )

    assert not result.is_valid
    assert result.errors


@pytest.mark.parametrize("method", ["iqr", "multivariate"])
def test_public_detectors_reject_label_columns(method):
    detector = OutlierDetector()
    data = pd.DataFrame({"label": ["first", "second", "third", "fourth"]})
    result = (
        detector.detect_outliers_iqr(data, "label")
        if method == "iqr"
        else detector.detect_multivariate_outliers(data, ["label"])
    )

    assert not result.is_valid
    assert result.errors


def test_multivariate_requires_selected_columns():
    result = OutlierDetector().detect_multivariate_outliers(
        pd.DataFrame({"measurement": [1.0, 2.0, 3.0]}), []
    )

    assert not result.is_valid
    assert result.errors


@pytest.mark.parametrize("multiplier", [0.0, np.inf])
def test_iqr_rejects_invalid_multipliers(multiplier):
    result = OutlierDetector().detect_outliers_iqr(
        pd.DataFrame({"measurement": [1.0, 2.0, 3.0, 4.0]}),
        "measurement",
        multiplier=multiplier,
    )

    assert not result.is_valid
    assert result.errors


def test_iqr_retains_real_outlier_detection():
    # Q1=11 and Q3=13 give bounds 8 and 16 with the existing default multiplier.
    result = OutlierDetector().detect_outliers_iqr(
        pd.DataFrame({"measurement": [10.0, 11.0, 12.0, 13.0, 100.0]}), "measurement"
    )

    assert result.is_valid
    assert len(result.warnings) == 1
    assert result.warnings[0].row_index == 4


def test_iqr_reports_insufficient_sample_count():
    result = OutlierDetector().detect_outliers_iqr(
        pd.DataFrame({"measurement": [1.0, 2.0, 3.0]}), "measurement"
    )

    assert result.has_warnings
    assert any("Insufficient" in warning.message for warning in result.warnings)


def test_multivariate_retains_real_outlier_detection():
    data = pd.DataFrame(
        [[-1.0, -1.0], [-1.0, 1.0], [1.0, -1.0], [1.0, 1.0]] * 20 + [[100.0, 100.0]],
        columns=["first", "second"],
    )

    result = OutlierDetector().detect_multivariate_outliers(data, ["first", "second"])

    assert result.is_valid
    assert any(warning.row_index == 80 for warning in result.warnings)


@pytest.mark.parametrize("method", ["framework", "zscore", "iqr", "multivariate"])
def test_detectors_accept_numeric_objects_without_text_coercion(method):
    data = pd.DataFrame(
        {"oil_volume": pd.Series([10.0, 12.0, 15.0, 16.0, 18.0], dtype=object)}
    )
    detector = OutlierDetector()
    if method == "framework":
        result = DataQualityFramework().run_quality_checks(data)
    elif method == "zscore":
        result = detector.detect_outliers_zscore(data, "oil_volume")
    elif method == "iqr":
        result = detector.detect_outliers_iqr(data, "oil_volume")
    else:
        result = detector.detect_multivariate_outliers(data, ["oil_volume"])

    assert result.is_valid
    assert not result.warnings


@pytest.mark.parametrize("value", [np.inf, None])
def test_framework_rejects_nonfinite_object_measurements(value):
    data = pd.DataFrame({"measurement": pd.Series([1.0, value, 3.0], dtype=object)})

    result = DataQualityFramework().run_quality_checks(data)

    assert not result.is_valid
    assert any(error.field == "measurement" for error in result.errors)
    assert result.metadata["quality_score"] == 0.0
