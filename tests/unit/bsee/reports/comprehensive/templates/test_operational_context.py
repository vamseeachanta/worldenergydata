"""Tests for operational context building module."""

from datetime import date, datetime

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.operational_context import (
    add_equipment_reliability_analysis,
    add_failure_analysis,
    add_maintenance_schedule,
    add_operational_summary,
    add_production_efficiency_analysis,
    add_well_performance_analysis,
    format_kpis,
)
from worldenergydata.bsee.reports.comprehensive.templates.operational_models import (
    EquipmentMetrics,
    FailureAnalysis,
    MaintenanceRecord,
    OperationalKPI,
    ProductionEfficiencyMetrics,
    WellOperationalMetrics,
    WellStatus,
)


def _make_well(**overrides):
    defaults = {
        "well_api": 123,
        "well_name": "W-001",
        "status": WellStatus.PRODUCING,
        "report_date": date(2024, 6, 1),
        "uptime_hours": 8000,
        "total_hours": 8760,
        "daily_production_boe": 500,
        "cumulative_production_boe": 100000,
    }
    defaults.update(overrides)
    return WellOperationalMetrics(**defaults)


def _make_prod(**overrides):
    defaults = {
        "entity_id": "F001",
        "entity_type": "field",
        "report_date": date(2024, 6, 1),
        "design_capacity_boe": 1000,
        "actual_production_boe": 900,
        "production_days": 30,
        "operating_days": 28,
        "production_oil_bbl": 700,
        "production_water_bbl": 300,
        "production_gas_mcf": 3500,
        "total_wells": 10,
        "wells_producing": 9,
        "processing_utilization_pct": 88.0,
    }
    defaults.update(overrides)
    return ProductionEfficiencyMetrics(**defaults)


def _make_equip(**overrides):
    defaults = {
        "equipment_id": "ESP-001",
        "equipment_type": "ESP",
        "equipment_name": "ESP Unit 1",
        "total_runtime_hours": 8000,
        "planned_runtime_hours": 8760,
        "unplanned_downtime_hours": 500,
        "planned_downtime_hours": 260,
        "mtbf_hours": 4000,
        "mttr_hours": 100,
        "failure_count": 2,
    }
    defaults.update(overrides)
    return EquipmentMetrics(**defaults)


# ---------------------------------------------------------------------------
# add_operational_summary
# ---------------------------------------------------------------------------


class TestAddOperationalSummary:
    def test_empty_wells(self):
        ctx = {}
        add_operational_summary(ctx, [], None, None)
        assert ctx["operational_summary"]["total_wells"] == 0

    def test_with_wells(self):
        ctx = {}
        wells = [
            _make_well(status=WellStatus.PRODUCING),
            _make_well(status=WellStatus.DRILLING),
            _make_well(status=WellStatus.OFFLINE),
        ]
        add_operational_summary(ctx, wells, None, None)
        summary = ctx["operational_summary"]
        assert summary["total_wells"] == 3
        assert summary["wells_producing"] == 1
        assert summary["wells_drilling"] == 1
        assert summary["wells_offline"] == 1

    def test_with_production_metrics(self):
        ctx = {}
        prod = _make_prod()
        add_operational_summary(ctx, [], prod, None)
        assert ctx["operational_summary"]["production_efficiency"] > 0

    def test_with_equipment_metrics(self):
        ctx = {}
        equips = [_make_equip()]
        add_operational_summary(ctx, [], None, equips)
        assert ctx["operational_summary"]["equipment_reliability"] > 0


# ---------------------------------------------------------------------------
# add_well_performance_analysis
# ---------------------------------------------------------------------------


class TestAddWellPerformance:
    def test_basic(self):
        ctx = {}
        wells = [_make_well()]
        add_well_performance_analysis(ctx, wells)
        perf = ctx["well_performance"]
        assert perf["wells_producing"] == 1
        assert perf["total_production_boe"] == 100000
        assert len(perf["well_details"]) == 1

    def test_drilling_efficiency(self):
        ctx = {}
        wells = [_make_well(planned_drilling_days=30, actual_drilling_days=32)]
        add_well_performance_analysis(ctx, wells)
        assert ctx["well_performance"]["average_drilling_efficiency"] > 0

    def test_limits_to_10_wells(self):
        ctx = {}
        wells = [_make_well(well_name=f"W-{i:03d}") for i in range(15)]
        add_well_performance_analysis(ctx, wells)
        assert len(ctx["well_performance"]["well_details"]) == 10


