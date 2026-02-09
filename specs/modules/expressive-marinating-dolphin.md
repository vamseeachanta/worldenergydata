---
title: "WRK-104: Expand Drilling Rig Fleet Dataset"
description: "Expand rig fleet from 16 WAR-sample rigs to comprehensive GOM coverage using full BSEE WAR download"
version: "1.0"
module: bsee/data/loaders/rig_fleet
session:
  id: expressive-marinating-dolphin
  agent: claude-opus-4-6
review:
  status: implemented
  implemented_at: "2026-02-08"
  test_results: "109 passed, 0 failed"
---

# WRK-104: Expand Drilling Rig Fleet Dataset

## Context

The rig fleet dataset currently contains **16 rigs** extracted from a 100-row WAR sample CSV. The full BSEE WAR dataset (`eWellWARRawData.zip`, ~120MB) contains decades of drilling activity records with hundreds of unique rig names. We will download the full WAR via the existing `BSEEWebScraper` infrastructure, extract all unique rigs, and rebuild the fleet binary.

**Scope**: Offshore rigs (BSEE jurisdiction) with `LAND_RIG` enum stub for future onshore support.

## Implementation Plan

### Phase 1: Enum & Classifier Expansion
**File**: `src/worldenergydata/bsee/data/loaders/rig_fleet/constants.py`

1. Add `LAND_RIG = "land_rig"` to `RigType` enum
2. Add `DataSource` enum: `BSEE_WAR`, `MANUAL_OVERRIDE`, `XLS_HISTORICAL`, `UNKNOWN`
3. Expand `classify_rig_type()` keyword tuples:
   - Drillship: add `NOBLE GLOBETROTTER`, `PACIFIC`, `COBALT`, `BULLY`, `T.O.` prefix handling
   - Semi-sub: add `TRANSOCEAN`, `NAUTILUS`, `SEDCO`, `SCARABEO`, `MAERSK`
   - Jack-up: add `HERCULES`, `KEY SINGAPORE`, `KEY MANHATTAN`, `SEAHAWK`, `CECIL PROVINE`, `SUNDOWNER`
   - Platform: add `NABORS`, `HELMERICH`, `H&P`, `PARKER`, `FLEX RIG`
   - Inland barge: add `INLAND`, `BARGE`
4. Refactor classifier to use prefix-priority matching (longest prefix wins) to avoid ambiguous names

**Tests first** (`tests/modules/bsee/data/loaders/rig_fleet/test_constants.py`):
- Update enum count assertion (9 rig types)
- Add `DataSource` enum tests
- Add parametrized classifier test with ~25 known rig names

### Phase 2: Schema & Model Extension
**Files**:
- `src/worldenergydata/bsee/data/schemas/rig_fleet.py`
- `src/worldenergydata/bsee/data/models/rig_fleet.py`

Add fields:
- `DATA_SOURCE: Optional[str] = None`
- `IS_OFFSHORE: Optional[bool] = None`
- `FIRST_WAR_DATE: Optional[str] = None`
- `LAST_BLOCK_NUMBER: Optional[str] = None`
- `MAX_WATER_DEPTH_FT: Optional[float] = None`

Model additions:
- `is_offshore_derived` property (uses explicit flag, falls back to rig_type != land_rig)
- Update `_RIG_TYPE_DISPLAY_MAP` with `"land_rig": "Land Rig"`

**Tests first** (`test_rig_fleet_schema.py`, `test_rig_fleet_model.py`):
- Validate new fields coerce/validate correctly
- Test `is_offshore_derived` property

### Phase 3: WAR Data Acquirer
**New file**: `src/worldenergydata/bsee/data/loaders/rig_fleet/war_acquirer.py` (~120 lines)

```
WARDataAcquirer
  __init__(scraper, processor)   # DI for testability
  acquire_war_dataframe() -> DataFrame  # download + extract + merge + normalize
  _normalize_columns(df) -> DataFrame   # BOTM_AREA_CODE -> AREA_CODE etc.
```

