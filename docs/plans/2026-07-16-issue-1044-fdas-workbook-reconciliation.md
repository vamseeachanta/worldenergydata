# Plan for #1044: FDAS workbook reconciliation and integrated cost-map report

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1044
> **Blocked by:** #1041, #1042, and #1043
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** R1 Codex MAJOR: `scripts/review/results/2026-07-16-plan-1038-1044-codex-r1.md`; final artifacts PENDING

## Resource Intelligence Summary

- Frozen V30 references include `lease_assumptions.xlsx` (SHA-256 `a1193f669db49ac33b87481733fb13af409844fed890e763b4e8726e329a1407`, one `A1:G40` sheet) and `financial_project_summary.xlsx` (SHA-256 `00f200def283d307293bb93033f070718722618b9a8ace2bbbe11bfbffeddf04`, one `A1:AB11` summary plus ten `A1:M298` project sheets). The manifest will verify these live values rather than trust existing partial validation tests.
- The FDAS assumptions deck contains system-based single-point inputs rather than independently sourced disclosures. Reconciliation will therefore classify these as workbook assumptions with their own vintage.
- Existing V50 comparison work remains linked to #899. This issue will not silently adopt V50 formulas or after-tax/NOL behavior.
- Big Foot provides an overlap through observed D&C days and dry-system assumptions even where workbook/project identities do not line up as a direct row match.
- The visible facilities components are $100MM or $200MM below the workbook `Facilities Cost` for producing projects because water-injection-facility cost is embedded in the total without a summary column; the crosswalk will represent this explicitly.
- Only five workbook identities have candidate sanctioned-cost matches, and `Tiber` versus `Tiber-Guadalupe` requires a scope decision rather than a silent alias.
- The D&C workbook is frozen at SHA-256 `3ecfa1128b33edf73db3a793f8839c98c50bc27184487a8af579c5ef22795e7f`; workbook core metadata will be excluded from publishable inventories.

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
| Generate | `data/modules/cost/derived/fdas_reconciliation_manifest.json` |

## Deliverable

A deterministic, read-only workbook inventory and component crosswalk, a project/component/time reconciliation table, and one integrated HTML decision surface spanning requirements, awards, synthesis, traces, estimates, workbook values, and explained variance.

## Planned Tasks and TDD Order

1. Preflight RED tests will require the exact #1041–#1043 manifests without recomputing their outputs.
2. Golden-fixture tests will fingerprint all three workbook files, exact sheets/dimensions/headers, named systems, formulas/data-only values, units, and assumption vintage before comparison.
3. A reviewed crosswalk will map workbook host, SURF, drilling, completion, pump, dry-system, installation, OPEX, and other fields to approved components, including one-to-many/unmapped statuses.
4. A ten-row project crosswalk will enumerate `Stones`, `Cascade Chinook`, `Julia`, `Anchor`, `Jack St Malo`, `Kaskida`, `Tiber`, `Shenandoah`, `North Platte`, and `Big Foot`; each row will carry identity relationship, scope relationship, evidence, and comparison eligibility.
5. Reconciliation will preserve disclosed, award-derived/mapped, modeled/allocated, workbook-assumption, and variance lanes.
6. Variance classification and resolution will be separate. For workbook interval `W=[Wlo,Whi]` and comparison interval `C=[Clo,Chi]`, variance will be `[Wlo-Chi, Whi-Clo]`. With materiality `M=max($25MM, 1% of the compatible workbook total)` and persisted denominator, the result will be definitely immaterial only when `Vlo >= -M and Vhi <= M`, definitely material only when `Vhi < -M or Vlo > M`, and `uncertain_materiality` otherwise. Zero-crossing and open bounds will remain explicit; midpoint substitution is forbidden. Unsupported, missing-evidence, or uncertain material differences will fail closed.
7. Monthly/annual and component/total sums will be tested independently; formula and cached-value modes will be explicit, including synthetic formula fixtures because the frozen V30 financial workbook has no formulas.
8. The report manifest will allowlist publishable workbook fields and exclude core metadata/personal identifiers, raw private paths, formulas outside the allowlist, and unescaped text.
9. The final HTML will provide portfolio summary, project drill-down, both cost-map directions, traces, backtests, workbook comparisons, and provenance legend.

## TDD Test List

- `test_frozen_workbook_fingerprints_and_sheet_inventory`
- `test_schema_drift_fails_with_actionable_diff`
- `test_crosswalk_covers_or_explicitly_excludes_every_used_cost_cell`
- `test_water_injection_facility_explains_embedded_facilities_residual`
- `test_tiber_scope_relationship_requires_explicit_decision`
- `test_all_ten_workbook_projects_have_evidenced_identity_and_scope_status`
- `test_formula_and_cached_value_modes_are_not_mixed`
- `test_workbook_values_are_never_labeled_disclosed`
- `test_monthly_component_sums_reconcile_to_expected_total`
- `test_assumption_vintages_remain_separate`
- `test_variance_classifier_uses_closed_vocabulary`
- `test_unexplained_material_variance_fails_closed`
- `test_interval_variance_and_zero_crossing_materiality_are_explicit`
- `test_uncertain_materiality_fails_closed_without_midpoint`
- `test_material_missing_evidence_or_unsupported_classification_fails_closed`
- `test_workbook_core_metadata_is_not_published`
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
- [ ] The final manifest will pin upstream manifests, workbook hashes/schemas, crosswalk hashes, materiality policy, allowlist, and output hashes.

## Pseudocode

```text
assert preflight(manifest_v3_synthesis, manifest_v3_trace, estimator_manifest)
assert workbook_hashes_and_schemas_match_manifest
for each of 10 workbook projects: require identity + scope + eligibility evidence
for each used cost cell: require component mapping or explicit exclusion
variance = [workbook.low - comparison.high, workbook.high - comparison.low]
materiality = classify_entire_interval_against([-M, M])
if materiality in {definitely_material, uncertain_materiality} and resolution unsupported_or_missing_evidence: fail
render only allowlisted escaped fields; emit final manifest
```

## Attested Evidence — 2026-07-16

`sha256sum` and `openpyxl` inspection at `090228fb` verified the three workbook hashes, exact sheets/dimensions, ten project identities, no formulas in the financial workbook, and the hidden water-injection-facility residual. Existing tests were inspected and found incomplete for hashes/crosswalks. No runtime defect is alleged; reproduction is N/A.

## Implementation and Closeout Gates

The executable slice command will be `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --extra test python -m pytest -p no:cacheprovider --noconftest -o addopts='' tests/unit/cost/test_fdas_cost_crosswalk.py tests/unit/cost/test_fdas_workbook_reconciliation.py -xq`. Each slice will record a behavior-relevant nonzero RED, run the identical command after minimal GREEN, refactor, and run it unchanged again. Source workbooks must remain byte-identical. Stable ordering, Decimal, locale `C`, UTC/injected time, escaping, safe URLs, allowlisted fields, and two-build SHA equality will govern outputs. Legal/deny-list/de-identification scans, T3 code/artifact review, issue comment, exact upstream manifest verification, and cleanup audit will pass before close. No email, external send, or stakeholder circulation will occur.

## Out of Scope

Workbook overwrite, canonical assumption promotion, after-tax/NOL changes, V50 adoption, and stakeholder circulation will remain outside this issue.

## Complexity: T3

This will be the final cross-system verification and human decision surface for the entire program.
