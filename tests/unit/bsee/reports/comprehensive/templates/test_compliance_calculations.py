"""Tests for compliance calculations."""

from worldenergydata.bsee.reports.comprehensive.templates.compliance_calculations import (
    assess_environmental_risks,
    analyze_environmental_trends,
    calculate_environmental_kpis,
    calculate_performance_percentile,
    calculate_risk_score,
    check_environmental_thresholds,
    compare_to_benchmarks,
    generate_environmental_actions,
    generate_recommendations,
    get_compliance_status_color,
    get_environmental_benchmarks,
    get_environmental_thresholds,
)
from worldenergydata.bsee.reports.comprehensive.templates.compliance_models import (
    EnvironmentalMetrics,
)


class TestGetEnvironmentalThresholds:
    def test_returns_dict(self):
        t = get_environmental_thresholds()
        assert isinstance(t, dict)

    def test_zero_spill_tolerance(self):
        t = get_environmental_thresholds()
        assert t["spill_incidents_monthly"] == 0

    def test_spill_volume_limit(self):
        t = get_environmental_thresholds()
        assert t["spill_volume_monthly_bbls"] == 1.0

    def test_has_all_keys(self):
        t = get_environmental_thresholds()
        expected = {
            "spill_incidents_monthly", "spill_volume_monthly_bbls",
            "air_emissions_annual_tons", "water_discharge_monthly_bbls",
            "waste_monthly_tons", "violation_tolerance",
        }
        assert set(t.keys()) == expected


class TestGetEnvironmentalBenchmarks:
    def test_returns_dict(self):
        b = get_environmental_benchmarks()
        assert isinstance(b, dict)

    def test_has_industry_average(self):
        b = get_environmental_benchmarks()
        assert "industry_average" in b

    def test_has_best_in_class(self):
        b = get_environmental_benchmarks()
        assert "best_in_class" in b

    def test_has_regulatory_minimum(self):
        b = get_environmental_benchmarks()
        assert "regulatory_minimum" in b

    def test_best_in_class_better_than_average(self):
        b = get_environmental_benchmarks()
        assert (
            b["best_in_class"]["environmental_score"]
            > b["industry_average"]["environmental_score"]
        )


class TestCalculatePerformancePercentile:
    def test_excellent_score(self):
        assert calculate_performance_percentile(0.96) == 95

    def test_very_good_score(self):
        assert calculate_performance_percentile(0.91) == 85

    def test_good_score(self):
        assert calculate_performance_percentile(0.86) == 75

    def test_average_score(self):
        assert calculate_performance_percentile(0.81) == 60

    def test_below_average(self):
        assert calculate_performance_percentile(0.76) == 45

    def test_fair_score(self):
        assert calculate_performance_percentile(0.71) == 30

    def test_poor_score(self):
        assert calculate_performance_percentile(0.50) == 15

    def test_boundary_095(self):
        assert calculate_performance_percentile(0.95) == 95

    def test_boundary_090(self):
        assert calculate_performance_percentile(0.90) == 85


class TestCheckEnvironmentalThresholds:
    def test_all_compliant(self):
        m = EnvironmentalMetrics()
        result = check_environmental_thresholds(m)
        assert result["spill_incidents_compliant"] is True
        assert result["spill_volume_compliant"] is True
        assert result["air_emissions_compliant"] is True
        assert result["water_discharge_compliant"] is True
        assert result["waste_compliant"] is True
        assert result["violations_compliant"] is True
        assert result["overall_threshold_compliance"] == 100.0

    def test_spill_non_compliant(self):
        m = EnvironmentalMetrics(spill_incidents=5, total_spill_volume_bbls=10.0)
        result = check_environmental_thresholds(m)
        assert result["spill_incidents_compliant"] is False
        assert result["spill_volume_compliant"] is False
        assert result["overall_threshold_compliance"] < 100.0

    def test_emissions_non_compliant(self):
        m = EnvironmentalMetrics(air_emissions_tons=200.0)
        result = check_environmental_thresholds(m)
        assert result["air_emissions_compliant"] is False

    def test_violations_non_compliant(self):
        m = EnvironmentalMetrics(environmental_violations=3)
        result = check_environmental_thresholds(m)
        assert result["violations_compliant"] is False