Uses existing:
- `BSEEWebScraper` at `src/worldenergydata/bsee/data/scrapers/bsee_web.py` (line 27: WAR URL)
- `MemoryProcessor` at `src/worldenergydata/bsee/data/processors/`

**Tests first** (`tests/modules/bsee/data/loaders/rig_fleet/test_war_acquirer.py`):
- Test column normalization with mock DataFrame
- Test acquire with injected mock scraper/processor

### Phase 4: Loader Updates
**File**: `src/worldenergydata/bsee/data/loaders/rig_fleet/rig_fleet_loader.py`

Update `build_fleet_from_war()`:
- Add `FIRST_WAR_DATE` aggregation (`WAR_START_DT: min`)
- Add `MAX_WATER_DEPTH_FT` aggregation (`WATER_DEPTH: max`) if column present
- Set `DATA_SOURCE = "bsee_war"` on all rows
- Set `IS_OFFSHORE = True` on all BSEE WAR rows

Add method:
- `get_rigs_by_offshore_status(is_offshore, cfg)` for filtering

**Tests first** (`test_rig_fleet_loader.py`):
- Test new aggregation columns
- Test DATA_SOURCE / IS_OFFSHORE auto-set
- Test offshore status filter
- Existing tests unchanged

### Phase 5: Build Script Rewrite
**File**: `scripts/build_rig_fleet_from_war.py`

Changes:
1. Fix import: `worldenergydata.modules.bsee...` -> `worldenergydata.bsee...`
2. Add `--source` arg: `download` (default, uses WARDataAcquirer) vs `local` (reads CSV)
3. Add `--dry-run` flag
4. Apply overrides after fleet build
5. Save `rig_fleet_metadata.json` alongside .bin with build stats
6. Print "unknown rigs" report for override CSV expansion

### Phase 6: Expand Override CSV
**File**: `data/modules/bsee/bin/rig_fleet/rig_type_overrides.csv`

After running build script with full WAR data:
- Classify all unknown rigs manually
- Add `NOTES` column for documentation
- Expected growth: 8 -> 50-100 rows

## Critical Files

| File | Action |
|------|--------|
| `src/worldenergydata/bsee/data/loaders/rig_fleet/constants.py` | Modify |
| `src/worldenergydata/bsee/data/loaders/rig_fleet/rig_fleet_loader.py` | Modify |
| `src/worldenergydata/bsee/data/loaders/rig_fleet/war_acquirer.py` | **New** |
| `src/worldenergydata/bsee/data/schemas/rig_fleet.py` | Modify |
| `src/worldenergydata/bsee/data/models/rig_fleet.py` | Modify |
| `scripts/build_rig_fleet_from_war.py` | Modify |
| `data/modules/bsee/bin/rig_fleet/rig_type_overrides.csv` | Modify |
| `tests/modules/bsee/data/loaders/rig_fleet/test_constants.py` | Modify |
| `tests/modules/bsee/data/loaders/rig_fleet/test_rig_fleet_schema.py` | Modify |
| `tests/modules/bsee/data/loaders/rig_fleet/test_rig_fleet_model.py` | Modify |
| `tests/modules/bsee/data/loaders/rig_fleet/test_rig_fleet_loader.py` | Modify |
| `tests/modules/bsee/data/loaders/rig_fleet/test_war_acquirer.py` | **New** |

## Reuse Existing Code

