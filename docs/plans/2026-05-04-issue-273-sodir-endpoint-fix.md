# Plan: Issue #273 — Fix SODIR scheduler runtime endpoint contract

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/273
**Status:** plan-review
**Tier:** T2 (endpoint URL correction + response parsing fix)

## Problem
`sodir_refresh` job reaches SODIR endpoints but fails at runtime because configured
endpoint paths don't match the current SODIR factpages API.

## Plan

### Task 1 — Verify current SODIR API endpoints
```bash
curl -s "https://factpages.sodir.no/api/wellbore/GetPageData?culture=en&after=0" | head -200
```
Compare response structure to what the job parser expects.

### Task 2 — Read job implementation
`src/worldenergydata/scheduler/jobs/sodir_refresh.py` — identify hardcoded endpoint URLs
and response parsing logic.

### Task 3 — Fix endpoint URLs
Update to current SODIR factpages API paths. If the API structure changed, update the
response parser to match new field names/structure.

### Task 4 — Run a bounded sample fetch
```bash
uv run python -m worldenergydata.scheduler run-job sodir_refresh \
  --config config/scheduler/scheduler_config.yml \
  --max-records 50 --dry-run
```
Expect: ≥1 record fetched, no exception.

### Task 5 — Unit test with fixture response
Add a unit test that mocks the current SODIR API response structure and asserts the
job correctly parses it to the output schema.

## Acceptance Criteria
- `sodir_refresh` job completes without exception on a bounded fetch
- At least 1 record written to `data/modules/sodir/`
- Unit test covers the response parser
