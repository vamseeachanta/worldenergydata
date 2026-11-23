# Plan: Issue #702 - Texas RRC field architecture dossiers

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/702
**Status:** plan-review
**Tier:** T2 (new report package, candidate selection contract, HTML and machine-readable outputs, CLI, tests, docs)
**Client:** N/A
**Project:** worldenergydata onshore field development
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after user
approval. The work will remain blocked until this plan is reviewed, pushed,
marked `status:plan-review`, and explicitly approved by the user. Implementation
will use TDD, with failing tests written before production code for source
loading, candidate selection, dossier model assembly, HTML rendering, output
persistence, quality reporting, and CLI behavior.

### Reproduction proofs

N/A. Issue #702 proposes a new report product and does not allege a runtime
failure, regression, missing method, or incorrect numeric output. The
implementation worker will still re-run the source-inventory probes below before
coding because dossier output depends on live `/mnt/ace` artifacts.

### Direct-source artifact inventory

The dossier builder will consume direct Texas RRC-derived curated artifacts
already published under `/mnt/ace/worldenergydata/data/modules/texas_rrc`. It
will not call PatchOps, scrape LinkedIn, use third-party scraper output, or
fetch new network data during dossier publication.

Planning-time probes from 2026-07-02 report these current inputs:

| Input | Current rows | Current source gaps | Current generated_at | Expected path | Planned use |
|---|---:|---|---|---|---|
| Field opportunity ranking | 67,082 | none | 2026-07-02T10:31:17Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/field_opportunity_rankings.csv` | Candidate selection, opportunity score, architecture signal, follow-up reason, caveats |
| Opportunity manifest | 67,082 | none | 2026-07-02T10:31:17Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/manifest.json` | Input provenance, scoring version, upstream manifest list, source gaps, code revision |
| Field atlas summary | 67,082 | none | 2026-07-02T02:27:21Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/field_atlas_summary.parquet` | Field report links, lifecycle, production, operator, and infrastructure context |
| Field atlas pages | 67,082 pages | none | 2026-07-02T02:27:21Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/fields/` | Link target for each selected dossier |
| Field-development metrics | 67,082 | none | 2026-07-01T04:59:00Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/field_development/metrics/field_development_metrics.csv` | Upstream fallback and source provenance for lifecycle/development metrics |
| Infrastructure access metrics | 61,518 | none | 2026-07-01T22:29:46Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/infrastructure/access/field_infrastructure_access.csv` | Upstream provenance only in v1; field-level access signals are consumed through #695 and #666 outputs |
| Production atlas | 470,505 | water and well-count metric gaps | 2026-06-30T23:20:41Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/production_field_atlas.csv` | Upstream provenance only in v1; production/operator context is consumed through #666 and #664 outputs |
| Well lifecycle spine | 1,007,517 | source gaps not emitted in current manifest | 2026-07-01T04:18:58Z | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/well_lifecycle/spine/` | Provenance for lifecycle rollups; not a direct row-level input unless required by a later approved scope |

Top planning-time opportunity candidates include:

| Rank | District | Field number | Field | Score | Architecture signal |
|---:|---|---|---|---:|---|
| 1 | 05 | 00870500 | AGUILA VADO (EAGLEFORD) | 74.79 | `high_access_infill_redevelopment` |
| 2 | 03 | 84750500 | SOUTHERN BAY (EAGLE FORD) | 74.62 | `high_access_infill_redevelopment` |
| 3 | 02 | 27135750 | EAGLEVILLE (EAGLE FORD-2) | 74.61 | `high_access_infill_redevelopment` |
| 4 | 03 | 34733610 | GIDDINGS (EAGLEFORD) | 74.58 | `high_access_infill_redevelopment` |
| 5 | 02 | 86950300 | SUGARKANE (AUSTIN CHALK) | 74.55 | `high_access_infill_redevelopment` |

The full ranking currently includes 2,208
`high_access_infill_redevelopment`, 12 `emerging_growth`, 3
`infrastructure_constrained_activity`, 10,840 `mature_harvest`, 3,724
`monitor_only`, and 50,295 `low_data_confidence` rows. The default dossier
selection will therefore use a bounded top-N set plus class-coverage rules so
rare signal classes do not disappear from the report packet.

### Input boundary

The v1 dossier builder will use three direct row-level inputs:

1. #695 field-opportunity ranking.
2. #666 field-atlas summary.
3. #664 field-development metrics.

