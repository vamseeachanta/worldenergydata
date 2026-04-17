"""Tests for production quota analysis module."""

from datetime import date

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.production_quota_analysis import (
    ProductionQuotaAnalyzer,
    QuotaVarianceAnalysis,
)


def _make_analysis(**overrides):
    """Create a QuotaVarianceAnalysis with sensible defaults."""
    defaults = {
        "entity_id": "E001",
        "period_start": date(2024, 1, 1),
        "period_end": date(2024, 3, 31),
        "oil_quota_bbls": 100000,
        "oil_actual_bbls": 95000,
        "gas_quota_mcf": 500000,
        "gas_actual_mcf": 480000,
    }
    defaults.update(overrides)
    return QuotaVarianceAnalysis(**defaults)


# ---------------------------------------------------------------------------
# QuotaVarianceAnalysis
# ---------------------------------------------------------------------------


class TestQuotaVarianceAnalysisPostInit:
    def test_oil_variance(self):
        a = _make_analysis(oil_quota_bbls=100000, oil_actual_bbls=95000)
        assert a.oil_variance_bbls == -5000

    def test_gas_variance(self):
        a = _make_analysis(gas_quota_mcf=500000, gas_actual_mcf=520000)
        assert a.gas_variance_mcf == 20000

    def test_oil_variance_pct(self):
        a = _make_analysis(oil_quota_bbls=100000, oil_actual_bbls=110000)
        assert a.oil_variance_pct == pytest.approx(10.0)

    def test_zero_quota_variance_pct(self):
        a = _make_analysis(oil_quota_bbls=0, oil_actual_bbls=100)
        assert a.oil_variance_pct == 0

    def test_compliance_ratio(self):
        a = _make_analysis(oil_quota_bbls=100000, oil_actual_bbls=95000)
        assert a.oil_compliance_ratio == pytest.approx(0.95)

    def test_zero_quota_compliance_ratio(self):
        a = _make_analysis(gas_quota_mcf=0, gas_actual_mcf=100)
        assert a.gas_compliance_ratio == 0


class TestQuotaVarianceAnalysisMethods:
    def test_is_oil_over_quota_true(self):
        a = _make_analysis(oil_quota_bbls=100000, oil_actual_bbls=110000)
        assert a.is_oil_over_quota() is True

    def test_is_oil_over_quota_false(self):
        a = _make_analysis(oil_quota_bbls=100000, oil_actual_bbls=90000)
        assert a.is_oil_over_quota() is False

    def test_is_gas_over_quota_true(self):
        a = _make_analysis(gas_quota_mcf=500000, gas_actual_mcf=600000)
        assert a.is_gas_over_quota() is True

    def test_is_any_quota_exceeded(self):
        a = _make_analysis(oil_actual_bbls=110000)
        assert a.is_any_quota_exceeded() is True

    def test_none_exceeded(self):
        a = _make_analysis(oil_actual_bbls=90000, gas_actual_mcf=400000)
        assert a.is_any_quota_exceeded() is False


class TestGetVarianceStatus:
    def test_over_quota(self):
        a = _make_analysis(oil_actual_bbls=110000, gas_actual_mcf=600000)
        status = a.get_variance_status()
        assert status["oil_status"] == "Over"
        assert status["gas_status"] == "Over"
        assert status["overall_status"] == "Over Quota"

    def test_under_quota(self):
        a = _make_analysis(oil_actual_bbls=90000, gas_actual_mcf=400000)
        status = a.get_variance_status()
        assert status["oil_status"] == "Under"
        assert status["gas_status"] == "Under"
        assert status["overall_status"] == "Within Limits"

    def test_on_target(self):
        a = _make_analysis(oil_actual_bbls=100000, gas_actual_mcf=500000)
        status = a.get_variance_status()
        assert status["oil_status"] == "On Target"
        assert status["gas_status"] == "On Target"


class TestCalculatePenaltyExposure:
    def test_over_quota_penalty(self):
        a = _make_analysis(oil_actual_bbls=110000, gas_actual_mcf=600000)
        penalties = a.calculate_penalty_exposure(
            oil_penalty_rate=25.0, gas_penalty_rate=5.0
        )
        assert penalties["oil_penalty_usd"] == 10000 * 25.0
        assert penalties["gas_penalty_usd"] == 100000 * 5.0
        assert penalties["total_penalty_usd"] == 250000 + 500000

    def test_under_quota_no_penalty(self):
        a = _make_analysis(oil_actual_bbls=90000, gas_actual_mcf=400000)
        penalties = a.calculate_penalty_exposure()
        assert penalties["oil_penalty_usd"] == 0
        assert penalties["gas_penalty_usd"] == 0
        assert penalties["total_penalty_usd"] == 0


class TestCalculateOpportunityCost:
    def test_under_quota_opportunity(self):
        a = _make_analysis(oil_actual_bbls=90000, gas_actual_mcf=400000)
        costs = a.calculate_opportunity_cost(oil_price_usd=75.0, gas_price_usd=4.0)
        assert costs["oil_opportunity_cost_usd"] == 10000 * 75.0
        assert costs["gas_opportunity_cost_usd"] == 100000 * 4.0

    def test_over_quota_no_opportunity(self):
        a = _make_analysis(oil_actual_bbls=110000, gas_actual_mcf=600000)
        costs = a.calculate_opportunity_cost()
        assert costs["oil_opportunity_cost_usd"] == 0
        assert costs["gas_opportunity_cost_usd"] == 0


class TestGetSummaryMetrics:
    def test_summary_fields(self):
        a = _make_analysis()
        summary = a.get_summary_metrics()
        assert "oil_compliance_pct" in summary
        assert "gas_compliance_pct" in summary
        assert "days_in_period" in summary
        assert summary["days_in_period"] == 91  # Jan 1 to Mar 31 inclusive