class TestCompareToBenchmarks:
    def test_excellent_performer(self):
        m = EnvironmentalMetrics()  # Score 1.0, all clean
        result = compare_to_benchmarks(m)
        assert result["vs_industry_average"] == "Above"
        assert result["vs_best_in_class"] == "Above"
        assert result["vs_regulatory_minimum"] == "Above"
        assert result["performance_percentile"] == 95
        assert result["improvement_potential"] == 0

    def test_poor_performer(self):
        m = EnvironmentalMetrics(
            spill_incidents=5,
            total_spill_volume_bbls=50.0,
            environmental_violations=5,
            air_emissions_tons=300.0,
        )
        result = compare_to_benchmarks(m)
        assert result["vs_best_in_class"] == "Below"


class TestCalculateRiskScore:
    def test_zero_risk(self):
        m = EnvironmentalMetrics()
        assert calculate_risk_score(m) == 0.0

    def test_spill_risk(self):
        m = EnvironmentalMetrics(spill_incidents=2, total_spill_volume_bbls=20.0)
        score = calculate_risk_score(m)
        assert 0 < score <= 1.0

    def test_emissions_risk(self):
        m = EnvironmentalMetrics(air_emissions_tons=200.0)
        score = calculate_risk_score(m)
        assert score > 0

    def test_violation_risk(self):
        m = EnvironmentalMetrics(environmental_violations=3)
        score = calculate_risk_score(m)
        assert score > 0

    def test_max_capped_at_1(self):
        m = EnvironmentalMetrics(
            spill_incidents=10,
            total_spill_volume_bbls=100.0,
            air_emissions_tons=500.0,
            environmental_violations=10,
        )
        assert calculate_risk_score(m) <= 1.0


class TestAssessEnvironmentalRisks:
    def test_low_risk(self):
        m = EnvironmentalMetrics()
        result = assess_environmental_risks(m)
        assert result["overall_risk_level"] == "Low"
        assert result["risk_factors"] == []
        assert result["mitigation_priority"] == "Routine"

    def test_high_risk_spills(self):
        m = EnvironmentalMetrics(spill_incidents=5, total_spill_volume_bbls=30.0)
        result = assess_environmental_risks(m)
        assert result["overall_risk_level"] == "High"
        assert len(result["risk_factors"]) >= 1
        assert result["mitigation_priority"] == "Immediate"

    def test_medium_risk_some_incidents(self):
        m = EnvironmentalMetrics(spill_incidents=1)
        result = assess_environmental_risks(m)
        assert result["overall_risk_level"] == "Medium"
        assert result["mitigation_priority"] == "Planned"

    def test_high_risk_emissions(self):
        m = EnvironmentalMetrics(air_emissions_tons=250.0)
        result = assess_environmental_risks(m)
        assert result["overall_risk_level"] == "High"

    def test_high_risk_violations(self):
        m = EnvironmentalMetrics(environmental_violations=5)
        result = assess_environmental_risks(m)
        assert result["overall_risk_level"] == "High"

    def test_medium_risk_elevated_emissions(self):
        m = EnvironmentalMetrics(air_emissions_tons=150.0)
        result = assess_environmental_risks(m)
        assert result["overall_risk_level"] == "Medium"

    def test_medium_risk_moderate_volume(self):
        m = EnvironmentalMetrics(total_spill_volume_bbls=10.0)
        result = assess_environmental_risks(m)
        assert result["overall_risk_level"] == "Medium"


class TestAnalyzeEnvironmentalTrends:
    def test_excellent(self):
        m = EnvironmentalMetrics()  # Score 1.0
        result = analyze_environmental_trends(m)
        assert result["spill_trend"] == "stable_good"
        assert result["compliance_trend"] == "maintaining_excellence"

    def test_good(self):
        m = EnvironmentalMetrics(spill_incidents=1)
        result = analyze_environmental_trends(m)
        assert "trend_analysis" in result
        assert "leading_indicators" in result

    def test_poor(self):
        m = EnvironmentalMetrics(
            spill_incidents=5, environmental_violations=5,
            air_emissions_tons=500.0,
        )
        result = analyze_environmental_trends(m)
        assert result["compliance_trend"] == "requires_immediate_action"


