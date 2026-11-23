"""Tests for BSEE operational reporting models."""

from datetime import date, datetime

import pytest

from worldenergydata.bsee.reports.comprehensive.templates.operational_models import (
    EquipmentMetrics,
    FailureAnalysis,
    MaintenanceRecord,
    OperationalKPI,
    ProductionEfficiencyMetrics,
    WellOperationalMetrics,
    WellStatus,
)


class TestWellStatus:
    def test_all_members(self):
        names = {m.name for m in WellStatus}
        assert "PRODUCING" in names
        assert "SHUT_IN" in names
        assert "ABANDONED" in names
        assert "DRILLING" in names
        assert "WORKOVER" in names

    def test_member_count(self):
        assert len(WellStatus) == 10


class TestWellOperationalMetrics:
    def _make_well(self, **kwargs):
        defaults = {
            "well_api": 42001234,
            "well_name": "Test Well",
            "status": WellStatus.PRODUCING,
            "report_date": date(2024, 6, 15),
        }
        defaults.update(kwargs)
        return WellOperationalMetrics(**defaults)

    def test_minimal(self):
        w = self._make_well()
        assert w.well_api == 42001234
        assert w.well_name == "Test Well"
        assert w.status == WellStatus.PRODUCING

    def test_defaults(self):
        w = self._make_well()
        assert w.drilling_depth_ft == 0
        assert w.drilling_cost == 0
        assert w.daily_production_boe == 0
        assert w.failure_count == 0

    def test_drilling_efficiency(self):
        w = self._make_well(planned_drilling_days=30, actual_drilling_days=40)
        assert w.drilling_efficiency() == pytest.approx(75.0)

    def test_drilling_efficiency_zero_actual(self):
        w = self._make_well(planned_drilling_days=30, actual_drilling_days=0)
        assert w.drilling_efficiency() == 0

    def test_completion_efficiency(self):
        w = self._make_well(
            planned_completion_days=10,
            actual_completion_days=12,
        )
        assert w.completion_efficiency() == pytest.approx(83.333, rel=1e-2)

    def test_completion_efficiency_zero(self):
        w = self._make_well()
        assert w.completion_efficiency() == 0

    def test_well_cycle_time(self):
        w = self._make_well(
            drilling_start_date=date(2024, 1, 1),
            first_production_date=date(2024, 4, 1),
        )
        assert w.well_cycle_time() == 91

    def test_well_cycle_time_no_dates(self):
        w = self._make_well()
        assert w.well_cycle_time() == 0

    def test_availability(self):
        w = self._make_well(uptime_hours=900, total_hours=1000)
        assert w.availability_percentage() == pytest.approx(90.0)

    def test_availability_zero(self):
        w = self._make_well()
        assert w.availability_percentage() == 0

    def test_drilling_rate(self):
        w = self._make_well(drilling_depth_ft=15000, actual_drilling_days=30)
        assert w.drilling_rate_ft_per_day() == pytest.approx(500.0)

    def test_cost_per_foot(self):
        w = self._make_well(
            drilling_cost=1000000,
            completion_cost=500000,
            total_depth_ft=15000,
        )
        assert w.cost_per_foot_drilled() == pytest.approx(100.0)

    def test_production_days(self):
        w = self._make_well(
            first_production_date=date(2024, 1, 1),
            last_production_date=date(2024, 1, 31),
        )
        assert w.production_days() == 31


