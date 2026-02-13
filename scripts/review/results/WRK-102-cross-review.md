# WRK-102 Cross-Review: Hull Form Classification and Dimension Estimation

**Commit**: `22e66dd` (worldenergydata)
**Date**: 2026-02-13
**Files reviewed**:
- `src/worldenergydata/vessel_hull_models/rig_hulls/hull_form_mapper.py` (121 lines)
- `src/worldenergydata/vessel_hull_models/rig_hulls/hull_estimator.py` (236 lines)
- `src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py` (126 lines)
- `tests/modules/vessel_hull_models/rig_hulls/test_hull_form_mapper.py` (157 lines)
- `tests/modules/vessel_hull_models/rig_hulls/test_hull_estimator.py` (129 lines)
- `tests/modules/vessel_hull_models/rig_hulls/test_hull_loader.py` (98 lines)
- `scripts/vessel_fleet/fuse_and_deduplicate.py` (diff: +12 lines)
- `scripts/vessel_fleet/populate_hull_forms.py` (73 lines)
- `data/modules/vessel_hull_models/csv/rig_hulls/sample_rigs.csv` (6 lines)

**Total**: 958 insertions across 12 files, 53 unit tests

---

## Claude Review

**Verdict**: MINOR

### Strengths

1. **Clean architecture**: The three-module split (mapper, estimator, loader) follows single-responsibility principle well. Each module has a clear, focused purpose.

2. **RIG_TYPE to HULL_FORM_TYPE mapping correctness**: All 7 vessel rig types map to the correct hydrodynamic hull form. The engineering rationale is sound:
   - `submersible` -> `semi_sub`: Correct, submersible drilling rigs use semi-submersible hull geometry.
   - `tender_assisted` -> `semi_sub`: Correct, tender-assist drilling typically occurs on semi-sub hulls.
   - `lift_boat` -> `jackup`: Correct, lift boats are self-elevating vessels in the jackup family.
   - Non-vessel types (platform_rig, land_rig, etc.) correctly excluded.

3. **Engineering soundness of dimension estimates**: The water-depth-refined brackets for drillships (190m/228m/238m LOA) and semi-subs (85m/104m/120m LOA) are reasonable industry-representative values. The drillship generic draft of 12m and semi-sub operating draft of 21m align with public fleet data.

4. **Confidence level system**: The measured/estimated/generic tiering is a strong data quality pattern that enables downstream consumers to filter by data reliability.

5. **Immutability**: All DataFrame-operating functions return copies, never modifying inputs. Tests explicitly verify this.

6. **Test quality**: Tests follow Arrange-Act-Assert, cover edge cases (None, NaN, empty strings, case insensitivity), and verify immutability. The loader tests use `tmp_path` fixtures with parquet files -- proper integration tests without external dependencies.

7. **Legal compliance**: No client references, proprietary tool names, or denied terms found. Sample CSV cites only public sources (fleet pages, class records, Offshore Magazine).

8. **No security issues**: No hardcoded secrets, no file path injection vectors, proper use of `logging.getLogger(__name__)`.

### Findings

#### P2: HULL_LIBRARY_REF becomes stale after dimension estimation

**File**: `hull_form_mapper.py:92-101` / `hull_loader.py:53-54` / `fuse_and_deduplicate.py:80-85`

`HULL_LIBRARY_REF` is assigned in `populate_hull_forms()` before `populate_estimated_dimensions()` fills in LOA_M. For rigs that start with no dimensions, the ref is set to `{hull_form}_generic` and never updated when LOA_M is later estimated. Verified:

```
After populate_hull_forms:   drillship_generic  LOA_M=None
After populate_estimated:    drillship_generic  LOA_M=238.0   <-- stale ref
```

**Fix**: Either (a) move HULL_LIBRARY_REF assignment to a separate function called after dimension estimation, or (b) have `populate_estimated_dimensions` update the ref when it fills LOA_M.

#### P2: Sample CSV has misaligned columns (3 of 5 data rows)

**File**: `data/modules/vessel_hull_models/csv/rig_hulls/sample_rigs.csv` (rows 3, 4, 6)

Header has 19 columns but rows for DEEPWATER PROTEUS, VALARIS DS-17, and ROWAN GORILLA VI have 20 fields. The extra empty field shifts `DIMENSION_CONFIDENCE` and `SOURCE_CITATION` by one position:

```
Column 17 (DIMENSION_CONFIDENCE) = ""        <-- should be "measured"
Column 18 (SOURCE_CITATION)      = "measured" <-- should be the citation text
Column 19 (EXTRA)                = citation   <-- orphaned
```

