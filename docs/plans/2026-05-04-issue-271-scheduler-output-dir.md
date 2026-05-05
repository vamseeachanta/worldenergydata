# Plan: Issue #271 — Wire output_dir into all scheduler jobs

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/271
**Status:** plan-review
**Tier:** T2 (cross-cutting config + base class fix)

## Problem
No scheduler job has `output_dir` wired. Jobs don't know where to write output files.

## Plan

### Task 1 — Audit base job class
Read `src/worldenergydata/scheduler/base.py` (or equivalent).
Check if there is an `output_dir` parameter in the job base class or config schema.

### Task 2 — Add output_dir to base job config schema
If not present, add to the base job dataclass/config:
```python
output_dir: str = "data/modules/{source}"  # Default convention
```
Support env var override: `WORLDENERGYDATA_DATA_DIR / modules / {source_id}`.

### Task 3 — Update all 7 wired job configs in scheduler_config.yml
Add `output_dir` to each job entry:
```yaml
  - name: bsee_refresh
    output_dir: data/modules/bsee
  ...
```

### Task 4 — Update job implementations
For each job implementation in `src/worldenergydata/scheduler/jobs/`:
- Accept `output_dir` from config
- Write output timestamped files to `output_dir`

### Task 5 — Smoke test
```bash
uv run python -c "
import yaml
with open('config/scheduler/scheduler_config.yml') as f:
    cfg = yaml.safe_load(f)
missing = [j['name'] for j in cfg['jobs'] if 'output_dir' not in j]
assert not missing, f'Jobs missing output_dir: {missing}'
print('All jobs have output_dir')
"
```

## Acceptance Criteria
- All 7 scheduled jobs have `output_dir` in their config entries
- Base job class reads `output_dir` from config and uses it for writes
- `data/modules/` directory structure matches the convention