class TestProductionEfficiencyMetrics:
    def _make_metrics(self, **kwargs):
        defaults = {
            "entity_id": "FIELD-001",
            "entity_type": "field",
            "report_date": date(2024, 6, 15),
        }
        defaults.update(kwargs)
        return ProductionEfficiencyMetrics(**defaults)

    def test_minimal(self):
        m = self._make_metrics()
        assert m.entity_id == "FIELD-001"
        assert m.entity_type == "field"

    def test_valid_entity_types(self):
        for t in ("well", "lease", "field", "block"):
            m = self._make_metrics(entity_type=t)
            assert m.entity_type == t

    def test_invalid_entity_type(self):
        with pytest.raises(ValueError, match="Invalid entity_type"):
            self._make_metrics(entity_type="invalid")

    def test_empty_entity_id(self):
        with pytest.raises(ValueError, match="entity_id cannot be empty"):
            self._make_metrics(entity_id="")

    def test_negative_production_clamped(self):
        m = self._make_metrics(production_oil_bbl=-100)
        assert m.production_oil_bbl == 0

    def test_negative_gas_clamped(self):
        m = self._make_metrics(production_gas_mcf=-50)
        assert m.production_gas_mcf == 0

    def test_negative_water_clamped(self):
        m = self._make_metrics(production_water_bbl=-10)
        assert m.production_water_bbl == 0

    def test_production_efficiency(self):
        m = self._make_metrics(
            design_capacity_boe=1000,
            actual_production_boe=8000,
            production_days=10,
        )
        expected = (8000 / (1000 * 10)) * 100
        assert m.production_efficiency() == pytest.approx(expected)

    def test_production_efficiency_zero(self):
        m = self._make_metrics()
        assert m.production_efficiency() == 0

    def test_operating_efficiency(self):
        m = self._make_metrics(operating_days=25, production_days=30)
        assert m.operating_efficiency() == pytest.approx(83.333, rel=1e-2)

    def test_well_availability(self):
        m = self._make_metrics(wells_producing=8, total_wells=10)
        assert m.well_availability() == pytest.approx(80.0)

    def test_daily_production_rate(self):
        m = self._make_metrics(actual_production_boe=30000, production_days=30)
        assert m.daily_production_rate_boe() == pytest.approx(1000.0)

    def test_water_cut(self):
        m = self._make_metrics(
            production_oil_bbl=800,
            production_water_bbl=200,
        )
        assert m.water_cut_percentage() == pytest.approx(20.0)

    def test_gas_oil_ratio(self):
        m = self._make_metrics(
            production_oil_bbl=1000,
            production_gas_mcf=5000,
        )
        assert m.gas_oil_ratio() == pytest.approx(5.0)


class TestEquipmentMetrics:
    def _make_equip(self, **kwargs):
        defaults = {
            "equipment_id": "ESP-001",
            "equipment_type": "ESP",
            "equipment_name": "Test ESP",
        }
        defaults.update(kwargs)
        return EquipmentMetrics(**defaults)

    def test_minimal(self):
        e = self._make_equip()
        assert e.equipment_id == "ESP-001"
        assert e.total_runtime_hours == 0

    def test_availability(self):
        e = self._make_equip(
            total_runtime_hours=800,
            unplanned_downtime_hours=100,
            planned_downtime_hours=100,
        )
        assert e.equipment_availability() == pytest.approx(80.0)

    def test_availability_zero(self):
        e = self._make_equip()
        assert e.equipment_availability() == 0

    def test_utilization(self):
        e = self._make_equip(
            total_runtime_hours=450,
            planned_runtime_hours=500,
        )
        assert e.equipment_utilization() == pytest.approx(90.0)

    def test_reliability(self):
        e = self._make_equip(mtbf_hours=1000, mttr_hours=100)
        expected = (1000 / (1000 + 100)) * 100
        assert e.equipment_reliability() == pytest.approx(expected)

    def test_age_days(self):
        e = self._make_equip(
            installation_date=date(2024, 1, 1),
            report_date=date(2024, 7, 1),
        )
        assert e.equipment_age_days() == 182

    def test_cost_effectiveness(self):
        e = self._make_equip(
            maintenance_cost=50000,
            replacement_cost=500000,
        )
        assert e.cost_effectiveness_ratio() == pytest.approx(0.1)


