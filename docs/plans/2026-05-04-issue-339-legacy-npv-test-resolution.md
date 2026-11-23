# Plan for [#339](https://github.com/vamseeachanta/worldenergydata/issues/339): follow-up(tests): re-enable or delete legacy NPV comparison tests after financial-module audit

> **Status:** plan-review
> **Complexity:** T2
> **Date:** 2026-05-04
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/339
> **Review artifacts:** scripts/review/results/2026-05-04-plan-339-claude.md | ...-codex.md | ...-gemini.md

---

## Resource Intelligence Summary

### Existing repo code

- Found: `src/worldenergydata/fdas/api.py` — `EconomicsQuery.npv(cashflows, discount_rate, *, period, trimmed)` is the canonical post-refactor entry point; accepts plain lists or numpy arrays, returns `float`
- Found: `src/worldenergydata/bsee/analysis/production_api12.py` — `ProductionAPI12Analysis.perform_npv_calculation(cfg, revenue_df)` still exists as a thin delegation wrapper; class is not removed but is the legacy surface
- Found: `src/worldenergydata/bsee/analysis/legacy/production_api12_original.py` — original implementation moved to `legacy/`; confirms the refactor is structural and complete
- Found: `tests/modules/bsee/analysis/npv-data-source-comparison/test_cash_flow_components.py` — lines 444–453: `TestProductionAPI12CashFlowMethods` class gated behind `@pytest.mark.skipif(not PRODUCTION_API12_AVAILABLE, …)` — one live skip marker targeting the legacy class
- Found: `tests/modules/bsee/analysis/npv-data-source-comparison/test_current_npv_implementation.py` — lines 23–27: hard import of `ProductionAPI12Analysis`; all six test methods call `self.analyzer.perform_npv_calculation(…)` directly with no guard
- Found: `tests/modules/bsee/analysis/npv-data-source-comparison/test_npv_integration_workflow.py` — lines 23–30: try/except import of `ProductionAPI12Analysis` + `engine`; lines 433/441/453/484/544: five `pytest.skip()` call-sites for Excel-data and archived-validator unavailability; line 580: `@pytest.mark.skipif(not ENGINE_AVAILABLE, …)`
- Found: `tests/modules/bsee/analysis/npv-data-source-comparison/test_oil_price_extraction.py` — no `ProductionAPI12Analysis` references; tests operate directly on Excel file rows; no skip markers
- Found: `tests/_archive/modules/bsee/analysis/test_excel_aligned_npv.py` — line 29: hard import of `ProductionAPI12Analysis` from old namespace `worldenergydata.bsee.analysis.production_api12`; already archived
- Found: `tests/_archive/modules/bsee/analysis/test_npv_accuracy_validation.py` — lines 23/508/512/540/548: references `ProductionAPI12Analysis`; already archived; also referenced at runtime by `test_npv_integration_workflow.py:429`
- Gap: No `EconomicsQuery`-based tests exist in `tests/modules/bsee/analysis/npv-data-source-comparison/`; the directory only targets the legacy API shape

### Standards

| Standard | Status | Source |
|---|---|---|
| n/a | not applicable | This is a test-maintenance issue, not an engineering-standards issue |

### LLM Wiki pages consulted

- No relevant wiki pages — scope is internal test refactoring with no domain-standard dependency

### Documents consulted

- `docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md` — prior NPV-adjacent plan; context: proxy boundary tests; confirmed stabilization pattern used previously
- GitHub issue #339 (worldenergydata) — issue body documents that workspace-hub #2451 added temporary stabilization skip markers; this plan resolves the deferred decision
- GitHub issue #2451 (workspace-hub) — confirmed as the source of the skip/guard markers present in `test_cash_flow_components.py` and `test_npv_integration_workflow.py`
- GitHub issue #2433 (workspace-hub) — listed as related in issue body; financial-module audit parent

### Gaps identified

- No `EconomicsQuery.npv()`-based tests exist for cash-flow computation paths — must be written from scratch for test files that are kept
- `test_current_npv_implementation.py` has no guard and will fail immediately if `ProductionAPI12Analysis.perform_npv_calculation` is removed — requires full rewrite targeting `EconomicsQuery.npv()`

### Evidence (embedded verification)

**Issue statuses** (verified 2026-05-04 via `gh issue view`):
- `worldenergydata#339` — OPEN — follow-up(tests): re-enable or delete legacy NPV comparison tests after financial-module audit

