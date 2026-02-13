# WRK-104 Steps 6-7 Cross-Review: Rig Fleet Bridge

Date: 2026-02-12

## Files Reviewed

| File | Lines | Description |
|------|-------|-------------|
| `src/worldenergydata/vessel_fleet/bridge/rig_fleet_bridge.py` | 84 | Bridge: curated vessel_fleet parquet to legacy BSEE rig_fleet format |
| `src/worldenergydata/vessel_fleet/bridge/__init__.py` | 8 | Re-exports LEGACY_COLUMNS and convert_curated_to_rig_fleet |
| `tests/modules/vessel_fleet/test_rig_fleet_bridge.py` | 283 | 13 tests (8 unit + 5 integration) |
| `scripts/vessel_fleet/build_expanded_rig_fleet.py` | 164 | Build script writing .bin files for RigFleetLoader fallback |

## Test Results

All 13 tests PASSED (run at review time):
- 8 unit tests: always run
- 5 integration tests: ran successfully against real curated parquet on disk

---

## Claude Review

### Overall Assessment

The bridge module is clean, concise (84 lines), and correctly implements the conversion contract. The LEGACY_COLUMNS list exactly matches all 23 fields of `RigFleetSchema` (verified by set comparison against `RigFleetSchema.model_fields`). The build script correctly places files in the `.local/rig_fleet/` directory for RigFleetLoader's 3-tier fallback (config override -> `.local/` -> `bin/`), and deliberately stores the 16-rig subset in a `subsets/` subdirectory to prevent the loader from auto-concatenating it with the full fleet.

### Findings

#### P2 - RIG_NAME column assumed present when VESSEL_NAME exists (MINOR)

**File**: `rig_fleet_bridge.py:67-69`

```python
if "VESSEL_NAME" in df.columns:
    mask = df["RIG_NAME"].isna() | (df["RIG_NAME"].str.strip() == "")
    df.loc[mask, "RIG_NAME"] = df.loc[mask, "VESSEL_NAME"]
```

The guard checks for `VESSEL_NAME` but unconditionally accesses `df["RIG_NAME"]`. If the curated DataFrame has `VESSEL_NAME` but no `RIG_NAME` column at all, this raises `KeyError`. In practice, the curated parquet always has both columns, so this is not a runtime risk today. However, a more defensive guard would be:

```python
if "VESSEL_NAME" in df.columns and "RIG_NAME" in df.columns:
```

Or, initialize `RIG_NAME` from the LEGACY_COLUMNS fill-loop first (lines 76-78 already add missing columns as `None`). Moving that loop before the fallback logic would make the function order-independent.

**Severity**: P2 (minor) -- curated data invariant guarantees both columns exist.

#### P2 - Empty-string fallback from VESSEL_NAME not tested (MINOR)

**File**: `test_rig_fleet_bridge.py`

The tests cover `RIG_NAME=None` falling back to `VESSEL_NAME` (line 73-80), and rows where both are `None` being dropped (line 99-110). However, there is no test for:

- `RIG_NAME=""` (empty string) falling back to `VESSEL_NAME` -- the bridge handles this (line 68: `str.strip() == ""`), but no test exercises it.
- `RIG_NAME="  "` (whitespace-only) falling back to `VESSEL_NAME` -- also handled but untested.
- `VESSEL_NAME` itself being whitespace-only after fallback -- the final filter at line 73 would catch this, but no test verifies it.

**Recommendation**: Add one test case with `RIG_NAME=["", "  ", None]` and corresponding `VESSEL_NAME` values to verify all three fallback triggers.

#### P3 - Pickle path user-controllable via --sample-bin (INFORMATIONAL)

**File**: `build_expanded_rig_fleet.py:64`

```python
df = pickle.load(f)  # nosec B301
```

The `nosec B301` annotation is justified for the default path (`data/modules/bsee/bin/rig_fleet/rig_fleet.bin`), which is repo-owned. However, the `--sample-bin` CLI argument allows an arbitrary path. In practice, this script is only run by developers with local file access, so the risk is negligible. The `nosec` annotation is acceptable.

#### P3 - Path input branch not tested (INFORMATIONAL)

**File**: `rig_fleet_bridge.py:61-62`, `test_rig_fleet_bridge.py`

```python
if isinstance(curated, (str, Path)):
    df = pd.read_parquet(Path(curated))
```

The function accepts `Union[pd.DataFrame, Path]` but all unit tests pass DataFrames. The integration tests read the parquet themselves and then pass the DataFrame. No test exercises the `Path` input branch of `convert_curated_to_rig_fleet`. This is low priority since the build script calls `pd.read_parquet` externally and passes the DataFrame.

### Positive Observations