# ---------------------------------------------------------------------------
# add_production_efficiency_analysis
# ---------------------------------------------------------------------------


class TestAddProductionEfficiency:
    def test_basic(self):
        ctx = {}
        prod = _make_prod()
        add_production_efficiency_analysis(ctx, prod)
        eff = ctx["production_efficiency"]
        assert "efficiency_percentage" in eff
        assert "water_cut" in eff
        assert "gas_oil_ratio" in eff
        assert eff["capacity_utilization"] == 88.0


# ---------------------------------------------------------------------------
# add_equipment_reliability_analysis
# ---------------------------------------------------------------------------


class TestAddEquipmentReliability:
    def test_basic(self):
        ctx = {}
        equips = [_make_equip()]
        add_equipment_reliability_analysis(ctx, equips)
        rel = ctx["equipment_reliability"]
        assert rel["total_equipment"] == 1
        assert rel["total_failures"] == 2
        assert len(rel["equipment_details"]) == 1

    def test_limits_to_10(self):
        ctx = {}
        equips = [_make_equip(equipment_id=f"E-{i:03d}") for i in range(15)]
        add_equipment_reliability_analysis(ctx, equips)
        assert len(ctx["equipment_reliability"]["equipment_details"]) == 10


# ---------------------------------------------------------------------------
# add_maintenance_schedule
# ---------------------------------------------------------------------------


class TestAddMaintenanceSchedule:
    def test_basic(self):
        ctx = {}
        records = [
            MaintenanceRecord(
                maintenance_id="M001",
                equipment_id="E001",
                maintenance_date=date(2024, 1, 1),
                maintenance_type="preventive",
                description="Quarterly check",
                duration_hours=4,
                cost=5000,
                performed_by="tech",
                next_scheduled_date=date(2099, 4, 1),
            ),
            MaintenanceRecord(
                maintenance_id="M002",
                equipment_id="E001",
                maintenance_date=date(2024, 1, 1),
                maintenance_type="corrective",
                description="Repair",
                duration_hours=8,
                cost=15000,
                performed_by="tech",
            ),
        ]
        add_maintenance_schedule(ctx, records)
        sched = ctx["maintenance_schedule"]
        assert sched["total_maintenance"] == 2
        assert sched["preventive"] == 1
        assert sched["corrective"] == 1
        assert sched["total_cost"] == 20000
        assert len(sched["upcoming"]) == 1


# ---------------------------------------------------------------------------
# add_failure_analysis
# ---------------------------------------------------------------------------


class TestAddFailureAnalysis:
    def test_basic(self):
        ctx = {}
        failures = [
            FailureAnalysis(
                failure_id="F001",
                failure_type="mechanical",
                severity="high",
                downtime_hours=48,
                repair_cost=50000,
                preventable=True,
                failure_date=datetime(2024, 6, 1),
            ),
            FailureAnalysis(
                failure_id="F002",
                failure_type="electrical",
                severity="low",
                downtime_hours=4,
                repair_cost=2000,
                preventable=False,
                failure_date=datetime(2024, 5, 1),
            ),
        ]
        add_failure_analysis(ctx, failures)
        analysis = ctx["failure_analysis"]
        assert analysis["total_failures"] == 2
        assert analysis["preventable"] == 1
        assert analysis["total_downtime"] == 52
        assert analysis["by_type"]["mechanical"] == 1
        assert analysis["by_type"]["electrical"] == 1
        assert analysis["by_severity"]["high"] == 1
        assert len(analysis["recent_failures"]) == 2


# ---------------------------------------------------------------------------
# format_kpis
# ---------------------------------------------------------------------------


class TestFormatKPIs:
    def test_empty(self):
        assert format_kpis([]) == []

    def test_format_single(self):
        kpi = OperationalKPI(
            kpi_id="K001",
            kpi_name="Uptime",
            kpi_category="reliability",
            target_value=90,
            actual_value=95,
            unit="percent",
            measurement_date=date(2024, 6, 1),
            status="good",
            trend="improving",
        )
        result = format_kpis([kpi])
        assert len(result) == 1
        assert result[0]["name"] == "Uptime"
        assert result[0]["on_target"] is True
        assert result[0]["performance"] == pytest.approx(105.56, abs=0.1)
