# Plan for #1039: Big Foot end-to-end asset cost-map pilot

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1039
> **Parent:** https://github.com/vamseeachanta/worldenergydata/issues/1038
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** R1 Codex MAJOR: `scripts/review/results/2026-07-16-plan-1038-1044-codex-r1.md`; final artifacts PENDING

## Resource Intelligence Summary

- `sanctioned_projects.csv` will identify Big Foot as a dry-tree extended TLP with an on-board rig, a $4,000MM 2010 sanction basis, and 2018 first oil.
- `cost_revision_trails.csv` will provide the $4,000MM sanction and $5,100MM final/outturn observations in separate dated rows.
- `contract_awards.csv` will provide exactly two current Big Foot rows: a $45MM riser-tensioner point award and a $200MM midstream export system that must be excluded from Chevron project CAPEX. Host design/hull references will remain research leads outside the curated registry and will therefore appear as award-coverage gaps unless separately imported through a sourced issue.
- `drilling_and_completion_days.xlsx` and the deterministic completion report will provide 38 Big Foot wellbores and 3,033 D&C days. Big Foot will be WED-only in the current World Oil comparison, so that workbook comparison will require explicit status rather than a forced match.
- The frozen FDAS assumption workbook will provide the legacy dry-system cost representation to crosswalk, not disclosure evidence.

## Artifact Map

| Action | Path |
|---|---|
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py` |
| Create | `data/modules/cost/curated/project_asset_requirements.csv` |
| Create | `data/modules/cost/curated/award_asset_links.csv` |
| Create | `data/modules/cost/curated/cost_project_identity.csv` |
| Create | `data/modules/cost/curated/cost_award_identity.csv` |
| Create | `data/modules/cost/curated/cost_map_contract_manifest.json` |
| Create | `data/modules/cost/curated/fdas_project_cost_crosswalk.csv` |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map.py` |
| Create | `scripts/cost/build_big_foot_cost_map.py` |
| Create | `tests/unit/cost/test_cost_map_schema.py` |
| Create | `tests/unit/cost/test_big_foot_cost_map.py` |
| Generate | `reports/cost/big_foot_cost_map.html` |
| Generate | `reports/cost/big_foot_cost_map_reconciliation.csv` |

## Deliverable

The pilot will enumerate Big Foot’s required physical assets and commercial work packages, link every known award, reconcile eligible bottom-up values to both sanction and outturn totals, allocate each total back to assets as uncertainty bands, produce a dated trace, and compare the result with frozen FDAS inputs. The resulting schema and accounting choices will become the proposed portfolio contract.

## Planned Tasks and TDD Order

1. Tests will first pin immutable amount/basis, requirement, award-link, and reconciliation models.
2. RED tests will require controlled, immutable project/award/requirement/event IDs and independent link-resolution, scope-coverage, value-basis, evidence, and counting fields before fixtures are added.
3. The requirements fixture will enumerate host/TLP, dry trees and wells, drilling/completion, riser/tensioner, export, installation/hookup, controls, and explicit unknown quantities with citations or evidence notes.
4. Linkage tests will classify every live Big Foot award and will prove that the midstream export award cannot enter project CAPEX.
5. Bottom-up tests will sum only eligible non-overlapping values and will retain unavailable items in scope coverage.
6. Top-down tests will allocate the $4,000MM sanction and $5,100MM outturn as separate evidence scenarios through reviewed joint TLP share vectors; every scenario will conserve its total and remain `allocated`.
7. Timeline tests will use precision-bearing date intervals. They will order the 2009 award before the 2010 sanction, represent a revised estimate as unavailable, and retain the 2018 low-confidence outturn without inventing a 2015 monetary event.
8. Workbook-crosswalk tests will map the actual V30 summary categories—host, SURF, booster pump, water-injection pump/facility, dry-well system, drilling, completion, and OPEX—without treating workbook cells as disclosure; installation/hookup will remain explicitly unmapped where the workbook has no separate category.
9. The builder will emit manifest v1, deterministic CSV/HTML, and a decision checklist; the owner will accept or revise the proposed contract and manifest before #1040 starts.

