"""
Operational context building for BSEE operational performance reporting.

This module contains all context building functions for
operational reporting including:
- Operational summary building
- Well performance analysis
- Production efficiency analysis
- Equipment reliability analysis
- Maintenance schedule building
- Failure analysis building
- KPI formatting
"""

from typing import Any, Dict, List, Optional

import numpy as np

from .operational_models import (
    EquipmentMetrics,
    FailureAnalysis,
    MaintenanceRecord,
    OperationalKPI,
    ProductionEfficiencyMetrics,
    WellOperationalMetrics,
    WellStatus,
)


def add_operational_summary(
    context: Dict[str, Any],
    well_metrics: List[WellOperationalMetrics],
    production_metrics: Optional[ProductionEfficiencyMetrics],
    equipment_metrics: Optional[List[EquipmentMetrics]],
) -> None:
    """
    Add operational summary to context.

    Args:
        context: Report context dictionary to update
        well_metrics: List of well operational metrics
        production_metrics: Production efficiency metrics (optional)
        equipment_metrics: List of equipment metrics (optional)
    """
    # Calculate summary statistics
    total_wells = len(well_metrics)
    wells_producing = sum(1 for w in well_metrics if w.status == WellStatus.PRODUCING)
    wells_drilling = sum(1 for w in well_metrics if w.status == WellStatus.DRILLING)
    wells_offline = sum(1 for w in well_metrics if w.status == WellStatus.OFFLINE)

    avg_availability = (
        np.mean([w.availability_percentage() for w in well_metrics])
        if well_metrics
        else 0
    )

    summary = {
        "total_wells": total_wells,
        "wells_producing": wells_producing,
        "wells_drilling": wells_drilling,
        "wells_offline": wells_offline,
        "average_availability": round(avg_availability, 2),
        "production_efficiency": 0,
        "equipment_reliability": 0,
    }

    if production_metrics:
        summary["production_efficiency"] = round(
            production_metrics.production_efficiency(), 2
        )

    if equipment_metrics:
        avg_reliability = np.mean(
            [e.equipment_reliability() for e in equipment_metrics]
        )
        summary["equipment_reliability"] = round(avg_reliability, 2)

    context["operational_summary"] = summary


def add_well_performance_analysis(
    context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
) -> None:
    """
    Add well performance analysis to context.

    Args:
        context: Report context dictionary to update
        well_metrics: List of well operational metrics
    """
    performance = {
        "wells_producing": sum(
            1 for w in well_metrics if w.status == WellStatus.PRODUCING
        ),
        "average_drilling_efficiency": 0,
        "average_completion_efficiency": 0,
        "average_cycle_time": 0,
        "total_production_boe": 0,
        "average_uptime": 0,
        "well_details": [],
    }

    drilling_efficiencies = [
        w.drilling_efficiency() for w in well_metrics if w.actual_drilling_days > 0
    ]
    if drilling_efficiencies:
        performance["average_drilling_efficiency"] = round(
            np.mean(drilling_efficiencies), 2
        )

    completion_efficiencies = [
        w.completion_efficiency() for w in well_metrics if w.actual_completion_days > 0
    ]
    if completion_efficiencies:
        performance["average_completion_efficiency"] = round(
            np.mean(completion_efficiencies), 2
        )

    cycle_times = [w.well_cycle_time() for w in well_metrics if w.well_cycle_time() > 0]
    if cycle_times:
        performance["average_cycle_time"] = round(np.mean(cycle_times), 0)

    performance["total_production_boe"] = sum(
        w.cumulative_production_boe for w in well_metrics
    )

    uptimes = [w.availability_percentage() for w in well_metrics if w.total_hours > 0]
    if uptimes:
        performance["average_uptime"] = round(np.mean(uptimes), 2)

    # Add individual well details
    for well in well_metrics[:10]:  # Limit to top 10 for summary
        performance["well_details"].append(
            {
                "name": well.well_name,
                "status": well.status.value,
                "availability": round(well.availability_percentage(), 2),
                "production": well.daily_production_boe,
            }
        )

    context["well_performance"] = performance


def add_production_efficiency_analysis(
    context: Dict[str, Any], production_metrics: ProductionEfficiencyMetrics
) -> None:
    """
    Add production efficiency analysis to context.

    Args:
        context: Report context dictionary to update
        production_metrics: Production efficiency metrics
    """
    efficiency = {
        "efficiency_percentage": round(production_metrics.production_efficiency(), 2),
        "operating_efficiency": round(production_metrics.operating_efficiency(), 2),
        "well_availability": round(production_metrics.well_availability(), 2),
        "daily_rate_boe": round(production_metrics.daily_production_rate_boe(), 2),
        "water_cut": round(production_metrics.water_cut_percentage(), 2),
        "gas_oil_ratio": round(production_metrics.gas_oil_ratio(), 2),
        "capacity_utilization": production_metrics.processing_utilization_pct,
    }

    context["production_efficiency"] = efficiency


