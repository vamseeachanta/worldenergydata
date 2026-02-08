"""
Well-level economic analysis utilities
Contains NPV, ROI, EUR, and investment grade calculations for individual wells
"""

from typing import Any, Dict, List

import numpy_financial as npf


def determine_well_investment_grade(
    npv_12: float, irr: float, payback_years: float
) -> str:
    """Determine investment grade for individual well"""
    # Excellent: High NPV, High IRR, Quick Payback
    if npv_12 > 5000000 and irr > 0.25 and payback_years < 3:
        return "Excellent"
    # Good: Positive NPV, Good IRR, Reasonable Payback
    elif npv_12 > 2000000 and irr > 0.15 and payback_years < 5:
        return "Good"
    # Acceptable: Positive NPV, Meets hurdle rates
    elif npv_12 > 0 and irr > 0.12 and payback_years < 8:
        return "Acceptable"
    # Marginal: Barely profitable
    elif npv_12 > -1000000 and irr > 0.08 and payback_years < 10:
        return "Marginal"
    # Poor: Not profitable
    else:
        return "Poor"


def analyze_individual_well_economics(
    well_id: str,
    well_context: Dict[str, Any],
    initial_well_cost: float = 8000000.0,
    well_life_years: int = 20,
    decline_rate: float = 0.08,
) -> Dict[str, Any]:
    """Analyze individual well economics with NPV and ROI metrics"""
    # Get first-year economics
    first_year_net_income = well_context["goby_economic_summary"]["net_income"]

    # Generate cash flow projections with decline
    cash_flows = [-initial_well_cost]  # Initial investment
    for year in range(1, well_life_years + 1):
        year_factor = (1 - decline_rate) ** (year - 1)
        cash_flows.append(first_year_net_income * year_factor)

    # Calculate NPV and IRR
    npv_10 = npf.npv(0.10, cash_flows)
    npv_12 = npf.npv(0.12, cash_flows)
    npv_15 = npf.npv(0.15, cash_flows)

    try:
        irr = npf.irr(cash_flows)
    except:
        irr = 0.0

    # Calculate payback period
    cumulative_cash = -initial_well_cost
    payback_years = well_life_years
    for year, cash_flow in enumerate(cash_flows[1:], 1):
        cumulative_cash += cash_flow
        if cumulative_cash >= 0:
            prev_cumulative = cumulative_cash - cash_flow
            payback_years = year - 1 + abs(prev_cumulative) / cash_flow
            break

    # Calculate ROI metrics
    total_cash_flows = sum(cash_flows[1:])
    total_roi = (total_cash_flows - initial_well_cost) / initial_well_cost
    annual_roi = total_roi / well_life_years

    # Calculate EUR (Estimated Ultimate Recovery)
    first_year_oil = well_context["production_metrics"]["oil_bbls"]
    first_year_gas = well_context["production_metrics"]["gas_mcf"]

    eur_oil = sum(
        [
            first_year_oil * ((1 - decline_rate) ** (year - 1))
            for year in range(1, well_life_years + 1)
        ]
    )
    eur_gas = sum(
        [
            first_year_gas * ((1 - decline_rate) ** (year - 1))
            for year in range(1, well_life_years + 1)
        ]
    )
    eur_boe = eur_oil + (eur_gas / 6)

    # Well-level efficiency metrics
    finding_cost_per_boe = initial_well_cost / eur_boe if eur_boe > 0 else 0
    revenue_per_investment = (
        total_cash_flows / initial_well_cost if initial_well_cost > 0 else 0
    )

    # Daily BOE calculation
    daily_boe = well_context["production_metrics"]["oil_bbls"] / 365 + well_context[
        "production_metrics"
    ]["gas_mcf"] / (365 * 6)

    return {
        "well_identification": {
            "well_id": well_id,
            "entity_id": well_context["production_metrics"].get("entity_id", "unknown"),
            "analysis_assumptions": {
                "initial_well_cost": initial_well_cost,
                "well_life_years": well_life_years,
                "decline_rate": decline_rate,
            },
        },
        "npv_analysis": {
            "npv_10_percent": npv_10,
            "npv_12_percent": npv_12,
            "npv_15_percent": npv_15,
            "irr": irr,
            "cash_flows": cash_flows,
        },
        "roi_metrics": {
            "total_roi": total_roi,
            "annual_roi": annual_roi,
            "payback_period_years": payback_years,
            "revenue_per_investment_dollar": revenue_per_investment,
        },
        "production_forecast": {
            "eur_oil_bbls": eur_oil,
            "eur_gas_mcf": eur_gas,
            "eur_boe": eur_boe,
            "first_year_oil": first_year_oil,
            "first_year_gas": first_year_gas,
        },
        "cost_efficiency": {
            "finding_cost_per_boe": finding_cost_per_boe,
            "initial_cost_per_daily_boe": (
                initial_well_cost / daily_boe if daily_boe > 0 else 0
            ),
        },
        "profitability_assessment": {
            "is_profitable_10_percent": npv_10 > 0,
            "is_profitable_12_percent": npv_12 > 0,
            "is_profitable_15_percent": npv_15 > 0,
            "irr_exceeds_10_percent": irr > 0.10 if irr else False,
            "payback_under_5_years": payback_years < 5,
            "investment_grade": determine_well_investment_grade(
                npv_12, irr, payback_years
            ),
        },
        "first_year_metrics": well_context["goby_economic_summary"],
    }


