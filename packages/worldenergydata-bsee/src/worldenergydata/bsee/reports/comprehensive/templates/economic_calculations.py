"""
Economic calculation utilities for comprehensive financial analysis
Contains netback analysis, cost structure analysis, revenue optimization, and KPIs
"""

from typing import Any, Dict, List

# Re-export well analysis functions for backward compatibility


def calculate_enhanced_netback_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate enhanced netback analysis with detailed cost breakdown"""
    revenue_breakdown = context.get("revenue_breakdown", {})
    cost_analysis = context.get("cost_analysis", {})
    production_metrics = context.get("production_metrics", {})

    # Calculate BOE for per-unit calculations
    oil_bbls = production_metrics.get("oil_bbls", 0)
    gas_mcf = production_metrics.get("gas_mcf", 0)
    total_boe = oil_bbls + (gas_mcf / 6) if oil_bbls or gas_mcf else 1

    # Revenue components per BOE
    revenue_per_boe_breakdown = {
        "oil_revenue_per_boe": revenue_breakdown.get("oil_revenue", 0) / total_boe,
        "gas_revenue_per_boe": revenue_breakdown.get("gas_revenue", 0) / total_boe,
        "ngl_revenue_per_boe": revenue_breakdown.get("ngl_revenue", 0) / total_boe,
        "total_revenue_per_boe": revenue_breakdown.get("total_revenue", 0) / total_boe,
    }

    # Cost components per BOE
    cost_per_boe_breakdown = {
        "operating_cost_per_boe": cost_analysis.get("operating_costs", 0) / total_boe,
        "royalties_per_boe": cost_analysis.get("royalties", 0) / total_boe,
        "severance_tax_per_boe": cost_analysis.get("severance_tax", 0) / total_boe,
        "transportation_cost_per_boe": cost_analysis.get("transportation_costs", 0)
        / total_boe,
        "processing_cost_per_boe": cost_analysis.get("processing_costs", 0) / total_boe,
        "total_variable_cost_per_boe": cost_analysis.get("variable_costs", 0)
        / total_boe,
    }

    # Netback calculation (revenue minus variable costs per BOE)
    netback_calculation = {
        "gross_netback_per_boe": revenue_per_boe_breakdown["total_revenue_per_boe"],
        "operating_netback_per_boe": (
            revenue_per_boe_breakdown["total_revenue_per_boe"]
            - cost_per_boe_breakdown["operating_cost_per_boe"]
        ),
        "royalty_netback_per_boe": (
            revenue_per_boe_breakdown["total_revenue_per_boe"]
            - cost_per_boe_breakdown["operating_cost_per_boe"]
            - cost_per_boe_breakdown["royalties_per_boe"]
        ),
        "full_netback_per_boe": (
            revenue_per_boe_breakdown["total_revenue_per_boe"]
            - cost_per_boe_breakdown["total_variable_cost_per_boe"]
        ),
    }

    # Netback percentages
    gross_revenue_per_boe = revenue_per_boe_breakdown["total_revenue_per_boe"]
    netback_percentages = {}
    if gross_revenue_per_boe > 0:
        netback_percentages = {
            "operating_netback_pct": (
                netback_calculation["operating_netback_per_boe"]
                / gross_revenue_per_boe
                * 100
            ),
            "royalty_netback_pct": (
                netback_calculation["royalty_netback_per_boe"]
                / gross_revenue_per_boe
                * 100
            ),
            "full_netback_pct": (
                netback_calculation["full_netback_per_boe"]
                / gross_revenue_per_boe
                * 100
            ),
        }

    return {
        "revenue_per_boe_breakdown": revenue_per_boe_breakdown,
        "cost_per_boe_breakdown": cost_per_boe_breakdown,
        "netback_calculation": netback_calculation,
        "netback_percentages": netback_percentages,
        "total_boe": total_boe,
    }


def calculate_cost_structure_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate detailed cost structure analysis"""
    cost_analysis = context.get("cost_analysis", {})
    revenue_breakdown = context.get("revenue_breakdown", {})

    total_costs = cost_analysis.get("total_costs", 0)
    total_revenue = revenue_breakdown.get("total_revenue", 0)

    # Cost breakdown percentages
    cost_breakdown_pct = {}
    if total_costs > 0:
        cost_breakdown_pct = {
            "operating_costs_pct": (
                cost_analysis.get("operating_costs", 0) / total_costs * 100
            ),
            "capital_costs_pct": (
                cost_analysis.get("capital_costs", 0) / total_costs * 100
            ),
            "royalties_pct": (cost_analysis.get("royalties", 0) / total_costs * 100),
            "severance_tax_pct": (
                cost_analysis.get("severance_tax", 0) / total_costs * 100
            ),
            "other_costs_pct": (
                cost_analysis.get("other_costs", 0) / total_costs * 100
            ),
        }

    # Cost as percentage of revenue
    cost_as_revenue_pct = {}
    if total_revenue > 0:
        cost_as_revenue_pct = {
            "total_costs_vs_revenue_pct": (total_costs / total_revenue * 100),
            "operating_costs_vs_revenue_pct": (
                cost_analysis.get("operating_costs", 0) / total_revenue * 100
            ),
            "royalties_vs_revenue_pct": (
                cost_analysis.get("royalties", 0) / total_revenue * 100
            ),
            "severance_tax_vs_revenue_pct": (
                cost_analysis.get("severance_tax", 0) / total_revenue * 100
            ),
        }

    # Cost efficiency metrics
    cost_efficiency = {
        "cost_efficiency_index": (
            (1 - (total_costs / total_revenue)) if total_revenue > 0 else 0
        ),
        "operating_efficiency": (
            (1 - (cost_analysis.get("operating_costs", 0) / total_revenue))
            if total_revenue > 0
            else 0
        ),
        "variable_cost_ratio": (
            (cost_analysis.get("variable_costs", 0) / total_revenue)
            if total_revenue > 0
            else 0
        ),
    }

    return {
        "cost_breakdown_percentages": cost_breakdown_pct,
        "cost_as_revenue_percentages": cost_as_revenue_pct,
        "cost_efficiency_metrics": cost_efficiency,
        "absolute_costs": {
            "operating_costs": cost_analysis.get("operating_costs", 0),
            "capital_costs": cost_analysis.get("capital_costs", 0),
            "royalties": cost_analysis.get("royalties", 0),
            "severance_tax": cost_analysis.get("severance_tax", 0),
            "total_costs": total_costs,
        },
    }


