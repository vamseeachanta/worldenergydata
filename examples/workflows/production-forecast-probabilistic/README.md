# Probabilistic production and economics

This offline example propagates **synthetic, independent** input distributions
through an Arps decline forecast and horizon NPV. It does not estimate a named
field's reserves. Public-field calibration remains unfinished under
[#833](https://github.com/vamseeachanta/worldenergydata/issues/833).

Run with the repository environment:

```sh
uv run python -m worldenergydata examples/workflows/production-forecast-probabilistic/input.yml
```

The router writes a sample matrix CSV, a monthly fan CSV, a summary JSON and a
self-contained HTML report beside the configured output directory. The frozen
synthetic report is `reports/production_forecast/index.html`; the site builder
copies it and adds a landing-page link. Output files are regenerated, not inputs.

## Inputs and units

All prior bounds and economics in `input.yml` are illustrative required inputs,
not inferred public-data spreads. The rate basis extends the adjacent
`production-forecast-arps/README.md` synthetic example. Study dimensions and seed
follow the issue's example plan; they are reproducibility settings, not accuracy
or convergence criteria.

| Input | Meaning and unit |
| --- | --- |
| `qi` | Rate at forecast time zero, bbl/month |
| `Di` | Nominal initial decline, 1/month |
| `b` | Dimensionless exponent, from exponential through harmonic |
| `economic_limit` | Abandonment rate, bbl/month |
| `oil_price`, `opex` | USD/bbl; OPEX here is variable cost only |
| `capex` | USD at time zero |
| `discount_rate` | Effective annual fraction supported by FDAS |
| `price_multipliers` | Optional nonnegative monthly deck factors applied to sampled price |
| `minimum_p10_npv_usd` | Optional user criterion for the lower non-exceedance NPV percentile |

Table 1. Caller-supplied inputs and their calculation basis.

Supported prior distributions are uniform (`low`, `high`), normal (`mean`,
`std`), lognormal (`median` or `mean_log`, plus `std_log`) and triangular (`low`,
`mode`, `high`). Invalid samples stop the study; there is no clipping or silent
resampling. Choose priors with physically valid support. Uncertain inputs
override the corresponding `base` inputs. Omitted base parameters are errors.

`engine: auto` prefers `digitalmodel.uncertainty` LHS and its percentile/rank
analytics. `engine: digitalmodel` requires that dependency; `engine: builtin`
explicitly selects the seeded SciPy naive-MC compatibility backend. The example
pins builtin for reproducibility. Neither a missing transitive dependency nor
an error in an installed shared engine triggers silent fallback.

## Method and independent calculation

[ResInsight, Decline Curve Analysis](https://resinsight.org/plot-window/declinecurveanalysis/)
(accessed 2026), rate-time and cumulative sections, gives exponential
`q(t)=qi exp(-Di t)`, hyperbolic `q(t)=qi(1+b Di t)^(-1/b)`, and harmonic
`q(t)=qi/(1+Di t)`. The corresponding cumulative integrals are evaluated at
monthly boundaries clipped to the abandonment time. Their differences give
monthly barrels, including a partial final month. Month-end rates become zero
at abandonment. The fitted-history API is preserved; `simulate` is the forward
parameter API and returns no fitted R squared.

For the independent synthetic check `qi=1000`, `Di=0.1`, `b=0.5` and
`economic_limit=250`, the source's cumulative equation gives
`1000/(0.1*(1-0.5)) * (1-(250/1000)^(1-0.5)) = 10000 bbl`.
For exponential `Di=ln(2)` and `economic_limit=qi/4`, month volumes are
`qi/(2 ln(2))` and `qi/(4 ln(2))`. With price `2`, OPEX `1`, CAPEX `10` and
zero discount, the two-month answer is `NPV=-10+3*qi/(4 ln(2))` USD.
These hand calculations are written independently in the unit-test docstrings.

NPV delegates to `EconomicsQuery.npv`, using effective annual-to-monthly
conversion and [numpy-financial 1.0.0, npv function and Notes](https://github.com/numpy/numpy-financial/blob/v1.0.0/numpy_financial/_financial.py#L712-L789):
time-zero CAPEX followed by month-end operating cash. Future EUR
extends to abandonment; NPV ends at `forecast_months`, with no terminal value.

The [NumPy 2.2 linear percentile method](https://numpy.org/doc/2.2/reference/generated/numpy.percentile.html)
defines **non-exceedance** p10/p50/p90 as the low/median/high empirical quantiles.
These labels reverse petroleum exceedance P10/P90; the report states the
convention. Pointwise production bands need not describe any single trajectory.
For a sample `[0,10]`, linear interpolation gives p10=`1`, p50=`5`, p90=`9`.
The tornado displays signed [SciPy 1.15.2 Spearman correlations](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.stats.spearmanr.html),
sorted by absolute magnitude. Constant input or output correlations are undefined
and emitted as JSON null, rather than zero. Correlation does not establish causation.

## Worked result

The configured example propagates the supplied priors and records the actual
seed, sample count, selected backend, data basis and input SHA-256 in its summary.
For the committed inputs, builtin sampling gives the following calculated
results (rounded for display; these are example outputs, not validation anchors):

| Quantity | p10 | p50 | p90 |
| --- | ---: | ---: | ---: |
| Future recovery (bbl) | 11,106.0 | 13,612.7 | 17,340.3 |
| Horizon NPV (USD) | -39,865.2 | 52,243.6 | 182,156.3 |

Table 2. Synthetic example answer for the committed inputs and fixed seed.

The frozen HTML includes the input echo, numerical answer, production fan,
NPV histogram, sensitivity tornado, sources and limitations. An absent NPV
criterion produces `NOT_EVALUATED`, never a default engineering pass.

## Later slices and limits

Public-field calibration needs retained public production evidence, sourced
distribution fitting and a field-specific criterion. Correlated priors,
convergence analysis, pressure/facility constraints, fixed costs, fiscal terms,
reserve classification and the portfolio integration remain outside this example.
The compact report uses static vector charts; interactive Plotly controls remain
a presentation extension. This avoids committing a third-party script bundle.
