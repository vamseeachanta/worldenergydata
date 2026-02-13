# WRK-104 Step 1 Cross-Review: WAR Fleet Export

Date: 2026-02-13

## Files Reviewed

| File | Lines | Purpose |
|------|-------|---------|
| `src/worldenergydata/vessel_fleet/exporters/war_export.py` | 72 | Core export function |
| `tests/modules/vessel_fleet/test_war_export.py` | 236 | 14 unit tests in 6 classes |
| `scripts/vessel_fleet/export_war_to_vessel_fleet.py` | 121 | CLI script for batch export |

---

## Claude Review

### Overall Assessment

The implementation is clean, focused, and well under the 400-line limit. The single-function design with clear separation between filtering, mapping, and output is good. The test suite follows AAA (Arrange-Act-Assert) structure consistently and uses a thoughtful `_make_war_df` helper that includes all 21 WAR schema columns for realistic test data.

### Findings

#### P1 (High): Non-string RIG_NAME causes crash or leaks NaN records

**File**: `src/worldenergydata/vessel_fleet/exporters/war_export.py`, lines 43 vs 56

The filtering logic on line 43 uses `.astype(str)` to safely handle non-string types during the filter mask:

```python
mask = df["RIG_NAME"].notna() & (df["RIG_NAME"].astype(str).str.strip() != "")
```

But line 56 applies `.str.strip()` directly without conversion:

```python
df["RIG_NAME"] = df["RIG_NAME"].str.strip()
```

If `RIG_NAME` has `int64` dtype, `.str.strip()` raises `AttributeError`. If dtype is mixed `object` with some numeric values, non-strings become `NaN` after `.str.strip()` and are emitted as `VESSEL_NAME=NaN`, violating the `BaseVesselSchema.VESSEL_NAME: str` (required, non-null) contract.

**Reproduction**: Confirmed by Codex CLI reviewer via runtime test:
```python
pd.DataFrame({'RIG_NAME': [101, 202]})  # -> AttributeError
pd.DataFrame({'RIG_NAME': ['RIG A', 303]})  # -> exports NaN VESSEL_NAME
```

**Impact**: Low in practice (upstream WAR loader guarantees string RIG_NAME), but the function accepts `pd.DataFrame` generically and should be defensive.

**Fix**: Add `df["RIG_NAME"] = df["RIG_NAME"].astype(str)` after the initial copy, or at minimum before the `.str.strip()` call on line 56. Alternatively, add `.astype(str)` to line 56: `df["RIG_NAME"] = df["RIG_NAME"].astype(str).str.strip()`.

#### P2 (Medium): CLI pickle.load has no try/except for corrupt/unreadable files

**File**: `scripts/vessel_fleet/export_war_to_vessel_fleet.py`, lines 45-46

```python
with open(war_bin_path, "rb") as f:
    df = pickle.load(f)  # nosec B301
```

The function checks `war_bin_path.exists()` (line 41) and type-checks the result (line 48), but does not catch `pickle.UnpicklingError`, `EOFError`, `PermissionError`, or other I/O exceptions. A corrupt binary would produce an unhandled traceback instead of the clean error-and-return-1 pattern used elsewhere in the script.

**Fix**: Wrap in `try/except (pickle.UnpicklingError, EOFError, OSError) as e:` with `logger.error(...)` and `return pd.DataFrame()`.

#### P3 (Low): Test suite missing coverage for missing-column and all-filtered-out paths

The function has three early-return paths:
1. `war_fleet_df.empty` (line 33) -- tested by `test_empty_dataframe_returns_empty_list`
2. `"RIG_NAME" not in war_fleet_df.columns` (line 36) -- **not tested**
3. All rows filtered out post-mask (line 52) -- **not tested** (individual filter tests exist but not a combined "all rows invalid" scenario)

**Fix**: Add two tests:
- `test_missing_rig_name_column_returns_empty_list`: pass a DataFrame with columns but no `RIG_NAME`
- `test_all_rows_filtered_returns_empty_list`: pass a DataFrame where every row is null/blank/"NON RIG"

#### P4 (Low): `pytest` import unused

**File**: `tests/modules/vessel_fleet/test_war_export.py`, line 7

```python
import pytest
```

`pytest` is imported but never used (no `@pytest.mark`, no `pytest.raises`, no parametrize). This is harmless but triggers linter warnings.

#### P5 (Info): DATA_SOURCE overwrite is intentional but undocumented

The WAR fleet binary from upstream already has `DATA_SOURCE="bsee_war"` set by the rig fleet loader (`rig_fleet_loader.py:162`). The exporter unconditionally overwrites it on line 62:

```python
df["DATA_SOURCE"] = "bsee_war"
```

This is idempotent and correct (ensures the field is set regardless of input state), but a brief comment explaining the intentional overwrite would help future readers understand it's not a bug.

### Positive Observations