def calculate_revenue_optimization_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate revenue optimization analysis"""
    revenue_breakdown = context.get("revenue_breakdown", {})
    production_metrics = context.get("production_metrics", {})

    oil_bbls = production_metrics.get("oil_bbls", 0)
    gas_mcf = production_metrics.get("gas_mcf", 0)

    # Revenue per unit calculations
    revenue_per_unit = {}
    if oil_bbls > 0:
        revenue_per_unit["oil_revenue_per_bbl"] = (
            revenue_breakdown.get("oil_revenue", 0) / oil_bbls
        )
    if gas_mcf > 0:
        revenue_per_unit["gas_revenue_per_mcf"] = (
            revenue_breakdown.get("gas_revenue", 0) / gas_mcf
        )

    # Revenue mix analysis
    total_revenue = revenue_breakdown.get("total_revenue", 0)
    revenue_mix = {}
    if total_revenue > 0:
        revenue_mix = {
            "oil_revenue_percentage": revenue_breakdown.get("oil_percentage", 0),
            "gas_revenue_percentage": revenue_breakdown.get("gas_percentage", 0),
            "ngl_revenue_percentage": revenue_breakdown.get("ngl_percentage", 0),
            "hydrocarbon_revenue_percentage": (
                revenue_breakdown.get("oil_percentage", 0)
                + revenue_breakdown.get("gas_percentage", 0)
                + revenue_breakdown.get("ngl_percentage", 0)
            ),
        }

    # Revenue diversification index (higher = more diversified)
    oil_pct = revenue_mix.get("oil_revenue_percentage", 0) / 100
    gas_pct = revenue_mix.get("gas_revenue_percentage", 0) / 100
    ngl_pct = revenue_mix.get("ngl_revenue_percentage", 0) / 100

    diversification_index = (
        1 - (oil_pct**2 + gas_pct**2 + ngl_pct**2)
        if oil_pct or gas_pct or ngl_pct
        else 0
    )

    # Revenue quality metrics
    revenue_quality = {
        "revenue_concentration_risk": max(oil_pct, gas_pct, ngl_pct),
        "revenue_diversification_index": diversification_index,
        "high_value_revenue_pct": oil_pct + ngl_pct,
        "gas_revenue_dependency": gas_pct,
    }

    return {
        "revenue_per_unit": revenue_per_unit,
        "revenue_mix": revenue_mix,
        "revenue_quality_metrics": revenue_quality,
        "optimization_opportunities": identify_revenue_optimization_opportunities(
            revenue_mix, revenue_quality
        ),
    }


def identify_revenue_optimization_opportunities(
    revenue_mix: Dict[str, float], revenue_quality: Dict[str, float]
) -> List[str]:
    """Identify revenue optimization opportunities"""
    opportunities = []

    if revenue_quality.get("gas_revenue_dependency", 0) > 0.6:
        opportunities.append("Consider oil development to reduce gas dependence")

    if revenue_quality.get("revenue_diversification_index", 0) < 0.3:
        opportunities.append("Improve revenue diversification across hydrocarbon types")

    if revenue_mix.get("ngl_revenue_percentage", 0) < 5:
        opportunities.append("Evaluate NGL capture and processing opportunities")

    if revenue_quality.get("revenue_concentration_risk", 0) > 0.8:
        opportunities.append(
            "Mitigate revenue concentration risk through diversification"
        )

    return opportunities


def get_economic_kpis(
    context: Dict[str, Any], netback_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Get key economic performance indicators"""
    profitability = context.get("profitability_metrics", {})
    npv_analysis = context.get("npv_analysis", {})
    roi_metrics = context.get("roi_metrics", {})

    return {
        "primary_kpis": {
            "net_income": profitability.get("net_income", 0),
            "profit_margin": profitability.get("profit_margin", 0),
            "netback_per_boe": netback_analysis["netback_calculation"].get(
                "full_netback_per_boe", 0
            ),
            "npv": npv_analysis.get("npv", 0),
        },
        "secondary_kpis": {
            "operating_margin": profitability.get("operating_margin", 0),
            "ebitda": profitability.get("ebitda", 0),
            "irr": npv_analysis.get("irr", 0),
            "roi": roi_metrics.get("annual_roi", 0),
            "operating_netback_per_boe": netback_analysis["netback_calculation"].get(
                "operating_netback_per_boe", 0
            ),
        },
        "financial_ratios": {
            "revenue_per_boe": netback_analysis["revenue_per_boe_breakdown"].get(
                "total_revenue_per_boe", 0
            ),
            "cost_per_boe": netback_analysis["cost_per_boe_breakdown"].get(
                "total_variable_cost_per_boe", 0
            ),
            "payback_period": roi_metrics.get("payback_period_years", 0),
            "full_netback_percentage": netback_analysis["netback_percentages"].get(
                "full_netback_pct", 0
            ),
        },
        "cost_efficiency_metrics": {
            "operating_cost_per_boe": netback_analysis["cost_per_boe_breakdown"].get(
                "operating_cost_per_boe", 0
            ),
            "royalties_per_boe": netback_analysis["cost_per_boe_breakdown"].get(
                "royalties_per_boe", 0
            ),
            "total_variable_cost_per_boe": netback_analysis[
                "cost_per_boe_breakdown"
            ].get("total_variable_cost_per_boe", 0),
        },
    }


def prepare_tornado_chart_data(
    oil_sensitivity: List[Dict],
    production_sensitivity: List[Dict],
    cost_sensitivity: List[Dict],
) -> List[Dict]:
    """Prepare data for tornado chart showing sensitivity impact"""

    def get_sensitivity_range(data, key="npv"):
        values = [item[key] for item in data]
        return max(values) - min(values)

    tornado_data = [
        {
            "variable": "Oil Price",
            "impact_range": get_sensitivity_range(oil_sensitivity),
            "low_case": min(item["npv"] for item in oil_sensitivity),
            "high_case": max(item["npv"] for item in oil_sensitivity),
        },
        {
            "variable": "Production Volume",
            "impact_range": get_sensitivity_range(production_sensitivity),
            "low_case": min(item["npv"] for item in production_sensitivity),
            "high_case": max(item["npv"] for item in production_sensitivity),
        },
        {
            "variable": "Operating Costs",
            "impact_range": get_sensitivity_range(cost_sensitivity),
            "low_case": min(item["npv"] for item in cost_sensitivity),
            "high_case": max(item["npv"] for item in cost_sensitivity),
        },
    ]

    # Sort by impact range (most sensitive first)
    return sorted(tornado_data, key=lambda x: x["impact_range"], reverse=True)
