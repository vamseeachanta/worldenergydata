# Plan: Issue #327 — Fix conftest.py import path blocking marine_safety tests

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/327
**Status:** plan-review
**Tier:** T1 (single targeted fix, no design decisions)

## Root Cause

`tests/unit/marine_safety/conftest.py:16` imports from:
```python
from tests.modules.marine_safety.fixtures.sample_data import ...
```
The path `tests.modules.marine_safety.fixtures` does not exist. The actual fixture file is at:
```
tests/unit/marine_safety/fixtures/sample_data.py
```
Correct import path: `tests.unit.marine_safety.fixtures.sample_data`

## Plan

### Task 1 — Fix the import path (1 edit)
File: `tests/unit/marine_safety/conftest.py:16`
Change:
```python
from tests.modules.marine_safety.fixtures.sample_data import (
```
To:
```python
from tests.unit.marine_safety.fixtures.sample_data import (
```

### Task 2 — Verify collection succeeds
```bash
uv run pytest tests/unit/marine_safety/ --collect-only -q
```
Expected: non-zero collected items, no ImportError.

### Task 3 — Run the collected tests
```bash
uv run pytest tests/unit/marine_safety/ -x -q 2>&1 | tail -20
```
Accept any failures unrelated to the conftest import (pre-existing test failures are out of scope).

## Acceptance Criteria
- `uv run pytest tests/unit/marine_safety/ --collect-only` exits 0 with items collected
- No `ModuleNotFoundError: No module named 'tests.modules.marine_safety.fixtures'`
