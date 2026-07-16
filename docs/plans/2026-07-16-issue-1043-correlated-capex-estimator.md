# Plan for #1043: correlated CAPEX estimator for undisclosed projects

> **Status:** plan-review
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1043
> **Blocked by:** #1041 and #1042
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** Codex R1/R2 MAJOR patched; Codex R3 inline APPROVE; Claude final MINOR patched; Gemini UNAVAILABLE — see `scripts/review/results/2026-07-16-plan-1038-1044-*.md`

## Resource Intelligence Summary

- `field_development.cost_estimator` and analog modules provide adjacent estimation logic, while `cost.calibration.cost_predictor` provides an existing cost-domain predictor that is unsuitable as the new training boundary: its request includes the mandatory target, it uses ordinary row K-fold, it applies a fixed 3% escalation, and it substitutes a ±50% interval when bootstrap fails.
- `public_dataset.py` contains 29 synthetic calibration-offset rows. The new estimator will exclude synthetic, allocated, modeled, and duplicate targets and will train only on observed compatible disclosures.
- The sanctioned corpus is small and heterogeneous. Model viability will depend on strict compatible cohorts and grouped validation; a non-estimable result will be preferable to a falsely precise prediction.
- Project vintage and feature-availability timestamps from #1042 are required to prevent final-cost or future-award leakage into historical predictions.

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
3. Dataset tests will separate `feature_as_of_date`, `training_cutoff`, `prediction_date`, and `evaluation_label_date`. Features and fitted targets available after their cutoffs will be rejected; a later observed outcome may be revealed only as an untouched evaluation label after prediction. Synthetic/allocated/modeled targets and incompatible currency/basis/scope/ownership rows will be excluded. Floors/ceilings/ranges will use censored/range-aware fitting or be excluded; they will never become points.
4. Normalization will retain nominal values and will use only an owner-approved public deflator mapping recorded in the manifest; proposed candidates are CPI for total CAPEX and PPI drilling/support/machinery for mapped component classes. Until approved, the normalized lane will fail closed. Index vintage will be bounded by prediction date. Every standards- or index-derived constant will emit the repository-required `Citation` sidecar (`code_id`, revision/vintage, source, and applicability); calculation will fail closed when that citation is absent.
5. A deterministic cohort selector will segment architecture first and will require at least eight observed compatible training projects per fitted fold and at least twenty untouched outer predictions to assess interval calibration. Smaller validation sets will return `non_estimable` rather than claim calibrated coverage.
6. Untouched outer project-group or rolling-origin folds will measure the complete predeclared selection procedure exactly once. Cohort selection, preprocessing, tuning, family selection, and interval calibration will occur only in group-separated inner folds inside each outer training partition; no outer score will feed any choice.
7. The bounded nonlinear candidate will be `HistGradientBoostingRegressor` over a fixed manifest grid (`max_leaf_nodes={3,5}`, `learning_rate={0.03,0.1}`, `max_iter={100,300}`, `l2_regularization={0.1,1.0}`, fixed seed). Inner validation will select it over the log-linear baseline only if inner median absolute error improves by at least 10% without degrading inner 80% interval coverage. The resulting locked selection procedure will then face outer evaluation. Publication will require outer median APE ≤50%, empirical outer 80% interval coverage between 70% and 90%, and an exact-binomial 95% confidence interval containing 0.80; otherwise the cohort will be `non_estimable`.
8. For direct `[Dlo,Dhi]` and bottom-up `[Blo,Bhi]`, relation will be `overlap` when intervals intersect, `direct_above` when `Dlo > Bhi`, `bottom_up_above` when `Blo > Dhi`, and `indeterminate` when either bound is open/unavailable. Shared evidence/dependence will be disclosed and midpoint substitution forbidden.
9. The report and model manifest will expose provenance, comparables, features, missingness, model hash, errors, thresholds, and failure cases.

## TDD Test List

- `test_training_rows_require_compatible_accounting_basis`
- `test_feature_snapshot_cannot_contain_target`
- `test_synthetic_allocated_and_modeled_targets_are_excluded`
- `test_features_available_after_prediction_date_are_rejected`
- `test_later_target_is_hidden_from_training_but_allowed_as_evaluation_label`
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
- [ ] The model manifest will carry the common envelope: contract version, schema hash, ordered input hashes, producer commit, generated-at policy, Decimal/rounding policy, and output hashes.

## Pseudocode

```text
assert preflight(synthesis_manifest, trace_manifest)
train_records = compatible targets with disclosure_date <= training_cutoff
evaluation_labels = later outcomes hidden until after prediction
outer_split(train_records, evaluation_labels, group=validation_group_id or rolling_origin):
    inner_select cohort/preprocess/family/tune/calibrate only on outer_train
    score locked procedure once on untouched outer_test/evaluation_labels
if n_train_per_fold < 8 or n_outer_predictions < 20 or thresholds fail: non_estimable
compare direct_interval vs bottom_up_interval without midpoint substitution
```

## Attested Evidence — 2026-07-16

Inspection at `090228fb` verified 29 synthetic calibration-offset records, mandatory target-bearing requests, ordinary row K-fold, fixed 3% escalation, and ±50% fallback in the legacy predictor. The new estimator will be isolated from that API. No runtime defect is alleged; reproduction is N/A.

## Implementation and Closeout Gates

Dataset/schema/leakage nodes will run individually in `tests/unit/cost/test_capex_estimator_dataset.py`; fitting/selection/calibration/report nodes will run individually in `tests/unit/cost/test_capex_estimator.py`, using the exact base `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --extra test python -m pytest -p no:cacheprovider --noconftest -o addopts=''`, the literal listed node ID, and `-xq`. Nodes will be introduced one slice at a time. Each node will record behavior-relevant RED, identical-command minimal GREEN, refactor, and unchanged-command GREEN. Deterministic serialization, escaped/safe report content, Citation-sidecar enforcement, legal/de-identification scans, T3 code/artifact review, issue comment, exact synthesis/trace-manifest preflight, and cleanup audit will pass before close. No email, external send, or stakeholder circulation will occur.

## Out of Scope

Production deployment, automatic workbook replacement, confidential training data, point-only estimates, and circulation will remain outside this issue.

## Complexity: T3

Small, heterogeneous data and leakage risk make validation and uncertainty more important than model sophistication.
