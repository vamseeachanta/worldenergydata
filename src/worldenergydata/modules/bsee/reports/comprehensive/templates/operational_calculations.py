"""
Operational calculations for BSEE operational performance reporting.

This module contains all metric calculation functions for
operational reporting including:
- Operational KPI calculations
- Drilling performance analysis
- Completion efficiency metrics
- Production optimization tracking
- Equipment utilization analysis
"""

from datetime import date
from typing import Any, Dict, List, Optional

import numpy as np

from .operational_models import (
    EquipmentMetrics,
    OperationalKPI,
    ProductionEfficiencyMetrics,
    WellOperationalMetrics,
)


def calculate_operational_kpis(
    well_metrics: List[WellOperationalMetrics],
    production_metrics: Optional[ProductionEfficiencyMetrics] = None,
    equipment_metrics: Optional[List[EquipmentMetrics]] = None,
) -> List[OperationalKPI]:
    """
    Calculate operational KPIs from metrics.

    Args:
        well_metrics: Well operational metrics
        production_metrics: Production efficiency metrics
        equipment_metrics: Equipment reliability metrics

    Returns:
        List of calculated KPIs
    """
    kpis = []
    report_date = date.today()

    # Well performance KPIs
    if well_metrics:
        # Well availability KPI
        avg_availability = np.mean([w.availability_percentage() for w in well_metrics])
        kpis.append(
            OperationalKPI(
                kpi_id="KPI-001",
                kpi_name="Well Availability",
                kpi_category="reliability",
                target_value=90.0,
                actual_value=round(avg_availability, 2),
                unit="percent",
                measurement_date=report_date,
                variance=avg_availability - 90.0,
                status=(
                    "good"
                    if avg_availability >= 90
                    else "warning" if avg_availability >= 85 else "critical"
                ),
                trend="stable",
            )
        )

        # Drilling efficiency KPI
        drilling_wells = [w for w in well_metrics if w.actual_drilling_days > 0]
        if drilling_wells:
            avg_drilling_eff = np.mean(
                [w.drilling_efficiency() for w in drilling_wells]
            )
            kpis.append(
                OperationalKPI(
                    kpi_id="KPI-002",
                    kpi_name="Drilling Efficiency",
                    kpi_category="drilling",
                    target_value=95.0,
                    actual_value=round(avg_drilling_eff, 2),
                    unit="percent",
                    measurement_date=report_date,
                    variance=avg_drilling_eff - 95.0,
                    status=(
                        "good"
                        if avg_drilling_eff >= 95
                        else "warning" if avg_drilling_eff >= 90 else "critical"
                    ),
                    trend="improving" if avg_drilling_eff > 90 else "declining",
                )
            )

    # Production efficiency KPIs
    if production_metrics:
        # Overall production efficiency
        prod_eff = production_metrics.production_efficiency()
        kpis.append(
            OperationalKPI(
                kpi_id="KPI-003",
                kpi_name="Overall Production Efficiency",
                kpi_category="production",
                target_value=85.0,
                actual_value=round(prod_eff, 2),
                unit="percent",
                measurement_date=report_date,
                variance=prod_eff - 85.0,
                status=(
                    "good"
                    if prod_eff >= 85
                    else "warning" if prod_eff >= 75 else "critical"
                ),
                trend="stable",
            )
        )

        # Operating efficiency
        op_eff = production_metrics.operating_efficiency()
        kpis.append(
            OperationalKPI(
                kpi_id="KPI-004",
                kpi_name="Operating Efficiency",
                kpi_category="production",
                target_value=95.0,
                actual_value=round(op_eff, 2),
                unit="percent",
                measurement_date=report_date,
                variance=op_eff - 95.0,
                status=(
                    "good"
                    if op_eff >= 95
                    else "warning" if op_eff >= 90 else "critical"
                ),
                trend="stable",
            )
        )

    # Equipment reliability KPIs
    if equipment_metrics:
        # Average equipment reliability
        avg_reliability = np.mean(
            [e.equipment_reliability() for e in equipment_metrics]
        )
        kpis.append(
            OperationalKPI(
                kpi_id="KPI-005",
                kpi_name="Equipment Reliability",
                kpi_category="reliability",
                target_value=98.0,
                actual_value=round(avg_reliability, 2),
                unit="percent",
                measurement_date=report_date,
                variance=avg_reliability - 98.0,
                status=(
                    "good"
                    if avg_reliability >= 98
                    else "warning" if avg_reliability >= 95 else "critical"
                ),
                trend="stable",
            )
        )

        # Equipment utilization
        avg_utilization = np.mean(
            [e.equipment_utilization() for e in equipment_metrics]
        )
        kpis.append(
            OperationalKPI(
                kpi_id="KPI-006",
                kpi_name="Equipment Utilization",
                kpi_category="reliability",
                target_value=85.0,
                actual_value=round(avg_utilization, 2),
                unit="percent",
                measurement_date=report_date,
                variance=avg_utilization - 85.0,
                status=(
                    "good"
                    if avg_utilization >= 85
                    else "warning" if avg_utilization >= 75 else "critical"
                ),
                trend="improving" if avg_utilization > 80 else "declining",
            )
        )

    return kpis


