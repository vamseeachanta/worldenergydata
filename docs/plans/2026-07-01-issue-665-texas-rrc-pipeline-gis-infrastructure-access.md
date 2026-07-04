# Plan: Issue #665 - Texas RRC pipeline and GIS infrastructure access metrics

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/665
**Status:** plan-approved
**Tier:** T2 (official GIS fanout, shapefile normalization, spatial metrics, `/mnt/ace` output contract, CLI, tests)
**Client:** N/A
**Project:** worldenergydata onshore field development

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after user
approval. The work will remain behind the issue approval gate until this plan is
reviewed and approved by the user. Implementation will use TDD, with failing
tests written before production code for GIS source loading, spatial distance
math, field aggregation, deterministic scoring, output persistence, and CLI
behavior.

### Official source evidence

Implementation will use official Texas RRC direct-source GIS datasets as the
source of record:

| Source | Official evidence | Planned use |
|---|---|---|
| RRC data downloads | `https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/` lists `Pipeline Layers by County` and `Well Layers by County` as ArcView shapefiles refreshed twice weekly. | Raw county shapefile ZIPs will be refreshed into `/mnt/ace` using the existing GoDrive directory refresh machinery. |
| RRC GIS viewer | `https://www.rrc.texas.gov/resource-center/research/gis-viewer/` says the viewer shows oil, gas, and pipeline data and is updated nightly. | Viewer behavior will be a manual/validation surface only; it will not become the durable input. |
| RRC pipeline mapping | `https://www.rrc.texas.gov/pipeline-safety/permitting-and-mapping/mapping/` says the Texas Pipeline Mapping System is continuously updated from operator-provided shapefiles and includes active, inactive, and abandoned lines not removed from the ground. | Pipeline proximity metrics will preserve caveats that mapped pipeline presence is not a definitive commercial tie-in route or active-service confirmation. |
| RRC GIS disclaimer | `https://www.rrc.texas.gov/about-us/faqs/general-faq/digital-map-information-gis-data/` says RRC GIS data is continually updated/refined and exported in `.SHP` format, with users responsible for suitability. | Output quality reports will label the infrastructure metrics as planning-screening metrics, not legal/survey-grade engineering deliverables. |

PatchOps will remain a validation-only comparison surface. It may validate a
small sample of pipeline proximity queries when access is available, but
implementation will not fetch durable input data from PatchOps and will not make
PatchOps required for repeatable builds.

### Dependency and source status

Implementation will treat these merged prerequisites as required source code:

- [#660](https://github.com/vamseeachanta/worldenergydata/issues/660) for the
  Texas RRC source catalog and `/mnt/ace` storage contract.
- [#661](https://github.com/vamseeachanta/worldenergydata/issues/661) and
  [#669](https://github.com/vamseeachanta/worldenergydata/issues/669) for
  official GoDrive raw refresh support, including directory fanout.
- [#664](https://github.com/vamseeachanta/worldenergydata/issues/664) for the
  field-development metrics output that #665 will join against.

Implementation will verify the actual `/mnt/ace` filesystem at runtime. It will
fail closed with actionable source gaps when GIS raw layers or #664 field
metrics are absent unless the CLI is explicitly asked to refresh/build missing
inputs.

### Dependency policy

Implementation will add a small pure-Python shapefile reader dependency to the
Texas RRC package, expected as `pyshp>=2.3,<3`, unless implementation discovery
finds an already-approved local reader. The implementation will avoid adding a
heavy GIS runtime such as GeoPandas/Fiona/Shapely as an incidental dependency.
Distance and extent metrics will use deterministic local math with documented
screening accuracy caveats.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review | `scripts/review/results/2026-07-01-plan-665-codex-inline.md` |
| GIS package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/__init__.py` |
| GIS source loading | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/gis_sources.py` |
| Spatial math | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/spatial.py` |
| Infrastructure metrics | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/access_metrics.py` |
| Infrastructure quality | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/quality.py` |
| Infrastructure I/O | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/io.py` |
| CLI | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_infrastructure_gis_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_infrastructure_spatial.py` |
| Unit tests | `tests/unit/texas_rrc/test_infrastructure_access_metrics.py` |
| Unit tests | `tests/unit/texas_rrc/test_infrastructure_io.py` |
| CLI tests | `tests/unit/texas_rrc/test_infrastructure_access_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md` |

## Deliverable

The deliverable will materialize official RRC GIS-derived infrastructure access
metrics under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/infrastructure/access/
  field_infrastructure_access.csv
  field_infrastructure_access.parquet
  field_infrastructure_access_quality.json
  manifest.json
```

The output will be keyed so it can join to the #664 field-development metrics:

```text
district, field_number
```

Stable output columns will include:

- `district`
- `field_number`, `field_name`
- `field_well_count_with_location`
- `field_centroid_latitude`, `field_centroid_longitude`
- `field_latitude_min`, `field_latitude_max`
- `field_longitude_min`, `field_longitude_max`
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

The output will not claim commercial pipeline capacity, ownership, tariff,
product compatibility, right-of-way availability, or engineered route
feasibility. Those will remain follow-on architecture and market-access work.

## Plan

### Task 1 - Refresh and stage official GIS raw inputs

Write failing tests that prove `well_gis_layers` and `pipeline_gis_layers`
directory refreshes can be requested by the #665 CLI path without writing
outside the Texas RRC `/mnt/ace` root. The tests will use fake GoDrive directory
transport and will assert source manifests include per-file checksum, byte size,
RRC modified label, and source URL.

Extend the Texas RRC CLI with an implementation-only helper path that will
reuse the existing raw refresh machinery when `--refresh-gis` is passed:

```bash
worldenergydata texas-rrc build-infrastructure-access-metrics --refresh-gis
```

Default execution will not silently download large GIS fanout. It will instead
report missing raw GIS source gaps unless refresh is requested.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_infrastructure_access_cli.py tests/unit/texas_rrc/test_raw_refresh_directory.py -q
```

### Task 2 - Normalize RRC GIS shapefiles

Write failing tests with tiny zipped shapefile fixtures for:

- well point records with API identifiers and latitude/longitude geometry
- pipeline polyline records with a stable source identifier
- malformed ZIPs, missing `.shp/.shx/.dbf` members, unsupported geometry, and
  missing coordinate records

Create `infrastructure/gis_sources.py` with public interfaces:

```python
@dataclass(frozen=True)
class WellGisRecord:
    api_number: str | None
    county_fips: str | None
    latitude: float
    longitude: float
    source_file: str

@dataclass(frozen=True)
class PipelineGisRecord:
    pipeline_identifier: str | None
    county_fips: str | None
    coordinates: tuple[tuple[float, float], ...]
    source_file: str

def load_well_gis_records(raw_root: Path | str) -> tuple[WellGisRecord, ...]:
    ...

def load_pipeline_gis_records(raw_root: Path | str) -> tuple[PipelineGisRecord, ...]:
    ...
```

The loader will preserve source filenames, normalize API-like identifiers for
joining, reject non-local paths, and emit structured load gaps rather than
silently dropping malformed files.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_infrastructure_gis_sources.py -q
```

### Task 3 - Add deterministic spatial math without heavy GIS runtime

Write failing tests for:

- point-to-point distance in miles
- point-to-polyline distance in miles
- antimeridian-free Texas coordinate bounds
- bounding-box and county prefilters
- no-pipeline behavior

Create `infrastructure/spatial.py` with small, deterministic helpers for Texas
screening distances. The implementation will compute distances in miles using a
local tangent-plane approximation around each field centroid. It will use
county and grid/bounding-box prefilters before exact point-to-segment checks so
statewide runs do not degrade into an unbounded all-fields-by-all-pipelines
scan.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_infrastructure_spatial.py -q
```

### Task 4 - Build field-level infrastructure access metrics

Write failing tests that combine small lifecycle/field-development fixtures,
well GIS records, and pipeline records. The tests will cover:

- a field with nearby pipelines
- a field with wells but no nearby pipelines
- a field with field-development metrics but no GIS well locations
- a field with GIS wells but no matching #664 field metrics
- deterministic scoring thresholds
- repeatable sorting and join keys

Create `infrastructure/access_metrics.py` with:

```python
@dataclass(frozen=True)
class InfrastructureAccessInputs:
    field_development: pd.DataFrame
    lifecycle: pd.DataFrame
    well_gis: tuple[WellGisRecord, ...]
    pipeline_gis: tuple[PipelineGisRecord, ...]
    source_gaps: tuple[str, ...]

def build_infrastructure_access_metrics(
    inputs: InfrastructureAccessInputs,
) -> pd.DataFrame:
    ...
```

The implementation will derive field geometries from RRC well GIS points joined
to lifecycle rows by normalized API number and then to #664 field keys. It will
compute nearest pipeline distance from field well points to RRC pipeline
polylines, not from production records alone.

The deterministic access score will use explicit thresholds:

| Class | Rule |
|---|---|
| `direct_access` | nearest pipeline distance `<= 1` mile |
| `near_access` | nearest pipeline distance `> 1` and `<= 5` miles |
| `regional_access` | nearest pipeline distance `> 5` and `<= 10` miles |
| `remote_access` | nearest pipeline distance `> 10` and `<= 25` miles |
| `isolated_or_unknown` | no pipeline within 25 miles, no pipeline source, or no field well locations |

`infrastructure_access_score` will map those classes to
`1.0`, `0.75`, `0.50`, `0.25`, and `0.0`, with caveats separating true remote
fields from missing source geometry.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_infrastructure_access_metrics.py -q
```

### Task 5 - Persist outputs and quality metadata

Write failing tests for CSV/Parquet output, JSON quality report, manifest,
atomic staging, and `/mnt/ace` root enforcement.

Create `infrastructure/io.py` and `infrastructure/quality.py`. The manifest
will include:

- code revision
- command
- generated timestamp
- input raw GIS manifest paths
- #664 field-development manifest path
- row count
- source gaps
- scoring thresholds
- direct-source caveats

The quality report will include field counts by access class, missing GIS well
coverage count, missing pipeline source count, malformed source file counts,
and maximum/minimum nearest-pipeline distance for fields with valid geometry.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_infrastructure_io.py -q
```

### Task 6 - Add CLI and documentation

Add:

```bash
worldenergydata texas-rrc build-infrastructure-access-metrics
```

CLI options will include:

- `--output-root`
- `--refresh-gis`
- `--require-sources`
- `--dry-run`
- `--nearby-radius-miles`
- `--allow-non-ace-root` for tests only

Add `docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md`
covering source-of-record policy, refresh cadence, output schema, scoring
thresholds, caveats, and PatchOps validation-only usage.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_infrastructure_access_cli.py -q
uv run --no-sync pytest tests/unit/texas_rrc -q
uv run --no-sync black --check --diff src/ tests/ packages/worldenergydata-texas_rrc/src/
uv run --no-sync isort --check-only --diff src/ tests/ packages/worldenergydata-texas_rrc/src/
uv run --no-sync flake8 src/ packages/worldenergydata-texas_rrc/src/ --max-line-length=100 --extend-ignore=E203,W503 --exclude=__pycache__,*.egg-info,.git,.venv
```

### Task 7 - Build direct-source `/mnt/ace` artifacts

After tests pass, implementation will run:

```bash
uv run --no-sync worldenergydata texas-rrc build-infrastructure-access-metrics --refresh-gis --require-sources
```

The run will write the curated infrastructure access outputs under `/mnt/ace`.
The manifest `code_revision` will match the final implementation commit before
the PR is merged.

## Acceptance Criteria Mapping

| Issue acceptance criterion | Planned evidence |
|---|---|
| Well and pipeline GIS inputs are materialized or staged under the Texas RRC `/mnt/ace` tree with source manifests. | Task 1 raw refresh tests, `/mnt/ace/raw/gis/*` manifests, and Task 7 direct-source run. |
| Field-level metrics include nearest pipeline distance, nearby pipeline count, well spatial extent, and infrastructure access score. | Task 4 metrics tests and Task 5 output schema. |
| PatchOps RRC tool coverage is mapped to equivalent internal query functions for validation where practical. | Docs will map PatchOps-style nearest pipeline and well/area queries to internal functions; PatchOps will stay validation-only. |
| Tests cover spatial joins with small fixtures, no-pipeline cases, and deterministic access scoring. | Tasks 2-4 fixture and scoring tests. |
| Output joins cleanly to the field-development metrics from the lifecycle/production analysis. | Task 4 join-key tests on `district, field_number`; Task 5 manifest input link to #664 field-development metrics. |

## Out of Scope

- Commercial pipeline capacity or tariff analysis.
- Pipeline ownership enrichment beyond attributes present in official RRC GIS
  files.
- Engineered tie-in routing, hydraulic sizing, or right-of-way feasibility.
- PatchOps as a durable input source.
- HTML/PDF onshore field atlas publication, which will remain in
  [#666](https://github.com/vamseeachanta/worldenergydata/issues/666).

## Approval Gate

Implementation will not start until the user explicitly approves
[Issue #665](https://github.com/vamseeachanta/worldenergydata/issues/665) for
implementation and the issue carries `status:plan-approved`.