The #665 infrastructure metrics and #663 production atlas remain upstream
provenance for v1. Their field-level access and production/operator signals are
already carried into the #695 ranking, #666 field-atlas summary, and #664
field-development metrics. The implementation will not load
`field_infrastructure_access.csv` or `production_field_atlas.csv` directly in
v1. If a requested dossier metric is not present in those three row-level
inputs, the builder will emit a visible context caveat rather than silently
dropping the field.

### Current code shape

- `worldenergydata.texas_rrc.opportunities` already loads the #666 field-atlas
  summary, computes #695 opportunity rankings, classifies architecture screening
  signals, renders a summary HTML report, writes staged CSV/Parquet/JSON outputs,
  and exposes `run_build_field_opportunities`.
- `worldenergydata.texas_rrc.reports` already builds per-field field-atlas page
  models and self-contained HTML reports with staged writes.
- `src/worldenergydata/cli/commands/texas_rrc.py` already hosts Texas RRC Typer
  commands including `publish-field-atlas-reports` and
  `build-field-opportunities`.
- `tests/unit/texas_rrc/` already contains focused tests for source loading,
  staged writes, quality summaries, HTML rendering, and CLI support across the
  onshore modules.
- The repo uses an ADR 0001 workspace-member split. Texas RRC domain code lives
  in `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc`, while
  the root CLI registration remains in `src/worldenergydata/cli/commands`.
  The root package depends on `worldenergydata-texas_rrc` through
  `[tool.uv.sources]`, so tests and CLI runs must include package member source
  roots when they bypass a full editable install.

The implementation will create a new Texas RRC-local `dossiers` package. It
will consume the opportunity ranking and report summary outputs rather than
moving dossier responsibility into `opportunities` or overloading the field
atlas publisher.

### Interpretation policy

The dossier output will remain a screening and decision-support product. It
will not claim reserves, economic value, NPV, tariffs, pipeline capacity,
product compatibility, right-of-way availability, route feasibility, or
engineered facility design. Every page and manifest will preserve caveats from
the upstream RRC-derived artifacts, including lease-level production allocation,
no per-well production allocation, RRC GIS screening-only distances, dominant
county pipeline filtering, missing well GIS, and PDQ water/well-count gaps.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-02-issue-702-texas-rrc-field-architecture-dossiers.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex | `scripts/review/results/2026-07-02-plan-702-codex-inline.md` |
| Plan review - Claude fallback | `scripts/review/results/2026-07-02-plan-702-claude.md` |
| Plan review - Gemini availability | `scripts/review/results/2026-07-02-plan-702-gemini-unavailable.md` |
| Plan review synthesis | `scripts/review/results/2026-07-02-plan-702-synthesis.md` |
| Code review - Codex | `scripts/review/results/2026-07-02-code-702-codex-inline.md` |
| Code review - Claude fallback | `scripts/review/results/2026-07-02-code-702-claude.md` |
| Code review - Gemini availability | `scripts/review/results/2026-07-02-code-702-gemini-unavailable.md` |
| Legal/security scan evidence | `scripts/review/results/2026-07-02-code-702-legal-sanity-scan.txt` plus issue closeout comment |
| Dossier package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/__init__.py` |
| Source loading | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/sources.py` |
| Candidate selection | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/selection.py` |
| Dossier model assembly | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/models.py` |
| HTML rendering | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/html.py` |
| Quality reporting | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/quality.py` |
| Output persistence | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/io.py` |
| CLI support | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/cli_support.py` |
| CLI command | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_dossier_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_dossier_selection.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_dossier_models.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_dossier_html.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_architecture_dossier_io.py` |
| CLI tests | `tests/unit/texas_rrc/test_field_architecture_dossier_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md` |

## Deliverable

The deliverable will publish Texas RRC field architecture dossiers under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_dossiers/
  field_architecture_dossier_index.csv
  field_architecture_dossier_index.parquet
  field_architecture_dossier_summary.html
  fields/
    <district>-<field_number>-<field_slug>-dossier.html
  quality.json
  field_architecture_dossier_quality.json
  manifest.json
```

`quality.json` will satisfy the issue-body artifact name. The component-specific
`field_architecture_dossier_quality.json` will carry the same payload for
consistency with the existing Texas RRC output convention used by field atlas,
field-opportunity, infrastructure, field-development, and production-atlas
publishers. Tests will assert that both files are written with identical JSON.

The output will be keyed by:

```text
district, field_number
```

Stable index columns will include:

- `dossier_rank`
- `district`
- `field_number`
- `field_name`
- `field_slug`
- `dossier_path`
- `source_field_atlas_report_path`
- `opportunity_rank`
- `opportunity_score`
- `opportunity_class`
- `architecture_signal_class`
- `architecture_signal_reason`
- `recommended_followup`
- `dossier_focus`
- `production_maturity_class`
- `first_production_month`
- `last_production_month`
- `still_producing`
- `production_span_months`
- `remaining_activity_score`
- `well_count`
- `active_well_count`
- `permit_count`
- `completion_count`
- `cumulative_boe`
- `production_per_well_boe`
- `lease_count`
- `operator_count`
- `infrastructure_access_class`
- `infrastructure_access_score`
- `nearest_pipeline_distance_miles`
- `nearby_pipeline_count_1mi`
- `nearby_pipeline_count_5mi`
- `nearby_pipeline_count_10mi`
- `top_operator_name`
- `top_operator_share`
- `selection_reason`
- `source_caveats`
- `quality_flags`
- `dossier_limitations`

Planning-time column probes on 2026-07-02 verify the v1 row-level sources for
the stable index columns:

| Column group | Source priority |
|---|---|
| Opportunity score/class/rank, architecture signal, follow-up, key drivers | #695 `field_opportunity_rankings.csv` |
| Infrastructure class/score/distance/counts | #695 ranking first; #666 field-atlas summary as context check |
| Cumulative BOE, BOE per well, maturity, remaining activity, well counts, operator name/share | #695 ranking first; #666 field-atlas summary then #664 field-development metrics as context check |
| Permit count, completion count, lease count, operator count | #666 field-atlas summary first; #664 field-development metrics as fallback |
| First production month, last production month, still-producing flag | #664 field-development metrics |
| Production span months | Derived only from #664 first/last production month when both parse cleanly |
| Source caveats and quality flags | union of #695 ranking, #666 field-atlas summary, and #664 field-development metrics |

If a stable column is missing from the expected source frame at runtime, the
builder will keep the column in the index, fill null for affected rows, and add
a visible `missing_column:<column>` context caveat. Missing required input files
and unreadable manifests remain blocking source gaps.

`manifest.json` will include:

- generated timestamp
- code revision
- command
- output paths
- input paths and upstream manifests
- selected row count
- blocking source gaps
- informational upstream gaps and metric gaps
- selected architecture class counts
- default selection policy
- source manifest generated timestamps
- caveat and quality summaries
- explicit limitations on reserves, economics, tariffs, capacity, right of way,
  and engineered facility design

## Files to Change

| Action | File | Reason |
|---|---|---|
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/__init__.py` | Export the public dossier builder functions and constants |
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/sources.py` | Load #695 rankings, opportunity manifest, field-atlas summary, field-development metrics, and upstream manifests |
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/selection.py` | Select top-ranked and class-coverage candidate rows deterministically |
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/models.py` | Join selected rankings to context metrics and assemble page/index models |
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/html.py` | Render self-contained summary and per-field dossier HTML |
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/quality.py` | Summarize selected rows, caveats, source gaps, and limitations |
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/io.py` | Write staged CSV, Parquet, HTML, quality JSON, and manifest outputs |
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/dossiers/cli_support.py` | Orchestrate load, select, join, render, write, dry-run, and require-source behavior |
| Modify | `src/worldenergydata/cli/commands/texas_rrc.py` | Add the `build-field-architecture-dossiers` Typer command |
| Create | `tests/unit/texas_rrc/test_field_architecture_dossier_sources.py` | Test source loading and provenance gaps |
| Create | `tests/unit/texas_rrc/test_field_architecture_dossier_selection.py` | Test deterministic candidate selection |
| Create | `tests/unit/texas_rrc/test_field_architecture_dossier_models.py` | Test joins, production trend context, caveats, and stable index rows |
| Create | `tests/unit/texas_rrc/test_field_architecture_dossier_html.py` | Test HTML sections, escaping, links, and remote-dependency avoidance |
| Create | `tests/unit/texas_rrc/test_field_architecture_dossier_io.py` | Test staged writes, quality files, manifest, and output-root guard |
| Create | `tests/unit/texas_rrc/test_field_architecture_dossier_cli.py` | Test CLI argument wiring, dry-run, require-source, and success messages |
| Create | `docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md` | Document lifecycle, refresh cadence, output contract, selection, and limitations |

## Pseudocode

