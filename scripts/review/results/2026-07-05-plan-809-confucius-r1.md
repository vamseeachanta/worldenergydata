# Adversarial Plan Review: Issue #809 Spain CORES Scheduler Refresh Job

**Plan:** `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md`
**Reviewer:** Codex subagent `Confucius` (`019f2fcf-53a8-7e12-8726-e3f6f2da3312`)
**Round:** r1
**Verdict:** MAJOR

## Findings

- **MAJOR:** The plan header said `plan-review` while GitHub issue
  [#809](https://github.com/vamseeachanta/worldenergydata/issues/809) did not
  yet carry `status:plan-review` or a lane label. The plan branch also had not
  been pushed. The closeout sequence must push reviewed artifacts and then label
  the issue with evidence.
- **MAJOR:** The scheduler config default was unresolved because the plan said
  "disabled-by-default or enabled-reviewed". The plan must choose one explicit
  default and test it.
- **MAJOR:** The issue asks the scheduler to refresh committed fixtures and
  `_metadata.json` provenance, but the draft allowed fixture refresh to stay
  disabled indefinitely. The plan must define whether committed fixture refresh
  is scheduler-owned, manual-only, or out of scope.
- **MAJOR:** The draft mixed `data/spain/cores` and
  `data/modules/spain/cores` because its pseudocode used
  `get_module_data_safe("spain") / "cores"`. The plan must choose one canonical
  root and align config, defaults, README, and tests.
- **MAJOR:** The draft did not guarantee job-written output and scheduler
  `manifest.json` would land under the same root when `output_dir` is relative
  and `run_once(...)` is invoked from another cwd. The plan must normalize
  output paths consistently or add a scheduler-level test.
- **MINOR:** Registry tests that inspect `_JOB_SPECS` or `ALL_JOBS` do not prove
  Spain job modules are not eagerly imported. The lazy-import startup guard
  should include the Spain scheduler job and Spain CORES module prefixes.
- **MINOR:** Adding `worldenergydata-spain` to the scheduler package dependency
  metadata means `uv.lock` refresh should be mandatory, not conditional.

## Patch Response

- The plan now documents the post-push issue-label sequence rather than treating
  local plan text as live GitHub status.
- The scheduler config default is explicit: `enabled: true`,
  `output_dir: data/spain/cores`, `refresh_fixture: true`, and a relative
  committed fixture output path.
- The plan makes committed fixture refresh part of the repo default scheduler
  behavior, with deployment-specific configs allowed to override
  `refresh_fixture: false`.
- The canonical scheduler output root is `data/spain/cores`, matching the
  [#806](https://github.com/vamseeachanta/worldenergydata/issues/806) live lane
  and `/mnt/ace/worldenergydata/data/spain/cores` operational target.
- The plan adds a `DataScheduler.run_once(...)` change to pass
  `_scheduler_repo_root` into job config and requires tests proving job outputs
  and manifest share one root from a non-repo cwd.
- The lazy-import startup guard and `uv.lock` refresh are now explicit test and
  acceptance requirements.
