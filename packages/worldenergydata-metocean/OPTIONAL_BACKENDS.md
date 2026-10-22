# Optional backends and joint-model example

The joint wrapper decodes the statistics backend explicitly, records guarded
zero residuals and distinguishes backend iso-density curves from IFORM/ISORM.
The data adapter accepts only NORA3 and NorKyst800. Numerical checks below
establish software contracts and algebra; engineering applicability remains
NOT_EVALUATED.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-22 | Document backend boundaries, corrected API names and an independently calculated example. |

## Installation and integration prerequisites

Dependency declarations and CI installation are already proposed in #1363
(statistics) and #1393 (data adapter). This change builds on those interfaces;
it does not duplicate their manifests or lockfile. The workspace installation
clarification in #1612 remains applicable. After integrating those changes:

```sh
uv sync --frozen --package worldenergydata --package worldenergydata-metocean --extra test --extra statistics --extra metocean-api
```

| Member extra | Backend | Enables |
| --- | --- | --- |
| `statistics` | `metocean-stats==1.2.0` | Statistical wrappers, joint fitting and contours |
| `metocean-api` | `metocean-api==1.1.14` | Uncached NORA3 and NorKyst800 retrieval |

The second library is LGPL and remains optional. Importing the core package or
adapter module does not import either backend. A completed data cache can be
read without metocean-api. At this base revision, the statistics dependency is
still mandatory at an older release and the seven original statistics test
files are excluded by the root test configuration; #1363 supplies that
packaging and collection change. Its temporary expected failures must be removed
when integrating the repair: the original statistics tests now pass.
Compatibility execution against the base dependency pin also passed all 122
statistics tests. Frozen workspace installation and the
manifest/import guard remain integration prerequisites, not verified claims
of this change. The tests here use an isolated environment with the inspected
backend releases and explicitly collect the statistics directory.

## Statistical contract and numerical guard

The statistics release returns this tuple, in order:

```text
(a1, a2, a3, b1, b2, b3, pdf_Hs, h, t3, h3, X, hs_tpl_tph)
```

The named adapter rejects a different tuple length. The first six entries are
conditional log-period coefficients, with
`mu(h) = a1 + a2*h**a3` and
`variance(h) = b1 + b2*exp(-b3*h)`.
The conditional standard deviation is the square root of that variance.
`pdf_Hs` and `h` describe the hybrid LogNoWe marginal grid; they are not samples
or Weibull coefficients. Observations remain paired in the legacy sample
fields. `t3` is period and `h3` is height. Backend curves require an exact fitted
return period; a nearby period is never substituted.

The local curve adaptation preserves the release's peak-finding algorithm.
An exact zero residual is assigned an infinite rank without computing its
reciprocal. Every affected location and index appears in
`JointModel.guarded_points`. Nonzero residuals retain their reciprocals. No
small epsilon, warning filter or installed-library modification is used.
Invalid residuals and other numerical warnings remain failures. The private
function namespace prevents replacement of the shared backend function.

`backend_contour(model, period)` returns `method="backend_iso_density"`.
`iform()` and `isorm()` instead transform normal-space circles using their
respective normal and chi-square radii. Their marginal CDF is the trapezoidal
integral of the backend PDF, normalized on its finite support, with linear
inverse interpolation. This approximates a truncated marginal; it does not
supply unobserved tail probabilities. Invalid grids or conditional variances
raise errors. The old silent random/ellipse fallback has been removed.

The finite-grid tail error, complete nonlinear fitting accuracy, empirical
backend coefficients and calendar conversions, and engineering suitability
are NOT_EVALUATED. The backend still applies its own period correction, global
NumPy RNG seeding and pandas option change; thread safety is not claimed.
The legacy `mu`/`sigma` dictionary entries are replaced by
`mu_coefficients`/`variance_coefficients`; consumers must update accordingly.

## Worked example

Inputs are six synthetic pairs, selected for hand calculation:
`Hs=(1,1,2,2,3,3)` and `Tp=(1,4,1,4,1,4)`.
Fix Weibull shape to one and location to zero; impose zero dependence slopes.
These are example assumptions, not environmental criteria.

For the resulting exponential marginal, differentiating
`-n*log(scale)-sum(Hs)/scale` gives `scale=mean(Hs)=2.0`.
For the conditional normal distribution of `log(Tp)`, differentiating its log
likelihood gives `mu=mean(log(Tp))=log(2)` and
`variance=mean((log(Tp)-mu)**2)=log(2)**2`.
Every height bin contains the same period pair, so these conditional parameters
are constant. Displayed to one decimal place, they are 0.7 and 0.5.

At normal-space point `(0,1)` on a circle of radius one, the marginal
probabilities are `(1/2, Phi(1))`. Inverting gives
`Hs=-2*log(1-1/2)=2*log(2)` and
`Tp=exp(log(2)+log(2)*1)=4`.
The contour point is therefore **Hs=1.4, Tp=4.0**, displayed to one decimal
place; tests compare the unrounded expressions. No return period is assigned
to this demonstration. The unconstrained backend fit is underdetermined on
this tiny sample and is NOT_EVALUATED.

