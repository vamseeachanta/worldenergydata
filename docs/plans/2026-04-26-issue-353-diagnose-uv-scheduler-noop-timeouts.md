# Plan for #353: diagnose uv/scheduler no-op command timeouts

> **Status:** plan-review — revised after Codex/Gemini adversarial review
> **Complexity:** T3
> **Date:** 2026-04-26
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/353
> **Review artifacts:** `docs/reports/2026-04-26-plan-353-codex.md`, `docs/reports/2026-04-26-plan-353-gemini.md`, `docs/reports/2026-04-26-plan-353-rerun-gemini.md`

---

## Resource Intelligence Summary

### Existing repo code
- `pyproject.toml` defines a broad runtime dependency set including `pandas`, `pyarrow`, `scrapy`, `selenium`, `fastapi`, `dash`, `scikit-learn`, `schedule`, `loguru`, and `[tool.uv]` settings with `python = "3.11"`, `seed = true`, and `compile = true`.
- `src/worldenergydata/scheduler/__main__.py` imports `worldenergydata.scheduler.cli.main`, so even no-arg scheduler help pays the full `scheduler.cli` import cost.
- `src/worldenergydata/scheduler/cli.py` eagerly imports all scheduler job adapters at module import time and eagerly instantiates `ALL_JOBS` at lines 29-37.
- Several scheduler job modules import heavy libraries or module-specific clients at import time:
  - `src/worldenergydata/scheduler/jobs/bsee_refresh.py` imports `pandas`, `BSEEWebScraper`, and computes `_DEFAULT_OUTPUT_DIR = get_module_data_safe("bsee")` during import.
  - `src/worldenergydata/scheduler/jobs/sodir_refresh.py` imports `pandas`, SODIR API client/endpoints/errors, and computes `_DEFAULT_OUTPUT_DIR = get_module_data_safe("sodir")` during import.
  - `src/worldenergydata/scheduler/jobs/eia_us_refresh.py` imports `pandas`, `EIAIngestionSync`, shared parquet output code, and computes `_DEFAULT_OUTPUT_DIR = get_module_data_safe("eia")` during import.
- `scripts/refresh_bsee_all.py` imports `pandas` and `requests` before building the `argparse` parser, so `--help` can be slow or timeout before reaching usage output.
- Existing scheduler unit tests in `tests/unit/scheduler/test_scheduler.py` exercise `DataScheduler`, registration, status, run_once, start/stop, and disabled-job behavior with mock jobs, but they do not enforce import/no-op latency budgets or lazy CLI behavior.

### Documents and reports consulted
- Issue #353 body: timeout evidence from safe probes.
- `docs/reports/2026-04-26-worldenergydata-scheduler-safe-probe-results.md`: original safe-probe artifact showing 30-60s timeouts for `uv run`, scheduler no-op/status, config validation, and `refresh_bsee_all.py --help/--dry-run`.
- `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md`: follow-up read-only isolation probe created during planning.

### Follow-up probe evidence
The follow-up bounded probe changed the fault picture:
- `.venv/bin/python -c "print('hello')"` completed in 0.06s.
- `uv run python -c "print('hello')"` still timed out after 10s, so the uv path remains a separate environment-resolution blocker.
- `import pandas` completed but took ~11.6s in the local environment; a second run remained ~10.9s.
- `import worldenergydata.scheduler` completed in ~14.1s; `import worldenergydata.scheduler.config` hit a 15s timeout in one probe; `import worldenergydata.scheduler.scheduler` completed in ~13.8s.
- `python -m worldenergydata.scheduler` with no args completed in ~5.1s and printed usage through logging.
- `python -m worldenergydata.scheduler status --config config/scheduler/scheduler_config.yml` completed in ~12.1s and registered all seven scheduler jobs.
- `scripts/refresh_bsee_all.py --help` timed out at 20s in the first probe, but completed in ~12.7s with a 60s cap in a subsequent check.

### Gaps identified
- No test currently protects low-latency CLI help/no-op startup for scheduler or refresh scripts.
- No test currently proves scheduler CLI no-op commands avoid importing and instantiating every data-source job adapter.
- The `uv run` timeout may be host/environment state, lock/metadata resolution, cache, or resolver behavior rather than a repo-code defect; it must be classified before changing repo code.
- The `refresh_bsee_all.py --help` timeout is likely not a network/download problem; it is affected by import-time cost before `argparse` handles help.
- The acceptance criterion of `<10s` is not currently met by `scheduler status` (~12s) or `refresh_bsee_all.py --help` (~12.7s in the successful follow-up run), even when they no longer hang indefinitely.