```text
load_field_architecture_dossier_inputs(root):
  locate curated/analysis/field_opportunities
  load field_opportunity_rankings.parquet else CSV
  require/read opportunity manifest; emit missing_field_opportunity_manifest if absent
  parse opportunity manifest source_gaps, metric_gaps, input_paths, upstream_manifests
  load field_atlas_summary.parquet else CSV when present
  load field_development_metrics.parquet else CSV when present
  emit blocking source gaps for missing rankings, missing manifest, missing context, unreadable manifests
  emit informational upstream gaps for inherited source_gaps and metric_gaps
  return FieldArchitectureDossierInputs

run_build_field_architecture_dossiers(..., dry_run, require_sources):
  inputs = load_field_architecture_dossier_inputs(root)
  if inputs.blocking_source_gaps and (require_sources or not dry_run):
    raise ValueError listing blocking source gaps
  select candidates, build page models, assess quality
  if dry_run: return row count and gaps without writing
  write staged outputs

select_dossier_candidates(rankings, max_fields, class_coverage_limit):
  validate max_fields > 0 and class_coverage_limit >= 0
  coerce opportunity_rank to numeric; emit invalid_opportunity_rank on failures
  take top max_fields by opportunity_rank, district, field_number, field_name
  for each architecture_signal_class in sorted stable order:
    if class already represented in selected: skip adding coverage rows
    otherwise append up to class_coverage_limit rows by opportunity_rank,
      district, field_number, field_name
  de-duplicate by district, field_number
  sort final selected set by opportunity_rank, district, field_number, field_name
  encode selection_reason as exactly one token: top_ranked or class_coverage:<class>
  assign dossier_rank from final order

build_field_architecture_dossier_pages(selected, context):
  left-join selected rows to field_atlas_summary on district, field_number
  left-join selected rows to field_development_metrics on district, field_number
  prefer ranking values for opportunity fields
  fill overlapping context by the column-source priority table
  derive production_span_months from first_production_month and last_production_month when both parse
  derive curated-relative source_field_atlas_report_path from report_path
  preserve caveats, quality flags, and limitation text
  return page models and stable index dataframe

write_field_architecture_dossier_outputs(pages, index, quality, output_root):
  reject non-ACE output roots unless allow_non_ace_root is true
  write all files under a staging directory
  write CSV, Parquet, summary HTML, per-field HTML, quality.json,
    field_architecture_dossier_quality.json, and manifest.json
  atomically promote staging directory and remove stale prior outputs
```

## Selection Contract

The first implementation will select a deterministic bounded dossier set using:

1. Include the top `--max-fields` rows by `opportunity_rank`; default `25`.
2. Add up to `--class-coverage-limit` rows from each non-empty architecture
   signal class not already represented; default `3`.
3. Preserve original opportunity-rank order after de-duplication.
4. Emit `selection_reason` as a single token. `top_ranked` will be used for rows
   from the top-N set. `class_coverage:<class>` will be used for rows added only
   by the coverage pass. A row will not carry both tokens in v1 because coverage
   rows are added only for classes absent from the top-N set.
5. Reject negative or zero `--max-fields` and negative
   `--class-coverage-limit` values at the CLI support layer.

The selected row count can exceed `--max-fields` when class-coverage rows are
added. A live planning probe against the #695 ranking selects 37 default rows:
the top 25 already contain `high_access_infill_redevelopment` and
`emerging_growth`, then coverage adds three rows each for
`infrastructure_constrained_activity`, `low_data_confidence`, `mature_harvest`,
and `monitor_only`. Tests will pin this already-represented-class behavior with
small fixtures so coverage does not duplicate top-ranked classes.

## Dossier Page Contract

Each per-field page will be self-contained HTML and will include:

- headline identity: field name, district, field number, architecture signal,
  opportunity rank, and opportunity score
- opportunity summary: scoring components, key drivers, recommended follow-up,
  and selection reason
- lifecycle and production panel: maturity class, remaining activity score,
  wells, active wells, permits, completions, cumulative BOE, BOE per well,
  first production month, last production month, still-producing flag, and
  derived production span when present in source rows
- infrastructure panel: access class, access score, nearest pipeline distance,
  nearby pipeline counts, and GIS screening caveats
- operator and lease context: top operator, operator share, lease count, and
  operator count when present in source rows
- evidence and provenance: links to the #666 field-atlas page, input manifest
  paths, source caveats, quality flags, and generated timestamp
- limitations panel: no reserves/economics/tariffs/capacity/ROW/facility-design
  conclusions

The summary page will include batch counts, selected class distribution, top
dossier table, source gaps, and limitations.

