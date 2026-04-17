"""Tests for executive template calculations."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.reports.comprehensive.templates.executive_calculations import (
    ExecutiveCalculations,
)
from worldenergydata.bsee.reports.comprehensive.templates.executive_models import (
    ExecutiveKPI,
    PerformanceScore,
    StrategicMetric,
)

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestExecutiveCalculationsInit:
    def test_defaults(self):
        calc = ExecutiveCalculations()
        assert "uptime" in calc.kpi_thresholds
        assert "uptime" in calc.benchmarks

    def test_custom_thresholds(self):
        custom = {"uptime": {"green": 99, "yellow": 95}}
        calc = ExecutiveCalculations(kpi_thresholds=custom)
        assert calc.kpi_thresholds["uptime"]["green"] == 99

    def test_custom_benchmarks(self):
        custom = {"uptime": 98.0}
        calc = ExecutiveCalculations(benchmarks=custom)
        assert calc.benchmarks["uptime"] == 98.0


# ---------------------------------------------------------------------------
# calculate_trend
# ---------------------------------------------------------------------------


class TestCalculateTrend:
    def test_empty_history(self):
        calc = ExecutiveCalculations()
        assert calc.calculate_trend([]) == "stable"

    def test_single_value(self):
        calc = ExecutiveCalculations()
        assert calc.calculate_trend([100]) == "stable"

    def test_upward_trend(self):
        calc = ExecutiveCalculations()
        result = calc.calculate_trend([100, 110, 120])
        assert result == "up"

    def test_downward_trend(self):
        calc = ExecutiveCalculations()
        result = calc.calculate_trend([120, 110, 100])
        assert result == "down"

    def test_stable_trend(self):
        calc = ExecutiveCalculations()
        result = calc.calculate_trend([100, 100, 100])
        assert result == "stable"

    def test_two_values_up(self):
        calc = ExecutiveCalculations()
        result = calc.calculate_trend([100, 120])
        assert result == "up"

    def test_two_values_down(self):
        calc = ExecutiveCalculations()
        result = calc.calculate_trend([120, 100])
        assert result == "down"

    def test_uses_last_three_values(self):
        calc = ExecutiveCalculations()
        # Many values, but last 3 are [90, 95, 100] -> up
        result = calc.calculate_trend([200, 150, 90, 95, 100])
        assert result == "up"

    def test_analyze_kpi_trend_delegates(self):
        calc = ExecutiveCalculations()
        assert calc.analyze_kpi_trend([100, 110, 120]) == "up"


# ---------------------------------------------------------------------------
# determine_kpi_status / determine_traffic_light_status
# ---------------------------------------------------------------------------


class TestDetermineKpiStatus:
    def test_green(self):
        calc = ExecutiveCalculations()
        assert calc.determine_kpi_status(100, 95) == "green"

    def test_yellow(self):
        calc = ExecutiveCalculations()
        assert calc.determine_kpi_status(91, 95) == "yellow"

    def test_red(self):
        calc = ExecutiveCalculations()
        assert calc.determine_kpi_status(80, 95) == "red"


class TestDetermineTrafficLightStatus:
    def test_green(self):
        calc = ExecutiveCalculations()
        assert calc.determine_traffic_light_status(100, 95, 90) == "green"

    def test_yellow(self):
        calc = ExecutiveCalculations()
        assert calc.determine_traffic_light_status(92, 95, 90) == "yellow"

    def test_red(self):
        calc = ExecutiveCalculations()
        assert calc.determine_traffic_light_status(85, 95, 90) == "red"


# ---------------------------------------------------------------------------
# calculate_performance_score
# ---------------------------------------------------------------------------


class TestCalculatePerformanceScore:
    def test_empty_kpis(self):
        calc = ExecutiveCalculations()
        score = calc.calculate_performance_score([])
        assert isinstance(score, PerformanceScore)
        assert score.overall == 0.0

    def test_single_kpi_meeting_target(self):
        calc = ExecutiveCalculations()
        kpi = ExecutiveKPI(
            name="Revenue",
            value=100,
            unit="$",
            target=100,
            category="Financial",
        )
        score = calc.calculate_performance_score([kpi])
        assert score.overall == 100.0
        assert "Financial" in score.category_scores

    def test_single_kpi_below_target(self):
        calc = ExecutiveCalculations()
        kpi = ExecutiveKPI(
            name="Revenue",
            value=50,
            unit="$",
            target=100,
            category="Financial",
        )
        score = calc.calculate_performance_score([kpi])
        assert score.overall == 50.0

    def test_multiple_categories(self):
        calc = ExecutiveCalculations()
        kpis = [
            ExecutiveKPI(
                name="Revenue", value=100, unit="$", target=100, category="Financial"
            ),
            ExecutiveKPI(
                name="Uptime", value=80, unit="%", target=100, category="Operational"
            ),
        ]
        score = calc.calculate_performance_score(kpis)
        assert "Financial" in score.category_scores
        assert "Operational" in score.category_scores
        # Financial=100%, Operational=80%, overall = (100+80)/2 = 90
        assert score.overall == 90.0

    def test_no_target_kpi_skipped(self):
        calc = ExecutiveCalculations()
        kpis = [
            ExecutiveKPI(
                name="Revenue", value=100, unit="$", target=None, category="Financial"
            ),
        ]
        score = calc.calculate_performance_score(kpis)
        assert score.overall == 0.0

    def test_trend_up_for_high_score(self):
        calc = ExecutiveCalculations()
        kpis = [
            ExecutiveKPI(
                name="Revenue", value=100, unit="$", target=100, category="Financial"
            ),
        ]
        score = calc.calculate_performance_score(kpis)
        assert score.trend == "up"  # overall >= 85

    def test_trend_down_for_low_score(self):
        calc = ExecutiveCalculations()
        kpis = [
            ExecutiveKPI(
                name="Revenue", value=50, unit="$", target=100, category="Financial"
            ),
        ]
        score = calc.calculate_performance_score(kpis)
        assert score.trend == "down"  # overall < 70

    def test_trend_stable_for_mid_score(self):
        calc = ExecutiveCalculations()
        kpis = [
            ExecutiveKPI(
                name="Revenue", value=75, unit="$", target=100, category="Financial"
            ),
        ]
        score = calc.calculate_performance_score(kpis)
        assert score.trend == "stable"  # 70 <= overall < 85


# ---------------------------------------------------------------------------
# rank_kpis_by_priority
# ---------------------------------------------------------------------------


class TestRankKpisByPriority:
    def test_empty(self):
        calc = ExecutiveCalculations()
        assert calc.rank_kpis_by_priority([]) == []

    def test_revenue_first(self):
        calc = ExecutiveCalculations()
        kpis = [
            ExecutiveKPI(
                name="Efficiency", value=80, unit="%", target=100, status="yellow"
            ),
            ExecutiveKPI(
                name="Revenue", value=1000, unit="$", target=2000, status="red"
            ),
        ]
        ranked = calc.rank_kpis_by_priority(kpis)
        assert ranked[0].name == "Revenue"

    def test_safety_high_priority(self):
        calc = ExecutiveCalculations()
        kpis = [
            ExecutiveKPI(name="Uptime", value=90, unit="%", target=95),
            ExecutiveKPI(name="Safety Score", value=80, unit="score", target=95),
        ]
        ranked = calc.rank_kpis_by_priority(kpis)
        assert ranked[0].name == "Safety Score"


# ---------------------------------------------------------------------------
# calculate_strategic_metrics
# ---------------------------------------------------------------------------


class TestCalculateStrategicMetrics:
    def test_empty_data(self):
        calc = ExecutiveCalculations()
        assert calc.calculate_strategic_metrics({}) == []

    def test_missing_periods(self):
        calc = ExecutiveCalculations()
        assert calc.calculate_strategic_metrics({"current_period": {}}) == []

    def test_with_revenue(self):
        calc = ExecutiveCalculations()
        data = {
            "current_period": {"revenue": 1000000},
            "previous_period": {"revenue": 900000},
            "targets": {"revenue": 1100000},
        }
        metrics = calc.calculate_strategic_metrics(data)
        assert len(metrics) == 1
        assert isinstance(metrics[0], StrategicMetric)
        assert metrics[0].name == "Revenue"
        assert metrics[0].current_value == 1000000

    def test_multiple_metrics(self):
        calc = ExecutiveCalculations()
        data = {
            "current_period": {"revenue": 1000000, "market_share": 15.5, "roi": 22.0},
            "previous_period": {"revenue": 900000, "market_share": 14.0, "roi": 18.0},
        }
        metrics = calc.calculate_strategic_metrics(data)
        names = [m.name for m in metrics]
        assert "Revenue" in names
        assert "Market Share" in names
        assert "Return on Investment" in names


# ---------------------------------------------------------------------------
# compare_with_benchmarks
# ---------------------------------------------------------------------------


class TestCompareWithBenchmarks:
    def test_empty(self):
        calc = ExecutiveCalculations()
        assert calc.compare_with_benchmarks({}, {}) == {}

    def test_above_benchmark(self):
        calc = ExecutiveCalculations()
        data = {"operational": {"uptime": 95.0}}
        benchmarks = {"uptime": 92.0}
        result = calc.compare_with_benchmarks(data, benchmarks)
        assert "uptime" in result
        assert result["uptime"]["performance"] == "above"
        assert result["uptime"]["vs_benchmark"] == 3.0

    def test_below_benchmark(self):
        calc = ExecutiveCalculations()
        data = {"operational": {"uptime": 88.0}}
        benchmarks = {"uptime": 92.0}
        result = calc.compare_with_benchmarks(data, benchmarks)
        assert result["uptime"]["performance"] == "below"

    def test_missing_metric_in_data(self):
        calc = ExecutiveCalculations()
        data = {"operational": {"uptime": 95.0}}
        benchmarks = {"uptime": 92.0, "efficiency": 85.0}
        result = calc.compare_with_benchmarks(data, benchmarks)
        assert "efficiency" not in result


# ---------------------------------------------------------------------------
# analyze_year_over_year
# ---------------------------------------------------------------------------


class TestAnalyzeYearOverYear:
    def test_insufficient_data(self):
        calc = ExecutiveCalculations()
        result = calc.analyze_year_over_year({"2024": {"revenue": 1000}})
        assert "error" in result

    def test_two_years_growth(self):
        calc = ExecutiveCalculations()
        data = {
            "2023": {"revenue": 1000},
            "2024": {"revenue": 1200},
        }
        result = calc.analyze_year_over_year(data)
        assert result["trend_direction"] == "growth"
        assert result["latest_year"] == "2024"
        assert result["comparison_year"] == "2023"
        assert result["cagr"] is None  # Only 2 years, no CAGR

    def test_two_years_decline(self):
        calc = ExecutiveCalculations()
        data = {
            "2023": {"revenue": 1200},
            "2024": {"revenue": 1000},
        }
        result = calc.analyze_year_over_year(data)
        assert result["trend_direction"] == "decline"

    def test_three_years_cagr(self):
        calc = ExecutiveCalculations()
        data = {
            "2022": {"revenue": 1000},
            "2023": {"revenue": 1100},
            "2024": {"revenue": 1210},
        }
        result = calc.analyze_year_over_year(data)
        assert result["cagr"] is not None
        assert result["cagr"] > 0

    def test_volatility(self):
        calc = ExecutiveCalculations()
        data = {
            "2022": {"revenue": 1000},
            "2023": {"revenue": 1500},
            "2024": {"revenue": 1000},
        }
        result = calc.analyze_year_over_year(data)
        assert result["volatility"] > 0


# ---------------------------------------------------------------------------
# generate_strategic_forecast
# ---------------------------------------------------------------------------


class TestGenerateStrategicForecast:
    def test_revenue_forecast(self):
        calc = ExecutiveCalculations()
        df = pd.DataFrame({"revenue": [100, 200, 300, 400, 500]})
        result = calc.generate_strategic_forecast(df, periods=3)
        assert "revenue_forecast" in result
        assert len(result["revenue_forecast"]) == 3
        # Linear trend should forecast values > 500
        assert result["revenue_forecast"][0] > 500

    def test_production_forecast(self):
        calc = ExecutiveCalculations()
        df = pd.DataFrame({"production": [1000, 1100, 1200]})
        result = calc.generate_strategic_forecast(df, periods=2)
        # Source code maps production forecast via revenue_forecast key from _forecast_metric
        assert "production_forecast" in result

    def test_empty_columns(self):
        calc = ExecutiveCalculations()
        df = pd.DataFrame({"other": [1, 2, 3]})
        result = calc.generate_strategic_forecast(df, periods=2)
        assert result == {}

    def test_confidence_interval(self):
        calc = ExecutiveCalculations()
        df = pd.DataFrame({"revenue": [100, 200, 300]})
        result = calc.generate_strategic_forecast(df, periods=1)
        assert "confidence_interval" in result


# ---------------------------------------------------------------------------
# track_strategic_goals
# ---------------------------------------------------------------------------


class TestTrackStrategicGoals:
    def test_empty_goals(self):
        calc = ExecutiveCalculations()
        assert calc.track_strategic_goals([]) == []

    def test_single_goal(self):
        calc = ExecutiveCalculations()
        goals = [
            {
                "name": "Revenue Target",
                "current": 800000,
                "target": 1000000,
                "deadline": "2027-12-31",
            }
        ]
        results = calc.track_strategic_goals(goals)
        assert len(results) == 1
        assert results[0]["name"] == "Revenue Target"
        assert results[0]["progress_percentage"] == 80.0
        assert "days_remaining" in results[0]
        assert "on_track" in results[0]

    def test_zero_target(self):
        calc = ExecutiveCalculations()
        goals = [
            {
                "name": "Test",
                "current": 500,
                "target": 0,
                "deadline": "2027-12-31",
            }
        ]
        results = calc.track_strategic_goals(goals)
        assert results[0]["progress_percentage"] == 0


# ---------------------------------------------------------------------------
# generate_executive_kpis (integration through ExecutiveCalculations)
# ---------------------------------------------------------------------------


class TestGenerateExecutiveKpis:
    def test_financial_kpis(self):
        calc = ExecutiveCalculations()
        data = {
            "financial": {
                "revenue": 5000000,
                "revenue_target": 4000000,
                "ebitda": 2000000,
                "ebitda_target": 1800000,
                "roi": 25.0,
            }
        }
        kpis = calc.generate_executive_kpis(data)
        assert len(kpis) >= 2
        names = [k.name for k in kpis]
        assert "Revenue" in names
        assert "EBITDA" in names

    def test_operational_kpis(self):
        calc = ExecutiveCalculations()
        data = {
            "operational": {
                "uptime_percentage": 96.5,
                "efficiency_rate": 88.0,
            }
        }
        kpis = calc.generate_executive_kpis(data)
        assert len(kpis) == 2
        names = [k.name for k in kpis]
        assert "Uptime" in names
        assert "Efficiency" in names

    def test_empty_data(self):
        calc = ExecutiveCalculations()
        kpis = calc.generate_executive_kpis({})
        assert kpis == []
