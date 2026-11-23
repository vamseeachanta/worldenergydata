# Stream B — Issue #338

Issue: #338
URL: https://github.com/vamseeachanta/worldenergydata/issues/338
Goal: implement derived annual disclosure analytics views plus the FDAS disclosure namespace/API seam, while keeping lower-tertiary mapping deferred and cost benchmarking limited to already-comparable rows.

Owned paths:
- `src/worldenergydata/cost/disclosure_analytics.py`
- `src/worldenergydata/cost/__init__.py`
- `src/worldenergydata/fdas/api.py`
- `src/worldenergydata/fdas/__init__.py`
- `tests/unit/cost/test_disclosure_analytics.py`
- `tests/unit/fdas/test_disclosure_api.py`
- `tests/test_query_api.py`

Read-only paths:
- `src/worldenergydata/cost/calibration/cost_predictor.py`
- `src/worldenergydata/lower_tertiary/npv.py`
- `docs/plans/2026-04-22-issue-338-annual-disclosure-analytics-views-and-consumer-integration.md`
- `docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md`
- `docs/plans/2026-04-22-issue-336-currency-normalization-and-comparability-policy-for-annual-disclosures.md`

Forbidden paths:
- `src/worldenergydata/cost/data_collection/`
- `src/worldenergydata/cost/data_collection/linkage.py`
- `src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py`
- `tests/unit/cost/test_linkage.py`
- `tests/unit/cost/test_disclosure_ingest_contract.py`
- `src/worldenergydata/lower_tertiary/npv.py`
- `tests/unit/lower_tertiary/`

TDD targets:
- new: `tests/unit/cost/test_disclosure_analytics.py`
- new: `tests/unit/fdas/test_disclosure_api.py`
- regression: `tests/test_query_api.py`

Implementation rules:
- Do not change lower-tertiary behavior in this issue.
- Do not define comparability policy here; only accept/refuse rows already comparable under #336 outputs.
- Keep raw-vs-derived separation explicit.
- FDAS surface must be grounded in `fdas/api.py` + `fdas/__init__.py`.
- Cost-side hook must remain thin and must not mutate `CostPredictor` semantics.

Execution steps:
1. Post execution start comment on #338.
2. Write failing tests for derived views and FDAS API exposure.
3. Implement `cost/disclosure_analytics.py` and required export/API changes.
4. Run targeted tests.
5. Run `tests/test_query_api.py` as package-level regression.
6. Post closeout evidence comment; do not close the issue.
