# Code Review — worldenergydata #716 Norway Sodir Reference Chain

- **Reviewer:** Codex inline adversarial review
- **Date:** 2026-07-04
- **Scope:** local diff for issue #716
- **Verdict:** APPROVE

## Checks

- Reviewed `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py`.
- Reviewed `packages/worldenergydata-sodir/src/worldenergydata/sodir/field_concept.py`.
- Reviewed `packages/worldenergydata-sodir/src/worldenergydata/sodir/reference_chain.py`.
- Reviewed new tests under `tests/unit/production/unified/` and `tests/unit/sodir/`.
- Compared implementation against the approved #716 narrowed slice: loader-backed adapter, FieldConcept mapping, recommendation, finite labeled pre-tax plumbing metrics.

## Findings

### Finding 1 — Compatibility fallback vs. "mock gone" wording

**Initial risk:** the approved issue text says "mock gone", but the existing unified-production tests depend on `SodirAdapter()` returning non-empty synthetic benchmark data. Removing the fallback would create broad unrelated churn in `tests/unit/production/unified/test_adapters.py`, `test_unified_client.py`, and cross-basin tests.

**Resolution:** the implementation makes the direct SODIR path explicit and fixture-backed when a `MonthlyProductionLoader`-compatible loader is supplied, while preserving the no-loader synthetic fallback. The plan artifact was patched to state this compatibility boundary. The #716 tests assert the direct loader path uses `source="sodir"` and the existing fallback remains isolated to no-loader behavior.

**Status:** resolved.

### Finding 2 — Water injection must not become produced water

**Risk:** `MonthlyProductionLoader` has `water_injected_sm3`, but FDAS requires `water_bbl`; mapping injection to produced water would contaminate economics inputs.

**Resolution:** `SodirAdapter._loader_to_standard_columns` sets `water_bbl` to `NaN`, drops `water_injected_sm3`, and tests assert this behavior.

**Status:** resolved.

### Finding 3 — Pre-tax Norway economics could be misread as an investment metric

**Risk:** Norway's fiscal regime is not represented in this chain slice; a pre-tax result could overstate investor value.

**Resolution:** `run_norway_reference_chain` returns `economics_label="chain_plumbing_pre_tax"` and only aggregate plumbing metrics. No after-tax NPV headline is emitted.

**Status:** resolved.

## Verification Evidence

- `PYTHONPATH=src:packages/worldenergydata-core/src:packages/worldenergydata-production/src:packages/worldenergydata-fdas/src:packages/worldenergydata-sodir/src /usr/bin/python3 -m pytest tests/unit/production/unified/test_adapters.py tests/unit/production/unified/test_unified_client.py tests/unit/production/unified/test_router.py tests/unit/fdas/adapters/test_contract.py tests/unit/fdas/adapters/test_field_concept_normalizer.py tests/unit/fdas/adapters/test_conformance.py tests/unit/sodir/test_norway_716.py tests/unit/sodir/test_norway_reference_chain.py tests/unit/production/unified/test_sodir_adapter_loader.py --noconftest -o addopts="" -q` -> 161 passed.
- `black --check`, `isort --check-only`, `flake8`, and `ruff check` passed on touched Python files.
- `git diff --check` passed.
- `scripts/legal/legal-sanity-scan.sh` passed.