**File existence** (`ls -la` 2026-05-04):
- EXISTS: `tests/modules/bsee/analysis/npv-data-source-comparison/test_cash_flow_components.py`
- EXISTS: `tests/modules/bsee/analysis/npv-data-source-comparison/test_current_npv_implementation.py`
- EXISTS: `tests/modules/bsee/analysis/npv-data-source-comparison/test_npv_integration_workflow.py`
- EXISTS: `tests/modules/bsee/analysis/npv-data-source-comparison/test_oil_price_extraction.py`
- EXISTS: `tests/modules/bsee/analysis/npv-data-source-comparison/investigate_excel_npv_structure.py`
- EXISTS: `tests/_archive/modules/bsee/analysis/test_excel_aligned_npv.py`
- EXISTS: `tests/_archive/modules/bsee/analysis/test_npv_accuracy_validation.py`
- EXISTS: `src/worldenergydata/fdas/api.py` — contains `EconomicsQuery.npv()`
- EXISTS: `src/worldenergydata/bsee/analysis/production_api12.py` — `perform_npv_calculation` present (delegation wrapper)
- EXISTS: `src/worldenergydata/bsee/analysis/legacy/production_api12_original.py`

**Line excerpts** — skip/legacy markers in active test files:

```
# test_cash_flow_components.py lines 444–447
@pytest.mark.skipif(
    not PRODUCTION_API12_AVAILABLE, reason="ProductionAPI12Analysis not available"
)
class TestProductionAPI12CashFlowMethods:

# test_npv_integration_workflow.py line 580
@pytest.mark.skipif(not ENGINE_AVAILABLE, reason="Engine components not available")

# test_npv_integration_workflow.py lines 433/441/453
pytest.skip("Archived NPV accuracy validator is unavailable")
pytest.skip("Excel data not available for accuracy validation")
pytest.skip("Could not calculate benchmark NPV")

# test_current_npv_implementation.py lines 23–24 (hard import, no guard)
from worldenergydata.modules.bsee.analysis.production_api12 import (
    ProductionAPI12Analysis,
```

**EconomicsQuery.npv() signature** (`src/worldenergydata/fdas/api.py` lines 53–60):
```python
@staticmethod
def npv(
    cashflows: Union[Sequence[float], np.ndarray],
    discount_rate: float,
    *,
    period: str = "monthly",
    trimmed: bool = False,
) -> float:
```

<!-- Verification: distinct sources — issue body (1), production_api12.py (2), fdas/api.py (3), test_cash_flow_components.py (4), test_current_npv_implementation.py (5), test_npv_integration_workflow.py (6), test_oil_price_extraction.py (7), archive tests (8), prior plan #342 (9). Count: 9. Minimum 3 met. -->

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-05-04-issue-339-legacy-npv-test-resolution.md` |
| Keep + repoint | `tests/modules/bsee/analysis/npv-data-source-comparison/test_cash_flow_components.py` |
| Rewrite | `tests/modules/bsee/analysis/npv-data-source-comparison/test_current_npv_implementation.py` |
| Repoint | `tests/modules/bsee/analysis/npv-data-source-comparison/test_npv_integration_workflow.py` |
| Keep as-is | `tests/modules/bsee/analysis/npv-data-source-comparison/test_oil_price_extraction.py` |
| Delete | `tests/modules/bsee/analysis/npv-data-source-comparison/investigate_excel_npv_structure.py` |
| Already archived | `tests/_archive/modules/bsee/analysis/test_excel_aligned_npv.py` |
| Already archived | `tests/_archive/modules/bsee/analysis/test_npv_accuracy_validation.py` |
| Reference implementation | `src/worldenergydata/fdas/api.py` — `EconomicsQuery.npv()` |
| Plan review — Claude | `scripts/review/results/2026-05-04-plan-339-claude.md` |
| Plan review — Codex | `scripts/review/results/2026-05-04-plan-339-codex.md` |
| Plan review — Gemini | `scripts/review/results/2026-05-04-plan-339-gemini.md` |

---

## Deliverable

All test files under `tests/modules/bsee/analysis/npv-data-source-comparison/` either pass cleanly against `EconomicsQuery.npv()` or are deleted; no `pytest.skip`, `xfail`, or `skipif` markers referencing `ProductionAPI12Analysis`, `ENGINE_AVAILABLE`, or `PRODUCTION_API12_AVAILABLE` remain in that directory.

---

## Pseudocode

Per-file resolution logic:

```
# Step 1 — test_oil_price_extraction.py
  NO CHANGES: zero legacy imports, no skip markers, tests valid extraction path
  Action: keep as-is; verify passes in CI

