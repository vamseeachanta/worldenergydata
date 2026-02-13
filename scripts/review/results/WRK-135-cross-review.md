# WRK-135 Cross-Review: XLS Historical Rig Fleet Ingest

**Commit**: `eb4d2de` (worldenergydata)
**Date**: 2026-02-13
**Files reviewed**:
- `src/worldenergydata/vessel_fleet/parsers/xls.py` (17 lines changed)
- `tests/modules/vessel_fleet/parsers/test_xls.py` (80 lines added)

---

## Claude Review

**Verdict**: APPROVE (MINOR findings)

### Summary

The commit adds three parser enhancements to the XLS fleet parser: (1) `HULL_FORM_TYPE` mapping for RAO/diffraction analysis, (2) multi-word vessel type fallback logic, and (3) `RIG_NAME` field population. It also adds 10 new tests across three test classes (unit, real data integration, malformed type handling). The implementation is clean, well-scoped, and consistent with the existing codebase patterns.

### Findings

**P1 - No findings**

**P2 - Minor**

1. **Inconsistent naming between `_VESSEL_TYPE_MAP` and `_HULL_FORM_MAP`**: The vessel type map uses `"semi_submersible"` while the hull form map uses `"semi_sub"` for the same `"SS"` code. This is intentional (confirmed by schema comment `# semi_sub, drillship, jackup, barge, spar`) but could confuse future maintainers. A brief comment on the hull form map explaining the distinction (vessel classification vs hull geometry classification) would help.

2. **`HULL_FORM_TYPE` returns `None` for unknown types silently**: When `vtype_raw` is not in `_HULL_FORM_MAP` and `vtype_prefix` is also not found, the field is set to `None`. This is correct for data quality (don't guess), but there is no log message for this case. The commit message notes "1 unknown, 2 fixed" in the ingest results, suggesting some rigs do hit this path. A `logger.debug` for unmapped hull form types would aid data quality audits.

3. **`RIG_NAME` set unconditionally outside the mapping block**: Line 165 sets `record["RIG_NAME"] = rig_name` directly, whereas other fields follow the pattern of being set conditionally from `raw`. This is correct (RIG_NAME always equals rig_name from the column header) but breaks the visual pattern slightly. Minor style point only.

**P3 - Observations**

4. **Real data tests use relative path traversal**: `Path(__file__).resolve().parents[4]` traverses up 4 levels from the test file to reach the project root. This is fragile if the test file moves. However, this pattern is consistent with other tests in the codebase, so no action needed.

5. **`import math` inside test function**: `test_real_only_floater_types` imports `math` inside the function body. While PEP 8 prefers top-level imports, this is a common pattern in pytest for conditional-skip test classes and is acceptable.

6. **`parse_bool` imported but not used in diff**: The parser imports `parse_bool` from `numeric.py` but it does not appear in the changed lines. This is pre-existing (used elsewhere in the file or a leftover from prior development). Not introduced by this commit.

### Parser Correctness Assessment

- **Transposed layout**: Correctly reads row 0 as rig names, column 0 as field labels, transposes via `values.T`. Solid.
- **Field mapping**: `_FIELD_MAP` maps 23 XLS labels to schema fields. All mapped fields are processed through appropriate type conversion (numeric, integer, dimension pair, boolean).
- **Unit conversion**: FT_TO_M = 0.3048 applied to LOA, BEAM, DRAFT, MOONPOOL dimensions. BOP Ksi to PSI via * 1000. All correct.
- **Multi-word fallback**: Two-stage lookup (`vtype_raw` exact match, then `vtype_prefix` first-word match) is a clean, defensive approach. Handles "SS F&G 9500" and "DS Gusto, MSC Bully PRD" correctly.
- **Hull form mapping**: Separate `_HULL_FORM_MAP` with only two entries (`SS` -> `semi_sub`, `DS` -> `drillship`) is appropriate since the XLS dataset only contains floaters. Aligns with schema enum values.

### Test Coverage Assessment

- **Unit tests (TestXlsFleetParser)**: 15 tests covering all field types (vessel name, rig type, water depth, year, LOA conversion, DP class, moonpool compound, BOP pressure, data source, offshore flag, hull form type, rig name). Good breadth.
- **Real data tests (TestXlsRealData)**: 5 integration tests with graceful skip when parquet not present. Tests count (>= 150), hull form type population (>= 140), rig name consistency, LOA population, and type constraints. Good data quality assertions.
- **Malformed type tests (TestXlsFleetParserMalformedTypes)**: 2 tests with dedicated fixture creating XLS files with multi-word vessel type codes. Directly validates the new fallback logic. Correct and sufficient.
- **Total**: 22 tests, covering the three new features plus pre-existing functionality.

---

## Codex CLI Review

**Verdict**: APPROVE (no actionable findings)

**Tool**: Codex CLI v0.98.0, model gpt-5.3-codex

**Output**:

> I did not identify any discrete, actionable regressions introduced by this commit in the parser logic or accompanying tests. The changes appear consistent with the stated behavior improvements for vessel type normalization and added compatibility fields.

**Automated checks performed by Codex**:
- Inspected commit diff via `git show --name-only --oneline eb4d2de`
- Read full parser file (`xls.py`, 243 lines)
- Compared prior file version for the `_map_row` method
- Read full test file (205 lines)
- Searched codebase for `HULL_FORM_TYPE`, `RIG_NAME`, `RIG_TYPE` usage across all source files
- Verified schema field declarations in `drilling_rig.py`
- Attempted to run tests (failed due to conftest.py venv issue, not a code defect)
- Assessed hull form mapping gaps

---

## Gemini CLI Review

**Verdict**: APPROVE

**Tool**: Gemini CLI (google-gemini)

**Findings**:

1. **Parser Correctness**: The parsing logic for `RIG_TYPE` and `HULL_FORM_TYPE` has been enhanced to correctly handle multi-word vessel type entries by extracting a prefix for mapping. The `RIG_NAME` field is also correctly populated.

2. **Hull Form Type Mapping**: A new `_HULL_FORM_MAP` dictionary is introduced and correctly utilized to assign `HULL_FORM_TYPE` based on the vessel type code, including the multi-word fallback mechanism.

3. **Multi-word Vessel Type Fallback**: The implementation of splitting `vtype_raw` to get `vtype_prefix` and then using it as a fallback for both `_VESSEL_TYPE_MAP` and `_HULL_FORM_MAP` is correct and robust, addressing the requirement for malformed multi-word entries.

4. **Test Coverage**: New unit tests directly verify the new fields. Integration test suite provides excellent coverage against real-world data. Dedicated malformed-type test class explicitly validates the multi-word fallback logic.

---

## Cross-Review Summary

| Reviewer | Verdict | Findings |
|----------|---------|----------|
| Claude Opus 4.6 | APPROVE (MINOR) | 3 minor, 3 observations |
| Codex CLI (gpt-5.3-codex) | APPROVE | No actionable findings |
| Gemini CLI | APPROVE | 4 positive findings, no issues |

**Consensus**: 3/3 APPROVE. No blocking issues identified. Two minor suggestions from Claude review (add comment distinguishing hull form vs vessel type naming, add debug logging for unmapped hull form types) are recommended but not required.

**Reviewers**: 3 (meets minimum threshold per CLAUDE.md cross-review policy)
