# Texas RRC Field Atlas Reports

Issue [#666](https://github.com/vamseeachanta/worldenergydata/issues/666)
publishes onshore field-atlas reports from direct curated Texas RRC sources.

## Source Lifecycle

| Source | Refresh cycle | Required artifact |
|---|---:|---|
| Field-development metrics | After lifecycle and production atlas refresh | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/field_development/metrics/field_development_metrics.csv` |
| Infrastructure access metrics | After RRC GIS refresh and field-development metrics | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/infrastructure/access/field_infrastructure_access.csv` |
| Production atlas | Monthly, after the last Saturday PDQ refresh | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/production_field_atlas.csv` |

The report publisher is read-only against upstream sources. It does not refresh,
normalize, or rebuild lifecycle, production, or GIS artifacts.

## Command

```bash
uv run worldenergydata texas-rrc publish-field-atlas-reports --require-sources
```

Useful operator options:

```bash
uv run worldenergydata texas-rrc publish-field-atlas-reports --dry-run
uv run worldenergydata texas-rrc publish-field-atlas-reports --max-fields 100
```

Use `--allow-non-ace-output` only for isolated tests or sandbox publication.

## Published Layout

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/
  index.html
  fields/
    <district>-<field_number>-<field_slug>.html
  field_atlas_summary.csv
  field_atlas_summary.parquet
  field_atlas_report_quality.json
  manifest.json
```

The HTML files are self-contained and use no remote script or style
dependencies. The machine-readable summary carries one row per published field
page and preserves the district/field-number key used by the source artifacts.

## Caveats

- Production is sourced from the RRC PDQ production atlas. BOE uses the upstream
  atlas conversion and inherits the upstream metric gaps.
- Infrastructure access is a proximity screen to official RRC pipeline GIS
  geometry. It is not a tie-in feasibility study.
- A field without an infrastructure row is still reported with
  `infrastructure_access_class=not_available` and a
  `missing_infrastructure_access` caveat.
