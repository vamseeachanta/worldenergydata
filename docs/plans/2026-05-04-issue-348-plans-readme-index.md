# Plan: Issue #348 — Add docs/plans/README.md index for issue-plan tracking

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/348
**Status:** plan-review
**Tier:** T1 (docs only, no code)

## Plan

### Task 1 — Create docs/plans/README.md
Write a concise index with:
- Table format: `| Issue | Plan File | Status | Date |`
- Backfill entries for all existing plan files under `docs/plans/`
- Status column values: `plan-review`, `plan-approved`, `implemented`, `cancelled`
- One-liner description per plan

### Task 2 — Populate backfill entries
Scan `docs/plans/*.md` and extract issue number, date, and description from filenames/headers.
Current known active plans to index:
- #274, #326, #327, #328, #339, #341, #342, #343, #344, #349, #360, #364, #367
- #334, #335, #336, #337, #338, #353, #354, #355
- LT epic: #374, #375, #376, #377

### Task 3 — Add maintenance note
At top of README:
> Update this index when creating or approving a plan. Run `scripts/plans/index_plans.py --check` to verify no plan file is unindexed.

(Script implementation out of scope for this plan — the README structure comes first.)

## Acceptance Criteria
- `docs/plans/README.md` exists with all current plan files indexed
- Table is machine-scannable (pipe-delimited markdown)
