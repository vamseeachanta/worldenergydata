# Annual corporate income-tax bridge

## Summary

`calculate_annual_income_tax` provides an opt-in annual corporate tax and
net operating loss (NOL) roll-forward for issue #651. Every tax policy value,
opening balance, taxable income and eligible new loss is an explicit input.
The result retains policy provenance and bridges pre-tax to after-tax cashflow.
Existing monthly economics and assumption decks continue to use their existing
interfaces. This helper does not make an assumption deck canonical.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-19 | Added an annual bridge to test explicit tax and loss inputs before integration. |
| Update | 2026-10-22 | Clarified nominal money and loss-vintage eligibility, accepted NumPy integer years, and moved the guide out of package data. |

## Scope and source

The equation source is the [IRS Instructions for Form 1120 (2025)](https://www.irs.gov/instructions/i1120),
line 30, **Net operating loss (NOL)**, and Schedule J, line 1a, **Income Tax**.
The public page was read on 2026-10-19 with HTTP status 200. That edition supplies
the example corporate rate of 21% and a conditional NOL offset limit of 80%.
These values are example inputs, not defaults or approved cost-basis changes.
The source also describes older loss vintages and special limitations that this
single-pool helper does not implement.

The caller must establish applicability for each supplied tax year. One schedule
uses one non-expiring carryforward pool and one policy. Mixed loss vintages,
carrybacks, ownership changes and special restrictions require separate treatment.
The 80% example limit covers losses originating in tax years beginning after
2017 when deducted in tax years beginning after 2020. Its income base excludes
the NOL deduction and deductions under sections 199A and 250; it does not apply
the 80% cap to a pre-2018 loss pool. See
[26 USC 172(a)(2)](https://www.law.cornell.edu/uscode/text/26/172), read on
2026-10-22 with HTTP status 200, and the IRS instructions cited above, reopened
on the same date with HTTP status 200. Mixed vintages require separate treatment,
including the older-loss adjustment to the income base.

In particular, the example policy must not be applied across the full historical
production window as though it were valid in every year.

## Equations

For each complete tax year let `I` be nonnegative taxable income before this
pool's NOL deduction, `L` opening eligible losses, `G` newly generated eligible
losses, `f` the selected offset fraction, `r` the selected corporate tax rate,
and `C` pre-tax cashflow:

- `used = min(L, f * I)` — Form 1120 (2025), line 30 NOL, restricted to one pool.
- `taxable = I - used` — taxable income after the selected deduction.
- `tax = r * taxable` — Form 1120 (2025), Schedule J, line 1a.
- `closing = L - used + G` — conservation of the eligible loss balance.
- `after_tax_cashflow = C - tax` — cashflow bridge, charging tax once.

The last two equations are accounting identities. No tax refund is credited for
a loss year. Tax is charged in the same annual period; payment-date modelling
is deferred. Every year must be supplied in consecutive ascending order, including
idle years. A policy change can be represented by separate schedules, passing
the previous closing NOL as the next opening NOL after checking pool eligibility.

## Example and independent check

All dollar amounts and years here are synthetic test inputs. The policy rates
are cited above; the test docstring writes out the hand calculation independently
of the helper. All amounts must be undiscounted nominal USD (money of each tax
year), using one consistent ownership share. The helper performs no inflation
adjustment or discounting.

```python
from worldenergydata.fdas.fiscal.income_tax import (
    AnnualTaxInput,
    IncomeTaxPolicy,
    calculate_annual_income_tax,
)

policy = IncomeTaxPolicy(
    # IRS Instructions for Form 1120 (2025), Schedule J line 1a; line 30 NOL.
    corporate_tax_rate=0.21,
    nol_offset_limit=0.80,
    source="IRS Instructions for Form 1120 (2025), Schedule J 1a; line 30 NOL",
    assumption_version="illustrative-tax-basis",
)
years = [
    AnnualTaxInput(2025, -1000, 0, 1000),
    AnnualTaxInput(2026, 500, 500, 0),
    AnnualTaxInput(2027, 1000, 1000, 0),
]
schedule = calculate_annual_income_tax(years, policy=policy, opening_nol_usd=0)
```

| Year | Opening NOL | New NOL | Used NOL | Closing NOL | Taxable income | Tax | After-tax cash |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025 | 0.0 | 1000.0 | 0.0 | 1000.0 | 0.0 | 0.0 | -1000.0 |
| 2026 | 1000.0 | 0.0 | 400.0 | 600.0 | 100.0 | 21.0 | 479.0 |
| 2027 | 600.0 | 0.0 | 600.0 | 0.0 | 400.0 | 84.0 | 916.0 |

The middle year uses `min(1000, 0.8 * 500) = 400`; the final year uses the
remaining 600. The tax amounts are `0.21 * 100 = 21` and `0.21 * 400 = 84`.

## Required inputs and later slices

Taxable income and eligible losses are deliberately separate from pre-tax
cashflow. A cash outflow for CAPEX is not automatically a tax deduction.
The helper rejects a year containing both positive taxable income and a new
NOL. Rates, amounts and years are validated; results and provenance are immutable.
Positive integer years include NumPy integer scalars taken from a DataFrame;
boolean and floating-point years remain invalid. Missing required inputs prevent
evaluation rather than selecting a fallback.

The following remain **NOT_EVALUATED** by this helper:

- Depreciation lives, depreciation schedules, IDC eligibility and amortisation.
- Depletion, special deductions, corporate minimum taxes and tax credits.
- Severance, ad-valorem charges and royalty-relief eligibility or volume limits.
- Loss-vintage ordering, expiry, carrybacks and ownership-change limits.
- Monthly tax-payment timing, discount reference dates and after-tax NPV.
- Regional drilling durations, refreshed costs and canonical deck adoption.

Slice 1 is this standalone annual bridge. Slice 2 requires accepted tax-basis
construction and monthly integration. Slice 3 requires accepted deck reconciliation
and versioned canonical workbook generation. Those later slices remain associated
with #899, #900, #901 and #1017; this change does not resolve their decisions.
