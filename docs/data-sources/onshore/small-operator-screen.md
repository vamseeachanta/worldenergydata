# Small-operator candidacy screen

The screen ranks operators and attributable wells using descriptive public-data
signals. Each row retains observations, peer medians, policy thresholds, weights
and score contributions. The synthetic worked example recovers its constructed
anomaly; documented rework recovery and a field false-positive rate remain
**NOT_EVALUATED**. Rates alone do not establish mechanical addressability.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-20 | Introduce explainable ranking, sensitivity and an evidence gate for reproducible screening. |

## Scope

Refs #1127; registry contract #1126; pressure observations #709; gate pattern #710.

- Slice 1: validated registry and well inputs, peer-relative rate deficit,
  deterministic well and operator ranking, and evidence per ranked row.
- Slice 2: endpoint decline, largest monthly drop, prior-producing idle wells,
  variability, dated pressure context, and operator field concentration.
- Slice 3: alternate peer definitions, rank and candidacy sensitivity, documented
  case validation, command-line JSON output, and this worked example.

The screen consumes normalized inputs; it does not download data, reconcile
operator aliases, allocate lease production, estimate ownership or generate
outreach material. No predicted production uplift is emitted.

## Input contract

`examples/analysis/small_operator_screen.json` is a complete synthetic input.
The top level has `config` and `data`. Identifiers are strings, so leading zeros
are preserved. `data.registry` contains unique `operator_no`, `well_count_total`
and `source`. Counts select the configured inclusive operator size band. A
supplied eligible inventory larger than the registry count is rejected.

`data.wells` contains unique `well_key`, `operator_no`, jurisdiction-qualified
`field_key`, `first_production_year`, optional `depth_ft`, `source`, explicit
`production_basis: "well"`, and `production` rows with `month: "YYYY-MM"` and
`oil_bbl`. The volume unit is stock-tank barrels per calendar month. Null and
absent months are missing observations; a reported zero is an observation.
Duplicate months, negative or nonfinite volumes, unknown operators and future
first-production years are rejected. Future monthly rows do not enter features.
Missing field or vintage and any basis other than explicitly attributable well
production appear in `excluded`, rather than receiving well rankings.

The existing PDQ loader maps production to `OG_LEASE_NO` and well counts;
joining that table to an API does not establish well attribution. A registry
producer must resolve this boundary before supplying screen inputs. Operator
of record identifies the reporting entity; it does not establish working interest.

Optional `data.pressure` accepts #709-style records keyed by `api14` (matching
`well_key`), with ISO `test_date`, `pressure_psia`, `pressure_kind`,
`reference_depth_ft` and `source_file`. The latest usable observation at or before
the cutoff month is shown. Pressure/depth is calculated only for `BHP_measured`
or `BHP_calc` with positive depth; shut-in wellhead pressure is never silently
converted to BHP. Pressure contributes no score and is not a virgin-pressure claim.

## Policy and method

All size limits, lookback length, peer counts, vintage and depth widths, signal
thresholds, minimum prior rate, signal weights, concentration weight and gate
limits are required inputs. `policy_source` records their supplied basis. The
example's values are **synthetic arithmetic choices**, not field acceptance
limits. Production use requires a reviewed policy source for those choices;
none is provided by this example. Zero weights disable candidacy for a signal.

The following are descriptive definitions for this issue, rather than empirical
engineering correlations. The only literal numeric quantities in the algorithm
are calendar definitions, mathematical identities and the minimum sample size
needed to define sample standard deviation.

| Quantity | Equation and basis |
| --- | --- |
| Calendar rate | `q = oil_bbl / calendar days`; definition of daily average, #1127 method (2026). |
| Rate deficit | `max(0, 1 - q / median(peer q))`; fractional comparison, #1127 method (2026). |
| Endpoint decline | `D = 1 - q_last/q_first`; descriptive fractional loss, #1127 method (2026); no fitted decline curve or forecast. |
| Step change | `S = max(0, 1 - q_t/q_previous)` over positive previous rates; #1127 method (2026). |
| Variability | `CV = sample standard deviation(q) / mean(q)`; NIST Dataplot (2017), Coefficient of Variation. |
| Peer anomalies | `max(0, own D/S/CV - median(peer D/S/CV))`; #1127 descriptive method (2026). |
| Idle | Count consecutive reported zero months ending at cutoff, immediately preceded by a positive rate meeting the supplied prior-rate limit; #1127 method (2026). |
| Well score | Sum of supplied weights for positive signal values meeting their supplied thresholds; #1127 ranking policy (2026). |
| Field HHI | `sum((field well count / supplied well count)^2)`; squared-share definition, DOJ (2024), rescaled to fractional shares. |
| Operator score | Mean score of evaluated wells plus supplied concentration weight times HHI; #1127 ranking policy (2026). |
| Recall and FPR | `TP/(TP+FN)` and `FP/(FP+TN)`; conditional proportions with an independent hand matrix in the tests. |

A zero denominator leaves a comparison NOT_EVALUATED. Complete, contiguous
lookback history is required for decline, step and CV; sample CV also requires
positive mean. Idle detection can use earlier supplied months to find a prior
positive observation. A missing month breaks that sequence. Idle evidence states
prior rate and time idle, rather than estimating recoverable production.

Evaluated wells sort first. Ranking is deterministic: decreasing well score, decreasing prior idle rate,
increasing idle duration, then identifier. Each signal reports its measured value,
threshold, weight, contribution, peer count and comparator when applicable.
No enabled triggered signal means `candidate: false`. A row with no evaluable
signals is NOT_EVALUATED; partial evidence is exposed through `signals_evaluated`.
Operator scores with no evaluable wells are null. Evaluated operators sort by
decreasing score, with identifier as tie breaker; unevaluated operators sort last.
The operator mean uses evaluated wells only; its count and inventory coverage
must be read alongside the score. HHI describes the **supplied eligible inventory**,
not an inferred full portfolio. It supplies service concentration context, not
proof of technical upside or an economic valuation.

