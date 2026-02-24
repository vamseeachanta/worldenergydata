"""
ABOUTME: Tests for NPV and MIRR discounted cash flow calculations.
ABOUTME: Uses known textbook examples with exact numeric verification.

All expected values derived analytically or with numpy_financial for cross-check.
"""

from __future__ import annotations

import numpy as np
import pytest

from worldenergydata.economics.dcf import (
    CashFlowSchedule,
    MIRRResult,
    NPVResult,
    calculate_mirr,
    calculate_npv,
    build_cash_flow_schedule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_schedule(capex: float, revenues: list[float], opex_per_year: float) -> CashFlowSchedule:
    """Build a minimal CashFlowSchedule with zero carbon costs."""
    n = len(revenues)
    return CashFlowSchedule(
        years=list(range(n + 1)),
        capex=[capex] + [0.0] * n,
        revenue=[0.0] + revenues,
        opex=[0.0] + [opex_per_year] * n,
        carbon_cost=[0.0] * (n + 1),
    )


# ---------------------------------------------------------------------------
# NPV tests
# ---------------------------------------------------------------------------

class TestNPVCalculation:
    """Tests for calculate_npv with known textbook results."""

    def test_npv_basic_positive_result(self):
        """NPV > 0 for a profitable project at 10% discount rate.

        Cash flows: -1000 (t=0), +400, +400, +400, +400 (t=1..4)
        NPV = -1000 + 400/1.1 + 400/1.1^2 + 400/1.1^3 + 400/1.1^4
            = -1000 + 363.64 + 330.58 + 300.53 + 273.21
            = 267.95
        """
        schedule = CashFlowSchedule(
            years=[0, 1, 2, 3, 4],
            capex=[1000.0, 0.0, 0.0, 0.0, 0.0],
            revenue=[0.0, 400.0, 400.0, 400.0, 400.0],
            opex=[0.0] * 5,
            carbon_cost=[0.0] * 5,
        )
        result = calculate_npv(schedule, discount_rate=0.10)
        assert isinstance(result, NPVResult)
        assert result.npv == pytest.approx(267.95, rel=1e-3)

    def test_npv_zero_discount_rate_equals_sum(self):
        """At r=0, NPV equals sum of net cash flows."""
        capex = 500.0
        revenues = [200.0, 200.0, 200.0]
        opex = 50.0
        schedule = _simple_schedule(capex, revenues, opex)
        result = calculate_npv(schedule, discount_rate=0.0)
        # Net cash flow: -500 + (200-50)*3 = -500 + 450 = -50
        assert result.npv == pytest.approx(-50.0, abs=1e-6)

    def test_npv_negative_for_unprofitable_project(self):
        """NPV < 0 when revenues do not cover capex at given rate."""
        schedule = CashFlowSchedule(
            years=[0, 1, 2],
            capex=[1000.0, 0.0, 0.0],
            revenue=[0.0, 100.0, 100.0],
            opex=[0.0] * 3,
            carbon_cost=[0.0] * 3,
        )
        result = calculate_npv(schedule, discount_rate=0.10)
        assert result.npv < 0

    def test_npv_raises_on_mismatched_lengths(self):
        """ValueError when schedule arrays have different lengths."""
        with pytest.raises(ValueError, match="same length"):
            CashFlowSchedule(
                years=[0, 1, 2],
                capex=[1000.0, 0.0],  # wrong length
                revenue=[0.0, 400.0, 400.0],
                opex=[0.0] * 3,
                carbon_cost=[0.0] * 3,
            )

    def test_npv_raises_on_negative_discount_rate(self):
        """ValueError for discount rate < -1."""
        schedule = _simple_schedule(100.0, [50.0, 50.0], 10.0)
        with pytest.raises(ValueError, match="discount_rate"):
            calculate_npv(schedule, discount_rate=-1.5)

    def test_npv_net_cash_flows_stored(self):
        """NPVResult carries per-period net cash flows."""
        schedule = CashFlowSchedule(
            years=[0, 1, 2],
            capex=[500.0, 0.0, 0.0],
            revenue=[0.0, 300.0, 300.0],
            opex=[0.0, 50.0, 50.0],
            carbon_cost=[0.0] * 3,
        )
        result = calculate_npv(schedule, discount_rate=0.10)
        expected_net = [-500.0, 250.0, 250.0]
        for calc, exp in zip(result.net_cash_flows, expected_net):
            assert calc == pytest.approx(exp, abs=1e-6)

    def test_npv_with_multi_year_capex(self):
        """NPV correct when capex spans multiple years."""
        schedule = CashFlowSchedule(
            years=[0, 1, 2, 3],
            capex=[600.0, 400.0, 0.0, 0.0],
            revenue=[0.0, 0.0, 800.0, 800.0],
            opex=[0.0] * 4,
            carbon_cost=[0.0] * 4,
        )
        result = calculate_npv(schedule, discount_rate=0.10)
        # Manual: -600 + (-400/1.1) + 800/1.21 + 800/1.331
        #       = -600 - 363.636 + 661.157 + 601.052 = 298.573
        assert result.npv == pytest.approx(298.573, rel=1e-3)

    def test_npv_discount_rate_stored_on_result(self):
        """NPVResult stores the discount rate used."""
        schedule = _simple_schedule(100.0, [60.0, 60.0], 0.0)
        result = calculate_npv(schedule, discount_rate=0.12)
        assert result.discount_rate == pytest.approx(0.12)


# ---------------------------------------------------------------------------
# MIRR tests
# ---------------------------------------------------------------------------

class TestMIRRCalculation:
    """Tests for calculate_mirr with known results."""

    def test_mirr_basic_example(self):
        """MIRR textbook example.

        Cash flows: -120 (t=0), +200 (t=1), +200 (t=2), -100 (t=3), +400 (t=4)
        Finance rate = 10%, reinvestment rate = 12%

        PV of negatives (at 10%): 120 + 100/1.1^3 = 120 + 75.131 = 195.131
        FV of positives (at 12%): 200*1.12^3 + 200*1.12^2 + 0 + 400
                                 = 280.986 + 250.88 + 400 = 931.866
        MIRR = (931.866 / 195.131)^(1/4) - 1 = 0.4769... => ~47.7%
        """
        schedule = CashFlowSchedule(
            years=[0, 1, 2, 3, 4],
            capex=[120.0, 0.0, 0.0, 100.0, 0.0],
            revenue=[0.0, 200.0, 200.0, 0.0, 400.0],
            opex=[0.0] * 5,
            carbon_cost=[0.0] * 5,
        )
        result = calculate_mirr(
            schedule,
            finance_rate=0.10,
            reinvestment_rate=0.12,
        )
        assert isinstance(result, MIRRResult)
        assert result.mirr == pytest.approx(0.4769, rel=1e-2)

    def test_mirr_equals_irr_when_rates_equal_irr(self):
        """When finance_rate == reinvestment_rate == IRR, MIRR ≈ IRR.

        For cash flows [-1000, 400, 400, 400, 400] the IRR ≈ 21.86%.
        Setting both rates to IRR should give MIRR close to IRR.
        """
        schedule = CashFlowSchedule(
            years=[0, 1, 2, 3, 4],
            capex=[1000.0, 0.0, 0.0, 0.0, 0.0],
            revenue=[0.0, 400.0, 400.0, 400.0, 400.0],
            opex=[0.0] * 5,
            carbon_cost=[0.0] * 5,
        )
        irr_approx = 0.2186
        result = calculate_mirr(
            schedule,
            finance_rate=irr_approx,
            reinvestment_rate=irr_approx,
        )
        assert result.mirr == pytest.approx(irr_approx, rel=5e-2)

    def test_mirr_raises_on_all_positive_cash_flows(self):
        """ValueError when there are no negative net cash flows."""
        schedule = CashFlowSchedule(
            years=[0, 1, 2],
            capex=[0.0, 0.0, 0.0],
            revenue=[100.0, 200.0, 300.0],
            opex=[0.0] * 3,
            carbon_cost=[0.0] * 3,
        )
        with pytest.raises(ValueError, match="negative"):
            calculate_mirr(schedule, finance_rate=0.10, reinvestment_rate=0.10)

    def test_mirr_stores_rates(self):
        """MIRRResult stores finance and reinvestment rates."""
        schedule = CashFlowSchedule(
            years=[0, 1, 2, 3],
            capex=[500.0, 0.0, 0.0, 0.0],
            revenue=[0.0, 300.0, 300.0, 300.0],
            opex=[0.0] * 4,
            carbon_cost=[0.0] * 4,
        )
        result = calculate_mirr(schedule, finance_rate=0.08, reinvestment_rate=0.12)
        assert result.finance_rate == pytest.approx(0.08)
        assert result.reinvestment_rate == pytest.approx(0.12)

    def test_mirr_simple_case(self):
        """MIRR for [-1000, 0, 0, 1500] at finance=10%, reinvest=10%.

        PV negatives: 1000
        FV positives: 1500
        MIRR = (1500/1000)^(1/3) - 1 = 0.14471...
        """
        schedule = CashFlowSchedule(
            years=[0, 1, 2, 3],
            capex=[1000.0, 0.0, 0.0, 0.0],
            revenue=[0.0, 0.0, 0.0, 1500.0],
            opex=[0.0] * 4,
            carbon_cost=[0.0] * 4,
        )
        result = calculate_mirr(schedule, finance_rate=0.10, reinvestment_rate=0.10)
        assert result.mirr == pytest.approx(0.14471, rel=1e-3)


# ---------------------------------------------------------------------------
# build_cash_flow_schedule helper
# ---------------------------------------------------------------------------

class TestBuildCashFlowSchedule:
    """Tests for the convenience constructor from production volumes."""

    def test_build_schedule_correct_length(self):
        """Schedule length matches years_list."""
        production_boe = [100_000.0, 90_000.0, 80_000.0]
        schedule = build_cash_flow_schedule(
            years=[0, 1, 2, 3],
            production_boe_per_year=[0.0] + production_boe,
            oil_price_usd_per_boe=70.0,
            opex_usd_per_boe=15.0,
            capex_by_year=[500_000.0, 0.0, 0.0, 0.0],
            carbon_cost_usd_per_tonne=0.0,
            scope1_tco2_per_boe=0.0,
            scope2_tco2_per_boe=0.0,
        )
        assert len(schedule.years) == 4
        assert len(schedule.capex) == 4
        assert len(schedule.revenue) == 4
        assert len(schedule.opex) == 4
        assert len(schedule.carbon_cost) == 4

    def test_build_schedule_revenue_calculation(self):
        """Revenue = production * price per boe."""
        schedule = build_cash_flow_schedule(
            years=[0, 1],
            production_boe_per_year=[0.0, 10_000.0],
            oil_price_usd_per_boe=80.0,
            opex_usd_per_boe=0.0,
            capex_by_year=[0.0, 0.0],
            carbon_cost_usd_per_tonne=0.0,
            scope1_tco2_per_boe=0.0,
            scope2_tco2_per_boe=0.0,
        )
        assert schedule.revenue[1] == pytest.approx(800_000.0)

    def test_build_schedule_carbon_cost_calculation(self):
        """Carbon cost = production * (scope1 + scope2) * price_per_tonne."""
        schedule = build_cash_flow_schedule(
            years=[0, 1],
            production_boe_per_year=[0.0, 10_000.0],
            oil_price_usd_per_boe=0.0,
            opex_usd_per_boe=0.0,
            capex_by_year=[0.0, 0.0],
            carbon_cost_usd_per_tonne=50.0,
            scope1_tco2_per_boe=0.02,
            scope2_tco2_per_boe=0.03,
        )
        # CO2 = 10000 * (0.02 + 0.03) = 500 tonne
        # cost = 500 * 50 = 25000
        assert schedule.carbon_cost[1] == pytest.approx(25_000.0)

    def test_build_schedule_opex_calculation(self):
        """Opex = production * opex_per_boe."""
        schedule = build_cash_flow_schedule(
            years=[0, 1, 2],
            production_boe_per_year=[0.0, 5_000.0, 4_000.0],
            oil_price_usd_per_boe=0.0,
            opex_usd_per_boe=20.0,
            capex_by_year=[0.0, 0.0, 0.0],
            carbon_cost_usd_per_tonne=0.0,
            scope1_tco2_per_boe=0.0,
            scope2_tco2_per_boe=0.0,
        )
        assert schedule.opex[1] == pytest.approx(100_000.0)
        assert schedule.opex[2] == pytest.approx(80_000.0)
