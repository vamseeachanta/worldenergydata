# Plan #462 Review — Repo Integration/Testability r2

Verdict: MAJOR

## Findings

- MAJOR — `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` Task 6 lines 196-207: legal scan recipe is still not reliably reproducible. The snippet reads `os.environ["WORKSPACE_HUB"]` but only assigns/checks a shell variable, not an exported environment variable. Fix: `export WORKSPACE_HUB=...`, add `set -euo pipefail` or explicit `REL_FROM_HUB` non-empty validation, then run the scanner.
- MAJOR — plan Artifact Map plus `.gitignore:299`: review artifacts are local-only ignored files. `git status --ignored` reports both `scripts/review/results/2026-06-09-plan-462-*-r1.md` as ignored, and `git ls-files` has no entries for them. Fix: move them to a tracked path or force-add them.
- MINOR — scorecard mapping test only covers `empty`, `sample`, and `full`, while the plan maps/requires `runtime_fetched` and current repo data has multiple `runtime_fetched` catalog rows. Fix: add `runtime_fetched` to the mapping test or add a dedicated regression test.

## Checked

- Plan file, plan index row, r1 review artifacts, git tracked/ignored state.
- Scheduler config output dirs, including `eia_us_refresh -> data/modules/eia`.
- Scorecard script/tests and current freshness scorecard/module manifest values.
- Workspace-hub legal scanner path handling and revised command behavior.
