# Plan: Issue #809 - Spain CORES scheduler refresh job

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/809
**Status:** plan-review
**Tier:** T2 (scheduler integration, direct-source refresh, fixture/provenance mode)
**Client:** N/A
**Project:** worldenergydata Spain CORES production lifecycle
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will use a single-lane TDD workflow because this slice will touch
the scheduler package, its job registry, scheduler configuration, and package
dependency metadata. Read-only review and verification can run independently,
but code writes will remain serialized to avoid scheduler registry conflicts.

Implementation will not begin until this plan is reviewed, pushed, moved to
`status:plan-review`, and explicitly approved by the user as
`status:plan-approved`.

### Issue and dependency status

| Issue | State | Role for this plan |
|---|---|---|
| [#763](https://github.com/vamseeachanta/worldenergydata/issues/763) | closed, `status:done` | Spain CORES parser, fixture, adapter, and reference chain |
| [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) | closed, `status:done` | Direct-source live CORES XLSX download lane this scheduler job will wrap |
| [#809](https://github.com/vamseeachanta/worldenergydata/issues/809) | open, unapproved | This scheduler job slice |
| [#810](https://github.com/vamseeachanta/worldenergydata/issues/810) | open | Spain CORES field-development report consumer |

### Reproduction proofs

N/A - [#809](https://github.com/vamseeachanta/worldenergydata/issues/809)
requests a new scheduler feature rather than alleging a failing test or runtime
regression.

Verification probes for current integration surfaces:

```bash
PYTHONPATH=packages/worldenergydata-spain/src:packages/worldenergydata-scheduler/src:packages/worldenergydata-core/src \
  python -c "from worldenergydata.spain.production.cores_live import CoresLiveProductionLoader, refresh_ayoluengo_fixture; from worldenergydata.scheduler.cli import _JOB_SPECS; print('imports ok'); print([name for name, _ in _JOB_SPECS])"
```

Output:

```text
imports ok
['bsee_refresh', 'hse_refresh', 'sodir_refresh', 'eia_us_refresh', 'brazil_anp_refresh', 'ukcs_refresh', 'metocean_refresh', 'lng_terminals_refresh']
```

Focused pytest was attempted through direct Python, but the local non-`uv`
environment lacks `plotly`, which is imported by `tests/conftest.py`:

```text
ModuleNotFoundError: No module named 'plotly'
```

`uv run` probes were interrupted after first-time workspace setup remained
quiet beyond the useful planning window. Implementation verification will use
serial `uv run` commands after the approval gate.

### Plan-state transition

The live GitHub issue labels will move to `status:plan-review` only after
review artifacts exist and the plan branch has been pushed. The label update
will include an evidence comment; labels will not be applied before pushed
artifacts exist.

### Current code surfaces this implementation will reuse

- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py`
  exposes `CoresLiveProductionLoader.refresh(force_refresh=False)`,
  `load_oil_production()`, `load_gas_production()`,
  `load_all_production()`, `metadata()`, and `refresh_ayoluengo_fixture(...)`.
- `packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py`
  exposes `CoresWorkbookSource`, official CORES workbook URLs, statistics page
  discovery, atomic raw workbook writes, and `metadata/cores_refresh_metadata.json`.
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/base.py`
  defines `AbstractJob`, `JobResult`, `write_refresh_metadata(...)`, and
  `write_success_manifest(...)`.
- `packages/worldenergydata-core/src/worldenergydata/common/data_resolver.py`
  defines `get_data_root_safe()`. The Spain scheduler job will use that helper
  for its default output directory because the [#806](https://github.com/vamseeachanta/worldenergydata/issues/806)
  CORES live lane writes under `data/spain/cores`, not
  `data/modules/spain/cores`.
- Scheduler live-refresh jobs such as
  `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py`
  and `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/ukcs_refresh.py`
  require an explicit `output_dir`, skip without network when it is missing,
  write raw and normalized outputs under that directory, and return `JobResult`.
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/cli.py`
  uses `_JOB_SPECS` plus `LazyRefreshJob` so concrete data-source jobs import
  only when status/start/run-job paths consume the registry.
- `packages/worldenergydata-scheduler/pyproject.toml` currently depends on
  source-domain members refreshed by scheduler jobs, but it does not list
  `worldenergydata-spain`. This implementation will add that dependency.

### Boundary decisions

- The scheduler job will wrap the [#806](https://github.com/vamseeachanta/worldenergydata/issues/806)
  live loader rather than duplicating CORES discovery, download, parsing, or
  normalization logic.
- The job will require an explicit `output_dir`, matching SODIR, UKCS, and
  Brazil ANP live-refresh safety behavior.
- Production code will not hardcode `/mnt/ace`; `config/scheduler/scheduler_config.yml`
  will use `data/spain/cores`, and operators can point a deployed config at
  `/mnt/ace/worldenergydata/data/spain/cores`.
- The job will write full raw, normalized, and source metadata under the
  configured output directory:

```text
<output_dir>/
  raw/
    crude-oil-production.xlsx
    gas-production.xlsx
  normalized/
    cores_oil_production.csv
    cores_gas_production.csv
    cores_all_production.csv
  metadata/
    cores_refresh_metadata.json
  _metadata.json
  manifest.json
```

- The repo default scheduler config will set `refresh_fixture: true` and
  `fixture_output_dir: packages/worldenergydata-spain/src/worldenergydata/spain/data/cores`
  because [#809](https://github.com/vamseeachanta/worldenergydata/issues/809)
  explicitly asks the scheduler job to refresh committed fixtures and
  `_metadata.json` provenance.
- Operators who run unattended non-repo deployments can override
  `refresh_fixture: false` in a deployment-specific config, but the implemented
  repo default and tests will cover the committed-fixture refresh path.
- Fixture refresh will refresh only the small Ayoluengo sample and
  `_metadata.json` via `refresh_ayoluengo_fixture(...)`.
- The scheduler job will count records from the merged full production frame so
  `JobResult.records_updated`, `_metadata.json`, and `manifest.json` report the
  same scheduler-scale row count.
- `DataScheduler.run_once(...)` will pass an internal `_scheduler_repo_root`
  value into the job config before calling `job.run(...)`. The Spain job will
  use that root to resolve relative `output_dir` and `fixture_output_dir`,
  aligning job-written raw/normalized/source metadata with the manifest path
  `DataScheduler` already resolves from the scheduler config root.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review artifacts | `scripts/review/results/2026-07-05-plan-809-*.md` |
| Scheduler job | `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/spain_cores_refresh.py` |
| Scheduler lazy export | `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/__init__.py` |
| CLI job registry | `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/cli.py` |
| Scheduler package dependency | `packages/worldenergydata-scheduler/pyproject.toml` |
| Workspace lock update | `uv.lock` |
| Scheduler config | `config/scheduler/scheduler_config.yml` |
| Scheduler README | `packages/worldenergydata-scheduler/README.md` |
| Unit tests | `tests/unit/scheduler/test_spain_cores_refresh.py` |
| Registry/interface tests | `tests/unit/scheduler/test_jobs.py`, `tests/unit/scheduler/test_cli.py`, `tests/unit/scheduler/test_scheduler.py`, `tests/unit/scheduler/test_scheduler_cli_startup.py` |

## Deliverable

The implementation will add `SpainCoresRefreshJob` to `worldenergydata-scheduler`
so operators can run:

```bash
uv run python -m worldenergydata.scheduler run-job spain_cores_refresh --config config/scheduler/scheduler_config.yml
```

The job will:

1. Require an explicit scheduler `output_dir`.
2. Resolve the configured `output_dir` against the scheduler repo root when it
   is relative, then instantiate `CoresLiveProductionLoader(cache_root=output_dir)`.
3. Run `loader.refresh(force_refresh=<config>)`, which validates current CORES
   links and downloads official oil/gas workbooks from the direct source.
4. Load the merged all-product frame and count its rows.
5. Write scheduler `_metadata.json` and allow `DataScheduler` to write
   `manifest.json` on success.
6. Refresh the small committed Ayoluengo fixture when the repo default
   `refresh_fixture: true` setting is configured.
7. Register the job through the lazy scheduler job registry and default
   scheduler config.

## Pseudocode

```python
class SpainCoresRefreshJob(AbstractJob):
    name = "spain_cores_refresh"
    default_output_dir = get_data_root_safe() / "spain" / "cores"

    def run(self, config: dict) -> JobResult:
        start = datetime.now()
        if "output_dir" not in config:
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="skipped",
                records_updated=0,
                error_msg="Spain CORES live refresh requires an explicit output_dir",
            )

        scheduler_root = Path(config.get("_scheduler_repo_root", Path.cwd()))
        output_dir = _resolve_configured_path(config["output_dir"], scheduler_root)
        force_refresh = bool(config.get("force_refresh", False))
        refresh_fixture = bool(config.get("refresh_fixture", True))

        try:
            loader = CoresLiveProductionLoader(cache_root=output_dir)
            loader.refresh(force_refresh=force_refresh)
            production = loader.load_all_production()
            records = len(production)

            if refresh_fixture:
                oil = loader.load_oil_production()
                fixture_kwargs = {}
                if config.get("fixture_output_dir"):
                    fixture_kwargs["output_dir"] = _resolve_configured_path(
                        config["fixture_output_dir"], scheduler_root
                    )
                refresh_ayoluengo_fixture(
                    oil_frame=oil,
                    metadata=loader.metadata(),
                    **fixture_kwargs,
                )

            write_refresh_metadata("spain_cores", output_dir, records)
            return JobResult(self.name, start, datetime.now(), "success", records, None)
        except Exception as exc:
            logger.warning("Spain CORES refresh failed: %s", exc)
            return JobResult(self.name, start, datetime.now(), "failure", 0, str(exc))
```

The implementation will keep the actual code under the repo's line-length,
file-size, and focused-function guardrails.

## Files to Change

- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/spain_cores_refresh.py`
  will define `SpainCoresRefreshJob` and keep imports scoped to the job module.
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/__init__.py`
  will add a lazy export for `SpainCoresRefreshJob`.
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/cli.py`
  will add `("spain_cores_refresh", "...SpainCoresRefreshJob")` to `_JOB_SPECS`.
- `packages/worldenergydata-scheduler/src/worldenergydata/scheduler/scheduler.py`
  will add `_scheduler_repo_root` to the copied job config passed into
  `job.run(...)` so relative job output paths and manifest paths share one
  base directory.
- `packages/worldenergydata-scheduler/pyproject.toml` will add
  `worldenergydata-spain` to scheduler runtime dependencies.
- `uv.lock` will be refreshed after the scheduler dependency metadata changes.
- `config/scheduler/scheduler_config.yml` will add a `spain_cores_refresh`
  entry with `enabled: true`, monthly cadence,
  `output_dir: data/spain/cores`, `refresh_fixture: true`, and
  `fixture_output_dir: packages/worldenergydata-spain/src/worldenergydata/spain/data/cores`.
- `packages/worldenergydata-scheduler/README.md` will document Spain CORES as a
  scheduler-orchestrated source domain and show the `/mnt/ace` deployment path
  as configuration, not library code.
- `tests/unit/scheduler/test_spain_cores_refresh.py` will cover the new job.
- `tests/unit/scheduler/test_jobs.py` will include `SpainCoresRefreshJob` in
  interface/default-output checks.
- `tests/unit/scheduler/test_cli.py` will assert the default lazy registry
  includes `spain_cores_refresh`.

## TDD Test List

1. `test_spain_cores_missing_output_dir_skips_without_network`
   - Patch `CoresLiveProductionLoader`.
   - Call `SpainCoresRefreshJob().run({})`.
   - Expect `status == "skipped"`, `records_updated == 0`, and no loader call.

2. `test_spain_cores_refresh_downloads_and_writes_scheduler_metadata`
   - Patch `CoresLiveProductionLoader`.
   - Configure `output_dir=tmp_path` and `force_refresh=True`.
   - Mock `refresh()` to return source metadata.
   - Mock `load_all_production()` to return a two-row DataFrame.
   - Expect `refresh(force_refresh=True)` and `load_all_production()` calls.
   - Expect `JobResult(status="success", records_updated=2)`.
   - Expect `<tmp_path>/_metadata.json` to exist with module `spain_cores`.

3. `test_spain_cores_refresh_fixture_mode_writes_ayoluengo_fixture`
   - Patch `CoresLiveProductionLoader` and `refresh_ayoluengo_fixture`.
   - Configure `refresh_fixture=True` and `fixture_output_dir=tmp_path / "fixture"`.
   - Mock `load_oil_production()` and `metadata()`.
   - Expect `refresh_ayoluengo_fixture(...)` to receive the oil frame,
     loader metadata, and configured fixture output dir.

4. `test_spain_cores_fixture_mode_can_be_disabled_for_deployments`
   - Patch `refresh_ayoluengo_fixture`.
   - Configure `output_dir` plus `refresh_fixture=False`.
   - Expect no fixture refresh call.

5. `test_spain_cores_client_failure_returns_failure`
   - Patch `CoresLiveProductionLoader.refresh` to raise `RuntimeError("CORES offline")`.
   - Expect `status == "failure"`, `records_updated == 0`, and the error text
     in `error_msg`.

6. `test_cli_default_registry_includes_spain_cores_refresh`
   - Inspect `ALL_JOBS` or `_JOB_SPECS`.
   - Expect `spain_cores_refresh` present without importing the concrete Spain
     job module eagerly.

7. `test_jobs_interface_includes_spain_cores_refresh`
   - Add `SpainCoresRefreshJob` to scheduler job interface parametrization.
   - Expect abstract-subclass, job name, empty-config skip, and default output
     directory convention checks to pass.

8. `test_scheduler_config_contains_explicit_spain_output_dir`
   - Load `config/scheduler/scheduler_config.yml`.
   - Expect the Spain job entry to include `enabled: true`,
     `output_dir: data/spain/cores`, `refresh_fixture: true`,
     `fixture_output_dir`, and no absolute `/mnt/ace` hardcode in repo config.

9. `test_scheduler_passes_repo_root_to_jobs`
   - Register a capture job.
   - Call `DataScheduler.run_once(...)` from a cwd outside the repo root.
   - Expect the job config received by `run(...)` to include
     `_scheduler_repo_root` equal to the repo root inferred from the config path.

10. `test_spain_cores_run_once_keeps_job_outputs_and_manifest_in_one_root`
    - Run `DataScheduler.run_once("spain_cores_refresh")` with a fake
      `CoresLiveProductionLoader`.
    - Use relative `output_dir: data/spain/cores` and a cwd outside the repo
      root.
    - Expect raw/normalized/source metadata, `_metadata.json`, and
      `manifest.json` under the same repo-root-relative output tree.

11. `test_scheduler_cli_noop_does_not_import_spain_cores_refresh_job`
    - Extend `tests/unit/scheduler/test_scheduler_cli_startup.py` forbidden
      prefixes with `worldenergydata.scheduler.jobs.spain_cores_refresh` and
      `worldenergydata.spain.production.cores_live`.
    - Import `worldenergydata.scheduler.cli` and run `main([])`.
    - Expect no forbidden eager import.

## Acceptance Criteria

- `SpainCoresRefreshJob` will run the [#806](https://github.com/vamseeachanta/worldenergydata/issues/806)
  direct-source CORES live loader instead of implementing a second downloader.
- The scheduler job will be available as `spain_cores_refresh` through
  `cmd_run_job`, `ALL_JOBS`, and scheduler config.
- The scheduler package will declare `worldenergydata-spain` as a runtime
  dependency so installed scheduler environments can import the job.
- The job will skip without network when `output_dir` is omitted.
- The job will write raw, normalized, source metadata, scheduler metadata, and
  scheduler success manifest under one caller-configured data root, including
  when `output_dir` is relative and `run_once(...)` is called from a different
  cwd.
- Production code will not hardcode `/mnt/ace`; the README will document
  `/mnt/ace/worldenergydata/data/spain/cores` as an operator-supplied config
  value.
- The repo scheduler config will enable committed fixture refresh through
  `refresh_fixture: true`, and the job will call `refresh_ayoluengo_fixture(...)`
  rather than writing fixture files by hand.
- `uv.lock` will be updated with the scheduler package dependency metadata.
- Focused tests will pass:

```bash
uv run python -m pytest \
  tests/unit/scheduler/test_spain_cores_refresh.py \
  tests/unit/scheduler/test_jobs.py \
  tests/unit/scheduler/test_cli.py \
  tests/unit/scheduler/test_scheduler.py \
  tests/unit/scheduler/test_scheduler_cli_startup.py -q
```

- Source tests for the wrapped loader will remain green:

```bash
uv run python -m pytest tests/unit/spain/test_cores_live.py -q
```

- `scripts/legal/legal-sanity-scan.sh --diff-only` will pass.

## Risks

| Risk | Mitigation |
|---|---|
| Scheduler package cannot import Spain in installed environments | Add `worldenergydata-spain` to scheduler package dependencies and keep job imports lazy. |
| Duplicate CORES parsing logic diverges from [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) | Wrap `CoresLiveProductionLoader` and `refresh_ayoluengo_fixture(...)`; do not parse workbooks in scheduler code. |
| Scheduler job dirties a non-repo deployment checkout | The repo default will satisfy [#809](https://github.com/vamseeachanta/worldenergydata/issues/809) with `refresh_fixture: true`; deployment configs can override `refresh_fixture: false`. |
| `/mnt/ace` path leaks into library code | Use config-driven `output_dir`; add tests/docs that distinguish operational path from code defaults. |
| Relative output paths diverge between job output and scheduler manifest | Pass `_scheduler_repo_root` from `DataScheduler.run_once(...)` into job config and test from a cwd outside the repo root. |
| Retry layer repeats deterministic source failures | Return failure with the exception text; consider `retryable=False` only if tests identify deterministic CORES validation failures that should not retry immediately. |
| Record counts become inconsistent | Count rows from `load_all_production()` after refresh and pass that count to `write_refresh_metadata(...)`. |

## Adversarial Review Summary

Plan-stage review artifacts:

- `scripts/review/results/2026-07-05-plan-809-confucius-r1.md` - MAJOR;
  patched explicit config default, fixture-refresh ownership, canonical output
  root, scheduler-root normalization, lazy-import coverage, and `uv.lock`
  refresh.
- `scripts/review/results/2026-07-05-plan-809-confucius-r2.md` - MAJOR on
  closeout-state requirements and MINOR on focused verification command; patched
  verification command and carried closeout requirements forward.
- `scripts/review/results/2026-07-05-plan-809-codex-inline-r3.md` - APPROVE for
  plan content; force-add/push/comment/label remain required before surfacing
  for user approval.

Implementation will not start until the final review artifact set has no
unresolved MAJOR findings and the user explicitly approves the plan.
