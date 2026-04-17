# ABOUTME: Unit tests for WRK-019 cross-regional benchmarking module.
# ABOUTME: Covers outlier detection, cross-regional comparison,
# ABOUTME: BenchmarkResult dataclass, and DataFrame outputs.

"""Unit tests for worldenergydata.bsee.analysis.cost.benchmarking."""

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.cost.benchmarking import (
    BenchmarkResult,
    build_comparison_dataframe,
    compare_fields_to_regional_average,
    detect_outliers,
)
from worldenergydata.bsee.analysis.cost.cost_summary import (
    FieldCostSummary,
)
from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    CostEstimate,
    WaterDepthBand,
    WellDepthBand,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_estimate(
    activity: ActivityType,
    region: str,
    cost_mm: float,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
) -> CostEstimate:
    return CostEstimate(
        activity_type=activity,
        region=region,
        water_depth_band=WaterDepthBand.DEEP,
        well_depth_band=WellDepthBand.MEDIUM,
        cost_usd_mm=cost_mm,
        cost_per_day_usd=400_000.0,
        duration_days=60.0,
        confidence=confidence,
        source="proxy_day_rate",
        year=2022,
    )


def _make_summary(
    field_name: str,
    region: str,
    drilling_cost: float,
    completion_cost: float = 0.0,
    n_wells: int = 1,
) -> FieldCostSummary:
    drilling_estimates = [
        _make_estimate(ActivityType.DRILLING, region, drilling_cost / max(n_wells, 1))
        for _ in range(n_wells)
    ]
    completion_estimates = (
        [_make_estimate(ActivityType.COMPLETION, region, completion_cost)]
        if completion_cost > 0
        else []
    )
    return FieldCostSummary(
        field_name=field_name,
        region=region,
        drilling_estimates=drilling_estimates,
        completion_estimates=completion_estimates,
        intervention_estimates=[],
    )


# ---------------------------------------------------------------------------
# TestBenchmarkResult
# ---------------------------------------------------------------------------


class TestBenchmarkResult:
    def test_construction_with_required_fields(self):
        result = BenchmarkResult(
            field_name="Atlantis",
            region="gom",
            total_cost_usd_mm=500.0,
            regional_avg_usd_mm=400.0,
            deviation_pct=25.0,
            is_outlier=False,
            n_wells=4,
            confidence=ConfidenceLevel.MEDIUM,
        )
        assert result.field_name == "Atlantis"
        assert result.deviation_pct == 25.0

    def test_to_dict_has_required_keys(self):
        result = BenchmarkResult(
            field_name="Test",
            region="gom",
            total_cost_usd_mm=200.0,
            regional_avg_usd_mm=180.0,
            deviation_pct=11.1,
            is_outlier=False,
            n_wells=2,
            confidence=ConfidenceLevel.MEDIUM,
        )
        d = result.to_dict()
        required = {
            "field_name",
            "region",
            "total_cost_usd_mm",
            "regional_avg_usd_mm",
            "deviation_pct",
            "is_outlier",
        }
        assert required.issubset(set(d.keys()))


# ---------------------------------------------------------------------------
# TestCompareFieldsToRegionalAverage
# ---------------------------------------------------------------------------


