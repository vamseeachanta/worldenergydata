"""
Compliance Template for regulatory compliance reporting.

Implements BSEE regulatory compliance sections and metrics.
This module serves as the main entry point, importing from specialized submodules.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import ProductionMetrics
from .base import BaseReportTemplate

# Import calculation functions
from .compliance_calculations import (
    analyze_environmental_trends,
    assess_environmental_risks,
    calculate_environmental_kpis,
    calculate_performance_percentile,
    calculate_risk_score,
    check_environmental_thresholds,
    compare_to_benchmarks,
    generate_environmental_actions,
    generate_recommendations,
    get_compliance_status_color,
    get_environmental_benchmarks,
    get_environmental_thresholds,
)

# Import chart generation functions
from .compliance_charts import (
    create_compliance_dashboard,
    create_environmental_trends_chart,
    create_milestone_timeline,
    create_production_quota_chart,
    create_safety_metrics_chart,
)

# Import data models (re-exported for backward compatibility)
from .compliance_models import (
    ComplianceMetrics,
    EnvironmentalMetrics,
    ProductionQuota,
    RegulatoryMilestone,
    SafetyMetrics,
)

# Import regulatory reference functions
from .compliance_references import (
    get_all_references,
    get_quick_references,
    get_reference_metadata,
    get_regulatory_references,
)


class ComplianceTemplate(BaseReportTemplate):
    """
    Compliance Template for BSEE regulatory compliance reporting.

    Implements regulatory sections including production quotas, environmental compliance,
    safety metrics, and regulatory milestone tracking.
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
        env_compliance["regulatory_thresholds"] = get_environmental_thresholds()
        env_compliance["threshold_compliance"] = check_environmental_thresholds(
            environmental_metrics
        )

        # Add environmental performance benchmarks
        env_compliance["benchmarks"] = get_environmental_benchmarks()
        env_compliance["benchmark_comparison"] = compare_to_benchmarks(
            environmental_metrics
        )

        # Add environmental risk assessment
        env_compliance["risk_assessment"] = assess_environmental_risks(
            environmental_metrics
        )

        # Add compliance trends with historical analysis
        env_compliance["trends"] = analyze_environmental_trends(environmental_metrics)

        # Add corrective actions and recommendations
        env_compliance["corrective_actions"] = generate_environmental_actions(
            environmental_metrics
        )

        # Add environmental KPIs
        env_compliance["kpis"] = calculate_environmental_kpis(environmental_metrics)

        self.context["environmental_compliance"] = env_compliance

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
        charts["compliance_dashboard"] = create_compliance_dashboard(compliance_data)

        # Production Quota Chart
        if "quota_analysis" in self.context:
            charts["production_quota_chart"] = create_production_quota_chart(
                self.context["quota_analysis"]
            )

        # Environmental Trends Chart
        if "environmental_compliance" in self.context:
            charts["environmental_trends"] = create_environmental_trends_chart()

        # Safety Metrics Chart
        if "safety_compliance" in self.context:
            charts["safety_metrics"] = create_safety_metrics_chart(
                self.context["safety_compliance"]
            )

        # Milestone Timeline
        if "milestone_tracking" in self.context:
            charts["milestone_timeline"] = create_milestone_timeline(
                self.context["milestone_tracking"]["milestones"]
            )

        return charts

    def add_regulatory_references(self):
        """Add comprehensive regulatory reference links and citations"""
        all_references = get_all_references()
        reference_metadata = get_reference_metadata(all_references)

        self.context["regulatory_references"] = all_references
        self.context["reference_metadata"] = reference_metadata

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
            "recommendations": generate_recommendations(summary),
        }

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


# Re-export for backward compatibility
__all__ = [
    # Main class
    "ComplianceTemplate",
    # Data models
    "ComplianceMetrics",
    "EnvironmentalMetrics",
    "SafetyMetrics",
    "ProductionQuota",
    "RegulatoryMilestone",
    # Calculation functions
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
    # Chart functions
    "create_compliance_dashboard",
    "create_production_quota_chart",
    "create_environmental_trends_chart",
    "create_safety_metrics_chart",
    "create_milestone_timeline",
    # Reference functions
    "get_regulatory_references",
    "get_quick_references",
    "get_all_references",
    "get_reference_metadata",
]
