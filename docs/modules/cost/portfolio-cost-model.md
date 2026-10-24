# Portfolio cost accounting and CAPEX estimation

The reusable API separates observed component costs, joint allocation assumptions,
dated evidence, modeled estimates and frozen workbook values. It extends the
existing pilot without changing its curated data, manifest or workbooks. The
generated example demonstrates the calculation contracts with synthetic inputs;
it does not qualify a real-project estimate.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-20 | Add reusable accounting, dated comparisons and a guarded estimator to retain uncertainty and provenance. |
| Correction | 2026-10-24 | Correct dependent residual fractions, share interval arithmetic, pin output bytes and clarify source sections and publication limits. |

## Three implementation slices

1. `worldenergydata.cost.portfolio.accounting`: interval reconciliation, compatible
   accounting envelopes, requirement coverage, duplicate and overlap rejection,
   and architecture-specific joint allocations.
2. `worldenergydata.cost.portfolio.history`: as-of traces and read-only frozen
   workbook-cell comparisons, including digest and cached-value checks.
3. `worldenergydata.cost.portfolio.estimator` and `report`: physical-driver
   regression, grouped model selection, independent calibration and validation,
   and deterministic HTML/JSON outputs with a digest manifest.

## Accounting contract and equations

Every amount carries currency, native unit, price basis and vintage, ownership,
phase, scope envelope and CAPEX basis. All dimensions must match for arithmetic.
Component requirements describe commercial scope within that common envelope.
Unknown basis dimensions prevent evaluation even when two unknown labels match.
No FX or inflation adjustment is performed. Numeric inputs use finite `Decimal`;
the current Decimal context governs division and regression precision.

The accounting equations implement the repository's
[cost-map program contract](../../plans/2026-07-16-issue-1038-cost-map-program.md),
“Shared Contract to Freeze” (2026):

- Eligible subtotal: `E = [sum(component.low), sum(component.high)]`.
- Residual: `R = [T.low - E.high, T.high - E.low]`.
- Coverage: `E/T`; evaluate all endpoint quotients with a positive denominator.
- Model consistency: `direct - bottom_up` by interval subtraction; intersecting
  intervals mean `overlap`, not agreement of point values or independence.
- A joint scenario's nonnegative shares sum exactly to unity. Allocation floors
  each raw amount to the caller's quantum, then distributes remaining units by
  fractional remainder, with stable requirement-ID ties. Each scenario conserves
  its total; marginal min/max bands across scenarios are **not additive**.

The portfolio API additionally reports the residual fraction as `1 - E/T`, with
bounds `[1 - E.high/T.low, 1 - E.low/T.high]` for nonnegative eligible amounts and
`T.low > 0`; otherwise it is unavailable. This follows directly from `(T-E)/T`
and accounts for the common total in numerator and denominator. It preserves
overruns and zero-crossing residuals. The shared contract specifies residual and
coverage, without defining this additional fraction. The existing time-series
`residual_percentage` remains an outer enclosure from interval `R/T`.
The portfolio interval specializes the existing closed interval with finite-bound
validation, and its adapters use the existing ratio and residual primitives. The
frozen time-series producer bytes and its manifest remain intact.

An award linked to several requirements contributes once. Conflicting duplicate
IDs and multiple included awards in one overlap group fail closed. Overlap
identification is supplied by the evidence adapter; shared requirement IDs alone
do not establish overlapping commercial scope. Excluded/overlap items remain in
the result with native bases and are not added to the eligible subtotal.
`not_public` remains unavailable. Backlog, combined-project, lease and midstream
values cannot enter additive CAPEX merely by changing their counting label.
Open or unbounded amounts are not represented as finite closed intervals; an
adapter must retain those as unavailable findings rather than invent endpoints.

Allocation shares, architecture and output quantum are required inputs with a
source. There are no embedded engineering allocation factors. `unallocated` is a
scenario share, distinct from the observed bottom-up residual. The generic map
does not assert quantities or canonical requirements for unresearched projects.

## Dated evidence and workbook comparisons

`trace(events, as_of)` orders unique event IDs and keeps only events whose
occurrence and evidence-availability dates are no later than `as_of`. Native
currencies, revisions, scope changes and unknown events remain separate records.
Events are not summed as cash flows, and missing years are not interpolated.
Confidence and source-tier qualification remain responsibilities of the upstream
curated evidence adapter; the API does not promote trade-press records.

