# Plan: Issue #325 — Fix 8 pre-existing xfail bugs

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/325
**Status:** plan-review
**Tier:** T2 (8 targeted bug fixes in 2 files)

## Files
- `src/worldenergydata/modules/bsee/analysis/compliance/compliance_calculations.py`
- `src/worldenergydata/modules/bsee/analysis/compliance/compliance_template.py`
- `src/worldenergydata/modules/bsee/analysis/compliance/compliance_visualization.py`

## Plan

### Task 1 — Float equality (bug 1)
File: `compliance_calculations.py`
Fix float comparison to use `pytest.approx` or `abs(result - 110.0) < 1e-9`.

### Task 2 — Safety score cap (bug 2)
File: `compliance_calculations.py::ComplianceMetrics.calculate_safety_score`
Either cap at 1.0 (update test expectation) or remove cap (match test's `score > 1.0`).
Check spec to determine intended behavior.

### Task 3 — Hardcoded future date (bug 3)
File: `compliance_calculations.py::test_is_overdue_false_future_date`
Replace `2025-12-31` with `(datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")`.

### Task 4 — Missing methods on ComplianceTemplate (bugs 4, 5)
File: `compliance_template.py`
Add:
- `get_compliance_status_color(status: str) -> str`
- `_create_compliance_dashboard(context: dict) -> Any`
Based on test expectations.

### Task 5 — KeyError on partial context (bug 6)
File: `compliance_visualization.py::create_production_quota_chart`
Add: `quota = context.get("gas_quota", 0)` instead of `context["gas_quota"]`.

### Task 6 — Misleading "error" in chart HTML (bug 7)
File: `compliance_visualization.py`
Find where literal `"error"` is embedded in chart HTML. Replace with empty string or
proper error state rendering.

### Task 7 — ValueError on invalid input (bug 8)
File: `compliance_visualization.py::generate_compliance_visualizations`
Wrap plotly call in try/except, return empty figure or `None` on invalid input.

### Task 8 — Remove xfail markers
After fixes pass, remove `@pytest.mark.xfail` from the 10 tests.

## Acceptance Criteria
- `uv run pytest tests/modules/bsee/analysis/comprehensive-report-system/ -v` — all 10 formerly-xfail tests pass
- No remaining xfail markers in those files
