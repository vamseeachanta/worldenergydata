# 2026-07-07 Exit Handoff: JSM D&C Diagnostic for #846

## Active task

Issue: https://github.com/vamseeachanta/worldenergydata/issues/846

Branch: `fix/846-jsm-dc-overcount`

PR: https://github.com/vamseeachanta/worldenergydata/pull/897

Diagnostic commit: `6f83ceed09a1e880fb6d269132b7c26c820ba9ac`

Exit handoff commit: this document's commit at branch head. Verify with `git rev-parse HEAD`.

This session completed PR 1 from the approved #846 plan: diagnostics and reporting only. No extractor behavior was changed.

## Completed actions

- Merged prior approved PR #892 for #757 before starting #846.
- Claimed #846 on the issue thread.
- Built and committed the JSM frozen-vs-candidate D&C diagnostic:
  - `scripts/lower_tertiary/build_jsm_dc_diff.py`
  - `src/worldenergydata/lower_tertiary/jsm_dc_report.py`
  - `src/worldenergydata/lower_tertiary/jsm_dc_sensitivity.py`
  - `tests/unit/lower_tertiary/test_jsm_dc_diff.py`
  - `reports/lower_tertiary/data/jsm_dc_per_bore_diff.csv`
  - `reports/lower_tertiary/data/jsm_post_td_activity.csv`
  - `reports/lower_tertiary/data/jsm_rule_sensitivity.csv`
  - `reports/lower_tertiary/jsm_dc_diff.html`
- Wired the report into `scripts/build_pages.py` so `scripts/build_pages.py --domains lower_tertiary` publishes `public/jsm-dc-diff.html`.
- Opened PR #897 and posted the required findings comment on #846:
  - https://github.com/vamseeachanta/worldenergydata/issues/846#issuecomment-4906592829

## Key findings

The live canonical extractor reproduces the issue headline but not the approved plan's expected completion-only split:

- Frozen JSM: 73 bores, 2,949 drilling + 3,864 completion = 6,813 D&C days.
- Candidate JSM: 73 bores, 3,065 drilling + 3,982 completion = 7,047 D&C days.
- Delta: +234 total, split +116 drilling / +118 completion.

Only two bores move:

- API `608124015400`, lease `G17016`: +48 drilling, +71 completion, `BOTH`.
- API `608124015504`, lease `G17015`: +68 drilling, +47 completion, `BOTH`.

Rule sensitivity showed every tested boundary rule disqualifies itself by moving Anchor and/or Buckskin pins.

## Verified state

PR #897 is open, non-draft, mergeable, and all GitHub checks are green as of 2026-07-07:

- `Test (PR gate)` passed.
- `domain-tests / Domain unit-lower_tertiary` passed.
- `domain-tests / Domain _always` passed.
- Lint, type check, security scan, documentation, build package, file-size, sensitive-file, title, changelog, docs, and GitGuardian checks passed.

Local verification run before opening/pushing PR #897:

- `uv run --no-sync --extra dev black --check ...` passed.
- `uv run --no-sync --extra dev isort --check-only ...` passed.
- `uv run --no-sync --extra dev flake8 ...` passed.
- `.venv/bin/python -m pytest tests/unit/lower_tertiary/test_jsm_dc_diff.py -q --no-cov` passed: 4 passed.
- `.venv/bin/python -m pytest tests/unit/lower_tertiary -q --no-cov` passed: 237 passed, 137 skipped.
- `uv run --no-sync pytest tests/integration/test_kc_ingest_fidelity.py -m slow -q --no-cov` passed: 4 passed.
- `uv run --no-sync python scripts/lower_tertiary/build_jsm_dc_diff.py` passed and printed the verified +234 split.
- `uv run --no-sync python scripts/build_pages.py --domains lower_tertiary` built 15 lower-tertiary pages including `jsm-dc-diff.html`.
- `cmp -s reports/lower_tertiary/jsm_dc_diff.html public/jsm-dc-diff.html` passed.
- Self-contained report gate passed: no external script/link URLs and no `cdn.plot`.
- Three-dot diff contains no `uv.lock`, `.bin`, or `.xlsx`.

## Current gate / blocker

Stop here for #846 until the owner records the PR 2 decision on the issue.

Do not self-approve or self-merge past this point. The next action is an owner decision on #846:

1. Choose a boundary rule despite Anchor/Buckskin sensitivity regressions; or
2. Document the current extractor behavior as an explained diagnostic finding and close without extractor changes.

## Cleanup / residue

Task repo state at exit:

- Worktree: `/mnt/local-analysis/wt-wed-846-jsm`
- Branch: `fix/846-jsm-dc-overcount`
- Head: this document's commit at branch head; verify with `git rev-parse HEAD`.
- Remote branch is pushed.
- Task temp workbook `/tmp/wed-846-dc-days-candidate.xlsx` was removed.

Expected pre-existing workspace residue observed during cleanup audit:

- Old stash on `main`: `stash@{0}: On main: wed stale pre-reorg dirty tree (recoverable) 2026-06-26`.
- Many sibling worktrees/checkouts under `/mnt/local-analysis/`.
- Existing `.cleanup-trash/20260616-095709`.
- Recent `uv`/`pytest` lock files under `/tmp`.

No task-local unexpected residue was left.

## Suggested skills

- `github:gh-address-comments` if PR #897 receives review comments.
- `github:gh-fix-ci` if any PR #897 checks regress after a new push.
- `superpowers:executing-plans` plus `superpowers:test-driven-development` if the owner approves PR 2 extractor behavior work.
- `coordination/pre-completion-cleanup-audit` before any next closeout.