## Peer construction and sensitivity

Peers share the exact field key and an absolute vintage bucket
`floor(first_production_year / vintage_years)`. If enabled, depth adds
`floor(depth_ft / depth_band_ft)`. Depth must be finite and positive for this
comparison; missing depths are not pooled together. This is a fixed bucket,
not a moving age tolerance. Bucket boundaries can separate nearly identical wells.
First-production year is a vintage proxy, not completion date or producing age.

The target well is excluded from its own comparator. Operators outside the size
band still supply peers. Each metric uses only peers with that metric evaluated,
and requires the configured minimum number. Medians follow NIST/SEMATECH
§1.3.5.1. Rates are compared at the same cutoff, and changes over the same calendar
lookback. This does not control for completion design, fluid, producing days,
reservoir compartment or operating constraints; these remain confounders.

`sensitivity_peer_group` is mandatory. Each well reports alternate signals,
score difference, alternate rank, rank change and whether candidacy changed.
Each operator also reports alternate score and rank. Both policies are retained
in the output. A narrower group that loses its peers yields NOT_EVALUATED
signals, not a claim that the anomaly disappeared. Broad and narrow comparisons
in the example coincide; the tests also demonstrate lost peers after a vintage
change. Sensitivity must be reported for any real population before use.

## Worked example

Three synthetic wells share a field, vintage and depth. Well `a` belongs to
`op-a`; wells `b` and `c` belong to `op-b`. Their operator registry counts are one
and two. The supplied policy uses a three-month lookback, two peers and equal
signal weights of 1.0; concentration weight is 1.0. Each policy value is a test
input rather than a sourced operational limit.

| Well | January 2024 (bbl) | February 2024 (bbl) | March 2024 (bbl) |
| --- | ---: | ---: | ---: |
| a | 310 | 145 | 62 |
| b | 310 | 290 | 310 |
| c | 310 | 290 | 310 |

The calendar daily rates are `(10, 5, 2)` and `(10, 10, 10)`. For `a`, rate
deficit and decline excess are both `1 - 2/10 = 0.8`; largest drop excess is
`1 - 2/5 = 0.6`. Its sample variance is `49/3`, mean is `17/3`, and CV is
`7 / (sqrt(3) * (17/3))`, reported as 0.7. Peer CVs and decline values are zero.
Four signals exceed the synthetic policy: score 4.0. No idle signal is triggered.
One field gives `HHI = 1.0`; `op-a` scores `4.0 + 1.0 = 5.0` and ranks first.
Peer wells have score 0.0; `op-b` scores 1.0 from concentration context only.
The independent calculations are written out in the test docstrings.

```bash
PYTHONPATH=src uv run --no-project python -m worldenergydata.analysis.small_operator_screen \
  --input examples/analysis/small_operator_screen.json \
  --output "$TMPDIR/small-operator-screen.json"
```

The output records the input SHA-256 digest, policy, rankings, evidence, exclusions,
coverage and validation gate. The command writes its output and exits with code
2 because no documented field cases were supplied. Gate PASS exits 0; FAIL exits
1. Input errors do not produce a completed result. Output must differ from input.
Use a caller-selected data location; no bulk or generated field results belong
in the repository.

## Validation and known limits

`data.validation_cases` accepts distinct `well_key`, boolean `known_good` and a
nonempty public `source` citation. A negative control is a documented negative,
not an unlabeled well. The gate calculates the confusion matrix, recall and FPR,
and compares them with the supplied `validation` limits. Missing citations,
missing ranked wells, unevaluated rows or either absent label class leave the
gate NOT_EVALUATED. No cases cannot pass. Synthetic labels can test the gate's
arithmetic but never establish external field accuracy.

A deployment validation dataset has **not been supplied or demonstrated**.
Documented rework fields must be identified, matched to attributable wells and
screened using a pre-intervention cutoff. Labels and sources require independent
review for representativeness and information leakage. The current API records
the supplied citation but does not authenticate it or enforce intervention dates.
No documented field recovery, false-positive rate or commercial readiness is
claimed. This gate is a reproducible reporting control, not certification.

Mechanical failure, reservoir depletion, curtailment, seasonal operations,
reporting revisions and lease allocation can produce similar rate patterns.
Every well therefore carries `cause_status: "UNRESOLVED"`. Pressure alone does
not resolve them. Rates use calendar days, so downtime can depress apparent rate.
Overlapping signals can double count the same episode; weights are not calibrated
probabilities. The implementation is an in-memory screen; large peer groups need
performance measurement before bulk deployment.

## Sources

- NIST/SEMATECH, *e-Handbook of Statistical Methods*, §1.3.5.1,
  [Measures of Location](https://www.itl.nist.gov/div898/handbook/eda/section3/eda351.htm),
  live edition accessed 2026-10-20: median definition.
- NIST Dataplot (2017),
  [Coefficient of Variation](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/coefvari.htm):
  sample standard deviation divided by mean, and near-zero-mean limitations.
- DOJ (2024),
  [Herfindahl–Hirschman Index](https://www.justice.gov/atr/herfindahl-hirschman-index):
  sum of squared shares only. No antitrust thresholds are used.
- Repository PDQ loader, `PRODUCTION_FIELD_MAPPING` in
  `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/pdq_loader.py`:
  lease-based production key and well-count metadata.
- Issues #1127 (2026), #1126 (2026), #709 and #710: signal requirements,
  attribution boundary, pressure schema and validation-gate precedent.
