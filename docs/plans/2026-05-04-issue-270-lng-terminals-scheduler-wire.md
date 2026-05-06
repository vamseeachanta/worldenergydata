# Plan: Issue #270 — Wire lng_terminals_refresh into scheduler config

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/270
**Status:** plan-review
**Tier:** T1 (single config addition)
**Note:** #354 already corrected `module-manifest.yaml` to `in_scheduler: true` for lng_terminals.
          This plan wires the actual scheduler config entry.

## Root Cause
`src/worldenergydata/scheduler/jobs/lng_terminals_refresh.py` exists but
`config/scheduler/scheduler_config.yml` has no `lng_terminals_refresh` entry.

## Plan

### Task 1 — Read existing config structure
```bash
cat config/scheduler/scheduler_config.yml
```
Find the pattern used by existing jobs (e.g. `bsee_refresh`, `metocean_refresh`).

### Task 2 — Add entry to scheduler_config.yml
```yaml
  - name: lng_terminals_refresh
    enabled: true
    schedule: "0 6 * * 1"  # Weekly, Monday 6am (monthly cadence adequate for reference data)
    output_dir: data/modules/lng_terminals
    config_file: config/lng_terminals.yml
```
Adapt cadence to match existing similar reference-data jobs.

### Task 3 — Verify job loads without error
```bash
uv run python -c "
from worldenergydata.scheduler.jobs.lng_terminals_refresh import LngTerminalsRefreshJob
print('LngTerminalsRefreshJob loaded OK')
"
```

### Task 4 — Add drift test assertion
`test_capability_drift.py::TestSchedulerIndexMatchesConfig::test_manifest_scheduler_matches_config`
already verifies this — confirm test passes after the config edit.

## Acceptance Criteria
- `lng_terminals_refresh` entry present in `scheduler_config.yml`
- All 7 drift tests still pass
