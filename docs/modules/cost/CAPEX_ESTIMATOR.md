# Correlated CAPEX estimator

The estimator separates prediction-time physical features from observed cost
labels. It provides modeled intervals, project holdouts, comparable identities,
feature completeness and explicit `NOT_EVALUATED` results. It does not turn an
undisclosed value into a disclosure. The legacy `CostPredictor` is unchanged.

## Input contract

Import `CapexEstimator` from `worldenergydata.cost.calibration.capex_estimator`.
Contracts live in `capex_estimator_schema` in the same package.

- `FeatureSnapshot` contains project and canonical validation-group identities,
  architecture, host type, region, basis, prediction date and dated features.
- Allowed numeric features are water depth (m), well count, capacity (boe/day),
  asset quantity and vintage year. Counts/quantities are nonnegative physical
  inputs. Feature availability dates cannot follow the snapshot date.
- Omit an unavailable feature or supply `None`. Completeness is relative to the
  keys declared by the request; it is not completeness against every possible
  project driver. No available features means `NOT_EVALUATED`.
- `TrainingRecord` holds a positive cost amount in currency millions, disclosure
  date, source, derivation and bound type separately. Only disclosed point
  observations qualify. Synthetic, modeled, allocated, award-derived and censored
  labels are excluded. Test fixtures deliberately exercise the trusted ingestion
  boundary; they are not a qualified project corpus.
- Basis fields follow the existing `MoneyInterval` terminology. Currency, price
  basis, basis year, normalization source, ownership, scope and CAPEX basis shall
  match exactly. Architecture and host type also match exactly. No implicit FX,
  escalation, deflation, architecture pooling or missing-value imputation occurs.
- Upstream ingestion shall retain source rights, verify the disclosure and dated
  features, and preserve canonical project/group identities. This API cannot
  establish provenance truth from a supplied string. Multiple observations in one
  project/group are all excluded, rather than counted as independent projects.

`EstimatorPolicy` requires application-specific minimum training, calibration and
backtest project counts, miscoverage `alpha`, maximum median absolute percentage
error (fraction), minimum empirical coverage (fraction), a criteria source, and
a fixed split salt. No engineering acceptance limits are built in. A criteria
source shall identify the decision setting those inputs. A text citation alone
does not approve a criterion.

## Method and sources

The baseline fits `ln(C) = b0 + sum(bj*xj)` by ordinary least squares. The
alternative adds individual squared feature terms. Scaling parameters are fitted
inside each training fold. No interaction terms or empirical coefficients are
supplied. OLS and transformed-response fitting follow the
[NIST/SEMATECH e-Handbook, 2012, sections 4.4.3.1](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm)
and [4.4.5.2](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd452.htm).
Exponentiating the fitted log cost provides a log-scale central estimate, not an
unbiased arithmetic mean cost.

