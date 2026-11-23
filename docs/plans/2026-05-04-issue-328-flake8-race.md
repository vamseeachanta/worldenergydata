# Plan: Issue #328 — Flake8 F821 count variance investigation

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/328
**Status:** plan-review
**Tier:** T2 (tooling investigation + remediation)

## Problem
`uv run --extra dev flake8 src/ tests/ --select=F821` returns different counts across runs
on the same codebase (observed: 104 / 29 / 137 in three runs during #314 sweep).

## Plan

### Task 1 — Reproduce the variance
Run 5× with output captured:
```bash
for i in $(seq 5); do
  uv run --extra dev flake8 src/ tests/ --select=F821 2>&1 | wc -l
  echo "---"
done
```
If counts are stable → variance was transient (bytecode cold-start only); document and close.
If counts vary → continue to Task 2.

### Task 2 — Isolate uv vs flake8
```bash
# Direct .venv invocation (bypass uv)
.venv/bin/flake8 src/ tests/ --select=F821 2>&1 | wc -l
# Repeat 3x
```
If `.venv/bin/flake8` is stable but `uv run flake8` varies → the issue is uv env state.

### Task 3 — Compare to ruff (as replacement signal)
```bash
uv run --extra dev ruff check src/ tests/ --select=F821 --output-format=json | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
```
If ruff count is stable and matches ground truth → recommend replacing flake8 F821 checks with ruff in CI.

### Task 4 — Update CI to use stable path
If ruff is stable: update `.github/workflows/ci.yml` bandit step (or quality gate step) to use:
```bash
uv run ruff check src/ tests/ --select=F821
```
instead of `uv run --extra dev flake8 --select=F821`.

If variance is confirmed to be cold-start only: add a warmup step:
```bash
uv run --extra dev python -c "pass"  # warm env before flake8
```

## Acceptance Criteria
- Root cause documented in plan or issue comment
- CI uses a deterministic F821 check
- 5 consecutive same-branch runs return the same count
