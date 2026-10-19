"""Opt-in annual income-tax bridge with explicit policy and tax-basis inputs.

Equation reference: IRS Instructions for Form 1120 (2025), line 30, Net
operating loss (NOL), and Schedule J, line 1a (Income Tax):
https://www.irs.gov/instructions/i1120

This models one non-expiring, carryforward-only NOL pool with one policy over
the supplied years. It does not implement a complete corporate tax return.
The caller supplies already adjusted taxable income and eligible new NOLs;
neither is inferred from cashflow. Pre-existing loss vintages, carrybacks,
special deductions, credits, minimum taxes and ownership-change restrictions
require separate treatment before this bridge is applicable.

No fiscal rate, loss limit or opening balance has a default. The helper does
not read or promote any assumption deck or alter the monthly cashflow engine.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Real


def _amount(name: str, value: float, *, nonnegative: bool = False) -> float:
    """Reject missing, boolean and non-finite values without coercing strings."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    # Zero is the algebraic lower bound of a nonnegative amount, not a rate.
    if nonnegative and number < 0:
        raise ValueError(f"{name} must be nonnegative")
    return number


@dataclass(frozen=True)
class IncomeTaxPolicy:
    """Required fractional rates and provenance for one homogeneous NOL pool.

    The source and assumption version describe the caller's selected scenario;
    they do not establish that it has been accepted as a canonical basis.
    """

    corporate_tax_rate: float
    nol_offset_limit: float
    source: str
    assumption_version: str

    def __post_init__(self) -> None:
        for name in ("corporate_tax_rate", "nol_offset_limit"):
            fraction = _amount(name, getattr(self, name), nonnegative=True)
            # Unity is the definition of a whole fraction, not a fiscal default.
            if fraction > 1:
                raise ValueError(f"{name} must be a fraction between zero and one")
        for name in ("source", "assumption_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")


@dataclass(frozen=True)
class AnnualTaxInput:
    """One complete tax year; all amounts are USD on the same interest basis.

    ``taxable_income_before_nol_usd`` is nonnegative income after caller-provided
    tax adjustments but before this pool's deduction. In a loss year it is zero
    and ``nol_generated_usd`` is the separately established eligible tax loss.
    CAPEX, IDC, depreciation, depletion and other deductions are not inferred.
    ``pre_tax_cashflow_usd`` may be negative even when taxable income is positive.
    """

    year: int
    pre_tax_cashflow_usd: float
    taxable_income_before_nol_usd: float
    nol_generated_usd: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.year, bool)
            or not isinstance(self.year, int)
            or self.year <= 0
        ):
            raise ValueError("year must be a positive integer")
        _amount("pre_tax_cashflow_usd", self.pre_tax_cashflow_usd)
        income = _amount(
            "taxable_income_before_nol_usd",
            self.taxable_income_before_nol_usd,
            nonnegative=True,
        )
        loss = _amount("nol_generated_usd", self.nol_generated_usd, nonnegative=True)
        if income > 0 and loss > 0:
            raise ValueError("a year cannot have both taxable profit and a new NOL")


@dataclass(frozen=True)
class AnnualTaxResult:
    """Auditable annual bridge, including the input basis and NOL roll-forward."""

    year: int
    pre_tax_cashflow_usd: float
    taxable_income_before_nol_usd: float
    nol_opening_usd: float
    nol_generated_usd: float
    nol_used_usd: float
    nol_closing_usd: float
    taxable_income_usd: float
    income_tax_usd: float
    after_tax_cashflow_usd: float


@dataclass(frozen=True)
class AnnualTaxSchedule:
    """Results retain the exact policy provenance and initial loss balance."""

    policy: IncomeTaxPolicy
    opening_nol_usd: float
    years: tuple[AnnualTaxResult, ...]


def calculate_annual_income_tax(
    years: Iterable[AnnualTaxInput],
    *,
    policy: IncomeTaxPolicy,
    opening_nol_usd: float,
) -> AnnualTaxSchedule:
    """Apply a caller-selected carryforward policy to consecutive tax years.

    With income I, opening loss L, eligible new loss G, offset fraction f and
    corporate rate r: used=min(L, f*I), taxable=I-used, tax=r*taxable,
    closing=L-used+G, after-tax cash=pre-tax cash-tax.

    The deduction and tax equations follow IRS Instructions for Form 1120
    (2025), line 30 NOL and Schedule J line 1a. The loss roll-forward is the
    conservation identity for the single pool; the cashflow bridge subtracts
    the computed tax exactly once. No loss-year refund is assumed. Tax is
    charged in the same annual period; payment timing is outside this helper.

    Missing years, duplicate years and unsorted years raise ValueError; include
    explicit zero-income years to carry losses through idle periods. Rates are
    constant across this schedule; split policy changes into separate schedules
    carrying the last closing loss into the next opening balance.
    """
    if not isinstance(policy, IncomeTaxPolicy):
        raise TypeError("policy must be an IncomeTaxPolicy")
    opening = _amount("opening_nol_usd", opening_nol_usd, nonnegative=True)
    inputs = tuple(years)
    if not inputs:
        raise ValueError("at least one complete tax year is required")
    previous_year = None
    for row in inputs:
        if not isinstance(row, AnnualTaxInput):
            raise TypeError("years must contain AnnualTaxInput values")
        # Adding one defines consecutive integer years; it is not a time basis.
        if previous_year is not None and row.year != previous_year + 1:
            raise ValueError("tax years must be ordered and consecutive")
        previous_year = row.year

    results = []
    balance = opening
    for row in inputs:
        income = float(row.taxable_income_before_nol_usd)
        generated = float(row.nol_generated_usd)
        # IRS Form 1120 instructions (2025), line 30 NOL: lesser of available
        # carryforward and the selected fraction of eligible taxable income.
        used = min(balance, float(policy.nol_offset_limit) * income)
        taxable = income - used
        # IRS Form 1120 instructions (2025), Schedule J line 1a: rate * income.
        tax = float(policy.corporate_tax_rate) * taxable
        closing = _amount("closing NOL", balance - used + generated, nonnegative=True)
        cash = _amount("after-tax cashflow", float(row.pre_tax_cashflow_usd) - tax)
        results.append(
            AnnualTaxResult(
                year=row.year,
                pre_tax_cashflow_usd=float(row.pre_tax_cashflow_usd),
                taxable_income_before_nol_usd=income,
                nol_opening_usd=balance,
                nol_generated_usd=generated,
                nol_used_usd=used,
                nol_closing_usd=closing,
                taxable_income_usd=taxable,
                income_tax_usd=tax,
                after_tax_cashflow_usd=cash,
            )
        )
        balance = closing
    return AnnualTaxSchedule(
        policy=policy, opening_nol_usd=opening, years=tuple(results)
    )
