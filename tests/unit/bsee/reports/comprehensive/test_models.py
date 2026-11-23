"""Tests for comprehensive reporting data models."""

from datetime import date

import pytest

from worldenergydata.bsee.reports.comprehensive.models import (
    Block,
    EconomicMetrics,
    Field,
    HierarchyLevel,
    Lease,
    OrganizationalUnit,
    ProductionMetrics,
    ProductionPeriod,
    Well,
    WellSummary,
)


class TestHierarchyLevel:
    def test_values(self):
        assert HierarchyLevel.WELL.value == "well"
        assert HierarchyLevel.LEASE.value == "lease"
        assert HierarchyLevel.FIELD.value == "field"
        assert HierarchyLevel.BLOCK.value == "block"

    def test_ordering(self):
        assert HierarchyLevel.WELL < HierarchyLevel.LEASE
        assert HierarchyLevel.LEASE < HierarchyLevel.FIELD
        assert HierarchyLevel.FIELD < HierarchyLevel.BLOCK

    def test_count(self):
        assert len(HierarchyLevel) == 4


class TestProductionPeriod:
    def test_values(self):
        assert ProductionPeriod.DAILY.value == "daily"
        assert ProductionPeriod.MONTHLY.value == "monthly"
        assert ProductionPeriod.YEARLY.value == "yearly"
        assert ProductionPeriod.CUMULATIVE.value == "cumulative"

    def test_daily_range(self):
        ref = date(2024, 6, 15)
        start, end = ProductionPeriod.get_date_range(ProductionPeriod.DAILY, ref)
        assert start == ref
        assert end == ref

    def test_monthly_range(self):
        ref = date(2024, 2, 15)
        start, end = ProductionPeriod.get_date_range(ProductionPeriod.MONTHLY, ref)
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)  # 2024 is a leap year

    def test_monthly_range_30_day(self):
        ref = date(2024, 6, 10)
        start, end = ProductionPeriod.get_date_range(ProductionPeriod.MONTHLY, ref)
        assert start == date(2024, 6, 1)
        assert end == date(2024, 6, 30)

    def test_yearly_range(self):
        ref = date(2024, 6, 15)
        start, end = ProductionPeriod.get_date_range(ProductionPeriod.YEARLY, ref)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_cumulative_range(self):
        ref = date(2024, 6, 15)
        start, end = ProductionPeriod.get_date_range(ProductionPeriod.CUMULATIVE, ref)
        assert start == date(1900, 1, 1)
        assert end == ref


class TestOrganizationalUnit:
    def test_init(self):
        ou = OrganizationalUnit("U001", "TestUnit", "well")
        assert ou.id == "U001"
        assert ou.name == "TestUnit"
        assert ou.level == "well"
        assert ou.parent_id is None
        assert ou.children == []
        assert ou.metadata == {}
        assert ou.attributes == {}
        assert ou.metrics == {}

    def test_add_child(self):
        parent = OrganizationalUnit("P001", "Parent", "field")
        child = OrganizationalUnit("C001", "Child", "well")
        parent.add_child(child)
        assert len(parent.children) == 1
        assert child.parent_id == "P001"

    def test_metadata(self):
        ou = OrganizationalUnit("U001", "Test", "well")
        ou.set_metadata("author", "tester")
        assert ou.get_metadata("author") == "tester"
        assert ou.get_metadata("missing") is None
        assert ou.get_metadata("missing", "default") == "default"

    def test_attributes(self):
        ou = OrganizationalUnit("U001", "Test", "well")
        ou.set_attribute("depth", 5000)
        assert ou.get_attribute("depth") == 5000
        assert ou.get_attribute("missing") is None

    def test_metrics(self):
        ou = OrganizationalUnit("U001", "Test", "well")
        ou.set_metric("production", 1000)
        assert ou.get_metric("production") == 1000
        assert ou.get_metric("missing") is None

    def test_kwargs_as_attributes(self):
        ou = OrganizationalUnit("U001", "Test", "well", custom_field="custom_value")
        assert ou.custom_field == "custom_value"