1. **Column contract is exact**: 23 LEGACY_COLUMNS == 23 RigFleetSchema fields, zero delta (verified programmatically).
2. **Defensive copy**: `df = curated.copy()` at line 64 prevents mutation of the caller's DataFrame.
3. **Index reset**: `reset_index(drop=True)` at line 81 ensures clean 0-based indexing after row drops.
4. **LFS stub detection**: Build script (lines 57-61) correctly detects Git LFS stubs before attempting pickle load, consistent with the project's LFS handling pattern.
5. **Subdirectory isolation**: Subset bin placed in `subsets/` to avoid loader auto-concatenation -- shows understanding of the loader's `glob("*.bin")` behavior.
6. **Summary statistics**: Build script prints null-percentage diagnostics, useful for data quality monitoring.

---

## Codex CLI Review

**Rating: MINOR**

### Findings

1. **`convert_curated_to_rig_fleet` can crash if `RIG_NAME` column is missing** (or not string-typed). `rig_fleet_bridge.py:68` uses `df["RIG_NAME"]` and `.str.strip()` unconditionally. If curated input has only `VESSEL_NAME` (or numeric `RIG_NAME` dtype), this raises `KeyError` / `.str` accessor errors instead of performing fallback.

2. **`nosec B301` is only conditionally justified in the build script** because `--sample-bin` is user-controllable (`build_expanded_rig_fleet.py:64`). The default path is repo-owned (reasonable trust), but CLI allows arbitrary pickle path, so "only our own data" is not strictly true for this code path.

3. **The 13 bridge tests miss key edge cases**: Missing tests for absent `RIG_NAME` column, absent `VESSEL_NAME` column, non-string name types, `Path` input mode, and fallback behavior with whitespace-only `VESSEL_NAME`. Real-data tests are `skipif`-gated and may not run in CI.

### Checks Verified

- `RIG_NAME` null -> `VESSEL_NAME` fallback: correct for normal string-typed data with existing `RIG_NAME` column; not defensive for missing/non-string `RIG_NAME`.
- 23 `LEGACY_COLUMNS` vs `RigFleetSchema`: match exactly by field set/count (23 vs 23).
- Pickle safety (`nosec B301`): acceptable for trusted internal files, but not fully justified on user-supplied `--sample-bin`.
- 13 tests edge coverage: useful baseline, but notable edge gaps remain.
- Build script placement for loader fallback: default placement is correct for loader precedence (cfg override -> `.local` -> `bin`). Script writes full file in `.local` and subset in `.local/subsets` (not auto-loaded).

---

## Gemini CLI Review

**Rating: APPROVE**

### Findings

1. **`RIG_NAME` null -> `VESSEL_NAME` fallback**: Robust and correct logic. The bridge correctly handles null and empty-string fallback, then drops remaining unnamed rows.

2. **`LEGACY_COLUMNS` match `RigFleetSchema`**: Perfect alignment of all 23 columns confirmed.

3. **`pickle` usage safety**: Justified `nosec B301` use with trusted internal data sources. The LFS stub detection adds an extra layer of safety.

4. **Adequacy of 13 tests**: Comprehensive unit and integration tests, covering critical edge cases including null name fallback, row dropping, column filtering, non-null guarantees, data source preservation, and rig type validation.

5. **Build script file placement for `RigFleetLoader`'s 3-tier fallback**: The script correctly places files for the "committed sample" tier, and the overall multi-tier strategy is well-designed. The subdirectory isolation for subsets is a strong design choice.

---

## Summary

| Reviewer | Rating | Key Findings |
|----------|--------|-------------|
| **Claude (Opus 4.6)** | **MINOR** | P2: RIG_NAME column assumed present when VESSEL_NAME guard fires; P2: empty-string/whitespace fallback paths untested; P3: pickle path user-controllable; P3: Path input branch untested |
| **Codex CLI (GPT-5.3)** | **MINOR** | Missing RIG_NAME column crash risk; pickle nosec only conditionally justified; test gaps for absent columns, non-string types, whitespace fallback, Path input |
| **Gemini CLI** | **APPROVE** | All 5 review points pass; robust fallback, exact schema match, justified pickle safety, comprehensive tests, correct file placement |

### Consensus: MINOR

All three reviewers confirm:
- The 23 LEGACY_COLUMNS exactly match RigFleetSchema (zero delta).
- The RIG_NAME -> VESSEL_NAME fallback logic is correct for normal operation.
- The build script correctly places files for the 3-tier loader fallback.
- Pickle usage is acceptable for this internal-data context.

Two of three reviewers flag minor gaps:
- The bridge function is not defensive against a missing `RIG_NAME` column (would crash before the fallback can fire). Low real-world risk since curated data always has both columns.
- Test coverage misses empty-string/whitespace fallback triggers and the `Path` input branch.

### Recommended Follow-ups (Non-blocking)

1. Add a guard for missing `RIG_NAME` column before the `VESSEL_NAME` fallback block (move the LEGACY_COLUMNS fill-loop earlier, or add an explicit column check).
2. Add 1-2 tests for empty-string and whitespace-only `RIG_NAME` triggering fallback.
3. Add one test exercising the `Path` input branch with a tmp parquet file.