## Plan

### Task 1 - Load ranked opportunity and context inputs

Before running any task-level `--no-sync` pytest command in a fresh worktree,
run `uv sync --all-packages --all-extras` once. The validation gate repeats this
sync step before closeout evidence is recorded.

Write failing tests for a tiny source tree with:

- `curated/analysis/field_opportunities/field_opportunity_rankings.csv`
- `curated/analysis/field_opportunities/manifest.json`
- opportunity manifest `upstream_manifests` entries
- `curated/reports/field_atlas/field_atlas_summary.csv`
- `curated/field_development/metrics/field_development_metrics.csv`
- missing rankings behavior
- missing opportunity manifest behavior
- unreadable manifest behavior

Create `dossiers/sources.py` with:

```python
@dataclass(frozen=True)
class FieldArchitectureDossierInputs:
    rankings: pd.DataFrame
    field_atlas_summary: pd.DataFrame
    field_development_metrics: pd.DataFrame
    input_paths: tuple[Path, ...]
    upstream_manifests: tuple[Path, ...]
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]

def load_field_architecture_dossier_inputs(
    root: Path | str,
) -> FieldArchitectureDossierInputs:
    ...
```

The loader will prefer `field_opportunity_rankings.parquet` and fall back to
CSV. It will prefer Parquet and fall back to CSV for field-atlas summary and
field-development metrics. It will normalize `district` and `field_number` to
strings across all frames, collect informational source and metric gaps from the
opportunity manifest, preserve the opportunity manifest `upstream_manifests`
list, and record blocking gaps such as
`missing_field_opportunity_rankings`, `missing_field_opportunity_manifest`,
`missing_field_atlas_summary`, `missing_field_development_metrics`, or
`unreadable_manifest` rather than fabricating missing evidence. If an upstream
manifest path listed by the opportunity manifest is absent in the current root,
the loader will emit blocking `missing_upstream_manifest:<name>`. Informational
upstream gaps such as PDQ water/well-count metric gaps will be preserved in
quality and manifest metadata but will not block publication. `--require-sources`
will fail on any blocking source gap, including a missing opportunity manifest.
Any non-dry-run publication will also fail on any blocking source gap, even when
`--require-sources` is not passed; dry-run is the only mode allowed to report
blocking gaps without writing.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest tests/unit/texas_rrc/test_field_architecture_dossier_sources.py -q
```

### Task 2 - Select dossier candidates

Write failing tests for:

- default top-25 selection
- architecture-class coverage rows added after top-N rows
- deterministic de-duplication when a class-coverage row is already top-ranked
- no extra coverage rows for a class already represented in the top-N set
- stable opportunity-rank ordering after de-duplication
- single-token `selection_reason` encoding
- duplicate or non-numeric `opportunity_rank` values producing visible gaps or
  deterministic tie-breaks
- invalid `max_fields` and `class_coverage_limit` values

Create `dossiers/selection.py` with:

```python
def select_dossier_candidates(
    rankings: pd.DataFrame,
    max_fields: int = 25,
    class_coverage_limit: int = 3,
) -> pd.DataFrame:
    ...
```

The selected rows will carry `dossier_rank`, `selection_reason`, and
`dossier_focus`. Selection will sort by `opportunity_rank`, `district`,
`field_number`, and `field_name`; non-numeric ranks will add
`invalid_opportunity_rank` and fail publication outside dry-run. `dossier_focus`
will map architecture signal classes to concise
screening review themes such as `infill_redevelopment_review`,
`growth_pattern_review`, `infrastructure_constraint_review`,
`late_life_harvest_review`, `source_gap_resolution`, and `monitoring_context`.
Unknown future classes will map to `unclassified_review` and will remain visible
in quality counts.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest tests/unit/texas_rrc/test_field_architecture_dossier_selection.py -q
```

### Task 3 - Build dossier page models

Write failing tests for:

- one selected row producing one page model and one index row
- selected ranking rows left-joining to field-atlas summary and
  field-development metrics by `district, field_number`
- production trend context flowing from field-development metrics:
  `first_production_month`, `last_production_month`, `still_producing`, and
  derived `production_span_months`
- source caveats and quality flags flowing through unchanged
- field-atlas report paths stored as curated-relative
  `source_field_atlas_report_path` values
- limitations emitted for every row
- empty selected inputs producing an empty index with stable columns

Create `dossiers/models.py` with:

```python
DOSSIER_INDEX_COLUMNS = [...]

@dataclass(frozen=True)
class FieldArchitectureDossierPage:
    district: str
    field_number: str
    field_name: str
    field_slug: str
    dossier_filename: str
    dossier_path: str
    summary: dict[str, object]
    source_caveats: tuple[str, ...]
    quality_flags: tuple[str, ...]
    limitations: tuple[str, ...]

def build_field_architecture_dossier_pages(
    selected: pd.DataFrame,
    field_atlas_summary: pd.DataFrame,
    field_development_metrics: pd.DataFrame,
) -> tuple[FieldArchitectureDossierPage, ...]:
    ...

def build_field_architecture_dossier_index(
    pages: tuple[FieldArchitectureDossierPage, ...],
) -> pd.DataFrame:
    ...
```

The model builder will reuse the local slugging behavior from the existing
field-atlas reports when practical, but will keep dossier filenames distinct
with the `-dossier.html` suffix.

The join contract will be explicit and left-biased to the selected #695 ranking:

1. Keep every selected row, even when context rows are missing.
2. Join field-atlas summary on `district, field_number` for report path,
   permit/completion counts, lease/operator counts, and field-atlas caveats.
3. Join field-development metrics on `district, field_number` for production
   trend fields: `first_production_month`, `last_production_month`,
   `still_producing`, and any context not present in the ranking.
4. Prefer #695 ranking values for opportunity score, opportunity class,
   architecture signal, recommended follow-up, infrastructure access, and
   scoring-driver columns.
5. Add row-level caveats such as `missing_field_atlas_context` and
   `missing_field_development_context` when context joins miss.
6. Derive `production_span_months` only when first and last production months
   parse cleanly; otherwise leave it null and preserve the source caveat.

For link safety, `source_field_atlas_report_path` will be stored as a
curated-relative provenance path such as
`reports/field_atlas/fields/05-00870500-aguila-vado-eagleford.html`. The HTML
renderer will compute hrefs from the dossier output location: summary pages will
link with `../../<source_field_atlas_report_path>`, and per-field dossier pages
under `fields/` will link with `../../../<source_field_atlas_report_path>`.
Tests will assert both relative forms so links do not silently resolve to the
dossier `fields/` directory.

When `--output-root` differs from `--root` for sandbox publication, the renderer
will not emit a relative href to the source field-atlas HTML because the source
tree may not exist beside the output tree. In that case it will render the
curated-relative source path as provenance text and will add
`source_link_not_relative_to_output_root` to the row caveats. Tests will cover
same-root clickable links and divergent-root provenance text.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest tests/unit/texas_rrc/test_field_architecture_dossier_models.py -q
```

### Task 4 - Render summary and per-field HTML

Write failing tests for:

- HTML escaping of field names, operators, caveats, and follow-up text
- summary page class counts and source-gap display
- per-field page sections for opportunity, lifecycle/production,
  infrastructure, operator context, provenance, and limitations
- correct relative hrefs to source field-atlas pages from both the summary page
  and per-field dossier pages
- no remote JavaScript, remote CSS, or external image dependencies

Create `dossiers/html.py` with:

```python
def render_field_architecture_dossier_summary_html(
    index: pd.DataFrame,
    quality: FieldArchitectureDossierQuality,
) -> str:
    ...

def render_field_architecture_dossier_html(
    page: FieldArchitectureDossierPage,
) -> str:
    ...
```

The HTML will follow the restrained self-contained style used by
`reports/html.py` and `opportunities/html.py`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest tests/unit/texas_rrc/test_field_architecture_dossier_html.py -q
```

### Task 5 - Write staged outputs and quality metadata

Write failing tests for:

- staged write of CSV, Parquet, summary HTML, per-field HTML, quality JSON, and
  manifest JSON
- both `quality.json` and `field_architecture_dossier_quality.json` carrying
  identical JSON payloads
- stale output removal on rewrite
- non-ACE output rejection unless `allow_non_ace_root=True`
- manifest carrying input paths, upstream manifests, command, code revision,
  source gaps, selected row count, selection policy, and limitations

Create `dossiers/quality.py` and `dossiers/io.py` with:

```python
@dataclass(frozen=True)
class FieldArchitectureDossierQuality:
    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    architecture_class_counts: dict[str, int]
    selection_reason_counts: dict[str, int]
    caveat_counts: dict[str, int]
    quality_flag_counts: dict[str, int]
    limitation_count: int

def assess_field_architecture_dossier_quality(
    index: pd.DataFrame,
    blocking_source_gaps: tuple[str, ...],
    informational_source_gaps: tuple[str, ...],
) -> FieldArchitectureDossierQuality:
    ...
```

