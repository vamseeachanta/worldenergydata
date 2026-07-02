# Texas RRC Field Opportunity Ranking

## Purpose

The field-opportunity ranking turns the Texas RRC field atlas into a deterministic
screening table for onshore field-development review. It ranks fields by direct
source-derived production scale, remaining activity, infrastructure access,
operator context, and quality/caveat penalties.

This output is a screening heuristic. It is not a reserves estimate, economics
model, tariff study, pipeline capacity study, right-of-way assessment, or
engineered facility design.

## Source Lifecycle

The ranking consumes curated outputs produced from official Texas RRC direct
sources under `/mnt/ace/worldenergydata/data/modules/texas_rrc`:

1. Raw Texas RRC snapshots are refreshed with `worldenergydata texas-rrc refresh`.
2. Lifecycle, production, and GIS-derived infrastructure artifacts are built
   into curated datasets.
3. `publish-field-atlas-reports` creates the field-atlas summary and per-field
   HTML pages.
4. `build-field-opportunities` consumes the field-atlas summary and upstream
   manifests to publish ranked opportunity outputs.

PatchOps is validation-only and is not a durable input dependency.

## Refresh Cadence

Refresh cadence is inherited from the Texas RRC source catalog and the upstream
commands:

- PDQ production and lifecycle sources refresh through the direct Texas RRC
  raw-refresh contract.
- RRC GoDrive GIS directory sources follow the cataloged directory refresh
  policy and official RRC availability.
- The opportunity ranking should be rebuilt after any upstream lifecycle,
  production, infrastructure, or field-atlas refresh.

## Command

```bash
uv run --no-sync worldenergydata texas-rrc build-field-opportunities \
  --root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --require-sources
```

For bounded smoke runs:

```bash
uv run --no-sync worldenergydata texas-rrc build-field-opportunities \
  --root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --require-sources \
  --max-fields 100
```

## Output Contract

Outputs are written to:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/
  field_opportunity_rankings.csv
  field_opportunity_rankings.parquet
  field_opportunity_summary.html
  field_opportunity_quality.json
  manifest.json
```

The ranking is keyed by `district, field_number`. The manifest records input
paths, upstream manifests, source gaps, scoring version, scoring weights, output
paths, row count, command, and code revision.

## Scoring

The current scoring version is `texas_rrc_field_opportunity_v1`.

```text
opportunity_score =
  0.35 * production_scale_component_score
  + 0.30 * remaining_activity_component_score
  + 0.20 * infrastructure_component_score
  + 0.10 * operator_concentration_component_score
  + 0.05 * active_well_component_score
  - quality_penalty_score
```

Scores are clamped to `0..100`. Component scores normalize upstream ratios or
percent values to a `0..100` scale while preserving the raw source columns such
as `remaining_activity_score` and `infrastructure_access_score`. Component
scores are retained so downstream review can inspect why a field ranked where
it did. Missing or low-confidence source evidence remains visible through
`source_caveats`, `quality_flags`, and `quality_penalty_score`.

## Architecture Signals

The architecture signal classes are screening labels:

- `high_access_infill_redevelopment`
- `infrastructure_constrained_activity`
- `mature_harvest`
- `emerging_growth`
- `low_data_confidence`
- `monitor_only`

Each row includes an architecture signal reason and a recommended follow-up.
These labels do not replace engineering, commercial, market-access, or reserves
work.

## Limitations

- RRC production data is field/lease-grain and may not allocate production per
  well.
- RRC GIS-derived infrastructure access is screening-grade and does not prove
  connection feasibility, product compatibility, tariff access, capacity,
  ownership, or right-of-way availability.
- Missing lifecycle, well GIS, infrastructure, or operator evidence lowers
  confidence rather than being fabricated.
- Output rankings are deterministic for a given input artifact set but should
  be regenerated after upstream Texas RRC refreshes.
