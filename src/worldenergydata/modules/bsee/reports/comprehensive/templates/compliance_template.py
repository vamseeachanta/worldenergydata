"""
Compliance Template for regulatory compliance reporting
Implements BSEE regulatory compliance sections and metrics
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from ..models import EconomicMetrics, ProductionMetrics
from .base import BaseReportTemplate, TemplateContext


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


class ComplianceTemplate(BaseReportTemplate):
    """
    Compliance Template for BSEE regulatory compliance reporting
    Implements regulatory sections including production quotas, environmental compliance,
    safety metrics, and regulatory milestone tracking
    """

    def __init__(
        self,
        template_name: str = "compliance_report",
        version: str = "1.0.0",
        template_path: Optional[Path] = None,
        **kwargs,
    ):
        """Initialize ComplianceTemplate"""
        super().__init__(
            template_name=template_name,
            template_type="compliance",
            version=version,
            template_path=template_path,
            **kwargs,
        )

        # Add compliance-specific context requirements
        self._setup_compliance_context_requirements()

        # Initialize compliance sections
        self.compliance_sections = {
            "production_compliance": True,
            "environmental_compliance": True,
            "safety_compliance": True,
            "regulatory_milestones": True,
            "inspection_results": True,
        }

    def _setup_compliance_context_requirements(self):
        """Set up compliance-specific context requirements"""
        compliance_requirements = [
            "compliance_metrics",
            "regulatory_status",
            "environmental_metrics",
            "safety_metrics",
            "production_quotas",
            "regulatory_milestones",
        ]

        # Add to existing requirements
        self.context.require_fields(compliance_requirements)

    def build_compliance_context(
        self,
        compliance_metrics: ComplianceMetrics,
        environmental_metrics: Optional[EnvironmentalMetrics] = None,
        safety_metrics: Optional[SafetyMetrics] = None,
        production_quotas: Optional[List[ProductionQuota]] = None,
        regulatory_milestones: Optional[List[RegulatoryMilestone]] = None,
    ) -> Dict[str, Any]:
        """Build compliance-specific context"""
        context = {
            "compliance_metrics": compliance_metrics,
            "regulatory_status": compliance_metrics.overall_compliance_status(),
            "environmental_metrics": environmental_metrics or EnvironmentalMetrics(),
            "safety_metrics": safety_metrics or SafetyMetrics(),
            "production_quotas": production_quotas or [],
            "regulatory_milestones": regulatory_milestones or [],
        }

        # Add compliance summary
        context["compliance_summary"] = self._generate_compliance_summary(
            compliance_metrics, environmental_metrics, safety_metrics
        )

        return context

    def add_production_quota_analysis(self, production: Any, quota: ProductionQuota):
        """Add production quota vs actual analysis"""
        quota_analysis = {
            "oil_quota": quota.oil_quota_bbls,
            "oil_actual": getattr(production, "oil_production_bbls", 0),
            "oil_compliance": quota.oil_compliance_percentage(),
            "gas_quota": quota.gas_quota_mcf,
            "gas_actual": getattr(production, "gas_production_mcf", 0),
            "gas_compliance": quota.gas_compliance_percentage(),
            "overall_compliance": quota.overall_compliance_score(),
            "quota_exceeded": quota.is_quota_exceeded(),
            "period_start": quota.period_start,
            "period_end": quota.period_end,
        }

        # Calculate variance
        quota_analysis["oil_variance"] = (
            quota_analysis["oil_actual"] - quota.oil_quota_bbls
        )
        quota_analysis["gas_variance"] = (
            quota_analysis["gas_actual"] - quota.gas_quota_mcf
        )
        quota_analysis["oil_variance_pct"] = (
            (quota_analysis["oil_variance"] / quota.oil_quota_bbls * 100)
            if quota.oil_quota_bbls > 0
            else 0
        )
        quota_analysis["gas_variance_pct"] = (
            (quota_analysis["gas_variance"] / quota.gas_quota_mcf * 100)
            if quota.gas_quota_mcf > 0
            else 0
        )

        self.context["quota_analysis"] = quota_analysis

    def _generate_compliance_summary(
        self,
        compliance: ComplianceMetrics,
        environmental: Optional[EnvironmentalMetrics],
        safety: Optional[SafetyMetrics],
    ) -> Dict[str, Any]:
        """Generate compliance summary statistics"""
        summary = {
            "overall_status": compliance.overall_compliance_status(),
            "production_compliance": compliance.production_compliance_percentage(),
            "regulatory_violations": compliance.regulatory_violations,
            "environmental_score": (
                environmental.calculate_environmental_score() if environmental else 0.0
            ),
            "safety_score": safety.calculate_safety_score() if safety else 0.0,
        }

        # Calculate overall compliance score
        scores = [
            compliance.production_compliance_percentage() / 100,
            summary["environmental_score"],
            summary["safety_score"],
        ]
        summary["overall_compliance_score"] = sum(scores) / len(scores)

        return summary

    def add_production_quota_analysis(
        self, production: ProductionMetrics, quota: ProductionQuota
    ):
        """Add production quota vs actual analysis"""
        quota_analysis = {
            "oil_quota": quota.oil_quota_bbls,
            "oil_actual": production.oil_production_bbls,
            "oil_compliance": quota.oil_compliance_percentage(),
            "gas_quota": quota.gas_quota_mcf,
            "gas_actual": production.gas_production_mcf,
            "gas_compliance": quota.gas_compliance_percentage(),
            "overall_compliance": quota.overall_compliance_score(),
            "quota_exceeded": quota.is_quota_exceeded(),
            "period_start": quota.period_start,
            "period_end": quota.period_end,
        }

        # Calculate variance
        quota_analysis["oil_variance"] = (
            production.oil_production_bbls - quota.oil_quota_bbls
        )
        quota_analysis["gas_variance"] = (
            production.gas_production_mcf - quota.gas_quota_mcf
        )
        quota_analysis["oil_variance_pct"] = (
            (quota_analysis["oil_variance"] / quota.oil_quota_bbls * 100)
            if quota.oil_quota_bbls > 0
            else 0
        )
        quota_analysis["gas_variance_pct"] = (
            (quota_analysis["gas_variance"] / quota.gas_quota_mcf * 100)
            if quota.gas_quota_mcf > 0
            else 0
        )

        self.context["quota_analysis"] = quota_analysis

    def add_environmental_compliance_tracking(
        self, environmental_metrics: EnvironmentalMetrics
    ):
        """Add comprehensive environmental compliance tracking"""
        env_compliance = {
            "spill_incidents": environmental_metrics.spill_incidents,
            "total_spill_volume": environmental_metrics.total_spill_volume_bbls,
            "air_emissions": environmental_metrics.air_emissions_tons,
            "water_discharge": environmental_metrics.water_discharge_bbls,
            "waste_generated": environmental_metrics.waste_generated_tons,
            "environmental_score": environmental_metrics.calculate_environmental_score(),
            "environmental_status": environmental_metrics.environmental_status(),
            "violations": environmental_metrics.environmental_violations,
        }

        # Add regulatory thresholds and compliance status
        env_compliance["regulatory_thresholds"] = self._get_environmental_thresholds()
        env_compliance["threshold_compliance"] = self._check_environmental_thresholds(
            environmental_metrics
        )

        # Add environmental performance benchmarks
        env_compliance["benchmarks"] = self._get_environmental_benchmarks()
        env_compliance["benchmark_comparison"] = self._compare_to_benchmarks(
            environmental_metrics
        )

        # Add environmental risk assessment
        env_compliance["risk_assessment"] = self._assess_environmental_risks(
            environmental_metrics
        )

        # Add compliance trends with historical analysis
        env_compliance["trends"] = self._analyze_environmental_trends(
            environmental_metrics
        )

        # Add corrective actions and recommendations
        env_compliance["corrective_actions"] = self._generate_environmental_actions(
            environmental_metrics
        )

        # Add environmental KPIs
        env_compliance["kpis"] = self._calculate_environmental_kpis(
            environmental_metrics
        )

        self.context["environmental_compliance"] = env_compliance

    def _get_environmental_thresholds(self) -> Dict[str, Any]:
        """Get regulatory environmental thresholds"""
        return {
            "spill_incidents_monthly": 0,  # Zero tolerance for spills
            "spill_volume_monthly_bbls": 1.0,  # Maximum 1 barrel per month
            "air_emissions_annual_tons": 100.0,  # Annual air emissions limit
            "water_discharge_monthly_bbls": 50000,  # Monthly water discharge limit
            "waste_monthly_tons": 25.0,  # Monthly waste generation limit
            "violation_tolerance": 0,  # Zero tolerance for violations
        }

    def _check_environmental_thresholds(
        self, metrics: EnvironmentalMetrics
    ) -> Dict[str, Any]:
        """Check environmental metrics against regulatory thresholds"""
        thresholds = self._get_environmental_thresholds()

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

    def _get_environmental_benchmarks(self) -> Dict[str, Any]:
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

    def _compare_to_benchmarks(self, metrics: EnvironmentalMetrics) -> Dict[str, Any]:
        """Compare environmental performance to industry benchmarks"""
        benchmarks = self._get_environmental_benchmarks()
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
            "performance_percentile": self._calculate_performance_percentile(env_score),
            "improvement_potential": max(
                0, benchmarks["best_in_class"]["environmental_score"] - env_score
            ),
        }

        return comparison

    def _calculate_performance_percentile(self, score: float) -> int:
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

    def _assess_environmental_risks(
        self, metrics: EnvironmentalMetrics
    ) -> Dict[str, Any]:
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
            "risk_score": self._calculate_risk_score(metrics),
            "mitigation_priority": (
                "Immediate"
                if risk_level == "High"
                else "Planned" if risk_level == "Medium" else "Routine"
            ),
        }

    def _calculate_risk_score(self, metrics: EnvironmentalMetrics) -> float:
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

    def _analyze_environmental_trends(
        self, metrics: EnvironmentalMetrics
    ) -> Dict[str, Any]:
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
                    "Monitor closely"
                    if env_score < 0.8
                    else "Continue current practices"
                ),
            },
            "leading_indicators": {
                "spill_frequency": metrics.spill_incidents,
                "violation_frequency": metrics.environmental_violations,
                "emissions_intensity": metrics.air_emissions_tons,
            },
        }

    def _generate_environmental_actions(
        self, metrics: EnvironmentalMetrics
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

    def _calculate_environmental_kpis(
        self, metrics: EnvironmentalMetrics
    ) -> Dict[str, Any]:
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
                "environmental_efficiency": metrics.calculate_environmental_score()
                * 100,
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

    def add_safety_compliance_metrics(self, safety_metrics: SafetyMetrics):
        """Add safety compliance metrics"""
        safety_compliance = {
            "incident_count": safety_metrics.incident_count,
            "lost_time_incidents": safety_metrics.lost_time_incidents,
            "total_recordables": safety_metrics.total_recordables,
            "near_misses": safety_metrics.near_misses,
            "trir": safety_metrics.calculate_trir(),
            "ltir": safety_metrics.calculate_ltir(),
            "safety_score": safety_metrics.calculate_safety_score(),
            "safety_status": safety_metrics.safety_status(),
            "safety_inspections": safety_metrics.safety_inspections,
            "training_hours": safety_metrics.safety_training_hours,
        }

        self.context["safety_compliance"] = safety_compliance

    def add_regulatory_milestone_tracking(self, milestones: List[RegulatoryMilestone]):
        """Add regulatory milestone and deadline tracking"""
        milestone_tracking = {
            "total_milestones": len(milestones),
            "completed": len([m for m in milestones if m.is_completed()]),
            "pending": len(
                [m for m in milestones if not m.is_completed() and not m.is_overdue()]
            ),
            "overdue": len([m for m in milestones if m.is_overdue()]),
            "upcoming_30_days": len(
                [m for m in milestones if 0 <= m.days_until_due() <= 30]
            ),
            "milestones": milestones,
        }

        # Calculate completion rate
        if milestone_tracking["total_milestones"] > 0:
            milestone_tracking["completion_rate"] = (
                milestone_tracking["completed"] / milestone_tracking["total_milestones"]
            ) * 100
        else:
            milestone_tracking["completion_rate"] = 0.0

        self.context["milestone_tracking"] = milestone_tracking

    def generate_compliance_visualizations(
        self, compliance_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate compliance-specific charts and dashboards"""
        charts = {}

        # Compliance Dashboard - Gauge charts for key metrics
        compliance_dashboard = self._create_compliance_dashboard(compliance_data)
        charts["compliance_dashboard"] = compliance_dashboard

        # Production Quota Chart
        if "quota_analysis" in self.context:
            quota_chart = self._create_production_quota_chart()
            charts["production_quota_chart"] = quota_chart

        # Environmental Trends Chart
        if "environmental_compliance" in self.context:
            env_chart = self._create_environmental_trends_chart()
            charts["environmental_trends"] = env_chart

        # Safety Metrics Chart
        if "safety_compliance" in self.context:
            safety_chart = self._create_safety_metrics_chart()
            charts["safety_metrics"] = safety_chart

        # Milestone Timeline
        if "milestone_tracking" in self.context:
            timeline_chart = self._create_milestone_timeline()
            charts["milestone_timeline"] = timeline_chart

        return charts

    def _create_compliance_dashboard(self, compliance_data: Dict[str, Any]) -> str:
        """Create compliance dashboard with gauge charts"""
        # Create subplot with gauge charts
        fig = make_subplots(
            rows=2,
            cols=2,
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}],
                [{"type": "indicator"}, {"type": "indicator"}],
            ],
            subplot_titles=[
                "Production Compliance",
                "Environmental Score",
                "Safety Score",
                "Overall Compliance",
            ],
        )

        # Production Compliance Gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=compliance_data.get("production_compliance", 0),
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Production Compliance (%)"},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 70], "color": "lightgray"},
                        {"range": [70, 90], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
            ),
            row=1,
            col=1,
        )

        # Environmental Score Gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=compliance_data.get("environmental_score", 0) * 100,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Environmental Score (%)"},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "green"},
                    "steps": [
                        {"range": [0, 70], "color": "lightgray"},
                        {"range": [70, 90], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 80,
                    },
                },
            ),
            row=1,
            col=2,
        )

        # Safety Score Gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=compliance_data.get("safety_score", 0) * 100,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Safety Score (%)"},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "orange"},
                    "steps": [
                        {"range": [0, 75], "color": "lightgray"},
                        {"range": [75, 90], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 85,
                    },
                },
            ),
            row=2,
            col=1,
        )

        # Overall Compliance Gauge
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=compliance_data.get("overall_compliance_score", 0) * 100,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Overall Compliance (%)"},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "purple"},
                    "steps": [
                        {"range": [0, 80], "color": "lightgray"},
                        {"range": [80, 95], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
            ),
            row=2,
            col=2,
        )

        fig.update_layout(title="Compliance Dashboard", height=600, showlegend=False)

        return pio.to_html(fig, include_plotlyjs="cdn")

    def _create_production_quota_chart(self) -> str:
        """Create production quota vs actual chart"""
        quota_data = self.context["quota_analysis"]

        categories = ["Oil Production", "Gas Production"]
        quota_values = [
            quota_data["oil_quota"],
            quota_data["gas_quota"] / 1000,
        ]  # Convert gas to Mcf
        actual_values = [quota_data["oil_actual"], quota_data["gas_actual"] / 1000]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(name="Quota", x=categories, y=quota_values, marker_color="lightblue")
        )

        fig.add_trace(
            go.Bar(
                name="Actual", x=categories, y=actual_values, marker_color="darkblue"
            )
        )

        fig.update_layout(
            title="Production Quota vs Actual",
            xaxis_title="Production Type",
            yaxis_title="Volume",
            barmode="group",
            height=400,
        )

        return pio.to_html(fig, include_plotlyjs="cdn")

    def _create_environmental_trends_chart(self) -> str:
        """Create environmental compliance trends chart"""
        # Placeholder data - in real implementation, this would use historical data
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        spill_incidents = [0, 1, 0, 0, 2, 1]
        environmental_scores = [0.95, 0.88, 0.95, 0.95, 0.82, 0.91]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=months,
                y=spill_incidents,
                mode="lines+markers",
                name="Spill Incidents",
                line=dict(color="red"),
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=months,
                y=environmental_scores,
                mode="lines+markers",
                name="Environmental Score",
                line=dict(color="green"),
            ),
            secondary_y=True,
        )

        fig.update_xaxes(title_text="Month")
        fig.update_yaxes(title_text="Spill Incidents", secondary_y=False)
        fig.update_yaxes(title_text="Environmental Score", secondary_y=True)

        fig.update_layout(title="Environmental Compliance Trends", height=400)

        return pio.to_html(fig, include_plotlyjs="cdn")

    def _create_safety_metrics_chart(self) -> str:
        """Create safety metrics chart"""
        safety_data = self.context["safety_compliance"]

        metrics = ["TRIR", "LTIR", "Near Misses", "Safety Score"]
        values = [
            safety_data.get("trir", 0),
            safety_data.get("ltir", 0),
            safety_data.get("near_misses", 0),
            safety_data.get("safety_score", 0) * 100,  # Convert to percentage
        ]

        fig = go.Figure(
            go.Bar(
                x=metrics, y=values, marker_color=["red", "orange", "yellow", "green"]
            )
        )

        fig.update_layout(
            title="Safety Performance Metrics",
            xaxis_title="Metric",
            yaxis_title="Value",
            height=400,
        )

        return pio.to_html(fig, include_plotlyjs="cdn")

    def _create_milestone_timeline(self) -> str:
        """Create regulatory milestone timeline"""
        milestones = self.context["milestone_tracking"]["milestones"]

        if not milestones:
            # Return empty chart if no milestones
            fig = go.Figure()
            fig.update_layout(
                title="Regulatory Milestones Timeline",
                annotations=[
                    dict(text="No milestones to display", showarrow=False, x=0.5, y=0.5)
                ],
            )
            return pio.to_html(fig, include_plotlyjs="cdn")

        # Prepare data for timeline
        milestone_names = [
            m.description[:50] + "..." if len(m.description) > 50 else m.description
            for m in milestones
        ]
        due_dates = [m.due_date for m in milestones if m.due_date]
        completion_dates = [m.completion_date for m in milestones if m.completion_date]

        fig = go.Figure()

        # Add due dates
        if due_dates:
            fig.add_trace(
                go.Scatter(
                    x=due_dates,
                    y=milestone_names[: len(due_dates)],
                    mode="markers",
                    name="Due Date",
                    marker=dict(color="red", size=10, symbol="x"),
                )
            )

        # Add completion dates
        if completion_dates:
            completed_names = [
                milestone_names[i]
                for i, m in enumerate(milestones)
                if m.completion_date
            ]
            fig.add_trace(
                go.Scatter(
                    x=completion_dates,
                    y=completed_names,
                    mode="markers",
                    name="Completed",
                    marker=dict(color="green", size=10, symbol="circle"),
                )
            )

        fig.update_layout(
            title="Regulatory Milestones Timeline",
            xaxis_title="Date",
            yaxis_title="Milestone",
            height=max(400, len(milestones) * 30),
        )

        return pio.to_html(fig, include_plotlyjs="cdn")

    def add_regulatory_references(self):
        """Add comprehensive regulatory reference links and citations"""
        regulatory_references = [
            # Core BSEE Production Regulations
            {
                "category": "Production Reporting",
                "title": "BSEE Production Reporting Requirements",
                "regulation": "30 CFR 250.1160",
                "url": "https://www.bsee.gov/guidance-and-regulations/regulations/30-cfr-250-oil-and-gas-and-sulphur-operations-in-the-ocs/subpart-l-oil-and-gas-production-measurement-surface-commingling-and-security",
                "description": "Requirements for monthly production reporting to BSEE",
                "compliance_area": "production",
                "frequency": "monthly",
                "penalties": "Civil penalties up to $44,539 per day per violation",
            },
            {
                "category": "Production Reporting",
                "title": "Well Production Casing Pressure Requirements",
                "regulation": "30 CFR 250.804",
                "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-H/section-250.804",
                "description": "Requirements for monitoring and reporting well casing pressures",
                "compliance_area": "production",
                "frequency": "continuous_monitoring",
                "penalties": "Shutdown orders and civil penalties",
            },
            # Environmental Compliance Regulations
            {
                "category": "Environmental Compliance",
                "title": "Environmental Compliance Requirements",
                "regulation": "30 CFR 250.300",
                "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-C",
                "description": "Environmental compliance and pollution prevention requirements",
                "compliance_area": "environmental",
                "frequency": "ongoing",
                "penalties": "Civil penalties and operational restrictions",
            },
            {
                "category": "Environmental Compliance",
                "title": "Spill Response and Reporting",
                "regulation": "30 CFR 254",
                "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-254",
                "description": "Oil spill response planning and incident reporting requirements",
                "compliance_area": "environmental",
                "frequency": "immediate_reporting",
                "penalties": "Civil penalties up to $44,539 per day per violation",
            },
            {
                "category": "Environmental Compliance",
                "title": "Air Quality Requirements",
                "regulation": "40 CFR 60 Subpart OOOO",
                "url": "https://www.ecfr.gov/current/title-40/chapter-I/subchapter-C/part-60/subpart-OOOO",
                "description": "Standards of performance for crude oil and natural gas facilities",
                "compliance_area": "environmental",
                "frequency": "ongoing_monitoring",
                "penalties": "EPA civil penalties up to $37,500 per day per violation",
            },
            # Safety and Management System Regulations
            {
                "category": "Safety Management",
                "title": "Safety and Environmental Management System (SEMS)",
                "regulation": "30 CFR 250.1900",
                "url": "https://www.bsee.gov/what-we-do/offshore-regulatory-programs/sems",
                "description": "Safety and Environmental Management System requirements",
                "compliance_area": "safety",
                "frequency": "annual_audit",
                "penalties": "Operational shutdowns and civil penalties",
            },
            {
                "category": "Safety Management",
                "title": "Incident Reporting Requirements",
                "regulation": "30 CFR 250.188",
                "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-B/section-250.188",
                "description": "Requirements for reporting incidents and accidents",
                "compliance_area": "safety",
                "frequency": "immediate_reporting",
                "penalties": "Civil penalties and potential criminal liability",
            },
            # Financial Assurance and Bonding
            {
                "category": "Financial Assurance",
                "title": "Supplemental Bonding Requirements",
                "regulation": "30 CFR 250.1700",
                "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-Q",
                "description": "Financial assurance requirements for offshore operations",
                "compliance_area": "financial",
                "frequency": "periodic_review",
                "penalties": "Lease cancellation and forfeiture",
            },
            # Inspection and Enforcement
            {
                "category": "Inspection and Enforcement",
                "title": "Inspection Requirements and Procedures",
                "regulation": "30 CFR 250.130",
                "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-250/subpart-B/section-250.130",
                "description": "BSEE inspection authority and facility access requirements",
                "compliance_area": "operational",
                "frequency": "unscheduled",
                "penalties": "Operational restrictions and civil penalties",
            },
            {
                "category": "Inspection and Enforcement",
                "title": "Civil Penalty Procedures",
                "regulation": "30 CFR 550.1400",
                "url": "https://www.ecfr.gov/current/title-30/chapter-II/subchapter-B/part-550/subpart-N",
                "description": "Civil penalty assessment and appeal procedures",
                "compliance_area": "enforcement",
                "frequency": "as_needed",
                "penalties": "Varies by violation type and severity",
            },
        ]

        # Add quick reference guides
        quick_references = [
            {
                "category": "Quick Reference",
                "title": "BSEE Compliance Checklist",
                "regulation": "BSEE Guidance",
                "url": "https://www.bsee.gov/sites/bsee.gov/files/guidance-and-regulations/guidance/notices-to-lessees-ntl/bsee-compliance-checklist.pdf",
                "description": "Comprehensive compliance checklist for offshore operations",
                "compliance_area": "all",
                "frequency": "reference_document",
            },
            {
                "category": "Quick Reference",
                "title": "Emergency Contact Information",
                "regulation": "BSEE Emergency Response",
                "url": "https://www.bsee.gov/what-we-do/emergency-response",
                "description": "Emergency contact information and reporting procedures",
                "compliance_area": "emergency",
                "frequency": "immediate_access",
            },
        ]

        all_references = regulatory_references + quick_references

        # Add metadata about references
        reference_metadata = {
            "total_references": len(all_references),
            "categories": list(set([ref["category"] for ref in all_references])),
            "compliance_areas": list(
                set(
                    [
                        ref["compliance_area"]
                        for ref in all_references
                        if ref.get("compliance_area")
                    ]
                )
            ),
            "last_updated": datetime.now().isoformat(),
            "disclaimer": "Regulatory references are provided for guidance only. Always consult current CFR text and legal counsel for authoritative interpretation.",
        }

        self.context["regulatory_references"] = all_references
        self.context["reference_metadata"] = reference_metadata

    def get_compliance_status_color(self, score: float) -> str:
        """Get color code for compliance status"""
        if score >= 0.9:
            return "#4CAF50"  # Green
        elif score >= 0.8:
            return "#FF9800"  # Orange
        elif score >= 0.7:
            return "#FFC107"  # Yellow
        else:
            return "#F44336"  # Red

    def generate_compliance_report_sections(self) -> Dict[str, Any]:
        """Generate all compliance report sections"""
        sections = {}

        # Executive Summary
        sections["executive_summary"] = self._generate_executive_summary()

        # Production Compliance Section
        if self.compliance_sections["production_compliance"]:
            sections["production_compliance"] = (
                self._generate_production_compliance_section()
            )

        # Environmental Compliance Section
        if self.compliance_sections["environmental_compliance"]:
            sections["environmental_compliance"] = (
                self._generate_environmental_section()
            )

        # Safety Compliance Section
        if self.compliance_sections["safety_compliance"]:
            sections["safety_compliance"] = self._generate_safety_section()

        # Regulatory Milestones Section
        if self.compliance_sections["regulatory_milestones"]:
            sections["regulatory_milestones"] = self._generate_milestones_section()

        return sections

    def _generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary section"""
        summary = self.context.get("compliance_summary", {})

        return {
            "overall_status": summary.get("overall_status", "Unknown"),
            "key_metrics": {
                "production_compliance": f"{summary.get('production_compliance', 0):.1f}%",
                "environmental_score": f"{summary.get('environmental_score', 0)*100:.1f}%",
                "safety_score": f"{summary.get('safety_score', 0)*100:.1f}%",
                "regulatory_violations": summary.get("regulatory_violations", 0),
            },
            "recommendations": self._generate_recommendations(summary),
        }

    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
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

    def _generate_production_compliance_section(self) -> Dict[str, Any]:
        """Generate production compliance section"""
        compliance = self.context.get("compliance_metrics")
        quota_analysis = self.context.get("quota_analysis", {})

        return {
            "permitted_production": (
                compliance.permitted_production_bbls if compliance else 0
            ),
            "actual_production": compliance.actual_production_bbls if compliance else 0,
            "compliance_percentage": (
                compliance.production_compliance_percentage() if compliance else 0
            ),
            "quota_analysis": quota_analysis,
            "status": (
                compliance.overall_compliance_status() if compliance else "Unknown"
            ),
        }

    def _generate_environmental_section(self) -> Dict[str, Any]:
        """Generate environmental compliance section"""
        return self.context.get("environmental_compliance", {})

    def _generate_safety_section(self) -> Dict[str, Any]:
        """Generate safety compliance section"""
        return self.context.get("safety_compliance", {})

    def _generate_milestones_section(self) -> Dict[str, Any]:
        """Generate regulatory milestones section"""
        return self.context.get("milestone_tracking", {})
