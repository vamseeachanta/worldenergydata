# Plan: Issue #278 — Restore broken modules.* compatibility shims

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/278
**Status:** plan-review
**Tier:** T2 (targeted import fixes, no design changes)

## Root Cause
After bsee and marine_safety consolidation, `__init__.py` files still import
deleted submodules, causing collection failures:
- `modules/bsee/analysis/type_curves/__init__.py` → deleted submodules
- `modules/marine_safety/importers/__init__.py` → deleted importer modules
- `modules/marine_safety/analysis/incidents/__init__.py` → deleted analysis modules
- `modules/marine_safety/processors/__init__.py` → deleted processor modules

## Plan

### Task 1 — Reproduce collection failures
```bash
uv run pytest tests/modules/bsee/analysis/test_type_curves.py --collect-only -q 2>&1 | head -20
uv run pytest tests/unit/marine_safety/ --collect-only -q 2>&1 | head -20
```

### Task 2 — Audit broken imports
For each broken `__init__.py`, identify which imports are broken:
```bash
python3 -c "from worldenergydata.modules.bsee.analysis.type_curves import *" 2>&1
python3 -c "from worldenergydata.modules.marine_safety.importers import *" 2>&1
```

### Task 3 — Fix each broken `__init__.py`
Options per import:
- If the module was renamed: update import to new path
- If the module was deleted and has no replacement: remove from `__init__.py`
- If backward compat is needed: add re-export stub pointing to new location

**Do not add re-export stubs for code that has been permanently deleted.**

### Task 4 — Verify collection
```bash
uv run pytest tests/modules/bsee/ tests/unit/marine_safety/ --collect-only -q 2>&1 | tail -10
```
No `ImportError` or `ModuleNotFoundError` at collection time.

### Task 5 — Run subset of collected tests
```bash
uv run pytest tests/modules/bsee/analysis/test_type_curves.py -x -q
```

## Acceptance Criteria
- `tests/modules/bsee/` and `tests/unit/marine_safety/` collect without ImportError
- No deleted module is re-imported from `__init__.py` files
