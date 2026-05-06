# Plan: Issue #316 — Incremental mypy cleanup (~2918 errors)

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/316
**Status:** plan-review
**Tier:** T2 (incremental cleanup in waves, not a single PR)

## Strategy
2918 errors is too many for one PR. Use a wave approach, targeting the highest-ROI
error codes first: `no-untyped-def` (978) is the largest class and mostly mechanical.

## Plan

### Task 1 — Establish current baseline
```bash
uv run mypy src/ --ignore-missing-imports 2>&1 | python3 -c "
import sys, collections
errors = collections.Counter()
for line in sys.stdin:
    m = __import__('re').search(r'\[(\w[\w-]+)\]', line)
    if m: errors[m.group(1)] += 1
for k,v in errors.most_common(10): print(f'{v:5d}  {k}')
"
```

### Task 2 — Wave 1: no-untyped-def (978 errors)
For each function missing annotations, add `-> None` to void functions and
`-> ReturnType` to others. Focus on `src/worldenergydata/common/` and `fdas/` first
(most-imported modules). Aim: reduce error count by ≥200.

### Task 3 — Wave 2: attr-defined (318 errors)
Often caused by `Optional[X]` accessed without None-check. Add guards or use `assert`.

### Task 4 — CI gate
In `pyproject.toml`:
```toml
[tool.mypy]
ignore_missing_imports = true
warn_return_any = false  # silence during incremental cleanup
```
Add `uv run mypy src/worldenergydata/common/ src/worldenergydata/fdas/` to CI (scoped).

## Acceptance Criteria
- Wave 1 complete: `no-untyped-def` count reduced by ≥200 errors
- `src/worldenergydata/common/` and `fdas/` are clean (0 mypy errors for these paths)
- CI runs mypy on these two scoped paths and passes
