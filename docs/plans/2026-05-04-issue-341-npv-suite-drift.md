# Plan: Issue #341 — Reconcile NPV comparison suite drift

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/341
**Status:** plan-review
**Tier:** T2 (test triage and cleanup)

## Context

`tests/modules/bsee/analysis/npv-data-source-comparison/` contains 5 test files.
After #339 stabilizes the 4 core legacy tests, this issue addresses the remaining
failures from separate root causes:
- `test_npv_integration_workflow.py` — uses legacy `generate_revenue_table` API, imports missing validation helper
- `test_oil_price_extraction.py` — references Excel file at `docs/NPV_JStM-...xlsx`; requires data file not in git

## Plan

### Task 1 — Run full failure inventory
```bash
uv run pytest tests/modules/bsee/analysis/npv-data-source-comparison/ -v 2>&1 | head -80
```
Classify each failure:
- `MISSING_DATA`: test requires file not in git → skip with `pytest.mark.skip(reason="requires local data file")`
- `STALE_API`: test uses removed/renamed API → update to current API or delete
- `MISSING_HELPER`: imports a helper that doesn't exist → inline or delete

### Task 2 — Fix `test_oil_price_extraction.py`
The fixture references `Path("docs") / "NPV_JStM-WELL-Production-Data-thru-2019.xlsx"`.
This file is not in git (local data). Apply:
```python
@pytest.mark.skip(reason="requires local Excel data file not in git; run manually with make data")
```
to the full class `TestOilPriceExtraction`.

### Task 3 — Fix `test_npv_integration_workflow.py`
- If `generate_revenue_table` was removed/renamed: update to current API surface
- If the test relies on deleted infrastructure: mark `@pytest.mark.skip(reason="legacy workflow removed; see #339")`

### Task 4 — Confirm no remaining collection errors
```bash
uv run pytest tests/modules/bsee/analysis/npv-data-source-comparison/ --collect-only -q
```
All files must collect cleanly (no ImportError, no AttributeError at collection time).

## Acceptance Criteria
- All files in `npv-data-source-comparison/` collect without error
- No test fails due to path-portability or missing-helper issues
- Remaining skips have explicit `reason=` documenting the prerequisite
