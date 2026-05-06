# Plan: Issue #267 — Fix BSEE scheduler runtime download/extraction compatibility

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/267
**Status:** plan-review
**Tier:** T2 (response parsing fix for live BSEE format)

## Problem
BSEE scheduler job reaches endpoints, downloads payloads (`platform`, `pipeline_permit`
succeed), but archive extraction/parsing fails because format assumptions don't match
current BSEE responses.

## Plan

### Task 1 — Run live scheduler job in diagnostic mode
```bash
uv run python -m worldenergydata.scheduler run-job bsee_refresh \
  --config config/scheduler/scheduler_config.yml \
  --max-records 10 2>&1 | tail -40
```
Capture the exact exception and archive structure.

### Task 2 — Inspect downloaded archive
If the job downloads a zip/tar, examine the actual file structure:
```bash
python3 -c "
import zipfile, glob
for f in glob.glob('/tmp/bsee_*'):
    with zipfile.ZipFile(f) as z:
        print(z.namelist()[:10])
"
```

### Task 3 — Fix extraction logic
Update `src/worldenergydata/scheduler/jobs/bsee_refresh.py` extraction to match
current BSEE archive structure. Common changes:
- CSV delimiter (tab vs comma)
- Column name changes
- File naming pattern in archive

### Task 4 — Bounded smoke test
After fix:
```bash
uv run python -m worldenergydata.scheduler run-job bsee_refresh \
  --config config/scheduler/scheduler_config.yml \
  --max-records 100
```
Expect: 100 records written to `data/modules/bsee/`.

## Acceptance Criteria
- `bsee_refresh` completes without exception on a bounded fetch
- Records written to `data/modules/bsee/` with correct schema
