"""Pure USD cost rollup, activity costing and explicit period allocation.

Base costs are summed, engineering is applied to the base and contingency uses
its supplied inclusion basis. Activity cost is days times USD/day, optionally
rounded to a supplied USD increment with decimal half-up arithmetic. A zero
increment requests no rounding. Outflows are summed at explicit period indices.

Input gaps: component estimates, engineering and contingency fractions, their
basis, activity durations, day rates, rounding increments and expenditure timing
are required inputs. No cost estimate, productivity factor, currency-year basis
or scheduling allocation is inferred from a legacy engineering workbook.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .scenario_inputs import CostBreakdown, Expenditure, _finite, _index, _series


@dataclass(frozen=True)
class CostTotals:
    """Unscheduled component, engineering, contingency and total costs [USD]."""

    base_usd: float
    engineering_usd: float
    contingency_usd: float
    total_usd: float


def cost_breakdown(inputs: CostBreakdown) -> CostTotals:
    """Roll up base components and explicitly based percentage allowances."""
    base = sum(inputs.components_usd)
    engineering = base * inputs.engineering_fraction
    basis = base + engineering if inputs.contingency_includes_engineering else base
    contingency = basis * inputs.contingency_fraction
    total = base + engineering + contingency
    _series((base, engineering, contingency, total), 'cost totals', 0.0)
    return CostTotals(base, engineering, contingency, total)


def activity_cost_usd(duration_days: float, rate_usd_per_day: float,
                      rounding_increment_usd: float) -> float:
    """Duration times day rate, rounded to an explicit nonnegative increment."""
    for name, value in (('duration_days', duration_days),
                        ('rate_usd_per_day', rate_usd_per_day),
                        ('rounding_increment_usd', rounding_increment_usd)):
        _finite(value, name, 0.0)
    value = duration_days * rate_usd_per_day
    _finite(value, 'activity cost')
    if rounding_increment_usd == 0:
        return value
    increment = Decimal(str(rounding_increment_usd))
    decimal_value = Decimal(str(duration_days)) * Decimal(str(rate_usd_per_day))
    return float((decimal_value / increment).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP) * increment)


def expenditure_profile_usd(events: tuple[Expenditure, ...], period_count: int,
                             category: str) -> tuple[float, ...]:
    """Sum outflows of the selected category; reject all out-of-horizon events."""
    _index(period_count, 'period_count')
    if not isinstance(events, tuple) or category not in ('capital', 'operating'):
        raise ValueError('Immutable events and a valid category are required')
    result = [0.0] * period_count
    for event in events:
        if not isinstance(event, Expenditure) or event.period_index >= period_count:
            raise ValueError('Expenditure is invalid or outside the horizon')
        if event.category == category:
            result[event.period_index] += event.amount_usd
    _series(tuple(result), 'expenditure profile', 0.0)
    return tuple(result)
