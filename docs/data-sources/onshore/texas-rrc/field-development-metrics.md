# Texas RRC Field Development Metrics

Texas RRC field-development metrics join the curated well lifecycle spine with
the field-level production atlas. The output is the onshore analog to the BSEE
field-development workflow: one row per RRC district and field number, with well
counts, lifecycle timing, production maturity, remaining activity, and ranking
features for later field architecture work.

## Source Of Record

The command uses direct Texas RRC source-derived artifacts only.

| Input | Upstream source | Refresh cycle | Curated path |
| --- | --- | --- | --- |
| Lifecycle spine | `wellbore_query`, `drilling_permits`, `completion_data` | Monthly for wellbore query; nightly for permits and completions | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/well_lifecycle/spine` |
| Production atlas | `production_pdq` | Monthly, after the last Saturday | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas` |

PatchOps, EWA web forms, and third-party scraper code remain validation
surfaces only. They are not durable inputs for this output.

## Command

Build or refresh upstream direct-source artifacts first:

```bash
uv run worldenergydata texas-rrc refresh --source wellbore_query
uv run worldenergydata texas-rrc refresh --source drilling_permits
uv run worldenergydata texas-rrc refresh --source completion_data
uv run worldenergydata texas-rrc refresh --source production_pdq
uv run worldenergydata texas-rrc normalize-lifecycle --require-sources
uv run worldenergydata texas-rrc build-production-atlas --require-sources
```

Then build the field-development metrics:

```bash
uv run worldenergydata texas-rrc build-field-development-metrics --require-sources
```

Use `--dry-run` to inspect row counts and source gaps without writing outputs:

```bash
uv run worldenergydata texas-rrc build-field-development-metrics --dry-run
```

If curated lifecycle or production artifacts are missing but local raw snapshots
already exist, the command can rebuild those prerequisites without touching the
network:

```bash
uv run worldenergydata texas-rrc build-field-development-metrics \
  --build-missing-lifecycle \
  --build-missing-production \
  --require-sources
```

Sandbox runs must explicitly opt into non-ACE output roots:

```bash
uv run worldenergydata texas-rrc build-field-development-metrics \
  --root /tmp/texas_rrc \
  --output-root /tmp/texas_rrc_out \
  --allow-non-ace-output
```

## Output Contract

The command writes:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/field_development/metrics/
+-- field_development_metrics.csv
+-- field_development_metrics.parquet
+-- field_development_metrics_quality.json
+-- manifest.json
```

Writes are staged under `.staging-field-development-metrics-*` before
promotion. By default, writes outside
`/mnt/ace/worldenergydata/data/modules/texas_rrc` are rejected.

## Metrics

Stable output columns include district and field identifiers, well count,
active and plugged well counts, permit and completion counts, horizontal and
directional well counts, drilling-to-completion timing, production start and end
months, cumulative oil, gas, condensate, and BOE, production per well, lease and
operator counts, top operator share, maturity class, remaining activity score,
well density proxy, rank columns, source caveats, and quality flags.

Ranking columns are:

- `rank_cumulative_boe`
- `rank_remaining_activity`
- `rank_well_density_proxy`
- `rank_development_maturity`

`well_density_proxy` is `well_count / lease_count` with
`well_density_basis = wells_per_lease`. It is not a surface-acreage density.

## Known Caveats

- PDQ production is lease and field grain; this output does not allocate
  production volumes to individual wells.
- Fields with lifecycle rows but no production atlas row carry
  `missing_production`.
- Fields with production atlas rows but no lifecycle row carry
  `missing_lifecycle`.
- `water_and_well_count_unavailable_from_pdq` is preserved from the production
  atlas quality contract when the direct PDQ member does not expose those
  values.
- Pipeline proximity, GIS acreage density, field economics, reserves, and
  published field reports remain separate follow-on scopes.
