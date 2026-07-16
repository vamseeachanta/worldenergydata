# Plan for #1044: FDAS workbook reconciliation and integrated cost-map report

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1044
> **Blocked by:** #1041, #1042, and #1043
> **Review artifacts:** `scripts/review/results/2026-07-16-plan-1038-1044-{claude,codex,gemini}.md`

## Resource Intelligence Summary

- Frozen V30 references will include `lease_assumptions.xlsx` (SHA-256 `a1193f669db49ac33b87481733fb13af409844fed890e763b4e8726e329a1407`, one `A1:G40` sheet) and `financial_project_summary.xlsx` (SHA-256 `00f200def283d307293bb93033f070718722618b9a8ace2bbbe11bfbffeddf04`, one `A1:AB11` summary plus ten `A1:M298` project sheets). The manifest will verify these live values rather than trust existing partial validation tests.
- The FDAS assumptions deck will contain system-based single-point inputs rather than independently sourced disclosures. Reconciliation will therefore classify these as workbook assumptions with their own vintage.
- Existing V50 comparison work will remain linked to #899. This issue will not silently adopt V50 formulas or after-tax/NOL behavior.
- Big Foot will provide an overlap through observed D&C days and dry-system assumptions even where workbook/project identities do not line up as a direct row match.
- The visible facilities components will be $100MM or $200MM below the workbook `Facilities Cost` for producing projects because water-injection-facility cost is embedded in the total without a summary column; the crosswalk will represent this explicitly.
- Only five workbook identities will have candidate sanctioned-cost matches, and `Tiber` versus `Tiber-Guadalupe` will require a scope decision rather than a silent alias.

## Artifact Map

| Action | Path |
|---|---|
| Create | `config/analysis/lower_tertiary/fdas_workbook_vintages.yml` |
| Create | `config/analysis/lower_tertiary/fdas_workbook_component_crosswalk.yml` |
| Create | `data/modules/cost/curated/fdas_project_crosswalk.csv` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/workbook_reconciliation/models.py` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/workbook_reconciliation/workbook_reader.py` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/workbook_reconciliation/crosswalk.py` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/workbook_reconciliation/reconcile.py` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/workbook_reconciliation/report.py` |
| Create | `scripts/cost/build_fdas_workbook_reconciliation.py` |
| Create | `tests/unit/cost/test_fdas_cost_crosswalk.py` |
| Create | `tests/unit/cost/test_fdas_workbook_reconciliation.py` |
| Generate | `reports/cost/fdas_workbook_reconciliation.csv` |
| Generate | `reports/cost/fdas_workbook_reconciliation.html` |

## Deliverable

A deterministic, read-only workbook inventory and component crosswalk, a project/component/time reconciliation table, and one integrated HTML decision surface spanning requirements, awards, synthesis, traces, estimates, workbook values, and explained variance.

## Planned Tasks and TDD Order

1. Golden-fixture tests will fingerprint workbook files, exact sheets/dimensions/headers, named systems, formulas/data-only values, units, and assumption vintage before comparison.
2. A reviewed crosswalk will map workbook host, SURF, drilling, completion, pump, dry-system, installation, OPEX, and other applicable fields to approved cost-map components, including one-to-many/unmapped statuses.
3. Reconciliation will preserve five lanes: disclosed, award-derived/mapped, modeled/allocated, workbook assumption, and variance.
4. Project identity tests will require an explicit scope relationship for `Tiber`/`Tiber-Guadalupe` and explicit unmatched status for workbook projects without sanctioned-cost counterparts.
5. Variances will be classified as scope, basis, timing, currency, assumption vintage, missing evidence, model error, or unexplained.
6. Monthly/annual and component/total sums will be tested independently; formula and cached-value modes will be explicit, including synthetic formula fixtures because the frozen V30 workbook currently contains no formulas.
7. Material unexplained variance thresholds will fail the build while classified differences will remain visible findings.
8. The final HTML will provide portfolio summary, project drill-down, both cost-map directions, traces, backtests, workbook comparisons, and provenance legend.

## TDD Test List

- `test_frozen_workbook_fingerprints_and_sheet_inventory`
- `test_schema_drift_fails_with_actionable_diff`
- `test_crosswalk_covers_or_explicitly_excludes_every_used_cost_cell`
- `test_water_injection_facility_explains_embedded_facilities_residual`
- `test_tiber_scope_relationship_requires_explicit_decision`
- `test_formula_and_cached_value_modes_are_not_mixed`
- `test_workbook_values_are_never_labeled_disclosed`
- `test_monthly_component_sums_reconcile_to_expected_total`
- `test_assumption_vintages_remain_separate`
- `test_variance_classifier_uses_closed_vocabulary`
- `test_unexplained_material_variance_fails_closed`
- `test_source_workbooks_are_byte_unchanged_after_build`
- `test_integrated_report_and_csv_are_deterministic`

## Acceptance Criteria

- [ ] Workbook structures, values/formulas, units, systems, identities, and vintages will be inventoried and frozen.
- [ ] Every compared workbook cell will map or receive an explicit exclusion/unmapped status.
- [ ] Project/component/time output will show observed, mapped, modeled, workbook, and variance lanes separately.
- [ ] Every material variance will be classified or will fail as unexplained.
- [ ] V30 reproduction will remain intact; V50 work will remain under #899.
- [ ] Source workbooks will remain byte-identical and read-only.
- [ ] The integrated HTML and CSV will regenerate deterministically.
- [ ] The report will state that circulation remains owner-gated under #1017.

## Out of Scope

Workbook overwrite, canonical assumption promotion, after-tax/NOL changes, V50 adoption, and stakeholder circulation will remain outside this issue.

## Complexity: T3

This will be the final cross-system verification and human decision surface for the entire program.
