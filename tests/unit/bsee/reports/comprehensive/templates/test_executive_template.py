"""Tests for ExecutiveTemplate facade class."""

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.executive_template import (
    ExecutiveTemplate,
)


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestExecutiveTemplateInit:
    def test_default(self):
        tpl = ExecutiveTemplate()
        assert tpl.template_name == "executive"
        assert tpl.version == "1.0.0"
        assert isinstance(tpl.kpi_thresholds, dict)
        assert isinstance(tpl.benchmarks, dict)
        assert "uptime" in tpl.kpi_thresholds
        assert "uptime" in tpl.benchmarks

    def test_custom_config(self):
        config = {
            "kpi_thresholds": {"uptime": {"green": 99, "yellow": 95}},
            "benchmarks": {"uptime": 97.0},
        }
        tpl = ExecutiveTemplate(config=config)
        assert tpl.kpi_thresholds["uptime"]["green"] == 99
        assert tpl.benchmarks["uptime"] == 97.0


# ---------------------------------------------------------------------------
# KPI threshold loading
# ---------------------------------------------------------------------------

class TestKpiThresholds:
    def test_default_thresholds(self):
        tpl = ExecutiveTemplate()
        thresholds = tpl.kpi_thresholds
        assert "efficiency" in thresholds
        assert "safety_trir" in thresholds
        assert "emissions_intensity" in thresholds
        assert "roi" in thresholds
        assert "npv" in thresholds

    def test_default_benchmarks(self):
        tpl = ExecutiveTemplate()
        benchmarks = tpl.benchmarks
        assert benchmarks["efficiency"] == 85.0
        assert benchmarks["safety_trir"] == 0.75
        assert benchmarks["operating_cost_per_boe"] == 28.0


# ---------------------------------------------------------------------------
# Delegation methods
# ---------------------------------------------------------------------------

class TestDelegationMethods:
    def test_determine_kpi_status(self):
        tpl = ExecutiveTemplate()
        # Above target = good
        status = tpl.determine_kpi_status(100.0, 90.0)
        assert isinstance(status, str)

    def test_analyze_kpi_trend(self):
        tpl = ExecutiveTemplate()
        trend = tpl.analyze_kpi_trend([80, 85, 90, 95])
        assert isinstance(trend, str)

    def test_generate_executive_kpis_empty(self):
        tpl = ExecutiveTemplate()
        kpis = tpl.generate_executive_kpis({})
        assert isinstance(kpis, list)

    def test_calculate_strategic_metrics_empty(self):
        tpl = ExecutiveTemplate()
        metrics = tpl.calculate_strategic_metrics({})
        assert isinstance(metrics, list)

    def test_compare_with_benchmarks(self):
        tpl = ExecutiveTemplate()
        result = tpl.compare_with_benchmarks(
            {"uptime": 95}, {"uptime": 92}
        )
        assert isinstance(result, dict)

    def test_rank_kpis_empty(self):
        tpl = ExecutiveTemplate()
        result = tpl.rank_kpis_by_priority([])
        assert result == []

    def test_get_dashboard_layout(self):
        tpl = ExecutiveTemplate()
        layout = tpl.get_dashboard_layout_config()
        assert isinstance(layout, dict)
        assert "grid_rows" in layout

    def test_get_dashboard_export(self):
        tpl = ExecutiveTemplate()
        config = tpl.get_dashboard_export_config()
        assert config["width"] == 1920

    def test_determine_traffic_light(self):
        tpl = ExecutiveTemplate()
        status = tpl.determine_traffic_light_status(96.0, 95.0, 90.0)
        assert isinstance(status, str)

    def test_get_status_color(self):
        tpl = ExecutiveTemplate()
        color = tpl._get_status_color("good")
        assert isinstance(color, str)

    def test_calculate_trend(self):
        tpl = ExecutiveTemplate()
        trend = tpl._calculate_trend([50, 60, 70, 80])
        assert isinstance(trend, str)


# ---------------------------------------------------------------------------
# Dashboard generation
# ---------------------------------------------------------------------------

class TestDashboardGeneration:
    def test_generate_empty_dashboard(self):
        tpl = ExecutiveTemplate()
        dashboard = tpl.generate_executive_dashboard({})
        assert dashboard is not None

    def test_generate_dashboard_with_kpis(self):
        tpl = ExecutiveTemplate()
        data = {
            "kpis": [
                {"name": "Uptime", "value": 95, "status": "good"},
            ]
        }
        dashboard = tpl.generate_executive_dashboard(data)
        assert dashboard is not None


# ---------------------------------------------------------------------------
# Benchmarking delegation
# ---------------------------------------------------------------------------

class TestBenchmarkingDelegation:
    def test_analyze_competitive_position(self):
        tpl = ExecutiveTemplate()
        result = tpl.analyze_competitive_position({
            "uptime": 95, "efficiency": 88,
        })
        assert isinstance(result, dict)

    def test_generate_peer_ranking_empty(self):
        tpl = ExecutiveTemplate()
        result = tpl.generate_peer_ranking_table([])
        assert isinstance(result, list)

    def test_generate_peer_ranking_with_data(self):
        tpl = ExecutiveTemplate()
        peers = [
            {"company": "Co A", "uptime": 95},
            {"company": "Co B", "uptime": 88},
        ]
        result = tpl.generate_peer_ranking_table(peers)
        assert isinstance(result, list)