### Scope split
#### In scope now
- Preserve and extend the read-only diagnostic artifact so future workers understand that `uv run` and `.venv` import latency are separate branches.
- Add deterministic import-surface tests that prove no-op/help paths do not import heavyweight job/data dependencies or perform network/download setup.
- Treat wall-clock timings as smoke/probe evidence, not as ordinary unit-test assertions, unless a threshold is explicitly calibrated for the execution environment.
- Refactor repo-owned CLI import surfaces only after tests prove eager imports are responsible for a no-op/help path; do not broaden #353 into a scheduler architecture rewrite.
- Classify `uv run` with concrete uv/cache/sync probes; document an operational workaround only if evidence shows the repo cannot own the fix.

#### Out of scope now
- Running full scheduler refreshes or downloading source datasets.
- Fixing SODIR/EIA endpoint contract failures from #351; those remain separate source-specific follow-ups.
- Rewriting all scheduler jobs or changing refresh semantics beyond lazy startup/no-op behavior.
- Treating `uv run` timeout as solved by repo code unless a repo-owned trigger is evidenced.

### Artifact map
| Artifact | Path |
|---|---|
| This plan | `docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md` |
| Original safe-probe evidence | `docs/reports/2026-04-26-worldenergydata-scheduler-safe-probe-results.md` |
| Follow-up timeout isolation probe | `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` |
| Scheduler CLI entry | `src/worldenergydata/scheduler/cli.py` |
| Scheduler module entrypoint | `src/worldenergydata/scheduler/__main__.py` |
| Scheduler package exports | `src/worldenergydata/scheduler/__init__.py` |
| Scheduler core | `src/worldenergydata/scheduler/scheduler.py` |
| Scheduler config loader | `src/worldenergydata/scheduler/config.py` |
| Scheduler job adapters | `src/worldenergydata/scheduler/jobs/*.py` |
| BSEE standalone refresh CLI | `scripts/refresh_bsee_all.py` |
| Existing scheduler tests | `tests/unit/scheduler/test_scheduler.py` |
| Candidate new CLI latency tests | `tests/unit/scheduler/test_scheduler_cli_startup.py` and/or `tests/unit/bsee/test_refresh_bsee_cli_startup.py` |

---

## Deliverable

A root-cause-backed scheduler/refresh startup repair that separates `uv` host/environment behavior from repo-owned Python import behavior, adds no-network regression coverage for no-op/help commands, and makes scheduler/refresh CLI help/status paths complete predictably enough for safe overnight readiness probes.

---

## Scope Boundaries

### In scope now
- Maintain the issue as diagnostic-first: first prove which branch is failing before implementing fixes.
- Add deterministic import-surface tests around no-op/help/status startup that run without network/download side effects; keep wall-clock thresholds in smoke probes unless explicitly calibrated.
- Make repo-owned CLI startup lazy where appropriate:
  - scheduler no-arg/help usage should return before importing or instantiating refresh job adapters.
  - `refresh_bsee_all.py --help` should return before importing `pandas`, `requests`, URL registries, or constructing sessions.
  - scheduler `status` must not be casually rewritten; if a fast status path is needed, use a concrete design that separates config-derived job metadata from execution-job factories while preserving `cmd_status(jobs=...)`, `cmd_run_job`, and `start` behavior.
- Add or update operator documentation only for the `uv run` branch if concrete uv probes prove it is host/environment-specific.

### Explicitly out of scope
- Full refresh execution.
- Downloading BSEE/SODIR/EIA/Open-Meteo/GIE data as part of this issue.
- Source-specific API contract fixes already identified by #351.
- Broad dependency cleanup unrelated to no-op/help startup latency.
- Changing scheduler job runtime semantics beyond import/startup boundaries.

---

## Pseudocode