def add_drilling_performance_analysis(
    context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
) -> None:
    """
    Add detailed drilling performance analysis to context.

    Args:
        context: Report context dictionary to update
        well_metrics: List of well operational metrics
    """
    drilling_data = [w for w in well_metrics if w.actual_drilling_days > 0]

    if not drilling_data:
        context["drilling_performance"] = {
            "total_wells_drilled": 0,
            "message": "No drilling data available",
        }
        return

    performance = {
        "total_wells_drilled": len(drilling_data),
        "average_drilling_days": np.mean(
            [w.actual_drilling_days for w in drilling_data]
        ),
        "average_drilling_depth": np.mean([w.drilling_depth_ft for w in drilling_data]),
        "average_drilling_rate": np.mean(
            [w.drilling_rate_ft_per_day() for w in drilling_data]
        ),
        "drilling_efficiency": np.mean(
            [w.drilling_efficiency() for w in drilling_data]
        ),
        "total_drilling_cost": sum(w.drilling_cost for w in drilling_data),
        "average_cost_per_foot": np.mean(
            [w.cost_per_foot_drilled() for w in drilling_data]
        ),
        "wells_by_status": {},
    }

    # Count wells by drilling performance
    performance["wells_on_time"] = sum(
        1 for w in drilling_data if w.actual_drilling_days <= w.planned_drilling_days
    )
    performance["wells_delayed"] = len(drilling_data) - performance["wells_on_time"]

    context["drilling_performance"] = performance


def add_completion_efficiency_metrics(
    context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
) -> None:
    """
    Add completion efficiency metrics to context.

    Args:
        context: Report context dictionary to update
        well_metrics: List of well operational metrics
    """
    completion_data = [w for w in well_metrics if w.actual_completion_days > 0]

    if not completion_data:
        context["completion_metrics"] = {
            "total_wells_completed": 0,
            "message": "No completion data available",
        }
        return

    metrics = {
        "total_wells_completed": len(completion_data),
        "average_completion_days": np.mean(
            [w.actual_completion_days for w in completion_data]
        ),
        "completion_efficiency": np.mean(
            [w.completion_efficiency() for w in completion_data]
        ),
        "total_completion_cost": sum(w.completion_cost for w in completion_data),
        "average_frac_stages": np.mean(
            [w.frac_stages for w in completion_data if w.frac_stages > 0]
        ),
        "total_proppant_lbs": sum(w.proppant_lbs for w in completion_data),
    }

    context["completion_metrics"] = metrics