class TestWellModel:
    def test_init_basic(self):
        w = Well("W001", "TestWell", lease_id="L001")
        assert w.id == "W001"
        assert w.name == "TestWell"
        assert w.lease_id == "L001"
        assert w.status == "active"
        assert w.production_data == {}

    def test_init_full(self):
        w = Well(
            "W001",
            "TestWell",
            api_number="123",
            lease_id="L001",
            spud_date=date(2024, 1, 1),
            last_activity_date=date(2024, 3, 15),
            water_depth_ft=500.0,
            total_depth_ft=15000.0,
        )
        assert w.api_number == "123"
        assert w.water_depth_ft == 500.0

    def test_construction_days(self):
        w = Well(
            "W001",
            "TestWell",
            lease_id="L001",
            spud_date=date(2024, 1, 1),
            last_activity_date=date(2024, 4, 1),
        )
        assert w.calculate_construction_days() == 91

    def test_construction_days_no_dates(self):
        w = Well("W001", "TestWell", lease_id="L001")
        assert w.calculate_construction_days() == 0

    def test_update_status(self):
        w = Well("W001", "TestWell", lease_id="L001")
        w.update_status("INACTIVE")
        assert w.wellbore_status == "INACTIVE"

    def test_production_data(self):
        w = Well("W001", "TestWell", lease_id="L001")
        data = {"oil_bbls": 1000, "gas_mcf": 5000}
        w.set_production_data(data)
        assert w.get_production_data() == data

    def test_directional_survey(self):
        w = Well("W001", "TestWell", lease_id="L001")
        survey = {"md": [0, 100], "inc": [0, 5]}
        w.set_directional_survey(survey)
        assert w.get_directional_survey() == survey


class TestLease:
    def test_init(self):
        lease = Lease("L001", "L-123", "F001")
        assert lease.number == "L-123"
        assert lease.field_id == "F001"
        assert lease.children == []

    def test_aggregate_production(self):
        lease = Lease("L001", "L-123", "F001")
        w1 = Well("W001", "Well1", lease_id="L001")
        w1.set_production_data({"oil_bbls": 500, "gas_mcf": 2000, "water_bbls": 100})
        w2 = Well("W002", "Well2", lease_id="L001")
        w2.set_production_data({"oil_bbls": 300, "gas_mcf": 1000, "water_bbls": 50})
        lease.add_child(w1)
        lease.add_child(w2)
        total = lease.aggregate_production()
        assert total["oil_bbls"] == 800
        assert total["gas_mcf"] == 3000
        assert total["water_bbls"] == 150

    def test_get_well_count(self):
        lease = Lease("L001", "L-123", "F001")
        lease.add_child(Well("W001", "Well1", lease_id="L001"))
        lease.add_child(Well("W002", "Well2", lease_id="L001"))
        assert lease.get_well_count() == 2

    def test_aggregate_production_empty(self):
        lease = Lease("L001", "L-123", "F001")
        total = lease.aggregate_production()
        assert total == {"oil_bbls": 0, "gas_mcf": 0, "water_bbls": 0}


class TestField:
    def test_init(self):
        f = Field("F001", "TestField", "B001")
        assert f.name == "TestField"
        assert f.block_id == "B001"

    def test_get_lease_count(self):
        f = Field("F001", "TestField", "B001")
        f.add_child(Lease("L001", "L-1", "F001"))
        f.add_child(Lease("L002", "L-2", "F001"))
        assert f.get_lease_count() == 2

    def test_aggregate_production(self):
        f = Field("F001", "TestField", "B001")
        l1 = Lease("L001", "L-1", "F001")
        l1.total_production = {"oil_bbls": 500, "gas_mcf": 2000, "water_bbls": 100}
        f.add_child(l1)
        total = f.aggregate_production()
        assert total["oil_bbls"] == 500


