# Plan for #1042: project component-cost time traces

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1042
> **Blocked by:** #1040
> **Client:** N/A
> **Lane:** lane:codex
> **Review artifacts:** R1 Codex MAJOR: `scripts/review/results/2026-07-16-plan-1038-1044-codex-r1.md`; final artifacts PENDING

## Resource Intelligence Summary

- The four curated tables will already contain dated sanction/FID rows, awards, partner/project statements, and revision/outturn points with differing time precision and confidence.
- `cost_component_timeseries.csv` will provide market component and index observations, but these will remain contextual lanes unless an explicit method links them to a project event.
- Missing years, not-public awards, and delayed source visibility will be meaningful findings. The trace will remain event-based and will not invent annual observations.

## Artifact Map

| Action | Path |
|---|---|
| Create | `packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/project_trace.py` |
| Create | `scripts/cost/build_project_cost_traces.py` |
| Create | `tests/unit/cost/test_project_cost_trace.py` |
| Generate | `reports/cost/project_cost_events.csv` |
| Generate | `reports/cost/project_cost_traces.html` |
| Generate | `data/modules/cost/derived/project_trace_contract_manifest.json` |

## Deliverable

An ordered, provenance-preserving event model and generated trace for every empirically eligible project, with separate native-currency lanes for total and component evidence.

## Planned Tasks and TDD Order

1. A preflight RED test will require #1040 manifest v2.
2. Event RED tests will define stable event identity, observed-date interval, precision, type, component link, range, currency, basis, provenance, confidence, and `validation_group_id`.
3. Adapters will normalize rows without altering values; the collapsed Sangomar midpoint will be migrated to its disclosed $4,900–5,200MM range instead of parsed from notes at runtime.
4. Deduplication will use controlled event identity and will surface conflicting duplicates rather than choose one silently.
5. Evidenced order will be a partial order over date intervals. A separate stable display key will sort unresolved ties without claiming chronology.
6. Coverage will enumerate the 85-project union, classify five trail-only projects explicitly, and report sanctioned/award/statement/trail denominators separately.
7. Optional real-cost views will use a versioned approved deflator method and will retain nominal values side-by-side; the default will remain nominal/native.
8. HTML and manifest v3-trace will expose filters, component/total consistency, gaps, not-public events, trade-press confidence, and exact coverage.

## TDD Test List

- `test_trace_retains_original_date_precision`
- `test_events_order_deterministically_at_mixed_precision`
- `test_display_tie_break_does_not_claim_evidenced_chronology`
- `test_duplicate_identity_deduplicates_and_conflict_surfaces`
- `test_native_currencies_are_never_summed_together`
- `test_nominal_values_are_not_silently_deflated`
- `test_not_public_event_remains_visible_with_no_value`
- `test_award_event_links_to_approved_asset_identity`
- `test_component_award_is_not_treated_as_cumulative_project_spend`
- `test_trade_press_outturn_retains_low_confidence`
- `test_eighty_five_project_union_and_trail_only_disposition`
- `test_sangomar_range_is_not_midpoint_laundered`
- `test_scope_and_ownership_changes_create_distinct_events`
- `test_missing_years_are_not_interpolated`
- `test_coverage_enumerates_exact_live_eligible_projects`

## Acceptance Criteria

- [ ] Every eligible project will receive a deterministic ordered trace.
- [ ] Sanction, award, revision, scope/basis change, and outturn events will remain distinct.
- [ ] Component and total lanes will preserve native currency and nominal basis.
- [ ] Missing and not-public evidence will stay visible.
- [ ] Optional normalization will require explicit method metadata and will never overwrite nominal observations.
- [ ] HTML and CSV outputs will state exact project/event coverage and regenerate deterministically.
- [ ] Manifest v3-trace will pin event schema, source hashes, precision policy, and output hashes.

## Pseudocode

```text
assert preflight(manifest_v2)
event.interval = precision_to_interval(raw_date)
event_order(a,b) only when a.interval.end < b.interval.start
display_order = stable_key(interval.start, precision, event_id)  # presentation only
preserve native amount/range and confidence; never accumulate award as spend
emit 85-project coverage + manifest
```

## Attested Evidence — 2026-07-16

Live enumeration at `090228fb` verified 34 month-precision and 15 year-precision revision rows, no day-exact revision rows, an 85-project union, and a collapsed Sangomar range. This is new feature work; reproduction is N/A.

## Implementation and Closeout Gates

Every adapter/behavior will demonstrate RED then GREEN. Serialization will use stable display ordering, Decimal, locale `C`, UTC/injected time, escaping, safe URLs, and two-build SHA equality. Legal/de-identification scans, T3 review, issue comment, manifest preflight, and cleanup audit will pass before close.

## Out of Scope

Interpolation, forecasting, silent FX/deflation, causal claims about cost changes, and estimator training will remain outside this issue.

## Complexity: T3

The trace will merge heterogeneous evidence while preserving time, currency, basis, and provenance semantics.
