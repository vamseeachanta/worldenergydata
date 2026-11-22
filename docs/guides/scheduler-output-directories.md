# Scheduler output directories

Scheduled refreshes receive a resolved `output_dir` before the adapter runs.
Payloads, freshness metadata and scheduler manifests therefore share a root,
including when the scheduler starts from a different working directory.
Successful runs retain timestamped payload copies without changing the stable
filenames used by incremental ingestion and existing consumers.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Define shared output routing and retained run copies for issue #271. |

## Path selection

| Input | Destination |
| --- | --- |
| Absolute `output_dir` | The supplied directory, including an external volume |
| Relative `data/...` and `WORLDENERGYDATA_DATA_DIR` | The data-root override followed by the path after `data/` |
| Relative `data/...` and only `WED_DATA_ROOT` | The existing data-root override followed by the path after `data/` |
| Other relative `output_dir` | Relative to the configuration root |
| Omitted `output_dir` | `data/modules/{source}` using the same rules |

For `config/scheduler/scheduler_config.yml`, the configuration root is the
repository root. A standalone configuration uses its containing directory.
The working directory does not affect scheduled writes. A relative data-root
override also resolves against the configuration root. The new environment
name takes precedence when both names are set. Direct adapter calls retain
their existing explicit-output safeguards; use `DataScheduler` for conventions
and timestamped retention.

The default source is the job name without `_refresh`; `eia_us_refresh` uses
`eia`. Every shipped job configuration already declares `output_dir`. Explicit
legacy destinations, including the Spain CORES cache, remain supported. Empty,
null and non-path configuration values are rejected before execution.

```yaml
jobs:
  - name: sodir_refresh
    output_dir: data/modules/sodir
```

With `WORLDENERGYDATA_DATA_DIR` set to an external data directory, this writes
below its `modules/sodir` child. To choose a destination independently of either
environment variable, set `output_dir` to an absolute path.

## Retained outputs

On success, the scheduler copies the live payload into
`output_dir/runs/<UTC timestamp>-<unique suffix>Z/` and writes a run manifest.
It then maintains `output_dir/manifest.json` for existing health consumers.
Previous run directories and the previous health manifest are excluded from
the copy. Refresh metadata counts only current files. Metocean archive refreshes
honor `output_dir`, with `data_root` retained for direct legacy calls.

Failed, skipped and disabled runs do not create successful run snapshots.
A copy failure makes the scheduler result fail without advancing its successful
health manifest. An incomplete run directory may remain without a manifest.
Payload symlinks and a redirected `runs` directory are rejected.

Each successful execution copies the complete current payload, including raw
caches. Retention uses additional disk space; no automatic pruning is performed.
Copies require exclusive access to the output directory during the refresh.
This does not change source authentication, endpoint contracts or adapter
readiness. The disabled LNG adapter still reports skipped. Separate Spain
fixture exports remain controlled by `fixture_output_dir`.

## Worked example

Run the following in an environment with the scheduler installed, using a
scratch destination selected by the caller:

```bash
python examples/scheduler/output_dir_example.py "$TMPDIR/output-example"
```

Inputs are the two synthetic observations `first` and `second`. The example
writes their CSV through the scheduler, then compares the retained CSV bytes
with the live file. Independent hand count: `first` plus `second` is two records.
The answer is:

```json
{"records_updated": 2, "snapshot_matches_live": true, "status": "success"}
```

The example makes no upstream requests. Expected path cases in
`tests/unit/scheduler/test_output_paths.py` are independent concatenations of
the selected root, `modules` and the source name. No engineering equations,
coefficients or acceptance limits enter this filesystem contract.

The requirements and naming convention come from issue #271 and
`docs/plans/2026-05-04-issue-271-scheduler-output-dir.md`. Linked issues #264,
#266, #267 and #273 describe source-readiness work outside this path contract.
