"""Tests for operational calculations module."""

from datetime import date

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.operational_calculations import (
    add_completion_efficiency_metrics,
    add_drilling_performance_analysis,
    add_equipment_utilization_analysis,
    add_production_optimization_tracking,
    calculate_operational_kpis,
)
from worldenergydata.bsee.reports.comprehensive.templates.operational_models import (
    EquipmentMetrics,
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
        "maintenance_cost": 50000,
    }
    defaults.update(overrides)
    return EquipmentMetrics(**defaults)


# ---------------------------------------------------------------------------
# calculate_operational_kpis
# ---------------------------------------------------------------------------


class TestCalculateOperationalKPIs:
    def test_empty_wells(self):
        kpis = calculate_operational_kpis([])
        assert kpis == []

    def test_well_availability_kpi(self):
        wells = [_make_well(uptime_hours=8000, total_hours=8760)]
        kpis = calculate_operational_kpis(wells)
        names = [k.kpi_name for k in kpis]
        assert "Well Availability" in names

    def test_drilling_efficiency_kpi(self):
        wells = [_make_well(planned_drilling_days=30, actual_drilling_days=32)]
        kpis = calculate_operational_kpis(wells)
        names = [k.kpi_name for k in kpis]
        assert "Drilling Efficiency" in names

    def test_production_efficiency_kpi(self):
        prod = _make_prod()
        kpis = calculate_operational_kpis([], production_metrics=prod)
        names = [k.kpi_name for k in kpis]
        assert "Overall Production Efficiency" in names
        assert "Operating Efficiency" in names

    def test_equipment_kpis(self):
        equip = [_make_equip()]
        kpis = calculate_operational_kpis([], equipment_metrics=equip)
        names = [k.kpi_name for k in kpis]
        assert "Equipment Reliability" in names
        assert "Equipment Utilization" in names

    def test_all_combined(self):
        wells = [_make_well(planned_drilling_days=30, actual_drilling_days=32)]
        prod = _make_prod()
        equip = [_make_equip()]
        kpis = calculate_operational_kpis(wells, prod, equip)
        assert len(kpis) >= 5


# ---------------------------------------------------------------------------
# add_drilling_performance_analysis
# ---------------------------------------------------------------------------


class TestAddDrillingPerformance:
    def test_empty(self):
        ctx = {}
        add_drilling_performance_analysis(ctx, [])
        assert ctx["drilling_performance"]["total_wells_drilled"] == 0

    def test_with_data(self):
        ctx = {}
        wells = [
            _make_well(
                actual_drilling_days=30,
                planned_drilling_days=28,
                drilling_depth_ft=15000,
                total_depth_ft=15000,
                drilling_cost=5000000,
            ),
        ]
        add_drilling_performance_analysis(ctx, wells)
        perf = ctx["drilling_performance"]
        assert perf["total_wells_drilled"] == 1
        assert perf["average_drilling_days"] == 30

    def test_wells_on_time_count(self):
        ctx = {}
        wells = [
            _make_well(
                actual_drilling_days=28, planned_drilling_days=30, drilling_depth_ft=1
            ),
            _make_well(
                actual_drilling_days=35, planned_drilling_days=30, drilling_depth_ft=1
            ),
        ]
        add_drilling_performance_analysis(ctx, wells)
        assert ctx["drilling_performance"]["wells_on_time"] == 1
        assert ctx["drilling_performance"]["wells_delayed"] == 1


# ---------------------------------------------------------------------------
# add_completion_efficiency_metrics
# ---------------------------------------------------------------------------


class TestAddCompletionEfficiency:
    def test_empty(self):
        ctx = {}
        add_completion_efficiency_metrics(ctx, [])
        assert ctx["completion_metrics"]["total_wells_completed"] == 0

    def test_with_data(self):
        ctx = {}
        wells = [
            _make_well(
                actual_completion_days=20,
                planned_completion_days=18,
                completion_cost=2000000,
                frac_stages=30,
                proppant_lbs=500000,
            ),
        ]
        add_completion_efficiency_metrics(ctx, wells)
        metrics = ctx["completion_metrics"]
        assert metrics["total_wells_completed"] == 1
        assert metrics["total_completion_cost"] == 2000000


# ---------------------------------------------------------------------------
# add_production_optimization_tracking
# ---------------------------------------------------------------------------


class TestAddProductionOptimization:
    def test_basic(self):
        ctx = {}
        prod = _make_prod()
        add_production_optimization_tracking(ctx, prod)
        opt = ctx["production_optimization"]
        assert "production_efficiency" in opt
        assert "water_cut" in opt
        assert "gas_oil_ratio" in opt

    def test_low_efficiency_recommendation(self):
        ctx = {}
        prod = _make_prod(
            design_capacity_boe=1000, actual_production_boe=100, production_days=1
        )
        add_production_optimization_tracking(ctx, prod)
        opt = ctx["production_optimization"]
        assert any(
            "debottlenecking" in opp for opp in opt["optimization_opportunities"]
        )

    def test_high_water_cut_recommendation(self):
        ctx = {}
        prod = _make_prod(production_oil_bbl=300, production_water_bbl=700)
        add_production_optimization_tracking(ctx, prod)
        opt = ctx["production_optimization"]
        assert any("water" in opp.lower() for opp in opt["optimization_opportunities"])

    def test_low_availability_recommendation(self):
        ctx = {}
        prod = _make_prod(wells_producing=5, total_wells=10)
        add_production_optimization_tracking(ctx, prod)
        opt = ctx["production_optimization"]
        assert any(
            "availability" in opp.lower() for opp in opt["optimization_opportunities"]
        )


# ---------------------------------------------------------------------------
# add_equipment_utilization_analysis
# ---------------------------------------------------------------------------


class TestAddEquipmentUtilization:
    def test_empty(self):
        ctx = {}
        add_equipment_utilization_analysis(ctx, [])
        assert ctx["equipment_analysis"]["total_equipment"] == 0

    def test_with_data(self):
        ctx = {}
        equips = [
            _make_equip(),
            _make_equip(equipment_id="ESP-002", equipment_type="compressor"),
        ]
        add_equipment_utilization_analysis(ctx, equips)
        analysis = ctx["equipment_analysis"]
        assert analysis["total_equipment"] == 2
        assert "ESP" in analysis["equipment_by_type"]
        assert "compressor" in analysis["equipment_by_type"]
