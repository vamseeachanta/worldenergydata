"""
Compliance Data Models for regulatory compliance reporting.

This module contains the dataclass definitions for compliance metrics,
environmental metrics, safety metrics, production quotas, and regulatory milestones.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Optional


@dataclass
class ComplianceMetrics:
    """Compliance metrics for regulatory reporting"""

    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    report_date: Optional[date] = None
    permitted_production_bbls: float = 0.0
    actual_production_bbls: float = 0.0
    permitted_gas_mcf: float = 0.0
    actual_gas_mcf: float = 0.0
    compliance_score: float = 0.0
    regulatory_violations: int = 0
    inspection_results: Dict[str, Any] = field(default_factory=dict)
    permit_status: str = "active"

    def production_compliance_percentage(self) -> float:
        """Calculate production compliance percentage"""
        if self.permitted_production_bbls > 0:
            return (self.actual_production_bbls / self.permitted_production_bbls) * 100
        return 0.0

    def gas_compliance_percentage(self) -> float:
        """Calculate gas production compliance percentage"""
        if self.permitted_gas_mcf > 0:
            return (self.actual_gas_mcf / self.permitted_gas_mcf) * 100
        return 0.0

    def is_over_production(self) -> bool:
        """Check if production exceeds permitted levels"""
        return self.actual_production_bbls > self.permitted_production_bbls

    def over_production_amount(self) -> float:
        """Calculate over-production amount"""
        if self.is_over_production():
            return self.actual_production_bbls - self.permitted_production_bbls
        return 0.0

    def overall_compliance_status(self) -> str:
        """Get overall compliance status"""
        if self.regulatory_violations == 0 and not self.is_over_production():
            return "Compliant"
        elif self.regulatory_violations > 0 or self.is_over_production():
            return "Non-Compliant"
        else:
            return "Under Review"


@dataclass
class EnvironmentalMetrics:
    """Environmental compliance metrics"""

    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    report_date: Optional[date] = None
    spill_incidents: int = 0
    total_spill_volume_bbls: float = 0.0
    air_emissions_tons: float = 0.0
    water_discharge_bbls: float = 0.0
    waste_generated_tons: float = 0.0
    environmental_violations: int = 0
    permit_compliance_score: float = 0.0

    def calculate_environmental_score(self) -> float:
        """Calculate overall environmental compliance score"""
        # Base score starts at 1.0 (perfect)
        score = 1.0

        # Deduct for spill incidents (0.1 per incident)
        score -= self.spill_incidents * 0.1

        # Deduct for spill volume (0.01 per barrel)
        score -= self.total_spill_volume_bbls * 0.01

        # Deduct for violations (0.15 per violation)
        score -= self.environmental_violations * 0.15

        # Deduct for high emissions (above 100 tons)
        if self.air_emissions_tons > 100:
            score -= (self.air_emissions_tons - 100) * 0.001

        # Ensure score doesn't go below 0
        return max(0.0, score)

    def spill_rate_per_bbl_produced(self, production_bbls: float) -> float:
        """Calculate spill rate per barrel produced"""
        if production_bbls > 0:
            return self.total_spill_volume_bbls / production_bbls
        return 0.0

    def environmental_status(self) -> str:
        """Get environmental compliance status"""
        score = self.calculate_environmental_score()
        if score >= 0.9:
            return "Excellent"
        elif score >= 0.8:
            return "Good"
        elif score >= 0.7:
            return "Fair"
        else:
            return "Poor"


@dataclass
class SafetyMetrics:
    """Safety compliance metrics"""

    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    report_date: Optional[date] = None
    incident_count: int = 0
    lost_time_incidents: int = 0
    total_recordables: int = 0
    near_misses: int = 0
    man_hours_worked: float = 0.0
    safety_violations: int = 0
    safety_inspections: int = 0
    safety_training_hours: float = 0.0

    def calculate_trir(self) -> float:
        """Calculate Total Recordable Incident Rate"""
        if self.man_hours_worked > 0:
            return (self.total_recordables * 200000) / self.man_hours_worked
        return 0.0

    def calculate_ltir(self) -> float:
        """Calculate Lost Time Incident Rate"""
        if self.man_hours_worked > 0:
            return (self.lost_time_incidents * 200000) / self.man_hours_worked
        return 0.0

    def calculate_safety_score(self) -> float:
        """Calculate overall safety score"""
        # Base score starts at 1.0
        score = 1.0

        # Deduct for incidents
        score -= self.incident_count * 0.1
        score -= self.lost_time_incidents * 0.2
        score -= self.safety_violations * 0.15

        # Add for positive factors
        if self.safety_inspections > 0:
            score += min(0.1, self.safety_inspections * 0.01)

        if self.safety_training_hours > 0:
            score += min(0.05, self.safety_training_hours * 0.001)

        return max(0.0, min(1.0, score))

    def safety_status(self) -> str:
        """Get safety compliance status"""
        score = self.calculate_safety_score()
        if score >= 0.95:
            return "Excellent"
        elif score >= 0.85:
            return "Good"
        elif score >= 0.75:
            return "Fair"
        else:
            return "Poor"


@dataclass
class ProductionQuota:
    """Production quota and compliance tracking"""

    entity_id: Optional[str] = None
    quota_type: str = "monthly"  # daily, monthly, yearly
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    oil_quota_bbls: float = 0.0
    gas_quota_mcf: float = 0.0
    actual_oil_bbls: float = 0.0
    actual_gas_mcf: float = 0.0
    quota_source: str = "BSEE"
    permit_number: Optional[str] = None

    def oil_compliance_percentage(self) -> float:
        """Calculate oil production compliance percentage"""
        if self.oil_quota_bbls > 0:
            return (self.actual_oil_bbls / self.oil_quota_bbls) * 100
        return 0.0

    def gas_compliance_percentage(self) -> float:
        """Calculate gas production compliance percentage"""
        if self.gas_quota_mcf > 0:
            return (self.actual_gas_mcf / self.gas_quota_mcf) * 100
        return 0.0

    def overall_compliance_score(self) -> float:
        """Calculate overall compliance score (weighted average)"""
        oil_compliance = self.oil_compliance_percentage() / 100
        gas_compliance = self.gas_compliance_percentage() / 100

        # Weight by production volumes if available
        oil_weight = self.actual_oil_bbls
        gas_weight = self.actual_gas_mcf * 0.17  # Convert to oil equivalent

        total_weight = oil_weight + gas_weight
        if total_weight > 0:
            return (
                oil_compliance * oil_weight + gas_compliance * gas_weight
            ) / total_weight
        else:
            return (oil_compliance + gas_compliance) / 2

    def is_quota_exceeded(self) -> bool:
        """Check if any quota is exceeded"""
        return (
            self.actual_oil_bbls > self.oil_quota_bbls
            or self.actual_gas_mcf > self.gas_quota_mcf
        )


@dataclass
class RegulatoryMilestone:
    """Regulatory milestone and deadline tracking"""

    milestone_id: str
    entity_id: Optional[str] = None
    description: str = ""
    due_date: Optional[date] = None
    completion_date: Optional[date] = None
    status: str = "pending"  # pending, completed, overdue
    regulatory_agency: str = "BSEE"
    regulation_reference: Optional[str] = None
    priority: str = "medium"  # low, medium, high, critical
    responsible_party: Optional[str] = None

    def is_completed(self) -> bool:
        """Check if milestone is completed"""
        return self.status == "completed" and self.completion_date is not None

    def is_overdue(self) -> bool:
        """Check if milestone is overdue"""
        if self.due_date and not self.is_completed():
            return date.today() > self.due_date
        return False

    def days_until_due(self) -> int:
        """Calculate days until due date"""
        if self.due_date:
            return (self.due_date - date.today()).days
        return 0

    def completion_status(self) -> str:
        """Get completion status string"""
        if self.is_completed():
            return "Completed"
        elif self.is_overdue():
            return "Overdue"
        else:
            return "Pending"


# Public API
__all__ = [
    "ComplianceMetrics",
    "EnvironmentalMetrics",
    "SafetyMetrics",
    "ProductionQuota",
    "RegulatoryMilestone",
]