The issue is drillships and the jackup have no pontoon/column fields but an extra comma appears in the empty field sequence. Rows for semi-subs (which populate `COLUMN_SPACING_M` and `COLUMN_COUNT`) parse correctly.

#### P3: Partial dimension case leaves DIMENSION_CONFIDENCE as None

**File**: `hull_estimator.py:185-200`

When a rig has some but not all of LOA_M/BEAM_M/DRAFT_M present, the logic skips estimation (correct) but also does not set DIMENSION_CONFIDENCE to "measured" (line 185-189 requires all three to be not-null). This means rigs with e.g. only LOA_M measured get `None` confidence instead of "partial" or "measured". Not blocking but worth documenting or handling.

#### P3: Spar hull form unreachable from mapper

**File**: `hull_estimator.py:60-67` / `hull_form_mapper.py:19-27`

`_HULL_DEFAULTS` includes `spar` dimensions, but no RIG_TYPE maps to `spar` in `_RIG_TYPE_TO_HULL_FORM`. The spar estimate is only reachable if `HULL_FORM_TYPE` is manually set to "spar" (e.g., from XLS data). This is acceptable for now but worth a comment explaining the asymmetry.

#### P4: Inline import in fuse_and_deduplicate.py

**File**: `scripts/vessel_fleet/fuse_and_deduplicate.py:78`

`import pandas as pd` is done inline inside the `if drilling:` block, despite pandas already being used by the surrounding code (dedup, validation). Should use the existing top-level import.

#### P4: LOA_M bucket rounding for spar (loa_m=None)

**File**: `hull_form_mapper.py:117-121`

The spar default has `loa_m=None` (spars are vertical cylinders, LOA is not the conventional dimension). If a spar row exists with `HULL_FORM_TYPE="spar"` and no LOA_M, the ref will be `spar_generic`. This is correct behavior but deserves a brief comment explaining why spar LOA is intentionally None.

---

## Codex Review

**Verdict**: MINOR (2 findings)

**Reviewer**: OpenAI Codex v0.98.0, model gpt-5.3-codex

### Findings

1. **[P2] HULL_LIBRARY_REF stale after dimension estimation** (`hull_form_mapper.py:95-99`): `populate_hull_forms` assigns `HULL_LIBRARY_REF` as `*_generic` before `populate_estimated_dimensions` fills in `LOA_M`. Rigs that receive estimated dimensions keep the permanently generic ref instead of the correct bucket key (e.g., `jackup_generic` instead of `jackup_70m`).

2. **[P2] Sample CSV rows misaligned** (`sample_rigs.csv:3`): Header declares 19 columns but 3 data rows contain 20 fields due to extra comma in the empty pontoon/column field sequence. This shifts `DIMENSION_CONFIDENCE` and `SOURCE_CITATION` columns.

---

## Gemini Review

**Verdict**: APPROVE

**Reviewer**: Gemini CLI (Google)

Gemini found the implementation correct across all four review criteria:
- RIG_TYPE to HULL_FORM_TYPE mapping is complete and accurate
- Dimension estimation is engineering-sound with appropriate depth-based refinement
- Test coverage is comprehensive with good edge case handling
- HULL_LIBRARY_REF naming convention correctly implemented with rounding

No findings raised.

---

## Summary

| Reviewer | Verdict | Findings |
|----------|---------|----------|
| Claude Opus 4.6 | MINOR | 2x P2, 2x P3, 2x P4 |
| Codex (gpt-5.3-codex) | MINOR | 2x P2 |
| Gemini CLI | APPROVE | None |

**Overall assessment**: MINOR -- approve with recommended fixes.

The implementation is well-structured, correctly maps all 7 vessel rig types to their hydrodynamic hull forms, and provides sound engineering estimates for hull dimensions. The confidence-level system is a strong data quality feature. Test coverage at 53 tests across 3 modules is thorough.

Two P2 issues should be addressed in a follow-up:

1. **HULL_LIBRARY_REF stale reference** (confirmed by Claude + Codex): After the full pipeline runs, rigs that received estimated dimensions still carry `*_generic` refs. This affects ~1,475 rigs (the "generic" dimension tier). Fix by re-computing the ref after dimension estimation.

2. **Sample CSV column misalignment** (confirmed by Claude + Codex): 3 of 5 data rows have an extra comma, shifting DIMENSION_CONFIDENCE and SOURCE_CITATION. Fix by removing the extra empty field in drillship and jackup rows.

Neither issue blocks the core functionality, and both are straightforward fixes. The commit is approved for merge with these recommended follow-up corrections.

**Reviewers attempted**: 3 (Claude, Codex, Gemini) -- minimum met.
