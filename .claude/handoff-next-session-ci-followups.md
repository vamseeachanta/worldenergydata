# Handoff: CI Cleanup Follow-ups — fresh-session execution

Continues the work from `handoff-2026-04-16-complete.md` and `handoff-2026-04-17-ci-cleanup.md`.

## What to read first (context, ~5 min)

1. `.claude/handoff-2026-04-17-ci-cleanup.md` — what was shipped in the 4 CI-cleanup PRs (#308, #311, #312) and closed in #310
2. `.claude/handoff-2026-04-16-complete.md` — the original 11-PR merge train and how the gitlink pollution was discovered

## 5 GitHub issues awaiting work

Dependency-ordered (easiest → hardest):

| # | Repo | Issue | Size | Priority |
|---|---|---|---|---|
| 1 | [workspace-hub#2326](https://github.com/vamseeachanta/workspace-hub/issues/2326) | Ecosystem: prevent `.claude/worktrees/` gitlink pollution | ~30 min | 🔴 Security-adjacent (prevent recurrence) |
| 2 | [worldenergydata#314](https://github.com/vamseeachanta/worldenergydata/issues/314) | Fix 51 flake8 F821 undefined-name errors | ~2-3 hrs | 🔴 Real bugs |
| 3 | [worldenergydata#313](https://github.com/vamseeachanta/worldenergydata/issues/313) | Test infrastructure cleanup | ~2-3 hrs | 🟡 Unblocks other test work |
| 4 | [worldenergydata#315](https://github.com/vamseeachanta/worldenergydata/issues/315) | Evaluate ruff migration | ~2-4 hrs | 🟢 Strategic cleanup |
| 5 | [worldenergydata#316](https://github.com/vamseeachanta/worldenergydata/issues/316) | Mypy incremental typing plan | multi-week | 🟢 Architectural — may just need a decision |

## Recommended session plan

### Session A (1-2 hours): Ecosystem safety sweep
Resolves #2326. Low-risk, high-value — prevents the gitlink pollution from hitting digitalmodel, assethold, assetutilities, achantas-data.

Per affected repo, a 2-line PR:
```bash
cd <repo>
# Check for already-tracked gitlinks (should be empty)
git ls-tree HEAD .claude/worktrees/ 2>/dev/null | head
# Update .gitignore
printf '\n# Agent worktrees (local-only, must not be tracked as gitlinks)\n.claude/worktrees/\n' >> .gitignore
git add .gitignore
git commit -m "chore(gitignore): exclude .claude/worktrees/ to prevent submodule gitlinks"
git push
gh pr create --title "chore(gitignore): exclude .claude/worktrees/" --body "Ref: vamseeachanta/workspace-hub#2326"
```

Repos: `digitalmodel`, `assetutilities`, `assethold`, `achantas-data`. worldenergydata is already fixed.

Also consider updating any shared `.gitignore` template under `workspace-hub/` so new repos inherit the fix.

### Session B (2-3 hours): Fix F821 real bugs
Resolves #314. Run:
```bash
cd worldenergydata
uv run flake8 src/ tests/ --select=F821
```

For each of the 51 errors, identify whether it's (a) missing import, (b) typo, (c) stale call to removed code. Fix grouped by module. One commit per logical group. Add regression tests where a fix reveals a bug that had no coverage.

### Session C (2-3 hours): Test infra cleanup
Resolves #313. This was PR #310's original scope — reviewable in detail in the closed PR diff. Main tasks:
- Pick one pytest config file, delete the other
- Move `--maxfail=5` → removed, `--import-mode=importlib` → added
- Restore 3 type_curves submodule files (available via `git show 3c04803^:src/worldenergydata/modules/bsee/analysis/type_curves/blasingame.py` etc.)
- Move `numpy-financial` from `[dependency-groups].dev` to `[project.dependencies]`
- Rewrite stale imports (9 sodir-integration test files, 2 well_production_dashboard tests, 1 cost test)

### Session D (strategic decision, then 2-4 hrs): Ruff migration
Resolves #315. Start by getting agreement that ruff is the right move — document decision in an ADR or in `docs/CONTRIBUTING.md`. Then do the migration in one focused PR.

### Session E (1-hour decision, then ongoing): Mypy strategy
Resolves #316. This is mostly a decision: pick strategy A/B/C, implement the per-module override scaffold, document the "clean modules" list. Actual typing work proceeds incrementally over weeks.

## Fresh-session startup prompt

Copy-paste into a fresh Claude session:

```
Resume CI cleanup follow-ups for the worldenergydata/tier-1 ecosystem.

Read these in order:
1. /mnt/local-analysis/workspace-hub/worldenergydata/.claude/handoff-next-session-ci-followups.md
2. /mnt/local-analysis/workspace-hub/worldenergydata/.claude/handoff-2026-04-17-ci-cleanup.md (if more context needed)

Issues to tackle (pick one Session block from the handoff, don't try all five):
- workspace-hub#2326 — ecosystem worktree gitignore (~30 min, Session A — quickest win)
- worldenergydata#314 — fix 51 flake8 F821 real bugs (~2-3 hrs, Session B — highest bug-density)
- worldenergydata#313 — test infrastructure cleanup (~2-3 hrs, Session C — unblocks other work)
- worldenergydata#315 — ruff migration evaluation (~2-4 hrs, Session D — strategic)
- worldenergydata#316 — mypy typing plan (decision session, ongoing — Session E)

Start by asking me which block to tackle. Don't attempt multiple in one session — these are independent enough that each deserves focused attention and its own PR(s).

Conventions to follow (from previous sessions):
- Work directly on main branches is OK for trivial .gitignore fixes; everything else via PR
- Squash-merge via `gh pr merge --squash --delete-branch --admin`
- All PRs should have `Closes #NNN` in the body for auto-close
- If CI is still red after a fix (due to inherited debt from other layers), document the delta honestly and merge — "honestly red" is OK, "masking debt" is not
- Before any commit, verify .claude/worktrees/ doesn't have tracked gitlinks: `git ls-tree HEAD .claude/worktrees/`
```

## State snapshot (2026-04-17)

- Main branch: `main` at the post-PR-#312 tip
- 11 original PRs merged (#294-#307), 4 CI-cleanup PRs (#308, #311, #312 merged, #310 closed)
- All 11 original issues closed (#285-#293, #298-#300)
- 5 new follow-up issues open (#2326 on workspace-hub, #313-#316 on worldenergydata)
- No open PRs
- Main CI: partial pass (Black/isort/Docs/Security/File-size-checks all green; Lint/TypeCheck/Tests still failing on pre-existing debt documented in the issues above)