class TestCompareFieldsToRegionalAverage:
    def test_returns_list_of_benchmark_results(self):
        summaries = [
            _make_summary("Atlantis", "gom", 400.0),
            _make_summary("Thunder Horse", "gom", 600.0),
        ]
        results = compare_fields_to_regional_average(summaries)
        assert isinstance(results, list)
        assert all(isinstance(r, BenchmarkResult) for r in results)

    def test_returns_same_count_as_input(self):
        summaries = [
            _make_summary("Field A", "gom", 300.0),
            _make_summary("Field B", "gom", 400.0),
            _make_summary("Field C", "gom", 500.0),
        ]
        results = compare_fields_to_regional_average(summaries)
        assert len(results) == 3

    def test_deviation_pct_calculated(self):
        summaries = [
            _make_summary("Cheap", "gom", 100.0),
            _make_summary("Expensive", "gom", 300.0),
        ]
        results = compare_fields_to_regional_average(summaries)
        # Average is 200; cheap deviation = -50%, expensive = +50%
        cheap_result = next(r for r in results if r.field_name == "Cheap")
        expensive_result = next(r for r in results if r.field_name == "Expensive")
        assert cheap_result.deviation_pct < 0.0
        assert expensive_result.deviation_pct > 0.0

    def test_empty_summaries_returns_empty_list(self):
        results = compare_fields_to_regional_average([])
        assert results == []

    def test_single_field_has_zero_deviation(self):
        summaries = [_make_summary("Only Field", "gom", 200.0)]
        results = compare_fields_to_regional_average(summaries)
        assert len(results) == 1
        assert abs(results[0].deviation_pct) < 0.001

    def test_cross_region_comparison_supported(self):
        summaries = [
            _make_summary("GOM Field", "gom", 400.0),
            _make_summary("NCS Field", "north_sea", 500.0),
        ]
        results = compare_fields_to_regional_average(summaries)
        assert len(results) == 2


# ---------------------------------------------------------------------------
# TestDetectOutliers
# ---------------------------------------------------------------------------


class TestDetectOutliers:
    def test_extreme_cost_flagged_as_outlier(self):
        # Values: 100, 102, 98, 100, 1000 → mean ~280, std ~360, but 1000 is ~2.0 std above
        # Use lower threshold (1.0) to reliably flag a 10x cost outlier
        summaries = [
            _make_summary("Normal A", "gom", 100.0),
            _make_summary("Normal B", "gom", 102.0),
            _make_summary("Normal C", "gom", 98.0),
            _make_summary("Normal D", "gom", 100.0),
            _make_summary("Outlier", "gom", 1000.0),
        ]
        results = detect_outliers(summaries, threshold_std=1.0)
        outlier_result = next(r for r in results if r.field_name == "Outlier")
        assert outlier_result.is_outlier

    def test_normal_fields_not_flagged(self):
        summaries = [
            _make_summary("A", "gom", 100.0),
            _make_summary("B", "gom", 105.0),
            _make_summary("C", "gom", 95.0),
        ]
        results = detect_outliers(summaries, threshold_std=2.0)
        assert all(not r.is_outlier for r in results)

    def test_empty_summaries_returns_empty_list(self):
        results = detect_outliers([], threshold_std=2.0)
        assert results == []


# ---------------------------------------------------------------------------
# TestBuildComparisonDataframe
# ---------------------------------------------------------------------------


class TestBuildComparisonDataframe:
    def test_returns_dataframe(self):
        summaries = [
            _make_summary("Field A", "gom", 300.0),
            _make_summary("Field B", "north_sea", 400.0),
        ]
        df = build_comparison_dataframe(summaries)
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self):
        summaries = [_make_summary("Field A", "gom", 200.0)]
        df = build_comparison_dataframe(summaries)
        required_cols = {
            "field_name",
            "region",
            "total_cost_usd_mm",
            "deviation_pct",
            "is_outlier",
        }
        assert required_cols.issubset(set(df.columns))

    def test_row_count_matches_input(self):
        summaries = [
            _make_summary("F1", "gom", 100.0),
            _make_summary("F2", "gom", 200.0),
            _make_summary("F3", "north_sea", 300.0),
        ]
        df = build_comparison_dataframe(summaries)
        assert len(df) == 3

    def test_empty_summaries_returns_empty_dataframe(self):
        df = build_comparison_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_cost_per_well_column_present(self):
        summaries = [_make_summary("F1", "gom", 200.0, n_wells=2)]
        df = build_comparison_dataframe(summaries)
        assert "cost_per_well_usd_mm" in df.columns
