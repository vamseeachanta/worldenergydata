# Shared decline and NPV calculations

Production forecasts, FDAS, economics schedules and dashboard metrics share the
numerical equations in `worldenergydata.common.decline` and
`worldenergydata.common.finance`. Existing domain entry points retain their
fitting, calendar conversion, trimming and result formats.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-19 | Centralize duplicated equations and document timing conventions to prevent drift. |

## Equations and sources

The public [decline-analysis manual](https://manual.whitson.com/modules/well-performance/decline-curve-analysis/),
web edition accessed 2026-10-19 (publication year unspecified), sections
2.1.1–2.1.4, gives these rate equations:

- Exponential: `q(t) = qi * exp(-D*t)`.
- Hyperbolic: `q(t) = qi * (1 + b*D*t)**(-1/b)`.
- Harmonic: the hyperbolic case `b = 1`.
- At `b = 0`, the hyperbolic limit is exponential.

`D` is nominal decline and has reciprocal time units. The shared helpers do not
assume months or years. The hyperbolic implementation uses the equivalent
`exp(-log1p(b*D*t)/b)` form to avoid cancellation near zero exponent.

[NumPy Financial 1.0.0 (2019), `npv`, Notes and Warnings](https://raw.githubusercontent.com/numpy/numpy-financial/v1.0.0/numpy_financial/_financial.py)
defines `NPV = sum(CF[t] / (1+r)**t)` starting at time zero. The rate interval
must match the cash-flow interval. `discounted_cash_flows` returns the individual
terms; `net_present_value` returns their sum. A leading zero occupies a period.
An empty sum returns zero. The helpers evaluate equations; callers retain their
existing input validation and policies for invalid rates or arrays.

## Adapter conventions

| Entry point | Convention retained |
| --- | --- |
| `economics.dcf.calculate_npv` | Schedule labels do not change equally spaced discount indices; returns `NPVResult` and components. |
| `fdas.core.financial.calculate_npv` | Annual effective discount input; monthly conversion by compounding; first flow at time zero. |
| `fdas.core.financial.calculate_trimmed_npv` | Explicitly trims and re-bases the existing significant-flow range. |
| `bsee.analysis.financial.cash_flow_calculator.calculate_npv` | Input rate is already monthly. |
| Dashboard NPV helpers | Input rate is per cash-flow period; field capex is deducted at time zero. |
| `production.forecast.ArpsDeclineCurve` | Existing fitting, bounds, EUR and result schema; forecast begins at month one. |
| `fdas.data.production.ProductionForecaster` | Exponential accepts effective annual decline; hyperbolic accepts nominal annual decline and begins at time zero. |
| Dashboard `DeclineCurveAnalyzer` | Nominal annual decline converted to monthly; fitted curve begins at zero and forecast at month one. |

For effective annual decline `d`, the exponential adapter obtains
`D = -ln(1-d)` by evaluating the sourced exponential equation at one year.
The calendar conversion uses twelve months per year, as in the existing FDAS
adapter. Complete depletion retains the initial rate at time zero and gives
zero thereafter. A dashboard hyperbolic forecast with `b=0` now uses the
exponential limit rather than dividing by zero.

## Worked example

Run `python examples/decline_npv.py` in an environment containing the core package.
All inputs are synthetic, chosen to make the arithmetic visible:

| Input | Value |
| --- | --- |
| Initial rate | 100.0 volume/year |
| Nominal decline | `ln(2)` per year |
| Sample times | 1.0 and 2.0 years |
| Price | 4.0 currency/volume |
| Initial investment | 200.0 currency |
| Annual discount rate | 25.0% |

The rate equation gives sampled rates of 50.0 and 25.0 volume/year. For this
example only, each sample represents the assumed volume in a unit-length annual
bucket. Multiplying by price gives cash flows `[-200, 200, 100]`, with the initial
investment at time zero. The NPV calculation is
`-200 + 200/1.25 + 100/1.25**2 = -200 + 160 + 64 = 24.0` currency.
This sampling assumption is explicit: continuous cumulative production requires
integration of the decline curve instead.

Expected output:

```text
Sampled annual rates: 50.0, 25.0
Cash flows: -200.0, 200.0, 100.0
NPV: 24.0
```

## Coverage and limits

The tests use the published NumPy Financial example and independent hand
calculations for decline rates, time zero, leading zeros, trimming, monthly
conversion, capex placement and effective versus nominal decline. Existing
module suites cover fitting and domain behavior.

This consolidation does not qualify the dashboard's approximate hyperbolic
fitting method or reconcile its EUR convention with production forecasting.
Those are distinct algorithms requiring separate behavior decisions. Regional
forecast models and report wrappers around third-party financial functions
remain outside these adapters. No default engineering or economic assumption
is introduced by the shared helpers.
