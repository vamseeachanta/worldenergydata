# Plan for #1039: Big Foot end-to-end asset cost-map pilot

> **Status:** plan-review
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1039
> **Parent:** https://github.com/vamseeachanta/worldenergydata/issues/1038
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** Codex R1/R2 MAJOR patched; Codex R3 inline APPROVE; Claude final MINOR patched; Gemini UNAVAILABLE — see `scripts/review/results/2026-07-16-plan-1038-1044-*.md`

## Resource Intelligence Summary

- `sanctioned_projects.csv` identifies Big Foot as a dry-tree extended TLP with an on-board rig, a $4,000MM 2010 sanction basis, and 2018 first oil.
- `cost_revision_trails.csv` provides the $4,000MM sanction and $5,100MM final/outturn observations in separate dated rows.
- `contract_awards.csv` provides exactly two current Big Foot rows: a 2009 $45MM riser-tensioner point award and a $200MM midstream export system that must be excluded from Chevron project CAPEX. Host design/hull references remain research leads outside the curated registry and will therefore appear as award-coverage gaps unless separately imported through a sourced issue.
- `drilling_and_completion_days.xlsx` and the deterministic completion report provide 38 Big Foot wellbores and 3,033 D&C days. Big Foot is WED-only in the current World Oil comparison, so that workbook comparison will require explicit status rather than a forced match.
- The frozen FDAS assumption workbook provides the legacy dry-system cost representation to crosswalk, not disclosure evidence.

## Artifact Map

| Action | Path |
|---|---|
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_map_schema.py` |
| Create | `data/modules/cost/curated/project_asset_requirements.csv` |
| Create | `data/modules/cost/curated/award_asset_links.csv` |
| Create | `data/modules/cost/curated/cost_project_identity.csv` |
| Create | `data/modules/cost/curated/cost_award_identity.csv` |
| Create | `data/modules/cost/curated/cost_requirement_identity.csv` |
| Create | `data/modules/cost/curated/cost_event_identity.csv` |
| Create | `data/modules/cost/curated/cost_map_contract_manifest.v1.json` |
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
2. RED tests will require controlled opaque project/award/requirement/event IDs in four versioned registries, assigned monotonically rather than derived from row order or mutable content, plus independent link-resolution, scope-coverage, bundle topology, value-basis, bound-type, evidence, and counting fields. Alias/phase corrections will preserve IDs; deleted/merged IDs will be tombstoned and never reused; collisions, broken foreign keys, and unrecorded split/merge migrations will fail closed.
3. The requirements fixture will enumerate host/TLP, dry trees and wells, drilling/completion, riser/tensioner, export, installation/hookup, controls, and explicit unknown quantities with citations or evidence notes.
4. Linkage tests will classify every live Big Foot award and will prove that the midstream export award cannot enter project CAPEX.
5. Bottom-up tests will sum only eligible non-overlapping values and will retain unavailable items in scope coverage.
6. Top-down tests will allocate the $4,000MM sanction and $5,100MM outturn as separate evidence scenarios through reviewed joint TLP share vectors; every scenario will conserve its total and remain `allocated`.
7. Timeline tests will use precision-bearing date intervals. They will order the 2009 award before the 2010 sanction, represent a revised estimate as unavailable, and retain the 2018 low-confidence outturn without inventing a 2015 monetary event.
8. Workbook-crosswalk tests will map the actual V30 summary categories—host, SURF, booster pump, water-injection pump/facility, dry-well system, drilling, completion, and OPEX—without treating workbook cells as disclosure. Development CAPEX will be `2730.0 + 965.6 + 821.7 = 4517.3MM`; OPEX will remain a separate basis lane and will never enter that total. Installation/hookup will remain explicitly unmapped where the workbook has no separate category.
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
- `test_synthetic_status_axis_fixture_supports_linked_midstream_excluded_and_linked_not_public`
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
- [ ] Manifest v1 will carry the common envelope: contract version, schema hash, ordered input hashes, producer commit, generated-at policy, Decimal/rounding policy, and output hashes.

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

Each literal node name in the TDD Test List will be introduced one at a time and recorded in a TDD ledger. For example, the first schema slice will run exactly `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --extra test python -m pytest -p no:cacheprovider --noconftest -o addopts='' tests/unit/cost/test_cost_map_schema.py::test_big_foot_requirements_cover_dry_tree_tlp_architecture -xq`; every later ledger row will spell out its literal node ID, with schema/identity nodes in `test_cost_map_schema.py` and Big Foot data/reconciliation/report nodes in `test_big_foot_cost_map.py`. No later test file will be collected before its slice begins. Every node will record behavior-relevant RED, identical-command minimal GREEN, refactor, and unchanged-command GREEN. Serialization will use stable ordering, exact `Decimal`, locale `C`, UTC, injected `SOURCE_DATE_EPOCH`, HTML escaping, and http(s)-only links; two clean builds must have identical SHA-256 hashes. The legal scan, deny-list/de-identification scan, T3 code/artifact review, issue comment, manifest preflight, and cleanup audit will all pass before close. Workbook core metadata will not be published. No email, external send, or stakeholder circulation will occur.

## Out of Scope

Portfolio scaling, estimator training, workbook mutation, after-tax/NOL changes, and stakeholder circulation will remain outside this issue.

## Complexity: T3

The pilot will freeze a load-bearing accounting contract across data, calculations, workbooks, and report surfaces.
