# Codex Inline Code Review - Issue #732

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/732
**Branch:** `feature/issue-732-texas-pressure-screen`
**Reviewer:** Codex inline adversarial review
**Date:** 2026-07-03
**Verdict:** APPROVE AFTER FIXES

## Findings

1. **MAJOR - Same-year Texas G-1/G-10 duplicates were selected by input order,
   not by #709's source earliest-observation flag.**

   The first implementation normalized Texas rows and then reused the existing
   `earliest_per_well()` sort of `well_key, test_year`. This was insufficient
   for Texas #709 because an API14 can have both G-1 Field Data and G-10
   shut-in WHP observations in the same test year, with different depth
   denominators. In live output, that could choose the G-1 row even when #709
   had marked the G-10 row as the earliest usable observation for that API14.

   **Fix:** Added `screen_observation_priority`, populated it from
   `is_earliest_observation_for_well` for Texas rows, and changed
   `earliest_per_well()` to sort by `well_key`, `test_year`, and
   `screen_observation_priority`. Added
   `test_earliest_per_well_uses_source_priority_for_same_year_ties`.

2. **MINOR - Report table initially used pre-fix Briscoe Ranch gradients.**

   After the priority fix, the live ranked-field parquet changed Briscoe Ranch
   median estimated gradient from 0.0918 to 0.1361 psi/ft.

   **Fix:** Reran the live `/mnt/ace` screen and updated the report table and
   narrative to match the regenerated parquet.

3. **MINOR - Markdown caveat indentation drifted during report rewrite.**

   **Fix:** Restored normal two-space continuation indentation.

## Verification Evidence

- RED test observed before fix:
  - `test_earliest_per_well_uses_source_priority_for_same_year_ties` failed by
    selecting `reference_depth_ft=15150.5` instead of `7394.0`.
- Focused tests after fixes:
  - `PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest tests/unit/analysis/test_underpressured_observations.py tests/unit/analysis/test_underpressured_screen.py -q`
  - Result: 23 passed.
- Lint/format:
  - `uv run --no-sync ruff check ...`
  - `uv run --no-sync ruff format --check ...`
  - Result: passed.
- Live screen:
  - `PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m worldenergydata.analysis.underpressured_screen.screen --config config/underpressured_screen.yml`
  - Result: validation gate passed, Texas participation gate passed, 10,128
    wells screened, state counts `KS=10103`, `TX=25`.
- Legal scan:
  - `scripts/legal/legal-sanity-scan.sh`
  - Result: PASS.

## Residual Risk

- Texas #709 remains a narrow daily completion-packet sample, not a full Texas
  historical pressure archive. The implementation intentionally uses a Texas
  participation gate rather than a West Panhandle analog recovery gate.
- Texas WHP gradients remain screening-only. The docs and summary preserve that
  caveat.
