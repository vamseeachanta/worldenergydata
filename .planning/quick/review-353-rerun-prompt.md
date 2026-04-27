Adversarial re-review of revised GitHub issue plan #353 for worldenergydata.

You are reviewing ONLY the plan, not implementing it. Be adversarial and concise.

Context:
- Repo: /mnt/local-analysis/workspace-hub/worldenergydata
- Issue: https://github.com/vamseeachanta/worldenergydata/issues/353
- This is a planning-gated workflow. Do not implement. Do not edit files. Do not change labels.
- The revised plan already incorporated initial MAJOR feedback: deterministic import-sentinel tests instead of flaky timing-only unit tests; explicit lazy factory design constraints; concrete uv probes; and status-scope guardrails.

Return exactly:
Verdict: APPROVE|MINOR|MAJOR
Findings:
- [severity] evidence -> required change
Missing Tests:
- ...
Scope Creep / Boundary Risks:
- ...
Approval Readiness: one paragraph saying whether a user could approve this for implementation.

Plan content:

     1|# Plan for #353: diagnose uv/scheduler no-op command timeouts
     2|
     3|> **Status:** draft — revised after initial Codex/Gemini MAJOR review
     4|> **Complexity:** T3
     5|> **Date:** 2026-04-26
     6|> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/353
     7|> **Review artifacts:** `scripts/review/results/2026-04-26-plan-353-codex.md`, `scripts/review/results/2026-04-26-plan-353-gemini.md`
     8|
     9|---
    10|
    11|## Resource Intelligence Summary
    12|
    13|### Existing repo code
    14|- `pyproject.toml` defines a broad runtime dependency set including `pandas`, `pyarrow`, `scrapy`, `selenium`, `fastapi`, `dash`, `scikit-learn`, `schedule`, `loguru`, and `[tool.uv]` settings with `python = "3.11"`, `seed = true`, and `compile = true`.
    15|- `src/worldenergydata/scheduler/__main__.py` imports `worldenergydata.scheduler.cli.main`, so even no-arg scheduler help pays the full `scheduler.cli` import cost.
    16|- `src/worldenergydata/scheduler/cli.py` eagerly imports all scheduler job adapters at module import time and eagerly instantiates `ALL_JOBS` at lines 29-37.
    17|- Several scheduler job modules import heavy libraries or module-specific clients at import time:
    18|  - `src/worldenergydata/scheduler/jobs/bsee_refresh.py` imports `pandas`, `BSEEWebScraper`, and computes `_DEFAULT_OUTPUT_DIR = get_module_data_safe("bsee")` during import.
    19|  - `src/worldenergydata/scheduler/jobs/sodir_refresh.py` imports `pandas`, SODIR API client/endpoints/errors, and computes `_DEFAULT_OUTPUT_DIR = get_module_data_safe("sodir")` during import.
    20|  - `src/worldenergydata/scheduler/jobs/eia_us_refresh.py` imports `pandas`, `EIAIngestionSync`, shared parquet output code, and computes `_DEFAULT_OUTPUT_DIR = get_module_data_safe("eia")` during import.
    21|- `scripts/refresh_bsee_all.py` imports `pandas` and `requests` before building the `argparse` parser, so `--help` can be slow or timeout before reaching usage output.
    22|- Existing scheduler unit tests in `tests/unit/scheduler/test_scheduler.py` exercise `DataScheduler`, registration, status, run_once, start/stop, and disabled-job behavior with mock jobs, but they do not enforce import/no-op latency budgets or lazy CLI behavior.
    23|
    24|### Documents and reports consulted
    25|- Issue #353 body: timeout evidence from safe probes.
    26|- `docs/reports/2026-04-26-worldenergydata-scheduler-safe-probe-results.md`: original safe-probe artifact showing 30-60s timeouts for `uv run`, scheduler no-op/status, config validation, and `refresh_bsee_all.py --help/--dry-run`.
    27|- `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md`: follow-up read-only isolation probe created during planning.
    28|
    29|### Follow-up probe evidence
    30|The follow-up bounded probe changed the fault picture:
    31|- `.venv/bin/python -c "print('hello')"` completed in 0.06s.
    32|- `uv run python -c "print('hello')"` still timed out after 10s, so the uv path remains a separate environment-resolution blocker.
    33|- `import pandas` completed but took ~11.6s in the local environment; a second run remained ~10.9s.
    34|- `import worldenergydata.scheduler` completed in ~14.1s; `import worldenergydata.scheduler.config` hit a 15s timeout in one probe; `import worldenergydata.scheduler.scheduler` completed in ~13.8s.
    35|- `python -m worldenergydata.scheduler` with no args completed in ~5.1s and printed usage through logging.
    36|- `python -m worldenergydata.scheduler status --config config/scheduler/scheduler_config.yml` completed in ~12.1s and registered all seven scheduler jobs.
    37|- `scripts/refresh_bsee_all.py --help` timed out at 20s in the first probe, but completed in ~12.7s with a 60s cap in a subsequent check.
    38|
    39|### Gaps identified
    40|- No test currently protects low-latency CLI help/no-op startup for scheduler or refresh scripts.
    41|- No test currently proves scheduler CLI no-op commands avoid importing and instantiating every data-source job adapter.
    42|- The `uv run` timeout may be host/environment state, lock/metadata resolution, cache, or resolver behavior rather than a repo-code defect; it must be classified before changing repo code.
    43|- The `refresh_bsee_all.py --help` timeout is likely not a network/download problem; it is affected by import-time cost before `argparse` handles help.
    44|- The acceptance criterion of `<10s` is not currently met by `scheduler status` (~12s) or `refresh_bsee_all.py --help` (~12.7s in the successful follow-up run), even when they no longer hang indefinitely.
    45|
    46|### Scope split
    47|#### In scope now
    48|- Preserve and extend the read-only diagnostic artifact so future workers understand that `uv run` and `.venv` import latency are separate branches.
    49|- Add deterministic import-surface tests that prove no-op/help paths do not import heavyweight job/data dependencies or perform network/download setup.
    50|- Treat wall-clock timings as smoke/probe evidence, not as ordinary unit-test assertions, unless a threshold is explicitly calibrated for the execution environment.
    51|- Refactor repo-owned CLI import surfaces only after tests prove eager imports are responsible for a no-op/help path; do not broaden #353 into a scheduler architecture rewrite.
    52|- Classify `uv run` with concrete uv/cache/sync probes; document an operational workaround only if evidence shows the repo cannot own the fix.
    53|
    54|#### Out of scope now
    55|- Running full scheduler refreshes or downloading source datasets.
    56|- Fixing SODIR/EIA endpoint contract failures from #351; those remain separate source-specific follow-ups.
    57|- Rewriting all scheduler jobs or changing refresh semantics beyond lazy startup/no-op behavior.
    58|- Treating `uv run` timeout as solved by repo code unless a repo-owned trigger is evidenced.
    59|
    60|### Artifact map
    61|| Artifact | Path |
    62||---|---|
    63|| This plan | `docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md` |
    64|| Original safe-probe evidence | `docs/reports/2026-04-26-worldenergydata-scheduler-safe-probe-results.md` |
    65|| Follow-up timeout isolation probe | `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` |
    66|| Scheduler CLI entry | `src/worldenergydata/scheduler/cli.py` |
    67|| Scheduler module entrypoint | `src/worldenergydata/scheduler/__main__.py` |
    68|| Scheduler package exports | `src/worldenergydata/scheduler/__init__.py` |
    69|| Scheduler core | `src/worldenergydata/scheduler/scheduler.py` |
    70|| Scheduler config loader | `src/worldenergydata/scheduler/config.py` |
    71|| Scheduler job adapters | `src/worldenergydata/scheduler/jobs/*.py` |
    72|| BSEE standalone refresh CLI | `scripts/refresh_bsee_all.py` |
    73|| Existing scheduler tests | `tests/unit/scheduler/test_scheduler.py` |
    74|| Candidate new CLI latency tests | `tests/unit/scheduler/test_scheduler_cli_startup.py` and/or `tests/unit/bsee/test_refresh_bsee_cli_startup.py` |
    75|
    76|---
    77|
    78|## Deliverable
    79|
    80|A root-cause-backed scheduler/refresh startup repair that separates `uv` host/environment behavior from repo-owned Python import behavior, adds no-network regression coverage for no-op/help commands, and makes scheduler/refresh CLI help/status paths complete predictably enough for safe overnight readiness probes.
    81|
    82|---
    83|
    84|## Scope Boundaries
    85|
    86|### In scope now
    87|- Maintain the issue as diagnostic-first: first prove which branch is failing before implementing fixes.
    88|- Add deterministic import-surface tests around no-op/help/status startup that run without network/download side effects; keep wall-clock thresholds in smoke probes unless explicitly calibrated.
    89|- Make repo-owned CLI startup lazy where appropriate:
    90|  - scheduler no-arg/help usage should return before importing or instantiating refresh job adapters.
    91|  - `refresh_bsee_all.py --help` should return before importing `pandas`, `requests`, URL registries, or constructing sessions.
    92|  - scheduler `status` must not be casually rewritten; if a fast status path is needed, use a concrete design that separates config-derived job metadata from execution-job factories while preserving `cmd_status(jobs=...)`, `cmd_run_job`, and `start` behavior.
    93|- Add or update operator documentation only for the `uv run` branch if concrete uv probes prove it is host/environment-specific.
    94|
    95|### Explicitly out of scope
    96|- Full refresh execution.
    97|- Downloading BSEE/SODIR/EIA/Open-Meteo/GIE data as part of this issue.
    98|- Source-specific API contract fixes already identified by #351.
    99|- Broad dependency cleanup unrelated to no-op/help startup latency.
   100|- Changing scheduler job runtime semantics beyond import/startup boundaries.
   101|
   102|---
   103|
   104|## Pseudocode
   105|
   106|```text
   107|Phase 1: reproduce and classify
   108|    run bounded probes for:
   109|        venv print
   110|        uv --version
   111|        uv run python print
   112|        uv run --no-sync python print
   113|        uv run --offline python print
   114|        uv cache/config/lockfile state sufficient to classify resolver vs host/cache behavior
   115|        scheduler module no args
   116|        scheduler status with config
   117|        refresh_bsee_all --help
   118|        import timing for pandas/scheduler/job modules
   119|    classify each symptom as:
   120|        uv/host environment
   121|        Python import cost
   122|        scheduler eager job registration
   123|        refresh script eager dependency import
   124|        external/network/download path
   125|    update diagnostic artifact with classification
   126|
   127|Phase 2: write failing deterministic tests first
   128|    add import-sentinel tests for scheduler CLI import/help path:
   129|        importing scheduler.cli or invoking no-arg main must not import scheduler job modules
   130|        no refresh job instances are constructed before commands that need jobs
   131|    add import-sentinel tests for refresh_bsee_all --help path:
   132|        help handling must not import pandas, requests, url_registry, or construct network sessions
   133|    preserve existing public APIs:
   134|        cmd_status(jobs=[mock]) still works
   135|        cmd_run_job(..., jobs=[mock]) still works
   136|        start still uses execution job adapters
   137|    keep timing checks as smoke/probe artifacts unless thresholds are calibrated with environment metadata
   138|
   139|Phase 3: implement minimal repo-owned fixes
   140|    if scheduler help imports all jobs:
   141|        introduce a lazy execution-job factory, e.g. build_default_jobs(), used only by start/status/run-job paths that need execution adapters
   142|        ensure no-arg/help paths return before calling the factory
   143|    if scheduler status must be made faster:
   144|        do not guess; choose one explicit design:
   145|            use config-derived job names for metadata-only status, or
   146|            defer status-speed work to a follow-up metadata-registry issue
   147|        preserve injected jobs behavior for tests/API
   148|    if refresh_bsee_all --help imports heavy dependencies before argparse:
   149|        move pandas/requests/url_registry imports behind argparse help handling or into execution-only functions
   150|        use TYPE_CHECKING imports for annotations if needed
   151|    if uv remains independent:
   152|        document concrete workaround and update affected batch guidance to use .venv/bin/python where appropriate
   153|
   154|Phase 4: verify
   155|    run targeted deterministic import-surface tests
   156|    run smoke timing probes and save measured before/after evidence
   157|    rerun existing scheduler tests
   158|    update issue with measured before/after evidence
   159|```
   160|
   161|---
   162|
   163|## Files to Change
   164|
   165|| Action | Path | Reason |
   166||---|---|---|
   167|| Create/modify | `tests/unit/scheduler/test_scheduler_cli_startup.py` | deterministic import-sentinel coverage for scheduler no-op/help paths; timing only as optional smoke evidence |
   168|| Create/modify | `tests/unit/bsee/test_refresh_bsee_cli_startup.py` | deterministic import-sentinel coverage for `refresh_bsee_all.py --help`; no pandas/requests/url_registry/session construction on help path |
   169|| Modify if test requires | `src/worldenergydata/scheduler/cli.py` | replace eager job imports/`ALL_JOBS` instantiation with an explicit lazy execution-job factory for commands that need real jobs |
   170|| Modify if test requires | `src/worldenergydata/scheduler/__main__.py` | preserve module entrypoint compatibility after CLI lazy-loading changes |
   171|| Modify if test requires | `scripts/refresh_bsee_all.py` | move heavyweight imports behind argparse/help handling and use `TYPE_CHECKING` for annotations if needed |
   172|| Verify only | `src/worldenergydata/scheduler/jobs/*.py` | confirm no network/disk-heavy work occurs at import time; defer broader job-adapter import budget audit unless directly evidenced |
   173|| Update | `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` or successor | record uv probe matrix and final before/after smoke timings |
   174|| Update if uv branch is operational | `docs/reports/...` or issue comment | document `uv run` host/environment classification and `.venv/bin/python` workaround for affected batches |
   175|
   176|---
   177|
   178|## TDD Test List
   179|
   180|| Test name | What it verifies | Expected input | Expected output |
   181||---|---|---|---|
   182|| `test_scheduler_cli_import_is_lazy` | importing `worldenergydata.scheduler.cli` avoids eager job adapter imports | import with sentinel/import instrumentation | job modules/classes are not imported/instantiated at module import |
   183|| `test_scheduler_no_args_does_not_construct_default_jobs` | usage/no-arg path is import-light and exits before execution-job factory | call `main([])` with factory patched to fail if called | exits 0 / usage path without factory call |
   184|| `test_scheduler_injected_jobs_contract_preserved` | lazy factory does not break existing API seams | `cmd_status(jobs=[mock])`, `cmd_run_job(..., jobs=[mock])` | same behavior as existing tests |
   185|| `test_scheduler_status_design_is_explicit` | if status is changed, it either uses injected jobs/factory or config-derived metadata deliberately | status command/function under chosen design | complete job list without accidental eager imports, or status speed deferred explicitly |
   186|| `test_refresh_bsee_help_is_import_light` | BSEE refresh help exits before heavy/data work | execute help/import with sentinels | no `pandas`, `requests`, `url_registry`, or session construction before help exits |
   187|| `test_refresh_bsee_execution_still_imports_required_runtime_deps` | deferred imports do not break real dry-run/execution code paths | dry-run path with network/download mocked | required runtime imports happen only after argparse execution branch |
   188|| `test_existing_scheduler_unit_suite_still_passes` | lazy changes do not break core scheduler behavior | existing scheduler tests | pass |
   189|| `smoke_scheduler_and_refresh_timings_recorded` | timing evidence is captured without becoming flaky unit criteria | bounded probe script | report records before/after timings and environment metadata |
   190|
   191|---
   192|
   193|## Acceptance Criteria
   194|
   195|- [ ] Root cause classification distinguishes at least these branches: `uv run` environment/resolution, repo-owned scheduler import latency, and standalone BSEE refresh help import latency.
   196|- [ ] `uv` classification includes concrete probes for version, no-sync/offline behavior, cache/config/lockfile state, and outside-project behavior where feasible.
   197|- [ ] No full data refresh or unbounded download is performed during diagnosis, tests, or verification for this issue.
   198|- [ ] Deterministic tests prove scheduler no-arg/help paths do not import or instantiate refresh job adapters before they are needed.
   199|- [ ] Deterministic tests prove `scripts/refresh_bsee_all.py --help` does not import `pandas`, `requests`, URL registries, or construct network sessions before argparse help exits.
   200|- [ ] Existing public seams `cmd_status(jobs=[...])`, `cmd_run_job(..., jobs=[...])`, and scheduler `start` behavior remain compatible with existing scheduler tests.
   201|- [ ] `.venv/bin/python -m worldenergydata.scheduler` no-arg/help path completes under 10s in smoke probes after deterministic fixes.
   202|- [ ] `.venv/bin/python scripts/refresh_bsee_all.py --help` completes under 10s in smoke probes after deterministic fixes.
   203|- [ ] Scheduler `status` is either kept behaviorally compatible with measured smoke timing, or explicitly deferred to a metadata-registry follow-up if making it fast would require architectural scope beyond #353.
   204|- [ ] `uv run python -c "print('hello')"` either completes under 10s or a documented operational workaround/classification is attached to #353; repo code must not claim to fix `uv` if the evidence points to host/environment behavior.
   205|- [ ] New deterministic tests fail before any repo-owned startup fix and pass after the fix.
   206|- [ ] Existing scheduler unit tests still pass.
   207|- [ ] Final issue comment includes measured before/after smoke timings and identifies any residual operational-only `uv` action.
   208|
   209|---
   210|
   211|## Risks and Open Questions
   212|
   213|- The local environment has slow `pandas` import (~11s), so ordinary unit tests must not depend on wall-clock `<10s` thresholds; timing belongs in smoke probes with environment metadata.
   214|- `uv run` timeout may be outside repo control; the correct outcome may be an operational workaround plus repo-side `.venv/bin/python` command guidance for overnight batches.
   215|- Scheduler `status` may still need to register job names. A metadata-only registry is explicitly not part of #353 unless the implementation can prove a narrow config-derived design that preserves existing `cmd_status(jobs=...)`, `cmd_run_job`, and `start` behavior.
   216|- Existing logging currently emits duplicate log lines for scheduler usage/status in the probe output; this is probably not the blocking issue and should not be silently expanded into this fix unless tests require it.
   217|- If the follow-up probe no longer reproduces the original 30s scheduler hangs, the implementation must avoid overfitting to stale evidence and instead target reproducible lazy-import and uv-classification defects.
   218|
   219|---
   220|
   221|## Follow-up Issues
   222|
   223|- None created from this planning pass. Source-specific endpoint failures from #351 already belong to separate source-contract work, not #353.
   224|
   225|---
   226|
   227|## Review Readiness Notes
   228|
   229|Reviewers should focus on whether the plan correctly separates operational `uv` behavior from repo-owned startup latency, whether the test plan is specific enough to prevent regressions without becoming flaky, and whether lazy-import changes are tightly scoped.
   230|
   231|---
   232|
   233|## Complexity: T3
   234|
   235|**T3** — cross-cutting diagnostic issue touching execution environment, dependency/import cost, scheduler CLI startup, standalone script startup, and future overnight batch safety. The implementation should still be narrow after the root-cause branch is classified.
   236|
