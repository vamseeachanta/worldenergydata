# Probabilistic oil resource estimation

The reservoir module estimates original oil in place (OOIP) and ultimate
recoverable oil using independent Monte Carlo inputs. It reports low P90,
median P50 and high P10 estimates in stock-tank barrels (STB). Quantitative
uncertainty alone does not establish a PRMS Reserves category.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-19 | Define validated inputs, percentile interpolation and reproducible examples. |

## Method and sources

The [AAPG public reference](https://wiki.aapg.org/Reserves_estimation#Volumetric_estimation)
(*Reserves estimation*, revision 27160, 2022, “Volumetric estimation”) gives:

```text
OOIP = 7758 * area * net_pay * porosity * (1 - water_saturation) / Boi
EUR  = OOIP * recovery_factor
```

Area is acres, net pay is feet, porosity and water saturation are fractions,
and Boi is reservoir barrels per stock-tank barrel. The published conversion
factor is rounded; it is retained for compatibility. Recovery factor must be
supplied. No typical recovery factor or reservoir property is assumed.

The [repository PRMS reference](../reference/petroleum-domain/reserves-classification.md#probabilistic-ranges-p90--p50--p10)
(2026, based on SPE PRMS 2018) defines exceedance P90/P50/P10. The simulation
therefore uses cumulative probabilities 0.1/0.5/0.9. Quantiles interpolate
between sorted realizations at zero-based index `h = (n - 1) * q`, equivalent
to [Python 3.10 inclusive quantiles](https://docs.python.org/3.10/library/statistics.html#statistics.quantiles)
(R7). This interpolation is an implementation choice, not a PRMS requirement.
A single realization has the same value at every percentile. Results for small
samples can differ from the previous integer-index selection.

The [SPE public PRMS page](https://www.spe.org/en/industry/petroleum-resources-management-system-2018/)
was accessible, but obtaining the document required a form; the full publication
was not retrieved. The exceedance convention is supported here by the existing
repository reference. No claim of full PRMS compliance is made.

## Input contract

Import `worldenergydata.reservoir.resource_estimation` from the reservoir
workspace package. Every volumetric input accepts one distribution specification:

| `dist` | Required fields | Meaning |
| --- | --- | --- |
| `constant` | `value` | Deterministic value |
| `uniform` | `low`, `high` | Bounded uniform sampling |
| `triangular` | `low`, `mode`, `high` | Bounded triangular sampling |
| `normal` | `mean`, `std` | Unbounded Gaussian sampling |

All parameters must be finite. Bounds must be ordered, mode must lie between
bounds, and standard deviation must be nonnegative. Degenerate distributions
are accepted. Area and thickness are nonnegative; porosity, water saturation
and recovery factor lie in the closed unit interval; Boi is strictly positive.
These are physical definitions, not empirical acceptance limits.

Invalid bounded support is rejected before sampling. Unbounded normal samples
are checked individually: an unphysical draw raises `ValueError` naming the
input. No clipping or rejection sampling changes the supplied distribution.
Use bounded distributions for uncertain fractions. The iteration count must
be a positive integer. Seed and iteration count are computational settings,
not convergence guarantees. A fixed seed and specifications reproduce results
within the same Python runtime. Sampling uses a local random generator.

## Worked example: exact arithmetic

All inputs in this example are synthetic choices for transparent arithmetic,
not representative field data. A one-acre reservoir with one foot of net pay,
porosity and water saturation both one half, and Boi of unity gives
`7758 * 1 * 1 * 0.5 * 0.5 / 1 = 1939.5 STB` OOIP. Half recovery gives
`1939.5 * 0.5 = 969.75 STB` EUR. With deterministic inputs every percentile
and the mean equal that value.

```python
from worldenergydata.reservoir.resource_estimation import run_resource_estimation


def constant(value):
    return {"dist": "constant", "value": value}


result = run_resource_estimation(
    area=constant(1),
    thickness=constant(1),
    porosity=constant(0.5),
    water_saturation=constant(0.5),
    fvf=constant(1),
    recovery_factor=constant(0.5),
    n_iterations=4,  # Chosen only to illustrate repeated deterministic draws.
    seed=7,  # Arbitrary reproducibility setting; not a physical coefficient.
)
assert result["ooip_distribution"] == [1939.5] * 4
assert result["eur_distribution"] == [969.75] * 4
assert result["p90"] == result["p50"] == result["p10"] == 969.75
```

For uncertain inputs, replace `area` with
`{"dist": "triangular", "low": 1, "mode": 2, "high": 3}` and recovery factor
with `{"dist": "uniform", "low": 0, "high": 1}`. These remain synthetic
choices. Increase iterations as needed and assess quantile stability across
independent seeds; this module imposes no unsupported convergence threshold.

For an independent percentile example, take synthetic EUR realizations
`[0, 10, 20, 30] STB`. The interpolation indices are `0.3`, `1.5`, `2.7`:
P90 is `0 + 0.3 * 10 = 3 STB`, P50 is `10 + 0.5 * 10 = 15 STB`, and P10 is
`20 + 0.7 * 10 = 27 STB`. The mean is `(0 + 10 + 20 + 30) / 4 = 15 STB`.
These calculations appear independently in the regression test docstrings.

## Sensitivity and outputs

`run_sensitivity_analysis(base_inputs, ranges)` takes deterministic base values
under `area`, `thickness`, `porosity`, `water_saturation`, `fvf` and
`recovery_factor`. Each range is an ordered `(low, high)` input pair. The result
contains endpoint EURs, the base EUR and absolute swing, sorted by decreasing
swing for a tornado chart. `low_eur` refers to the low **input**; increasing
water saturation or Boi decreases EUR. Inputs are not modified. This screening
method does not quantify interactions or contributions to variance.

Simulation results retain `p10`, `p50`, `p90`, `mean`, and `eur_distribution`.
They also contain `ooip_distribution`, `units`, `n_iterations`, `seed`,
`quantile_method`, and `reserves_classification`. The classification is always
`NOT_EVALUATED`: discovery, commerciality, development maturity, economic limit
and production-to-date are not evaluated. EUR is ultimate recovery, not remaining
reserves. Consumers must establish those conditions separately before applying
1P/2P/3P labels. Gas volumes, correlated inputs, chance of discovery/development,
portfolio aggregation and convergence diagnostics are outside this implementation.
Do not add marginal percentiles to construct portfolio percentiles.
