# Stream A — Issue #335

Issue: #335
URL: https://github.com/vamseeachanta/worldenergydata/issues/335
Goal: implement the derived-only linkage contract for exact `(operator, project_name)` matching between approved disclosure project rows and existing `CostDataPoint` sanction records.

Owned paths:
- `src/worldenergydata/cost/data_collection/linkage.py`
- `src/worldenergydata/cost/data_collection/__init__.py`
- `tests/unit/cost/test_linkage.py`

Read-only paths:
- `src/worldenergydata/cost/data_collection/public_dataset.py`
- `src/worldenergydata/cost/data_collection/calibration_schema.py`
- `tests/unit/cost/test_calibration_schema.py`
- `tests/unit/cost/test_proxy_comparison.py`
- `docs/plans/2026-04-22-issue-335-disclosure-to-costdatapoint-linkage-model.md`
- `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md`

Forbidden paths:
- `src/worldenergydata/cost/disclosure_analytics.py`
- `src/worldenergydata/cost/__init__.py`
- `src/worldenergydata/fdas/`
- `src/worldenergydata/lower_tertiary/`
- `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py`
- `tests/unit/cost/test_disclosure_ingest_contract.py`
- `tests/unit/cost/test_disclosure_analytics.py`
- `tests/unit/fdas/`
- `tests/test_query_api.py`

TDD targets:
- new: `tests/unit/cost/test_linkage.py`
- regression: `tests/unit/cost/test_proxy_comparison.py`

Implementation rules:
- The resolver is a sanction-side primitive only.
- Do NOT make the public API scope-aware beyond the approved contract.
- Operator-scope disclosure rows are never linkable; this must be expressed via tests/contracts, not fuzzy runtime magic.
- Distinguish `sanctioned_records is None` from an explicitly injected empty list.
- No fuzzy matching, aliasing, trimming, or case normalization.

Execution steps:
1. Post execution start comment on #335.
2. Write failing tests in `tests/unit/cost/test_linkage.py`.
3. Implement minimal code in `linkage.py` and export from `data_collection/__init__.py`.
4. Run targeted tests.
5. Run `tests/unit/cost/test_proxy_comparison.py` as regression boundary.
6. Post closeout evidence comment; do not close the issue.
