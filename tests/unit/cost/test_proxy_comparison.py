"""
ABOUTME: Tests for CostPredictor proxy-rate comparison — AC4 of WRK-171.
ABOUTME: Verifies that calibrated rates can be compared to WRK-019 proxy rates
ABOUTME: with quantified bias and RMSE per cell.
"""

from __future__ import annotations

import pytest

from worldenergydata.cost.data_collection.public_dataset import load_public_dataset
from worldenergydata.cost.calibration.cost_predictor import CostPredictor
from worldenergydata.cost.calibration.proxy_comparison import (
    ProxyComparisonResult,
    ProxyRateComparison,
    compare_calibrated_to_proxy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def public_dataset():
    return load_public_dataset()


@pytest.fixture(scope="module")
def fitted_predictor(public_dataset):
    predictor = CostPredictor()
    predictor.fit(public_dataset)
    return predictor


# ---------------------------------------------------------------------------
# TestProxyComparisonResult
# ---------------------------------------------------------------------------


class TestProxyComparisonResult:
    """ProxyComparisonResult dataclass holds per-cell comparison data."""

    def test_result_instantiates(self):
        """ProxyComparisonResult can be created with valid fields."""
        result = ProxyComparisonResult(
            region="gom",
            water_depth_band="deep",
            activity_type="drilling",
            proxy_rate_usd_day=440_000.0,
            calibrated_rate_usd_day=420_000.0,
            bias_pct=-4.55,
            n_data_points=3,
            rmse_usd_mm=25.0,
            confidence="medium",
        )
        assert result.region == "gom"
        assert result.proxy_rate_usd_day == 440_000.0

    def test_bias_pct_sign_convention(self):
        """Positive bias_pct means calibrated > proxy (proxy underestimated)."""
        result = ProxyComparisonResult(
            region="gom",
            water_depth_band="deep",
            activity_type="drilling",
            proxy_rate_usd_day=400_000.0,
            calibrated_rate_usd_day=440_000.0,
            bias_pct=10.0,
            n_data_points=1,
            rmse_usd_mm=0.0,
            confidence="low",
        )
        assert result.bias_pct > 0.0

    def test_negative_bias_pct(self):
        """Negative bias_pct means calibrated < proxy (proxy overestimated)."""
        result = ProxyComparisonResult(
            region="gom",
            water_depth_band="deep",
            activity_type="drilling",
            proxy_rate_usd_day=500_000.0,
            calibrated_rate_usd_day=400_000.0,
            bias_pct=-20.0,
            n_data_points=2,
            rmse_usd_mm=10.0,
            confidence="low",
        )
        assert result.bias_pct < 0.0


# ---------------------------------------------------------------------------
# TestProxyRateComparison
# ---------------------------------------------------------------------------


class TestProxyRateComparison:
    """ProxyRateComparison.compare() returns calibrated vs proxy analysis."""

    def test_compare_returns_list(self, fitted_predictor, public_dataset):
        """compare() returns a list of ProxyComparisonResult instances."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        assert isinstance(results, list)

    def test_compare_returns_non_empty_list(self, fitted_predictor, public_dataset):
        """compare() returns at least one comparison entry."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        assert len(results) > 0

    def test_all_results_are_proxy_comparison_result(self, fitted_predictor, public_dataset):
        """Every entry returned is a ProxyComparisonResult instance."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        for r in results:
            assert isinstance(r, ProxyComparisonResult)

    def test_results_have_positive_proxy_rates(self, fitted_predictor, public_dataset):
        """All proxy_rate_usd_day values are positive."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        for r in results:
            assert r.proxy_rate_usd_day > 0.0

    def test_results_have_positive_calibrated_rates(self, fitted_predictor, public_dataset):
        """All calibrated_rate_usd_day values are positive."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        for r in results:
            assert r.calibrated_rate_usd_day > 0.0

    def test_results_cover_multiple_regions(self, fitted_predictor, public_dataset):
        """Comparison covers at least 3 distinct regions."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        regions = {r.region for r in results}
        assert len(regions) >= 3

    def test_confidence_levels_present(self, fitted_predictor, public_dataset):
        """All results have a valid confidence level string."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        valid_levels = {"high", "medium", "low"}
        for r in results:
            assert r.confidence in valid_levels

    def test_bias_pct_calculated(self, fitted_predictor, public_dataset):
        """bias_pct is calculated as (calibrated - proxy) / proxy * 100."""
        comparator = ProxyRateComparison(predictor=fitted_predictor)
        results = comparator.compare(public_dataset)
        for r in results:
            expected = (
                (r.calibrated_rate_usd_day - r.proxy_rate_usd_day)
                / r.proxy_rate_usd_day
                * 100.0
            )
            assert abs(r.bias_pct - expected) < 0.01, (
                f"bias_pct mismatch: {r.bias_pct} vs {expected}"
            )


# ---------------------------------------------------------------------------
# TestCompareFunction
# ---------------------------------------------------------------------------


class TestCompareFunction:
    """compare_calibrated_to_proxy() convenience function."""

    def test_function_returns_list(self, public_dataset):
        """compare_calibrated_to_proxy() trains and returns comparison."""
        results = compare_calibrated_to_proxy(public_dataset)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_function_results_have_required_fields(self, public_dataset):
        """All results from the convenience function have required fields."""
        results = compare_calibrated_to_proxy(public_dataset)
        required_fields = {
            "region", "water_depth_band", "activity_type",
            "proxy_rate_usd_day", "calibrated_rate_usd_day",
            "bias_pct", "n_data_points", "rmse_usd_mm", "confidence",
        }
        for r in results:
            result_fields = {
                f for f in required_fields
                if hasattr(r, f)
            }
            assert result_fields == required_fields

    def test_function_unfitted_predictor_trains_on_data(self, public_dataset):
        """compare_calibrated_to_proxy() accepts an unfitted predictor."""
        unfitted = CostPredictor()
        results = compare_calibrated_to_proxy(public_dataset, predictor=unfitted)
        assert isinstance(results, list)
        assert len(results) > 0
