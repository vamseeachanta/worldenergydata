"""
Compliance Calculations for regulatory compliance analysis.

This module contains calculation functions for environmental thresholds,
benchmarks, risk assessment, trend analysis, corrective actions, and KPIs.
"""

from typing import Any, Dict, List

from .compliance_models import EnvironmentalMetrics


def get_environmental_thresholds() -> Dict[str, Any]:
    """Get regulatory environmental thresholds"""
    return {
        "spill_incidents_monthly": 0,  # Zero tolerance for spills
        "spill_volume_monthly_bbls": 1.0,  # Maximum 1 barrel per month
        "air_emissions_annual_tons": 100.0,  # Annual air emissions limit
        "water_discharge_monthly_bbls": 50000,  # Monthly water discharge limit
        "waste_monthly_tons": 25.0,  # Monthly waste generation limit
        "violation_tolerance": 0,  # Zero tolerance for violations
    }


def check_environmental_thresholds(metrics: EnvironmentalMetrics) -> Dict[str, Any]:
    """Check environmental metrics against regulatory thresholds"""
    thresholds = get_environmental_thresholds()

    compliance_checks = {
        "spill_incidents_compliant": metrics.spill_incidents
        <= thresholds["spill_incidents_monthly"],
        "spill_volume_compliant": metrics.total_spill_volume_bbls
        <= thresholds["spill_volume_monthly_bbls"],
        "air_emissions_compliant": metrics.air_emissions_tons
        <= thresholds["air_emissions_annual_tons"],
        "water_discharge_compliant": metrics.water_discharge_bbls
        <= thresholds["water_discharge_monthly_bbls"],
        "waste_compliant": metrics.waste_generated_tons
        <= thresholds["waste_monthly_tons"],
        "violations_compliant": metrics.environmental_violations
        <= thresholds["violation_tolerance"],
    }

    # Calculate overall threshold compliance
    compliant_count = sum(compliance_checks.values())
    total_checks = len(compliance_checks)
    compliance_checks["overall_threshold_compliance"] = (
        compliant_count / total_checks
    ) * 100

    return compliance_checks


def get_environmental_benchmarks() -> Dict[str, Any]:
    """Get industry environmental performance benchmarks"""
    return {
        "industry_average": {
            "spill_incidents_per_month": 0.5,
            "spill_volume_per_1000bbls": 0.01,
            "emissions_per_1000bbls": 0.8,
            "environmental_score": 0.85,
        },
        "best_in_class": {
            "spill_incidents_per_month": 0.1,
            "spill_volume_per_1000bbls": 0.001,
            "emissions_per_1000bbls": 0.5,
            "environmental_score": 0.95,
        },
        "regulatory_minimum": {
            "environmental_score": 0.70,
            "max_violations_per_year": 2,
        },
    }


def calculate_performance_percentile(score: float) -> int:
    """Calculate performance percentile based on environmental score"""
    if score >= 0.95:
        return 95
    elif score >= 0.90:
        return 85
    elif score >= 0.85:
        return 75
    elif score >= 0.80:
        return 60
    elif score >= 0.75:
        return 45
    elif score >= 0.70:
        return 30
    else:
        return 15


def compare_to_benchmarks(metrics: EnvironmentalMetrics) -> Dict[str, Any]:
    """Compare environmental performance to industry benchmarks"""
    benchmarks = get_environmental_benchmarks()
    env_score = metrics.calculate_environmental_score()

    comparison = {
        "vs_industry_average": (
            "Above"
            if env_score > benchmarks["industry_average"]["environmental_score"]
            else "Below"
        ),
        "vs_best_in_class": (
            "Above"
            if env_score > benchmarks["best_in_class"]["environmental_score"]
            else "Below"
        ),
        "vs_regulatory_minimum": (
            "Above"
            if env_score > benchmarks["regulatory_minimum"]["environmental_score"]
            else "Below"
        ),
        "performance_percentile": calculate_performance_percentile(env_score),
        "improvement_potential": max(
            0, benchmarks["best_in_class"]["environmental_score"] - env_score
        ),
    }

    return comparison


