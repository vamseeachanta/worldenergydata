# Plan for #1039: Big Foot end-to-end asset cost-map pilot

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1039
> **Parent:** https://github.com/vamseeachanta/worldenergydata/issues/1038
> **Review artifacts:** `scripts/review/results/2026-07-16-plan-1038-1044-{claude,codex,gemini}.md`

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
2. The requirements fixture will enumerate host/TLP, dry trees and wells, drilling/completion, riser/tensioner, export, installation/hookup, controls, and explicit unknown quantities with citations or evidence notes.
3. Linkage tests will classify every live Big Foot award and will prove that the midstream export award cannot enter project CAPEX.
4. Bottom-up tests will sum only eligible non-overlapping values and will retain `not_public` items in coverage counts.
5. Top-down tests will allocate the $4,000MM sanction and $5,100MM outturn separately through `DevelopmentType.NEW_HOST_TLP` bands and will label every allocation `allocated`.
6. Timeline tests will order sanction, award, disruption/revision, and outturn events without interpolation.
7. Workbook-crosswalk tests will map the actual V30 summary categories—host, SURF, booster pump, water-injection pump/facility, dry-well system, drilling, completion, and OPEX—without treating workbook cells as disclosure; installation/hookup will remain explicitly unmapped where the workbook has no separate category.
8. The builder will generate deterministic CSV and self-contained HTML, then the owner will accept or revise the proposed contract.

## TDD Test List

- `test_big_foot_requirements_cover_dry_tree_tlp_architecture`
- `test_unknown_quantity_is_valid_but_unproven_number_is_not`
- `test_every_big_foot_award_has_one_resolution_status`
- `test_big_foot_curated_registry_has_exactly_two_awards_and_zero_not_public`
- `test_thirty_eight_wellbores_does_not_fill_blank_sanctioned_well_count`
- `test_midstream_export_is_excluded_from_project_capex`
- `test_riser_tensioner_point_award_is_a_component_floor`
- `test_bundled_link_contributes_value_once`
- `test_missing_host_awards_reduce_scope_and_value_coverage`
- `test_bottom_up_subtotal_preserves_included_excluded_overlap_and_residual`
- `test_sanction_and_outturn_reconcile_as_distinct_total_bases`
- `test_top_down_allocations_are_banded_and_marked_allocated`
- `test_trace_is_ordered_and_never_interpolates_missing_values`
- `test_fdas_crosswalk_preserves_workbook_vintage_and_assumption_status`
- `test_fdas_total_is_4517_3_mm_and_stale_5200_mm_config_is_not_disclosure`
- `test_installation_and_hookup_are_explicitly_unmapped_in_fdas`
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

## Out of Scope

Portfolio scaling, estimator training, workbook mutation, after-tax/NOL changes, and stakeholder circulation will remain outside this issue.

## Complexity: T3

The pilot will freeze a load-bearing accounting contract across data, calculations, workbooks, and report surfaces.
