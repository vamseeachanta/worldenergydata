## Parent
- Parent: #334

## Summary
Define the deterministic linkage model between annual disclosure records and existing `CostDataPoint` sanction records.

## Why
Parent issue #334 is being narrowed to a foundation-only disclosure layer. Cross-review identified explicit linkage strategy as a missing approval blocker. Downstream analytics and economics integrations should not proceed until the relationship between recurring disclosure rows and sanction-point records is formalized.

## Scope
- Define canonical linkage identifiers and matching fields
- Support exact `(operator, project_name)` linkage as the initial deterministic rule
- Define how nullable / unmatched / ambiguous relationships are represented
- Add tests for exact match, no match, and ambiguous match behavior
- Document how downstream consumers should use linked vs unlinked rows

## Deliverables
- Linkage contract between disclosure records and `CostDataPoint`
- Validation/tests for deterministic linkage behavior
- Documentation for unmatched and ambiguous cases

## Out of scope
- Currency normalization
- Automated ingestion
- Derived analytics or dashboards
- Broad historical backfill
- `fdas` / `lower_tertiary` code integration