- `BSEEWebScraper.download()` (bsee_web.py:24-33) for WAR zip download
- `MemoryProcessor` for in-memory zip extraction
- `RigFleetLoader.build_fleet_from_war()` core aggregation logic (extend, don't rewrite)
- `RigFleetLoader.load_overrides()` unchanged

## Dependency Order

```
Phase 1 (enums + classifier) ─┐
Phase 2 (schema + model) ─────┤── can run in parallel
Phase 3 (WAR acquirer) ───────┘
         │
Phase 4 (loader updates) ── depends on 1,2,3
         │
Phase 5 (build script) ── depends on 4
         │
Phase 6 (overrides) ── depends on running build script
Phase 7 (.local/ storage + gitignore) ── integrate into phases 3,4,5
```

## Verification

1. `uv run pytest tests/modules/bsee/data/loaders/rig_fleet/ -v` -- all tests pass
2. `uv run python scripts/build_rig_fleet_from_war.py --source download` -- downloads full WAR, builds fleet
3. Verify `rig_fleet.bin` contains 200+ rigs (vs current 16)
4. Verify `rig_fleet_metadata.json` has accurate stats
5. Review unknown rigs list, update overrides, rebuild
6. `uv run pytest` -- full test suite passes

## Phase 7: Local Data Storage (No Git Sync)

The full WAR download (~120MB compressed, multi-GB uncompressed) and rebuilt rig fleet binary must live on local disk but NOT be tracked by git. This prevents heavy git operations while keeping data accessible.

### Strategy: `.local/` Data Directory

**New directory**: `data/modules/bsee/.local/` (gitignored)

```
data/modules/bsee/.local/
  war/
    eWellWARRawData.zip           # cached download
    mv_war_main.txt               # extracted
    mv_war_main_prop.txt          # extracted
    download_metadata.json        # when, size, checksum
  rig_fleet/
    rig_fleet_full.bin            # full fleet pickle (replaces bin/rig_fleet.bin for local use)
    rig_fleet_metadata.json       # build stats
```

**Gitignore additions** (`.gitignore`):
```
# Local data - not synced to git (large files, downloaded on demand)
data/modules/bsee/.local/
```

**Loader changes**: `RigFleetLoader._load_data()` checks `.local/rig_fleet/` first, falls back to `bin/rig_fleet/` (the committed sample). This way:
- Git repo keeps the small 16-rig sample as a working fallback
- Local machines that run the build script get the full fleet from `.local/`
- No large files in git history

**Build script changes**: Output goes to `.local/rig_fleet/` by default (not `bin/rig_fleet/`)

**WAR acquirer caching**: After downloading, save the zip to `.local/war/` with metadata. On next run, check if cached zip exists and is < 30 days old; skip download if so.

### Data Index Manifest

**New file**: `data/modules/bsee/.local/data_index.json` (gitignored, auto-generated)

```json
{
  "generated_at": "2026-02-08T12:00:00Z",
  "datasets": {
    "war_raw": {
      "path": "data/modules/bsee/.local/war/eWellWARRawData.zip",
      "size_bytes": 125000000,
      "downloaded_at": "2026-02-08T11:30:00Z",
      "source_url": "https://www.data.bsee.gov/Well/Files/eWellWARRawData.zip",
      "checksum_sha256": "abc123...",
      "record_count": 3500000
    },
    "rig_fleet_full": {
      "path": "data/modules/bsee/.local/rig_fleet/rig_fleet_full.bin",
      "size_bytes": 45000,
      "built_at": "2026-02-08T12:00:00Z",
      "built_from": "war_raw",
      "rig_count": 450
    }
  }
}
```

The build script auto-updates this index. The loader can read it to report what data is available.

## Updated Critical Files

Add to the table:

| File | Action |
|------|--------|
| `.gitignore` | Modify (add `.local/` pattern) |
| `src/worldenergydata/bsee/data/loaders/rig_fleet/rig_fleet_loader.py` | Modify (`.local/` fallback) |
| `src/worldenergydata/bsee/data/loaders/rig_fleet/war_acquirer.py` | Modify (cache to `.local/war/`) |

## Notes

- Full WAR download takes ~10-40 minutes (120MB). Tests use synthetic data, never real download.
- The WAR zip is cached in `.local/war/` with 30-day freshness check, avoiding repeated downloads.
- Git repo stays lean: only sample data + overrides + code are committed. Full data is local-only.
- A general-purpose "data indexing" system across all modules should be a separate WRK item. This plan adds a lightweight per-module `data_index.json`.
