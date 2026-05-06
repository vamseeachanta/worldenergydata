# Plan: Issue #313 — Test infrastructure cleanup

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/313
**Status:** plan-review
**Tier:** T2 (multiple targeted cleanup fixes)

## Scope
Three sub-problems per issue:
1. Unify pytest config (multiple `pytest.ini` / `pyproject.toml` `[tool.pytest]` entries)
2. Restore `type_curves` test fixtures
3. Fix broken imports across test directories

## Plan

### Task 1 — Audit pytest config state
```bash
find . -name "pytest.ini" -o -name "conftest.py" | head -20
grep -n "\[tool.pytest" pyproject.toml
```
Identify if there are conflicting pytest configurations.

### Task 2 — Unify into single `pyproject.toml` pytest section
Merge any standalone `pytest.ini` content into `pyproject.toml [tool.pytest.ini_options]`.
Delete standalone `pytest.ini` if present.

### Task 3 — Restore type_curves fixtures
```bash
uv run pytest tests/modules/bsee/analysis/test_type_curves.py --collect-only 2>&1 | head -20
```
If collection fails due to missing fixtures, identify what was deleted and either:
- Restore the fixture factory inline in the test
- Create `tests/fixtures/bsee/type_curves.py` with minimal synthetic data

### Task 4 — Fix remaining broken imports
```bash
uv run pytest tests/ --collect-only -q 2>&1 | grep "ImportError\|ModuleNotFoundError" | head -20
```
For each unique broken import:
- If module renamed: update import
- If module deleted: remove or skip the test with `reason=`

### Task 5 — Verify clean collection
```bash
uv run pytest tests/ --collect-only -q 2>&1 | tail -5
```
Target: no ImportError or collection errors.

## Acceptance Criteria
- Single unified pytest config in `pyproject.toml`
- `tests/` directory collects without ImportError
- `type_curves` tests collect and run (or explicitly skipped with reason)
