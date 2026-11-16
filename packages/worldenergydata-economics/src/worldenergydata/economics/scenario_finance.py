"""Validated USD revenue, cash flow and discounting using shared dcf primitives.

Oil volumes [barrels] and prices [USD/barrel] are multiplied by the existing
schedule constructor. Net cash flow subtracts positive outflows. Discounting
uses dcf.calculate_npv at consecutive indices and shifts the origin by an
explicit integer offset. Rate is per supplied period; no annual conversion is
applied, despite the annual terminology of the underlying general formula.

Input gaps: price and cost bases, day counts upstream, rate period and origin
are caller responsibilities. Negative prices and net cash flows are permitted.
No fiscal model, calendar grouping, inflation or IRR is inferred.
"""
from math import isfinite

from .dcf import CashFlowSchedule, build_cash_flow_schedule, calculate_npv
from .scenario_inputs import _finite, _index, _series


def _aligned(*series: tuple[float, ...]) -> None:
    for values in series:
        _series(values, 'USD or volume series')
    if len({len(values) for values in series}) > 1:
        raise ValueError('All series must have the same horizon')


def revenue_usd(volumes_barrels: tuple[float, ...],
                prices_usd_per_barrel: tuple[float, ...]) -> tuple[float, ...]:
    """Gross USD revenue using shared production-times-price arithmetic."""
    _aligned(volumes_barrels, prices_usd_per_barrel)
    _series(volumes_barrels, 'volumes_barrels', 0.0)
    result = tuple(build_cash_flow_schedule(
        [0], [volume], price, 0.0, [0.0], 0.0, 0.0, 0.0).revenue[0]
        for volume, price in zip(volumes_barrels, prices_usd_per_barrel))
    _series(result, 'revenue_usd')
    return result


def _schedule(revenue: tuple[float, ...], capital: tuple[float, ...],
              operating: tuple[float, ...]) -> CashFlowSchedule:
    _aligned(revenue, capital, operating)
    return CashFlowSchedule(list(range(len(revenue))), list(capital),
                            list(revenue), list(operating), [0.0] * len(revenue))


def net_cash_flow_usd(revenue_usd: tuple[float, ...],
                       capital_usd: tuple[float, ...],
                       operating_usd: tuple[float, ...]) -> tuple[float, ...]:
    """Subtract explicit capital and operating outflows, preserving all slots."""
    _series(capital_usd, 'capital_usd', 0.0)
    _series(operating_usd, 'operating_usd', 0.0)
    result = tuple(calculate_npv(_schedule(
        revenue_usd, capital_usd, operating_usd), 0.0).net_cash_flows)
    _series(result, 'net_cash_flow_usd')
    return result


def discounted_cash_flow_usd(cash_flows_usd: tuple[float, ...],
                              discount_rate_per_period: float,
                              first_discount_period: int) -> tuple[float, ...]:
    """Discount at indices first_discount_period + i; zero retains time zero."""
    _series(cash_flows_usd, 'cash_flows_usd')
    _finite(discount_rate_per_period, 'discount_rate_per_period')
    _index(first_discount_period, 'first_discount_period')
    if discount_rate_per_period <= -1:
        raise ValueError('Discount rate must exceed minus one')
    zeros = (0.0,) * len(cash_flows_usd)
    discounted = calculate_npv(_schedule(cash_flows_usd, zeros, zeros),
                               discount_rate_per_period).discounted_cash_flows
    try:
        shift = (1 + discount_rate_per_period) ** first_discount_period
        if not isfinite(shift) or shift == 0:
            raise ValueError('Discount origin exceeds numerical range')
        result = tuple(value / shift for value in discounted)
    except OverflowError as exc:
        raise ValueError('Discount origin exceeds numerical range') from exc
    _series(result, 'discounted_cash_flow_usd')
    return result


def npv_usd(cash_flows_usd: tuple[float, ...], discount_rate_per_period: float,
            first_discount_period: int) -> float:
    """Sum shared-engine discounted flows [USD], with explicit period origin."""
    value = sum(discounted_cash_flow_usd(
        cash_flows_usd, discount_rate_per_period, first_discount_period))
    _finite(value, 'npv_usd')
    return value