`read_workbook_cell` hashes the exact workbook bytes before reading a numeric or
cached formula value using `openpyxl`. A digest mismatch fails closed, a missing
formula cache remains unavailable, and text/errors/booleans are rejected. The
caller supplies the independently reviewed cell/component and basis crosswalk;
the workbook is never written or recalculated.

`compare_workbook` compares project, component, currency, basis, assumption
vintage and period. It reports `NOT_EVALUATED` with a specific reason when these
do not match or a value is missing. Otherwise, variance is the observed interval
minus the workbook interval. A nonzero difference remains `unexplained` until
separate evidence attributes it. No acceptance tolerance is assumed.

An integration test reads one existing frozen FDAS cell through the adapter and
checks its value against the existing crosswalk. That crosswalk has no price year:
the missing dimension is preserved as `not_disclosed` and prevents arithmetic.
The test does not treat a workbook assumption as a cost disclosure.

## Estimator method, sources and validation

The request has one named physical driver with an explicit unit and feature
provenance; it has no target cost. Observed target costs live only in `Comparable`
records. Evidence adapters must verify that a driver is physical and available at
the prediction date; renaming a target cost as a driver is invalid input.

Training excludes synthetic, allocated, modeled, nonpoint and nonpositive targets,
future targets/features, incompatible accounting bases/architectures and the
target's project or validation group. Every exclusion has a reason. Region is
reported rather than silently used as a normalization coefficient. One target
vintage per project is required; related projects share a validation group.

Linear `y = b0 + b1*x` and quadratic `y = b0 + b1*x + b2*x²` are fitted by least
squares, minimizing `sum((observed - predicted)²)`. The normal equations and
interpretation follow the public
[NIST/SEMATECH e-Handbook, section 4.4.3.1](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd431.htm)
(2003). Polynomial degrees are mathematical model definitions; coefficients are
learned, not supplied as cost factors. Rank-deficient candidates are unavailable.

Three disjoint **predeclared project-group partitions** are mandatory:

1. Training groups: leave one whole group out internally to compare candidate
   group-mean absolute errors. Select the lower error, preferring linear on an
   exact tie, and refit only the training partition.
2. Calibration groups: compute absolute residuals, taking the maximum within each
   group. For `m` calibration groups and required miscoverage `alpha`, set
   `k = ceil((m+1)*(1-alpha))`. The radius is the kth ordered residual; if `k > m`,
   the estimate is `NOT_EVALUATED`, with no fabricated finite interval.
3. Untouched validation groups: evaluate the locked model and interval once.
   Report individual failures, group-weighted MAE/mean APE, whole-group coverage,
   region counts and errors. These outcomes do not select or refit a candidate.

