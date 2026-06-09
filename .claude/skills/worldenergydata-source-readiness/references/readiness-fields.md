# Readiness Fields

## Table Columns

| Field | Meaning |
|---|---|
| `module` | worldenergydata module / data group key. |
| `catalog_status` | Declared module status from the freshness scorecard. |
| `freshness_status` | Derived freshness class from scorecard and scheduler manifest. |
| `latest_known_date` | Best available timestamp from scheduler success, metadata refresh, or newest file modified date. |
| `latest_date_basis` | Which clock produced `latest_known_date`. |
| `data_location` | Repo-local `data/modules/<module>` path. |
| `external_data_root` | External storage path from module metadata, when present. |
| `scheduler_output_dir` | Configured scheduler output directory, when present. |
| `datasets` | Dataset count from scorecard/catalog. |
| `records` | Record count from scorecard or module metadata. |
| `files` | File count from module metadata. |
| `size` | Human-readable module size from metadata. |
| `scheduler_last_success` | Last successful scheduler manifest timestamp. |

## Interpretation

- `runtime_fetched` plus `missing` usually means the source is configured or planned but lacks a repo-visible success manifest.
- `sample` means local data exists but should not be represented as full production coverage.
- `full` means catalog declares full coverage, but still verify data vintage before making buyer-facing freshness claims.
- `unknown` needs classification before acceptance criteria can be closed.
- `not_applicable` modules are infrastructure or analytical modules unless the issue explicitly scopes them as data products.

## Fast Commands

```bash
python .claude/skills/worldenergydata-source-readiness/scripts/source_readiness_summary.py
python scripts/audit/data_freshness_scorecard.py --project-root . --check --max-unknown 999
bash scripts/cron/scheduler-health.sh
```