Output persistence will mirror the staged promote/backup behavior used by
`opportunities/io.py`, writing under:

```text
curated/analysis/field_architecture_dossiers/
```

The manifest will list both quality-file paths so downstream consumers can use
the issue-body generic name or the Texas RRC component-specific name without
guessing. `FieldArchitectureDossierOutputManifest` will be defined in
`dossiers/io.py` with paths for the CSV, Parquet, summary HTML, field directory,
both quality JSON files, manifest JSON, row count, input paths, upstream
manifests, command, code revision, blocking gaps, informational gaps, selection
policy, and limitation text.

The I/O layer parameter will be named `allow_non_ace_root`, matching existing
writer functions. CLI support will accept `allow_non_ace_output` and pass it
through to I/O as `allow_non_ace_root`. The CLI flag will remain
`--allow-non-ace-output`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest tests/unit/texas_rrc/test_field_architecture_dossier_io.py -q
```

### Task 6 - Add CLI support and documentation

Write failing CLI tests for:

- `worldenergydata texas-rrc build-field-architecture-dossiers` passing
  `--root`, `--output-root`, `--max-fields`, `--class-coverage-limit`,
  `--require-sources`, `--dry-run`, and `--allow-non-ace-output` to the support
  layer
- dry-run reporting blocking and informational gaps without writing outputs
- `--require-sources` failing on blocking source gaps
- successful write reporting output location and row count

Create `dossiers/cli_support.py` with:

```python
@dataclass(frozen=True)
class FieldArchitectureDossierBuildResult:
    row_count: int
    blocking_source_gaps: tuple[str, ...]
    informational_source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldArchitectureDossierOutputManifest | None

def run_build_field_architecture_dossiers(
    root: Path | str = SOURCE_CATALOG_ROOT,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    dry_run: bool = False,
    require_sources: bool = False,
    allow_non_ace_output: bool = False,
    max_fields: int = 25,
    class_coverage_limit: int = 3,
) -> FieldArchitectureDossierBuildResult:
    ...
```

The support layer will follow the existing field-opportunity fail-closed
pattern: if `inputs.blocking_source_gaps` is non-empty and the call is not a
dry-run, it will raise before writing. `--require-sources` will make dry-runs
fail on blocking gaps too. This makes the opportunity manifest mandatory for
publication while still allowing operators to inspect missing-source state
without writes. Informational upstream metric gaps will remain visible in the
dry-run result, quality JSON, and manifest, but will not block publication.
If rankings are present but no candidates are selected, dry-run will report
`no_dossier_candidates`; non-dry-run publication will fail before writing.

Modify `src/worldenergydata/cli/commands/texas_rrc.py` with a sibling Typer
command named `build-field-architecture-dossiers`.

Add `docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md`
documenting source lifecycle, refresh cadence, command examples, output
contract, selection policy, and limitations.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest \
  tests/unit/texas_rrc/test_field_architecture_dossier_cli.py -q
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest \
  tests/unit/texas_rrc/test_field_architecture_dossier_sources.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_selection.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_models.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_html.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_io.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_cli.py \
  -q
```

## TDD Test List

- `test_loads_field_opportunity_rankings_and_manifests`
- `test_records_missing_field_opportunity_rankings_gap`
- `test_records_missing_field_opportunity_manifest_gap`
- `test_records_unreadable_dossier_manifest_gap`
- `test_loads_upstream_manifests_from_opportunity_manifest`
- `test_loads_field_atlas_and_field_development_context`
- `test_splits_blocking_and_informational_source_gaps`
- `test_selects_default_top_ranked_candidates`
- `test_selection_adds_architecture_class_coverage`
- `test_selection_skips_coverage_for_classes_already_in_top_ranked_set`
- `test_selection_preserves_rank_order_after_deduplication`
- `test_selection_reason_uses_single_stable_token`
- `test_selection_uses_stable_tie_breakers`
- `test_selection_rejects_invalid_limits`
- `test_builds_dossier_pages_and_index_rows`
- `test_dossier_model_joins_context_by_district_and_field_number`
- `test_dossier_model_emits_production_trend_context`
- `test_dossier_model_preserves_caveats_flags_and_source_report_link`
- `test_dossier_model_uses_column_source_priority`
- `test_dossier_model_maps_unknown_architecture_focus_to_unclassified_review`
- `test_empty_dossier_selection_has_stable_index_columns`
- `test_summary_html_escapes_values_and_lists_source_gaps`
- `test_field_html_renders_required_sections_and_limitations`
- `test_dossier_html_links_to_source_field_atlas_pages_relatively`
- `test_dossier_html_renders_provenance_text_when_roots_diverge`
- `test_html_has_no_remote_dependencies`
- `test_writes_staged_dossier_outputs_quality_and_manifest`
- `test_writes_generic_and_component_quality_files_with_same_payload`
- `test_rewrite_removes_stale_dossier_outputs`
- `test_rejects_non_ace_dossier_output_without_override`
- `test_io_and_cli_use_explicit_non_ace_parameter_mapping`
- `test_build_field_architecture_dossiers_cli_calls_support_layer`
- `test_run_build_field_architecture_dossiers_dry_run_reports_missing_sources`
- `test_run_build_field_architecture_dossiers_requires_sources`
- `test_run_build_field_architecture_dossiers_rejects_empty_publication`