An outcome-independent salted hash partitions eligible projects into proper
training and calibration sets. The salt and criteria shall be fixed before
evaluation, rather than adjusted to obtain a desired outcome. Inner
leave-one-project-out mean absolute log error selects the model using proper
training only; an exact tie retains the baseline. Calibration remains untouched.
Every outer project holdout repeats this entire selection/calibration procedure.
This implements the project-separation principle in the
[scikit-learn cross-validation documentation, Leave One Group Out](https://scikit-learn.org/stable/modules/cross_validation.html#leave-one-group-out).

For `m` calibration residuals `abs(ln(C)-predicted_ln(C))`, the interval radius is
the `ceil((m+1)*(1-alpha))` order statistic. A rank exceeding `m` returns
`NOT_EVALUATED`; it is not replaced by the largest residual. Bounds are
`exp(predicted_ln(C) ± radius)`. This follows
[Distribution-Free Predictive Inference For Regression, 2017, section 2.2,
Algorithm 2 and Remark 2.7](https://arxiv.org/html/1604.04173v2#S2.SS2).
Marginal coverage requires exchangeability; a hash partition does not establish
that assumption for project economics. Empirical holdout coverage is reported
separately and is not a guarantee for a particular region or project.

Outer errors, failure cases and counts are reported overall and by region and
architecture. Any failed outer fold blocks a modeled target result. Supplied
validation limits, finite intervals, identifiable fits and target features within
the proper-training coordinate ranges are required; calibration rows do not extend
those ranges. Each retrospective outer fold records `extrapolation_features`
against its own proper-training rows. These folds remain in the validation metrics,
including extrapolating extreme holdouts; the flag does not authorize extrapolation
for a target prediction. Coordinate range checks do not
establish multivariate support. Holdouts are retrospective at the common training
cutoff, not rolling historical forecasts. Every training label must already have
been disclosed by that cutoff, which cannot follow the target prediction date.

## Worked hand calculation

This illustration is synthetic, with no engineering use. Define sixteen
independent projects with well counts `x=1,...,16` and costs
`C=exp(1+x/10)` in currency millions. Coefficients `1` and `1/10` are definitions
of this hand example, not fitted engineering constants. The exact linear
log-cost relation has zero residual in exact arithmetic. For a target with
`x=2`, `ln(C)=1+2/10=1.2`, hence the answer is `exp(1.2)`, displayed as **3.3
currency million**. Exact-arithmetic interval endpoints equal the answer;
floating-point roundoff may create a small interval.

Positive report values below 0.1 currency million are displayed as `<0.1`,
and negative reconciliation differences above -0.1 as `>-0.1`; a true zero
is displayed as `0.0`. Machine-readable results retain numeric precision.

The executable version is
`tests/unit/cost/test_capex_estimator.py::test_deterministic_prediction_matches_hand_calculated_line`.
Its policy uses four minimum training projects, four calibration projects, eight
minimum backtests, `alpha=0.5`, a maximum median APE of `1.0`, and minimum coverage
of `0.0`. These deliberately permissive test criteria are defined for this
illustration only. They do not qualify any real project or calibrated interval.
For a separate uncertainty hand check, residuals `[1,2,3,4]` and `alpha=0.5` give
rank `ceil(5*0.5)=3` and radius `3`, per the cited order-statistic formula.

## Asset reconciliation and report generation

Estimate each component using its own compatible scope cohort. Pass the direct
estimate and a mapping of component scope names to `reconcile_estimates`, together
with the exhaustive, disjoint scope set from the requirements map. Project,
currency and accounting bases are checked; each component's scope shall match its
map key. Missing/unavailable components produce `indeterminate`. Physical scope
disjointness remains an upstream requirements-map assertion.

Interval arithmetic gives the bottom-up envelope `[sum(lo), sum(hi)]` and central
variance `direct - sum(component estimates)`. For component intervals `[2,4]`
and `[3,5]`, the hand sum is `[5,9]`. Central values `3` and `5` sum to `8`;
direct central value `10` gives variance `2`. Direct interval `[9.5,11]` is
`direct_above` because its lower bound exceeds `9`. These are defined arithmetic
inputs, not sourced project amounts. A sum of marginal bounds is an envelope,
not a joint prediction interval; dependence and double-counting cannot be
resolved from amount triples alone.

To generate HTML and full-precision JSON, supply a JSON request containing
`records`, `targets`, `policy`, `cutoff`, `issued_on` and `revision`, matching the
contracts above, then run:

```bash
python scripts/cost/build_capex_estimator_report.py request.json \
  --html report.html --json results.json
```

Outputs are read back after writing. JSON includes the input-byte SHA-256 digest
and per-result evidence/policy hashes. HTML escapes supplied text, distinguishes
modeled/disclosed values, shows non-estimable projects, and includes project
backtests and diagnostics. No generated report or invented sample dataset is
committed. The command's integration tests exercise both absent evidence and the
hand-calculated synthetic corpus.

Optional `required_scopes` maps each project identity to its exhaustive component
scope list. The request includes separate target snapshots for each such scope
and a `total_project` target. Reconciliation is included in both outputs; absent
scope maps yield `indeterminate`. Optional `prior_revisions` carries existing
`[revision, date, change and reason]` rows; a re-issue appends its current row
without changing those earlier entries.

## Limits and remaining qualification

No real-project training corpus or application criteria have been qualified by
this implementation. Portfolio ingestion from synthesis and time traces,
approved normalization mappings, independent review, and public-project
backtests remain required before engineering use. Sources and per-feature dates
shall be verified upstream. The model hash pins evidence and policy inputs; it
does not certify them. Confidential data and licensed standards are not bundled.
