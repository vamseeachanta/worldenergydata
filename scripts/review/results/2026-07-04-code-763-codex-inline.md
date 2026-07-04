# Code Review — Issue #763 Spain CORES Reference Chain

- **Reviewer:** Codex inline
- **Date:** 2026-07-04
- **Verdict:** APPROVE after inline fixes
- **Scope:** `worldenergydata-spain` member, CORES loader/provenance fixture, unified `SpainCoresAdapter`, Spain FieldConcept/reference-chain runner, registry tests.

## Findings Checked

### R1 — MAJOR: production adapter could not consume separate oil/gas product frames

CORES source parsing emits product-specific loader rows (`oil_bbl` from tonnes and `gas_mcf` from GWh). The first adapter implementation only accepted a combined loader frame, which would block a direct live-loader path.

**Fix:** added a RED test for `load_oil_production()` + `load_gas_production()` and implemented `_merge_product_frames()` with outer merge on `field_name/year/month`. Missing oil/gas product rows normalize to `0.0`; water and condensate remain `NaN`.

### R2 — MAJOR: scalar `region` assignment produced `NaN`

The first implementation assigned scalar `region` to an empty DataFrame before indexed columns, so pandas filled `region` with `NaN`.

**Fix:** field-indexed columns are assigned before scalar `region`. Regression covered by adapter schema and fixture-backed tests.

### R3 — MAJOR: onshore Ayoluengo must not fall through to subsea CAPEX

Norway/UKCS fallback logic maps unknown water depth to `subsea15`; applying that to onshore Ayoluengo would create a false host CAPEX line.

**Fix:** Spain field metadata maps onshore sparse fields to `water_depth_m=0.0`; the reference chain forces `dev_system="dry"` for onshore metadata and returns `onshore_model_mismatch: true` plus `host_capex_usd == 0.0`.

### R4 — MINOR: new workspace member required packaging/docs registration

`packages/*` makes a member directory without `pyproject.toml` break `uv run`.

**Fix:** added `packages/worldenergydata-spain/pyproject.toml`, root dependency/source/exclude entries, `uv.lock`, and docs source path.

## Verification

- RED: separate product-frame test failed with `TypeError` before adapter merge support.
- Focused: `13 passed` for Spain loader/reference-chain + Spain adapter tests.
- Adjacent: `233 passed` for `tests/unit/spain`, `tests/unit/production/unified`, `tests/unit/fdas/adapters`.
- Formatting/lint: Black check, isort check, flake8 on touched Python paths passed.
- Hygiene: `git diff --check` passed.
- Legal: `scripts/legal/legal-sanity-scan.sh --diff-only` passed.

## Residual Risk

- Live CORES download and scheduler refresh are deferred follow-ons.
- Oil tonnes-to-bbl uses the approved approximate `7.33 bbl/tonne`; per-field density/API remains a follow-on.
- Gas production is converted to Mcf, but FDAS cashflow still models oil revenue only; gas-revenue economics remain a follow-on.
