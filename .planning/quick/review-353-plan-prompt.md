# Adversarial Plan Review — worldenergydata Issue #353

## Your role
You are an adversarial reviewer. Assume the plan has defects until proven otherwise.
Do not praise. Do not restate the plan. Focus only on what is wrong, missing, or risky.
Return APPROVE only after affirmatively verifying each correctness-critical claim. When in doubt, return MINOR or MAJOR.
Each finding must cite a specific plan section, file path, or quoted claim.
Treat cited sources as assertions to verify, not facts to trust.
If nothing is found, explicitly list what you checked.

## Issue context
#353 fix(scheduler): diagnose uv/scheduler no-op command timeouts
Evidence includes uv run print timeout, earlier scheduler no-op/status/help timeouts, follow-up probe showing venv print is fast, uv still times out, pandas import ~11s, scheduler status ~12s, refresh_bsee_all --help ~12.7s with longer cap.

## Plan under review
# Plan for #353: diagnose uv/scheduler no-op command timeouts

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-04-26
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/353
> **Review artifacts:** pending

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
- Add regression tests that enforce bounded no-op/help command behavior without network access or downloads.
- Refactor repo-owned CLI import surfaces if tests show eager imports are responsible for slow no-op/help commands.
- Document any operational-only `uv` remediation separately if no repo-owned fix is identified.

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
- Add tests around no-op/help/status startup that run with bounded timeouts and no network/download side effects.
- Make repo-owned CLI startup lazy where appropriate:
  - scheduler help/no-arg usage should not import/instantiate all refresh jobs.
  - `refresh_bsee_all.py --help` should not import `pandas` before argparse can exit.
  - scheduler status should avoid work not required for status registration if feasible.
- Add or update operator documentation only for the `uv run` branch if it proves host/environment-specific.

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
        uv print
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

Phase 2: write failing tests first
    add scheduler CLI startup tests using subprocess with timeout
    add refresh_bsee_all --help startup test using subprocess with timeout
    assert no network/download methods are called for help/no-op paths where mockable
    choose a realistic threshold that satisfies issue acceptance (<10s) but does not make tests flaky

Phase 3: implement minimal repo-owned fixes
    if scheduler help imports all jobs:
        move job adapter imports/ALL_JOBS construction behind a factory used only by commands that need jobs
        keep no-arg/help path import-light
    if refresh_bsee_all --help imports pandas before argparse:
        move pandas import into parsing/execution path after help handling, or into functions that require DataFrame work
    if scheduler status remains slow from job eager imports:
        evaluate lazy job registry metadata vs instantiated job objects while preserving run-job behavior
    if uv remains independent:
        document operational workaround and do not pretend repo code fixes uv itself

Phase 4: verify
    run targeted startup tests
    rerun bounded probes
    rerun existing scheduler tests
    update issue with measured before/after evidence
