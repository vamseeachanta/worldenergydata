# Plan for #326: Bug: self.prepare_production_data called but never defined on ProductionAnalyzer (bsee/analysis/production_api10.py)

> **Status:** plan-review
> **Complexity:** T2
> **Date:** 2026-05-04
> **Issue:** https://github.com/vamseeachanta/worldenergydata/issues/326
> **Review artifacts:** scripts/review/results/2026-05-04-plan-326-claude.md | ...-codex.md | ...-gemini.md

---

## Resource Intelligence Summary

### Existing repo code

- Found: `worldenergydata/src/worldenergydata/bsee/analysis/production_api10.py` — `ProductionAPI10Analysis` class with `router()`, `add_production_from_all_wells()`, `prepare_field_production_rate()`, and `prepare_field_production()` methods. `prepare_production_data()` is **called on line 17 but not defined anywhere in the file**.
- Found: `worldenergydata/tests/unit/bsee/test_bsee_analysis.py` — unit test pattern reference for BSEE analysis classes; uses `unittest.mock` and `pytest` fixtures; demonstrates how `router()` is exercised via `patch.object`.
- Gap: No test file exists for `production_api10.py`; `grep -r "ProductionAPI10Analysis" tests/` returns empty.
- Gap: `prepare_production_data` is not defined in any file under `src/worldenergydata/bsee/`.

### Standards

| Standard | Status | Source |
|---|---|---|
| Not applicable — pure Python bug fix | n/a | n/a |

### LLM Wiki pages consulted

- No relevant wiki pages for this Python bug-fix issue.

### Documents consulted

- `worldenergydata/src/worldenergydata/bsee/analysis/production_api10.py` lines 16–35 — confirms call site and orphaned loop code; see embedded evidence below.
- `worldenergydata/tests/unit/bsee/test_bsee_analysis.py` — test style reference; `ProductionAPI10Analysis` is instantiated via `bsee_analysis.prod_api10_analysis` (line 328 of that file), confirming the class is live in the module graph.
- `worldenergydata/CLAUDE.md` — TDD mandatory; `uv run pytest`; files ≤500 lines.

### Gaps identified

- `prepare_production_data(self, cfg, api12_production_data)` method does not exist in `ProductionAPI10Analysis`; any call to `router()` raises `AttributeError: 'ProductionAPI10Analysis' object has no attribute 'prepare_production_data'`.
- No unit test file for `production_api10.py`; test coverage for `router()` is zero.

### Evidence (embedded verification)

**Issue statuses** (verified 2026-05-04 via issue URL):
- `#326` — OPEN — Bug: self.prepare_production_data called but never defined on ProductionAnalyzer (bsee/analysis/production_api10.py)

**File existence** (`ls` 2026-05-04):
- EXISTS: `worldenergydata/src/worldenergydata/bsee/analysis/production_api10.py`
- MISSING (new — this plan creates): `worldenergydata/tests/unit/bsee/test_production_api10.py`

**Line excerpts** (`production_api10.py` lines 16–35):
```
16    def router(self, cfg, api12_production_data):
17        self.prepare_production_data(cfg, api12_production_data)   # <-- CALLED, not defined
18
19        # Iterate over completions in the provided production data and build
20        # per-completion field-production summaries. Mirrors the legacy
21        # ong_fd_components.prepare_production_data loop: for each completion
22        # name, slice the DataFrame and feed it to the per-field aggregators.
23        completion_name_list = api12_production_data.COMPLETION_NAME.unique()
24        for completion_name in completion_name_list:
25            df_temp = api12_production_data[
26                api12_production_data.COMPLETION_NAME == completion_name
27            ].copy()
28            self.prepare_field_production_rate(df_temp, completion_name)
29            self.prepare_field_production(df_temp, completion_name)
```

**Line excerpts** (`production_api10.py` lines 85 and 106 — methods that DO exist):
```
85    def prepare_field_production_rate(self, df_temp, df_column_label):
...
106   def prepare_field_production(self, df_temp, df_column_label):
```

**Gap proofs**:
- `grep -n "def prepare_production_data" src/worldenergydata/bsee/analysis/production_api10.py` → no output → method not defined.
- `find tests/ -name "test_production_api10.py"` → no output → no test file exists.

<!-- Verification: distinct sources — issue body (1), production_api10.py (2), test_bsee_analysis.py (3), worldenergydata/CLAUDE.md (4). Count: 4 ✓ -->

---

## Artifact Map

| Artifact | Path |
|---|---|
| This plan | `worldenergydata/docs/plans/2026-05-04-issue-326-prepare-production-data-missing.md` |
| Implementation | `worldenergydata/src/worldenergydata/bsee/analysis/production_api10.py` |
| Tests (new) | `worldenergydata/tests/unit/bsee/test_production_api10.py` |
| Plan review — Claude | `scripts/review/results/2026-05-04-plan-326-claude.md` |
| Plan review — Codex | `scripts/review/results/2026-05-04-plan-326-codex.md` |
| Plan review — Gemini | `scripts/review/results/2026-05-04-plan-326-gemini.md` |