class TestMaintenanceRecord:
    def _make_record(self, **kwargs):
        defaults = {
            "maintenance_id": "MAINT-001",
            "equipment_id": "ESP-001",
            "maintenance_date": date(2024, 6, 1),
            "maintenance_type": "preventive",
            "description": "Routine check",
            "duration_hours": 4.0,
            "cost": 5000.0,
            "performed_by": "Tech Team",
        }
        defaults.update(kwargs)
        return MaintenanceRecord(**defaults)

    def test_minimal(self):
        r = self._make_record()
        assert r.maintenance_id == "MAINT-001"
        assert r.parts_replaced == []

    def test_is_overdue_no_date(self):
        r = self._make_record()
        assert r.is_overdue() is False

    def test_is_overdue_future(self):
        r = self._make_record(next_scheduled_date=date(2099, 1, 1))
        assert r.is_overdue() is False

    def test_is_overdue_past(self):
        r = self._make_record(next_scheduled_date=date(2020, 1, 1))
        assert r.is_overdue() is True

    def test_days_until_next_no_date(self):
        r = self._make_record()
        assert r.days_until_next() == 0

    def test_days_until_next_future(self):
        r = self._make_record(next_scheduled_date=date(2099, 12, 31))
        assert r.days_until_next() > 0


class TestFailureAnalysis:
    def _make_failure(self, **kwargs):
        defaults = {
            "failure_id": "FAIL-001",
        }
        defaults.update(kwargs)
        return FailureAnalysis(**defaults)

    def test_minimal(self):
        f = self._make_failure()
        assert f.failure_id == "FAIL-001"
        assert f.corrective_actions == []

    def test_total_impact_cost(self):
        f = self._make_failure(
            production_impact_boe=100,
            repair_cost=10000,
        )
        cost = f.total_impact_cost(oil_price=80)
        assert cost == pytest.approx(18000.0)

    def test_total_impact_cost_custom_price(self):
        f = self._make_failure(
            production_impact_boe=50,
            repair_cost=5000,
        )
        assert f.total_impact_cost(oil_price=100) == pytest.approx(10000.0)

    def test_failure_rate(self):
        f = self._make_failure()
        rate = f.failure_rate_per_1000_hours(runtime_hours=5000)
        assert rate == pytest.approx(0.2)

    def test_failure_rate_zero_hours(self):
        f = self._make_failure()
        assert f.failure_rate_per_1000_hours(0) == 0


class TestOperationalKPI:
    def _make_kpi(self, **kwargs):
        defaults = {
            "kpi_id": "KPI-001",
            "kpi_name": "Production Uptime",
            "kpi_category": "production",
            "target_value": 95.0,
            "actual_value": 90.0,
            "unit": "%",
            "measurement_date": date(2024, 6, 15),
        }
        defaults.update(kwargs)
        return OperationalKPI(**defaults)

    def test_minimal(self):
        k = self._make_kpi()
        assert k.kpi_id == "KPI-001"
        assert k.trend == "stable"
        assert k.status == "normal"

    def test_performance_percentage(self):
        k = self._make_kpi(target_value=100, actual_value=90)
        assert k.performance_percentage() == pytest.approx(90.0)

    def test_performance_zero_target(self):
        k = self._make_kpi(target_value=0, actual_value=90)
        assert k.performance_percentage() == 0

    def test_is_on_target_true(self):
        k = self._make_kpi(target_value=90, actual_value=95)
        assert k.is_on_target() is True

    def test_is_on_target_false(self):
        k = self._make_kpi(target_value=95, actual_value=90)
        assert k.is_on_target() is False

    def test_is_on_target_equal(self):
        k = self._make_kpi(target_value=90, actual_value=90)
        assert k.is_on_target() is True

    def test_variance_percentage(self):
        k = self._make_kpi(target_value=100, actual_value=110)
        assert k.variance_percentage() == pytest.approx(10.0)

    def test_variance_negative(self):
        k = self._make_kpi(target_value=100, actual_value=80)
        assert k.variance_percentage() == pytest.approx(-20.0)
