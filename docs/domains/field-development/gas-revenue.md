# Monthly gas revenue

The shared FDAS cashflow engine accepts `gas_prices`, an optional dictionary
mapping `YYYY-MM` to realized **USD/Mcf**. This uses the same monthly time base
as the oil deck. Monthly gas revenue equals `MONTHLY_GAS_MCF * gas_prices[month]`.
Oil and gas revenue are added before the existing royalty and net-cashflow
calculations; existing NPV functions consume the resulting net cashflows.

The price-times-volume identity is consistent with EIA's
[Natural Gas Prices: Definitions, Sources and Explanatory Notes](https://www.eia.gov/dnav/ng/TblDefs/ng_pri_sum_tbldef2.asp),
"Average Price of Deliveries to Consumers" (undated; accessed 2026-10-19),
which defines average price as reported revenue divided by associated sales
volume. This supports the arithmetic only; no EIA price series or Spanish
fiscal assumption is inferred from it.

Gas-enabled cashflows expose `gas_production_mcf`, `gas_revenue_usd`, and
`total_revenue_usd` alongside the oil line. Without a gas deck, gas is unpriced
and the legacy oil-only row schema and values are retained. With a deck, every
production month requires an explicit finite nonnegative price and volume;
zero prices are permitted. Duplicate production months are rejected.

The deck contains realized monthly prices; any escalation is supplied in those
prices, following the oil convention. Prices in USD/MMBtu must be converted by
the caller using an explicit, sourced heating-value input before this API is
called. The engine introduces no heating-value constant. The Spain loader's
existing approximate `GWH_TO_MCF` conversion is retained unchanged, as documented
in its source and the [Spain reference issue](https://github.com/vamseeachanta/worldenergydata/issues/763).

```python
# SYNTHETIC illustration only; this is not a market price series.
synthetic_gas_prices = {"2025-01": 3.0, "2025-02": 3.0}
cashflows = engine.generate_monthly_cashflow(
    production_monthly, drilling_timeline, oil_prices, first_production_date,
    gas_prices=synthetic_gas_prices,
)
```

`run_spain_reference_chain` accepts the same `gas_prices` keyword. Its gross
revenue metric includes both commodities, including for a pure-gas field.
Its `pre_tax_metrics` also exposes `oil_revenue_usd` and `gas_revenue_usd`,
summed from the engine's monthly commodity lines. With no gas deck,
`gas_revenue_usd` is `None` (JSON `null`): a gas value is not established.
With an explicit zero-price deck it is numeric zero. `gross_revenue_usd`
retains its existing oil-only value when the gas deck is omitted; it does
not establish a valuation of unpriced gas. These fields are additive;
existing aggregate revenue, royalty, cost and cashflow values are unchanged.

The chain remains labeled `chain_plumbing_pre_tax`: the existing engine has no
income-tax calculation, and no gas-specific operating-cost model is added.
Missing drilling inputs and the onshore development-model caveat remain
limitations on economic interpretation.

Tests use only labeled synthetic prices and production. No real gas-price
series is acquired for this change. Public-source candidates for subsequent
price curation include EIA natural-gas price statistics and Eurostat gas-price
statistics; their terms, access, units, and suitability require verification
before acquisition or use.
