# Plan: Issue #366 — HSE bulk deduplication + ingest pipeline

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/366
**Status:** plan-review
**Tier:** T3 (large-data ingest pipeline)
**Data location:** `/mnt/ace/worldenergydata/data/modules/hse/raw/`

## Context
6.8 GB of HSE data at `/mnt/ace`:
- OSHA violations: 11 fragmented CSVs (91–163 MB each), ~7M rows, oil & gas subset
- Freshness: 2026-02-10 (stale)

## Plan

### Task 1 — Inventory and assess data quality
```bash
for f in /mnt/ace/worldenergydata/data/modules/hse/raw/osha_violation*.csv; do
  echo "$f: $(wc -l < $f) rows"
done
```
Identify duplicate rows, overlapping date ranges, and column schemas.

### Task 2 — Write `scripts/ingest/hse_bulk_ingest.py`
Steps:
1. Read all 11 fragmented CSVs into a single DataFrame (streaming to avoid OOM)
2. Deduplicate on `(violation_id, establishment_id, citation_date)`
3. Filter to NAICS codes: `213112`, `213111`, `211111` (oil & gas)
4. Write chunked Parquet to `data/modules/hse/osha_violations_YYYYMMDD.parquet`

### Task 3 — Target ingest size
Goal: ≤500 MB Parquet after dedup + oil-gas filter.
Use `fastparquet` or `pyarrow` with compression.

### Task 4 — Register in data/catalog.yaml
Add HSE entries:
```yaml
  - module: hse
    dataset: osha_violations
    path: data/modules/hse/osha_violations_YYYYMMDD.parquet
    rows: <count>
    last_refresh: 2026-02-10
    catalog_status: full
```

### Task 5 — Wire into HSE query API (#363)
Once ingested, `HSEIncidentsQuery.query(source="osha")` should read from Parquet.

## Acceptance Criteria
- Deduplicated Parquet file exists at `data/modules/hse/osha_violations_*.parquet`
- Row count and dedup stats documented in script output
- Requires `/mnt/ace` to be mounted (documented in script header)
- `data/catalog.yaml` updated
