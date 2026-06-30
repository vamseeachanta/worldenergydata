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

Each atlas row includes cumulative oil, gas, condensate, water, BOE, first and
last production month, still-producing flag, production span, peak monthly
production, lease/operator counts, peak well count, and top-operator BOE share.

## Known Gaps

- PDQ production is lease/field/operator grain; this atlas does not allocate
  volumes to individual wells.
- Lifecycle-to-production joins remain in issue #664.
- Pipeline/GIS access metrics remain in issue #665.
- Published deep-dive reports remain in issue #666.
