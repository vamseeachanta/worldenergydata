# Texas RRC Production Field Atlas

The Texas RRC production field atlas summarizes official Production Data Query
(`production_pdq`) snapshots into field, lease, district, operator, and
statewide production rollups for onshore field-development analysis.

## Source Of Record

The atlas uses the direct Texas RRC PDQ dump from the source catalog:

| Source | Refresh cycle | Raw path | Curated path |
| --- | --- | --- | --- |
| `production_pdq` | Monthly, after the last Saturday | `/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/production/pdq` | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas` |

PatchOps and EWA remain validation surfaces only. They are not durable atlas
inputs.

## Command

Refresh the official PDQ raw snapshot first:

```bash
uv run worldenergydata texas-rrc refresh --source production_pdq
```

Build the atlas from local raw snapshots:

```bash
uv run worldenergydata texas-rrc build-production-atlas
```

Use `--dry-run` to inspect row counts without writing outputs:

```bash
uv run worldenergydata texas-rrc build-production-atlas --dry-run
```

Sandbox runs must opt into non-ACE output roots:

```bash
uv run worldenergydata texas-rrc build-production-atlas \
  --raw-root /tmp/texas_rrc \
  --output-root /tmp/texas_rrc \
  --allow-non-ace-output
```

## Output Contract

The command writes:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/
+-- production_field_atlas.csv
+-- production_field_atlas.parquet
+-- production_field_atlas_quality.json
+-- manifest.json
```

Each atlas row includes cumulative oil, gas, condensate, BOE, first and last
production month, still-producing flag, production span, peak monthly
production, lease/operator counts, and top-operator BOE share. The
`still_producing` flag uses the latest filed positive production month; future
scheduled cycles with `PROD_REPORT_FILED_FLAG = N` do not move the active
production horizon.

`cumulative_water_bbl` and `well_count_peak` remain stable output columns, but
the preferred direct RRC member (`OG_LEASE_CYCLE_DATA_TABLE.dsv`) does not
include water or well-count fields. Those values are emitted as nulls for the
direct PDQ build and are reported in `production_field_atlas_quality.json` under
`metric_gaps`.

## Known Gaps

- PDQ production is lease/field/operator grain; this atlas does not allocate
  volumes to individual wells.
- The direct PDQ production member does not provide water production or well
  count; those atlas metrics are nullable and flagged as metric gaps.
- Lifecycle-to-production joins remain in issue #664.
- Pipeline/GIS access metrics remain in issue #665.
- Published deep-dive reports remain in issue #666.
