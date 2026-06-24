"""
Operational data models for BSEE operational performance reporting.

This module contains all data classes, enums, and value objects used
in operational reporting including:
- Well status enumeration
- Well operational metrics
- Production efficiency metrics
- Equipment metrics
- Maintenance records
- Failure analysis records
- Operational KPIs
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional


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


# Export all public names
__all__ = [
    "WellStatus",
    "WellOperationalMetrics",
    "ProductionEfficiencyMetrics",
    "EquipmentMetrics",
    "MaintenanceRecord",
    "FailureAnalysis",
    "OperationalKPI",
]
