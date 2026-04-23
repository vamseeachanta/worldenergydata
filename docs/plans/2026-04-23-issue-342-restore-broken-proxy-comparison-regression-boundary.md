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

A restored compatibility module at `src/worldenergydata/cost/calibration/proxy_comparison.py` that preserves the existing public import contract used by `tests/unit/cost/test_proxy_comparison.py`, adapts current `CostPredictor` + sanctioned `CostDataPoint` inputs into the tested proxy-comparison result surface, and documents that this is the supported sanction-layer regression boundary.

---

## Scope Boundaries

### In scope now
- Restore `worldenergydata.cost.calibration.proxy_comparison` as the canonical supported import path for this regression boundary.
- Build a narrow compatibility adapter around the current sanction-layer predictor/data surfaces instead of retargeting the test to an unrelated BSEE-only module.
- Use the existing proxy-rate source from the BSEE calibration feature surface as a read-only lookup precedent, with this fixed internal proxy-key set:
  - `gom`
  - `north_sea`
  - `west_africa`
  - `asia_pacific`
- Use this explicit sanctioned-region to proxy-key mapping in the adapter:
  - `GOM -> gom`
  - `NCS -> north_sea`
  - `UKCS -> north_sea`
  - `West Africa -> west_africa`
  - `Asia-Pacific -> asia_pacific`
  - `Middle East -> unsupported` (row skipped from proxy comparison in v1 until a supported proxy bucket exists)
- Derive `proxy_rate_usd_day` by reading the fixed proxy-rate table already used by the BSEE calibration feature surface; do not invent a second proxy-rate source.
- Derive `calibrated_rate_usd_day` by adapting the current sanction-layer predictor output onto the restored comparison surface, preserving the existing regression boundary semantics rather than creating a new benchmark contract.
- Preserve this exact public compatibility contract:
  - `ProxyComparisonResult(region, water_depth_band, activity_type, proxy_rate_usd_day, calibrated_rate_usd_day, bias_pct, n_data_points, rmse_usd_mm, confidence)`
  - `ProxyRateComparison(predictor=...)`
  - `compare_calibrated_to_proxy(...)`
- Add or retain tests that ground behavior on the existing regression assertions, not just importability.
- Forbid weakening or retargeting `tests/unit/cost/test_proxy_comparison.py`; it may only be tightened to reflect newly explicit adapter semantics, not relaxed to fit the implementation.
- Document the ownership boundary in code comments/module docs so future callers know this is a compatibility surface over the current sanction-layer predictor.

### Explicitly out of scope for this issue
- Retargeting the test away from `cost.calibration.proxy_comparison` as the primary fix path
- Redesigning the broader BSEE cost calibration stack
- Expanding annual disclosure analytics or linkage behavior
- Reworking the sanctioned public dataset schema
- Normalization/comparability policy work from #336

---

## Pseudocode

