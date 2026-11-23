# Issue #353 scheduler timeout validation

- Date: 2026-05-11
- Branch: `codex/burn-20260511-worldenergydata-bundle`
- Mode: bounded validation only; no refresh jobs or external data downloads

## Result

The repo-owned scheduler and BSEE refresh no-op paths complete quickly when the
already-synced environment is used with `uv run --no-sync`. The remaining
timeout is isolated to plain `uv run` environment synchronization/compile work,
not to scheduler or refresh Python import side effects.

## Evidence

| Command | Result | Notes |
|---|---:|---|
| `timeout 30 uv run python -c "print('hello')"` | `EXIT:124` | Timed out before user Python output while uv was checking/syncing the environment. |
| `timeout 10 uv run --no-sync python -c "print('hello')"` | `EXIT:0` | Printed `hello`. |
| `PYTHONPATH='src:../assetutilities/src' timeout 15 uv run --no-sync python -m worldenergydata.scheduler` | `EXIT:0` | Printed scheduler usage. |
| `PYTHONPATH='src:../assetutilities/src' timeout 15 uv run --no-sync python -m worldenergydata.scheduler status --config config/scheduler/scheduler_config.yml` | `EXIT:0` | Registered all seven scheduler jobs and printed status JSON. |
| `PYTHONPATH='src:../assetutilities/src' timeout 15 uv run --no-sync python scripts/refresh_bsee_all.py --help` | `EXIT:0` | Printed argparse help. |
| `PYTHONPATH='src:../assetutilities/src' uv run --no-sync python -m pytest --noconftest tests/unit/scheduler/test_scheduler_cli_startup.py tests/unit/bsee/test_refresh_bsee_cli_startup.py -q` | pass | `3 passed in 17.07s`. |
| `PYTHONPATH='src:../assetutilities/src' uv run --no-sync python -m pytest --noconftest tests/unit/scheduler/test_cli.py -q` | pass | `12 passed in 23.64s`. |

## Classification

- `uv run` branch: operational environment synchronization/compile latency.
  Fresh or partially synced bundles can exceed 30 seconds before running Python.
  Use `uv run --no-sync` after an explicit sync, or use the workspace `.venv`
  interpreter when available for scheduler readiness probes.
- Scheduler no-op/help branch: repo-owned lazy import coverage is present and
  passing; no refresh job adapter import is required for the usage path.
- `refresh_bsee_all.py --help` branch: repo-owned lazy import coverage is
  present and passing; help exits before `pandas`, `requests`, or the BSEE URL
  registry are imported.

## Follow-up

The original `<10s` `uv run python -c "print('hello')"` acceptance criterion is
not met in this fresh bundle because `uv run` still performs environment work.
The bounded operational workaround is `uv run --no-sync` after sync has been
performed, or a direct `.venv/bin/python` path in workspaces that already have a
complete virtual environment.
