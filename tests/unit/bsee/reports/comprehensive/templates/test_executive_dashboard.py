"""Tests for executive_dashboard ExecutiveDashboardBuilder."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.executive_dashboard import (
    ExecutiveDashboardBuilder,
)


class TestExecutiveDashboardBuilderInit:
    def test_init(self):
        builder = ExecutiveDashboardBuilder()
        assert builder is not None


class TestGetDashboardLayoutConfig:
    def test_returns_dict(self):
        builder = ExecutiveDashboardBuilder()
        layout = builder.get_dashboard_layout_config()
        assert isinstance(layout, dict)
        assert layout["grid_rows"] == 3
        assert layout["grid_cols"] == 4
        assert "component_positions" in layout
        assert "spacing" in layout

    def test_component_positions(self):
        builder = ExecutiveDashboardBuilder()
        layout = builder.get_dashboard_layout_config()
        positions = layout["component_positions"]
        assert "kpi_summary" in positions
        assert "traffic_lights" in positions
        assert "trend_chart" in positions
        assert "details" in positions


class TestGetDashboardExportConfig:
    def test_returns_dict(self):
        builder = ExecutiveDashboardBuilder()
        config = builder.get_dashboard_export_config()
        assert isinstance(config, dict)
        assert config["width"] == 1920
        assert config["height"] == 1080
        assert config["format"] == "png"
        assert "png" in config["formats_available"]
        assert "pdf" in config["formats_available"]
        assert "svg" in config["formats_available"]


class TestCreateKpiGrid:
    def test_empty_kpis(self):
        builder = ExecutiveDashboardBuilder()
        grid = builder._create_kpi_grid([])
        assert grid["type"] == "grid"
        assert grid["kpis"] == []
        assert grid["layout"]["rows"] == 2

    def test_with_kpis(self):
        builder = ExecutiveDashboardBuilder()
        kpis = [{"name": "Revenue", "value": 100}, {"name": "Cost", "value": 50}]
        grid = builder._create_kpi_grid(kpis)
        assert len(grid["kpis"]) == 2


class TestCreateTrafficLights:
    def test_empty_kpis(self):
        builder = ExecutiveDashboardBuilder()
        lights = builder._create_traffic_lights([])
        assert lights == []

    def test_kpis_with_status(self):
        builder = ExecutiveDashboardBuilder()
        kpis = [
            {"name": "Revenue", "value": 100, "status": "good"},
            {"name": "Cost", "value": 50, "status": "warning"},
        ]
        lights = builder._create_traffic_lights(kpis)
        assert len(lights) == 2
        assert lights[0]["name"] == "Revenue"
        assert lights[0]["status"] == "good"
        assert "color" in lights[0]

    def test_kpis_without_status_skipped(self):
        builder = ExecutiveDashboardBuilder()
        kpis = [{"name": "Revenue", "value": 100}]
        lights = builder._create_traffic_lights(kpis)
        assert lights == []


class TestCreateTrendCharts:
    def test_empty_trends(self):
        builder = ExecutiveDashboardBuilder()
        charts = builder._create_trend_charts({})
        assert charts == []

    def test_with_trends(self):
        builder = ExecutiveDashboardBuilder()
        trends = {
            "periods": ["Q1", "Q2", "Q3"],
            "revenue": [100, 200, 300],
            "costs": [50, 60, 70],
        }
        charts = builder._create_trend_charts(trends)
        assert len(charts) == 2  # revenue and costs, not periods
        metrics = [c["metric"] for c in charts]
        assert "revenue" in metrics
        assert "costs" in metrics
        assert charts[0]["periods"] == ["Q1", "Q2", "Q3"]

    def test_skips_periods_key(self):
        builder = ExecutiveDashboardBuilder()
        trends = {"periods": ["Q1"], "revenue": [100]}
        charts = builder._create_trend_charts(trends)
        metrics = [c["metric"] for c in charts]
        assert "periods" not in metrics

    def test_skips_non_list_values(self):
        builder = ExecutiveDashboardBuilder()
        trends = {"revenue": "not_a_list", "costs": [100]}
        charts = builder._create_trend_charts(trends)
        metrics = [c["metric"] for c in charts]
        assert "revenue" not in metrics
        assert "costs" in metrics


class TestGenerateExecutiveDashboard:
    def test_empty_data(self):
        builder = ExecutiveDashboardBuilder()
        dashboard = builder.generate_executive_dashboard({})
        assert dashboard is not None
        assert hasattr(dashboard, "layout")
        assert hasattr(dashboard, "charts")
        assert hasattr(dashboard, "components")

    def test_with_kpis(self):
        builder = ExecutiveDashboardBuilder()
        data = {
            "kpis": [
                {"name": "Revenue", "value": 100, "status": "good"},
            ]
        }
        dashboard = builder.generate_executive_dashboard(data)
        assert "kpi_grid" in dashboard.components
        assert "traffic_lights" in dashboard.components

    def test_with_trends(self):
        builder = ExecutiveDashboardBuilder()
        data = {
            "trends": {
                "periods": ["Q1", "Q2"],
                "revenue": [100, 200],
            }
        }
        dashboard = builder.generate_executive_dashboard(data)
        assert "trend_charts" in dashboard.components
