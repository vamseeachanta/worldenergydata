# Adversarial Plan Review: Issue #809 Spain CORES Scheduler Refresh Job

**Plan:** `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md`
**Reviewer:** Codex inline
**Round:** r3
**Verdict:** APPROVE

## Findings

None remaining at plan-content level.

## Verified Checks

- Confirmed the scheduler config default is explicit:
  `enabled: true`, `output_dir: data/spain/cores`, `refresh_fixture: true`, and
  a relative committed-fixture output path.
- Confirmed the plan aligns the canonical Spain CORES output root to
  `data/spain/cores`, matching the [#806](https://github.com/vamseeachanta/worldenergydata/issues/806)
  live refresh lane and `/mnt/ace/worldenergydata/data/spain/cores` operational
  target.
- Confirmed the plan uses `get_data_root_safe() / "spain" / "cores"` for the
  job default output directory and does not instruct use of
  `get_module_data_safe("spain") / "cores"`.
- Confirmed the plan requires `DataScheduler.run_once(...)` to pass
  `_scheduler_repo_root` into job config so relative `output_dir` and
  `fixture_output_dir` can resolve consistently with scheduler manifest output.
- Confirmed the test plan covers direct job behavior, fixture refresh enabled
  and disabled modes, CLI registry exposure, scheduler repo-root propagation,
  one-root output/manifest behavior, and no-op CLI lazy-import guards.
- Confirmed the acceptance command includes:
  `tests/unit/scheduler/test_spain_cores_refresh.py`,
  `tests/unit/scheduler/test_jobs.py`,
  `tests/unit/scheduler/test_cli.py`,
  `tests/unit/scheduler/test_scheduler.py`, and
  `tests/unit/scheduler/test_scheduler_cli_startup.py`.
- Confirmed `uv.lock` refresh is mandatory after adding the scheduler package
  dependency on `worldenergydata-spain`.
- Confirmed `git diff --check` passed for the plan, index, #806 status cleanup,
  and review artifacts.

## Closeout Requirements

The r2 findings about ignored review artifacts and GitHub labels are closeout
state requirements, not remaining plan-content defects. This plan must still be
force-added with its review artifacts, pushed, commented on
[#809](https://github.com/vamseeachanta/worldenergydata/issues/809), and labeled
`status:plan-review`/`lane:codex` before it is surfaced for user approval.