1. **Schema alignment**: UPPERCASE field names (`VESSEL_NAME`, `DATA_SOURCE`, `VESSEL_CATEGORY`, `IS_OFFSHORE`) match both `BaseVesselSchema` and `DrillingRigSchema` perfectly.
2. **Defensive `.copy()`**: Both the initial copy (line 40) and the post-filter copy (line 50) prevent `SettingWithCopyWarning` and avoid mutating the caller's DataFrame.
3. **Test helper design**: `_make_war_df` with all 21 base columns ensures tests produce realistic DataFrames, not minimal stubs that could mask column-interaction bugs.
4. **CLI script structure**: Clean `argparse` with sensible defaults, proper `sys.exit(main())` pattern, shebang line `#!/usr/bin/env python3`.
5. **Security**: `pickle.load` has `# nosec B301` annotation acknowledging the known Bandit warning. This is acceptable for internal-only data processing.
6. **Line counts**: 72 + 236 + 121 = 429 total lines across 3 files. All well under limits.

**Verdict**: MINOR

Two actionable findings (P1 non-string RIG_NAME, P2 pickle error handling) and two test coverage gaps (P3). None block the current use case but should be addressed before Step 2 integration.

---

## Codex CLI Review

**Model**: gpt-5.3-codex | **Session**: 019c5536-6381-74f2-8fb9-56a15c50482b

### Findings

1. **High: `RIG_NAME` type handling can crash export or emit invalid records**
   - `export_war_to_vessel_fleet` filters with `astype(str)` (`war_export.py:43`) but later applies `.str.strip()` directly (`war_export.py:56`).
   - For `RIG_NAME` as `int64`, this raises `AttributeError`; for mixed object types, non-string names become `NaN` and still get exported as `VESSEL_NAME=NaN`.
   - This violates downstream expectation that `VESSEL_NAME` is a valid string (`schemas/base.py:20`).

2. **Medium: CLI loader has uncaught failure modes on bad pickle/input errors**
   - `_load_war_fleet` does `pickle.load` without `try/except` (`export_war_to_vessel_fleet.py:45`).
   - Corrupt file, permission error, or unpickling error will crash the script instead of returning a clean exit path.

3. **Medium: Test suite misses the main robustness edge cases**
   - Missing `RIG_NAME` column (function returns `[]` but untested).
   - Non-string `RIG_NAME` values (reveals bug #1).
   - All rows filtered-out by NON RIG/null/blank combinations.
   - Script-level behavior has no tests.

**Validation notes**: Codex verified the RIG_NAME bug via direct runtime test with `python3` against `export_war_to_vessel_fleet` (int-only input crashes; mixed input exports `NaN` names).

**Verdict**: MINOR (leaning MAJOR on the type-safety bug, but mitigated by upstream guarantees)

---

## Gemini CLI Review

**Model**: Gemini CLI (YOLO mode)

### Output

> The code and tests are well-written and comprehensive.
>
> - **Correctness:** The `export_war_to_vessel_fleet` function correctly implements all specified logic, including filtering invalid entries, setting mandatory fields, and mapping `RIG_NAME` to `VESSEL_NAME`. The use of `.copy()` prevents `SettingWithCopyWarning` and ensures the original DataFrame is not mutated.
> - **Edge Cases:** The function gracefully handles empty input DataFrames and cases where the `RIG_NAME` column is missing. It correctly filters out `None`, empty strings, whitespace-only strings, and entries containing "NON RIG" in the `RIG_NAME`.
> - **Naming Conventions:** Adheres to standard Python naming conventions (snake_case for functions and variables, PascalCase for classes). Names are descriptive and clear.
> - **Test Coverage:** The test suite is highly comprehensive, covering: Mapping `RIG_NAME` to `VESSEL_NAME` and ensuring `RIG_NAME` is preserved. Correctly setting `DATA_SOURCE`, `VESSEL_CATEGORY`, and `IS_OFFSHORE`. Preservation of `RIG_TYPE` and other relevant columns. All identified filtering scenarios. Output format and behavior with an empty input DataFrame. The `_make_war_df` helper function is excellent for creating consistent test data.

**Verdict**: APPROVE

---

## Summary

| Reviewer | Verdict | Key Findings |
|----------|---------|--------------|
| Claude (Opus 4.6) | **MINOR** | P1: non-string RIG_NAME crash/NaN leak; P2: pickle error handling; P3: test gaps for 2 return paths; P4: unused pytest import |
| Codex CLI (gpt-5.3-codex) | **MINOR** | Same P1 + P2 + P3 (independently discovered + runtime-verified) |
| Gemini CLI | **APPROVE** | Clean pass; praised correctness, edge cases, test coverage |

**Consensus**: 2 MINOR, 1 APPROVE -- **MINOR** overall.

### Recommended Actions Before Step 2

1. **Fix P1**: Add `df["RIG_NAME"] = df["RIG_NAME"].astype(str)` before `.str.strip()` on line 56
2. **Fix P2**: Wrap `pickle.load` in `try/except` in the CLI script
3. **Fix P3**: Add 2 tests for missing-column and all-filtered-out paths
4. **Fix P4**: Remove unused `import pytest`
