# Plan for #1043: correlated CAPEX estimator for undisclosed projects

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1043
> **Blocked by:** #1041 and #1042
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** R1 Codex MAJOR: `scripts/review/results/2026-07-16-plan-1038-1044-codex-r1.md`; final artifacts PENDING

## Resource Intelligence Summary

- `field_development.cost_estimator` and analog modules will provide adjacent estimation logic, while `cost.calibration.cost_predictor` will provide an existing cost-domain predictor that is unsuitable as the new training boundary: its request includes the mandatory target, it uses ordinary row K-fold, it applies a fixed 3% escalation, and it substitutes a ±50% interval when bootstrap fails.
- `public_dataset.py` will also contain 29 synthetic calibration-offset rows. The new estimator will exclude synthetic, allocated, modeled, and duplicate targets and will train only on observed compatible disclosures.
- The sanctioned corpus will be small and heterogeneous. Model viability will depend on strict compatible cohorts and grouped validation; a non-estimable result will be preferable to a falsely precise prediction.
- Project vintage and feature-availability timestamps from #1042 will be required to prevent final-cost or future-award leakage into historical predictions.

## Artifact Map

| Action | Path |
|---|---|
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/calibration/capex_estimator.py` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/calibration/capex_estimator_schema.py` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/calibration/estimator_dataset.py` |
| Extend | `packages/worldenergydata-cost/src/worldenergydata/cost/calibration/__init__.py` |
| Create | `scripts/cost/build_capex_estimator_report.py` |
| Create | `tests/unit/cost/test_capex_estimator_dataset.py` |
| Create | `tests/unit/cost/test_capex_estimator.py` |
| Generate | `reports/cost/capex_estimator_backtests.csv` |
| Generate | `reports/cost/capex_estimator.html` |
| Generate | `data/modules/cost/derived/capex_estimator_manifest.json` |

## Deliverable

An interpretable, uncertainty-bounded estimator for compatible undisclosed projects, with direct-total and bottom-up asset predictions, explicit comparable cohorts, grouped out-of-sample validation, model vintage, and fail-closed non-estimable outcomes.

## Planned Tasks and TDD Order

1. Preflight RED tests will require #1041/#1042 manifests and matching `validation_group_id` semantics.
2. A feature-only `CapexFeatureSnapshot` will structurally exclude the target; `CapexTrainingRecord` will hold observed target interval/bound type, basis, target disclosure date, and project group separately.
3. Dataset tests will enforce prediction-time feature and target-disclosure cutoffs, exclude synthetic/allocated/modeled targets, and reject incompatible currency/basis/scope/ownership rows. Floors/ceilings/ranges will use censored/range-aware fitting or be excluded; they will never become points.
4. Normalization will retain nominal values and will use existing public index lanes by component: CPI for total CAPEX, PPI drilling/support/machinery for mapped component classes; an unmapped class will be non-estimable. Index vintage will be bounded by prediction date.
5. A deterministic cohort selector will segment architecture first and will require at least eight observed compatible training projects and five outer test predictions.
6. Untouched outer project-group or rolling-origin folds will measure performance. Cohort selection, preprocessing, tuning, and model selection will occur only inside outer training partitions; interval calibration will be cross-fitted/group-separated.
7. The nonlinear alternative will replace the interpretable baseline only if outer median absolute error improves by at least 10% without degrading 80% interval coverage. Publication will require median APE ≤50% and empirical 80% interval coverage between 70% and 90%; otherwise the cohort will be `non_estimable`.
8. Direct-total and bottom-up intervals will produce `overlap`, `direct_above`, `bottom_up_above`, or `indeterminate`; shared evidence/dependence will be disclosed and midpoint substitution forbidden.
9. The report and model manifest will expose provenance, comparables, features, missingness, model hash, errors, thresholds, and failure cases.

## TDD Test List

- `test_training_rows_require_compatible_accounting_basis`
- `test_feature_snapshot_cannot_contain_target`
- `test_synthetic_allocated_and_modeled_targets_are_excluded`
- `test_features_available_after_prediction_date_are_rejected`
- `test_target_disclosed_after_prediction_date_is_rejected`
- `test_floor_ceiling_and_range_targets_are_not_points`
- `test_target_and_future_awards_never_enter_features`
- `test_group_split_keeps_project_rows_together`
- `test_outer_group_fold_is_untouched_by_selection_and_interval_calibration`
- `test_sparse_or_too_small_cohort_returns_non_estimable`
- `test_prediction_is_deterministic_for_fixed_dataset`
- `test_prediction_interval_is_ordered_and_empirically_calibrated`
- `test_viability_thresholds_return_non_estimable_when_missed`
- `test_direct_bottom_up_interval_relation_uses_closed_states_without_midpoints`
- `test_comparable_cohort_and_feature_missingness_are_exposed`
- `test_bottom_up_and_direct_predictions_report_consistency_variance`
- `test_backtest_metrics_include_counts_and_failure_cases`

## Acceptance Criteria

- [ ] Training will use only compatible projects and prediction-time features.
- [ ] The request schema will contain no target, and observed targets will remain in a separate training-only record.
- [ ] The retained model will beat or justify deviation from the interpretable baseline under grouped validation.
- [ ] Overall and cohort-level errors, sample counts, and interval coverage will be reported.
- [ ] Every prediction will carry range, comparable cohort, completeness, model vintage, and modeled status.
- [ ] Insufficient evidence will return `non_estimable` without fallback fabrication.
- [ ] Direct and asset-level estimates will reconcile or expose variance.
- [ ] Report and backtest outputs will regenerate deterministically.
- [ ] The model manifest will pin training IDs, source/feature cutoffs, normalization series, folds, thresholds, model hash, and output hashes.

## Pseudocode

```text
assert preflight(synthesis_manifest, trace_manifest)
records = observed compatible targets disclosed by prediction_date
outer_split(records, group=validation_group_id or rolling_origin):
    select cohort/preprocess/tune/calibrate only on outer_train
    score untouched outer_test
if n_train < 8 or n_outer_predictions < 5 or thresholds fail: non_estimable
compare direct_interval vs bottom_up_interval without midpoint substitution
```

## Attested Evidence — 2026-07-16

Inspection at `090228fb` verified 29 synthetic calibration-offset records, mandatory target-bearing requests, ordinary row K-fold, fixed 3% escalation, and ±50% fallback in the legacy predictor. The new estimator will be isolated from that API. No runtime defect is alleged; reproduction is N/A.

## Implementation and Closeout Gates

Every schema, leakage control, fold, threshold, and report behavior will demonstrate RED then GREEN. Deterministic serialization, escaped/safe report content, legal/de-identification scans, T3 code/artifact review, issue comment, manifest preflight, and cleanup audit will pass before close.

## Out of Scope

Production deployment, automatic workbook replacement, confidential training data, point-only estimates, and circulation will remain outside this issue.

## Complexity: T3

Small, heterogeneous data and leakage risk make validation and uncertainty more important than model sophistication.
