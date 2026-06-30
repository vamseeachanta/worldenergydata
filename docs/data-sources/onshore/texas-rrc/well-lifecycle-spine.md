# Texas RRC Well Lifecycle Spine

The Texas RRC well lifecycle spine is the first onshore analog to the BSEE
field-development workflow. It centers official Texas RRC raw snapshots on the
API14/API10 well identity, then writes a curated spine under `/mnt/ace` for
production analysis, lease/field rollups, and later field architecture work.

## Source Of Record

The lifecycle spine uses direct Texas RRC sources only:

| Lifecycle stage | Catalog source | Refresh cycle | Current role |
| --- | --- | --- | --- |
| Production and lease history | `production_pdq` | Monthly, after the last Saturday | Downstream production and field/lease rollups |
| Well identity and status | `wellbore_query` | Monthly, beginning of month | API, district, field, lease, operator, well status |
| Development intent | `drilling_permits` | Nightly | Permit number, permit dates, depth, location, spud date |
| Completion milestone | `completion_data` | Nightly | W-2/G-1 completion date and completion evidence |
| Trajectory evidence | `directional_surveys` | Daily | Source-gap flag until PDF extraction is implemented |

PatchOps and RRC EWA query flows remain validation surfaces. They are useful for
spot-checking official joins but are not durable storage inputs for this repo.

## Storage Contract

Raw refreshes land under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/
```

The lifecycle command writes curated outputs under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/well_lifecycle/spine/
+-- well_lifecycle_spine.csv
+-- well_lifecycle_quality.json
+-- manifest.json
```

Writes are staged under `.staging-well-lifecycle-spine-*` and then promoted into
the final curated directory.

## Command

Refresh the official raw sources first, then normalize the lifecycle spine:

```bash
uv run worldenergydata texas-rrc refresh --source wellbore_query
uv run worldenergydata texas-rrc refresh --source drilling_permits
uv run worldenergydata texas-rrc refresh --source completion_data
uv run worldenergydata texas-rrc normalize-lifecycle --require-sources
```

Use `--dry-run` to load and assess local raw snapshots without writing curated
outputs:

```bash
uv run worldenergydata texas-rrc normalize-lifecycle --dry-run
```

For test or sandbox runs, override both roots:

```bash
uv run worldenergydata texas-rrc normalize-lifecycle \
  --raw-root /tmp/texas_rrc \
  --output-root /tmp/texas_rrc_out
```

## Spine Grain

The spine is one row per API10/API14 well identity. It preserves the normalized
API14, derived API10, county code, well unique number, sidetrack code,
completion code, district, field, lease, operator, permit, well status,
milestone dates, coordinates, and source-presence flags.

Current join priority is:

1. Wellbore Query for durable well identifiers and status.
2. Drilling permits for intent, permit dates, spud date, and surface location.
3. Completion data for completion milestones and completion-form evidence.

## Quality Report

`well_lifecycle_quality.json` counts high-signal quality defects:

- duplicate API14 values
- missing field, lease, or operator identifiers
- invalid Texas coordinate bounds
- impossible milestone ordering
- permits or completions without a wellbore row
- wellbores without completion evidence
- missing lifecycle source directories

The CSV also carries row-level `quality_flags` so downstream production and field
development analysis can filter or inspect suspect joins.

## Field Development Use

This spine is the onshore lifecycle anchor for later work:

- production decline and lease/field allocation from `production_pdq`
- drilling-to-completion cycle time and permit aging analysis
- active, shut-in, plugged, and orphaned well status rollups
- operator, lease, field, and district field-development comparisons
- pipeline and surface-infrastructure overlays once official GIS layers are
  normalized
- architecture analysis that links well pads, pipelines, leases, and production
  facilities from official RRC sources
