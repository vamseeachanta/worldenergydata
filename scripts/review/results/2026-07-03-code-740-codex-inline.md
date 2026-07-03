# Code Review: Issue #740 - Oklahoma OCC completion pressures

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/740
**Mode:** Codex inline adversarial review
**Date:** 2026-07-03
**Scope reviewed:**

- `src/worldenergydata/modules/state_regulators/oklahoma_occ/`
- `src/worldenergydata/analysis/underpressured_screen/`
- `config/oklahoma_occ.yml`
- `config/underpressured_screen.yml`
- focused unit tests
- onshore source catalog and screen report docs

## Routing Note

The runtime exposed subagent tools, but their tool contract says not to spawn
subagents unless the user explicitly asks for subagents/delegation/parallel
agent work. No such explicit request was present in this closeout turn, so this
review is an inline defect-hunting review rather than a dispatched multi-agent
review.

## Findings

### R1 - Fixed: XLSX workbook handle could remain open on empty/error paths

`_read_selected_columns()` originally called `workbook.close()` only after the
normal row-iteration path. An empty workbook or exception while iterating rows
could skip close and leak the file handle during large direct-source refreshes.

Resolution: wrapped selected-column reading in `try/finally` so
`workbook.close()` always runs after `load_workbook()`.

## Post-Fix Review Result

No open blocking findings remain in the reviewed diff.

Residual risks:

- OCC workbook schema drift is controlled by fail-closed required-column
  validation, but semantic drift in optional columns still requires source
  review.
- `WHP_flowing_tubing` remains a screening-only fallback pressure. It is now
  treated consistently as a surface wellhead pressure, but it is not measured
  BHP and should not be presented as virgin pressure.
- Form 1016 back-pressure/deliverability tests and Oklahoma Tax Commission
  production data remain outside this issue.

## Verification Evidence

- Focused tests: `35 passed` with `--no-cov`.
- Ruff check: pass.
- Ruff format check: pass.
- Direct OCC ingest: pass; workbook SHA256
  `6d68d41320a6fcefd0b9973d544cf1c836de4c43a3cdeca0c9f58e74c2757e1f`.
- OCC curated invariant check: 108,518 rows, 19,972 wells, test years
  2010-2026.
- Multi-state pressure screen: pass; 30,100 wells screened; validation and
  participation gates passed.
- Legal scan: `legal-sanity-scan: PASS`.
