# Plan: Issue #350 — Data completeness and freshness scorecard

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/350
**Status:** plan-review
**Tier:** T2 (audit script + output docs)
**Related:** #354 (manifest schema, DONE), #349 (capability inventory)

## Context
`data/catalog.yaml` covers 12 modules / 44 datasets. `MODULE_INDEX.md` advertises 27 modules.
Several catalog entries appear sample-sized or empty. The manifest `catalog_status` field
(added in #354) is the authoritative freshness signal per module.

## Plan

### Task 1 — Write `scripts/audit/data_freshness_scorecard.py`
Reads:
- `module-manifest.yaml` — `catalog_status`, `in_scheduler`, `public_cli` per module
- `data/catalog.yaml` — record counts, last refresh timestamps
- `data/modules/*/` metadata files — for actual on-disk state

Outputs `docs/reports/data-freshness-scorecard-YYYY-MM-DD.md` with:
```markdown
| Module | catalog_status | Records | Last Refresh | Scheduler | Notes |
```
One row per module. Marks modules as: `✅ full`, `🟡 sample`, `🔴 empty`, `⏳ scheduled`

### Task 2 — Run and review output
```bash
python3 scripts/audit/data_freshness_scorecard.py
```
Review the generated scorecard for accuracy. Correct any `catalog_status` mismatches.

### Task 3 — Emit machine-readable JSON sidecar
`data/freshness-scorecard.json` — module-keyed dict with score metadata.
(Consumed by #364 capability matrix.)

### Task 4 — Add to CI (optional)
Document that `scripts/audit/data_freshness_scorecard.py --check` can be run in CI
to fail if more than 3 modules have `catalog_status: unknown`.

## Acceptance Criteria
- `docs/reports/data-freshness-scorecard-*.md` generated with all 27 modules
- `data/freshness-scorecard.json` is valid JSON
- Script is idempotent
