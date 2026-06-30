# Plan: Issue #663 - Texas RRC production field atlas

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/663
**Status:** plan-approved
**Tier:** T2 (official PDQ production normalization, multi-level aggregation, `/mnt/ace` output contract, CLI, tests)
**Client:** N/A
**Project:** worldenergydata onshore field development

## Resource Intelligence Summary

Issue dependencies [#660](https://github.com/vamseeachanta/worldenergydata/issues/660),
[#661](https://github.com/vamseeachanta/worldenergydata/issues/661), and
[#662](https://github.com/vamseeachanta/worldenergydata/issues/662) are closed.
The implementation will consume the official Texas RRC `production_pdq`
snapshot refreshed under `/mnt/ace/worldenergydata/data/modules/texas_rrc`.
PatchOps and EWA will remain validation-only surfaces.

The source catalog defines `production_pdq` as a monthly official GoDrive file
with raw path `raw/production/pdq` and curated path
`curated/production/field_atlas`. The existing `PDQLoader` and
`ProductionProcessor` already provide useful field mappings, date parsing, and
numeric coercion; the atlas implementation will reuse those conventions while
preserving deterministic output ordering and `/mnt/ace` persistence semantics.

## Deliverable

The deliverable will build a deterministic production atlas from local official
PDQ raw snapshots and will write:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/
  production_field_atlas.csv
  production_field_atlas.parquet
  production_field_atlas_quality.json
  manifest.json
```

The atlas will include field, lease, district, operator, and statewide
summaries. It will not join the lifecycle spine or compute field-development
architecture metrics; those will remain in follow-on issues
[#664](https://github.com/vamseeachanta/worldenergydata/issues/664) and
[#665](https://github.com/vamseeachanta/worldenergydata/issues/665).

## Output Contract

Stable atlas columns will include:

- `aggregation_level`
- `district`
- `field_number`, `field_name`
- `lease_number`, `lease_name`
- `operator_number`, `operator_name`
- `cumulative_oil_bbl`, `cumulative_gas_mcf`, `cumulative_condensate_bbl`,
  `cumulative_water_bbl`, `cumulative_boe`
- `first_production_month`, `last_production_month`, `still_producing`
- `production_month_count`, `production_span_months`
- `peak_oil_bbl`, `peak_gas_mcf`, `peak_boe`
- `lease_count`, `operator_count`, `well_count_peak`
- `top_operator_number`, `top_operator_name`, `top_operator_boe`,
  `top_operator_share`

## Plan

### Task 1 - Add production atlas tests and source loading

Create `tests/unit/texas_rrc/test_production_atlas.py` with failing tests for
official PDQ column aliases, production month parsing, oil/gas/condensate/water
normalization, BOE convention, empty inputs, and local ZIP loading from
`raw/production/pdq`.

Create `worldenergydata.texas_rrc.production_atlas.sources` with a
`ProductionInputFrame` dataclass and `load_production_inputs(raw_root: Path)`.
The reader will inspect local files only, reject URL-like inputs, read CSV/TXT
members from official PDQ ZIP snapshots, and return source gaps rather than
failing on missing optional inputs.

### Task 2 - Build deterministic atlas aggregations

Create `worldenergydata.texas_rrc.production_atlas.atlas` with
`normalize_production_frame(frame: pd.DataFrame) -> pd.DataFrame` and
`build_production_atlas(frame: pd.DataFrame) -> pd.DataFrame`.

The implementation will aggregate field, lease, district, operator, and
statewide summaries. Monthly grouped rows will drive peak and still-producing
metrics. Operator concentration will use BOE share within each aggregate.

### Task 3 - Persist curated `/mnt/ace` outputs

Create `worldenergydata.texas_rrc.production_atlas.io` with
`write_production_atlas_outputs(...)` and `load_production_atlas(...)`.

Writes will stage under `.staging-production-field-atlas-*` and then promote
CSV, Parquet, quality JSON, and manifest JSON. The output root will default to
and be enforced under `/mnt/ace/worldenergydata/data/modules/texas_rrc`, with
an explicit non-ACE override only for isolated tests.

### Task 4 - Add CLI and docs

Extend `worldenergydata texas-rrc` with `build-production-atlas`, accepting
`--raw-root`, `--output-root`, `--dry-run`, `--require-sources`, and
`--allow-non-ace-output`.

Add `docs/data-sources/onshore/texas-rrc/production-field-atlas.md` documenting
source lifecycle, refresh cadence, output paths, CLI usage, and known gaps.

### Task 5 - Verify

Run:

```bash
uv run pytest tests/unit/texas_rrc/test_production_atlas.py -q
uv run pytest tests/unit/texas_rrc -q
uv run ruff check <touched files>
scripts/legal/legal-sanity-scan.sh
```

If the legal scan script is absent, closeout will report that explicitly.

## Out of Scope

- Joining lifecycle rows to production rows.
- Per-well allocation from lease-level production.
- Pipeline/GIS infrastructure access metrics.
- HTML/PDF report publication.
