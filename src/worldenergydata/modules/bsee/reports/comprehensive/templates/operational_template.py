"""
Operational Template for BSEE operational performance reporting.

This module provides comprehensive operational reporting including:
- Well status and performance tracking
- Production efficiency metrics
- Equipment utilization and reliability
- Maintenance scheduling and tracking
- Failure analysis and root cause tracking
- Operational KPI dashboards
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..models import EconomicMetrics, ProductionMetrics
from .base import BaseReportTemplate

# Note: WellData, LeaseData, etc. are not used in this template
# from ..hierarchical_aggregator import WellData, LeaseData, FieldData, BlockData


class WellStatus(Enum):
    """Well operational status enumeration"""

    PRODUCING = "producing"
    SHUT_IN = "shut_in"
    OFFLINE = "offline"
    DRILLING = "drilling"
    COMPLETING = "completing"
    ABANDONED = "abandoned"
    SUSPENDED = "suspended"
    TESTING = "testing"
    WORKOVER = "workover"
    MONITORING = "monitoring"


@dataclass
class WellOperationalMetrics:
    """Operational metrics for individual wells"""

    # Well identification
    well_api: int
    well_name: str
    status: WellStatus
    report_date: date

    # Drilling metrics
    drilling_start_date: Optional[date] = None
    drilling_end_date: Optional[date] = None
    drilling_depth_ft: float = 0
    total_depth_ft: float = 0
    lateral_length_ft: float = 0
    planned_drilling_days: int = 0
    actual_drilling_days: int = 0
    drilling_cost: float = 0

    # Completion metrics
    completion_start_date: Optional[date] = None
    completion_end_date: Optional[date] = None
    planned_completion_days: int = 0
    actual_completion_days: int = 0
    completion_cost: float = 0
    frac_stages: int = 0
    proppant_lbs: float = 0

    # Production metrics
    first_production_date: Optional[date] = None
    last_production_date: Optional[date] = None
    daily_production_boe: float = 0
    cumulative_production_boe: float = 0
    peak_production_boe: float = 0
    peak_production_date: Optional[date] = None

    # Operational metrics
    uptime_hours: float = 0
    total_hours: float = 0
    planned_downtime_hours: float = 0
    unplanned_downtime_hours: float = 0
    failure_count: int = 0
    workover_count: int = 0
    intervention_count: int = 0

    def drilling_efficiency(self) -> float:
        """Calculate drilling efficiency percentage"""
        if self.actual_drilling_days > 0:
            return (self.planned_drilling_days / self.actual_drilling_days) * 100
        return 0

    def completion_efficiency(self) -> float:
        """Calculate completion efficiency percentage"""
        if self.actual_completion_days > 0:
            return (self.planned_completion_days / self.actual_completion_days) * 100
        return 0

    def well_cycle_time(self) -> int:
        """Calculate total well cycle time from spud to first production"""
        if self.drilling_start_date and self.first_production_date:
            return (self.first_production_date - self.drilling_start_date).days
        return 0

    def availability_percentage(self) -> float:
        """Calculate well availability percentage"""
        if self.total_hours > 0:
            return (self.uptime_hours / self.total_hours) * 100
        return 0

    def drilling_rate_ft_per_day(self) -> float:
        """Calculate average drilling rate"""
        if self.actual_drilling_days > 0:
            return self.drilling_depth_ft / self.actual_drilling_days
        return 0

    def cost_per_foot_drilled(self) -> float:
        """Calculate cost per foot drilled"""
        if self.total_depth_ft > 0:
            total_cost = self.drilling_cost + self.completion_cost
            return total_cost / self.total_depth_ft
        return 0

    def production_days(self) -> int:
        """Calculate total production days"""
        if self.first_production_date and self.last_production_date:
            return (self.last_production_date - self.first_production_date).days + 1
        return 0


@dataclass
class ProductionEfficiencyMetrics:
    """Production efficiency metrics for various organizational levels"""

    entity_id: str
    entity_type: str  # well, lease, field, block
    report_date: date

    # Production volumes
    production_oil_bbl: float = 0
    production_gas_mcf: float = 0
    production_water_bbl: float = 0
    production_ngl_bbl: float = 0

    # Time metrics
    production_days: int = 0
    operating_days: int = 0
    downtime_days: int = 0

    # Capacity metrics
    design_capacity_boe: float = 0
    actual_production_boe: float = 0
    peak_production_boe: float = 0

    # Well counts
    wells_producing: int = 0
    wells_shut_in: int = 0
    wells_offline: int = 0
    total_wells: int = 0

    # Processing metrics
    processing_capacity_bbl: float = 0
    processing_utilization_pct: float = 0
    separator_efficiency_pct: float = 0

    def __post_init__(self):
        """Validate metrics after initialization"""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id cannot be empty")
        if self.entity_type not in ["well", "lease", "field", "block"]:
            raise ValueError(f"Invalid entity_type: {self.entity_type}")
        # Handle negative production values gracefully by setting to 0
        if self.production_oil_bbl < 0:
            self.production_oil_bbl = 0
        if self.production_gas_mcf < 0:
            self.production_gas_mcf = 0
        if self.production_water_bbl < 0:
            self.production_water_bbl = 0

    def production_efficiency(self) -> float:
        """Calculate production efficiency vs design capacity"""
        if self.design_capacity_boe > 0 and self.production_days > 0:
            theoretical = self.design_capacity_boe * self.production_days
            return (self.actual_production_boe / theoretical) * 100
        return 0

    def operating_efficiency(self) -> float:
        """Calculate operating efficiency"""
        if self.production_days > 0:
            return (self.operating_days / self.production_days) * 100
        return 0

    def well_availability(self) -> float:
        """Calculate well availability percentage"""
        if self.total_wells > 0:
            return (self.wells_producing / self.total_wells) * 100
        return 0

    def daily_production_rate_boe(self) -> float:
        """Calculate average daily production rate"""
        if self.production_days > 0:
            return self.actual_production_boe / self.production_days
        return 0

    def water_cut_percentage(self) -> float:
        """Calculate water cut percentage"""
        total_liquids = self.production_oil_bbl + self.production_water_bbl
        if total_liquids > 0:
            return (self.production_water_bbl / total_liquids) * 100
        return 0

    def gas_oil_ratio(self) -> float:
        """Calculate gas-oil ratio (GOR) in mcf/bbl"""
        if self.production_oil_bbl > 0:
            return self.production_gas_mcf / self.production_oil_bbl
        return 0


@dataclass
class EquipmentMetrics:
    """Equipment operational and reliability metrics"""

    equipment_id: str
    equipment_type: str  # ESP, gas lift, separator, compressor, etc.
    equipment_name: str
    installation_date: Optional[date] = None
    report_date: Optional[date] = None

    # Runtime metrics
    total_runtime_hours: float = 0
    planned_runtime_hours: float = 0
    unplanned_downtime_hours: float = 0
    planned_downtime_hours: float = 0

    # Reliability metrics
    failure_count: int = 0
    mtbf_hours: float = 0  # Mean Time Between Failures
    mttr_hours: float = 0  # Mean Time To Repair

    # Cost metrics
    maintenance_cost: float = 0
    replacement_cost: float = 0
    operating_cost: float = 0

    # Performance metrics
    efficiency_rating: float = 0
    capacity_utilization: float = 0
    performance_degradation: float = 0

    def equipment_availability(self) -> float:
        """Calculate equipment availability percentage"""
        total_time = (
            self.total_runtime_hours
            + self.unplanned_downtime_hours
            + self.planned_downtime_hours
        )
        if total_time > 0:
            return (self.total_runtime_hours / total_time) * 100
        return 0

    def equipment_utilization(self) -> float:
        """Calculate equipment utilization percentage"""
        if self.planned_runtime_hours > 0:
            return (self.total_runtime_hours / self.planned_runtime_hours) * 100
        return 0

    def equipment_reliability(self) -> float:
        """Calculate equipment reliability percentage"""
        if self.mtbf_hours > 0 and self.mttr_hours >= 0:
            return (self.mtbf_hours / (self.mtbf_hours + self.mttr_hours)) * 100
        return 0

    def equipment_age_days(self) -> int:
        """Calculate equipment age in days"""
        if self.installation_date and self.report_date:
            return (self.report_date - self.installation_date).days
        return 0

    def cost_effectiveness_ratio(self) -> float:
        """Calculate cost effectiveness ratio"""
        if self.replacement_cost > 0:
            return self.maintenance_cost / self.replacement_cost
        return 0


@dataclass
class MaintenanceRecord:
    """Maintenance activity record"""

    maintenance_id: str
    equipment_id: str
    maintenance_date: date
    maintenance_type: str  # preventive, corrective, predictive
    description: str
    duration_hours: float
    cost: float
    performed_by: str
    next_scheduled_date: Optional[date] = None
    effectiveness_score: float = 0
    parts_replaced: List[str] = field(default_factory=list)

    def is_overdue(self) -> bool:
        """Check if next maintenance is overdue"""
        if self.next_scheduled_date:
            return date.today() > self.next_scheduled_date
        return False

    def days_until_next(self) -> int:
        """Calculate days until next scheduled maintenance"""
        if self.next_scheduled_date:
            return (self.next_scheduled_date - date.today()).days
        return 0


@dataclass
class FailureAnalysis:
    """Failure event analysis and tracking"""

    failure_id: str
    equipment_id: Optional[str] = None
    well_api: Optional[int] = None
    failure_date: datetime = field(default_factory=datetime.now)
    failure_type: str = ""  # mechanical, electrical, process, human error
    root_cause: str = ""
    severity: str = ""  # low, medium, high, critical
    production_impact_boe: float = 0
    downtime_hours: float = 0
    repair_cost: float = 0
    preventable: bool = False
    corrective_actions: List[str] = field(default_factory=list)
    lessons_learned: str = ""

    def total_impact_cost(self, oil_price: float = 80) -> float:
        """Calculate total impact cost including lost production"""
        lost_revenue = self.production_impact_boe * oil_price
        return self.repair_cost + lost_revenue

    def failure_rate_per_1000_hours(self, runtime_hours: float) -> float:
        """Calculate failure rate per 1000 operating hours"""
        if runtime_hours > 0:
            return (1 / runtime_hours) * 1000
        return 0


@dataclass
class OperationalKPI:
    """Operational Key Performance Indicator"""

    kpi_id: str
    kpi_name: str
    kpi_category: str  # production, drilling, reliability, safety, cost
    target_value: float
    actual_value: float
    unit: str
    measurement_date: date
    trend: str = "stable"  # improving, declining, stable
    variance: float = 0
    status: str = "normal"  # good, warning, critical

    def performance_percentage(self) -> float:
        """Calculate KPI performance percentage"""
        if self.target_value > 0:
            return (self.actual_value / self.target_value) * 100
        return 0

    def is_on_target(self) -> bool:
        """Check if KPI meets target"""
        return self.actual_value >= self.target_value

    def variance_percentage(self) -> float:
        """Calculate variance from target as percentage"""
        if self.target_value > 0:
            return ((self.actual_value - self.target_value) / self.target_value) * 100
        return 0


class OperationalTemplate(BaseReportTemplate):
    """
    Operational Template for comprehensive operational performance reporting.

    This template provides:
    - Well status and performance tracking
    - Production efficiency analysis
    - Equipment reliability metrics
    - Maintenance scheduling
    - Failure analysis
    - Operational KPI dashboards
    """

    def __init__(
        self,
        template_name: str = "operational_report",
        version: str = "1.0.0",
        **kwargs,
    ):
        """Initialize operational template"""
        super().__init__(
            template_name=template_name,
            template_type="operational",
            version=version,
            **kwargs,
        )
        self._setup_operational_context_requirements()
        # Create alias for jinja_env for backward compatibility
        self.env = self.jinja_env

    def _setup_operational_context_requirements(self):
        """Set up operational-specific context requirements"""
        # Define required context fields for operational template
        operational_requirements = [
            "operational_summary",
            "well_performance",
            "production_efficiency",
            "equipment_reliability",
            "maintenance_schedule",
            "failure_analysis",
            "operational_kpis",
            "report_metadata",
        ]

        # Add to the context requirements
        self.context.require_fields(operational_requirements)

        # Store requirements for reference (if needed by tests)
        self.required_context = {
            "operational_summary": "Overall operational performance summary",
            "well_performance": "Individual well operational metrics",
            "production_efficiency": "Production efficiency analysis",
            "equipment_reliability": "Equipment reliability and utilization",
            "maintenance_schedule": "Maintenance activities and planning",
            "failure_analysis": "Failure events and root cause analysis",
            "operational_kpis": "Key performance indicators",
            "report_metadata": "Report generation metadata",
        }

    def build_operational_context(
        self,
        well_metrics: List[WellOperationalMetrics],
        production_metrics: Optional[ProductionEfficiencyMetrics] = None,
        equipment_metrics: Optional[List[EquipmentMetrics]] = None,
        maintenance_records: Optional[List[MaintenanceRecord]] = None,
        failure_records: Optional[List[FailureAnalysis]] = None,
        report_date: Optional[date] = None,
        entity_name: str = "Operational Unit",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Build operational report context.

        Args:
            well_metrics: List of well operational metrics
            production_metrics: Production efficiency metrics
            equipment_metrics: Equipment reliability metrics
            maintenance_records: Maintenance activity records
            failure_records: Failure analysis records
            report_date: Report generation date
            entity_name: Name of reporting entity
            **kwargs: Additional context parameters

        Returns:
            Complete context dictionary for template rendering
        """
        report_date = report_date or date.today()
        context = {
            "entity_name": entity_name,
            "report_metadata": {
                "generated_date": report_date.isoformat(),
                "report_type": "operational",
                "version": self.version,
                "total_wells": len(well_metrics),
            },
        }

        # Add operational summary
        self._add_operational_summary(
            context, well_metrics, production_metrics, equipment_metrics
        )

        # Add well performance analysis
        self._add_well_performance_analysis(context, well_metrics)

        # Add production efficiency metrics
        if production_metrics:
            self._add_production_efficiency_analysis(context, production_metrics)

        # Add equipment reliability analysis
        if equipment_metrics:
            self._add_equipment_reliability_analysis(context, equipment_metrics)

        # Add maintenance schedule
        if maintenance_records:
            self._add_maintenance_schedule(context, maintenance_records)

        # Add failure analysis
        if failure_records:
            self._add_failure_analysis(context, failure_records)

        # Calculate and add operational KPIs
        kpis = self.calculate_operational_kpis(
            well_metrics, production_metrics, equipment_metrics
        )
        context["operational_kpis"] = self._format_kpis(kpis)

        # Add any additional context
        context.update(kwargs)

        return context

    def _add_operational_summary(
        self,
        context: Dict[str, Any],
        well_metrics: List[WellOperationalMetrics],
        production_metrics: Optional[ProductionEfficiencyMetrics],
        equipment_metrics: Optional[List[EquipmentMetrics]],
    ):
        """Add operational summary to context"""
        # Calculate summary statistics
        total_wells = len(well_metrics)
        wells_producing = sum(
            1 for w in well_metrics if w.status == WellStatus.PRODUCING
        )
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

    def _add_well_performance_analysis(
        self, context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
    ):
        """Add well performance analysis to context"""
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
            w.completion_efficiency()
            for w in well_metrics
            if w.actual_completion_days > 0
        ]
        if completion_efficiencies:
            performance["average_completion_efficiency"] = round(
                np.mean(completion_efficiencies), 2
            )

        cycle_times = [
            w.well_cycle_time() for w in well_metrics if w.well_cycle_time() > 0
        ]
        if cycle_times:
            performance["average_cycle_time"] = round(np.mean(cycle_times), 0)

        performance["total_production_boe"] = sum(
            w.cumulative_production_boe for w in well_metrics
        )

        uptimes = [
            w.availability_percentage() for w in well_metrics if w.total_hours > 0
        ]
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

    def _add_production_efficiency_analysis(
        self, context: Dict[str, Any], production_metrics: ProductionEfficiencyMetrics
    ):
        """Add production efficiency analysis to context"""
        efficiency = {
            "efficiency_percentage": round(
                production_metrics.production_efficiency(), 2
            ),
            "operating_efficiency": round(production_metrics.operating_efficiency(), 2),
            "well_availability": round(production_metrics.well_availability(), 2),
            "daily_rate_boe": round(production_metrics.daily_production_rate_boe(), 2),
            "water_cut": round(production_metrics.water_cut_percentage(), 2),
            "gas_oil_ratio": round(production_metrics.gas_oil_ratio(), 2),
            "capacity_utilization": production_metrics.processing_utilization_pct,
        }

        context["production_efficiency"] = efficiency

    def _add_equipment_reliability_analysis(
        self, context: Dict[str, Any], equipment_metrics: List[EquipmentMetrics]
    ):
        """Add equipment reliability analysis to context"""
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

    def _add_maintenance_schedule(
        self, context: Dict[str, Any], maintenance_records: List[MaintenanceRecord]
    ):
        """Add maintenance schedule to context"""
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
            m
            for m in maintenance_records
            if m.next_scheduled_date and not m.is_overdue()
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

    def _add_failure_analysis(
        self, context: Dict[str, Any], failure_records: List[FailureAnalysis]
    ):
        """Add failure analysis to context"""
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

    def _format_kpis(self, kpis: List[OperationalKPI]) -> List[Dict[str, Any]]:
        """Format KPIs for template rendering"""
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

    def add_drilling_performance_analysis(
        self, context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
    ):
        """Add detailed drilling performance analysis"""
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
            "average_drilling_depth": np.mean(
                [w.drilling_depth_ft for w in drilling_data]
            ),
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
            1
            for w in drilling_data
            if w.actual_drilling_days <= w.planned_drilling_days
        )
        performance["wells_delayed"] = len(drilling_data) - performance["wells_on_time"]

        context["drilling_performance"] = performance

    def add_completion_efficiency_metrics(
        self, context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
    ):
        """Add completion efficiency metrics"""
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
        self, context: Dict[str, Any], production_metrics: ProductionEfficiencyMetrics
    ):
        """Add production optimization tracking"""
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
        self, context: Dict[str, Any], equipment_metrics: List[EquipmentMetrics]
    ):
        """Add detailed equipment utilization analysis"""
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
            "total_maintenance_cost": sum(
                e.maintenance_cost for e in equipment_metrics
            ),
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

    def calculate_operational_kpis(
        self,
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
            avg_availability = np.mean(
                [w.availability_percentage() for w in well_metrics]
            )
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

    def generate_operational_visualizations(
        self, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate operational visualizations using Plotly.

        Args:
            context: Report context with operational data

        Returns:
            Dictionary of Plotly figure JSONs
        """
        visualizations = {}

        # Create well status distribution chart
        if "operational_summary" in context:
            summary = context["operational_summary"]
            visualizations["well_status_chart"] = self._create_well_status_chart(
                summary
            )

        # Create production efficiency gauge
        if "production_efficiency" in context:
            efficiency = context["production_efficiency"]
            visualizations["efficiency_gauge"] = self._create_efficiency_gauge(
                efficiency
            )

        # Create equipment reliability chart
        if "equipment_reliability" in context:
            reliability = context["equipment_reliability"]
            visualizations["reliability_chart"] = self._create_reliability_chart(
                reliability
            )

        # Create KPI dashboard
        if "operational_kpis" in context:
            kpis = context["operational_kpis"]
            visualizations["kpi_dashboard"] = self._create_kpi_dashboard(kpis)

        # Create failure analysis chart
        if "failure_analysis" in context:
            failures = context["failure_analysis"]
            visualizations["failure_chart"] = self._create_failure_chart(failures)

        return visualizations

    def _create_well_status_chart(self, summary: Dict[str, Any]) -> str:
        """Create well status distribution pie chart"""
        labels = ["Producing", "Drilling", "Offline", "Other"]
        values = [
            summary.get("wells_producing", 0),
            summary.get("wells_drilling", 0),
            summary.get("wells_offline", 0),
            summary.get("total_wells", 0)
            - summary.get("wells_producing", 0)
            - summary.get("wells_drilling", 0)
            - summary.get("wells_offline", 0),
        ]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.3,
                    marker_colors=["#2ecc71", "#3498db", "#e74c3c", "#95a5a6"],
                )
            ]
        )

        fig.update_layout(title="Well Status Distribution", showlegend=True, height=400)

        return fig.to_json()

    def _create_efficiency_gauge(self, efficiency: Dict[str, Any]) -> str:
        """Create production efficiency gauge chart"""
        value = efficiency.get("efficiency_percentage", 0)

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=value,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Production Efficiency (%)"},
                delta={"reference": 85, "increasing": {"color": "green"}},
                gauge={
                    "axis": {
                        "range": [None, 100],
                        "tickwidth": 1,
                        "tickcolor": "darkblue",
                    },
                    "bar": {"color": "darkblue"},
                    "bgcolor": "white",
                    "borderwidth": 2,
                    "bordercolor": "gray",
                    "steps": [
                        {"range": [0, 50], "color": "#ffcccc"},
                        {"range": [50, 75], "color": "#fff4cc"},
                        {"range": [75, 90], "color": "#ffffcc"},
                        {"range": [90, 100], "color": "#ccffcc"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 85,
                    },
                },
            )
        )

        fig.update_layout(height=400)

        return fig.to_json()

    def _create_reliability_chart(self, reliability: Dict[str, Any]) -> str:
        """Create equipment reliability bar chart"""
        equipment_details = reliability.get("equipment_details", [])

        if not equipment_details:
            return "{}"

        names = [e["name"] for e in equipment_details]
        availabilities = [e["availability"] for e in equipment_details]
        reliabilities = [e["reliability"] for e in equipment_details]

        fig = go.Figure(
            data=[
                go.Bar(
                    name="Availability",
                    x=names,
                    y=availabilities,
                    marker_color="#3498db",
                ),
                go.Bar(
                    name="Reliability", x=names, y=reliabilities, marker_color="#2ecc71"
                ),
            ]
        )

        fig.update_layout(
            title="Equipment Performance Metrics",
            xaxis_title="Equipment",
            yaxis_title="Percentage (%)",
            barmode="group",
            height=400,
            showlegend=True,
        )

        return fig.to_json()

    def _create_kpi_dashboard(self, kpis: List[Dict[str, Any]]) -> str:
        """Create KPI dashboard with multiple indicators"""
        if not kpis:
            return "{}"

        # Create subplots for KPIs
        rows = (len(kpis) + 2) // 3  # 3 KPIs per row
        fig = make_subplots(
            rows=rows,
            cols=3,
            subplot_titles=[kpi["name"] for kpi in kpis],
            specs=[[{"type": "indicator"}] * 3 for _ in range(rows)],
        )

        for i, kpi in enumerate(kpis):
            row = (i // 3) + 1
            col = (i % 3) + 1

            color = (
                "#2ecc71"
                if kpi["status"] == "good"
                else "#f39c12" if kpi["status"] == "warning" else "#e74c3c"
            )

            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=kpi["actual"],
                    delta={"reference": kpi["target"], "relative": True},
                    number={"suffix": f" {kpi['unit']}", "font": {"color": color}},
                    domain={"x": [0, 1], "y": [0, 1]},
                ),
                row=row,
                col=col,
            )

        fig.update_layout(
            title="Operational KPI Dashboard", height=200 * rows, showlegend=False
        )

        return fig.to_json()

    def _create_failure_chart(self, failures: Dict[str, Any]) -> str:
        """Create failure analysis chart"""
        by_type = failures.get("by_type", {})

        if not by_type:
            return "{}"

        fig = go.Figure(
            data=[
                go.Bar(
                    x=list(by_type.keys()),
                    y=list(by_type.values()),
                    marker_color="#e74c3c",
                    text=list(by_type.values()),
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title="Failures by Type",
            xaxis_title="Failure Type",
            yaxis_title="Count",
            height=400,
        )

        return fig.to_json()

    def render_template_string(
        self, template_string: str, context: Dict[str, Any]
    ) -> str:
        """
        Render a template string with the given context.

        Args:
            template_string: Jinja2 template string
            context: Context dictionary

        Returns:
            Rendered template string
        """
        template = self.env.from_string(template_string)
        return template.render(**context)
