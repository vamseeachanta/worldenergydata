# LNG scheduler readiness

Issue #458 permits disabling LNG refresh until an upstream adapter can write
accepted data. The shipped configuration already uses that option. LNG remains
disabled, and an accidental direct or enabled invocation now reports an explicit,
non-retryable failure. Existing data and success manifests are preserved.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-21 | Document disabled LNG refresh and failure reporting to prevent false freshness. |

## Inputs, method and expected results

The inputs are the job's `enabled` setting and any existing success manifest.
The method follows `DataScheduler.run_once`: disabled jobs stop before the retry
manager; enabled jobs execute the adapter; only successful results can update a
success manifest. LNG has no upstream refresh implementation, so it returns
`failure`, `retryable: false` and a message instructing maintainers to keep
`enabled: false`.

The expected zero updates are counted independently: no collection is performed,
so the collection of updated records is empty. One enabled invocation returns a
terminal failure, so the retry manager makes no further calls and performs no
backoff sleeps. These are control-flow expectations, with no engineering
coefficients, unit conversions or acceptance thresholds.

| Invocation | Result | Updated records | Success manifest | Default health report |
| --- | --- | --- | --- | --- |
| Disabled through scheduler | `skipped` | 0 | Preserved or absent | Excluded |
| Accidentally enabled through scheduler | `failure`, non-retryable | 0 | Preserved or absent | Included; missing evidence remains stale |
| Direct adapter call | `failure`, non-retryable | 0 | Preserved or absent | Determined by scheduler config |

Sources: issue #458 acceptance criteria (2026), the linked health requirements in
issue #360 (2026), and the repository implementations
[`scheduler.py`](../../packages/worldenergydata-scheduler/src/worldenergydata/scheduler/scheduler.py),
[`monitor.py`](../../packages/worldenergydata-scheduler/src/worldenergydata/scheduler/monitor.py),
and [`scheduler-health.sh`](../../scripts/cron/scheduler-health.sh).
The readiness regression tests import the concrete classes behind the default
registry and require every enabled adapter to have `implemented = True`.
Placeholder adapters must declare `implemented = False` and remain disabled.
This test checks declarations without executing source collectors.

## Worked example

Run this Python example in the installed workspace, with `TMPDIR` set to a
writable scratch directory. It creates isolated configurations and output
locations there. The repository configuration and datasets are unchanged.
JSON is used as YAML-compatible configuration input.

```python
import json
from pathlib import Path
from tempfile import mkdtemp

from worldenergydata.scheduler.cli import cmd_run_job

for enabled in (False, True):
    scratch = Path(mkdtemp(prefix="lng-readiness-"))
    output = scratch / "data" / "lng"
    config_path = scratch / "config" / "scheduler" / "config.yml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({
        "jobs": [{
            "name": "lng_terminals_refresh",
            "enabled": enabled,
            "interval": "weekly",
            "output_dir": str(output),
        }],
        "monitoring": {
            "log_dir": str(scratch / "logs"),
            "status_file": str(scratch / "status.json"),
        },
    }))
    result = cmd_run_job("lng_terminals_refresh", str(config_path))
    print(json.dumps({
        "enabled": enabled,
        "status": result.status,
        "records_updated": result.records_updated,
        "manifest_written": (output / "manifest.json").exists(),
    }))
```

Expected standard output, independently derived from the state transitions above:

```json
{"enabled": false, "status": "skipped", "records_updated": 0, "manifest_written": false}
{"enabled": true, "status": "failure", "records_updated": 0, "manifest_written": false}
```

The enabled case also records the failure and corrective message in the isolated
scheduler status file and execution log. The scheduler CLI currently reports
results through logging; automation should inspect `JobResult.status` or the
status file rather than infer success from the process exit code.

## Requirements before enabling LNG

A future adapter needs an accepted upstream endpoint and payload schema, source
citations and vintage, explicit empty/invalid-response handling, and output in
the configured data directory. Cached or curated records alone cannot establish
that an upstream refresh succeeded. Test successful collection through
`DataScheduler.run_once`, assert `manifest.json` contains `status: success`, and
run the health script against that manifest before enabling the shipped job.

Live upstream freshness and source vintage remain NOT_EVALUATED. No upstream
requests or new freshness claims are made by this change. See the
[source refresh acceptance criteria](source-refresh-acceptance-criteria.md) for
the distinction between source-data vintage and a scheduler success timestamp.
