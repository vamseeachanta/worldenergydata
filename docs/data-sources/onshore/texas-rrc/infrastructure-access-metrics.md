# Texas RRC Infrastructure Access Metrics

Texas RRC infrastructure access metrics extend the onshore field-development
workflow with official GIS-derived screening features: field well geometry,
field-centroid pipeline-envelope distance, nearby pipeline counts, and a
deterministic access class for field architecture triage.

## Source Of Record

The command uses direct Texas RRC source-derived artifacts only.

| Input | Upstream source | Refresh cycle | Local path |
| --- | --- | --- | --- |
| Well GIS layers | `well_gis_layers` official RRC GoDrive directory | Twice weekly | `/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/gis/wells` |
| Pipeline GIS layers | `pipeline_gis_layers` official RRC GoDrive directory | Twice weekly | `/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/gis/pipelines` |
| Field-development metrics | Lifecycle plus production field atlas | Follows #664 inputs | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/field_development/metrics` |
| Lifecycle spine | Well lifecycle normalization | Follows lifecycle inputs | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/well_lifecycle/spine` |

PatchOps remains validation-only. Its nearest-pipeline and well/area query
surface maps to the internal shapefile loaders and screening functions, but it
is not a durable input and is not required for repeatable builds.

## Command

Refresh official RRC GIS layers, then build the metrics:

```bash
uv run worldenergydata texas-rrc build-infrastructure-access-metrics \
  --refresh-gis \
  --require-sources
```

Use `--dry-run` to inspect source gaps and row counts without writing outputs:

```bash
uv run worldenergydata texas-rrc build-infrastructure-access-metrics --dry-run
```

Sandbox runs must explicitly opt into non-ACE output roots:

```bash
uv run worldenergydata texas-rrc build-infrastructure-access-metrics \
  --root /tmp/texas_rrc \
  --output-root /tmp/texas_rrc_out \
  --allow-non-ace-output
```

## Output Contract

The command writes:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/infrastructure/access/
+-- field_infrastructure_access.csv
+-- field_infrastructure_access.parquet
+-- field_infrastructure_access_quality.json
+-- manifest.json
```

Writes are staged under `.staging-infrastructure-access-*` before promotion.
By default, writes outside `/mnt/ace/worldenergydata/data/modules/texas_rrc`
are rejected.

## Stable Columns

Stable output columns include:

- `district`
- `field_number`
- `field_name`
- `field_well_count_with_location`
- `field_centroid_latitude`
- `field_centroid_longitude`
- `field_latitude_min`
- `field_latitude_max`
- `field_longitude_min`
- `field_longitude_max`
- `field_extent_miles`
- `nearest_pipeline_distance_miles`
- `nearby_pipeline_count_1mi`
- `nearby_pipeline_count_5mi`
- `nearby_pipeline_count_10mi`
- `nearest_pipeline_source_county`
- `nearest_pipeline_identifier`
- `infrastructure_access_score`
- `infrastructure_access_class`
- `source_caveats`
- `quality_flags`

The join key is `district, field_number`, matching the field-development
metrics.

## Scoring

| Class | Rule | Score |
| --- | --- | --- |
| `direct_access` | nearest pipeline distance `<= 1` mile | `1.0` |
| `near_access` | nearest pipeline distance `> 1` and `<= 5` miles | `0.75` |
| `regional_access` | nearest pipeline distance `> 5` and `<= 10` miles | `0.5` |
| `remote_access` | nearest pipeline distance `> 10` and `<= 25` miles | `0.25` |
| `isolated_or_unknown` | no pipeline within 25 miles, no pipeline source, or no field well locations | `0.0` |

## Caveats

- RRC GIS pipeline presence is a planning-screening signal only.
- Distances and counts are field-level screening metrics from the field centroid
  to mapped pipeline envelopes, filtered to the dominant county among matched
  well GIS points.
- The output does not claim pipeline capacity, ownership, tariff, product
  compatibility, right-of-way availability, or engineered tie-in feasibility.
- Distances use deterministic local screening math, not survey-grade GIS or
  engineered route analysis.
- Fields without matched lifecycle API keys and well GIS points carry
  `missing_well_gis`.
- Missing or malformed official GIS source files are surfaced in quality JSON
  and manifest `source_gaps`.
