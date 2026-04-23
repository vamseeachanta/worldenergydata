# Plan for #342: restore broken proxy comparison regression boundary

> **Status:** draft
> **Complexity:** T2
> **Date:** 2026-04-23
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/342
> **Review artifacts:** pending

---

## Resource Intelligence Summary

### Existing repo code
- `tests/unit/cost/test_proxy_comparison.py` imports `ProxyComparisonResult`, `ProxyRateComparison`, and `compare_calibrated_to_proxy` from `worldenergydata.cost.calibration.proxy_comparison`.
- `src/worldenergydata/cost/calibration/` currently has no `proxy_comparison.py`, so the regression boundary fails at import/collection before executing any assertions.
- `src/worldenergydata/bsee/analysis/cost/cost_calibration.py` contains a different proxy-comparison concept (`CalibrationComparison` / `_build_proxy_comparisons`) under the BSEE calibration stack, but that module does not satisfy the tested `cost.calibration.proxy_comparison` import contract.
- `src/worldenergydata/cost/data_collection/public_dataset.py` is the sanctioned public dataset consumed by the failing regression test.

### Documents and issues consulted
- Issue #342 body
- #335 / #337 / #338 closeout evidence from the completed disclosure execution wave
- `tests/unit/cost/test_calibration_schema.py` as adjacent sanction-layer regression boundary
- `scripts/review/results/2026-04-22-plan-336-codex.md` because #336 referenced the same regression boundary as a compatibility check

### Gaps identified
- The intended ownership of proxy comparison is ambiguous: the test expects a `cost.calibration` surface, while available code exposes a BSEE-side calibration report surface.
- No current module-level docs explain whether the missing module was removed intentionally, renamed, or never implemented.
- Disclosure-wave compatibility validation cannot rely on this regression path until the import boundary is repaired or explicitly replaced.

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md` |
| Failing regression test | `tests/unit/cost/test_proxy_comparison.py` |
| Sanction dataset | `src/worldenergydata/cost/data_collection/public_dataset.py` |
| Existing calibration predictor surface | `src/worldenergydata/cost/calibration/cost_predictor.py` |
| Nearby proxy-comparison implementation precedent | `src/worldenergydata/bsee/analysis/cost/cost_calibration.py` |
| Adjacent sanction-schema boundary | `tests/unit/cost/test_calibration_schema.py` |

---

## Deliverable

A repaired and explicit proxy-comparison regression boundary in the `worldenergydata.cost.calibration` namespace that either restores the missing `proxy_comparison.py` public contract or truthfully retargets the regression test to the surviving supported module, with tests passing from import through comparison behavior.

---

## Scope Boundaries

### In scope now
- Decide whether `worldenergydata.cost.calibration.proxy_comparison` is the canonical supported surface
- Restore or retarget the public proxy-comparison contract to match reality
- Keep the fix narrow and limited to the broken regression boundary
- Add or adjust tests so importability, return types, and bias/RMSE semantics are grounded on the chosen supported module
- Document the chosen ownership boundary in code comments/module docs

### Explicitly out of scope for this issue
- Redesigning the broader BSEE cost calibration stack
- Expanding annual disclosure analytics or linkage behavior
- Reworking the sanctioned public dataset schema
- Normalization/comparability policy work from #336

---

## Pseudocode

```text
inspect failing test import contract
inspect current cost.calibration and bsee.analysis.cost surfaces
if missing module is still intended public API:
    create cost/calibration/proxy_comparison.py
    expose ProxyComparisonResult, ProxyRateComparison, compare_calibrated_to_proxy
    implement via current predictor + sanctioned dataset semantics
else:
    retarget test to the supported replacement surface
    preserve all behavior assertions with truthful module ownership
run targeted tests for proxy comparison + adjacent sanction boundaries
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Modify or create | `src/worldenergydata/cost/calibration/proxy_comparison.py` | restore supported public contract if this is the intended namespace |
| Verify or modify | `src/worldenergydata/cost/calibration/__init__.py` | export proxy-comparison surface if needed |
| Verify only | `src/worldenergydata/cost/calibration/cost_predictor.py` | ensure predictor behavior remains compatible |
| Verify only | `src/worldenergydata/bsee/analysis/cost/cost_calibration.py` | use only as reference unless ownership intentionally shifts |
| Modify | `tests/unit/cost/test_proxy_comparison.py` | align regression boundary with truthful supported surface |
| Verify only | `tests/unit/cost/test_calibration_schema.py` | ensure adjacent sanction-layer boundary still passes |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_proxy_comparison_module_imports` | supported import path exists again | module import | success |
| `test_compare_returns_list` | compare surface remains callable | fitted predictor + public dataset | list result |
| `test_all_results_are_proxy_comparison_result` | typed result contract is explicit | comparison output | all typed instances |
| `test_bias_pct_calculated` | bias sign/math semantics remain stable | comparison output | expected bias formula |
| `test_confidence_levels_present` | output classification remains bounded | comparison output | valid confidence values |
| `test_compare_calibrated_to_proxy_trains_unfitted_predictor` | convenience path still works | unfitted predictor | non-empty results |
| `test_calibration_schema_boundary_unchanged` | adjacent sanction schema remains unaffected | current schema tests | pass |

---

## Acceptance Criteria

- [ ] `tests/unit/cost/test_proxy_comparison.py` no longer fails at import/collection on current `main`
- [ ] The chosen module/test ownership boundary is explicit and truthful in code
- [ ] Proxy-comparison return types and bias semantics remain covered by targeted tests
- [ ] The fix is narrow and does not reopen unrelated disclosure or BSEE calibration redesign work
- [ ] Adjacent sanction-layer regression checks still pass

---

## Risks and Open Questions

- If the only surviving implementation is the BSEE-side calibration report path, we must decide whether to wrap it or to rewrite the test to the supported surface without creating a misleading duplicate API.
- If hidden callers rely on the old import path, restoring a thin compatibility wrapper may be safer than retargeting tests alone.
- Need to verify whether CI failures on current PRs are baseline repo noise versus regressions specific to this boundary before using CI as the primary acceptance signal.

---

## Complexity: T2

**T2** — bounded regression-boundary repair with a narrow surface-area decision, provided the issue stays focused on restoring/truthfully retargeting the missing proxy-comparison contract rather than redesigning calibration architecture.
