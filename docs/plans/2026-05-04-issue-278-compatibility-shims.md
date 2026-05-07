# Plan for #278: Restore broken modules.* compatibility shims after bsee and marine_safety consolidation

> **Status:** draft
> **Complexity:** T3
> **Date:** 2026-05-04 (revised 2026-05-06 after Step-1.5 verify-against-repo-state)
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/278
> **Review artifacts:** scripts/review/results/2026-05-06-plan-278-claude.md | ...-codex.md | ...-gemini.md (pending)

---

## Resource Intelligence Summary

### Existing repo code

- Found: `src/worldenergydata/_compat.py` — `_ModulesRedirectFinder` installs a `sys.meta_path` finder that redirects `worldenergydata.modules.X` to `worldenergydata.X` with a `DeprecationWarning`. Covers all 17 moved top-level modules (incl. `bsee`, `marine_safety`).
- Found: `src/worldenergydata/bsee/analysis/type_curves/__init__.py` — 35-line file (regular file, NOT a symlink — `file(1)` reports `ASCII text`; `readlink` exits 1) that re-exports `blasingame.{...}`, `fetkovich.{...}`, `models.{...}`. The three sibling implementation files do NOT exist on disk; `ls src/worldenergydata/bsee/analysis/type_curves/` returns only `__init__.py` + `__pycache__`.
- Found: `src/worldenergydata/marine_safety/importers/__init__.py` — re-exports `BaseImporter`, `MISLEImporter`, `EMSAImporter` from existing sibling modules. **Healthy** — contradicts prior plan's claim of breakage.
- Found: `src/worldenergydata/marine_safety/analysis/incidents/__init__.py` — large re-export aggregating `hatch_maloperation_analysis`, `incident_correlator`, `incident_taxonomy`, `maib_loader`, `ntsb_marine_loader`, `uscg_client`. **Healthy** — contradicts prior plan.
- Found: `src/worldenergydata/marine_safety/processors/` — contains `base_processor.py`, `data_cleaner.py`, `data_normalizer.py`, `__init__.py`. **Healthy** — contradicts prior plan.
- Gap: 566 LOC of typecurve implementation (`blasingame.py` 250 LOC + `fetkovich.py` 209 LOC + `models.py` 73 LOC, plus the original 34-line `__init__.py`) is missing on `main`. Last present at commit `2c385bd8` (2026-03-25); deleted by commit `3c048030` (2026-04-10).

### Standards

Not applicable — this is a code-restoration / compatibility issue, not a standards-derived calculation.

### LLM Wiki pages consulted

No relevant wiki pages — typecurve module is engineering implementation, not standards-derived. (Blasingame SPE-15028 / Palacio-Blasingame SPE-25909 references are inline in `blasingame.py` source per `git show 2c385bd8`.)

### Documents consulted

