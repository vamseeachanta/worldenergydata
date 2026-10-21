"""Schedule migration tests; expected values are independent hand calculations.

Synthetic inputs below are chosen for arithmetic, not field assumptions.
Equations: numpy-financial v1.0.0, npv/mirr/irr docstrings (2019).
FDAS trimming: core/financial.py, excel_like_mirr (2025).
"""

import numpy as np
import pytest

from worldenergydata.economics.carbon import carbon_npv_curve
from worldenergydata.economics.cash_flow import (
    CashFlowSchedule,
    build_cash_flow_schedule,
)
from worldenergydata.fdas.api import EconomicsQuery
from worldenergydata.fdas.core.financial import (
    calculate_all_metrics,
    calculate_irr,
    calculate_npv,
    excel_like_mirr,
)


def test_former_schedule_and_array_surfaces_have_npv_parity():
    """Net = [-100, 121]; -100 + 121/1.1 = 10 at the first period.

    Revenue 141 less opex 10 and carbon 10 gives 121. The annual rate
    0.1 is a synthetic input. Relative tolerances are pytest defaults.
    """
    schedule = CashFlowSchedule(
        years=[2024, 2025],
        capex=[100, 0],
        revenue=[0, 141],
        opex=[0, 10],
        carbon_cost=[0, 10],
        emission_tco2_per_period=[0, 1],
    )
    assert schedule.net_cashflows().tolist() == [-100, 121]
    assert calculate_npv(
        schedule.net_cashflows(), 0.1, period="annual"
    ) == pytest.approx(10)
    assert EconomicsQuery.npv([-100, 121], 0.1, period="annual") == pytest.approx(10)
    assert carbon_npv_curve(schedule, 0.1, np.array([10])).npv_values[
        0
    ] == pytest.approx(10)


@pytest.mark.parametrize("period", ["annual", "monthly"])
def test_former_annual_mirr_and_fdas_array_parity(period):
    """[-100, 121] has period IRR and MIRR 0.21; annual = 1.21**12-1
    for monthly inputs, or 0.21 for annual inputs. No intermediate positive
    cash flow means reinvestment has no effect. Synthetic rates are inputs.
    """
    schedule = CashFlowSchedule([0, 1], [100, 0], [0, 121], [0, 0], [0, 0])
    cf = schedule.net_cashflows()
    expected_annual = 1.21**12 - 1 if period == "monthly" else 0.21
    for actual in (
        excel_like_mirr(cf, 0.1, 0.2, period=period),
        EconomicsQuery.mirr(cf, 0.1, reinvestment_rate=0.2, period=period),
        calculate_irr(cf, period=period),
    ):
        assert actual == pytest.approx((0.21, expected_annual))
    assert calculate_all_metrics(cf, 0.1, period=period)[
        "mirr_annual"
    ] == pytest.approx(expected_annual)


def test_mirr_preserves_fdas_zero_trimming():
    """[0,-100,0,121,0] trims to [-100,0,121]: sqrt(121/100)-1=0.1.

    Ordinary NPV keeps the leading zero: -100/1.1 + 121/1.1**3.
    """
    cf = np.array([0, -100, 0, 121, 0])
    assert excel_like_mirr(cf, 0.1, period="annual") == pytest.approx((0.1, 0.1))
    assert calculate_npv(cf, 0.1, period="annual") == pytest.approx(
        -100 / 1.1 + 121 / 1.1**3
    )


def test_mirr_two_rates_hand_calculation():
    """PV(-) = 120 + 100/1.1**3; FV(+) = 200*1.12**3 + 200*1.12**2 + 400.

    MIRR=(FV/PV)**(1/4)-1; synthetic annual flows [-120,200,200,-100,400].
    """
    expected = ((200 * 1.12**3 + 200 * 1.12**2 + 400) / (120 + 100 / 1.1**3)) ** (
        1 / 4
    ) - 1
    assert excel_like_mirr(
        np.array([-120, 200, 200, -100, 400]), 0.1, 0.12, period="annual"
    ) == pytest.approx((expected, expected))


@pytest.mark.parametrize("flows", [[0, 0], [100, 121], [-100, -121]])
def test_mirr_undefined_without_both_signs(flows):
    """FDAS convention: missing either sign produces NaN, not an investment return."""
    assert all(
        np.isnan(v) for v in excel_like_mirr(np.array(flows), 0.1, period="annual")
    )


def test_schedule_length_validation():
    with pytest.raises(ValueError, match="same length"):
        CashFlowSchedule([0, 1], [100], [0, 121], [0, 0], [0, 0])
    with pytest.raises(ValueError, match="emission"):
        CashFlowSchedule([0], [100], [0], [0], [0], [0, 1])


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


@pytest.mark.parametrize(
    "flows,rate,expected",
    [
        ([-500, 150, 150, 150], 0, -50),
        ([-600, -400, 800, 800], 0.1, -600 - 400 / 1.1 + 800 / 1.1**2 + 800 / 1.1**3),
        ([-1000, 100, 100], 0.1, -1000 + 100 / 1.1 + 100 / 1.1**2),
    ],
)
def test_schedule_accounting_preserves_former_npv_cases(flows, rate, expected):
    """Independent hand sums retain zero-rate, staged-capex and loss cases.

    Synthetic cases: -500+3*150=-50; -600-400/1.1+800/1.1**2+800/1.1**3;
    -1000+100/1.1+100/1.1**2. Equation: numpy-financial v1.0.0 (2019), NPV.
    """
    schedule = CashFlowSchedule(
        list(range(len(flows))),
        [max(-cf, 0) for cf in flows],
        [max(cf, 0) for cf in flows],
        [0] * len(flows),
        [0] * len(flows),
    )
    assert calculate_npv(
        schedule.net_cashflows(), rate, period="annual"
    ) == pytest.approx(expected)
