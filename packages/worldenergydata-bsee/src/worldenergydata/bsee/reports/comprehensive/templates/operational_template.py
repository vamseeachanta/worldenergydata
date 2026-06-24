"""
Operational Template for BSEE operational performance reporting.

This module provides comprehensive operational reporting including:
- Well status and performance tracking
- Production efficiency metrics
- Equipment utilization and reliability
- Maintenance scheduling and tracking
- Failure analysis and root cause tracking
- Operational KPI dashboards

This module serves as the main entry point and re-exports all public
names from the split submodules for backward compatibility.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from .base import BaseReportTemplate

# Import calculation functions
from .operational_calculations import (
    add_completion_efficiency_metrics,
    add_drilling_performance_analysis,
    add_equipment_utilization_analysis,
    add_production_optimization_tracking,
    calculate_operational_kpis,
)

# Import chart generation functions
from .operational_charts import (
    create_efficiency_gauge,
    create_failure_chart,
    create_kpi_dashboard,
    create_reliability_chart,
    create_well_status_chart,
    generate_operational_visualizations,
)

# Import context building functions
from .operational_context import (
    add_equipment_reliability_analysis,
    add_failure_analysis,
    add_maintenance_schedule,
    add_operational_summary,
    add_production_efficiency_analysis,
    add_well_performance_analysis,
    format_kpis,
)

# Import all models for re-export
from .operational_models import (
    EquipmentMetrics,
    FailureAnalysis,
    MaintenanceRecord,
    OperationalKPI,
    ProductionEfficiencyMetrics,
    WellOperationalMetrics,
    WellStatus,
)


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
        add_operational_summary(
            context, well_metrics, production_metrics, equipment_metrics
        )

        # Add well performance analysis
        add_well_performance_analysis(context, well_metrics)

        # Add production efficiency metrics
        if production_metrics:
            add_production_efficiency_analysis(context, production_metrics)

        # Add equipment reliability analysis
        if equipment_metrics:
            add_equipment_reliability_analysis(context, equipment_metrics)

        # Add maintenance schedule
        if maintenance_records:
            add_maintenance_schedule(context, maintenance_records)

        # Add failure analysis
        if failure_records:
            add_failure_analysis(context, failure_records)

        # Calculate and add operational KPIs
        kpis = calculate_operational_kpis(
            well_metrics, production_metrics, equipment_metrics
        )
        context["operational_kpis"] = format_kpis(kpis)

        # Add any additional context
        context.update(kwargs)

        return context

    # Delegate methods to module functions for backward compatibility
    def _add_operational_summary(
        self,
        context: Dict[str, Any],
        well_metrics: List[WellOperationalMetrics],
        production_metrics: Optional[ProductionEfficiencyMetrics],
        equipment_metrics: Optional[List[EquipmentMetrics]],
    ):
        """Add operational summary to context (delegated)"""
        add_operational_summary(
            context, well_metrics, production_metrics, equipment_metrics
        )

    def _add_well_performance_analysis(
        self, context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
    ):
        """Add well performance analysis to context (delegated)"""
        add_well_performance_analysis(context, well_metrics)

    def _add_production_efficiency_analysis(
        self, context: Dict[str, Any], production_metrics: ProductionEfficiencyMetrics
    ):
        """Add production efficiency analysis to context (delegated)"""
        add_production_efficiency_analysis(context, production_metrics)

    def _add_equipment_reliability_analysis(
        self, context: Dict[str, Any], equipment_metrics: List[EquipmentMetrics]
    ):
        """Add equipment reliability analysis to context (delegated)"""
        add_equipment_reliability_analysis(context, equipment_metrics)

    def _add_maintenance_schedule(
        self, context: Dict[str, Any], maintenance_records: List[MaintenanceRecord]
    ):
        """Add maintenance schedule to context (delegated)"""
        add_maintenance_schedule(context, maintenance_records)

    def _add_failure_analysis(
        self, context: Dict[str, Any], failure_records: List[FailureAnalysis]
    ):
        """Add failure analysis to context (delegated)"""
        add_failure_analysis(context, failure_records)

    def _format_kpis(self, kpis: List[OperationalKPI]) -> List[Dict[str, Any]]:
        """Format KPIs for template rendering (delegated)"""
        return format_kpis(kpis)

    def add_drilling_performance_analysis(
        self, context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
    ):
        """Add detailed drilling performance analysis (delegated)"""
        add_drilling_performance_analysis(context, well_metrics)

    def add_completion_efficiency_metrics(
        self, context: Dict[str, Any], well_metrics: List[WellOperationalMetrics]
    ):
        """Add completion efficiency metrics (delegated)"""
        add_completion_efficiency_metrics(context, well_metrics)

    def add_production_optimization_tracking(
        self, context: Dict[str, Any], production_metrics: ProductionEfficiencyMetrics
    ):
        """Add production optimization tracking (delegated)"""
        add_production_optimization_tracking(context, production_metrics)

    def add_equipment_utilization_analysis(
        self, context: Dict[str, Any], equipment_metrics: List[EquipmentMetrics]
    ):
        """Add detailed equipment utilization analysis (delegated)"""
        add_equipment_utilization_analysis(context, equipment_metrics)

    def calculate_operational_kpis(
        self,
        well_metrics: List[WellOperationalMetrics],
        production_metrics: Optional[ProductionEfficiencyMetrics] = None,
        equipment_metrics: Optional[List[EquipmentMetrics]] = None,
    ) -> List[OperationalKPI]:
        """Calculate operational KPIs from metrics (delegated)"""
        return calculate_operational_kpis(
            well_metrics, production_metrics, equipment_metrics
        )

    def generate_operational_visualizations(
        self, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate operational visualizations using Plotly (delegated)"""
        return generate_operational_visualizations(context)

    def _create_well_status_chart(self, summary: Dict[str, Any]) -> str:
        """Create well status distribution pie chart (delegated)"""
        return create_well_status_chart(summary)

    def _create_efficiency_gauge(self, efficiency: Dict[str, Any]) -> str:
        """Create production efficiency gauge chart (delegated)"""
        return create_efficiency_gauge(efficiency)

    def _create_reliability_chart(self, reliability: Dict[str, Any]) -> str:
        """Create equipment reliability bar chart (delegated)"""
        return create_reliability_chart(reliability)

    def _create_kpi_dashboard(self, kpis: List[Dict[str, Any]]) -> str:
        """Create KPI dashboard with multiple indicators (delegated)"""
        return create_kpi_dashboard(kpis)

    def _create_failure_chart(self, failures: Dict[str, Any]) -> str:
        """Create failure analysis chart (delegated)"""
        return create_failure_chart(failures)

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


# Re-export all public names for backward compatibility
__all__ = [
    # Models
    "WellStatus",
    "WellOperationalMetrics",
    "ProductionEfficiencyMetrics",
    "EquipmentMetrics",
    "MaintenanceRecord",
    "FailureAnalysis",
    "OperationalKPI",
    # Main class
    "OperationalTemplate",
    # Calculation functions (for direct use)
    "calculate_operational_kpis",
    "add_drilling_performance_analysis",
    "add_completion_efficiency_metrics",
    "add_production_optimization_tracking",
    "add_equipment_utilization_analysis",
    # Context functions (for direct use)
    "add_operational_summary",
    "add_well_performance_analysis",
    "add_production_efficiency_analysis",
    "add_equipment_reliability_analysis",
    "add_maintenance_schedule",
    "add_failure_analysis",
    "format_kpis",
    # Chart functions (for direct use)
    "create_well_status_chart",
    "create_efficiency_gauge",
    "create_reliability_chart",
    "create_kpi_dashboard",
    "create_failure_chart",
    "generate_operational_visualizations",
]