def add_production_optimization_tracking(
    context: Dict[str, Any], production_metrics: ProductionEfficiencyMetrics
) -> None:
    """
    Add production optimization tracking to context.

    Args:
        context: Report context dictionary to update
        production_metrics: Production efficiency metrics
    """
    optimization = {
        "production_efficiency": production_metrics.production_efficiency(),
        "daily_rate": production_metrics.daily_production_rate_boe(),
        "capacity_utilization": (
            production_metrics.actual_production_boe
            / (
                production_metrics.design_capacity_boe
                * production_metrics.production_days
            )
            * 100
            if production_metrics.design_capacity_boe > 0
            else 0
        ),
        "water_cut": production_metrics.water_cut_percentage(),
        "gas_oil_ratio": production_metrics.gas_oil_ratio(),
        "well_availability": production_metrics.well_availability(),
        "operating_efficiency": production_metrics.operating_efficiency(),
        "optimization_opportunities": [],
    }

    # Identify optimization opportunities
    if optimization["production_efficiency"] < 80:
        optimization["optimization_opportunities"].append(
            "Production efficiency below 80% - consider debottlenecking"
        )

    if optimization["water_cut"] > 40:  # Lowered threshold for better detection
        optimization["optimization_opportunities"].append(
            "High water cut - evaluate water handling capacity"
        )

    if optimization["well_availability"] < 85:
        optimization["optimization_opportunities"].append(
            "Low well availability - review maintenance strategy"
        )

    context["production_optimization"] = optimization


def add_equipment_utilization_analysis(
    context: Dict[str, Any], equipment_metrics: List[EquipmentMetrics]
) -> None:
    """
    Add detailed equipment utilization analysis to context.

    Args:
        context: Report context dictionary to update
        equipment_metrics: List of equipment metrics
    """
    if not equipment_metrics:
        context["equipment_analysis"] = {
            "total_equipment": 0,
            "message": "No equipment data available",
        }
        return

    analysis = {
        "total_equipment": len(equipment_metrics),
        "average_availability": np.mean(
            [e.equipment_availability() for e in equipment_metrics]
        ),
        "average_utilization": np.mean(
            [e.equipment_utilization() for e in equipment_metrics]
        ),
        "average_reliability": np.mean(
            [e.equipment_reliability() for e in equipment_metrics]
        ),
        "average_mtbf": np.mean(
            [e.mtbf_hours for e in equipment_metrics if e.mtbf_hours > 0]
        ),
        "average_mttr": np.mean(
            [e.mttr_hours for e in equipment_metrics if e.mttr_hours > 0]
        ),
        "total_maintenance_cost": sum(e.maintenance_cost for e in equipment_metrics),
        "equipment_by_type": {},
    }

    # Group equipment by type
    for equip in equipment_metrics:
        if equip.equipment_type not in analysis["equipment_by_type"]:
            analysis["equipment_by_type"][equip.equipment_type] = {
                "count": 0,
                "availability": [],
                "reliability": [],
            }
        analysis["equipment_by_type"][equip.equipment_type]["count"] += 1
        analysis["equipment_by_type"][equip.equipment_type]["availability"].append(
            equip.equipment_availability()
        )
        analysis["equipment_by_type"][equip.equipment_type]["reliability"].append(
            equip.equipment_reliability()
        )

    # Calculate averages by type
    for eq_type in analysis["equipment_by_type"]:
        type_data = analysis["equipment_by_type"][eq_type]
        type_data["avg_availability"] = np.mean(type_data["availability"])
        type_data["avg_reliability"] = np.mean(type_data["reliability"])
        del type_data["availability"]  # Remove raw data
        del type_data["reliability"]

    context["equipment_analysis"] = analysis


# Export all public names
__all__ = [
    "calculate_operational_kpis",
    "add_drilling_performance_analysis",
    "add_completion_efficiency_metrics",
    "add_production_optimization_tracking",
    "add_equipment_utilization_analysis",
]
