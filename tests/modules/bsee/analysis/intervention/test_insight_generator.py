"""Tests for InsightGenerator (WRK-116 Phase 4).

TDD test suite verifying that InsightGenerator transforms structured
analysis results from ComprehensiveActivityAnalyzer.analyze() into
ranked business insights across 5 categories.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.insight_generator import (
    InsightGenerator,
)

_EXPECTED_KEYS = frozenset({
    "key_findings",
    "market_trends",
    "competitive_intelligence",
    "opportunity_areas",
    "risk_factors",
})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def analysis_results() -> dict:
    """Realistic analysis dict matching ComprehensiveActivityAnalyzer output.

    Uses small DataFrames (3-5 rows) with known values to enable
    deterministic assertion of insight content.
    """
    return {
        "drilling_efficiency": {
            "total_wells_with_duration": 42,
            "mean_drilling_days": 85.3,
            "median_drilling_days": 72.0,
            "by_rig_type": pd.DataFrame({
                "RIG_TYPE": ["drillship", "semi_submersible", "jack_up"],
                "mean_days": [95.2, 80.1, 45.6],
                "median_days": [90.0, 75.0, 40.0],
                "count": [20, 15, 7],
            }),
            "by_depth_class": pd.DataFrame({
                "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep", "Shallow"],
                "mean_days": [70.0, 110.5, 35.0],
                "median_days": [65.0, 105.0, 30.0],
                "count": [18, 16, 8],
            }),
            "by_year": pd.DataFrame({
                "YEAR": [2020, 2021, 2022],
                "mean_days": [90.0, 85.0, 78.0],
                "median_days": [88.0, 82.0, 75.0],
                "count": [14, 16, 12],
            }),
        },
        "well_depth": {
            "mean_total_md": 18500.0,
            "max_total_md": 32000.0,
            "by_rig_type": pd.DataFrame({
                "RIG_TYPE": ["drillship", "semi_submersible", "jack_up"],
                "mean_md": [22000.0, 19000.0, 12000.0],
                "max_md": [32000.0, 25000.0, 15000.0],
                "count": [20, 15, 7],
            }),
            "by_area": pd.DataFrame({
                "AREA_CODE": ["GC", "WR", "MC"],
                "mean_md": [20000.0, 22000.0, 15000.0],
                "max_md": [32000.0, 28000.0, 18000.0],
                "count": [18, 14, 10],
            }),
            "by_year": pd.DataFrame({
                "YEAR": [2020, 2021, 2022],
                "mean_md": [17000.0, 18500.0, 20000.0],
                "max_md": [28000.0, 30000.0, 32000.0],
                "count": [14, 16, 12],
            }),
        },
        "geological_era": {
            "wells_with_era": 30,
            "era_distribution": pd.DataFrame({
                "GEOLOGICAL_ERA": ["Miocene", "Eocene", "Pleistocene"],
                "activity_count": [18, 8, 4],
                "unique_wells": [12, 6, 3],
            }),
            "era_by_category": pd.DataFrame({
                "GEOLOGICAL_ERA": ["Miocene", "Miocene", "Eocene"],
                "ACTIVITY_CATEGORY": ["drilling", "intervention", "drilling"],
                "count": [12, 6, 8],
            }),
        },
        "cross_activity": {
            "drilling_count": 42,
            "intervention_count": 28,
            "ratio": 1.5,
            "by_depth_class": pd.DataFrame({
                "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep", "Shallow"],
                "drilling": [18, 16, 8],
                "intervention": [10, 12, 6],
                "ratio": [1.8, 1.33, 1.33],
            }),
            "by_area": pd.DataFrame({
                "AREA_CODE": ["GC", "WR", "MC", "HI"],
                "drilling": [15, 12, 8, 7],
                "intervention": [10, 8, 6, 4],
                "ratio": [1.5, 1.5, 1.33, 1.75],
            }),
        },
        "well_lifecycle": {
            "status_distribution": pd.DataFrame({
                "WELL_STATUS": ["COM", "PA", "DRL", "TA", "ST"],
                "count": [25, 20, 10, 8, 7],
                "pct": [0.357, 0.286, 0.143, 0.114, 0.100],
            }),
            "by_depth_class": pd.DataFrame({
                "WATER_DEPTH_CLASS": ["Deep", "Deep", "Ultra-deep"],
                "WELL_STATUS": ["COM", "PA", "COM"],
                "count": [12, 8, 10],
            }),
            "completion_rate": 0.357,
        },
        "operator_portfolio": {
            "top_operators": pd.DataFrame({
                "BUS_ASC_NAME": [
                    "SHELL OFFSHORE", "BP EXPLORATION",
                    "CHEVRON USA", "TOTAL E&P USA",
                ],
                "activity_count": [18, 14, 10, 8],
                "unique_wells": [10, 8, 6, 5],
                "unique_areas": [3, 4, 2, 3],
            }),
            "by_depth_class": pd.DataFrame({
                "BUS_ASC_NAME": ["SHELL OFFSHORE", "BP EXPLORATION"],
                "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep"],
                "count": [12, 10],
            }),
            "by_rig_type": pd.DataFrame({
                "BUS_ASC_NAME": ["SHELL OFFSHORE", "BP EXPLORATION"],
                "RIG_TYPE": ["drillship", "semi_submersible"],
                "count": [10, 8],
            }),
        },
        "duration_benchmarking": {
            "by_depth_and_type": pd.DataFrame({
                "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep"],
                "RIG_TYPE": ["drillship", "semi_submersible"],
                "mean_days": [85.0, 110.0],
                "p25": [60.0, 80.0],
                "p50": [80.0, 105.0],
                "p75": [100.0, 130.0],
                "count": [15, 12],
            }),
            "quartiles": pd.DataFrame({
                "quartile": ["Q1", "Q2", "Q3", "Q4"],
                "min_days": [10.0, 45.0, 72.0, 110.0],
                "max_days": [45.0, 72.0, 110.0, 200.0],
            }),
        },
    }


@pytest.fixture()
def high_drilling_ratio_results(analysis_results: dict) -> dict:
    """Analysis results where a depth class has ratio > 3 (opportunity)."""
    results = analysis_results.copy()
    results["cross_activity"] = {
        "drilling_count": 50,
        "intervention_count": 10,
        "ratio": 5.0,
        "by_depth_class": pd.DataFrame({
            "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep", "Shallow"],
            "drilling": [20, 16, 14],
            "intervention": [5, 3, 2],
            "ratio": [4.0, 5.33, 7.0],
        }),
        "by_area": pd.DataFrame({
            "AREA_CODE": ["GC", "WR"],
            "drilling": [30, 20],
            "intervention": [5, 5],
            "ratio": [6.0, 4.0],
        }),
    }
    return results


@pytest.fixture()
def high_pa_results(analysis_results: dict) -> dict:
    """Analysis results with PA rate > 30% for risk factor detection."""
    results = analysis_results.copy()
    results["well_lifecycle"] = {
        "status_distribution": pd.DataFrame({
            "WELL_STATUS": ["PA", "COM", "DRL"],
            "count": [40, 30, 10],
            "pct": [0.50, 0.375, 0.125],
        }),
        "by_depth_class": pd.DataFrame({
            "WATER_DEPTH_CLASS": ["Deep"],
            "WELL_STATUS": ["PA"],
            "count": [20],
        }),
        "completion_rate": 0.375,
    }
    return results


@pytest.fixture()
def empty_analysis_results() -> dict:
    """All 7 keys present but with empty/zero data."""
    return {
        "drilling_efficiency": {
            "total_wells_with_duration": 0,
            "mean_drilling_days": 0.0,
            "median_drilling_days": 0.0,
            "by_rig_type": pd.DataFrame(columns=["RIG_TYPE", "mean_days", "median_days", "count"]),
            "by_depth_class": pd.DataFrame(columns=["WATER_DEPTH_CLASS", "mean_days", "median_days", "count"]),
            "by_year": pd.DataFrame(columns=["YEAR", "mean_days", "median_days", "count"]),
        },
        "well_depth": {
            "mean_total_md": 0.0,
            "max_total_md": 0.0,
            "by_rig_type": pd.DataFrame(columns=["RIG_TYPE", "mean_md", "max_md", "count"]),
            "by_area": pd.DataFrame(columns=["AREA_CODE", "mean_md", "max_md", "count"]),
            "by_year": pd.DataFrame(columns=["YEAR", "mean_md", "max_md", "count"]),
        },
        "geological_era": {
            "wells_with_era": 0,
            "era_distribution": pd.DataFrame(columns=["GEOLOGICAL_ERA", "activity_count", "unique_wells"]),
            "era_by_category": pd.DataFrame(columns=["GEOLOGICAL_ERA", "ACTIVITY_CATEGORY", "count"]),
        },
        "cross_activity": {
            "drilling_count": 0,
            "intervention_count": 0,
            "ratio": 0.0,
            "by_depth_class": pd.DataFrame(columns=["WATER_DEPTH_CLASS", "drilling", "intervention", "ratio"]),
            "by_area": pd.DataFrame(columns=["AREA_CODE", "drilling", "intervention", "ratio"]),
        },
        "well_lifecycle": {
            "status_distribution": pd.DataFrame(columns=["WELL_STATUS", "count", "pct"]),
            "by_depth_class": pd.DataFrame(columns=["WATER_DEPTH_CLASS", "WELL_STATUS", "count"]),
            "completion_rate": 0.0,
        },
        "operator_portfolio": {
            "top_operators": pd.DataFrame(columns=["BUS_ASC_NAME", "activity_count", "unique_wells", "unique_areas"]),
            "by_depth_class": pd.DataFrame(columns=["BUS_ASC_NAME", "WATER_DEPTH_CLASS", "count"]),
            "by_rig_type": pd.DataFrame(columns=["BUS_ASC_NAME", "RIG_TYPE", "count"]),
        },
        "duration_benchmarking": {
            "by_depth_and_type": pd.DataFrame(columns=["WATER_DEPTH_CLASS", "RIG_TYPE", "mean_days", "p25", "p50", "p75", "count"]),
            "quartiles": pd.DataFrame(columns=["quartile", "min_days", "max_days"]),
        },
    }


@pytest.fixture()
def single_year_results(analysis_results: dict) -> dict:
    """Analysis results with only 1 year of data."""
    results = analysis_results.copy()
    results["drilling_efficiency"] = {
        **results["drilling_efficiency"],
        "by_year": pd.DataFrame({
            "YEAR": [2022],
            "mean_days": [78.0],
            "median_days": [75.0],
            "count": [12],
        }),
    }
    results["well_depth"] = {
        **results["well_depth"],
        "by_year": pd.DataFrame({
            "YEAR": [2022],
            "mean_md": [20000.0],
            "max_md": [32000.0],
            "count": [12],
        }),
    }
    return results


@pytest.fixture()
def empty_portfolio_results(analysis_results: dict) -> dict:
    """Analysis results with empty operator portfolio."""
    results = analysis_results.copy()
    results["operator_portfolio"] = {
        "top_operators": pd.DataFrame(
            columns=["BUS_ASC_NAME", "activity_count", "unique_wells", "unique_areas"],
        ),
        "by_depth_class": pd.DataFrame(
            columns=["BUS_ASC_NAME", "WATER_DEPTH_CLASS", "count"],
        ),
        "by_rig_type": pd.DataFrame(
            columns=["BUS_ASC_NAME", "RIG_TYPE", "count"],
        ),
    }
    return results


# ---------------------------------------------------------------------------
# 1. Contract: generate() returns dict with 5 keys
# ---------------------------------------------------------------------------


class TestGenerateContract:
    """Verify generate() output structure."""

    def test_generate_returns_dict_with_five_keys(
        self, analysis_results: dict,
    ) -> None:
        gen = InsightGenerator(analysis_results)
        result = gen.generate()
        assert isinstance(result, dict)
        assert set(result.keys()) == _EXPECTED_KEYS


# ---------------------------------------------------------------------------
# 2. Key findings
# ---------------------------------------------------------------------------


class TestKeyFindings:
    """Verify key_findings insights."""

    def test_key_findings_non_empty(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        assert len(result["key_findings"]) >= 1

    def test_key_findings_mentions_drilling_duration(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        findings = result["key_findings"]
        matches = [f for f in findings if "drilling" in f.lower() and "days" in f.lower()]
        assert len(matches) >= 1, (
            f"Expected a finding mentioning drilling and days, got: {findings}"
        )

    def test_key_findings_mentions_operator(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        findings = result["key_findings"]
        matches = [f for f in findings if "SHELL OFFSHORE" in f]
        assert len(matches) >= 1, (
            f"Expected a finding mentioning SHELL OFFSHORE, got: {findings}"
        )


# ---------------------------------------------------------------------------
# 3. Market trends
# ---------------------------------------------------------------------------


class TestMarketTrends:
    """Verify market_trends insights."""

    def test_market_trends_non_empty(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        assert len(result["market_trends"]) >= 1

    def test_market_trends_year_comparison(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        trends = result["market_trends"]
        has_yoy = any("year" in t.lower() for t in trends)
        has_insuff = any("insufficient" in t.lower() for t in trends)
        assert has_yoy or has_insuff, (
            f"Expected year-over-year or insufficient data note, got: {trends}"
        )

    def test_single_year_trend(
        self, single_year_results: dict,
    ) -> None:
        result = InsightGenerator(single_year_results).generate()
        trends = result["market_trends"]
        has_insuff = any("insufficient" in t.lower() for t in trends)
        assert has_insuff, (
            f"Expected insufficient data note for single year, got: {trends}"
        )


# ---------------------------------------------------------------------------
# 4. Competitive intelligence
# ---------------------------------------------------------------------------


class TestCompetitiveIntelligence:
    """Verify competitive_intelligence insights."""

    def test_competitive_intelligence_lists_operators(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        ci = result["competitive_intelligence"]
        assert len(ci) >= 1
        has_operator = any("SHELL" in s or "BP" in s or "CHEVRON" in s for s in ci)
        assert has_operator, (
            f"Expected operator name in competitive intelligence, got: {ci}"
        )

    def test_competitive_intelligence_empty_portfolio(
        self, empty_portfolio_results: dict,
    ) -> None:
        result = InsightGenerator(empty_portfolio_results).generate()
        ci = result["competitive_intelligence"]
        assert ci == ["No operator data available"]


# ---------------------------------------------------------------------------
# 5. Opportunity areas
# ---------------------------------------------------------------------------


class TestOpportunityAreas:
    """Verify opportunity_areas insights."""

    def test_opportunity_areas_non_empty(
        self, high_drilling_ratio_results: dict,
    ) -> None:
        result = InsightGenerator(high_drilling_ratio_results).generate()
        assert len(result["opportunity_areas"]) >= 1


# ---------------------------------------------------------------------------
# 6. Risk factors
# ---------------------------------------------------------------------------


class TestRiskFactors:
    """Verify risk_factors insights."""

    def test_risk_factors_non_empty(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        assert len(result["risk_factors"]) >= 1

    def test_risk_factors_high_pa_rate(
        self, high_pa_results: dict,
    ) -> None:
        result = InsightGenerator(high_pa_results).generate()
        risks = result["risk_factors"]
        has_pa = any("P&A" in r or "pa" in r.lower() for r in risks)
        assert has_pa, f"Expected P&A risk factor, got: {risks}"


# ---------------------------------------------------------------------------
# 7. Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Verify graceful handling of empty/missing data."""

    def test_empty_analysis_results_graceful(
        self, empty_analysis_results: dict,
    ) -> None:
        result = InsightGenerator(empty_analysis_results).generate()
        assert set(result.keys()) == _EXPECTED_KEYS
        for key in _EXPECTED_KEYS:
            assert isinstance(result[key], list)

    def test_all_lists_contain_strings(
        self, analysis_results: dict,
    ) -> None:
        result = InsightGenerator(analysis_results).generate()
        for key, items in result.items():
            assert isinstance(items, list), f"{key} is not a list"
            for i, item in enumerate(items):
                assert isinstance(item, str), (
                    f"{key}[{i}] is {type(item).__name__}, not str"
                )
