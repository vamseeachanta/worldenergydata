# Plan: Issue #129 — BOEM/BSEE data refresh CLI script

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/129
**Status:** plan-review
**Tier:** T2 (CLI script for manual data refresh)

## Context
Users need a simple script to refresh BSEE/BOEM data without understanding the scheduler
internals. The Makefile has `make data` which calls `scripts/refresh_bsee_all.py`.

## Plan

### Task 1 — Check if scripts/refresh_bsee_all.py exists and works
```bash
uv run python scripts/refresh_bsee_all.py --help 2>&1 | head -10
```
If it works: this issue is mostly done. Document and close.

### Task 2 — If script is missing or broken: create/fix it
`scripts/refresh_bsee_all.py`:
- Download BSEE production CSV
- Download BSEE wellbore CSV
- Save to `data/raw/bsee/`
- Print progress and file sizes

### Task 3 — Add CLI entrypoint
In `src/worldenergydata/cli/commands/bsee.py`, ensure `bsee refresh` command calls the script.

### Task 4 — Document in README
Under "Data-required commands": `make data # or: uv run worldenergydata bsee refresh`

## Acceptance Criteria
- `uv run worldenergydata bsee refresh --help` exits 0
- `scripts/refresh_bsee_all.py` runs and downloads data
