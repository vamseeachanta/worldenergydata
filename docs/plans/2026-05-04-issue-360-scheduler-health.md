# Plan: Issue #360 — Verify and instrument scheduler refresh health

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/360
**Status:** plan-review
**Tier:** T2 (ops diagnosis + instrumentation)

## Context

Last known scheduler run: 2026-03-25. As of audit date 2026-05-01, all production
data sources are 37+ days stale. No scheduler run logs found under `data/scheduler/runs/*.json`.

## Plan

### Task 1 — Diagnose whether scheduler is running
```bash
# Check cron/systemd for scheduler job
crontab -l | grep scheduler
systemctl list-timers | grep scheduler
```
If not running: document root cause (cron disabled? service stopped? host migration?).

### Task 2 — Check scheduler run log directory
```bash
ls -la data/scheduler/runs/ 2>/dev/null || echo "no runs dir"
find data/scheduler/ -name "*.json" -newer data/catalog.yaml 2>/dev/null | head -10
```
If logs exist but are stale, check last entries for error patterns.

### Task 3 — Validate scheduler config integrity
```bash
uv run python -c "
import yaml
with open('config/scheduler/scheduler_config.yml') as f:
    cfg = yaml.safe_load(f)
print('Jobs:', [j['name'] for j in cfg.get('jobs', [])])
"
```
Confirm all 7 wired jobs (bsee, sodir, ukcs, brazil_anp, eia_us, metocean, lng_terminals) are in config.

### Task 4 — Add `data/scheduler/runs/` freshness check to drift tests
In `tests/unit/cli/test_capability_drift.py` (or a new test file), add:
```python
def test_scheduler_has_recent_run_log():
    """Fail loudly if no scheduler run recorded in past 14 days."""
    runs_dir = _REPO / "data" / "scheduler" / "runs"
    if not runs_dir.exists():
        pytest.skip("scheduler runs dir absent — ops issue, not test failure")
    ...
```
This test should be marked `@pytest.mark.ops` and skipped in CI if `CI=true`.

### Task 5 — Produce postmortem note
Write `docs/ops/2026-05-04-scheduler-staleness-postmortem.md` with:
- Root cause
- Restart steps taken
- Monitoring instrument added (Task 4)

## Acceptance Criteria
- Root cause of 37-day staleness documented
- Scheduler either restarted (or deliberate decision to leave paused recorded)
- Drift test or freshness check added to catch future silences