## TDD Test List

- `test_big_foot_requirements_cover_dry_tree_tlp_architecture`
- `test_unknown_quantity_is_valid_but_unproven_number_is_not`
- `test_every_big_foot_award_has_one_resolution_status`
- `test_big_foot_curated_registry_has_exactly_two_awards_and_zero_not_public`
- `test_thirty_eight_wellbores_does_not_fill_blank_sanctioned_well_count`
- `test_midstream_export_is_excluded_from_project_capex`
- `test_riser_tensioner_point_award_is_a_component_floor`
- `test_bundled_link_contributes_value_once`
- `test_status_axes_support_linked_midstream_excluded_and_linked_not_public`
- `test_missing_host_awards_reduce_scope_and_value_coverage`
- `test_bottom_up_subtotal_preserves_included_excluded_overlap_and_residual`
- `test_sanction_and_outturn_reconcile_as_distinct_total_bases`
- `test_top_down_allocations_are_banded_and_marked_allocated`
- `test_each_joint_allocation_scenario_sums_exactly_to_project_total`
- `test_trace_is_ordered_and_never_interpolates_missing_values`
- `test_fdas_crosswalk_preserves_workbook_vintage_and_assumption_status`
- `test_fdas_total_is_4517_3_mm_and_stale_5200_mm_config_is_not_disclosure`
- `test_installation_and_hookup_are_explicitly_unmapped_in_fdas`
- `test_dnc_workbook_hash_is_3ecfa1128b33edf73db3a793f8839c98c50bc27184487a8af579c5ef22795e7f`
- `test_big_foot_outputs_are_byte_deterministic`

## Acceptance Criteria

- [ ] Every required asset/work package will carry a quantity or explicit `unknown` plus evidence.
- [ ] Every Big Foot award will have a traceable linkage status.
- [ ] Stable project, award, requirement, and event IDs will key every linkage and output row.
- [ ] Value coverage and requirement coverage will be reported separately.
- [ ] Sanction and outturn reconciliations will show eligible, excluded, overlap, unallocated, and residual amounts.
- [ ] Top-down allocations will remain ranges and will never masquerade as disclosures.
- [ ] FDAS differences will be classified by component, basis, vintage, timing, or missing evidence.
- [ ] The $5,100MM outturn will retain `trade_press` provenance and low confidence; it will not be relabeled as operator disclosure.
- [ ] The HTML and CSV outputs will regenerate deterministically.
- [ ] The owner will explicitly approve or revise the pilot contract before #1040 starts.
- [ ] The approved manifest will freeze schema/input hashes, controlled IDs, scenario vectors, and source-safe workbook fields.

## Pseudocode

```text
RED: load Big Foot rows -> require stable IDs and orthogonal status axes
GREEN: add controlled identity/crosswalk rows; no source-value rewrite
eligible = contributions where counting_disposition == included
residual = interval_subtract(total, interval_sum(eligible))
for scenario in approved_joint_vectors: assert sum(shares) == 1; allocate(total)
emit manifest v1; stop for owner decision
```

## Attested Evidence — 2026-07-16

Live CSV enumeration, workbook cell inspection, `sha256sum`, completion reconciliation tests, and GitHub issue inspection were run at `090228fb`. This feature will allege no runtime defect; reproduction is N/A. Verified Big Foot facts and confidence tiers are listed above.

## Implementation and Closeout Gates

Every slice will run a named failing test before the smallest data/code change and the same test after GREEN. Serialization will use stable ordering, `Decimal`, locale `C`, UTC, injected `SOURCE_DATE_EPOCH`, HTML escaping, and http(s)-only links; two clean builds must have identical SHA-256 hashes. The legal scan, deny-list/de-identification scan, T3 code/artifact review, issue comment, manifest preflight, and cleanup audit will all pass before close. Workbook core metadata will not be published.

## Out of Scope

Portfolio scaling, estimator training, workbook mutation, after-tax/NOL changes, and stakeholder circulation will remain outside this issue.

## Complexity: T3

The pilot will freeze a load-bearing accounting contract across data, calculations, workbooks, and report surfaces.
