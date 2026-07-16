# Plan for #1041: portfolio bidirectional asset/project cost synthesis

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1041
> **Blocked by:** #1040
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** R1 Codex MAJOR: `scripts/review/results/2026-07-16-plan-1038-1044-codex-r1.md`; final artifacts PENDING

## Resource Intelligence Summary

- `compute_coverage()` will already sum conservative eligible award lows against sanctioned gross totals, while excluding lease, midstream, combined-without-valid-bound, and not-public values.
- `back_allocation.py` will already allocate totals to six lifecycle stages using architecture-specific banded priors. This issue will generalize that reconciliation to the approved physical asset/work-package taxonomy without erasing stage-level evidence.
- Award values alone will not cover total CAPEX. Residual and unallocated values will therefore be first-class results, not errors to hide by tuning.

## Artifact Map

| Action | Path |
|---|---|
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/portfolio/basis.py` (≤300 lines) |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/portfolio/intervals.py` (≤250 lines) |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/portfolio/synthesis.py` (≤350 lines) |
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/portfolio/scenarios.py` (≤300 lines) |
| Verify only | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/reconciliation.py` |
| Verify only | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/back_allocation.py` |
| Create | `scripts/cost/build_project_cost_map.py` |
| Create | `tests/unit/cost/test_cost_synthesis.py` |
| Generate | `reports/cost/project_cost_map.csv` |
| Generate | `reports/cost/project_cost_map.html` |

## Deliverable

A two-way synthesis API and report in which eligible bottom-up asset/work-package values sum toward a compatible project total, and compatible disclosed totals allocate back through architecture-specific bands. Both directions will reconcile algebraically or expose a named variance.

## Planned Tasks and TDD Order

1. A preflight RED test will require #1040 manifest v2 and its exact schema/input hashes.
2. Interval RED tests will define closed/open bounds, Decimal quantization, addition, subtraction `[Tlo-Ehi, Thi-Elo]`, zero crossing, and coverage denominators.
3. Eligibility RED tests will fail closed unless currency, price basis, ownership, phase, scope, and `capex_basis` match the target total.
4. Ledger RED tests will prove that link/scope/value/evidence fields cannot influence arithmetic except through counting disposition and that an award identity contributes at most once per overlap group.
5. Bottom-up synthesis will compute eligible subtotal interval, target interval, residual, and coverage without midpoint laundering.
6. Top-down synthesis will use disclosed splits when available; otherwise approved joint architecture scenarios will each conserve 100%. Independent prior marginals will remain diagnostic only.
7. The report will allow project-total → assets and asset → project traversal with distinct styles for observed and inferred values; manifest v3 will pin the result contract.

## TDD Test List

- `test_cost_envelope_rejects_low_above_high`
- `test_bottom_up_rejects_incompatible_currency_basis_scope_or_ownership`
- `test_each_award_identity_contributes_at_most_once`
- `test_range_and_band_arithmetic_preserves_bounds`
- `test_interval_residual_is_total_low_minus_eligible_high_to_total_high_minus_eligible_low`
- `test_open_bounds_zero_crossing_and_zero_denominator_fail_safely`
- `test_not_public_and_excluded_scope_remain_visible`
- `test_bottom_up_residual_reconciles_algebraically`
- `test_top_down_allocations_sum_to_total_with_residual`
- `test_non_additive_marginal_bands_are_never_summed`
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
- [ ] Manifest v3 will pin the synthesis schema, inputs, Decimal policy, scenario set, and output hashes.

## Pseudocode

```text
assert preflight(manifest_v2)
eligible = group_once(rows where counting == included, by overlap_group)
E = interval_sum(eligible); T = compatible_project_total
residual = [T.low - E.high, T.high - E.low]
coverage = [E.low / T.high, E.high / T.low] if T.low > 0 else unavailable
for scenario in joint_scenarios: assert sum(shares) == 1; allocate T
emit manifest_v3
```

## Attested Evidence — 2026-07-16

Inspection at `090228fb` verified that `back_allocation.py` is 479 lines and its independent bands are non-additive. This plan will create bounded modules rather than extend oversized legacy files. No runtime defect is alleged; reproduction is N/A.

## Implementation and Closeout Gates

Each listed behavior will run RED then GREEN with a narrow command. Stable ordering, Decimal formatting, locale `C`, UTC/injected build time, escaping, safe URLs, and two-build SHA equality will govern outputs. Legal/de-identification scans, T3 code/artifact review, issue comment, manifest preflight, and cleanup audit will pass before close.

## Out of Scope

Historical interpolation, FX conversion, estimator training, and workbook mutation will remain outside this issue.

## Complexity: T3

This will implement the program’s load-bearing arithmetic and inference boundary.
