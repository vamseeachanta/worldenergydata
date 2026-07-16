# Plan for #1043: correlated CAPEX estimator for undisclosed projects

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1043
> **Blocked by:** #1041 and #1042
> **Review artifacts:** `scripts/review/results/2026-07-16-plan-1038-1044-{claude,codex,gemini}.md`

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

## Deliverable

An interpretable, uncertainty-bounded estimator for compatible undisclosed projects, with direct-total and bottom-up asset predictions, explicit comparable cohorts, grouped out-of-sample validation, model vintage, and fail-closed non-estimable outcomes.

## Planned Tasks and TDD Order

1. A feature-only `CapexFeatureSnapshot` will structurally exclude the target; `CapexTrainingRecord` will hold observed target, basis, disclosure date, and project group separately.
2. Dataset tests will enforce target-time feature availability, exclude synthetic/allocated/modeled targets, and reject incompatible currency/basis/scope/ownership rows.
3. A deterministic cohort selector will segment architecture first, then report region/vintage/physical-driver filters and sample size.
4. The baseline will use a transparent robust analog or regularized model; a grouped nonlinear alternative will be evaluated only when sample size supports it.
5. Project-level leave-one-out or grouped holdout validation will report MAE, median absolute percentage error where defined, interval coverage, cohort counts, and failure cases; model selection will remain inside training folds.
6. Prediction intervals will be derived from held-out/group-aware residuals or another reviewable finite-sample method; they will fail closed rather than fall back to a fixed percentage.
7. Direct-total and bottom-up predictions will reconcile through a model-consistency variance without forcing equality or feeding one modeled estimate back into its own target model.
8. The report will expose training provenance, comparable projects, features, missingness, model/version hash, errors, and `non_estimable` cases.

## TDD Test List

- `test_training_rows_require_compatible_accounting_basis`
- `test_feature_snapshot_cannot_contain_target`
- `test_synthetic_allocated_and_modeled_targets_are_excluded`
- `test_features_available_after_prediction_date_are_rejected`
- `test_target_and_future_awards_never_enter_features`
- `test_group_split_keeps_project_rows_together`
- `test_sparse_or_too_small_cohort_returns_non_estimable`
- `test_prediction_is_deterministic_for_fixed_dataset`
- `test_prediction_interval_is_ordered_and_empirically_calibrated`
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

## Out of Scope

Production deployment, automatic workbook replacement, confidential training data, point-only estimates, and circulation will remain outside this issue.

## Complexity: T3

Small, heterogeneous data and leakage risk make validation and uncertainty more important than model sophistication.