def calculate_risk_score(metrics: EnvironmentalMetrics) -> float:
    """Calculate numerical environmental risk score (0-1, where 1 is highest risk)"""
    risk_score = 0.0

    # Spill risk component (max 0.3)
    risk_score += min(0.3, metrics.spill_incidents * 0.1)
    risk_score += min(0.2, metrics.total_spill_volume_bbls * 0.005)

    # Emissions risk component (max 0.3)
    if metrics.air_emissions_tons > 100:
        risk_score += min(0.3, (metrics.air_emissions_tons - 100) * 0.001)

    # Violation risk component (max 0.4)
    risk_score += min(0.4, metrics.environmental_violations * 0.15)

    return min(1.0, risk_score)


def assess_environmental_risks(metrics: EnvironmentalMetrics) -> Dict[str, Any]:
    """Assess environmental risks based on metrics"""
    risk_factors = []
    risk_level = "Low"

    # Assess spill risk
    if metrics.spill_incidents > 2:
        risk_factors.append("High spill frequency")
        risk_level = "High"
    elif metrics.spill_incidents > 0:
        risk_factors.append("Spill incidents present")
        if risk_level == "Low":
            risk_level = "Medium"

    # Assess volume risk
    if metrics.total_spill_volume_bbls > 25:
        risk_factors.append("Large spill volumes")
        risk_level = "High"
    elif metrics.total_spill_volume_bbls > 5:
        risk_factors.append("Moderate spill volumes")
        if risk_level == "Low":
            risk_level = "Medium"

    # Assess emissions risk
    if metrics.air_emissions_tons > 200:
        risk_factors.append("High air emissions")
        risk_level = "High"
    elif metrics.air_emissions_tons > 100:
        risk_factors.append("Elevated air emissions")
        if risk_level == "Low":
            risk_level = "Medium"

    # Assess violation risk
    if metrics.environmental_violations > 2:
        risk_factors.append("Multiple regulatory violations")
        risk_level = "High"
    elif metrics.environmental_violations > 0:
        risk_factors.append("Regulatory violations present")
        if risk_level == "Low":
            risk_level = "Medium"

    return {
        "overall_risk_level": risk_level,
        "risk_factors": risk_factors,
        "risk_score": calculate_risk_score(metrics),
        "mitigation_priority": (
            "Immediate"
            if risk_level == "High"
            else "Planned" if risk_level == "Medium" else "Routine"
        ),
    }


def analyze_environmental_trends(metrics: EnvironmentalMetrics) -> Dict[str, Any]:
    """Analyze environmental trends (enhanced from placeholder)"""
    # In a real implementation, this would analyze historical data
    # For now, provide structured trend analysis based on current metrics

    env_score = metrics.calculate_environmental_score()

    # Determine trends based on current performance level
    if env_score >= 0.9:
        spill_trend = "stable_good"
        emissions_trend = "stable_good"
        compliance_trend = "maintaining_excellence"
    elif env_score >= 0.8:
        spill_trend = "stable"
        emissions_trend = "stable"
        compliance_trend = "good"
    elif env_score >= 0.7:
        spill_trend = "concerning"
        emissions_trend = "concerning"
        compliance_trend = "needs_improvement"
    else:
        spill_trend = "poor"
        emissions_trend = "poor"
        compliance_trend = "requires_immediate_action"

    return {
        "spill_trend": spill_trend,
        "emissions_trend": emissions_trend,
        "compliance_trend": compliance_trend,
        "trend_analysis": {
            "current_score": env_score,
            "trend_direction": "stable",  # Placeholder - would calculate from historical data
            "forecast": (
                "Monitor closely" if env_score < 0.8 else "Continue current practices"
            ),
        },
        "leading_indicators": {
            "spill_frequency": metrics.spill_incidents,
            "violation_frequency": metrics.environmental_violations,
            "emissions_intensity": metrics.air_emissions_tons,
        },
    }


