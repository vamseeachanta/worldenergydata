## Parent
- Parent: #334

## Summary
Standardize citation quality requirements and define automated ingestion contracts for annual operator disclosures.

## Why
Parent issue #334 will use a tiny hand-curated seed dataset, but long-term value requires enforceable provenance standards and scalable ingestion. Cross-review also highlighted row-level provenance rigor as a blocker area.

## Scope
- Define minimum citation/provenance contract for every disclosure row
- Define source-priority hierarchy across annual reports, SEC filings, regulator docs, presentations, and press releases
- Add validator rules for source URL/title, page reference, quote support, and confidence
- Define duplicate/conflict detection behavior during ingest
- Define ingestion contract/templates for future automation

## Deliverables
- Citation/provenance standard
- Ingestion contract and validators
- Duplicate/conflict handling rules
- Tests showing ingested records satisfy provenance minimums

## Out of scope
- Broad operator coverage commitments
- Downstream analytics or economics-module consumption
- Currency normalization methodology
- Linkage-model expansion beyond consuming the approved linkage contract