def compare_wells_economic_performance(
    wells_data: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Compare economic performance across multiple wells"""
    well_comparisons = []
    for well_id, well_economics in wells_data.items():
        well_comparisons.append(
            {
                "well_id": well_id,
                "npv_12_percent": well_economics["npv_analysis"]["npv_12_percent"],
                "irr": well_economics["npv_analysis"]["irr"],
                "payback_years": well_economics["roi_metrics"]["payback_period_years"],
                "eur_boe": well_economics["production_forecast"]["eur_boe"],
                "finding_cost_per_boe": well_economics["cost_efficiency"][
                    "finding_cost_per_boe"
                ],
                "investment_grade": well_economics["profitability_assessment"][
                    "investment_grade"
                ],
                "first_year_netback": well_economics["first_year_metrics"][
                    "netback_per_boe"
                ],
            }
        )

    # Sort by NPV (descending)
    well_comparisons.sort(key=lambda x: x["npv_12_percent"], reverse=True)

    # Calculate portfolio statistics
    npvs = [w["npv_12_percent"] for w in well_comparisons]
    irrs = [w["irr"] for w in well_comparisons if w["irr"] > 0]
    paybacks = [w["payback_years"] for w in well_comparisons if w["payback_years"] < 20]

    portfolio_stats = {
        "total_wells": len(well_comparisons),
        "average_npv": sum(npvs) / len(npvs) if npvs else 0,
        "median_npv": sorted(npvs)[len(npvs) // 2] if npvs else 0,
        "average_irr": sum(irrs) / len(irrs) if irrs else 0,
        "median_payback": sorted(paybacks)[len(paybacks) // 2] if paybacks else 0,
        "profitable_wells_12_percent": sum(1 for npv in npvs if npv > 0),
        "excellent_grade_wells": sum(
            1 for w in well_comparisons if w["investment_grade"] == "Excellent"
        ),
        "poor_grade_wells": sum(
            1 for w in well_comparisons if w["investment_grade"] == "Poor"
        ),
    }

    top_performers = well_comparisons[:3]
    bottom_performers = well_comparisons[-3:] if len(well_comparisons) > 3 else []

    return {
        "well_rankings": well_comparisons,
        "portfolio_statistics": portfolio_stats,
        "top_performers": top_performers,
        "bottom_performers": bottom_performers,
        "investment_recommendations": generate_well_investment_recommendations(
            portfolio_stats, well_comparisons
        ),
    }


def generate_well_investment_recommendations(
    portfolio_stats: Dict[str, Any], well_comparisons: List[Dict[str, Any]]
) -> List[str]:
    """Generate investment recommendations based on well performance"""
    recommendations = []

    profitable_rate = (
        portfolio_stats["profitable_wells_12_percent"] / portfolio_stats["total_wells"]
    )
    if profitable_rate < 0.6:
        recommendations.append(
            "Portfolio has low profitability rate - review drilling strategy"
        )

    if portfolio_stats["average_npv"] < 1000000:
        recommendations.append(
            "Average well NPV is below $1M - consider higher-return prospects"
        )

    if portfolio_stats["average_irr"] < 0.15:
        recommendations.append(
            "Average IRR below 15% - evaluate cost reduction opportunities"
        )

    excellent_wells = [
        w for w in well_comparisons if w["investment_grade"] == "Excellent"
    ]
    if excellent_wells:
        recommendations.append(
            f"Focus on replicating {len(excellent_wells)} excellent-grade wells"
        )

    poor_wells = [w for w in well_comparisons if w["investment_grade"] == "Poor"]
    if poor_wells:
        recommendations.append(f"Investigate {len(poor_wells)} poor-performing wells")

    if portfolio_stats["median_npv"] > portfolio_stats["average_npv"]:
        recommendations.append(
            "Consider high-grading portfolio - eliminate bottom performers"
        )

    return recommendations
