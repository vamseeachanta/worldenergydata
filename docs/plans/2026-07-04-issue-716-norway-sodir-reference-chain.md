# Plan — worldenergydata #716: Norway Sodir reference-chain slice

- **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/716 (child of epic #713)
- **Status:** approved 2026-07-04 via GitHub `status:plan-approved`
- **Complexity:** T2 | **Lane:** codex | **Depends on:** #714 ✅, #715 ✅
- **Execution mode:** single-lane implementation after discovery; validation can run in parallel.

## Resource Intelligence Summary

Norway is the reference pilot for the international field-development chain because SODIR/Norsk Petroleum provide both per-field monthly production and rich field metadata. Current repo state has the F1/F2 prerequisites merged:

- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py` still emits synthetic mock profiles by default; existing unified-production tests depend on that compatibility fallback.
- `packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py` already parses SODIR monthly rows to `field_name, year, month, oil_sm3, gas_sm3, ngl_sm3, condensate_sm3, water_injected_sm3, oil_bbl, gas_mcf`.
- `packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/contract.py` provides `to_fdas_production`, which hard-requires `water_bbl`.
- `packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/field_concept_normalizer.py` provides `FieldMetaMapping`, transform callables, and `to_field_concept`.
- `src/worldenergydata/field_development/recommendation.py` accepts sparse `FieldConcept` objects and returns deterministic ranked concepts.
- `packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py` can run a pre-tax cashflow plumbing pass, with a loud warning for missing drilling timelines.

Reproduction proof: `SodirAdapter.fetch` currently returns mock `source="sodir_mock"` rows and does not use `MonthlyProductionLoader`; the plan will replace that with a loader-backed transform and fixture-backed tests.

## Deliverable

1. Rewire `SodirAdapter.fetch` to use `MonthlyProductionLoader` with an injectable API client/loader for fixture-backed tests.
2. Add the explicit loader-output to unified `STANDARD_COLUMNS` transform:
   - `region="ncs"`
   - `source="sodir"`
   - `oil_bbl` and `gas_mcf` from loader converted columns
   - `condensate_bbl` from `condensate_sm3`
   - `water_bbl` set to `0.0` or `NaN`, never from `water_injected_sm3`
3. Add Norway `FieldMetaMapping` helpers consuming `FieldProcessor.process()` output keys, with `region="norway"`, `year_first_oil`, meters-preserved `water_depth_m`, and combined recoverable reserves `oil_mmbbl + gas_bcf / 6`.
4. Add a one-fixture-field chain runner:
   - `fetch → to_fdas_production → CashflowEngine`
   - `to_field_concept → recommend`
   - output labels pre-tax economics as chain plumbing, not an investment headline.

## Files to Change

- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py`
- New Norway chain helper module under an existing SODIR-facing package path selected during implementation.
- Focused unit tests under `tests/unit/production/unified/` and `tests/unit/sodir/`.
- `.planning/plan-approved/716.md`
- `docs/plans/README.md`

## TDD Test List

- Loader transform pins every `STANDARD_COLUMNS` field, including `water_bbl` not coming from `water_injected_sm3` and `condensate_bbl` converted from Sm3.
- `SodirAdapter.fetch` with a fixture loader returns valid unified rows for a requested field/date range and `to_fdas_production` accepts them.
- Norway FieldMetaMapping consumes processed field keys and builds a valid `FieldConcept` with `region="norway"`, `water_depth_m`, `year_first_oil`, and combined recoverable reserves.
- Sparse Norway `FieldConcept` produces a non-empty deterministic `recommend()` ranking.
- One-field Norway chain returns finite pre-tax metrics labeled `chain_plumbing_pre_tax`.

## Acceptance Criteria

- `SodirAdapter` no longer uses synthetic mock profiles when a SODIR monthly loader is supplied; the no-loader synthetic fallback remains compatibility-only for existing unified-production tests.
- FDAS production normalization succeeds from fixture-backed SODIR monthly rows.
- Norway FieldConcept mapping is the first real F2 `to_field_concept` consumer.
- Concept screen returns deterministic ranked concepts.
- Cashflow output returns finite pre-tax metrics and is explicitly labeled as chain plumbing.
- No published Norway NPV headline; after-tax fiscal headline remains deferred to follow-on #736.
- Follow-ons are filed/commented for refresh-job monthly extension, Norway HTML report, and after-tax fiscal headline if not already represented.
- Focused tests, lint, diff check, legal scan, and code-review artifact are clean before PR.

## Risks

- Water production vs injection confusion: fail closed by never mapping `water_injected_sm3` to `water_bbl`.
- Sparse concept metadata can produce coarse recommendations; acceptance is deterministic ranked output, not field-accurate concept selection.
- Pre-tax FDAS output is not a Norway investment metric; label it as plumbing only.