```sh
python -m worldenergydata.metocean.statistics.examples.conditional_hand_case
```

A separate hand check uses a uniform height marginal on `[0,2]`, standard
normal log-period, and exceedance probability `1/4`. The IFORM point at angle
zero is `(Hs,Tp)=(1.5,1.0)`. For ISORM the two-dimensional chi-square survival
function is `exp(-r*r/2)`, hence `r=sqrt(2*log(4))`. Its quarter-circle point
is `(1, exp(sqrt(2*log(4))))`. These checks distinguish the two methods.

## Corrected external-tool examples

Inspection of statistics release 1.2.0 found these missing names in the
existing external-tool skill snippets. The replacements are explicit APIs,
not aliases claiming the old behaviour. Editing the protected skill directory
is outside the supplied finish manifest; this table and runnable examples
provide the corrections for subsequent integration there.

| Missing API | Replacement checked against the installed API |
| --- | --- |
| `metocean_stats.EVA`, block maxima | `ExtremeValueAnalysis.fit_annual_maxima` |
| `metocean_stats.EVA`, POT | `ExtremeValueAnalysis.fit_pot` |
| `metocean_stats.return_periods.calculate` | `ExtremeValueAnalysis.return_period_table` |
| `metocean_stats.joint_probability.fit` | `JointProbabilityModel.fit` for the conditional model; it is not a KDE |
| `metocean_stats.contours.IFORM` | `EnvironmentalContour.iform` |
| `metocean_stats.contours.DirectSampling` | No equivalent supplied; NOT_EVALUATED |
| `metocean_stats.directional.sector_stats` | `metocean_stats.stats.directional_extremes` for directional extremes; general sector summaries need a separate implementation |
| `metocean_stats.directional.plot_rose` | No Plotly equivalent supplied; NOT_EVALUATED |

The adapter release exposes `metocean_api.ts.TimeSeries`, its `import_data`
method and its `data` attribute. Those names in the fetching skill do exist.
The adapter restricts upstream product identifiers to `NORA3_wave_sub` and
`NORKYST800`; its public dataset names are `NORA3` and `NorKyst800`.

```python
from worldenergydata.metocean.clients.metocean_api_adapter import MetoceanAPIAdapter

# Supply a provider-supported point, short window and persistent cache location.
adapter = MetoceanAPIAdapter(cache_directory)
frame = adapter.fetch(
    dataset="NORA3", lon=longitude, lat=latitude,
    start_time=start, end_time=end, variables=["hs"],
)
```

Cached CSV samples and their request/digest manifests stay in the supplied
cache directory. Downloads run in a child interpreter there because the
upstream library writes relative cache files. The parent working directory
is preserved. Offline tests exercise that protocol with a fake upstream API.
The two `network` tests require `METOCEAN_API_NETWORK=1`,
`METOCEAN_API_SAMPLE_CACHE`, `METOCEAN_API_SAMPLE_LON`,
`METOCEAN_API_SAMPLE_LAT`, `METOCEAN_API_SAMPLE_START` and
`METOCEAN_API_SAMPLE_END`. They are skipped by default. Live archive coverage
and sample values remain NOT_EVALUATED in the recorded execution.

## Sources

- [Deriving environmental contours from highest density regions](https://doi.org/10.1016/j.coastaleng.2017.03.002),
  Coastal Engineering 123 (2017), section 3.1: Eq. (2), three-parameter Weibull;
  Eq. (3), conditional lognormal; Eq. (4), conditional mean; Eq. (6), joint
  density product; Eq. (7), sea-state exceedance conversion. Its period variable
  is zero-upcrossing period; the paper does not validate the backend's peak-period
  calibration. Its Eq. (5) describes standard deviation, whereas the inspected
  backend uses an exponential variance function. Those coefficients are not
  transferred between the two parameterizations.
- [NIST/SEMATECH e-Handbook, Weibull distribution](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3668.htm),
  section 1.3.6.6.8, PDF and CDF formulas, accessed 2026-10-22.
- [NIST/SEMATECH e-Handbook, lognormal distribution](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3669.htm),
  section 1.3.6.6.9, log-mean parameterization and CDF, accessed 2026-10-22.
- metocean-stats 1.2.0: `stats/aux_funcs.py`, `Hs_Tp_curve`, and
  `stats/extreme.py`, `joint_distribution_Hs_Tp`; public release sources read
  successfully on 2026-10-22. The tuple and empirical coefficients are backend
  contracts, not independently validated physical values.
- virocon 2.4.0: `contours.py`, `IFORMContour` and `ISORMContour`, normal-space
  radii and default angular discretization. Its original implementation was
  inspected; the statistical forms above have independent hand checks.
- metocean-api 1.1.14: installed `ts/ts_mod.py` and product definitions;
  constructor, method names, variable names and product keys were inspected.
