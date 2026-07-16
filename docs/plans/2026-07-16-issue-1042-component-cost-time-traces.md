# Plan for #1042: project component-cost time traces

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-07-16
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/1042
> **Blocked by:** #1040
> **Review artifacts:** `scripts/review/results/2026-07-16-plan-1038-1044-{claude,codex,gemini}.md`

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

## Deliverable

An ordered, provenance-preserving event model and generated trace for every empirically eligible project, with separate native-currency lanes for total and component evidence.

## Planned Tasks and TDD Order

1. Tests will define event identity, date precision, event type, component link, range, currency, basis, provenance, and confidence.
2. Adapters will normalize rows from sanctioned projects, awards, statements, and revision trails without altering their source values.
3. Deduplication will use source/event identity and will surface conflicting duplicates rather than choose one silently.
4. Ordering will handle year-only, month-only, and exact dates deterministically while retaining original precision.
5. Optional real-cost views will require a separately approved deflator/method and will retain nominal values side-by-side; the default will remain nominal/native.
6. HTML will expose event-type filters, component lanes, gaps, not-public events, and exact eligible coverage.

## TDD Test List

- `test_trace_retains_original_date_precision`
- `test_events_order_deterministically_at_mixed_precision`
- `test_duplicate_identity_deduplicates_and_conflict_surfaces`
- `test_native_currencies_are_never_summed_together`
- `test_nominal_values_are_not_silently_deflated`
- `test_not_public_event_remains_visible_with_no_value`
- `test_award_event_links_to_approved_asset_identity`
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

## Out of Scope

Interpolation, forecasting, silent FX/deflation, causal claims about cost changes, and estimator training will remain outside this issue.

## Complexity: T3

The trace will merge heterogeneous evidence while preserving time, currency, basis, and provenance semantics.
