"""Tests for operational_charts Plotly chart generation functions."""

import json

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.operational_charts import (
    create_efficiency_gauge,
    create_failure_chart,
    create_kpi_dashboard,
    create_reliability_chart,
    create_well_status_chart,
    generate_operational_visualizations,
)

# ---------------------------------------------------------------------------
# create_well_status_chart
# ---------------------------------------------------------------------------


class TestCreateWellStatusChart:
    def test_basic(self):
        summary = {
            "total_wells": 20,
            "wells_producing": 12,
            "wells_drilling": 3,
            "wells_offline": 2,
        }
        result = create_well_status_chart(summary)
        parsed = json.loads(result)
        assert "data" in parsed

    def test_empty_summary(self):
        result = create_well_status_chart({})
        parsed = json.loads(result)
        assert "data" in parsed

    def test_all_producing(self):
        summary = {
            "total_wells": 10,
            "wells_producing": 10,
            "wells_drilling": 0,
            "wells_offline": 0,
        }
        result = create_well_status_chart(summary)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# create_efficiency_gauge
# ---------------------------------------------------------------------------


class TestCreateEfficiencyGauge:
    def test_basic(self):
        efficiency = {"efficiency_percentage": 85.5}
        result = create_efficiency_gauge(efficiency)
        parsed = json.loads(result)
        assert "data" in parsed

    def test_zero_efficiency(self):
        result = create_efficiency_gauge({"efficiency_percentage": 0})
        assert isinstance(result, str)

    def test_missing_key(self):
        result = create_efficiency_gauge({})
        parsed = json.loads(result)
        assert "data" in parsed


# ---------------------------------------------------------------------------
# create_reliability_chart
# ---------------------------------------------------------------------------


class TestCreateReliabilityChart:
    def test_with_equipment(self):
        reliability = {
            "equipment_details": [
                {"name": "Pump A", "availability": 95, "reliability": 92},
                {"name": "Compressor B", "availability": 88, "reliability": 85},
            ]
        }
        result = create_reliability_chart(reliability)
        parsed = json.loads(result)
        assert "data" in parsed

    def test_empty_equipment(self):
        result = create_reliability_chart({"equipment_details": []})
        assert result == "{}"

    def test_missing_key(self):
        result = create_reliability_chart({})
        assert result == "{}"


# ---------------------------------------------------------------------------
# create_kpi_dashboard
# ---------------------------------------------------------------------------


class TestCreateKpiDashboard:
    def test_with_kpis(self):
        kpis = [
            {
                "name": "Uptime",
                "actual": 95,
                "target": 90,
                "status": "good",
                "unit": "%",
            },
            {
                "name": "Cost",
                "actual": 28,
                "target": 30,
                "status": "good",
                "unit": "$/bbl",
            },
            {
                "name": "Safety",
                "actual": 1.2,
                "target": 0.5,
                "status": "critical",
                "unit": "TRIR",
            },
        ]
        result = create_kpi_dashboard(kpis)
        parsed = json.loads(result)
        assert "data" in parsed

    def test_empty_kpis(self):
        result = create_kpi_dashboard([])
        assert result == "{}"

    def test_single_kpi(self):
        kpis = [
            {
                "name": "Uptime",
                "actual": 95,
                "target": 90,
                "status": "warning",
                "unit": "%",
            },
        ]
        result = create_kpi_dashboard(kpis)
        parsed = json.loads(result)
        assert "data" in parsed


# ---------------------------------------------------------------------------
# create_failure_chart
# ---------------------------------------------------------------------------


class TestCreateFailureChart:
    def test_with_failures(self):
        failures = {"by_type": {"Mechanical": 5, "Electrical": 3, "Corrosion": 2}}
        result = create_failure_chart(failures)
        parsed = json.loads(result)
        assert "data" in parsed

    def test_empty_failures(self):
        result = create_failure_chart({"by_type": {}})
        assert result == "{}"

    def test_missing_key(self):
        result = create_failure_chart({})
        assert result == "{}"


# ---------------------------------------------------------------------------
# generate_operational_visualizations
# ---------------------------------------------------------------------------


class TestGenerateOperationalVisualizations:
    def test_full_context(self):
        context = {
            "operational_summary": {
                "total_wells": 10,
                "wells_producing": 8,
                "wells_drilling": 1,
                "wells_offline": 1,
            },
            "production_efficiency": {"efficiency_percentage": 85},
            "equipment_reliability": {
                "equipment_details": [
                    {"name": "Pump", "availability": 95, "reliability": 90},
                ]
            },
            "operational_kpis": [
                {
                    "name": "Uptime",
                    "actual": 95,
                    "target": 90,
                    "status": "good",
                    "unit": "%",
                },
            ],
            "failure_analysis": {"by_type": {"Mechanical": 3}},
        }
        result = generate_operational_visualizations(context)
        assert "well_status_chart" in result
        assert "efficiency_gauge" in result
        assert "reliability_chart" in result
        assert "kpi_dashboard" in result
        assert "failure_chart" in result

    def test_empty_context(self):
        result = generate_operational_visualizations({})
        assert result == {}

    def test_partial_context(self):
        context = {
            "operational_summary": {"total_wells": 5},
        }
        result = generate_operational_visualizations(context)
        assert "well_status_chart" in result
        assert "efficiency_gauge" not in result
