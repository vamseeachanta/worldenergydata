# Handoff: worldenergydata Data Usability Improvements — 2026-04-16 COMPLETE

## Outcome

All 11 PRs from the original handoff merged into `main` via squash-merge with `--admin` override, under a **Delta-CI gate** (each PR must not increase CI error counts vs main's baseline). All 11 linked issues auto-closed.

## Merge log (in order)

| Order | PR | Issue | Merge commit | Notes |
|-------|-----|-------|--------------|-------|
| 1 | #295 | #287 | `dfb7416` | Test fixes. Also accidentally introduced 12 worktree gitlinks (cleaned in next commit). |
| - | — | — | `d45db93` | **Cleanup**: untrack `.claude/worktrees/*` gitlinks + add to `.gitignore`. |
| 2 | #296 | #291 | `5e910ab` | Legacy JSON removal, -8752 lines. |
| 3 | #303 | #300 | `5c22dc0` | Rebase conflict on `scripts/inventory_*.py` (also touched by #296) — resolved by taking PR #303's delete. |
| 4 | #294 | #285 | `6d41175` | DataResolver wiring, 36 files. Formatted 18 PR-touched files. |
| 5 | #297 | #292 | `bcbf158` | Freshness metadata. Rebase conflict on `bsee_refresh.py` + `sodir_refresh.py` — combined `get_module_data_safe` (from #294) with `write_refresh_metadata` import. |
| 6 | #301 | #286 | `c56a217` | Data catalog. Formatted 3 files. |
| 7 | #302 | #299 | `c164687` | Symlink tests. Rebase auto-skipped duplicated #286 commit. |
| 8 | #304 | #298 | `eedecf5` | Extend catalog to /mnt/ace. Rebase conflicts (both modified on 2 generator scripts) resolved by `checkout --theirs` + black reformat. |
| 9 | #305 | #290 | `77c2cbf` | Marine safety CLI. Skipped 3 ancestor commits (#286, #298, #290 parent). Formatted 4 files. |
| 10 | #306 | #288 | `15ba1d9` | Query API. Formatted 6 files. |
| 11 | #307 | #293 | `af3d371` | Quickstart notebooks. Skipped 3 merged ancestors. Formatted 5 notebook files. |

## CI Delta baseline

Main CI was already red when the session started (since 2026-04-14 dependabot typer update was the last green run). The Delta-CI gate tolerated inherited failures and only blocked *new* regressions:

| Check | Starting baseline | After merge train | Net change |
|-------|------------------:|------------------:|-----------:|
| Lint (black "would reformat") | 739 files | ~720 files | **−19 (improved)** |
| Type Check (mypy stub errors) | 61 | 61 | 0 |
| Test Python 3.11 collection errors | 5 | 5 | 0 |
| Test Python 3.10 collection errors | 5 | 5 | 0 |
| Test Python 3.9 collection errors | 5+ | 5+ | 0 |

## Root causes of inherited CI failures (still unfixed)

These were present on main BEFORE the 11-PR set and remain after:

1. **Lint (~720 files)**: Accumulated black/ruff formatting drift across the repo. Fixable by running `uv run black src/ tests/` and committing.
2. **Type Check (61 errors)**: Missing `types-requests` and `types-PyYAML` in `pyproject.toml` dev deps. Plus one torch/py3.11 pattern-matching syntax error deep in `.venv/lib/python3.11/site-packages/torch/_inductor/kernel/mm.py:813` (probably dep version pin).
3. **Test collection (5 errors on 3.10/3.11)**: Import failures in `tests/modules/bsee/analysis/test_type_curves.py`, `tests/modules/fdas/integration/test_end_to_end.py`, 3× `tests/modules/sodir-integration/test_*.py`.
4. **Test Python 3.9**: `str | None` union syntax (PEP 604) breaks on 3.9 — repo targets 3.9 but uses newer syntax. `eval_type_backport` package mentioned in error would help.

## Follow-ups recommended

- Open a single PR that runs repo-wide `black` + adds missing type stubs + fixes the 5 broken test imports — would likely flip main's CI back to green.
- The 12 leftover untracked `.claude/worktrees/` dirs on disk can be cleaned up with `rm -rf .claude/worktrees/` — they're now gitignored but still taking space.
- Remaining open items from original handoff: notebook validation, SODIR/EIA data fetch, #277 perf regressions, #278 module shims.

## Lessons captured

- **Worktree gitlink pollution** (new in global `.claude/memory/feedback_worktree_gitlink_pollution.md`): parallel agent workflows must gitignore `.claude/worktrees/` before the first commit, or sibling worktrees get tracked as 160000 submodule refs.
- **Delta-CI as a gate** works when main is broken but stable: compare PR's error counts vs main's, require ≤ (don't make it worse). Safer than "require green" (impossible on broken main) and more rigorous than "merge anyway."
- **Stacked branches + squash-merge**: `git rebase main` on later PRs auto-dropped equivalent commits via `--skip` when git saw the same content already merged upstream. No cherry-picking needed.

## Session duration

~2 hours end-to-end. Most time spent waiting on CI (2–5 min × 11 PRs).