class TestBlock:
    def test_init(self):
        b = Block("B001", "100", area="GC")
        assert b.number == "100"
        assert b.area == "GC"
        assert b.name == "GC 100"

    def test_init_no_area(self):
        b = Block("B001", "100")
        assert b.name == "100"

    def test_get_field_count(self):
        b = Block("B001", "100")
        b.add_child(Field("F001", "Field1", "B001"))
        b.add_child(Field("F002", "Field2", "B001"))
        assert b.get_field_count() == 2

    def test_aggregate_production(self):
        b = Block("B001", "100")
        f = Field("F001", "Field1", "B001")
        f.total_production = {"oil_bbls": 1000, "gas_mcf": 5000, "water_bbls": 200}
        b.add_child(f)
        total = b.aggregate_production()
        assert total["oil_bbls"] == 1000


class TestWellSummary:
    def test_defaults(self):
        ws = WellSummary(well_id="W001")
        assert ws.total_oil_bbls == 0.0
        assert ws.days_on_production == 0
        assert ws.status == "active"

    def test_average_daily_oil(self):
        ws = WellSummary(well_id="W001", total_oil_bbls=3000, days_on_production=30)
        assert ws.average_daily_oil == 100.0

    def test_average_daily_oil_zero_days(self):
        ws = WellSummary(well_id="W001", total_oil_bbls=3000, days_on_production=0)
        assert ws.average_daily_oil == 0.0

    def test_average_daily_gas(self):
        ws = WellSummary(well_id="W001", total_gas_mcf=9000, days_on_production=30)
        assert ws.average_daily_gas == 300.0

    def test_gas_oil_ratio(self):
        ws = WellSummary(well_id="W001", total_oil_bbls=1000, total_gas_mcf=6000)
        assert ws.gas_oil_ratio == 6.0

    def test_gas_oil_ratio_zero_oil(self):
        ws = WellSummary(well_id="W001", total_gas_mcf=6000)
        assert ws.gas_oil_ratio == 0.0

    def test_is_active(self):
        ws = WellSummary(well_id="W001", wellbore_status="ACTIVE")
        assert ws.is_active() is True

    def test_is_not_active(self):
        ws = WellSummary(well_id="W001", wellbore_status="P&A")
        assert ws.is_active() is False

    def test_is_not_active_abandoned(self):
        ws = WellSummary(well_id="W001", wellbore_status="ABANDONED")
        assert ws.is_active() is False

    def test_calculate_days_on_production(self):
        ws = WellSummary(
            well_id="W001",
            first_production=date(2024, 1, 1),
            last_production=date(2024, 1, 31),
        )
        assert ws.calculate_days_on_production() == 31

    def test_from_well(self):
        w = Well("W001", "TestWell", lease_id="L001")
        w.set_production_data(
            {"oil_bbls": 500, "gas_mcf": 2000, "water_bbls": 100, "days_on": 30}
        )
        ws = WellSummary.from_well(w)
        assert ws.well_id == "W001"
        assert ws.total_oil_bbls == 500
        assert ws.total_gas_mcf == 2000
        assert ws.days_on_production == 30


