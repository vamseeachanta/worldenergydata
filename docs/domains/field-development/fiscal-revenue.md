# Fiscal revenue and discounted cashflow

The FDAS cashflow engine uses fiscal-deck oil markers and annual discount rates
for pre-tax economics. A fiscal run requires explicit prices in USD/BBL;
missing observations and incompatible currencies raise `CashflowError`.
Income-tax terms remain metadata, so after-tax country parity is not established.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-19 | Document explicit benchmark pricing and dated discounting to prevent silent substitution of US assumptions. |

Table 1. Revision history.

## Oil pricing

`CashflowEngine.calculate_revenue` and `generate_monthly_cashflow` accept
`oil_prices_by_marker`, a mapping from `wti` or `brent` to monthly `YYYY-MM`
price series. A fiscal deck selects its own `price_marker`. An explicitly
supplied marker mapping is authoritative: a missing selected marker raises an
error. Without a marker mapping, the existing positional price dictionary is
WTI and can only serve a WTI fiscal deck. A Brent deck requires an explicit
Brent series, even if a positional WTI dictionary is present.

For each supplied production month:

```text
realized_price_usd_bbl = selected_price_usd_bbl + oil_differential_usd_bbl
oil_revenue_usd = oil_production_bbl * realized_price_usd_bbl
```

Revenue as price times quantity follows [OpenStax, Principles of Economics 3e
(2022), section 8.2](https://openstax.org/books/principles-economics-3e/pages/8-2-how-perfectly-competitive-firms-make-output-decisions).
The differential is a required caller decision when a nonzero differential is
needed; its default is no adjustment. No market price, conversion factor,
escalation or exchange rate is introduced. Finite negative oil prices remain
permitted. Volumes must be finite and nonnegative, prices and differentials
finite, and calculated revenue finite. Duplicate production months are rejected
before conversion to dictionaries on the fiscal or explicit-marker path.

The currency must be USD because costs and result fields use USD. Gas benchmark
markers cannot price barrels and are rejected by the oil seam. The existing
`gas_prices` API still accepts realized USD/Mcf separately; oil and gas revenues
are combined before royalties. The convenience function forwards both
`fiscal_terms` and `oil_prices_by_marker`.

```python
# prices_by_marker contains caller-supplied monthly USD/BBL observations.
rows = engine.generate_monthly_cashflow(
    production_monthly,
    drilling_timeline,
    {},
    first_oil_date,
    oil_prices_by_marker=prices_by_marker,
)
pre_tax_npv_usd = engine.calculate_npv(rows, discount_rate_annual=annual_rate)
```

Without a fiscal deck or marker mapping, the original oil-revenue path and
serialized cashflow fields are retained, including its legacy missing-price
fallback. The UK reference-chain scenario price is explicitly passed as Brent;
it remains an assumed flat price rather than a fetched market observation.

## Dated monthly NPV

`CashflowEngine.calculate_npv` accepts monthly cashflow rows. Rate precedence is
an explicit annual rate, then the fiscal deck rate, then the assumptions rate
only for a deckless engine. A fiscal deck that omits its rate requires an
explicit caller input; it does not inherit a US discount assumption.

The valuation month is the earliest supplied row, including an initial zero
cashflow. Rows are sorted and omitted calendar months receive zero cashflow.
Duplicate months, invalid `YYYY-MM` periods and nonfinite cashflows are rejected.
The existing `core.financial.calculate_npv` calculator is reused:

```text
monthly_rate = (1 + annual_rate) ** (1 / months_per_year) - 1
NPV = sum(cashflow_at_month_t / (1 + monthly_rate) ** t)
```

The discounted-cashflow equation follows [OpenStax, Principles of Finance
(2022), section 16.2, equation 16.2](https://openstax.org/books/principles-finance/pages/16-2-net-present-value-npv-method).
The monthly conversion and supported rate range follow the existing financial
calculator contract. Annual rates must exceed negative unity and cannot exceed
positive unity in that calculator. No trimming of zero-valued endpoints occurs.
The tests include independent hand calculations and the published cashflows in
table 16.3. That example's displayed total sums rounded terms; the regression
instead rounds once after independently summing the unrounded present values.

## Later slice: after-tax economics

No income-tax rate is applied by this change. Norway's existing tax helper
applies the special component after deducting ordinary tax, whereas its deck
records a combined marginal rate. Those bases require reconciliation before
parity can be asserted. The UK helper additionally deducts an investment
allowance that the fiscal deck does not describe. Effective dates, loss
handling, capital deductions, allowances and levy treatment require a sourced
contract before after-tax output is introduced. Existing country helpers and
shipped fiscal rates remain unchanged.
