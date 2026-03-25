"""
Go-by report calculation utilities for economic template
Contains methods for calculating 14-row structure and field economics matching Excel reports
"""

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from ..hierarchical_aggregator import (
        CostStructure,
        HierarchicalAggregator,
        PriceDeck,
    )
    from ..models import ProductionMetrics


def calculate_goby_14_row_structure(
    production_data: Dict[str, float],
    revenue_calcs: Dict[str, float],
    cost_calcs: Dict[str, float],
) -> Dict[str, Any]:
    """Calculate 14-row structure metrics matching go-by Excel reports"""

    # Extract volumes
    oil_bbls = production_data.get("oil_bbls", 0)
    gas_mcf = production_data.get("gas_mcf", 0)
    water_bbls = production_data.get("water_bbls", 0)
    boe_total = oil_bbls + (gas_mcf / 6)  # Convert gas to BOE

    # Extract financial values
    gross_revenue = revenue_calcs.get("gross_revenue", 0)
    operating_costs = cost_calcs.get("operating_cost", 0)
    royalties = cost_calcs.get("royalties", 0)
    severance_tax = cost_calcs.get("severance_tax", 0)
    net_income = cost_calcs.get("net_income", 0)

    # Calculate 14-row structure (following go-by Excel report format)
    goby_14_rows = {
        "row_1_oil_production_bbls": oil_bbls,
        "row_2_gas_production_mcf": gas_mcf,
        "row_3_water_production_bbls": water_bbls,
        "row_4_total_boe": boe_total,
        "row_5_oil_revenue_usd": revenue_calcs.get("oil_revenue", 0),
        "row_6_gas_revenue_usd": revenue_calcs.get("gas_revenue", 0),
        "row_7_ngl_revenue_usd": revenue_calcs.get("ngl_revenue", 0),
        "row_8_gross_revenue_usd": gross_revenue,
        "row_9_operating_costs_usd": operating_costs,
        "row_10_royalties_usd": royalties,
        "row_11_severance_tax_usd": severance_tax,
        "row_12_total_costs_usd": cost_calcs.get("total_costs", 0),
        "row_13_net_income_usd": net_income,
        "row_14_profit_margin_pct": (
            (net_income / gross_revenue * 100) if gross_revenue > 0 else 0
        ),
    }

    # Add per-BOE calculations (key metrics from go-by reports)
    if boe_total > 0:
        goby_14_rows.update(
            {
                "revenue_per_boe": gross_revenue / boe_total,
                "operating_cost_per_boe": operating_costs / boe_total,
                "royalties_per_boe": royalties / boe_total,
                "netback_per_boe": net_income / boe_total,
                "total_cost_per_boe": cost_calcs.get("total_costs", 0) / boe_total,
            }
        )

    # Add productivity metrics (common in go-by reports)
    if oil_bbls > 0:
        goby_14_rows.update(
            {
                "gas_oil_ratio": gas_mcf / oil_bbls,
                "water_cut_pct": (
                    (water_bbls / (oil_bbls + water_bbls) * 100)
                    if (oil_bbls + water_bbls) > 0
                    else 0
                ),
            }
        )

    return goby_14_rows


def apply_goby_revenue_calculations(
    production: "ProductionMetrics",
    price_deck: "PriceDeck",
    cost_structure: "CostStructure",
) -> Dict[str, Any]:
    """Apply go-by report revenue calculation patterns matching Excel reports"""
    from ..hierarchical_aggregator import HierarchicalAggregator

    # Initialize hierarchical aggregator with same price/cost settings
    hierarchical_agg = HierarchicalAggregator(
        price_deck=price_deck, cost_structure=cost_structure
    )

    # Convert ProductionMetrics to production dictionary format for aggregator
    production_data = {
        "oil_bbls": production.oil_production_bbls,
        "gas_mcf": production.gas_production_mcf,
        "ngl_bbls": getattr(production, "ngl_production_bbls", 0.0),
        "water_bbls": production.water_production_bbls,
    }

    # Apply hierarchical aggregator revenue calculations (matches go-by Excel logic)
    revenue_calculations = hierarchical_agg.well_aggregator.calculate_revenue(
        production_data
    )
    cost_calculations = hierarchical_agg.well_aggregator.calculate_costs(
        production_data, revenue_calculations
    )

    # Calculate 14-row structure metrics matching go-by reports
    goby_metrics = calculate_goby_14_row_structure(
        production_data, revenue_calculations, cost_calculations
    )

    boe_production = production_data["oil_bbls"] + (production_data["gas_mcf"] / 6)

    return {
        "goby_revenue_calculations": revenue_calculations,
        "goby_cost_calculations": cost_calculations,
        "goby_14_row_metrics": goby_metrics,
        "goby_economic_summary": {
            "gross_revenue": revenue_calculations["gross_revenue"],
            "total_costs": cost_calculations["total_costs"],
            "net_income": cost_calculations["net_income"],
            "boe_production": boe_production,
            "revenue_per_boe": (
                revenue_calculations["gross_revenue"] / boe_production
                if boe_production > 0
                else 0
            ),
            "cost_per_boe": (
                cost_calculations["total_costs"] / boe_production
                if boe_production > 0
                else 0
            ),
            "netback_per_boe": (
                cost_calculations["net_income"] / boe_production
                if boe_production > 0
                else 0
            ),
        },
    }


def integrate_goby_field_economics(field_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Integrate field-level economics following go-by report patterns"""

    # Extract field-level aggregated data (from hierarchical aggregator output)
    field_economics = {
        "field_summary": {
            "total_wells": field_metrics.get("total_wells", 0),
            "active_wells": field_metrics.get("active_wells", 0),
            "total_leases": field_metrics.get("total_leases", 0),
            "oil_production_bbls": field_metrics.get("oil_production_bbls", 0),
            "gas_production_mcf": field_metrics.get("gas_production_mcf", 0),
            "water_production_bbls": field_metrics.get("water_production_bbls", 0),
            "total_boe": field_metrics.get("total_boe", 0),
        },
        "field_economics": {
            "gross_revenue": field_metrics.get("gross_revenue", 0),
            "operating_cost": field_metrics.get("operating_cost", 0),
            "royalties": field_metrics.get("royalties", 0),
            "severance_tax": field_metrics.get("severance_tax", 0),
            "total_costs": field_metrics.get("total_costs", 0),
            "net_income": field_metrics.get("net_income", 0),
        },
        "field_performance": {
            "avg_oil_per_well": field_metrics.get("avg_oil_per_well", 0),
            "avg_gas_per_well": field_metrics.get("avg_gas_per_well", 0),
            "avg_revenue_per_well": field_metrics.get("gross_revenue", 0)
            / field_metrics.get("total_wells", 1),
            "avg_wells_per_lease": field_metrics.get("avg_wells_per_lease", 0),
        },
    }

    return field_economics


def build_production_context(production: "ProductionMetrics") -> Dict[str, Any]:
    """Build production metrics context dictionary"""
    return {
        "oil_bbls": production.oil_production_bbls,
        "gas_mcf": production.gas_production_mcf,
        "water_bbls": production.water_production_bbls,
        "daily_oil_rate": production.daily_oil_rate,
        "daily_gas_rate": production.daily_gas_rate,
        "period_start": production.period_start,
        "period_end": production.period_end,
        "days_in_period": production.days_in_period,
        "active_well_count": production.active_well_count,
        "entity_id": production.entity_id,
        "entity_type": production.entity_type,
    }
