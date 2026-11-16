"""Illustrative scenarios; independent expected cash-flow arithmetic."""
from dataclasses import replace

import pytest

from worldenergydata.economics.scenario_inputs import (
    Expenditure, Periods, ScenarioInputs, WellSchedule,
)
from worldenergydata.economics.scenario import compare_scenarios, evaluate_scenario


def example(name='illustrative example'):
    return ScenarioInputs(
        name=name, periods=Periods(1.0, (300.0,) * 3),
        wells=(WellSchedule(0, 0, 0, 0, 800.0, (1.0, 0.5, 0.5), (0.0,) * 3),),
        expenditures=(Expenditure(0, 'capital', 2500000.0),
                      Expenditure(1, 'operating', 20000.0)),
        oil_prices_usd_per_barrel=(60.0,) * 3,
        variable_costs_usd_per_barrel=(20.0,) * 3,
        net_margin_fractions=(0.8,) * 3,
        discount_rate_per_period=0.08, first_discount_period=1,
    )


def test_complete_single_well_scenario():
    result = evaluate_scenario(example())
    volumes = (800 * 300, 400 * 300, 200 * 300)
    margins = tuple(v * (60 - 20) * 0.8 for v in volumes)
    expected = (margins[0] - 2500000, margins[1] - 20000, margins[2])
    assert result.production.volumes_barrels == pytest.approx(volumes)
    assert result.gross_revenue_usd == pytest.approx(tuple(v * 60 for v in volumes))
    assert result.variable_operating_cost_usd == pytest.approx(tuple(v * 20 for v in volumes))
    assert result.net_margin_revenue_usd == pytest.approx(margins)
    assert result.net_cash_flow_usd == pytest.approx(expected)
    assert result.cumulative_cash_flow_usd == pytest.approx((
        expected[0], expected[0] + expected[1], sum(expected)))
    assert result.npv_usd == pytest.approx(
        expected[0] / 1.08 + expected[1] / 1.08 ** 2 + expected[2] / 1.08 ** 3)


def test_multiple_wells_and_no_well_limit():
    inputs = example()
    doubled = evaluate_scenario(replace(inputs, wells=inputs.wells * 2))
    assert doubled.production.rates_barrels_per_day == (1600, 800, 400)
    dry = evaluate_scenario(replace(inputs, wells=()))
    assert dry.net_cash_flow_usd == pytest.approx((-2500000, -20000, 0))
    assert dry.npv_usd == pytest.approx(-2500000 / 1.08 - 20000 / 1.08 ** 2)


def test_comparison_retains_inputs_and_reports_incremental_npv():
    base = example('illustrative baseline')
    alternative = replace(base, name='illustrative alternative', expenditures=())
    comparison = compare_scenarios((base, alternative))
    assert tuple(item.name for item in comparison.scenarios) == (base.name, alternative.name)
    assert comparison.incremental_npv_usd[0] == 0.0
    assert comparison.incremental_npv_usd[1] == pytest.approx(
        2500000 / 1.08 + 20000 / 1.08 ** 2)
    with pytest.raises(ValueError):
        compare_scenarios((base, replace(alternative, first_discount_period=0)))
    with pytest.raises(ValueError):
        compare_scenarios((base, replace(alternative, periods=Periods(0.5, (300.0,) * 3))))
    with pytest.raises(ValueError):
        compare_scenarios((base, replace(alternative, name=base.name)))
    with pytest.raises(ValueError):
        compare_scenarios(())


@pytest.mark.parametrize('changes', [
    {'net_margin_fractions': (1.2,) * 3},
    {'oil_prices_usd_per_barrel': (60.0,)},
    {'variable_costs_usd_per_barrel': (-20.0,) * 3},
    {'wells': []}, {'discount_rate_per_period': float('nan')},
])
def test_invalid_scenario_inputs(changes):
    with pytest.raises(ValueError):
        replace(example(), **changes)


def test_variable_days_prices_and_zero_margin_share():
    # Illustrative example: zero days, zero share, then a negative margin.
    inputs = replace(
        example(), periods=Periods(0.5, (0.0, 100.0, 200.0)),
        wells=(WellSchedule(0, 0, 0, 0, 800.0, (1.0,) * 3, (0.0,) * 3),),
        expenditures=(), oil_prices_usd_per_barrel=(20.0, 40.0, 10.0),
        variable_costs_usd_per_barrel=(25.0, 30.0, 15.0),
        net_margin_fractions=(1.0, 0.0, 0.5), first_discount_period=0,
    )
    result = evaluate_scenario(inputs)
    assert result.net_cash_flow_usd == (0.0, 0.0, 800 * 200 * (10 - 15) * 0.5)
    assert result.npv_usd == pytest.approx(800 * 200 * (10 - 15) * 0.5 / 1.08 ** 2)
