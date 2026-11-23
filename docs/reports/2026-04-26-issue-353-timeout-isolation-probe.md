# Issue #353 bounded timeout isolation probe

Read-only diagnostic probe. No implementation changes.

## venv print

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'print('"'"'hello'"'"')'
```

- exit_code: 0
- duration_s: 0.06

```
hello
```

## uv print

```bash
uv run python -c 'print('"'"'hello'"'"')'
```

- TIMEOUT after 10s
- duration_s: 10.02

```

```

## import pandas

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import pandas; print("pandas ok")'
```

- exit_code: 0
- duration_s: 11.61

```
pandas ok
```

## import requests

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import requests; print("requests ok")'
```

- exit_code: 0
- duration_s: 1.68

```
requests ok
```

## import package

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import worldenergydata; print("wed ok")'
```

- exit_code: 0
- duration_s: 0.19

```
wed ok
```

## import scheduler package

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import worldenergydata.scheduler; print("scheduler package ok")'
```

- exit_code: 0
- duration_s: 14.06

```
scheduler package ok
```

## import scheduler config

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import worldenergydata.scheduler.config; print("config ok")'
```

- TIMEOUT after 15s
- duration_s: 15.04

```

```

## import scheduler scheduler

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import worldenergydata.scheduler.scheduler; print("scheduler class ok")'
```

- exit_code: 0
- duration_s: 13.84

```
scheduler class ok
```

## import scheduler cli

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import worldenergydata.scheduler.cli; print("cli ok")'
```

- exit_code: 0
- duration_s: 4.39

```
cli ok
```

## import BSEE job

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'import worldenergydata.scheduler.jobs.bsee_refresh; print("bsee job ok")'
```

- exit_code: 0
- duration_s: 15.83

```
bsee job ok
```

## import BSEEWebScraper

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper; print("scraper ok")'
```

- exit_code: 0
- duration_s: 4.12

```
scraper ok
```

## import common data_resolver

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -c 'from worldenergydata.common.data_resolver import get_module_data_safe; print(get_module_data_safe("bsee"))'
```

- exit_code: 0
- duration_s: 2.81

```
/mnt/local-analysis/workspace-hub/worldenergydata/data/modules/bsee
```

## scheduler module no args

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -m worldenergydata.scheduler
```

- exit_code: 0
- duration_s: 5.12

```
[stderr]
2026-04-27 02:39:44.516 | INFO     | worldenergydata.scheduler.cli:main:120 | Usage:
  python -m worldenergydata.scheduler start [--config PATH]
  python -m worldenergydata.scheduler stop [--config PATH]
  python -m worldenergydata.scheduler status [--config PATH]
  python -m worldenergydata.scheduler run-job <name> [--config PATH]

2026-04-26 21:39:44,516 INFO worldenergydata.scheduler.cli: Usage:
  python -m worldenergydata.scheduler start [--config PATH]
  python -m worldenergydata.scheduler stop [--config PATH]
  python -m worldenergydata.scheduler status [--config PATH]
  python -m worldenergydata.scheduler run-job <name> [--config PATH]
```

## scheduler status minimal

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python -m worldenergydata.scheduler status --config config/scheduler/scheduler_config.yml
```

- exit_code: 0
- duration_s: 12.05

```
[stderr]
2026-04-27 02:39:56.617 | INFO     | worldenergydata.scheduler.scheduler:register_job:81 | Registered job: bsee_refresh
2026-04-26 21:39:56,616 INFO worldenergydata.scheduler.scheduler: Registered job: bsee_refresh
2026-04-27 02:39:56.617 | INFO     | worldenergydata.scheduler.scheduler:register_job:81 | Registered job: sodir_refresh
2026-04-26 21:39:56,617 INFO worldenergydata.scheduler.scheduler: Registered job: sodir_refresh
2026-04-27 02:39:56.617 | INFO     | worldenergydata.scheduler.scheduler:register_job:81 | Registered job: eia_us_refresh
2026-04-26 21:39:56,617 INFO worldenergydata.scheduler.scheduler: Registered job: eia_us_refresh
2026-04-27 02:39:56.618 | INFO     | worldenergydata.scheduler.scheduler:register_job:81 | Registered job: brazil_anp_refresh
2026-04-26 21:39:56,618 INFO worldenergydata.scheduler.scheduler: Registered job: brazil_anp_refresh
2026-04-27 02:39:56.618 | INFO     | worldenergydata.scheduler.scheduler:register_job:81 | Registered job: ukcs_refresh
2026-04-26 21:39:56,618 INFO worldenergydata.scheduler.scheduler: Registered job: ukcs_refresh
2026-04-27 02:39:56.618 | INFO     | worldenergydata.scheduler.scheduler:register_job:81 | Registered job: metocean_refresh
2026-04-26 21:39:56,618 INFO worldenergydata.scheduler.scheduler: Registered job: metocean_refresh
2026-04-27 02:39:56.618 | INFO     | worldenergydata.scheduler.scheduler:register_job:81 | Registered job: lng_terminals_refresh
2026-04-26 21:39:56,618 INFO worldenergydata.scheduler.scheduler: Registered job: lng_terminals_refresh
2026-04-27 02:39:56.619 | INFO     | worldenergydata.scheduler.cli:main:149 | {
  "jobs": {
    "bsee_refresh": {
      "last_run": null,
      "last_result": null,
      "next_run": "next weekly at 02:00"
    },
    "sodir_refresh": {
      "last_run": null,
      "last_result": null,
      "next_run": "next daily at 03:00"
    },
    "eia_us_refresh": {
      "last_run": null,
      "last_result": null,
      "next_run": "next monthly at 04:00"
    },
    "brazil_anp_refresh": {
      "last_run": null,
      "last_result": null,
      "next_run": "next monthly at 05:00"
    },
    "ukcs_refresh": {
      "last_run": null,
      "last_result": null,
      "next_run": "next monthly at 06:00"
    },
    "metocean_refresh": {
      "last_run": null,
      "last_result": null,
      "next_run": "next daily at 01:00"
    },
    "lng_terminals_refresh": {
      "last_run": null,
      "last_result": null,
      "next_run": "next weekly at 07:00"
    }
  },
  "staleness": {
    "sodir_refresh": {
      "threshold_hours": 36.0,
      "is_stale": true,
      "hours_since_last_success": null
    },
    "bsee_refresh": {
      "threshold_hours": 240.0,
      "is_stale": true,
      "hours_since_last_success": null
    },
    "eia_us_refresh": {
      "threshold_hours": 1080.0,
      "is_stale": true,
      "hours_since_last_success": null
    }
  },
  "alerts": []
}
2026-04-26 21:39:56,619 INFO worldenergydata.scheduler.cli: {
 
...[truncated]
```

## refresh_bsee_all help

```bash
/mnt/local-analysis/workspace-hub/worldenergydata/.venv/bin/python scripts/refresh_bsee_all.py --help
```

- TIMEOUT after 20s
- duration_s: 20.03

```

```

