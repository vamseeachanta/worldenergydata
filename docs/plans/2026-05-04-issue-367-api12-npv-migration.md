# Plan: Issue #367 — Migrate ProductionAPI12 NPV to FDAS forward layer

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/367
**Status:** plan-review
**Tier:** T3 (module refactor with parity tests)

## Context
Issue #357 restored `ProductionAPI12Analysis.calculate_npv()` by wiring it to legacy
`NPVCalculator` in `bsee/analysis/legacy/api12_economics.py` (~400 LOC, hardcoded prices,
Excel-2019 benchmarks). This plan migrates to the validated `fdas.core.financial.calculate_npv()`.

## Plan

### Task 1 — Read both code paths
- `src/worldenergydata/modules/bsee/analysis/production_api12.py` — find `calculate_npv()`
- `src/worldenergydata/modules/bsee/analysis/legacy/api12_economics.py` — understand legacy NPVCalculator
- `src/worldenergydata/fdas/core/financial.py` — understand FDAS API signature

### Task 2 — Implement migration
In `production_api12.py`:
- Replace `NPVCalculator(...)` delegation with `fdas.core.financial.calculate_npv(cashflows, discount_rate, ...)`
- Remove hardcoded oil price fallbacks — require caller to pass price assumption or default to `lower_tertiary.wti_prices` median
- Pass period parameter consistent with the 39-test FDAS validation suite

### Task 3 — Write parity assertion test
`tests/unit/bsee/test_api12_npv_parity.py`:
- On a representative fixture cashflow (not lease-dependent), assert legacy vs new path agree within 0.5% tolerance
- If results diverge: document in test as expected behavioral diff with explanation

### Task 4 — Quarantine or delete legacy path
- If no other callers: move `bsee/analysis/legacy/api12_economics.py` to `_archive/`
- Add `# noqa: F401` or deletion; update imports

### Task 5 — Update issue cross-references
- Comment on #339 and #341 — legacy NPV tests may retire once this lands

## Acceptance Criteria
- `ProductionAPI12Analysis.calculate_npv()` uses `fdas.core.financial.calculate_npv`
- No hardcoded oil prices in the migration path
- Parity test exists (pass or documented deviation)
- Legacy `NPVCalculator` no longer imported in production code path
