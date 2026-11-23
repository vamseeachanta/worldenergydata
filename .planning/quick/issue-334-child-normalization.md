## Parent
- Parent: #334

## Summary
Add currency normalization and comparability policy for annual disclosure records while preserving as-reported values.

## Why
Cross-review explicitly called out mixed-currency and comparability ambiguity. Parent issue #334 will preserve as-reported values only. A follow-up issue is needed to define normalized comparison behavior cleanly instead of overloading the foundation-layer issue.

## Scope
- Define normalization policy for annual disclosure monetary records
- Preserve original as-reported amount/currency alongside normalized comparable values
- Add schema/view contract for normalized outputs
- Add tests for currency/unit pairing and reproducible normalization behavior
- Document comparability limits and assumptions

## Deliverables
- Normalization/comparability contract
- Supporting schema/view additions or utilities
- Test coverage for multi-currency records
- Documentation of assumptions and limitations

## Out of scope
- Automated FX ingestion at scale beyond the selected baseline approach
- Derived dashboards/benchmark products
- Linkage-model redesign
- Broad source-ingestion automation
