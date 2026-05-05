# Plan: Issue #365 — BSEE binary tier decompression + ingest pipeline

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/365
**Status:** plan-review
**Tier:** T3 (new ingest pipeline for local data)
**Data location:** `/mnt/ace/worldenergydata/data/modules/bsee/{bin,zip}/`

## Context
2.7 GB of BSEE binary/zip data at `/mnt/ace` is not queryable. Key files:
- `BoreholeRawData.zip` (3.5 MB) + extracted txt (13.6 MB)
- `eWellWARRawData.zip` (127.9 MB) + decompressed pkl (6 MB)
- `rig_fleet_full.bin` (422 KB)

## Plan

### Task 1 — Inventory and document binary formats
```bash
ls /mnt/ace/worldenergydata/data/modules/bsee/bin/ 2>/dev/null | head -20
ls /mnt/ace/worldenergydata/data/modules/bsee/zip/ 2>/dev/null | head -20
```
For each archive, identify format and expected schema.

### Task 2 — Write `scripts/ingest/bsee_binary_ingest.py`
For each binary/zip tier:
- Decompress to `data/modules/bsee/{tier}/` (in-repo)
- Parse to DataFrame (CSV/Parquet)
- Write timestamped output: `data/modules/bsee/borehole/YYYYMMDD.csv`

### Task 3 — Ingest BoreholeRawData
```python
import zipfile, pandas as pd
with zipfile.ZipFile("/mnt/ace/.../BoreholeRawData.zip") as z:
    with z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, sep="\t")
df.to_csv("data/modules/bsee/borehole/YYYYMMDD.csv", index=False)
```

### Task 4 — Ingest eWellWAR data
Parse the `.pkl` file (Python pickle) to DataFrame, write to CSV/Parquet.

### Task 5 — Register in data/catalog.yaml
Add entries for new ingested datasets with row counts and timestamps.

## Acceptance Criteria
- `data/modules/bsee/borehole/` and `data/modules/bsee/war/` contain ingested CSV files
- `data/catalog.yaml` updated with new entries
- Script runs idempotently (re-run overwrites with fresh data)
- Requires `/mnt/ace` to be mounted (document in script header)
