"""
Executive Dashboard Generation.

This module provides dashboard layout, component creation, and export
configuration for executive reporting dashboards.
"""

from typing import Dict, List

from .executive_charts import (
    PLOTLY_AVAILABLE,
    create_kpi_summary_chart,
    create_trend_chart,
    get_status_color,
)
from .executive_models import ExecutiveDashboard


class ExecutiveDashboardBuilder:
    """
    Builder for executive dashboards.

    Provides methods for creating dashboard components, configuring
    layouts, and generating complete dashboard views.
    """

    def __init__(self):
        """Initialize dashboard builder."""
        pass

    def generate_executive_dashboard(self, data: Dict) -> ExecutiveDashboard:
        """
        Generate executive dashboard.

        Args:
            data: Dashboard data with 'kpis' and 'trends' keys

        Returns:
            ExecutiveDashboard object
        """
        if not PLOTLY_AVAILABLE:
            return ExecutiveDashboard(
                layout={},
                charts=[],
                components={"error": "Plotly not available"},
                export_config={},
            )

        # Create dashboard components
        components = {
            "kpi_grid": self._create_kpi_grid(data.get("kpis", [])),
            "traffic_lights": self._create_traffic_lights(data.get("kpis", [])),
            "trend_charts": self._create_trend_charts(data.get("trends", {})),
        }

        # Create charts
        charts = []

        # KPI summary chart
        if "kpis" in data:
            chart = create_kpi_summary_chart(data["kpis"])
            if chart:
                charts.append(chart)

        # Trend charts
        if "trends" in data:
            for metric, values in data["trends"].items():
                if metric != "periods":
                    chart = create_trend_chart(
                        metric, values, data["trends"].get("periods", [])
                    )
                    if chart:
                        charts.append(chart)

        # Layout configuration
        layout = self.get_dashboard_layout_config()

        # Export configuration
        export_config = self.get_dashboard_export_config()

        return ExecutiveDashboard(
            layout=layout,
            charts=charts,
            components=components,
            export_config=export_config,
        )

    def _create_kpi_grid(self, kpis: List[Dict]) -> Dict:
        """
        Create KPI grid component.

        Args:
            kpis: List of KPI dictionaries

        Returns:
            KPI grid configuration
        """
        return {
            "type": "grid",
            "kpis": kpis,
            "layout": {"rows": 2, "cols": 3, "spacing": 10},
        }

    def _create_traffic_lights(self, kpis: List[Dict]) -> List[Dict]:
        """
        Create traffic light indicators.

        Args:
            kpis: List of KPI dictionaries

        Returns:
            List of traffic light configurations
        """
        traffic_lights = []

        for kpi in kpis:
            if "status" in kpi:
                traffic_lights.append(
                    {
                        "name": kpi["name"],
                        "status": kpi["status"],
                        "value": kpi.get("value"),
                        "color": get_status_color(kpi["status"]),
                    }
                )

        return traffic_lights

    def _create_trend_charts(self, trends: Dict) -> List[Dict]:
        """
        Create trend chart configurations.

        Args:
            trends: Dictionary of trend data

        Returns:
            List of trend chart configurations
        """
        charts = []

        for metric, values in trends.items():
            if metric != "periods" and isinstance(values, list):
                charts.append(
                    {
                        "metric": metric,
                        "values": values,
                        "periods": trends.get("periods", []),
                    }
                )

        return charts

    def get_dashboard_layout_config(self) -> Dict:
        """
        Get dashboard layout configuration.

        Returns:
            Layout configuration dictionary
        """
        return {
            "grid_rows": 3,
            "grid_cols": 4,
            "component_positions": {
                "kpi_summary": {"row": 1, "col": 1, "colspan": 4},
                "traffic_lights": {"row": 2, "col": 1, "colspan": 2},
                "trend_chart": {"row": 2, "col": 3, "colspan": 2},
                "details": {"row": 3, "col": 1, "colspan": 4},
            },
            "spacing": {"horizontal": 0.05, "vertical": 0.1},
        }

    def get_dashboard_export_config(self) -> Dict:
        """
        Get dashboard export configuration.

        Returns:
            Export configuration dictionary
        """
        return {
            "width": 1920,
            "height": 1080,
            "scale": 2,
            "format": "png",
            "formats_available": ["png", "pdf", "svg"],
            "quality": "high",
        }
