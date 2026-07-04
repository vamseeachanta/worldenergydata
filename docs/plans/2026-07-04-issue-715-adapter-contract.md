# Plan — worldenergydata #715: F2 — country adapter contract (FDAS bridge + FieldConcept normalizer + conformance)

- **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/715 (child of epic #713)
- **Status:** v2 (r1 adversarial review APPROVE-WITH-CHANGES, 2 blocking folded); **approved** 2026-07-04 (owner "yes defer work to a follow on"); implemented same day.
- **Complexity:** T2 | **Lane:** claude | **Depends on:** #714 ✅ (FDAS carve, merged).

## Reframe (verified)
A country-adapter contract already exists — `production/unified/adapters/base.py:AbstractProductionAdapter` with `STANDARD_COLUMNS` and 8 country implementations. So F2 is the **FDAS-facing bridge**, not new adapters: normalize unified output → FDAS production schema + a FieldConcept metadata normalizer + conformance.

## Deliverable (implemented)
1. `fdas/adapters/contract.py` — `FDAS_PRODUCTION_COLUMNS` + `to_fdas_production(unified_df)` (STANDARD_COLUMNS → FDAS monthly `YEAR_MONTH`/`MONTHLY_OIL_BBL`/…; fail-closed; typed-empty). Pure leaf (no `field_development` import). Pins `_BBL`/`_MCF` (resolves the pre-existing `bsee_adapter` `MONTHLY_*_VOLUME` split). `FdasInputs` bundle (production-only in v1).
2. `fdas/adapters/field_concept_normalizer.py` — `FieldMetaMapping` (per-field **transform callables**, validated vs `FieldConcept.model_fields`) + `reduce_concept_type` (subsea-tieback-wins, preserves subseaiq logic) + `dev_system_from_water_depth_m` (m→ft→classifier, vocab `{dry,subsea15,subsea20,unknown}`) + `to_field_concept` via `loader.load_concept`. Ported transforms: `fluid_from_reserve_type`, `year_from`, `number_from`.
3. `fdas/analysis/cashflow.py` — **empty-drilling-timeline honesty guard** (review B1): logs WARNING when `drilling_monthly` empty (silent-zero-CAPEX made loud); number unchanged.
4. Conformance suite (synthetic per-region fixtures) + parity guard (canonical `MONTHLY_OIL_BBL`) + honesty-guard test.

## Folded review findings (r1 APPROVE-WITH-CHANGES)
- **B1** — wells/drilling undeliverable via FieldConcept/STANDARD_COLUMNS (no per-well spud/API); silent-zero-CAPEX. → wells schema REMOVED from scope + honesty WARNING + **follow-on filed**.
- **B2** — subseaiq isn't a rename-map (fluid/year/concept-reduction logic). → `FieldMetaMapping` carries callables; `reduce_concept_type` dedicated.
- Minors: classifier vocab `{dry,subsea15,subsea20,unknown}` (not `default`); `bsee_adapter` `_VOLUME` is live public API → reconcile/rename follow-on (not delete); conformance uses synthetic fixtures (BSEE data not in CI) + documented live-fetch follow-on.

## Verification
- 31 tests green (`.venv/bin/python -m pytest tests/unit/fdas/adapters/ --noconftest -o addopts=""` → 31 passed): contract 11, normalizer 12 (B2 parity + ft/m boundaries), conformance 8 (5 country + metadata + parity guard + honesty guard).
- NOTE: `tests/conftest.py` waits on local BSEE data (`make data`) absent on a fresh worktree → run local via `--noconftest`; CI runs the full path.

## Follow-ons (to file)
1. Per-country FDAS **wells/drilling-timeline source** (STANDARD_COLUMNS can't carry per-well spud/API). Note: DataVic (AU) exposes per-well `spud_date`+`abswaterdepth` — a candidate.
2. Reconcile/rename `bsee_adapter` `MONTHLY_*_VOLUME` → `_BBL` (public API — coordinated, not silent delete).

## Remaining (this PR or follow-up)
Registration-checklist doc + test (Suite E), member README consumed-vs-declarative note, live-fetch conformance lane (skip-with-reason).
