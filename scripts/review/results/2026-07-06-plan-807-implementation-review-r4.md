# Plan Review r4: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Implementation/Downstream

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Reviewer:** Codex subagent Mendel
**Verdict:** MAJOR

## Findings

1. **MAJOR - Repo-relative `density_registry_path` lacked repo-root
   resolution.**

   The plan added a relative path in scheduler config and said the job would
   pass it into the loader. Existing scheduler code already resolves
   `output_dir` and `fixture_output_dir` through `_scheduler_repo_root`; the
   density registry path needed the same contract so scheduled runs from a
   non-repo cwd can find the registry.

2. **MAJOR - Non-retryable density coverage error contract was
   under-specified.**

   Existing retry classification treats `CoresSourceError` as non-retryable.
   The plan expected `CoresParseError` in the live-loader test and a generic
   deterministic error in the scheduler test, which could false-green with a
   fake exception while real density gaps stayed retryable.

3. **MAJOR - Production adapter fallback test did not force the embedded
   fallback path.**

   `SpainCoresAdapter()` normally uses `CoresFixtureProductionLoader` in this
   repo, so embedded fallback rows could remain stale unless the plan directly
   forces `_EmbeddedCoresFixtureLoader` or removes the fallback.

4. **MINOR - YAML scheduler config was not included in verification gates.**

   The plan covered Python format gates but did not run `check-yaml` or
   `yamllint` against `config/scheduler/scheduler_config.yml`.

## r3 Implementation Finding Status

- Scheduler config test coverage was fixed before r4.
- The remaining blockers were repo-root path resolution, real exception
  classification, embedded fallback path coverage, and YAML validation.

## Patch Response

- Scheduler wiring now resolves repo-relative `density_registry_path` through
  `_scheduler_repo_root` before constructing `CoresLiveProductionLoader`.
- The live-loader strict gap path now raises exported
  `CoresDensityCoverageError`; scheduler retry classification will treat that
  real exception as non-retryable alongside `CoresSourceError`.
- Scheduler tests now require the fake loader to receive the resolved registry
  path and the real `CoresDensityCoverageError`.
- Adapter tests now force `_EmbeddedCoresFixtureLoader` or require removal of
  the embedded fallback with a clear missing-fixture error.
- Verification gates now include `check-yaml` and `yamllint` for
  `config/scheduler/scheduler_config.yml`.