```text
inspect existing regression contract in tests/unit/cost/test_proxy_comparison.py
create src/worldenergydata/cost/calibration/proxy_comparison.py
within the module:
    define ProxyComparisonResult dataclass compatible with existing tests
    define ProxyRateComparison adapter that accepts the current CostPredictor
    load sanctioned CostDataPoint dataset and normalize region names to proxy keys
    compute proxy_rate_usd_day and calibrated_rate_usd_day for covered cells
    preserve bias_pct, rmse_usd_mm, confidence, and list-return behavior expected by tests
    expose compare_calibrated_to_proxy convenience function
run targeted proxy-comparison tests plus adjacent sanction boundary tests
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `src/worldenergydata/cost/calibration/proxy_comparison.py` | restore the missing supported public import path |
| Verify or modify | `src/worldenergydata/cost/calibration/__init__.py` | export the compatibility surface if package exports require it |
| Verify only | `src/worldenergydata/cost/calibration/cost_predictor.py` | ensure predictor behavior remains compatible with the adapter |
| Verify only | `src/worldenergydata/bsee/analysis/cost/cost_calibration.py` | reference only for proxy-rate concepts; do not make it the new public surface |
| Modify minimally if needed | `tests/unit/cost/test_proxy_comparison.py` | only if assertions need truthful tightening after restoring the contract |
| Verify only | `tests/unit/cost/test_calibration_schema.py` | ensure adjacent sanction-layer boundary still passes |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_proxy_comparison_module_imports` | supported import path exists again | module import | success |
| `test_compare_returns_list` | compare surface remains callable | fitted predictor + public dataset | list result |
| `test_compare_returns_non_empty_list` | restored adapter produces substantive output | fitted predictor + public dataset | length > 0 |
| `test_all_results_are_proxy_comparison_result` | typed result contract is explicit | comparison output | all typed instances |
| `test_results_have_positive_proxy_rates` | proxy-rate semantics survive the restore | comparison output | all values > 0 |
| `test_results_have_positive_calibrated_rates` | calibrated-rate semantics survive the restore | comparison output | all values > 0 |
| `test_results_cover_multiple_regions` | restored adapter handles the sanctioned dataset’s supported region spread | comparison output | at least 3 supported normalized regions covered |
| `test_confidence_levels_present` | output classification remains bounded | comparison output | confidence values only in `{high, medium, low}` |
| `test_bias_pct_sign_convention` | positive/negative bias semantics remain stable | constructed result rows | positive means calibrated > proxy; negative means calibrated < proxy |
| `test_bias_pct_calculated` | bias formula remains stable | comparison output | `bias_pct == ((calibrated_rate_usd_day - proxy_rate_usd_day) / proxy_rate_usd_day) * 100` |
| `test_compare_calibrated_to_proxy_trains_unfitted_predictor` | convenience path still works | unfitted predictor | non-empty results |
| `test_function_results_have_required_fields` | convenience path preserves the expected public fields | function output | exactly `region`, `water_depth_band`, `activity_type`, `proxy_rate_usd_day`, `calibrated_rate_usd_day`, `bias_pct`, `n_data_points`, `rmse_usd_mm`, `confidence` |
| `test_unsupported_region_is_skipped_without_failure` | unsupported sanctioned buckets do not break the adapter | rows mapped to unsupported proxy buckets | safely skipped |
| `test_calibration_schema_boundary_unchanged` | adjacent sanction schema remains unaffected | current schema tests | pass |

---

## Acceptance Criteria

- [ ] `tests/unit/cost/test_proxy_comparison.py` no longer fails at import/collection on current `main`
- [ ] `worldenergydata.cost.calibration.proxy_comparison` is restored as the supported compatibility import path for this regression boundary
- [ ] The restored module preserves the concrete public compatibility contract:
  - `ProxyComparisonResult(region, water_depth_band, activity_type, proxy_rate_usd_day, calibrated_rate_usd_day, bias_pct, n_data_points, rmse_usd_mm, confidence)`
  - `ProxyRateComparison(predictor=...)`
  - `compare_calibrated_to_proxy(...)`
- [ ] The adapter uses the fixed sanctioned-region to proxy-key mapping defined in this plan and does not invent a second proxy-rate source
- [ ] Targeted proxy-comparison tests cover non-empty output, positive rates, at least 3 supported normalized regions, exact required fields, unfitted-predictor support, unsupported-region skip behavior, and explicit bias semantics
- [ ] `tests/unit/cost/test_proxy_comparison.py` is not weakened or retargeted away from the restored import path as part of the fix
- [ ] Adjacent sanction-layer regression checks still pass

---

## Risks and Open Questions

- The adapter strategy is fixed in this plan: restore the compatibility module and do not retarget the test as the primary fix path.
- If hidden callers rely on the old import path, restoring a thin compatibility wrapper remains the preferred approach and is aligned with this plan’s chosen strategy.
- Need to verify whether CI failures on current PRs are baseline repo noise versus regressions specific to this boundary before using CI as the primary acceptance signal.
- `Middle East` currently maps to an unsupported proxy bucket in v1 and is intentionally skipped until a supported proxy-rate bucket exists.

---

## Complexity: T2

**T2** — bounded regression-boundary repair with a narrow surface-area decision, provided the issue stays focused on restoring/truthfully retargeting the missing proxy-comparison contract rather than redesigning calibration architecture.
