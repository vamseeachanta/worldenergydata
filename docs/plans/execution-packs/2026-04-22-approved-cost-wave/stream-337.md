# Stream C — Issue #337

Issue: #337
URL: https://github.com/vamseeachanta/worldenergydata/issues/337
Goal: implement the disclosure-layer citation/provenance and ingest classification contract on top of the disclosure boundary from #334, with explicit accepted/duplicate/conflict/invalid partitioning and conflict-reason codes.

Launch only after Stream A (#335) completes and pushes because both streams own `src/worldenergydata/cost/data_collection/__init__.py`.

Owned paths:
- `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py`
- `src/worldenergydata/cost/data_collection/__init__.py`
- `tests/unit/cost/test_disclosure_ingest_contract.py`

Read-only paths:
- `src/worldenergydata/cost/data_collection/operator_disclosures_schema.py`
- `src/worldenergydata/cost/data_collection/operator_disclosures_dataset.py`
- `tests/unit/cost/test_operator_disclosures.py`
- `docs/plans/2026-04-22-issue-337-citation-quality-and-automated-ingestion-contracts-for-annual-disclosures.md`
- `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md`
- `src/worldenergydata/cost/data_collection/public_dataset.py`
- `tests/unit/cost/test_calibration_schema.py`
- `tests/unit/cost/test_proxy_comparison.py`

Forbidden paths:
- `src/worldenergydata/cost/disclosure_analytics.py`
- `src/worldenergydata/cost/__init__.py`
- `src/worldenergydata/fdas/`
- `src/worldenergydata/lower_tertiary/`
- `src/worldenergydata/cost/data_collection/linkage.py`
- `tests/unit/cost/test_linkage.py`
- `tests/unit/cost/test_disclosure_analytics.py`
- `tests/unit/fdas/`
- `tests/test_query_api.py`

TDD targets:
- new: `tests/unit/cost/test_disclosure_ingest_contract.py`
- regression: `tests/unit/cost/test_operator_disclosures.py`

Implementation rules:
- Stay on disclosure-layer surfaces only.
- Do NOT modify `public_dataset.py` or widen `CostDataPoint` to annual-disclosure citation fields.
- Conflict reasoning must use explicit reason codes.
- Source-priority affects conflict annotation, not automatic winner selection.
- Duplicate/conflict classification must work both against existing rows and within the incoming batch.

Execution steps:
1. Post execution start comment on #337.
2. Write failing tests for citation validity, accepted/duplicate/conflict/invalid partitioning, and conflict reason codes.
3. Implement `disclosure_ingest_contract.py` and export primitives from `data_collection/__init__.py`.
4. Run targeted tests.
5. Run `tests/unit/cost/test_operator_disclosures.py` as disclosure-layer compatibility boundary if present.
6. Post closeout evidence comment; do not close the issue.
