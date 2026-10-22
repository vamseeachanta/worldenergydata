# Cashflow input and discounting example

Three synthetic monthly operating receipts of 100.0, -50.0 and 100.0 MM USD
have operating present value 150.0 MM USD at zero discount. With investment of
100.0 MM USD at first oil, project NPV is 50.0 MM USD. At a synthetic monthly
discount rate of 10.0 percent, project NPV is 37.2 MM USD. An unknown first-oil
date raises `FinancialInputError` and produces no valuation.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-22 | Add independent arithmetic and refusal examples for incomplete financial inputs. |

## Inputs and method

All amounts, dates and rates in this example are synthetic scenario inputs.
There is no new engineering coefficient or financial recommendation.

| Input | Value and convention |
| --- | --- |
| First oil | January 2024 |
| Operating cashflows | January 100.0, February -50.0, March 100.0 MM USD |
| Investment | 100.0 MM USD, at first oil |
| Zero rate | Annual and monthly effective rates both zero |
| Positive rate | Monthly effective rate 10.0 percent; annual effective input is `1.1**12 - 1` |
| Period origin | First-oil month is time zero; successive months have exponents one and two |

Present value is `PV = sum(CF[t] / (1 + r)**t)` with a rate matching the period.
Source: [NumPy v1.17 NPV Notes (2020)](https://numpy.org/doc/1.17/reference/generated/numpy.npv.html),
citing *Principles of Managerial Finance, Brief*, third edition (2003), page 346.
The Lower Tertiary summary uses an annual effective input converted to a monthly
effective rate. Field-development enrichment instead books investment at time
zero and annual operating receipts at year end. The UKCS comparator retains a
nominal annual input divided by twelve; these conventions are distinct.

## Independent answer

Zero discount preserves the loss month:

```text
Operating PV = 100 - 50 + 100 = 150.0 MM USD
Project NPV = 150 - 100 = 50.0 MM USD
Cumulative operating receipts = [100, 50, 150] MM USD
```

With monthly discount `r = 0.1`:

```text
Operating PV = 100 - 50/1.1 + 100/1.21 = 16600/121 MM USD
Project NPV = 16600/121 - 100 = 4500/121 MM USD = 37.2 MM USD
```

The regression test retains the exact fractions rather than using rounded
answers: `tests/unit/lower_tertiary/test_npv.py::test_three_month_worked_example`.
It runs both rates and then removes `first_oil`; evaluation must raise
`FinancialInputError` with `field == "first_oil"`. A missing, non-finite or
nonpositive `capex.total_mm_usd` is refused too. Inventory loading may retain an
unknown date as `None`, but the financial summary cannot evaluate it.

The portfolio OPEX sweep has a separate synthetic one-year example: investment
10.0 MM USD, volume 1.0 MMbbl, price 50.0 USD/bbl, zero royalty and discount.
Explicit zero OPEX gives `-10 + 1*50 = 40.0` MM USD; previously it was replaced by
the inherited 15.0 USD/bbl assumption and gave `-10 + 1*(50-15) = 25.0` MM USD.
The inherited value is documented in `portfolio_economics.DEFAULT_OPEX_PER_BOE`;
it is not independently qualified here. Absent OPEX retains that assumption.

## Limits and way forward

The summary retains its historical `PI = project NPV / investment`, which differs
from gross present value divided by investment. No historical report artifact
is regenerated. Fiscal assumptions, gas conversion, optional reporting totals
and source-date accuracy remain outside this arithmetic check.

The UKCS chain now requires an explicit drilling timeline and nonempty
production. Its output remains labelled pre-tax plumbing. FDAS drilling costs
currently multiply days by a rate named in MM USD/day and assign the result to
a USD cashflow field without conversion. This unit basis, omitted fixed OPEX and
facilities capital remain NOT_EVALUATED for investment use. Qualify these inputs
and units before interpreting chain cashflow as an investment result.