# ---------------------------------------------------------------------------
# ProductionQuotaAnalyzer
# ---------------------------------------------------------------------------


class TestProductionQuotaAnalyzerInit:
    def test_init(self):
        analyzer = ProductionQuotaAnalyzer()
        assert analyzer.quota_analyses == []
        assert "excellent" in analyzer.compliance_thresholds


class TestRateComplianceRatio:
    def test_excellent(self):
        analyzer = ProductionQuotaAnalyzer()
        assert analyzer._rate_compliance_ratio(1.0) == "Excellent"
        assert analyzer._rate_compliance_ratio(0.95) == "Excellent"
        assert analyzer._rate_compliance_ratio(1.05) == "Excellent"

    def test_good(self):
        analyzer = ProductionQuotaAnalyzer()
        assert analyzer._rate_compliance_ratio(0.92) == "Good"
        assert analyzer._rate_compliance_ratio(1.08) == "Good"

    def test_fair(self):
        analyzer = ProductionQuotaAnalyzer()
        assert analyzer._rate_compliance_ratio(0.86) == "Fair"
        assert analyzer._rate_compliance_ratio(1.14) == "Fair"

    def test_poor(self):
        analyzer = ProductionQuotaAnalyzer()
        assert analyzer._rate_compliance_ratio(0.80) == "Poor"
        assert analyzer._rate_compliance_ratio(1.20) == "Poor"


class TestGenerateComplianceRating:
    def test_excellent_rating(self):
        analyzer = ProductionQuotaAnalyzer()
        a = _make_analysis(oil_actual_bbls=100000, gas_actual_mcf=500000)
        rating = analyzer.generate_compliance_rating(a)
        assert rating["oil_rating"] == "Excellent"
        assert rating["gas_rating"] == "Excellent"
        assert rating["overall_rating"] == "Excellent"

    def test_mixed_rating_uses_worst(self):
        analyzer = ProductionQuotaAnalyzer()
        a = _make_analysis(oil_actual_bbls=100000, gas_actual_mcf=400000)
        rating = analyzer.generate_compliance_rating(a)
        assert rating["oil_rating"] == "Excellent"
        assert rating["gas_rating"] == "Poor"  # 0.8 ratio
        assert rating["overall_rating"] == "Poor"


class TestCalculateComplianceTrend:
    def test_empty(self):
        analyzer = ProductionQuotaAnalyzer()
        result = analyzer.calculate_compliance_trend([])
        assert result["trend"] == "No Data"

    def test_single_period(self):
        analyzer = ProductionQuotaAnalyzer()
        a = _make_analysis()
        result = analyzer.calculate_compliance_trend([a])
        assert result["periods_analyzed"] == 1

    def test_improving_trend(self):
        analyzer = ProductionQuotaAnalyzer()
        analyses = [
            _make_analysis(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 3, 31),
                oil_actual_bbls=80000,
                gas_actual_mcf=400000,
            ),
            _make_analysis(
                period_start=date(2024, 4, 1),
                period_end=date(2024, 6, 30),
                oil_actual_bbls=95000,
                gas_actual_mcf=490000,
            ),
            _make_analysis(
                period_start=date(2024, 7, 1),
                period_end=date(2024, 9, 30),
                oil_actual_bbls=100000,
                gas_actual_mcf=500000,
            ),
        ]
        result = analyzer.calculate_compliance_trend(analyses)
        assert result["overall_trend"] == "Improving"


class TestCalculateTrendMethod:
    def test_single_value(self):
        analyzer = ProductionQuotaAnalyzer()
        assert analyzer._calculate_trend([0], [1.0]) == 0.0

    def test_positive_slope(self):
        analyzer = ProductionQuotaAnalyzer()
        slope = analyzer._calculate_trend([0, 1, 2], [1.0, 2.0, 3.0])
        assert slope == pytest.approx(1.0)


class TestGenerateComplianceRecommendation:
    def test_excellent(self):
        analyzer = ProductionQuotaAnalyzer()
        rec = analyzer._generate_compliance_recommendation(97, 97, 19, 20)
        assert "Excellent" in rec

    def test_good(self):
        analyzer = ProductionQuotaAnalyzer()
        rec = analyzer._generate_compliance_recommendation(90, 90, 17, 20)
        assert "Good" in rec

    def test_fair(self):
        analyzer = ProductionQuotaAnalyzer()
        rec = analyzer._generate_compliance_recommendation(85, 85, 14, 20)
        assert "Fair" in rec

    def test_poor(self):
        analyzer = ProductionQuotaAnalyzer()
        rec = analyzer._generate_compliance_recommendation(70, 70, 10, 20)
        assert "Poor" in rec


class TestCreateQuotaDashboardData:
    def test_empty(self):
        analyzer = ProductionQuotaAnalyzer()
        result = analyzer.create_quota_dashboard_data([])
        assert "error" in result

    def test_with_data(self):
        analyzer = ProductionQuotaAnalyzer()
        analyses = [_make_analysis()]
        result = analyzer.create_quota_dashboard_data(analyses)
        assert "current_period" in result
        assert "trends" in result
        assert "historical_performance" in result
        assert "risk_metrics" in result


class TestExportQuotaAnalysisReport:
    def test_empty(self):
        analyzer = ProductionQuotaAnalyzer()
        result = analyzer.export_quota_analysis_report([])
        assert "error" in result

    def test_with_data(self):
        analyzer = ProductionQuotaAnalyzer()
        analyses = [_make_analysis()]
        result = analyzer.export_quota_analysis_report(analyses)
        assert "report_metadata" in result
        assert "executive_summary" in result
        assert "detailed_analysis" in result
        assert len(result["detailed_analysis"]) == 1