# Step 2 — investigate_excel_npv_structure.py
  NOT a test (no test_ functions), is a one-off investigation script
  Action: delete — no test value, no production dependency

# Step 3 — test_cash_flow_components.py
  Split into two classes:
    TestCashFlowComponents (lines 1–443) — pure math tests, no legacy import
      Action: keep; verify passes without change
    TestProductionAPI12CashFlowMethods (lines 444–end) — gated behind skipif
      Tests: test_revenue_table_generation_structure, others
      Evaluate: does EconomicsQuery expose a cashflow-generating path?
      If yes: repoint fixture to EconomicsQuery; remove skipif block
      If no (cashflow generation is bsee-module-specific): delete this class
        and confirm TestCashFlowComponents standalone coverage is sufficient

# Step 4 — test_current_npv_implementation.py
  Hard import of ProductionAPI12Analysis, all tests call perform_npv_calculation
  No guard — will fail if legacy class removed
  Action: full rewrite
    replace ProductionAPI12Analysis fixture with EconomicsQuery()
    replace perform_npv_calculation(cfg, revenue_df) calls with:
      EconomicsQuery.npv(cashflows, discount_rate, period="monthly")
    preserve test intent (baseline, cash flow construction,
      discount rate application, period timing, full workflow)
    remove test_excel_benchmark_comparison (depends on archived validator)
      or rewrite if benchmark data is available in fixtures

# Step 5 — test_npv_integration_workflow.py
  try/except import guard — safe to run today but skips deeply
  Five inline pytest.skip() calls tied to Excel data + archived validator
  One class-level skipif on ENGINE_AVAILABLE
  Action: repoint
    replace ProductionAPI12Analysis workflow calls with EconomicsQuery.npv()
    replace Excel-data-dependent benchmark checks with synthetic fixture data
    remove test_npv_accuracy_requirements_validation if it solely relies
      on the archived test_npv_accuracy_validation module
    keep test_complete_integration_workflow skeleton but drive it through
      EconomicsQuery rather than engine + ProductionAPI12Analysis pipeline
    remove all pytest.skip() and skipif blocks from this file
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Keep, no change | `tests/modules/bsee/analysis/npv-data-source-comparison/test_oil_price_extraction.py` | No legacy references; valid extraction tests; passes today |
| Delete | `tests/modules/bsee/analysis/npv-data-source-comparison/investigate_excel_npv_structure.py` | Investigation script, not a test; has no `test_` functions |
| Modify | `tests/modules/bsee/analysis/npv-data-source-comparison/test_cash_flow_components.py` | Remove `TestProductionAPI12CashFlowMethods` skipif class or repoint to `EconomicsQuery` |
| Rewrite | `tests/modules/bsee/analysis/npv-data-source-comparison/test_current_npv_implementation.py` | Full repoint from `perform_npv_calculation` to `EconomicsQuery.npv()` |
| Modify | `tests/modules/bsee/analysis/npv-data-source-comparison/test_npv_integration_workflow.py` | Remove all skip markers; repoint NPV calls to `EconomicsQuery.npv()` |
| Update | `docs/plans/README.md` | Add this plan to index |

---

## TDD Test List

Tests that must pass (no skips) after this issue closes:

| Test name | File | What it verifies | Expected input | Expected output |
|---|---|---|---|---|
| `test_revenue_calculation_basic` | test_cash_flow_components.py | Revenue = production × oil price | 100 bbl/month × $70/bbl | $7,000 revenue |
| `test_opex_calculation_basic` | test_cash_flow_components.py | OPEX deducted from revenue | $7,000 revenue, $5/bbl OPEX | $6,500 net |
| `test_net_cash_flow_calculation` | test_cash_flow_components.py | Net cashflow = revenue − OPEX − CAPEX | known inputs | deterministic float |
| `test_current_npv_calculation_baseline` | test_current_npv_implementation.py (rewritten) | `EconomicsQuery.npv()` returns float for known cashflows | `[-1e6, 1e5, …]`, rate=0.10 | float, sign correct |
| `test_cash_flow_construction` | test_current_npv_implementation.py (rewritten) | cashflow list built correctly from revenue frame | synthetic DataFrame fixture | list length matches production months |
| `test_discount_rate_application` | test_current_npv_implementation.py (rewritten) | higher discount rate → lower NPV | same cashflows, 0.10 vs 0.20 | npv_10 > npv_20 |
| `test_period_timing_assumptions` | test_current_npv_implementation.py (rewritten) | `period="monthly"` vs `period="annual"` differ | same cashflows | different float values |
| `test_npv_workflow_configuration_validation` | test_npv_integration_workflow.py | config dict accepted without error | minimal valid config | no exception |
| `test_npv_calculation_workflow` | test_npv_integration_workflow.py (repointed) | end-to-end: cashflows → `EconomicsQuery.npv()` → float | synthetic cashflow list | finite float |
| `test_complete_integration_workflow` | test_npv_integration_workflow.py (repointed) | integration: data prep → NPV call → result file | synthetic config + temp dir | file written, NPV > -1e9 |
| `test_brent_price_extraction_basic` | test_oil_price_extraction.py | BRENT row reads non-null values | real Excel fixture | list of floats |
| `test_month_header_extraction` | test_oil_price_extraction.py | month headers align with price rows | real Excel fixture | correct month count |

---

## Acceptance Criteria

- [ ] All tests in `tests/modules/bsee/analysis/npv-data-source-comparison/` pass with no skips: `uv run pytest tests/modules/bsee/analysis/npv-data-source-comparison/ -v`
- [ ] `investigate_excel_npv_structure.py` is deleted from the active test directory
- [ ] Zero `pytest.skip`, `pytest.mark.skipif`, or `pytest.mark.xfail` calls referencing `PRODUCTION_API12_AVAILABLE`, `ENGINE_AVAILABLE`, or legacy NPV reasons remain in `tests/modules/bsee/analysis/npv-data-source-comparison/`
- [ ] `grep -r "ProductionAPI12" tests/modules/bsee/analysis/npv-data-source-comparison/` returns empty
- [ ] No regression: `uv run pytest tests/` passes (or matches pre-existing baseline failure count)
- [ ] Review artifacts posted to `scripts/review/results/`

---

## Adversarial Review Summary

<!-- Filled in after Step 4 completes. Do not post to GitHub until this section is populated. -->

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | APPROVE / MINOR / MAJOR | summary of findings |
| Codex | APPROVE / MINOR / MAJOR | summary of findings |
| Gemini | APPROVE / MINOR / MAJOR | summary of findings |

**Overall result:** PASS / FAIL (re-draft required)

Revisions made based on review:
- (list any changes made to the plan after adversarial review)

---

## Risks and Open Questions

- **Risk:** `TestProductionAPI12CashFlowMethods` in `test_cash_flow_components.py` tests `generate_revenue_table()` — this method is on `ProductionAPI12Analysis`, not `EconomicsQuery`. If no equivalent exists on `EconomicsQuery`, the class must be deleted and coverage verified sufficient from the remaining `TestCashFlowComponents` suite.
- **Risk:** `test_complete_integration_workflow` in `test_npv_integration_workflow.py` writes output files via `engine`; replacing `engine` with a direct `EconomicsQuery.npv()` call may require a synthetic fixture for the file-write assertion or a separate fixture directory.
- **Risk:** `test_current_npv_implementation.py:test_excel_benchmark_comparison` references an Excel benchmark file; if the file is not available in CI fixtures, this test must be deleted rather than left with a skip.
- **Open:** Does `EconomicsQuery` expose a `cashflow()` or `revenue_table()` method, or is cash-flow construction still the responsibility of the BSEE module? Confirm before deciding whether `TestProductionAPI12CashFlowMethods` can be repointed or must be deleted. (Flag for user during approval.)
- **Open:** Should `test_npv_accuracy_requirements_validation` be deleted outright or replaced with a numeric tolerance test against `EconomicsQuery.npv()` using a synthetic benchmark? (Flag for user during approval.)

---

## Complexity: T2

**T2** — four active test files requiring per-file decisions (keep/repoint/rewrite/delete), one file touching `EconomicsQuery` API, no new production code needed but test logic must be substantially rewritten in two files.
