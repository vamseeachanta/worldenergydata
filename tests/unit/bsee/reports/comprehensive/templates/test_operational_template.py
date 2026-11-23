"""Tests for operational_template OperationalTemplate class."""

from datetime import date

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.operational_template import (
    EquipmentMetrics,
    FailureAnalysis,
    MaintenanceRecord,
    OperationalKPI,
    OperationalTemplate,
    ProductionEfficiencyMetrics,
    WellOperationalMetrics,
    WellStatus,
)

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestOperationalTemplateInit:
    def test_default(self):
        tpl = OperationalTemplate()
        assert tpl.template_name == "operational_report"
        assert tpl.version == "1.0.0"
        assert hasattr(tpl, "required_context")
        assert "operational_summary" in tpl.required_context

    def test_custom(self):
        tpl = OperationalTemplate(template_name="custom_ops", version="2.0.0")
        assert tpl.template_name == "custom_ops"
        assert tpl.version == "2.0.0"


# ---------------------------------------------------------------------------
# build_operational_context
# ---------------------------------------------------------------------------


class TestBuildOperationalContext:
    def _make_well_metrics(self):
        return [
            WellOperationalMetrics(
                well_api=1001,
                well_name="Well-1",
                status=WellStatus.PRODUCING,
                report_date=date(2024, 6, 1),
                daily_production_boe=500.0,
                uptime_hours=700.0,
                total_hours=720.0,
            ),
            WellOperationalMetrics(
                well_api=1002,
                well_name="Well-2",
                status=WellStatus.SHUT_IN,
                report_date=date(2024, 6, 1),
            ),
        ]

    def test_basic_context(self):
        tpl = OperationalTemplate()
        wells = self._make_well_metrics()
        context = tpl.build_operational_context(
            well_metrics=wells,
            entity_name="Test Platform",
        )
        assert "report_metadata" in context
        assert "operational_summary" in context
        assert "well_performance" in context
        assert "operational_kpis" in context
        assert context["entity_name"] == "Test Platform"
        assert context["report_metadata"]["total_wells"] == 2

    def test_with_production_metrics(self):
        tpl = OperationalTemplate()
        wells = self._make_well_metrics()
        prod = ProductionEfficiencyMetrics(
            entity_id="FIELD-001",
            entity_type="field",
            report_date=date(2024, 6, 1),
            production_oil_bbl=15000.0,
            production_gas_mcf=60000.0,
            production_water_bbl=3000.0,
            design_capacity_boe=1000.0,
            actual_production_boe=880.0,
            production_days=30,
        )
        context = tpl.build_operational_context(
            well_metrics=wells,
            production_metrics=prod,
        )
        assert "production_efficiency" in context

    def test_with_equipment_metrics(self):
        tpl = OperationalTemplate()
        wells = self._make_well_metrics()
        equip = [
            EquipmentMetrics(
                equipment_id="EQ001",
                equipment_type="ESP",
                equipment_name="ESP Pump",
                mtbf_hours=2000.0,
                mttr_hours=24.0,
                total_runtime_hours=1800.0,
                planned_runtime_hours=2000.0,
            ),
        ]
        context = tpl.build_operational_context(
            well_metrics=wells,
            equipment_metrics=equip,
        )
        assert "equipment_reliability" in context

    def test_with_report_date(self):
        tpl = OperationalTemplate()
        wells = self._make_well_metrics()
        context = tpl.build_operational_context(
            well_metrics=wells,
            report_date=date(2024, 6, 15),
        )
        assert context["report_metadata"]["generated_date"] == "2024-06-15"


# ---------------------------------------------------------------------------
# Delegation methods
# ---------------------------------------------------------------------------


class TestDelegationMethods:
    def _make_well_metrics(self):
        return [
            WellOperationalMetrics(
                well_api=1001,
                well_name="Well-1",
                status=WellStatus.PRODUCING,
                report_date=date(2024, 6, 1),
                daily_production_boe=500.0,
            ),
        ]

    def test_calculate_operational_kpis(self):
        tpl = OperationalTemplate()
        kpis = tpl.calculate_operational_kpis(self._make_well_metrics())
        assert isinstance(kpis, list)

    def test_generate_operational_visualizations_empty(self):
        tpl = OperationalTemplate()
        result = tpl.generate_operational_visualizations({})
        assert result == {}

    def test_render_template_string(self):
        tpl = OperationalTemplate()
        result = tpl.render_template_string("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_format_kpis(self):
        tpl = OperationalTemplate()
        result = tpl._format_kpis([])
        assert result == []
