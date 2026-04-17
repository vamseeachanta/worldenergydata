# Handoff: worldenergydata CI Cleanup — 2026-04-17

Follow-up to `handoff-2026-04-16-complete.md`. Tackled the pre-existing CI debt that the 11-PR merge train inherited.

## Outcome per PR

| PR | Title | Status | Notes |
|----|-------|--------|-------|
| #308 | `chore(types): add types-requests and types-PyYAML stubs` | ✅ **Merged** | Added `types-requests`, `types-PyYAML`, `types-python-dateutil`; bumped mypy `python_version` from `3.8` → `3.10`. Eliminated 65 stub errors + the torch false-positive crash. Unmasked ~2918 real untyped-def errors — Type Check still red but honestly-red. |
| #310 | `fix(tests): restore broken imports in 5 CI-failing test files` | ❌ **Closed** | Scope larger than expected. Successfully fixed sodir-integration imports (3 errors cleared) and identified concrete next steps (restored type_curves files, moved `numpy-financial` to runtime deps, discovered dual pytest.ini config override, `--maxfail=5` hiding errors). Closed with explanatory comment recommending a dedicated "test infrastructure cleanup" issue. |
| #311 | `style: repo-wide black + isort formatting` | ✅ **Merged** | 746 files black-formatted, 399 isort-reordered. Added `isort>=5.0` to dev deps (was missing entirely). Black and isort now pass CI. Flake8 surfaced, reveals ~5000 pre-existing errors (3857 × E231, 419 × E501, 280 × F401, 51 × F821 real bugs, etc.). |
| #312 | `chore(ci): drop Python 3.9 support` | ✅ **Merged** | `requires-python >= 3.10`, classifiers + black target updated, CI matrix now `[3.10, 3.11, 3.12]`. Removes the failing 3.9 job (was failing on `str \| None` union syntax). Also fixed mis-labeled `minversion` comment in tests/pytest.ini. |

## Final main CI state

| Check | Before (2026-04-16) | After (2026-04-17) | Change |
|-------|---------------------|---------------------|--------|
| Lint ▸ Black | FAIL (720+ file drift) | **PASS** ✅ | Fixed via #311 |
| Lint ▸ isort | ERROR (not installed) | **PASS** ✅ | Fixed via #311 |
| Lint ▸ flake8 | Not reached (masked) | FAIL (~5000 errors) | Debt surfaced, not introduced |
| Type Check ▸ mypy | FAIL (61 stubs + torch crash) | FAIL (~2918 untyped defs) | Crash fixed, debt surfaced |
| Test Python 3.9 | FAIL | **REMOVED** 🗑️ | Dropped via #312 |
| Test Python 3.10 / 3.11 | FAIL (5 collection errors) | FAIL (same 5) | Unchanged |
| Test Python 3.12 | (not in matrix) | FAIL (same 5) | New target, same debt |
| Security Scan | PASS | PASS | — |

## Honest assessment

**Won:** Black formatting + isort + type stubs + py3.9 removal are shipped. These are concrete, completed debt reductions. The CI is no longer failing on cosmetic-but-fixable issues.

**Still open:** flake8 (5000+ errors) and mypy (2918+ errors) now show the full scope of pre-existing code-quality debt that was hidden behind crashes and missing deps. Neither is new — both existed before this session.

**Strategic insight:** This cleanup was a "peel the onion" exercise. Every layer of CI had its own debt, masked by a failing upstream layer. We can't make Lint or Type Check fully green without substantial manual typing / code quality work.

## Recommended next steps (separate sessions)

1. **Flake8 config**: Consider adding `.flake8` with `extend-ignore = E231,E501` to silence bulk rules. Focus on F821 (undefined names — real bugs) and F401 (unused imports — auto-fixable via `autoflake`).
2. **Consider migrating to `ruff`**: Single tool replacing black + isort + flake8, 10-100× faster, single config. Big simplification.
3. **Test infrastructure cleanup** (from closed #310):
   - Consolidate `./pytest.ini` + `./tests/pytest.ini` into one
   - Remove `--maxfail=5` to see full error picture
   - Add `--import-mode=importlib` to unify duplicate test filenames
   - Fix or delete broken tests in `well_production_dashboard/`, `unit/cost/test_proxy_comparison.py`, `modules/fdas/integration/test_end_to_end.py`
   - Separately: restore the deleted `type_curves` submodule files (`blasingame.py`, `fetkovich.py`, `models.py`) and move `numpy-financial` to runtime deps (this PR's work is reusable)
4. **Type annotations**: Incremental per-module typing to reduce the 2918 mypy errors. Or relax strict flags (`disallow_untyped_defs = false`) while gradually tightening per-module via `[[tool.mypy.overrides]]`.

## Session duration

~1.5 hours. Most time in CI iteration loops (5-10 min per retry × several retries on PR #311 due to black version mismatch and isort chain discovery).
