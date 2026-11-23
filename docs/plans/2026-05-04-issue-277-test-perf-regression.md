# Plan: Issue #277 — Investigate test suite performance regressions

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/277
**Status:** plan-review
**Tier:** T2 (performance investigation + targeted fix)

## Observed Regressions
- `TestAPISettings::test_default_values` — 1570× slower
- `TestDataValidatorInit::test_init_without_config` — 164–816× (high variance)
- `TestValidationErrorInitialization` — 130× slower

High variance on `test_init_without_config` suggests I/O or import-time cold start.

## Plan

### Task 1 — Reproduce regressions
```bash
uv run pytest tests/unit/test_settings.py::TestAPISettings::test_default_values \
  tests/unit/test_validators_data_validator.py::TestDataValidatorInit -v --tb=short \
  2>&1 | grep -E "PASSED|FAILED|seconds"
```

### Task 2 — Profile slow tests
```bash
uv run pytest tests/unit/test_settings.py::TestAPISettings::test_default_values \
  --profile --profile-svg 2>&1 | head -30
```
Or use `pytest-timeout` + print statements to isolate which line is slow.

### Task 3 — Root cause analysis
Hypothesis A — File I/O in Settings init: check if `Settings()` reads from disk on every instantiation.
Fix: cache `Settings` singleton or use `@functools.lru_cache`.

Hypothesis B — Import latency: check if `from worldenergydata.common import get_settings` triggers heavy imports.
Fix: lazy-load heavy dependencies inside the function body.

Hypothesis C — Fixture setup: check if autouse fixtures in conftest do expensive work.

### Task 4 — Fix root cause
Apply the appropriate fix from Task 3 analysis.

### Task 5 — Verify speedup
```bash
uv run pytest tests/unit/test_settings.py -v --tb=short
```
Target: slowdown factor < 5× baseline.

## Acceptance Criteria
- Root cause documented in issue comment
- Slowest test reduced from 1570× to < 5× vs baseline
- No regressions in test correctness
