"""Check legacy timing adapters against independent hand calculations."""

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
    calculate_npv as bsee_npv,
)
from worldenergydata.economics.dcf import CashFlowSchedule
from worldenergydata.economics.dcf import calculate_npv as schedule_npv
from worldenergydata.fdas.core.financial import calculate_npv as fdas_npv
from worldenergydata.fdas.core.financial import calculate_trimmed_npv
from worldenergydata.fdas.data.production import ProductionForecaster
from worldenergydata.production.forecast import ArpsDeclineCurve
from worldenergydata.well_production_dashboard.field_aggregation import (
    FieldEconomicSummary,
)
from worldenergydata.well_production_dashboard.views_decline import DeclineCurveAnalyzer
from worldenergydata.well_production_dashboard.views_financial import (
    EconomicMetricsCalculator,
)
from worldenergydata.well_production_dashboard.well_production import WellMetrics


def test_npv_adapters_keep_time_zero():
    """Hand calculation: -100 + 121/1.1 = 10, with rate per period.

    Equation: NumPy Financial 1.0.0 (2019), npv Notes.
    The schedule's years are labels, not irregular discount times.
    """
    flows = np.array([-100, 121])
    schedule = CashFlowSchedule([2020, 2021], [100, 0], [0, 121], [0, 0], [0, 0])
    result = schedule_npv(schedule, 0.1)
    assert result.npv == pytest.approx(10)
    np.testing.assert_allclose(result.discounted_cash_flows, [-100, 110])
    assert fdas_npv(flows, 0.1, period="annual") == pytest.approx(10)
    assert bsee_npv(flows, 0.1) == pytest.approx(10)
    assert EconomicMetricsCalculator().calculate_npv(flows, 0.1) == pytest.approx(10)
    assert WellMetrics.calculate_npv(flows.tolist(), 0.1) == pytest.approx(10)


def test_field_npv_keeps_capex_in_first_period():
    """Hand calculation: revenues [10,121], opex [10,0], capex=100.

    Net flows [-100,121] at r=.1 give -100+121/1.1=10.
    Equation: NumPy Financial 1.0.0 (2019), npv Notes.
    """
    revenue = pd.Series([10.0, 121.0])
    opex = pd.Series([10.0, 0.0])
    assert FieldEconomicSummary().calculate_field_npv(revenue, opex, 100, 0.1) == (
        pytest.approx(10)
    )
    np.testing.assert_array_equal(revenue, [10, 121])


def test_monthly_conversion_and_trimming():
    """Hand calculation: annual r=.1 and 12 monthly periods discount 121 to 110.

    Twelve months per year is the calendar convention of the FDAS adapter.
    Leading zeros remain periods: [0,-100,121] at r=.1 gives 10/1.1.
    Explicit trimming instead gives 10 at its re-based time zero.
    Equation: NumPy Financial 1.0.0 (2019), npv Notes.
    """
    flows = np.zeros(13)
    flows[0], flows[12] = -100, 121
    assert fdas_npv(flows, 0.1) == pytest.approx(10)
    padded = np.array([0, -100, 121, 0])
    assert fdas_npv(padded, 0.1, "annual") == pytest.approx(10 / 1.1)
    assert calculate_trimmed_npv(padded, 0.1, "annual") == pytest.approx(10)


@pytest.mark.parametrize("effective_decline,answer", [(0, 100), (0.75, 25), (1, 0)])
def test_fdas_effective_annual_decline(effective_decline, answer):
    """Hand calculation at one year: 100*(1-effective decline).

    Manual section 2.1.1 at one year (accessed 2026-10-19), D=-ln(1-d).
    Synthetic initial rate=100; effective d=0, .75, 1 gives 100,25,0.
    The first point remains 100, including complete depletion at d=1.
    """
    forecaster = ProductionForecaster(pd.DataFrame())
    rates = forecaster.exponential_decline(100, effective_decline, 13)
    assert rates[0] == 100
    assert rates[12] == pytest.approx(answer)


def test_fdas_nominal_hyperbolic_decline():
    """At one year qi=100,D=1,b=.5: 100/(1+.5)**2=100/2.25.

    For b=0,D=ln(4), q=100/4=25. Manual sections 2.1.1–2.1.2.
    """
    forecaster = ProductionForecaster(pd.DataFrame())
    assert forecaster.hyperbolic_decline(100, 1, 0.5, 13)[12] == pytest.approx(
        100 / 2.25
    )
    assert forecaster.hyperbolic_decline(100, np.log(4), 0, 13)[12] == pytest.approx(25)


def test_dashboard_nominal_months_and_zero_b():
    """qi=100,Dannual=12*ln(2): monthly values halve to 50,25.

    Fitted values start at zero; forecast starts at month one. Setting b=0
    gives the same exponential limit. Manual sections 2.1–2.1.1.
    """
    analyzer = DeclineCurveAnalyzer()
    params = {"initial_production": 100, "decline_rate": 12 * np.log(2), "b_factor": 0}
    np.testing.assert_allclose(
        analyzer.calculate_fitted_values(params, 3), [100, 50, 25]
    )
    np.testing.assert_allclose(analyzer.forecast_production(params, 2), [50, 25])
    np.testing.assert_allclose(
        analyzer.forecast_production(params, 2, "hyperbolic"), [50, 25]
    )


@pytest.mark.parametrize(
    "model,answer",
    [("exponential", 100 / np.e), ("harmonic", 50), ("hyperbolic", 100 / 2.25)],
)
def test_production_forecast_uses_same_equations(model, answer):
    """At month 1, qi=100,D=1,b=.5 gives 100/e,50,100/2.25.

    Manual sections 2.1.1–2.1.3; synthetic parameters avoid fitting error.
    """
    frame = ArpsDeclineCurve()._build_forecast_df(100, 1, 0.5, model, 1)
    assert frame.iloc[0].rate_bbl == pytest.approx(answer)


def test_worked_example():
    """Independent hand calculation: [-200,200,100] at r=.25 gives 24.

    qi=100 and D=ln(2) give sampled rates [50,25]; chosen price=4
    gives annual receipts [200,100]. NPV=-200+160+64=24.
    Equations and sampling assumption are documented in the example.
    """
    import runpy
    from pathlib import Path

    example = Path(__file__).resolve().parents[3] / "examples" / "decline_npv.py"
    result = runpy.run_path(str(example))["run_example"]()
    np.testing.assert_allclose(result["sampled_rates"], [50, 25])
    np.testing.assert_allclose(result["cash_flows"], [-200, 200, 100])
    assert result["npv"] == pytest.approx(24)