class TestGenerateEnvironmentalActions:
    def test_no_actions_excellent(self):
        m = EnvironmentalMetrics()
        actions = generate_environmental_actions(m)
        assert len(actions) == 1
        assert actions[0]["priority"] == "Low"
        assert actions[0]["category"] == "Continuous Improvement"

    def test_spill_actions(self):
        m = EnvironmentalMetrics(spill_incidents=1)
        actions = generate_environmental_actions(m)
        assert any(a["category"] == "Spill Prevention" for a in actions)

    def test_high_spill_priority(self):
        m = EnvironmentalMetrics(spill_incidents=5)
        actions = generate_environmental_actions(m)
        spill_action = [a for a in actions if a["category"] == "Spill Prevention"][0]
        assert spill_action["priority"] == "High"

    def test_large_spill_volume_action(self):
        m = EnvironmentalMetrics(total_spill_volume_bbls=20.0)
        actions = generate_environmental_actions(m)
        assert any(a["category"] == "Spill Response" for a in actions)

    def test_emissions_action(self):
        m = EnvironmentalMetrics(air_emissions_tons=200.0)
        actions = generate_environmental_actions(m)
        assert any(a["category"] == "Emissions Control" for a in actions)

    def test_violation_action(self):
        m = EnvironmentalMetrics(environmental_violations=2)
        actions = generate_environmental_actions(m)
        assert any(a["category"] == "Regulatory Compliance" for a in actions)


class TestCalculateEnvironmentalKPIs:
    def test_clean_metrics(self):
        m = EnvironmentalMetrics()
        kpis = calculate_environmental_kpis(m)
        assert kpis["primary_kpis"]["environmental_score"] == 1.0
        assert kpis["primary_kpis"]["spill_frequency"] == 0
        assert kpis["calculated_kpis"]["spill_rate_per_incident"] == 0
        assert kpis["calculated_kpis"]["regulatory_compliance_rate"] == 100

    def test_with_incidents(self):
        m = EnvironmentalMetrics(
            spill_incidents=2, total_spill_volume_bbls=10.0,
            environmental_violations=1,
        )
        kpis = calculate_environmental_kpis(m)
        assert kpis["primary_kpis"]["spill_frequency"] == 2
        assert kpis["calculated_kpis"]["spill_rate_per_incident"] == 5.0
        assert kpis["calculated_kpis"]["regulatory_compliance_rate"] == 75

    def test_has_performance_targets(self):
        m = EnvironmentalMetrics()
        kpis = calculate_environmental_kpis(m)
        targets = kpis["performance_targets"]
        assert targets["target_environmental_score"] == 0.90
        assert targets["target_spill_incidents"] == 0


class TestGetComplianceStatusColor:
    def test_green(self):
        assert get_compliance_status_color(0.95) == "#4CAF50"

    def test_orange(self):
        assert get_compliance_status_color(0.85) == "#FF9800"

    def test_yellow(self):
        assert get_compliance_status_color(0.75) == "#FFC107"

    def test_red(self):
        assert get_compliance_status_color(0.60) == "#F44336"


class TestGenerateRecommendations:
    def test_all_good(self):
        summary = {"production_compliance": 100, "environmental_score": 1.0, "safety_score": 1.0}
        recs = generate_recommendations(summary)
        assert len(recs) == 1
        assert "Continue" in recs[0]

    def test_low_production_compliance(self):
        summary = {"production_compliance": 90}
        recs = generate_recommendations(summary)
        assert any("production" in r.lower() for r in recs)

    def test_low_environmental_score(self):
        summary = {"environmental_score": 0.7}
        recs = generate_recommendations(summary)
        assert any("environmental" in r.lower() for r in recs)

    def test_low_safety_score(self):
        summary = {"safety_score": 0.7}
        recs = generate_recommendations(summary)
        assert any("safety" in r.lower() for r in recs)

    def test_violations(self):
        summary = {"regulatory_violations": 3}
        recs = generate_recommendations(summary)
        assert any("violation" in r.lower() for r in recs)

    def test_multiple_issues(self):
        summary = {
            "production_compliance": 80,
            "environmental_score": 0.6,
            "safety_score": 0.5,
            "regulatory_violations": 5,
        }
        recs = generate_recommendations(summary)
        assert len(recs) == 4
