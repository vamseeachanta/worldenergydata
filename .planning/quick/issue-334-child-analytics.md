## Parent
- Parent: #334

## Summary
Add derived analytics views and consumer integration surface for annual disclosure data in `cost`, `fdas`, and `lower_tertiary` workflows.

## Why
The parent issue originally bundled downstream integration and analytics into the same approval surface. Cross-review required that work to be deferred until the raw disclosure schema, linkage, and comparability layers are stable.

## Scope
- Define derived views for project cost revisions and operator annual capex series
- Define consumer-facing integration contracts for `cost`, `fdas`, and `lower_tertiary`
- Add tests demonstrating downstream consumers can use the linked/normalized disclosure views
- Document raw-vs-derived separation clearly

## Deliverables
- Derived analytics/view definitions
- Integration contract for downstream economics modules
- Example usage/tests for consumer-facing access patterns

## Out of scope
- Raw schema design for disclosure records
- Citation/ingestion pipeline work
- Core linkage matching rules
- Currency-methodology redesign
