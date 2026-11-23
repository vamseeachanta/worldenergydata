# Plan: Issue #269 — Implement SODIR, Brazil ANP, and UKCS adapters

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/269
**Status:** plan-review
**Tier:** T3 (3 new adapter implementations)
**Related:** #273 (SODIR endpoint fix — do that first)
**Prerequisite:** #271 (output_dir wiring)

## Plan

### Task 1 — SODIR adapter (depends on #273 endpoint fix)
`src/worldenergydata/scheduler/jobs/sodir_refresh.py`:
- Read current stub/broken state from #273 investigation
- Wire real `factpages.sodir.no` API calls
- Key endpoint: `/api/wellbore/GetPageData` or REST equivalent
- Output: `data/modules/sodir/wellbore_YYYYMMDD.json`

### Task 2 — Brazil ANP adapter
`src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py`:
- Identify current ANP data portal URL: `https://www.gov.br/anp/` (public bulk downloads)
- Download CSV/XLS from production bulletin
- Parse and write to `data/modules/brazil_anp/production_YYYYMMDD.csv`
- Monthly cadence — one bulk download per run

### Task 3 — UKCS adapter
`src/worldenergydata/scheduler/jobs/ukcs_refresh.py`:
- Source: NSTA Open Data Portal (`https://www.nstauthority.co.uk/data-centre/`)
- Download production CSV from NSTA UK open data
- Write to `data/modules/ukcs/production_YYYYMMDD.csv`

### Task 4 — Unit tests (one per adapter)
For each: mock HTTP response with 10-record fixture, assert correct output path.

### Task 5 — Bounded live smoke test
```bash
for job in sodir_refresh brazil_anp_refresh ukcs_refresh; do
  uv run python -m worldenergydata.scheduler run-job $job \
    --config config/scheduler/scheduler_config.yml --max-records 10
done
```

## Acceptance Criteria
- All 3 jobs complete without stub "records=0" return
- Data files written to `data/modules/{source}/`
- Unit tests mock HTTP and pass