def add_equipment_reliability_analysis(
    context: Dict[str, Any], equipment_metrics: List[EquipmentMetrics]
) -> None:
    """
    Add equipment reliability analysis to context.

    Args:
        context: Report context dictionary to update
        equipment_metrics: List of equipment metrics
    """
    reliability = {
        "total_equipment": len(equipment_metrics),
        "average_availability": 0,
        "average_utilization": 0,
        "average_reliability": 0,
        "total_failures": 0,
        "equipment_details": [],
    }

    availabilities = [e.equipment_availability() for e in equipment_metrics]
    if availabilities:
        reliability["average_availability"] = round(np.mean(availabilities), 2)

    utilizations = [e.equipment_utilization() for e in equipment_metrics]
    if utilizations:
        reliability["average_utilization"] = round(np.mean(utilizations), 2)

    reliabilities = [e.equipment_reliability() for e in equipment_metrics]
    if reliabilities:
        reliability["average_reliability"] = round(np.mean(reliabilities), 2)

    reliability["total_failures"] = sum(e.failure_count for e in equipment_metrics)

    # Add equipment details
    for equip in equipment_metrics[:10]:  # Limit to top 10
        reliability["equipment_details"].append(
            {
                "name": equip.equipment_name,
                "type": equip.equipment_type,
                "availability": round(equip.equipment_availability(), 2),
                "reliability": round(equip.equipment_reliability(), 2),
            }
        )

    context["equipment_reliability"] = reliability


def add_maintenance_schedule(
    context: Dict[str, Any], maintenance_records: List[MaintenanceRecord]
) -> None:
    """
    Add maintenance schedule to context.

    Args:
        context: Report context dictionary to update
        maintenance_records: List of maintenance records
    """
    schedule = {
        "total_maintenance": len(maintenance_records),
        "preventive": sum(
            1 for m in maintenance_records if m.maintenance_type == "preventive"
        ),
        "corrective": sum(
            1 for m in maintenance_records if m.maintenance_type == "corrective"
        ),
        "total_cost": sum(m.cost for m in maintenance_records),
        "overdue": sum(1 for m in maintenance_records if m.is_overdue()),
        "upcoming": [],
    }

    # Find upcoming maintenance
    upcoming = [
        m for m in maintenance_records if m.next_scheduled_date and not m.is_overdue()
    ]
    upcoming.sort(key=lambda x: x.next_scheduled_date)

    for maint in upcoming[:10]:  # Limit to next 10
        schedule["upcoming"].append(
            {
                "equipment_id": maint.equipment_id,
                "date": maint.next_scheduled_date.isoformat(),
                "days_until": maint.days_until_next(),
                "type": maint.maintenance_type,
            }
        )

    context["maintenance_schedule"] = schedule


def add_failure_analysis(
    context: Dict[str, Any], failure_records: List[FailureAnalysis]
) -> None:
    """
    Add failure analysis to context.

    Args:
        context: Report context dictionary to update
        failure_records: List of failure analysis records
    """
    analysis = {
        "total_failures": len(failure_records),
        "preventable": sum(1 for f in failure_records if f.preventable),
        "total_downtime": sum(f.downtime_hours for f in failure_records),
        "total_cost": sum(f.repair_cost for f in failure_records),
        "by_type": {},
        "by_severity": {},
        "recent_failures": [],
    }

    # Group by failure type
    for failure in failure_records:
        if failure.failure_type not in analysis["by_type"]:
            analysis["by_type"][failure.failure_type] = 0
        analysis["by_type"][failure.failure_type] += 1

    # Group by severity
    for failure in failure_records:
        if failure.severity not in analysis["by_severity"]:
            analysis["by_severity"][failure.severity] = 0
        analysis["by_severity"][failure.severity] += 1

    # Add recent failures
    recent = sorted(failure_records, key=lambda x: x.failure_date, reverse=True)
    for failure in recent[:5]:  # Last 5 failures
        analysis["recent_failures"].append(
            {
                "date": failure.failure_date.isoformat(),
                "type": failure.failure_type,
                "severity": failure.severity,
                "downtime": failure.downtime_hours,
                "cost": failure.repair_cost,
            }
        )

    context["failure_analysis"] = analysis


def format_kpis(kpis: List[OperationalKPI]) -> List[Dict[str, Any]]:
    """
    Format KPIs for template rendering.

    Args:
        kpis: List of operational KPIs

    Returns:
        List of formatted KPI dictionaries
    """
    formatted = []
    for kpi in kpis:
        formatted.append(
            {
                "name": kpi.kpi_name,
                "category": kpi.kpi_category,
                "actual": kpi.actual_value,
                "target": kpi.target_value,
                "unit": kpi.unit,
                "performance": round(kpi.performance_percentage(), 2),
                "variance": round(kpi.variance_percentage(), 2),
                "status": kpi.status,
                "trend": kpi.trend,
                "on_target": kpi.is_on_target(),
            }
        )
    return formatted


# Export all public names
__all__ = [
    "add_operational_summary",
    "add_well_performance_analysis",
    "add_production_efficiency_analysis",
    "add_equipment_reliability_analysis",
    "add_maintenance_schedule",
    "add_failure_analysis",
    "format_kpis",
]