- `docs/plans/2026-05-04-issue-278-compatibility-shims.md` (prior version, pre-revision) — claimed 4 broken `__init__.py` files: `modules/bsee/analysis/type_curves/`, `modules/marine_safety/importers/`, `modules/marine_safety/analysis/incidents/`, `modules/marine_safety/processors/`. Step-1.5 verification disproves 3 of 4: only the bsee `type_curves` path is broken, and the path the prior plan named (`modules/bsee/...`) is itself a redirect target — the real broken file lives at `src/worldenergydata/bsee/analysis/type_curves/__init__.py` (canonical post-#3c048030 location).
- Issue #278 body — names exactly the same 4 paths as the prior plan; user's "Recommended fix" of "Restore shim modules for deleted paths" is consistent with restoring the 566 LOC for the typecurve module specifically. The marine_safety bullets in the issue body are also stale relative to current `main` — the current `__init__.py`s import from existing siblings.
- PR #390 / issue #327 — already fixed the marine_safety conftest.py path bug; no work needed there.
- Issue #2433 — `tests/conftest.py:382-383` already documents `tests/modules/bsee/analysis/test_type_curves.py` as a known-broken collection target with comment "Missing worldenergydata.bsee.analysis.type_curves implementation pieces", confirming the typecurve gap is the only real bsee/marine_safety breakage.
- Commit `3c048030` (refactor consolidation, 2026-04-10) — message states "Backward-compatible re-exports preserved in modules/__init__.py" but the `bsee/analysis/type_curves/__init__.py` it left behind imports siblings that were deleted in the same commit. Net effect: 1 broken package, not 4.
- Commit `2c385bd8` (auto-sync, 2026-03-25) — adds 818 LOC including the three implementation files at the now-canonical-equivalent `modules/bsee/analysis/type_curves/` (pre-flatten path). Files are restorable via `git show 2c385bd8:<path>` or cherry-pick.

### Gaps identified

- 3 implementation files missing under `src/worldenergydata/bsee/analysis/type_curves/`: `blasingame.py`, `fetkovich.py`, `models.py`.
- The on-disk `__init__.py` is correct in shape (re-exports the right symbols) but cannot resolve its imports — it is the surviving header of an otherwise-deleted package.
- `tests/conftest.py:382-383` skip-list entry suppresses the failure at session level; the test file itself collects-error when targeted directly.

### Evidence (embedded verification)

**Issue statuses** (verified 2026-05-07T03:24Z via `gh issue view 278`):
- `#278` — OPEN — "Restore broken modules.* compatibility shims after bsee and marine_safety consolidation" (label: `status:plan-review`)
- `#327` — referenced in brief as already fixed by #390; not re-verified here (out of scope).

**File existence** (`ls -la` 2026-05-07T03:21Z):
- EXISTS: `src/worldenergydata/bsee/analysis/type_curves/__init__.py` (808 bytes, regular file — `readlink` exits 1)
- MISSING (broken — this plan restores): `src/worldenergydata/bsee/analysis/type_curves/blasingame.py`
- MISSING (broken — this plan restores): `src/worldenergydata/bsee/analysis/type_curves/fetkovich.py`
- MISSING (broken — this plan restores): `src/worldenergydata/bsee/analysis/type_curves/models.py`
- EXISTS (healthy — prior plan was wrong): `src/worldenergydata/marine_safety/importers/__init__.py`
- EXISTS (healthy — prior plan was wrong): `src/worldenergydata/marine_safety/analysis/incidents/__init__.py`
- EXISTS (healthy — prior plan was wrong): `src/worldenergydata/marine_safety/processors/__init__.py`

**Line excerpts** (`sed -n 1,18p src/worldenergydata/bsee/analysis/type_curves/__init__.py`):
```
"""Type curve matching for production analysis (Blasingame/Fetkovich)."""

from .blasingame import (
    blasingame_typecurve,
    match_blasingame,
    material_balance_time,
    normalized_rate,
    rate_integral,
    rate_integral_derivative,
)
from .fetkovich import (
    fetkovich_boundary,
    fetkovich_transient,
    fetkovich_typecurve,
    match_fetkovich,
)
from .models import MatchResult, ProductionData, ReservoirParams, TypeCurveSet
```

**Gap proofs** (`ls src/worldenergydata/bsee/analysis/type_curves/` 2026-05-07T03:21Z):
```
__init__.py  __pycache__
```
(no `blasingame.py`, no `fetkovich.py`, no `models.py` — confirms the 3 sibling modules referenced by `__init__.py` do not exist)

**Reproduction proofs** (verify-against-repo-state, per Step 1.5 of `issue-planning-mode`):

1. Symlink claim from triage brief is FALSE — `__init__.py` is a regular file:
```
$ readlink src/worldenergydata/bsee/analysis/type_curves/__init__.py; echo "exit:$?"
exit:1
$ file src/worldenergydata/bsee/analysis/type_curves/__init__.py
src/worldenergydata/bsee/analysis/type_curves/__init__.py: Python script, ASCII text executable
```
- Reproduced at: 2026-05-07T03:21Z
- Implication: the breakage is missing-sibling-modules, not a dangling symlink. Plan does NOT need a "retarget symlink" step.

2. Direct import fails with `ModuleNotFoundError`:
```
$ uv run python -c "import worldenergydata.bsee.analysis.type_curves" 2>&1 | tail -5
  File "/.../src/worldenergydata/bsee/analysis/type_curves/__init__.py", line 3, in <module>
    from .blasingame import (
ModuleNotFoundError: No module named 'worldenergydata.bsee.analysis.type_curves.blasingame'
```
- Reproduced at: 2026-05-07T03:25Z

3. Test collection fails on the actual test path (note: brief named a non-existent test path; real path is `tests/modules/bsee/analysis/test_type_curves.py`):
```
$ uv run pytest tests/modules/bsee/analysis/test_type_curves.py --collect-only 2>&1 | tail -10
src/worldenergydata/bsee/analysis/type_curves/__init__.py:3: in <module>
    from .blasingame import (
E   ModuleNotFoundError: No module named 'worldenergydata.bsee.analysis.type_curves.blasingame'
=========================== short test summary info ============================
ERROR tests/modules/bsee/analysis/test_type_curves.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
==================== no tests collected, 1 error in 47.19s =====================
```
- Reproduced at: 2026-05-07T03:24Z
- Failure mode observed matches issue claim: PARTIAL — issue alleges 4 broken `__init__.py` files; only 1 (the typecurve one) is actually broken. Plan addresses the verified failure mode, not the over-broad claim.

4. The `modules/*` namespace IS healthy (the `_compat.py` shim works):
```
$ uv run python -c "import worldenergydata.modules.bsee.analysis; import worldenergydata.modules.marine_safety; print('ok')" 2>&1 | tail -5
<string>:1: DeprecationWarning: worldenergydata.modules.bsee is deprecated. Use worldenergydata.bsee instead.
<string>:1: DeprecationWarning: worldenergydata.modules.bsee.analysis is deprecated. Use worldenergydata.bsee.analysis instead.
<string>:1: DeprecationWarning: worldenergydata.modules.marine_safety is deprecated. Use worldenergydata.marine_safety instead.
ok
```
- Reproduced at: 2026-05-07T03:24Z
- Implication: do NOT touch `_compat.py`. The compatibility layer is functioning. The single broken package surface is at the canonical path, not the redirect path.

**Source-SHA freshness proofs** (verifies that `2c385bd8` is the most-recent commit that touched each restoration target before the deletion at `3c048030`; rules out a hidden interim commit that would silently regress on restore):

```
$ git log --follow --all --oneline -- src/worldenergydata/modules/bsee/analysis/type_curves/blasingame.py
3c048030 refactor(modules): consolidate bsee and marine_safety to canonical locations
2c385bd8 chore(sync): auto-sync 2026-03-25

$ git log --follow --all --oneline -- src/worldenergydata/modules/bsee/analysis/type_curves/fetkovich.py
3c048030 refactor(modules): consolidate bsee and marine_safety to canonical locations
2c385bd8 chore(sync): auto-sync 2026-03-25

$ git log --follow --all --oneline -- src/worldenergydata/modules/bsee/analysis/type_curves/models.py
3c048030 refactor(modules): consolidate bsee and marine_safety to canonical locations
2c385bd8 chore(sync): auto-sync 2026-03-25
```

- Reproduced at: 2026-05-07T03:32Z
- Result: each of the 3 files has exactly two history entries — `2c385bd8` (creation/last-modify) and `3c048030` (deletion). No interim commit exists between 2026-03-25 and 2026-04-10 that touched these files at the legacy path. **Single-SHA extraction from `2c385bd8` is safe for all 3 files** (per-file SHA pinning collapses to the same SHA).

**Warnings configuration proof** (verifies whether pytest promotes `DeprecationWarning` to errors, which would force migrating the test-file imports off the `modules.*` redirect path):

```
$ grep -nE 'filterwarnings|error::DeprecationWarning' pyproject.toml pytest.ini tests/conftest.py 2>&1
pytest.ini:41:filterwarnings =

# Full block (pytest.ini lines 41-44):
filterwarnings =
    error
    ignore::UserWarning
    ignore::DeprecationWarning
```

- Reproduced at: 2026-05-07T03:32Z
- Interpretation: `error` IS the default rule, but `ignore::DeprecationWarning` follows it on a later line. pytest applies `filterwarnings` last-match-wins, so `DeprecationWarning` is **explicitly ignored, not promoted to error**. The existing test imports via `from worldenergydata.modules.bsee.analysis.type_curves import (...)` (verified at `tests/modules/bsee/analysis/test_type_curves.py:9`) will run cleanly through the `_compat.py` redirect — the `DeprecationWarning` they emit is suppressed by line 44.
- Implication: **no test-import migration required in this PR**. The existing Risk-LOW note (test imports via `modules.*` redirect) stands as-written; migration to the canonical path remains an optional follow-up, not a gating change.

<!-- Source count: issue #278 body, prior plan, _compat.py, type_curves/__init__.py, marine_safety __init__.py files, conftest.py:382, commit 2c385bd8, commit 3c048030, PR #390/#327, pytest.ini:41-44, git log --follow per-file (3) = 12 distinct sources -->

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `worldenergydata/docs/plans/2026-05-04-issue-278-compatibility-shims.md` |
| Tests (existing — already on disk, currently quarantined via conftest.py:383) | `worldenergydata/tests/modules/bsee/analysis/test_type_curves.py` |
| Implementation file 1 (restore) | `worldenergydata/src/worldenergydata/bsee/analysis/type_curves/blasingame.py` |
| Implementation file 2 (restore) | `worldenergydata/src/worldenergydata/bsee/analysis/type_curves/fetkovich.py` |
| Implementation file 3 (restore) | `worldenergydata/src/worldenergydata/bsee/analysis/type_curves/models.py` |
| Quarantine entry to remove | `worldenergydata/tests/conftest.py:382-383` |
| Plan review — Claude | `scripts/review/results/2026-05-06-plan-278-claude.md` |
| Plan review — Codex | `scripts/review/results/2026-05-06-plan-278-codex.md` |
| Plan review — Gemini | `scripts/review/results/2026-05-06-plan-278-gemini.md` |

---

## Deliverable

A working `worldenergydata.bsee.analysis.type_curves` package with the 3 sibling implementation modules restored from `2c385bd8`, `tests/modules/bsee/analysis/test_type_curves.py` collecting and passing, and the conftest.py:383 quarantine entry removed — proving the import surface promised by `__init__.py` is real and tested.

---

## Pseudocode

T3 issue — restoration of pre-existing implementation, not new design. Approach:

```
# Implementation steps (executed at implementation time, NOT during planning)

1. From a clean main branch, extract original files from commit 2c385bd8:
   for path in blasingame.py fetkovich.py models.py:
     git show 2c385bd8:src/worldenergydata/modules/bsee/analysis/type_curves/${path} \
       > src/worldenergydata/bsee/analysis/type_curves/${path}

2. Verify the imports inside each restored file:
   - blasingame.py imports from .models — OK (intra-package, models.py also restored)
   - fetkovich.py imports from .models — OK
   - models.py is a leaf — no internal imports
   - All three import from numpy / scipy — already in pyproject deps (verify with uv pip show)

3. Verify __init__.py re-export contract is exhaustive:
   - The 14 names in __all__ all resolve once the 3 sibling files exist
   - No additional symbols introduced

4. Run target test file:
   uv run pytest tests/modules/bsee/analysis/test_type_curves.py -v
   # Must pass; this is the TDD gate

5. Remove quarantine entry from tests/conftest.py:382-383
   (the broken_module_tests dict entry for test_type_curves.py)

6. Run broader collection sanity:
   uv run pytest tests/modules/bsee/ tests/unit/bsee/ --collect-only -q 2>&1 | tail -10
   # Must collect with zero ImportError/ModuleNotFoundError

7. Run regression sweep on adjacent surfaces:
   uv run pytest tests/unit/bsee/ tests/integration/bsee/ -q
   # Must pass — verifies restoration didn't shadow newer canonical typecurve impl
   # (Step-1.5 confirmed no other typecurve impl exists; this is the regression gate)
```

**Recommended option (rationale below): Option A — restore the 3 source files via `git show 2c385bd8:<path>`** (equivalent to a path-targeted cherry-pick but cleaner since `2c385bd8` is an `auto-sync` commit touching 9 unrelated files; we only want the 3 typecurve modules at the new canonical path).

Why not Option B (rewrite from scratch): wasteful — we have authoritative source at `2c385bd8`, and the test file (`test_type_curves.py`, 211 LOC, 28 test cases) was authored against that exact API surface.

Why not Option C (delete the dead module + tests): the issue body explicitly says "Restore shim modules for deleted paths or update all package re-exports and downstream imports atomically", and the test suite represents 211 LOC of behavioral specification (Fetkovich SPE-32629, Blasingame SPE-15028). The canonical __init__.py was preserved across the deletion commit, signaling intent-to-keep. Deleting it would discard committed-and-tested engineering value with no offsetting benefit.

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Restore (from `2c385bd8`) | `worldenergydata/src/worldenergydata/bsee/analysis/type_curves/blasingame.py` | 250 LOC implementation referenced by `__init__.py` |
| Restore (from `2c385bd8`) | `worldenergydata/src/worldenergydata/bsee/analysis/type_curves/fetkovich.py` | 209 LOC implementation referenced by `__init__.py` |
| Restore (from `2c385bd8`) | `worldenergydata/src/worldenergydata/bsee/analysis/type_curves/models.py` | 73 LOC dataclasses referenced by `__init__.py` and the others |
| Modify | `worldenergydata/tests/conftest.py` | Remove the `Path("tests/modules/bsee/analysis/test_type_curves.py")` entry from `broken_module_tests` (lines 382-383) |
| (no change) | `worldenergydata/src/worldenergydata/bsee/analysis/type_curves/__init__.py` | Already correct — leave as-is |
| (no change) | `worldenergydata/src/worldenergydata/_compat.py` | Already correct — Step 1.5 confirmed `modules.*` redirect path is healthy |
| (no change) | `worldenergydata/src/worldenergydata/marine_safety/{importers,analysis/incidents,processors}/__init__.py` | Step 1.5 confirmed all healthy — issue body and prior plan were wrong |
| Update | `worldenergydata/docs/plans/README.md` (if it indexes plans) | Note revision | 

---

## TDD Test List

The test file `tests/modules/bsee/analysis/test_type_curves.py` already exists (211 LOC, was authored alongside `2c385bd8`). It is currently quarantined via `conftest.py:382-383`. Once the 3 sibling modules are restored, the tests run as-is — no new test authoring needed for this plan. Verified test cases:

| Test name | What it verifies | Source location |
|---|---|---|
| `TestFetkovichBoundary::test_exponential_decline_b_zero` | b=0 yields exponential decline | `test_type_curves.py:31` |
| `TestFetkovichBoundary::test_intermediate_b_value` | b=0.5 produces hyperbolic | `test_type_curves.py:38` |
| `TestFetkovichBoundary::test_harmonic_decline_b_one` | b=1.0 yields harmonic | `test_type_curves.py:45` |
| `TestFetkovichBoundary::test_invalid_b_raises` | b<0 or b>1 raises | `test_type_curves.py:53` |
| `TestFetkovichTransient::test_finite_aquifer_transient` | reD=10 transient solution | `test_type_curves.py:65` |
| `TestFetkovichTransient::test_invalid_reD_raises` | reD<1 raises | `test_type_curves.py:72` |
| `TestFetkovichTypeCurve::test_typecurve_set_construction` | reD/b grid produces TypeCurveSet | `test_type_curves.py:99` |
| `TestBlasingameTypeCurve::test_blasingame_set_has_all_functions` | normalized rate + integrals present | `test_type_curves.py:143` |
| `TestMatching::test_fetkovich_match_exponential_recovers_params` | round-trip parameter recovery | `test_type_curves.py:178` |
| `TestMatching::test_blasingame_match_exponential_converges` | optimization converges | `test_type_curves.py:188` |
| (and 18 more — total 28) | full coverage of `__all__` symbols | — |

---

## Acceptance Criteria

- [ ] Direct import succeeds: `uv run python -c "import worldenergydata.bsee.analysis.type_curves"` exits 0.
- [ ] All 14 symbols in `__init__.py:__all__` are importable: `uv run python -c "from worldenergydata.bsee.analysis.type_curves import blasingame_typecurve, fetkovich_boundary, fetkovich_transient, fetkovich_typecurve, match_blasingame, match_fetkovich, material_balance_time, MatchResult, normalized_rate, ProductionData, rate_integral, rate_integral_derivative, ReservoirParams, TypeCurveSet"` exits 0.
- [ ] Test file collects and passes: `cd worldenergydata && uv run pytest tests/modules/bsee/analysis/test_type_curves.py -v` — 28 tests pass, 0 errors.
- [ ] Quarantine entry removed from `tests/conftest.py` (`Path("tests/modules/bsee/analysis/test_type_curves.py")` no longer in `broken_module_tests`).
- [ ] Compat-layer redirect still works: `uv run python -c "from worldenergydata.modules.bsee.analysis.type_curves import blasingame_typecurve; print('ok')"` exits 0 with `DeprecationWarning` only.
- [ ] No regression elsewhere in bsee: `uv run pytest tests/unit/bsee/ tests/modules/bsee/ -q` finishes without new failures relative to baseline (capture pre-fix counts in implementation PR).
- [ ] Review artifacts posted: `scripts/review/results/2026-05-06-plan-278-{claude,codex,gemini}.md`.

---

## Adversarial Review Summary

| Provider | Verdict (r1 → r2) | Key findings |
|---|---|---|
| Claude | MAJOR (r1) → APPROVE (r2) | r1: 2× blockers (P1 source-SHA freshness unverified; P2 pytest warnings config unverified). Both addressed in r2 with verified evidence. r2: 9× P3 polish (line-number drift, conditional Files-to-Change row, `28 tests` literal vs collect-only, SPE citation-contract justification, regression-gate path existence) + 5× author questions — none blocking. |
| Codex | UNAVAILABLE — INCOMPATIBLE_VERSION (both rounds) | CLI 0.128.0 in known-bad range (>= 0.124.0), upstream `openai/codex#19945`, see workspace-hub#2479. Remediation: `scripts/install/pin-codex.sh` to downgrade. |
| Gemini | NO_OUTPUT (both rounds) | Wrapper returned no review content (likely related to `feedback_gemini_sandbox_overlay_blindness.md`). |

**Overall result:** Single-provider Claude APPROVE on r2 with documented Codex/Gemini unavailability across both rounds. Per `feedback_permission_gate_blocks_cross_review.md`, treat as r2-complete with transparent provenance; user-approval surface accepts the documented provider gaps.

**Review artifacts:**
- r1 (2026-05-07T03:30:48Z): `scripts/review/results/20260507T033048Z-2026-05-04-issue-278-compatibility-shims.md-plan-{claude,codex,gemini}.md`
- r2 (2026-05-07T03:36:08Z): `scripts/review/results/20260507T033608Z-2026-05-04-issue-278-compatibility-shims.md-plan-{claude,codex,gemini}.md`

**P3 polish deferred to implementation review:** the r2 P3 findings (re-anchor conftest edit on textual marker not line numbers, replace literal `28 tests` with dynamic-N from `--collect-only`, add SPE-citation-contract justification, verify `tests/unit/bsee/` and `tests/integration/bsee/` directory existence before referencing them in regression gates) are non-blocking refinements to fold in at implementation time.

| Iteration | Verdict | Resolution |
|---|---|---|
| r1 → r2 | Claude MAJOR (2026-05-07T03:30:48Z) | Addressed P1 + P2 with verified evidence (`Source-SHA freshness proofs` and `Warnings configuration proof` evidence sub-blocks added under Resource Intelligence Summary > Evidence). P1: confirmed all 3 files share last-touched SHA `2c385bd8` — no interim commit, single-SHA extraction safe. P2: `pytest.ini` has `filterwarnings = error` followed by `ignore::DeprecationWarning` — DeprecationWarnings NOT promoted, no test-import migration required. P3s deferred to implementation review. |

Revisions made based on review:
- r1 → r2: added `Source-SHA freshness proofs` (3x `git log --follow --all --oneline`) and `Warnings configuration proof` (grep of pyproject.toml/pytest.ini/tests/conftest.py) evidence blocks; verified Pseudocode and Files-to-Change rows correctly extract from `2c385bd8` for all 3 files (no per-file SHA divergence found).

---

## Risks and Open Questions

- **Risk (HIGH): does restoring the deleted code regress whatever motivated commit `3c048030`?** — `3c048030`'s commit message says "consolidate bsee and marine_safety to canonical locations" and "(526 files) is canonical; modules/bsee/ stubs removed." The 566 LOC of typecurve implementation was deleted at the OLD path (`modules/bsee/analysis/type_curves/`), not the canonical path (`bsee/analysis/type_curves/`). The canonical __init__.py was preserved without its siblings — strongly implying accidental loss during the consolidation diff, not intentional removal. Mitigation: restore at the canonical path only (where `__init__.py` already lives); do NOT recreate the legacy `modules/bsee/analysis/type_curves/` siblings (the `_compat.py` redirect handles backward compat).
- **Risk (MEDIUM): the restored numpy/scipy code may use APIs that have shifted since 2026-03-25.** Mitigation: `pyproject.toml` pins (verify before implementation); test suite will exercise every public function; if any API drift appears, fix narrowly in the restored file.
- **Risk (LOW): test file at `tests/modules/bsee/analysis/test_type_curves.py` imports via the `modules.*` redirect path** (`from worldenergydata.modules.bsee.analysis.type_curves import ...`), which will emit `DeprecationWarning`. Acceptable per `_compat.py` design; can be migrated to the canonical path in a follow-up if desired (out of scope here).
- **Risk (LOW): conftest.py `broken_module_tests` is a single-source-of-truth file** — touching it to remove one entry is mechanically safe but should be done in the same PR as the restoration so test-collection matches code state.
- **Open:** Should the `modules/bsee/analysis/type_curves/__init__.py` legacy stub also be restored? **Recommendation: NO** — the `_compat.py` finder transparently redirects, so the legacy directory is unnecessary. Tests targeting `worldenergydata.modules.bsee.analysis.type_curves` work via the redirect path (verified Step 1.5).
- **Open:** Should the issue body (which lists 4 broken paths, 3 of which are healthy) be amended with the verify-against-repo-state findings before implementation? **Recommendation: YES** — post a comment on #278 summarizing the 3 false-positive paths and the 1 real one, so the audit trail reflects ground truth.

---

## Complexity: T3

**T3** — restores 532 LOC across 3 implementation files plus a conftest edit; touches 4 files in worldenergydata; carries non-trivial review burden because (a) we are reanimating deleted code so reviewers must verify nothing has shifted underneath, (b) the original failure diagnosis (4 broken `__init__.py`s + symlink) was wrong on every dimension and the revised plan must defensibly establish the new diagnosis, (c) we must verify the `_compat.py` redirect path still works through the restored package without subtle import-ordering bugs. Not a T2 — the resource-intelligence work alone (proving 3 of the 4 originally-claimed breakages are false) is non-trivial; not a T4 — no new design, no new dependencies, no schema changes.
