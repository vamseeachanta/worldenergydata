# Plan #462 Review — Repo Integration/Testability r1

Verdict: MAJOR

## Findings

- MAJOR — `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:136`: verification command uses `.venv/bin/python`, but this worktree has no `.venv/bin/python` or `.venv/bin/pytest`; focused verification will fail before tests run. Fix: use available `python -m pytest ...` or add an explicit environment bootstrap prerequisite.
- MAJOR — `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:141` and `workspace-hub/scripts/legal/legal-sanity-scan.sh:263-268`: legal scan is not reproducible for this worktree. `worldenergydata` has no local `scripts/legal` scanner, and the workspace-hub scanner only scans `$WORKSPACE_ROOT/$TARGET_REPO`. Fix: use an exact command that targets the actual worktree, or add a repo-local wrapper/validated scanner path.
- MINOR — `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:101-104` and `:163-164`: validator/test scope only requires a known scheduler job and some output dir. It does not require the contract output dir to equal the configured job `output_dir`. This permits drift, especially because `eia_us_refresh` maps to `data/modules/eia`, not `data/modules/eia_us`. Fix: validate exact job-to-output-dir pairs and add a negative test for wrong output dir.
- MINOR — `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:71` and `:182`: enum compatibility is under-specified. Current scorecard emits freshness values omitted from the proposed freshness enum: `sample`, `full`, and `empty`. Fix: add an explicit scorecard-to-contract mapping rule and tests, or expand the freshness enum deliberately.

## Checked

- Plan file and plan index row
- Scorecard script/tests
- Scheduler config and scheduler-health script
- Source-readiness skill/script/reference
- Module manifest and freshness scorecard
- Legal scanner availability/scope