def generate_environmental_actions(
    metrics: EnvironmentalMetrics,
) -> List[Dict[str, Any]]:
    """Generate corrective actions and recommendations"""
    actions = []

    # Spill-related actions
    if metrics.spill_incidents > 0:
        actions.append(
            {
                "priority": "High" if metrics.spill_incidents > 2 else "Medium",
                "category": "Spill Prevention",
                "action": "Review and enhance spill prevention protocols",
                "timeline": "30 days",
                "responsible_party": "Environmental Manager",
                "regulatory_reference": "30 CFR 254.47",
            }
        )

    if metrics.total_spill_volume_bbls > 10:
        actions.append(
            {
                "priority": "High",
                "category": "Spill Response",
                "action": "Conduct spill response drill and equipment inspection",
                "timeline": "14 days",
                "responsible_party": "Operations Manager",
                "regulatory_reference": "30 CFR 254.50",
            }
        )

    # Emissions-related actions
    if metrics.air_emissions_tons > 150:
        actions.append(
            {
                "priority": "Medium",
                "category": "Emissions Control",
                "action": "Review air emissions control systems and optimize operations",
                "timeline": "60 days",
                "responsible_party": "Environmental Engineer",
                "regulatory_reference": "40 CFR 60",
            }
        )

    # Violation-related actions
    if metrics.environmental_violations > 0:
        actions.append(
            {
                "priority": "Critical",
                "category": "Regulatory Compliance",
                "action": "Submit violation remediation plan to regulatory authority",
                "timeline": "7 days",
                "responsible_party": "Compliance Officer",
                "regulatory_reference": "30 CFR 250.300",
            }
        )

    # Preventive actions for good performers
    if metrics.calculate_environmental_score() > 0.9 and not actions:
        actions.append(
            {
                "priority": "Low",
                "category": "Continuous Improvement",
                "action": "Continue monitoring and maintain current environmental practices",
                "timeline": "Ongoing",
                "responsible_party": "Environmental Team",
                "regulatory_reference": "Best Practices",
            }
        )

    return actions


def calculate_environmental_kpis(metrics: EnvironmentalMetrics) -> Dict[str, Any]:
    """Calculate environmental Key Performance Indicators"""
    return {
        "primary_kpis": {
            "environmental_score": metrics.calculate_environmental_score(),
            "spill_frequency": metrics.spill_incidents,
            "total_spill_volume": metrics.total_spill_volume_bbls,
            "violation_count": metrics.environmental_violations,
        },
        "secondary_kpis": {
            "air_emissions_tons": metrics.air_emissions_tons,
            "water_discharge_bbls": metrics.water_discharge_bbls,
            "waste_generated_tons": metrics.waste_generated_tons,
        },
        "calculated_kpis": {
            "spill_rate_per_incident": (
                metrics.total_spill_volume_bbls / metrics.spill_incidents
                if metrics.spill_incidents > 0
                else 0
            ),
            "environmental_efficiency": metrics.calculate_environmental_score() * 100,
            "regulatory_compliance_rate": (
                100
                if metrics.environmental_violations == 0
                else max(0, 100 - (metrics.environmental_violations * 25))
            ),
        },
        "performance_targets": {
            "target_environmental_score": 0.90,
            "target_spill_incidents": 0,
            "target_violations": 0,
            "target_emissions_reduction_pct": 5.0,
        },
    }


def get_compliance_status_color(score: float) -> str:
    """Get color code for compliance status"""
    if score >= 0.9:
        return "#4CAF50"  # Green
    elif score >= 0.8:
        return "#FF9800"  # Orange
    elif score >= 0.7:
        return "#FFC107"  # Yellow
    else:
        return "#F44336"  # Red


def generate_recommendations(summary: Dict[str, Any]) -> List[str]:
    """Generate compliance recommendations"""
    recommendations = []

    # Production compliance recommendations
    prod_compliance = summary.get("production_compliance", 100)
    if prod_compliance < 95:
        recommendations.append(
            "Review production practices to ensure compliance with permitted levels"
        )

    # Environmental recommendations
    env_score = summary.get("environmental_score", 1.0)
    if env_score < 0.9:
        recommendations.append(
            "Implement enhanced environmental monitoring and spill prevention measures"
        )

    # Safety recommendations
    safety_score = summary.get("safety_score", 1.0)
    if safety_score < 0.9:
        recommendations.append(
            "Increase safety training and incident prevention protocols"
        )

    # Violations recommendations
    violations = summary.get("regulatory_violations", 0)
    if violations > 0:
        recommendations.append(
            "Address outstanding regulatory violations and implement corrective actions"
        )

    if not recommendations:
        recommendations.append(
            "Continue current compliance practices and maintain monitoring protocols"
        )

    return recommendations


# Public API
__all__ = [
    "get_environmental_thresholds",
    "check_environmental_thresholds",
    "get_environmental_benchmarks",
    "calculate_performance_percentile",
    "compare_to_benchmarks",
    "calculate_risk_score",
    "assess_environmental_risks",
    "analyze_environmental_trends",
    "generate_environmental_actions",
    "calculate_environmental_kpis",
    "get_compliance_status_color",
    "generate_recommendations",
]