class TestProductionMetrics:
    def test_defaults(self):
        pm = ProductionMetrics()
        assert pm.oil_production_bbls == 0.0
        assert pm.oil_price_usd == 75.0
        assert pm.gas_price_usd == 3.50

    def test_post_init_sync_oil(self):
        pm = ProductionMetrics(oil_volume_bbl=1000.0)
        assert pm.oil_production_bbls == 1000.0

    def test_post_init_sync_gas(self):
        pm = ProductionMetrics(gas_volume_mcf=5000.0)
        assert pm.gas_production_mcf == 5000.0

    def test_daily_oil_rate(self):
        pm = ProductionMetrics(oil_production_bbls=36500, days_in_period=365)
        assert pm.daily_oil_rate == 100.0

    def test_daily_gas_rate(self):
        pm = ProductionMetrics(gas_production_mcf=73000, days_in_period=365)
        assert pm.daily_gas_rate == 200.0

    def test_water_cut(self):
        pm = ProductionMetrics(oil_production_bbls=700, water_production_bbls=300)
        assert pm.water_cut == 0.3

    def test_water_cut_no_liquids(self):
        pm = ProductionMetrics()
        assert pm.water_cut == 0.0

    def test_oil_per_well_per_day(self):
        pm = ProductionMetrics(
            oil_production_bbls=36500,
            active_well_count=10,
            days_in_period=365,
        )
        assert pm.oil_per_well_per_day == 10.0

    def test_oil_revenue(self):
        pm = ProductionMetrics(oil_volume_bbl=1000, oil_price_usd=80.0)
        assert pm.oil_revenue() == 80000.0

    def test_gas_revenue(self):
        pm = ProductionMetrics(gas_volume_mcf=10000, gas_price_usd=4.0)
        assert pm.gas_revenue() == 40000.0

    def test_total_revenue(self):
        pm = ProductionMetrics(
            oil_volume_bbl=1000,
            oil_price_usd=80.0,
            gas_volume_mcf=10000,
            gas_price_usd=4.0,
        )
        assert pm.total_revenue() == 120000.0

    def test_net_revenue(self):
        pm = ProductionMetrics(
            oil_volume_bbl=1000,
            oil_price_usd=80.0,
            operating_cost_usd=20000,
        )
        assert pm.net_revenue() == 60000.0

    def test_operating_margin(self):
        pm = ProductionMetrics(
            oil_volume_bbl=1000,
            oil_price_usd=100.0,
            operating_cost_usd=25000,
        )
        assert pm.operating_margin() == 0.75

    def test_operating_margin_zero_revenue(self):
        pm = ProductionMetrics()
        assert pm.operating_margin() == 0.0

    def test_combine(self):
        m1 = ProductionMetrics(oil_production_bbls=100, gas_production_mcf=500)
        m2 = ProductionMetrics(oil_production_bbls=200, gas_production_mcf=1000)
        combined = ProductionMetrics.combine([m1, m2])
        assert combined.oil_production_bbls == 300
        assert combined.gas_production_mcf == 1500


class TestEconomicMetrics:
    def test_defaults(self):
        em = EconomicMetrics()
        assert em.revenue == 0.0
        assert em.discount_rate == 0.10

    def test_calculate_net_income(self):
        em = EconomicMetrics(
            revenue=100000,
            operating_costs=30000,
            capital_costs=10000,
            royalties=18750,
        )
        net = em.calculate_net_income()
        assert net == 41250.0
        assert em.net_income == 41250.0

    def test_operating_cost_per_bbl(self):
        em = EconomicMetrics(operating_costs=15000, production_bbls=1000)
        assert em.operating_cost_per_bbl == 15.0

    def test_operating_cost_per_bbl_zero(self):
        em = EconomicMetrics(operating_costs=15000, production_bbls=0)
        assert em.operating_cost_per_bbl == 0.0

    def test_revenue_per_bbl(self):
        em = EconomicMetrics(revenue=75000, production_bbls=1000)
        assert em.revenue_per_bbl == 75.0

    def test_netback_per_bbl(self):
        em = EconomicMetrics(net_income=50000, production_bbls=1000)
        assert em.netback_per_bbl == 50.0

    def test_profit_margin(self):
        em = EconomicMetrics(revenue=100000, net_income=25000)
        assert em.profit_margin == 0.25

    def test_profit_margin_zero_revenue(self):
        em = EconomicMetrics()
        assert em.profit_margin == 0.0

    def test_from_production(self):
        pm = ProductionMetrics(
            oil_production_bbls=1000,
            gas_production_mcf=5000,
        )
        price_deck = {"oil": 75.0, "gas": 4.0}
        em = EconomicMetrics.from_production(pm, price_deck)
        assert em.revenue == 95000.0  # 75000 + 20000
        assert em.production_bbls == 1000
        assert em.net_income < em.revenue  # Costs subtracted
