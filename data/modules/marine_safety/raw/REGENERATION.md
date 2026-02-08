# Marine Safety Raw Data Regeneration

> Data acquisition for marine safety incident analysis across multiple sources.

## Regeneration Scripts

Two download scripts in this directory:

### 1. Primary datasets

```bash
python data/modules/marine_safety/raw/download_datasets.py
```

Downloads from: Canadian TSB, NTSB Marine, BSEE Offshore, NIOSH CFID (GitHub),
OSHA Maritime, PHMSA Pipeline, PHMSA Hazmat, IMCA DP Reports.

### 2. Industrial datasets

```bash
python data/modules/marine_safety/raw/download_industrial_datasets.py
```

Downloads additional industrial safety datasets.

## Data Sources

| Source | URL | Format | Status |
|--------|-----|--------|--------|
| Canadian TSB | tsb.gc.ca | CSV | Working |
| NTSB Marine | data.ntsb.gov/carol-main-public/api | JSON | Working |
| BSEE Offshore | data.bsee.gov | JSON/CSV | Working |
| NIOSH CFID | github.com/data-liberation-project | CSV | Working |
| PHMSA Pipelines | phmsa.dot.gov | ZIP/XLSX | Working |
| ILO Seafarer | ilostat.ilo.org | Manual | Requires registration |
| EMSA Reports | emsa.europa.eu | Manual | PDF only |
| Paris MOU | parismou.org | Manual | Requires registration |
| IMO GISIS | gisis.imo.org | Manual | Requires registration |

## Output

- Raw data in source-specific subdirectories (e.g., `canadian_tsb/`, `ntsb/`, `uscg_misle/`)
- `download_log.json` — timestamp, source, status for each attempt
- See `DOWNLOAD_STATUS_QUICK_REFERENCE.md` for current status

## Gitignored File Types

CSV, XLSX, GPKG, ZIP, and PDF files in this directory tree are gitignored
(pipeline-regenerable data). Only README/documentation files are tracked.

## Dependencies

- requests, pandas

## Expected Sizes

Total raw data: ~500-600 MB across all sources
