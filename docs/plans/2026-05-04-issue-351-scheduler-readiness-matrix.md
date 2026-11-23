# Plan: Issue #351 — Scheduler source refresh runtime readiness matrix

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/351
**Status:** plan-review
**Tier:** T2 (audit script + report, no scheduler code changes)
**Related:** #266–#273 (individual source fixes), #360 (scheduler health)

## Context
Several scheduler jobs are missing, broken, or unverified. Before overnight data
refresh runs, this issue produces a runtime-readiness matrix separating repo defects
from host/API/credential blockers.

## Plan

### Task 1 — Inventory all scheduler-relevant source configurations
Files to read:
- `config/scheduler/scheduler_config.yml`
- `src/worldenergydata/scheduler/` — job implementations
- `scripts/*refresh*.py`, `scripts/*sync*.py`
- `Makefile` — refresh targets

### Task 2 — Classify each source job
For each of the 7 wired jobs + 4 unwired sources, record:
| Field | Values |
|-------|--------|
| `config_present` | yes/no |
| `endpoint_known` | yes/no/unknown |
| `credentials_required` | none/env_var/file |
| `output_dir_wired` | yes/no |
| `dry_run_available` | yes/no |
| `safe_overnight_action` | audit/probe/sample/full/blocked |

### Task 3 — Write `docs/reports/scheduler-readiness-matrix-YYYY-MM-DD.md`
Table per source with the classification. Include recommended overnight actions:
- `bsee`: full refresh (auth not required)
- `sodir`: endpoint probe → sample fetch
- `eia_us`: blocked until #266 (credential wiring)
- etc.

### Task 4 — Cross-reference open issues
For each `blocked` source, note which open issue (#266–#273) addresses it.

## Acceptance Criteria
- `docs/reports/scheduler-readiness-matrix-*.md` generated covering all 11 sources
- Every `blocked` entry cites the blocking issue
- No scheduler config files modified (audit only)
