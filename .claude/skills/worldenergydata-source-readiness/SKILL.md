---
name: worldenergydata-source-readiness
description: Summarize worldenergydata source readiness, freshness, data locations, and scheduler blockers from repo metadata. Use when asked for worldenergydata data completeness, latest data dates, data locations, refresh status, scheduler source health, or acceptance-criteria inputs for data-source freshness.
---

# WorldEnergyData Source Readiness

## Quick Start

From the worldenergydata repo root, run:

```bash
python .claude/skills/worldenergydata-source-readiness/scripts/source_readiness_summary.py
```

For JSON output:

```bash
python .claude/skills/worldenergydata-source-readiness/scripts/source_readiness_summary.py --format json
```

## What To Report

Use this skill to answer, in one pass:

- data group / module name
- catalog status and freshness status
- latest known date
- repo-local data location
- external data location, if metadata records one
- scheduler output location, if configured
- scheduler success manifest timestamp, if present
- dataset count, record count, file count, and data size
- blocker issue or operational gap, when known from current GitHub issue state

## Source Of Truth Order

1. `data/freshness-scorecard.json` for module-level status.
2. `data/modules/<module>/_metadata.json` for file counts, sizes, external roots, and newest file modified date.
3. `data/modules/<module>/manifest.json` for successful scheduler refresh timestamp.
4. `config/scheduler/scheduler_config.yml` for scheduler job names and output directories.
5. `data/catalog.yaml` for dataset paths and row counts.

If these disagree, state the disagreement instead of collapsing it. In particular, distinguish:

- **metadata refresh date**: when the module inventory was generated
- **newest file modified date**: newest known local file timestamp
- **scheduler success date**: when a scheduler job last completed successfully
- **source data vintage**: the newest business/date field inside the dataset; do not claim this unless inspected directly

## Acceptance Criteria Drafting Pattern

For Tier-A data-source readiness, require each source to expose:

- `source_data_latest_date`
- `last_successful_refresh`
- `data_location`
- `record_count`
- `freshness_status`
- `refresh_cadence`
- `blocker_issue` or `none`

Treat a source as green only when it has a successful scheduler manifest or another documented refresh proof within its cadence.

## Details

See [references/readiness-fields.md](references/readiness-fields.md) for field definitions and interpretation rules.