---

## Deliverable

`ProductionAPI10Analysis.prepare_production_data(self, cfg, api12_production_data)` is implemented as an orchestration method that loops over unique completion names and delegates to the two existing per-completion aggregators, so that calling `router()` no longer raises `AttributeError`.

---

## Pseudocode

```
method prepare_production_data(self, cfg, api12_production_data):
    # Guard: if DataFrame is empty or missing COMPLETION_NAME column, return early
    if api12_production_data is None or api12_production_data.empty:
        return
    if "COMPLETION_NAME" not in api12_production_data.columns:
        raise ValueError("api12_production_data missing COMPLETION_NAME column")

    # Core loop: iterate over each unique completion name
    completion_name_list = api12_production_data.COMPLETION_NAME.unique()
    for completion_name in completion_name_list:
        # Slice DataFrame to this completion's rows only
        df_temp = api12_production_data[
            api12_production_data.COMPLETION_NAME == completion_name
        ].copy()
        # Delegate to existing per-completion aggregators
        self.prepare_field_production_rate(df_temp, completion_name)
        self.prepare_field_production(df_temp, completion_name)
```

**Structural change to `router()`:**  
After adding the method, the orphaned loop code on lines 23–29 must be removed from `router()` (it now lives inside `prepare_production_data`). `router()` retains only the single `self.prepare_production_data(cfg, api12_production_data)` call.

---

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Modify | `worldenergydata/src/worldenergydata/bsee/analysis/production_api10.py` | Add `prepare_production_data` method; remove orphaned loop from `router()` |
| Create | `worldenergydata/tests/unit/bsee/test_production_api10.py` | TDD test suite — exercises `router()` and `prepare_production_data()` directly |

---

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_router_no_attribute_error` | `router()` no longer raises `AttributeError` | valid DataFrame with `COMPLETION_NAME` column | returns without exception |
| `test_prepare_production_data_calls_per_completion_delegates` | delegates to both sub-methods once per unique completion | DataFrame with 2 distinct `COMPLETION_NAME` values | `prepare_field_production_rate` and `prepare_field_production` each called twice |
| `test_prepare_production_data_single_completion` | single completion iterates exactly once | DataFrame with 1 `COMPLETION_NAME` | each delegate called exactly once |
| `test_prepare_production_data_empty_dataframe` | empty DataFrame short-circuits without error | empty `pd.DataFrame()` | returns without calling delegates |
| `test_prepare_production_data_missing_column` | missing `COMPLETION_NAME` raises `ValueError` | DataFrame without `COMPLETION_NAME` | `ValueError` raised |
| `test_router_invokes_prepare_production_data` | `router()` calls `prepare_production_data` with correct args | any valid input | `prepare_production_data` called with `(cfg, api12_production_data)` |

---

## Acceptance Criteria

- [ ] All new tests pass: `uv run pytest worldenergydata/tests/unit/bsee/test_production_api10.py -v`
- [ ] No regression: `uv run pytest worldenergydata/` passes
- [ ] `router()` on a minimal synthetic DataFrame (one completion, required columns) completes without `AttributeError`
- [ ] Orphaned loop code removed from `router()` body (lines 23–29 of current file)
- [ ] `prepare_production_data` appears in `dir(ProductionAPI10Analysis())` after the fix

---

## Adversarial Review Summary

<!-- Filled in after Step 4 completes. Do not post to GitHub until this section is populated. -->

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | pending | — |
| Codex | pending | — |
| Gemini | pending | — |

**Overall result:** pending

Revisions made based on review:
- (none yet)

---

## Risks and Open Questions

- **Risk:** The orphaned loop in `router()` (lines 23–29) currently runs *after* the failing `self.prepare_production_data()` call, so it has never executed in production. After the fix, the loop runs *inside* `prepare_production_data()` instead — confirm with caller that this behavioral change is acceptable (loop now encapsulated, not visible at `router()` level).
- **Risk:** `cfg` is accepted as a parameter by `prepare_production_data` to match the existing call signature, but the current orphaned loop does not use `cfg`. The method signature should retain `cfg` for forward-compatibility (future callers may use it), but the body can safely ignore it for now.
- **Open:** Should `prepare_production_data` accumulate results across completions (merging DataFrames) or only retain the last completion's state? Current `prepare_field_production_rate` and `prepare_field_production` each reinitialize `self.output_data_field_production_rate_df` / `self.output_data_field_production_df` on every call — if multi-completion accumulation is intended, those methods need a separate fix (#327 candidate). Flag for user during approval.

---

## Complexity: T2

**T2** — bug fix requires reading the full call chain across three methods, removing orphaned code from one location while inserting it into a new method, and writing a new test file with six test cases; no new modules or files beyond the test file.
