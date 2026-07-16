# Plan for #1041: portfolio bidirectional asset/project cost synthesis

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1041
> **Blocked by:** #1040
> **Review artifacts:** `scripts/review/results/2026-07-16-plan-1038-1044-{claude,codex,gemini}.md`

## Resource Intelligence Summary

- `compute_coverage()` will already sum conservative eligible award lows against sanctioned gross totals, while excluding lease, midstream, combined-without-valid-bound, and not-public values.
- `back_allocation.py` will already allocate totals to six lifecycle stages using architecture-specific banded priors. This issue will generalize that reconciliation to the approved physical asset/work-package taxonomy without erasing stage-level evidence.
- Award values alone will not cover total CAPEX. Residual and unallocated values will therefore be first-class results, not errors to hide by tuning.

## Artifact Map

| Action | Path |
|---|---|
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/cost_synthesis.py` |
| Extend | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/reconciliation.py` |
| Extend | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/back_allocation.py` |
| Create | `scripts/cost/build_project_cost_map.py` |
| Create | `tests/unit/cost/test_cost_synthesis.py` |
| Generate | `reports/cost/project_cost_map.csv` |
| Generate | `reports/cost/project_cost_map.html` |

## Deliverable

A two-way synthesis API and report in which eligible bottom-up asset/work-package values sum toward a compatible project total, and compatible disclosed totals allocate back through architecture-specific bands. Both directions will reconcile algebraically or expose a named variance.

## Planned Tasks and TDD Order

1. Tests will define `CostEnvelope`, `CostContribution`, and `ProjectCostSynthesis` invariants for lower/mid/upper values and bases.
2. Eligibility will fail closed unless currency, price basis, ownership, phase, scope, and capex basis match the target total.
3. A contribution ledger will include each award once, preserve asset links, and classify exclusion/overlap reasons.
4. Bottom-up synthesis will compute eligible low/high subtotal, disclosed total, unallocated amount, residual range, and coverage.
5. Top-down synthesis will use disclosed splits when available; otherwise it will refine architecture priors only with eligible evidence and retain `allocated`/`modeled` status.
6. The report will allow project-total → assets and asset → project traversal with distinct styles for observed and inferred values.

## TDD Test List

- `test_cost_envelope_rejects_low_above_high`
- `test_bottom_up_rejects_incompatible_currency_basis_scope_or_ownership`
- `test_each_award_identity_contributes_at_most_once`
- `test_range_and_band_arithmetic_preserves_bounds`
- `test_not_public_and_excluded_scope_remain_visible`
- `test_bottom_up_residual_reconciles_algebraically`
- `test_top_down_allocations_sum_to_total_with_residual`
- `test_disclosed_split_overrides_prior_without_relabeling`
- `test_architecture_cohorts_do_not_pool_incompatible_projects`
- `test_cost_map_output_is_deterministic`

## Acceptance Criteria

- [ ] Every included project will show total, eligible subtotal, exclusions, overlaps, unallocated amount, and residual percentage.
- [ ] Bottom-up arithmetic will fail closed on incompatible bases.
- [ ] Top-down values will retain uncertainty and inferred status.
- [ ] Combined, lease, midstream, not-public, and overlapping scopes will not inflate totals.
- [ ] Every displayed total will reconcile exactly within a documented decimal tolerance or show an unreconciled variance.
- [ ] The HTML cost map will provide bidirectional drill-down and provenance.

## Out of Scope

Historical interpolation, FX conversion, estimator training, and workbook mutation will remain outside this issue.

## Complexity: T3

This will implement the program’s load-bearing arithmetic and inference boundary.