```

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create/modify | `tests/unit/scheduler/test_scheduler_cli_startup.py` | enforce scheduler no-op/status/help startup budget and no-download behavior |
| Create/modify | `tests/unit/bsee/test_refresh_bsee_cli_startup.py` | enforce `refresh_bsee_all.py --help` budget and import-light behavior |
| Modify if test requires | `src/worldenergydata/scheduler/cli.py` | replace eager job imports/`ALL_JOBS` instantiation with lazy factory and help-first handling |
| Modify if test requires | `src/worldenergydata/scheduler/__main__.py` | preserve module entrypoint compatibility after CLI lazy-loading changes |
| Modify if test requires | `scripts/refresh_bsee_all.py` | move heavyweight imports behind argparse/help handling and avoid help-path pandas import |
| Verify only | `src/worldenergydata/scheduler/jobs/*.py` | confirm no network/disk-heavy work occurs at import time; defer broader job refactors unless directly evidenced |
| Update | `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` or successor | record final before/after probe results |
| Update if uv branch is operational | `docs/reports/...` or issue comment | document `uv run` host/environment classification and workaround |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_scheduler_module_no_args_completes_quickly` | `python -m worldenergydata.scheduler` usage path exits promptly | subprocess with timeout | exit 0 under threshold |
| `test_scheduler_status_completes_quickly_with_config` | status command remains bounded without downloads | subprocess with config | exit 0 under threshold, status contains jobs |
| `test_scheduler_cli_help_path_does_not_import_all_jobs` | help/no-arg path is import-light | monkeypatch/import instrumentation | no eager all-job imports/instantiation |
| `test_all_jobs_factory_is_lazy` | job construction happens only when needed | import `worldenergydata.scheduler.cli` | factory not executed on import |
| `test_refresh_bsee_help_completes_quickly` | BSEE refresh help exits before heavy/data work | subprocess `scripts/refresh_bsee_all.py --help` | exit 0 under threshold, usage text present |
| `test_refresh_bsee_help_does_not_import_pandas_before_argparse` | help path avoids heavyweight DataFrame dependency | import/monkeypatch or subprocess instrumentation | help succeeds without loading pandas on help path, if feasible |
| `test_existing_scheduler_unit_suite_still_passes` | lazy changes do not break core scheduler behavior | existing scheduler tests | pass |

---

## Acceptance Criteria

- [ ] Root cause classification distinguishes at least these branches: `uv run` environment/resolution, repo-owned scheduler import latency, and standalone BSEE refresh help import latency.
- [ ] No full data refresh or unbounded download is performed during diagnosis, tests, or verification for this issue.
- [ ] `.venv/bin/python -m worldenergydata.scheduler` no-arg/help path completes under 10s in the supported local environment.
- [ ] `.venv/bin/python -m worldenergydata.scheduler status --config config/scheduler/scheduler_config.yml` completes under 10s or the plan records why the threshold is unrealistic and revises acceptance with evidence before implementation closeout.
- [ ] `.venv/bin/python scripts/refresh_bsee_all.py --help` completes under 10s.
- [ ] `uv run python -c "print('hello')"` either completes under 10s or a documented operational workaround/classification is attached to #353; repo code must not claim to fix `uv` if the evidence points to host/environment behavior.
- [ ] New tests fail before any repo-owned startup fix and pass after the fix.
- [ ] Existing scheduler unit tests still pass.
- [ ] Final issue comment includes measured before/after timings and identifies any residual operational-only `uv` action.

---

## Risks and Open Questions

- The local environment has slow `pandas` import (~11s), which may make strict `<10s` subprocess tests flaky unless the implementation truly avoids pandas on help/no-op paths.
- `uv run` timeout may be outside repo control; the correct outcome may be an operational workaround plus repo-side `venv` command guidance for overnight batches.
- Scheduler status may still need to register job names; a lazy metadata registry may be safer than instantiating every job adapter, but that must be scoped narrowly to avoid scheduler behavior drift.
- Existing logging currently emits duplicate log lines for scheduler usage/status in the probe output; this is probably not the blocking issue and should not be silently expanded into this fix unless tests require it.
- If the follow-up probe no longer reproduces the original 30s scheduler hangs, the implementation must avoid overfitting to stale evidence and instead target the remaining reproducible slow paths.

---

## Follow-up Issues

- None created from this planning pass. Source-specific endpoint failures from #351 already belong to separate source-contract work, not #353.

---

## Review Readiness Notes

Reviewers should focus on whether the plan correctly separates operational `uv` behavior from repo-owned startup latency, whether the test plan is specific enough to prevent regressions without becoming flaky, and whether lazy-import changes are tightly scoped.

---

## Complexity: T3

**T3** — cross-cutting diagnostic issue touching execution environment, dependency/import cost, scheduler CLI startup, standalone script startup, and future overnight batch safety. The implementation should still be narrow after the root-cause branch is classified.


## Required output
- Verdict: APPROVE | MINOR | MAJOR
- Findings table with severity, cited evidence, risk, required change
- Missing tests
- Scope creep concerns
- Weakest assumption and what breaks if false
- Most likely implementation failure mode
- Most likely test gap
- Future issues suggested
- Review confidence