```text
Phase 1: reproduce and classify
    run bounded probes for:
        venv print
        uv --version
        uv run python print
        uv run --no-sync python print
        uv run --offline python print
        uv cache/config/lockfile state sufficient to classify resolver vs host/cache behavior
        scheduler module no args
        scheduler status with config
        refresh_bsee_all --help
        import timing for pandas/scheduler/job modules
    classify each symptom as:
        uv/host environment
        Python import cost
        scheduler eager job registration
        refresh script eager dependency import
        external/network/download path
    update diagnostic artifact with classification

Phase 2: write failing deterministic tests first
    add import-sentinel tests for scheduler CLI import/help path:
        importing scheduler.cli or invoking no-arg main must not import scheduler job modules
        no refresh job instances are constructed before commands that need jobs
    add import-sentinel tests for refresh_bsee_all --help path:
        help handling must not import pandas, requests, url_registry, or construct network sessions
    preserve existing public APIs:
        cmd_status(jobs=[mock]) still works
        cmd_run_job(..., jobs=[mock]) still works
        start still uses execution job adapters
    keep timing checks as smoke/probe artifacts unless thresholds are calibrated with environment metadata

Phase 3: implement minimal repo-owned fixes
    introduce a lazy execution-job factory, e.g. build_default_jobs(), used only by start/status/run-job paths that need execution adapters
    ensure no-arg/help paths return before calling the factory
    for scheduler status, choose one explicit design before editing runtime behavior:
        use injected jobs/factory behavior unchanged for existing status paths, or
        use config-derived job names for a metadata-only status path, or
        defer status-speed work to a follow-up metadata-registry issue if this exceeds #353 scope
    preserve injected jobs behavior for tests/API
    move pandas/requests/url_registry imports in refresh_bsee_all.py behind argparse help handling or into execution-only functions
    use TYPE_CHECKING imports for annotations if needed
    after concrete uv probes, document the exact workaround and update affected batch guidance to use .venv/bin/python where repo code cannot own the fix

Phase 4: verify
    run targeted deterministic import-surface tests
    run smoke timing probes and save measured before/after evidence
    rerun existing scheduler tests
    update issue with measured before/after evidence
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create/modify | `tests/unit/scheduler/test_scheduler_cli_startup.py` | deterministic import-sentinel coverage for scheduler no-op/help paths; timing only as optional smoke evidence |
| Create/modify | `tests/unit/bsee/test_refresh_bsee_cli_startup.py` | deterministic import-sentinel coverage for `refresh_bsee_all.py --help`; no pandas/requests/url_registry/session construction on help path |
| Modify if test requires | `src/worldenergydata/scheduler/cli.py` | replace eager job imports/`ALL_JOBS` instantiation with an explicit lazy execution-job factory for commands that need real jobs |
| Modify if test requires | `src/worldenergydata/scheduler/__main__.py` | preserve module entrypoint compatibility after CLI lazy-loading changes |
| Modify if test requires | `scripts/refresh_bsee_all.py` | move heavyweight imports behind argparse/help handling and use `TYPE_CHECKING` for annotations if needed |
| Verify only | `src/worldenergydata/scheduler/jobs/*.py` | confirm no network/disk-heavy work occurs at import time; defer broader job-adapter import budget audit unless directly evidenced |
| Update | `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` or successor | record uv probe matrix and final before/after smoke timings |
| Update if uv branch is operational | `docs/reports/...` or issue comment | document `uv run` host/environment classification and `.venv/bin/python` workaround for affected batches |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_scheduler_cli_import_is_lazy` | importing `worldenergydata.scheduler.cli` avoids eager job adapter imports | import with sentinel/import instrumentation | job modules/classes are not imported/instantiated at module import |
| `test_scheduler_no_args_does_not_construct_default_jobs` | usage/no-arg path is import-light and exits before execution-job factory | call `main([])` with factory patched to fail if called | exits 0 / usage path without factory call |
| `test_scheduler_injected_jobs_contract_preserved` | lazy factory does not break existing API seams | `cmd_status(jobs=[mock])`, `cmd_run_job(..., jobs=[mock])` | same behavior as existing tests |
| `test_scheduler_status_uses_explicit_default_job_source` | status behavior is deliberately routed through either injected jobs, a lazy factory, or documented config metadata, not accidental eager module import | status command/function under chosen design | complete job list and preserved behavior without implicit import-time job construction |
| `test_refresh_bsee_help_is_import_light` | BSEE refresh help exits before heavy/data work | execute help/import with sentinels | no `pandas`, `requests`, `url_registry`, or session construction before help exits |
| `test_refresh_bsee_execution_still_imports_required_runtime_deps` | deferred imports do not break real dry-run/execution code paths | dry-run path with network/download mocked | required runtime imports happen only after argparse execution branch |
| `test_existing_scheduler_unit_suite_still_passes` | lazy changes do not break core scheduler behavior | existing scheduler tests | pass |
| `smoke_scheduler_and_refresh_timings_recorded` | timing evidence is captured without becoming flaky unit criteria | bounded probe script | report records before/after timings and environment metadata |

---

## Acceptance Criteria

- [ ] Root cause classification distinguishes at least these branches: `uv run` environment/resolution, repo-owned scheduler import latency, and standalone BSEE refresh help import latency.
- [ ] `uv` classification includes concrete probes for version, no-sync/offline behavior, cache/config/lockfile state, and outside-project behavior where feasible.
- [ ] No full data refresh or unbounded download is performed during diagnosis, tests, or verification for this issue.
- [ ] Deterministic tests prove scheduler no-arg/help paths do not import or instantiate refresh job adapters before they are needed.
- [ ] Deterministic tests prove `scripts/refresh_bsee_all.py --help` does not import `pandas`, `requests`, URL registries, or construct network sessions before argparse help exits.
- [ ] Existing public seams `cmd_status(jobs=[...])`, `cmd_run_job(..., jobs=[...])`, and scheduler `start` behavior remain compatible with existing scheduler tests.
- [ ] `.venv/bin/python -m worldenergydata.scheduler` no-arg/help path completes under 10s in smoke probes after deterministic fixes.
- [ ] `.venv/bin/python scripts/refresh_bsee_all.py --help` completes under 10s in smoke probes after deterministic fixes.
- [ ] Scheduler `status` is either kept behaviorally compatible with measured smoke timing, or explicitly deferred to a metadata-registry follow-up if making it fast would require architectural scope beyond #353.
- [ ] `uv run python -c "print('hello')"` either completes under 10s or a documented operational workaround/classification is attached to #353; repo code must not claim to fix `uv` if the evidence points to host/environment behavior.
- [ ] New deterministic tests fail before any repo-owned startup fix and pass after the fix.
- [ ] Existing scheduler unit tests still pass.
- [ ] Final issue comment includes measured before/after smoke timings and identifies any residual operational-only `uv` action.

---

## Risks and Open Questions

- The local environment has slow `pandas` import (~11s), so ordinary unit tests must not depend on wall-clock `<10s` thresholds; timing belongs in smoke probes with environment metadata.
- `uv run` timeout may be outside repo control; the correct outcome may be an operational workaround plus repo-side `.venv/bin/python` command guidance for overnight batches.
- Scheduler `status` may still need to register job names. A metadata-only registry is explicitly not part of #353 unless the implementation can prove a narrow config-derived design that preserves existing `cmd_status(jobs=...)`, `cmd_run_job`, and `start` behavior.
- Existing logging currently emits duplicate log lines for scheduler usage/status in the probe output; this is probably not the blocking issue and should not be silently expanded into this fix unless tests require it.
- If the follow-up probe no longer reproduces the original 30s scheduler hangs, the implementation must avoid overfitting to stale evidence and instead target reproducible lazy-import and uv-classification defects.

---

## Follow-up Issues

- None created from this planning pass. Source-specific endpoint failures from #351 already belong to separate source-contract work, not #353.

---

## Review Readiness Notes

Reviewers should focus on whether the plan correctly separates operational `uv` behavior from repo-owned startup latency, whether the test plan is specific enough to prevent regressions without becoming flaky, and whether lazy-import changes are tightly scoped.

### Adversarial review synthesis

- Initial Codex review returned **MAJOR** because the first draft relied too much on wall-clock timing tests, lacked explicit import-sentinel coverage, left scheduler status lazy-loading underspecified, and did not define concrete `uv` probes.
- Initial Gemini review aligned with the need for stronger import/no-network coverage and tighter status/uv boundaries.
- The plan was revised to use deterministic import-sentinel tests, an explicit lazy execution-job factory boundary, concrete uv no-sync/offline/cache probes, and smoke-only timing evidence.
- Gemini re-review returned **MINOR** only: make the status test name/assertion concrete and remove conditional wording from already-evidenced implementation steps. Those two changes are incorporated in this revision.
- Claude/Codex second re-review attempts stalled in the local CLI environment and were killed to avoid waste; the durable Codex/Gemini findings are preserved in `docs/reports/` and the plan directly resolves their blocking findings.

---

## Complexity: T3

**T3** — cross-cutting diagnostic issue touching execution environment, dependency/import cost, scheduler CLI startup, standalone script startup, and future overnight batch safety. The implementation should still be narrow after the root-cause branch is classified.
