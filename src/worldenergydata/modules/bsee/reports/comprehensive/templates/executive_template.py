"""
Executive Template for Comprehensive Report System.

This module provides executive-level reporting with KPIs, strategic metrics,
traffic light indicators, and competitive benchmarking.

This is the main entry point that re-exports all executive template
components for backward compatibility. The implementation is split across:
- executive_models.py: Data classes and enumerations
- executive_charts.py: Chart generation functions
- executive_calculations.py: KPI and metric calculations
- executive_dashboard.py: Dashboard generation
- executive_benchmarks.py: Competitive analysis
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseReportTemplate
from .executive_benchmarks import ExecutiveBenchmarking

# Import calculation and dashboard builders
from .executive_calculations import ExecutiveCalculations

# Re-export chart functions
from .executive_charts import (
    PLOTLY_AVAILABLE,
    create_benchmark_radar_chart,
    create_executive_summary_chart,
    create_kpi_gauge_chart,
    create_kpi_summary_chart,
    create_multi_panel_dashboard,
    create_traffic_light_grid,
    create_trend_chart,
    create_trend_sparkline,
    get_status_color,
)
from .executive_dashboard import ExecutiveDashboardBuilder
from .executive_kpi_generator import KPIGenerator

# Re-export all models for backward compatibility
from .executive_models import (
    BusinessHighlight,
    ExecutiveChart,
    ExecutiveDashboard,
    ExecutiveKPI,
    ExecutiveSummary,
    KPIStatus,
    PerformanceScore,
    RiskIndicator,
    StrategicInitiative,
    StrategicMetric,
    TrafficLightIndicator,
    TrendDirection,
)


class ExecutiveTemplate(BaseReportTemplate):
    """
    Executive template for high-level reporting.

    Provides KPIs, strategic metrics, traffic light indicators,
    and competitive benchmarking for executive decision-making.

    This class delegates to specialized components:
    - ExecutiveCalculations: KPI generation and analysis
    - ExecutiveDashboardBuilder: Dashboard creation
    - ExecutiveBenchmarking: Competitive analysis
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize executive template."""
        super().__init__(
            template_name="executive", template_type="executive", version="1.0.0"
        )
        self.config = config or {}
        self.kpi_thresholds = self._load_kpi_thresholds()
        self.benchmarks = self._load_industry_benchmarks()

        # Initialize component handlers
        self._calculations = ExecutiveCalculations(
            kpi_thresholds=self.kpi_thresholds, benchmarks=self.benchmarks
        )
        self._dashboard_builder = ExecutiveDashboardBuilder()
        self._benchmarking = ExecutiveBenchmarking(industry_benchmarks=self.benchmarks)

    def _load_kpi_thresholds(self) -> Dict:
        """Load KPI threshold configurations."""
        return self.config.get(
            "kpi_thresholds",
            {
                "uptime": {"green": 95, "yellow": 90},
                "efficiency": {"green": 85, "yellow": 80},
                "safety_trir": {"green": 0.5, "yellow": 1.0},
                "emissions_intensity": {"green": 15, "yellow": 20},
                "roi": {"green": 20, "yellow": 15},
                "npv": {"green": 0, "yellow": -1000000},
            },
        )

    def _load_industry_benchmarks(self) -> Dict:
        """Load industry benchmark data."""
        return self.config.get(
            "benchmarks",
            {
                "uptime": 92.0,
                "efficiency": 85.0,
                "safety_trir": 0.75,
                "emissions_intensity": 18.0,
                "operating_cost_per_boe": 28.0,
                "finding_cost_per_boe": 15.0,
            },
        )

    # Delegate KPI and calculation methods to ExecutiveCalculations
    def generate_executive_kpis(self, data: Dict) -> List[ExecutiveKPI]:
        """Generate executive KPIs from report data."""
        return self._calculations.generate_executive_kpis(data)

    def determine_kpi_status(self, value: float, target: float) -> str:
        """Determine KPI status (green/yellow/red)."""
        return self._calculations.determine_kpi_status(value, target)

    def analyze_kpi_trend(self, values: List[float]) -> str:
        """Analyze KPI trend over time."""
        return self._calculations.analyze_kpi_trend(values)

    def calculate_performance_score(self, kpis: List[ExecutiveKPI]) -> PerformanceScore:
        """Calculate overall performance score from KPIs."""
        return self._calculations.calculate_performance_score(kpis)

    def calculate_strategic_metrics(self, data: Dict) -> List[StrategicMetric]:
        """Calculate strategic business metrics."""
        return self._calculations.calculate_strategic_metrics(data)

    def compare_with_benchmarks(self, data: Dict, benchmarks: Dict) -> Dict:
        """Compare KPIs with industry benchmarks."""
        return self._calculations.compare_with_benchmarks(data, benchmarks)

    def rank_kpis_by_priority(self, kpis: List[ExecutiveKPI]) -> List[ExecutiveKPI]:
        """Rank KPIs by priority."""
        return self._calculations.rank_kpis_by_priority(kpis)

    def analyze_year_over_year(self, data: Dict) -> Dict:
        """Analyze year-over-year metrics."""
        return self._calculations.analyze_year_over_year(data)

    def generate_strategic_forecast(
        self, historical_data: pd.DataFrame, periods: int = 3
    ) -> Dict:
        """Generate strategic forecast."""
        return self._calculations.generate_strategic_forecast(historical_data, periods)

    def track_strategic_goals(self, goals: List[Dict]) -> List[Dict]:
        """Track strategic goals progress."""
        return self._calculations.track_strategic_goals(goals)

    def determine_traffic_light_status(
        self, value: float, green_threshold: float, yellow_threshold: float
    ) -> str:
        """Determine traffic light status."""
        return self._calculations.determine_traffic_light_status(
            value, green_threshold, yellow_threshold
        )

    # Delegate dashboard methods to ExecutiveDashboardBuilder
    def generate_executive_dashboard(self, data: Dict) -> ExecutiveDashboard:
        """Generate executive dashboard."""
        return self._dashboard_builder.generate_executive_dashboard(data)

    def get_dashboard_layout_config(self) -> Dict:
        """Get dashboard layout configuration."""
        return self._dashboard_builder.get_dashboard_layout_config()

    def get_dashboard_export_config(self) -> Dict:
        """Get dashboard export configuration."""
        return self._dashboard_builder.get_dashboard_export_config()

    # Chart creation methods - delegate to module functions
    def create_kpi_gauge_chart(self, kpi_data: Dict) -> Any:
        """Create KPI gauge chart."""
        return create_kpi_gauge_chart(kpi_data)

    def create_trend_sparkline(self, trend_data: Dict) -> Any:
        """Create trend sparkline."""
        return create_trend_sparkline(trend_data)

    def create_executive_summary_chart(self, summary_data: Dict) -> Any:
        """Create executive summary chart."""
        return create_executive_summary_chart(summary_data)

    def create_traffic_light_grid(self, metrics: List[Dict]) -> Any:
        """Create traffic light grid visualization."""
        return create_traffic_light_grid(metrics)

    def create_multi_panel_dashboard(self, panels: List[Dict], data: Dict) -> Any:
        """Create multi-panel executive dashboard."""
        return create_multi_panel_dashboard(panels, data)

    def create_benchmark_radar_chart(self, benchmark_data: Dict) -> Any:
        """Create competitive benchmark radar chart."""
        return create_benchmark_radar_chart(benchmark_data)

    # Delegate benchmarking methods to ExecutiveBenchmarking
    def analyze_competitive_position(self, benchmark_data: Dict) -> Dict:
        """Analyze competitive positioning."""
        return self._benchmarking.analyze_competitive_position(benchmark_data)

    def generate_peer_ranking_table(self, peer_companies: List[Dict]) -> List[Dict]:
        """Generate peer ranking table."""
        return self._benchmarking.generate_peer_ranking_table(peer_companies)

    # Private helper methods kept for internal use
    def _calculate_trend(self, history: List[float]) -> str:
        """Calculate trend from historical data."""
        return self._calculations.calculate_trend(history)

    def _get_status_color(self, status: str) -> str:
        """Get color for status."""
        return get_status_color(status)

    def render(self, context: Dict) -> str:
        """
        Render the executive template.

        Args:
            context: Report context data

        Returns:
            Rendered report content
        """
        # Generate executive components
        context["executive_kpis"] = self.generate_executive_kpis(context)
        context["performance_score"] = self.calculate_performance_score(
            context["executive_kpis"]
        )

        # Generate strategic metrics if data available
        if "strategic_data" in context:
            context["strategic_metrics"] = self.calculate_strategic_metrics(
                context["strategic_data"]
            )

        # Generate dashboard if requested
        if context.get("include_dashboard", True):
            dashboard_data = {
                "kpis": [kpi.to_dict() for kpi in context["executive_kpis"]],
                "trends": context.get("trends", {}),
            }
            context["dashboard"] = self.generate_executive_dashboard(dashboard_data)

        # Render using base template
        return super().render(context)


# Backward compatibility: expose internal methods that were previously accessible
# These allow existing code to continue working without modification
__all__ = [
    # Main class
    "ExecutiveTemplate",
    # Models
    "KPIStatus",
    "TrendDirection",
    "ExecutiveKPI",
    "StrategicMetric",
    "PerformanceScore",
    "ExecutiveSummary",
    "BusinessHighlight",
    "RiskIndicator",
    "StrategicInitiative",
    "TrafficLightIndicator",
    "ExecutiveDashboard",
    "ExecutiveChart",
    # Chart functions
    "PLOTLY_AVAILABLE",
    "get_status_color",
    "create_kpi_summary_chart",
    "create_trend_chart",
    "create_kpi_gauge_chart",
    "create_trend_sparkline",
    "create_executive_summary_chart",
    "create_traffic_light_grid",
    "create_multi_panel_dashboard",
    "create_benchmark_radar_chart",
    # Component classes
    "ExecutiveCalculations",
    "ExecutiveDashboardBuilder",
    "ExecutiveBenchmarking",
    "KPIGenerator",
]
