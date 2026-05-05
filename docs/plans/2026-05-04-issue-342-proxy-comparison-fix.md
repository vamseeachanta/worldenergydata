# Plan: Issue #342 — Restore proxy comparison regression boundary

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/342
**Status:** plan-review
**Tier:** T2 (module stub creation with clear contract)

## Root Cause

`tests/unit/cost/test_proxy_comparison.py` imports from:
```python
from worldenergydata.cost.calibration.proxy_comparison import (
    ProxyComparisonResult,
    ProxyRateComparison,
    compare_calibrated_to_proxy,
)
```
`src/worldenergydata/cost/calibration/proxy_comparison.py` does not exist.
Only `cost_predictor.py` is present in `cost/calibration/`.

## Decision

Create the `proxy_comparison.py` module implementing the contract the test expects.
The module bridges `CostPredictor` calibrated rates against WRK-019 proxy rates.

## Plan

### Task 1 — Implement `proxy_comparison.py`
File: `src/worldenergydata/cost/calibration/proxy_comparison.py`

Exports required by the test:
- `ProxyComparisonResult` — dataclass with fields: `cell_key`, `calibrated_rate`, `proxy_rate`, `bias`, `rmse`
- `ProxyRateComparison` — class that holds a list of `ProxyComparisonResult`; has `.summary()` → dict
- `compare_calibrated_to_proxy(predictor: CostPredictor, proxy_rates: dict) -> ProxyRateComparison`

Read `tests/unit/cost/test_proxy_comparison.py` fully before implementing to match expected behavior.

### Task 2 — Export from `__init__.py`
Add to `src/worldenergydata/cost/calibration/__init__.py`:
```python
from .proxy_comparison import ProxyComparisonResult, ProxyRateComparison, compare_calibrated_to_proxy
```

### Task 3 — Verify tests collect and pass
```bash
uv run pytest tests/unit/cost/test_proxy_comparison.py -v 2>&1 | tail -20
```

## Acceptance Criteria
- `uv run pytest tests/unit/cost/test_proxy_comparison.py` exits 0
- No `ModuleNotFoundError` for `worldenergydata.cost.calibration.proxy_comparison`