The interval `[prediction-radius, prediction+radius]`, intersected with nonnegative
costs, follows
[A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification](https://arxiv.org/html/2107.07511v6)
(2021), section 1.1 (finite-sample quantile construction and Theorem 1).
Group-maximum scores apply the same construction to
whole-group error. Its coverage interpretation requires exchangeable groups and
independent calibration; a historical portfolio is not automatically exchangeable.
The retained model is not refitted on calibration or validation records.

Minimum training/validation group counts, `alpha`, maximum mean APE, minimum
validation coverage and their policy citation are required inputs. No production
acceptance limits are embedded. Sparse evidence, missing features, extrapolation,
negative predictions, singular models or failed validation return `NOT_EVALUATED`.
The output exposes cohort snapshots, exclusions, partitions, folds, coefficients,
candidate errors, calibration errors, validation rows and prediction vintage.

## Worked example

All quantities in this section are **synthetic problem inputs**, chosen for an
independent hand calculation; none is an empirical cost coefficient or recommended
acceptance limit. The example is explicitly synthetic at the artifact boundary.
Fictional target records mimic the disclosed-record interface only in this
demonstration and must not enter a real training cohort.

| Input | Declared value |
| --- | --- |
| Accounting envelope | Gross upstream development CAPEX, phase A, real 2020 USD million |
| Total range | 100–120 |
| Bundled host/installation award | 20–30, counted once |
| Wells award | 10 |
| Controls value | `not_public` |
| Joint scenario applied to the explicit low total bound | Host 50.0%, wells 30.0%, unallocated 20.0% |
| Allocation quantum | 0.01 million, example serialization input |
| Frozen workbook analogue | 90, same basis, component, period and vintage |
| Training points | `x = 1,2,3,4,5`; `y = 10 + 2*x` |
| Calibration points | `(2,15)` and `(4,21)` |
| Independent validation points | `(2,14)` and `(4,18)` |
| Target physical driver | 3 wells |
| Demonstration validation inputs | At least 3 training groups and 2 validation groups; alpha 50.0%, maximum mean APE 1.0%, minimum coverage 50.0% |

Hand calculation:

- Eligible award interval is `[20+10,30+10] = [30,40]`. Residual is
  `[100-40,120-30] = [60,90]`; value coverage is `[30/120,40/100] = [25.0%,40.0%]`.
  The residual fraction is `[1-40/100,1-30/120] = [60.0%,75.0%]`.
- The low-bound joint allocation is host 50.0, wells 30.0, unallocated 20.0. It
  conserves 100.0. The unallocated amount is separate from the residual range.
- Workbook variance is `[100-90,120-90] = [10,30]`, marked unexplained.
- For regression, mean x is 3.0 and mean y is 16.0. The centered covariance sum
  is 20.0 and squared-driver sum is 10.0, so slope is 2.0 and intercept is 10.0.
  At 3 wells the prediction is 16.0. Linear wins the exact-fit candidate tie.
- Calibration absolute errors are 1.0 and 3.0. The finite-sample rank is
  `ceil((2+1)*(1-0.5)) = 2`, so the radius is 3.0 and the interval is `[13,19]`.
- The two held-out validation predictions are 14.0 and 18.0, so MAE and mean APE
  are zero and interval coverage is 100.0%. This proves the example arithmetic,
  not real-world predictive accuracy.
- No asset-level modeled estimate is supplied for the inferred target, so its
  bottom-up/direct consistency result is `indeterminate`, not a false match.

Generate all three example artifacts into a chosen output directory:

```sh
PYTHONPATH=src:packages/worldenergydata-cost/src \
  uv run python scripts/cost/build_portfolio_example.py --output-dir reports/cost
```

The checked-in HTML is navigable in both accounting directions. JSON preserves
calculation precision, and the manifest records the input/output SHA-256 digests.
All three files use UTF-8 bytes with LF newlines on every platform, so the digests
describe the actual written files. No wall clock or local path enters the outputs.
Tests compare two builds byte for byte, simulate Windows text newline translation,
verify file digests and check HTML escaping. Test commands can disable pytest's repository-wide
coverage defaults with `--noconftest -o addopts='' -p no:cacheprovider` while running
the focused tests and their existing cost-domain regressions.

### Publication deviations

This synthetic demonstration does not implement the frozen contract's publication
envelope. HTML displays amounts to one decimal place and fractions to 0.1%, with
interval endpoints rounded outward; JSON retains calculation precision rather than
quantizing published money to 0.01 million with `ROUND_HALF_EVEN`. The example's
0.01-million allocation quantum applies only to joint allocation arithmetic.

The example manifest uses `contract`, `inputs_sha256`, `output_sha256`, a descriptive
rounding string and an explicit revision-date policy. It omits the required
`contract_version`, schema hash, ordered input hashes, producer commit, pinned
currency/source scale, serialization quantum, rounding modes and boundary. It
therefore supplies reproducibility digests only and must not be consumed as a
frozen-contract manifest. Adopting that publication envelope remains later work;
neither the guide nor this example asserts conformance to it.

## Known limits and later slices

- Portfolio requirement research, alias resolution, quantities, canonical award
  linkage and approval of allocation scenarios remain upstream work. The example
  does not create a portfolio census or modify the pilot's manifest contract.
- Real-project model fitting is **NOT_EVALUATED** until compatible dated targets,
  feature snapshots, predeclared partitions and sourced acceptance policy exist.
  No empirical coverage claim is made for a real cohort.
- Multivariate/asset-level models, rolling-origin validation and price-index
  normalization remain later slices. Direct/bottom-up consistency is available
  when both intervals exist, without asserting independent uncertainty.
- Full workbook inventories, monthly component crosswalks, variance attribution
  and financial reproduction remain later slices. No accepted workbook or fiscal
  assumption is changed.
- Open-bound interval arithmetic, stakeholder circulation and production adoption
  are outside this implementation. These limitations leave #1038 open.