## Validation Gates

Before moving #702 from implementation to closeout, the implementation worker
will verify the uv workspace environment is synced, then run and record:

```bash
uv sync --all-packages --all-extras
PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync python -m pytest \
  tests/unit/texas_rrc/test_field_architecture_dossier_sources.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_selection.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_models.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_html.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_io.py \
  tests/unit/texas_rrc/test_field_architecture_dossier_cli.py \
  -q
scripts/legal/legal-sanity-scan.sh | tee scripts/review/results/2026-07-02-code-702-legal-sanity-scan.txt
```

The implementation will also receive code-stage adversarial review. Codex will
review the diff against the approved plan. Claude will serve as the second
actual reviewer when Gemini is unavailable. Gemini will still be attempted; if
the current Gemini CLI remains unavailable, the implementation worker will
write an `UNAVAILABLE` artifact with the exact authentication/client error and
will not represent the missing provider as an approval.

Implementation closeout will use a feature branch and PR. The branch will be
pushed, a PR will be opened, review and validation evidence will be posted on
the issue, and the PR will be merged before #702 can be closed. Any MAJOR
verdict from Codex or Claude will block closeout until patched or explicitly
waived by the user.

## Acceptance Criteria

1. The CLI will publish a deterministic dossier packet under
   `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_architecture_dossiers/`.
2. The default selection will include top-ranked opportunity candidates and
   bounded architecture-class coverage rows with stable `selection_reason`
   values.
3. Each selected field will have a machine-readable index row and a self-
   contained HTML dossier page.
4. Manifest and quality JSON will tie outputs to input paths, upstream
   manifests, code revision, blocking gaps, informational upstream gaps,
   selection policy, and limitation language.
5. The implementation will reject non-ACE output roots unless explicitly
   allowed for tests and sandbox runs.
6. Blocking source gaps will fail closed under `--require-sources` and for any
   non-dry-run write. Informational upstream gaps will remain visible in dry-run
   output and quality metadata without blocking publication.
7. Tests will cover source loading, selection, model assembly, HTML rendering,
   staged writes, output-root guardrails, quality summaries, and CLI behavior.
8. Documentation will describe lifecycle, refresh cadence, command usage,
   output contract, and screening limitations.
9. The deliverable will remain screening-only and will not claim reserves,
   economics, tariffs, pipeline capacity, right-of-way status, route feasibility,
   or engineered facility design.
10. Code-stage review artifacts and `scripts/legal/legal-sanity-scan.sh` evidence
    will be posted before closeout.

## Risks

- The #695 opportunity ranking currently assigns quality penalties to many top
  rows because the upstream RRC artifacts preserve important caveats. The
  dossier product will surface those caveats rather than suppressing them.
- Rare architecture classes can be hidden by a pure top-N selection. The
  class-coverage rule will reduce this risk while keeping output bounded.
- Field-atlas page links are relative to the field-atlas report directory, while
  dossier pages will live in a separate analysis directory. The implementation
  will keep the source link as a provenance reference and test that it is
  emitted consistently.
- The lifecycle spine manifest currently lacks command/code-revision detail.
  The dossier manifest will record that as upstream provenance rather than
  inventing missing metadata.

## Out Of Scope

- New Texas RRC raw refresh logic.
- New PatchOps integration or third-party scraper ingestion.
- Per-well production allocation.
- Reserves, economics, tariffs, capacity, right-of-way, route engineering, or
  facility-design calculations.
- Public web publishing outside `/mnt/ace` curated outputs.
