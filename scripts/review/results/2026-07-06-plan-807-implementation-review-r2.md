# Plan Review r2: Issue [#807](https://github.com/vamseeachanta/worldenergydata/issues/807) Implementation/Downstream

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/807
**Plan:** `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`
**Reviewer:** Codex subagent Averroes
**Verdict:** MAJOR

## Findings

1. **MAJOR - Verification gates still did not cover all planned touched
   surfaces.**

   The plan changed scheduler code/config and production adapter fallback, but
   the format gates only covered Spain package files and selected tests. The
   plan also placed scheduler tests under a package-local path that does not
   match this repository's test layout.

   Required patch: use `tests/unit/scheduler/test_spain_cores_refresh.py` and
   include scheduler and production adapter source paths in the Black/isort
   gates.

2. **MINOR - Sidecar schema promised registry version/date without defining
   fields for it.**

   The prose said the sidecar would include registry version/date, but the exact
   schema had only `schema_version` and `generated_at`.

   Required patch: add explicit `registry_version` and `registry_date`, or
   remove the claim.

## Passed Checks

- All-or-blocked source coverage was planned.
- Ayoluengo non-representative evidence handling was planned.
- Parser conversion audit and sidecar/report caveat semantics were planned.
- Adapter fallback scope, scheduler non-retryable coverage semantics, legal
  scan, and user approval gate were present.

## Patch Response

- Scheduler tests now point to `tests/unit/scheduler/test_spain_cores_refresh.py`
  in the artifact map, TDD list, and pytest command.
- Formatting checks now include `packages/worldenergydata-scheduler/src`,
  `packages/worldenergydata-production/src`, `tests/unit/scheduler`, and
  `tests/unit/production/unified`.
- The sidecar schema now includes explicit `registry_version` and
  `registry_date` fields.
