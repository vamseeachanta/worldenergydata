# Plan: Issue #266 — Operationalize EIA scheduler job

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/266
**Status:** plan-review
**Tier:** T2 (credential wiring + config normalization)
**Prerequisite:** #271 (output_dir wiring)

## Current State
- Job code exists, unit tests pass
- Runtime fails with `EIA_API_KEY not set`
- `output_dir: data/eia` — needs normalization to `data/modules/eia_us`

## Plan

### Task 1 — Normalize output_dir in config
Change `output_dir: data/eia` to `output_dir: data/modules/eia_us` in `scheduler_config.yml`.

### Task 2 — Document EIA_API_KEY credential requirement
In `docs/ops/credentials.md` (create if absent), add:
```markdown
### EIA US Module
- Env var: `EIA_API_KEY`
- Registration: https://www.eia.gov/opendata/
- Free tier: yes, 5,000 req/hour
```

### Task 3 — Add graceful credential-absent handling
In the EIA job implementation, at startup:
```python
if not os.environ.get("EIA_API_KEY"):
    logger.warning("EIA_API_KEY not set — skipping eia_us_refresh")
    return JobResult(status="skipped", records=0, reason="credential_absent")
```
This prevents the scheduler from crashing when the key isn't present.

### Task 4 — Verify with credentials
When `EIA_API_KEY` is available:
```bash
uv run python -m worldenergydata.scheduler run-job eia_us_refresh --dry-run
```

## Acceptance Criteria
- `output_dir` normalized to `data/modules/eia_us`
- Job exits gracefully with `skipped` status when `EIA_API_KEY` not set
- Credential documentation exists
