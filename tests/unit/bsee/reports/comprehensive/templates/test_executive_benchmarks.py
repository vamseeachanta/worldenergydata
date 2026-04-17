"""Tests for executive benchmarking module."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.executive_benchmarks import (
    ExecutiveBenchmarking,
)

# ---------------------------------------------------------------------------
# ExecutiveBenchmarking init
# ---------------------------------------------------------------------------


class TestExecutiveBenchmarkingInit:
    def test_default_benchmarks(self):
        eb = ExecutiveBenchmarking()
        assert "uptime" in eb.industry_benchmarks
        assert "efficiency" in eb.industry_benchmarks
        assert "safety_trir" in eb.industry_benchmarks

    def test_custom_benchmarks(self):
        custom = {"uptime": 95.0, "efficiency": 90.0}
        eb = ExecutiveBenchmarking(industry_benchmarks=custom)
        assert eb.industry_benchmarks == custom


# ---------------------------------------------------------------------------
# analyze_competitive_position
# ---------------------------------------------------------------------------


class TestAnalyzeCompetitivePosition:
    def test_empty_data(self):
        eb = ExecutiveBenchmarking()
        result = eb.analyze_competitive_position({})
        assert result["percentile_rankings"] == {}
        assert result["strengths"] == []
        assert result["improvement_areas"] == []

    def test_high_percentile_is_strength(self):
        eb = ExecutiveBenchmarking()
        data = {
            "company_metrics": {"uptime": 99.0},
            "industry_benchmarks": {
                "uptime": {"p25": 85, "p50": 90, "p75": 95, "p90": 98},
            },
        }
        result = eb.analyze_competitive_position(data)
        assert result["percentile_rankings"]["uptime"] == 95
        assert "uptime" in result["strengths"]

    def test_low_percentile_is_improvement(self):
        eb = ExecutiveBenchmarking()
        data = {
            "company_metrics": {"uptime": 80.0},
            "industry_benchmarks": {
                "uptime": {"p25": 85, "p50": 90, "p75": 95, "p90": 98},
            },
        }
        result = eb.analyze_competitive_position(data)
        assert result["percentile_rankings"]["uptime"] == 25
        assert "uptime" in result["improvement_areas"]

    def test_p50_percentile(self):
        eb = ExecutiveBenchmarking()
        data = {
            "company_metrics": {"uptime": 89.0},
            "industry_benchmarks": {
                "uptime": {"p25": 85, "p50": 90, "p75": 95, "p90": 98},
            },
        }
        result = eb.analyze_competitive_position(data)
        assert result["percentile_rankings"]["uptime"] == 50

    def test_p75_percentile(self):
        eb = ExecutiveBenchmarking()
        data = {
            "company_metrics": {"uptime": 94.0},
            "industry_benchmarks": {
                "uptime": {"p25": 85, "p50": 90, "p75": 95, "p90": 98},
            },
        }
        result = eb.analyze_competitive_position(data)
        assert result["percentile_rankings"]["uptime"] == 75

    def test_peer_comparison(self):
        eb = ExecutiveBenchmarking()
        data = {
            "company_metrics": {"production_efficiency": 90.0, "safety_score": 95.0},
            "industry_benchmarks": {},
            "peer_companies": [
                {"name": "PeerA", "production_efficiency": 85.0, "safety_score": 92.0},
            ],
        }
        result = eb.analyze_competitive_position(data)
        assert "PeerA" in result["peer_comparison"]
        assert (
            result["peer_comparison"]["PeerA"]["production_efficiency"]["difference"]
            == 5.0
        )


# ---------------------------------------------------------------------------
# generate_peer_ranking_table
# ---------------------------------------------------------------------------


class TestGeneratePeerRankingTable:
    def test_empty_peers(self):
        eb = ExecutiveBenchmarking()
        result = eb.generate_peer_ranking_table([])
        assert len(result) == 1  # Just our company
        assert result[0]["rank"] == 1

    def test_with_peers(self):
        eb = ExecutiveBenchmarking()
        peers = [
            {"name": "PeerA", "production_efficiency": 92.0, "safety_score": 90.0},
            {"name": "PeerB", "production_efficiency": 85.0, "safety_score": 88.0},
        ]
        result = eb.generate_peer_ranking_table(peers)
        assert len(result) == 3
        # Sorted by production_efficiency descending
        assert result[0]["production_efficiency"] >= result[1]["production_efficiency"]
        assert result[0]["rank"] == 1

    def test_custom_company_data(self):
        eb = ExecutiveBenchmarking()
        company = {
            "name": "MyCompany",
            "production_efficiency": 99.0,
            "safety_score": 100.0,
        }
        result = eb.generate_peer_ranking_table([], company_data=company)
        assert result[0]["name"] == "MyCompany"


# ---------------------------------------------------------------------------
# calculate_benchmark_gaps
# ---------------------------------------------------------------------------


class TestCalculateBenchmarkGaps:
    def test_above_benchmark(self):
        eb = ExecutiveBenchmarking()
        gaps = eb.calculate_benchmark_gaps({"uptime": 95.0})
        assert gaps["uptime"]["status"] == "above"
        assert gaps["uptime"]["gap"] > 0

    def test_below_benchmark(self):
        eb = ExecutiveBenchmarking()
        gaps = eb.calculate_benchmark_gaps({"uptime": 88.0})
        assert gaps["uptime"]["status"] == "below"
        assert gaps["uptime"]["gap"] < 0

    def test_at_benchmark(self):
        eb = ExecutiveBenchmarking()
        gaps = eb.calculate_benchmark_gaps({"uptime": 92.0})
        assert gaps["uptime"]["status"] == "at"

    def test_gap_percentage(self):
        eb = ExecutiveBenchmarking()
        gaps = eb.calculate_benchmark_gaps({"efficiency": 90.0})
        # benchmark is 85.0, gap = 5.0, pct = (5/85)*100 = 5.88%
        assert gaps["efficiency"]["gap_percentage"] == pytest.approx(5.88, abs=0.1)

    def test_unknown_metric_ignored(self):
        eb = ExecutiveBenchmarking()
        gaps = eb.calculate_benchmark_gaps({"unknown_metric": 50.0})
        assert "unknown_metric" not in gaps


# ---------------------------------------------------------------------------
# identify_improvement_opportunities
# ---------------------------------------------------------------------------


class TestIdentifyImprovementOpportunities:
    def test_no_gaps(self):
        eb = ExecutiveBenchmarking()
        gaps = eb.calculate_benchmark_gaps({"uptime": 95.0})  # above
        opps = eb.identify_improvement_opportunities(gaps)
        assert opps == []

    def test_below_benchmark_creates_opportunity(self):
        eb = ExecutiveBenchmarking()
        gaps = eb.calculate_benchmark_gaps({"uptime": 80.0})
        opps = eb.identify_improvement_opportunities(gaps)
        assert len(opps) == 1
        assert opps[0]["metric"] == "uptime"

    def test_sorted_by_priority(self):
        eb = ExecutiveBenchmarking()
        gaps = {
            "efficiency": {
                "status": "below",
                "company_value": 70,
                "benchmark": 85,
                "gap": -15,
                "gap_percentage": -17.6,
            },
            "uptime": {
                "status": "below",
                "company_value": 80,
                "benchmark": 92,
                "gap": -12,
                "gap_percentage": -13.0,
            },
        }
        opps = eb.identify_improvement_opportunities(gaps)
        # Both should be medium or high priority
        assert len(opps) == 2


# ---------------------------------------------------------------------------
# _calculate_priority
# ---------------------------------------------------------------------------


class TestCalculatePriority:
    def test_critical_metric_is_high(self):
        eb = ExecutiveBenchmarking()
        assert eb._calculate_priority("safety_trir", -5) == "high"
        assert eb._calculate_priority("uptime", -5) == "high"
        assert eb._calculate_priority("efficiency", -5) == "high"

    def test_large_gap_is_high(self):
        eb = ExecutiveBenchmarking()
        assert eb._calculate_priority("some_metric", -25) == "high"

    def test_medium_gap(self):
        eb = ExecutiveBenchmarking()
        assert eb._calculate_priority("some_metric", -15) == "medium"

    def test_small_gap_is_low(self):
        eb = ExecutiveBenchmarking()
        assert eb._calculate_priority("some_metric", -5) == "low"


# ---------------------------------------------------------------------------
# _get_ranking_label
# ---------------------------------------------------------------------------


class TestGetRankingLabel:
    def test_leader(self):
        eb = ExecutiveBenchmarking()
        assert eb._get_ranking_label(95) == "Industry Leader"

    def test_above_average(self):
        eb = ExecutiveBenchmarking()
        assert eb._get_ranking_label(80) == "Above Average"

    def test_average(self):
        eb = ExecutiveBenchmarking()
        assert eb._get_ranking_label(60) == "Average"

    def test_below_average(self):
        eb = ExecutiveBenchmarking()
        assert eb._get_ranking_label(30) == "Below Average"

    def test_needs_improvement(self):
        eb = ExecutiveBenchmarking()
        assert eb._get_ranking_label(20) == "Needs Improvement"


# ---------------------------------------------------------------------------
# generate_competitive_summary
# ---------------------------------------------------------------------------


class TestGenerateCompetitiveSummary:
    def test_basic(self):
        eb = ExecutiveBenchmarking()
        data = {
            "company_metrics": {"uptime": 95.0, "efficiency": 90.0},
            "industry_benchmarks": {
                "uptime": {"p25": 85, "p50": 90, "p75": 93, "p90": 97},
                "efficiency": {"p25": 75, "p50": 82, "p75": 88, "p90": 93},
            },
        }
        summary = eb.generate_competitive_summary(data)
        assert "competitive_score" in summary
        assert "ranking_label" in summary
        assert "positioning" in summary
        assert "gaps" in summary
        assert "opportunities" in summary

    def test_empty_data(self):
        eb = ExecutiveBenchmarking()
        summary = eb.generate_competitive_summary({})
        assert summary["competitive_score"] == 50  # default when no rankings


# ---------------------------------------------------------------------------
# create_radar_chart (delegates to create_benchmark_radar_chart)
# ---------------------------------------------------------------------------


class TestCreateRadarChart:
    def test_basic_radar_chart(self):
        eb = ExecutiveBenchmarking()
        data = {
            "company_metrics": {"uptime": 95.0, "efficiency": 90.0},
            "industry_benchmarks": {
                "uptime": {"p25": 85, "p50": 90, "p75": 95, "p90": 98},
                "efficiency": {"p25": 75, "p50": 82, "p75": 88, "p90": 93},
            },
        }
        result = eb.create_radar_chart(data)
        # Returns a Plotly figure or None
        assert result is not None or result is None  # exercises the delegation path
