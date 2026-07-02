# Plan: Issue #695 - Texas RRC field opportunity and architecture-signal ranking

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/695
**Status:** plan-review
**Tier:** T2 (screening score contract, architecture-signal classification, `/mnt/ace` output contract, CLI, tests, docs)
**Client:** N/A
**Project:** worldenergydata onshore field development

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after user
approval. The work will remain behind the issue approval gate until this plan
is reviewed and approved by the user. Implementation will use TDD, with failing
tests written before production code for source loading, deterministic scoring,
architecture-signal classification, output persistence, HTML rendering, quality
reporting, and CLI behavior.

### Dependency and source status

Issues [#664](https://github.com/vamseeachanta/worldenergydata/issues/664),
[#665](https://github.com/vamseeachanta/worldenergydata/issues/665), and
[#666](https://github.com/vamseeachanta/worldenergydata/issues/666) are closed
and will be treated as required source-code prerequisites. Implementation will
still verify the live `/mnt/ace` filesystem before building rankings because
the ranking output depends on curated direct-source artifacts, not only merged
source code.

The current direct-source artifact inventory on `/mnt/ace` is:

| Input | Current rows | Current source gaps | Expected path | Planned use |
|---|---:|---|---|---|
| Field-atlas summary | 67,082 | none | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/field_atlas_summary.csv` | Primary per-field input for lifecycle, production scale, remaining activity, operator context, infrastructure access, caveats, report links |
| Field-atlas manifest | 67,082 rows / 67,082 pages | none | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/manifest.json` | Input provenance, generated timestamp, upstream input paths, code revision, report output references |
| Field-development metrics | 67,082 | none | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/field_development/metrics/field_development_metrics.csv` | Upstream fallback when the field-atlas summary is absent or stale |
| Infrastructure access metrics | 61,518 | none | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/infrastructure/access/field_infrastructure_access.csv` | Upstream fallback for GIS-derived pipeline access class and quality caveats |
| Production atlas | 470,505 | production metric gaps for water and well count | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/production_field_atlas.csv` | Upstream fallback for production totals and lease/operator detail if the report summary is absent |

PatchOps will remain validation-only. The ranking will use direct Texas RRC
source-derived artifacts only.

### Current code shape

- `worldenergydata.texas_rrc.reports` persists the #666 field-atlas summary,
  HTML report pages, report quality JSON, and manifest JSON.
- `worldenergydata.texas_rrc.field_development` persists the #664 lifecycle,
  production, operator, and activity metrics.
- `worldenergydata.texas_rrc.infrastructure` persists the #665 RRC GIS-derived
  pipeline access metrics.
- `worldenergydata.texas_rrc.production_atlas` persists field, lease, district,
  operator, and statewide production atlas rows.
- `worldenergydata texas-rrc` already hosts the onshore build commands and will
  receive a sibling command for opportunity ranking publication.

Implementation will create a Texas RRC-local `opportunities` package. It will
not import BSEE-specific offshore field-development models and will not extend
the #666 report publisher with ranking responsibility.

### Scoring and interpretation policy

The first scoring version will be a deterministic screening heuristic named
`texas_rrc_field_opportunity_v1`. It will not estimate reserves, NPV, tariffs,
pipeline capacity, commercial tie-in probability, or engineered facility
design. Component scores, weights, caveats, quality penalties, and the scoring
version will be emitted in the output manifest so downstream users can audit
why a field ranked where it did.

The scoring policy will be rank/percentile based where possible so outliers do
not dominate the output. Missing source values will reduce confidence through
the quality penalty and visible caveats instead of being fabricated.

The initial score formula will be:

```text
opportunity_score =
  0.35 * production_scale_component_score
  + 0.30 * remaining_activity_component_score
  + 0.20 * infrastructure_component_score
  + 0.10 * operator_concentration_component_score
  + 0.05 * active_well_component_score
  - quality_penalty_score
```

The final score will be clamped to `0..100`. The operator concentration
component will be treated as a decision-context signal, not as a commercial
preference. It will reward reliable operator context and identify concentrated
or fragmented fields in `key_drivers`; it will not assert that either condition
is economically superior.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review | `scripts/review/results/2026-07-02-plan-695-codex-inline.md` |
| Opportunity package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/__init__.py` |
| Source loading | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/sources.py` |
| Scoring | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/scoring.py` |
| Architecture signals | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/architecture.py` |
| HTML rendering | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/html.py` |
| Quality reporting | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/quality.py` |
| Output persistence | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/io.py` |
| CLI support | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/opportunities/cli_support.py` |
| CLI command | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_opportunity_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_opportunity_scoring.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_opportunity_architecture.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_opportunity_html.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_opportunity_io.py` |
| CLI tests | `tests/unit/texas_rrc/test_field_opportunity_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md` |

## Deliverable

The deliverable will publish Texas RRC field opportunity rankings under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/
  field_opportunity_rankings.csv
  field_opportunity_rankings.parquet
  field_opportunity_summary.html
  field_opportunity_quality.json
  manifest.json
```

The output will be keyed by:

```text
district, field_number
```

Stable output columns will include:

- `district`
- `field_number`
- `field_name`
- `field_slug`
- `report_path`
- `field_page_filename`
- `opportunity_rank`
- `opportunity_score`
- `opportunity_class`
- `production_scale_component_score`
- `remaining_activity_component_score`
- `infrastructure_component_score`
- `operator_concentration_component_score`
- `active_well_component_score`
- `quality_penalty_score`
- `architecture_signal_class`
- `architecture_signal_reason`
- `recommended_followup`
- `cumulative_boe`
- `production_per_well_boe`
- `remaining_activity_score`
- `active_well_count`
- `well_count`
- `production_maturity_class`
- `infrastructure_access_class`
- `infrastructure_access_score`
- `nearest_pipeline_distance_miles`
- `nearby_pipeline_count_1mi`
- `nearby_pipeline_count_5mi`
- `nearby_pipeline_count_10mi`
- `top_operator_name`
- `top_operator_share`
- `key_drivers`
- `source_caveats`
- `quality_flags`

`manifest.json` will include:

- generated timestamp
- code revision
- command
- output paths
- input artifact paths and upstream manifest paths
- row counts
- source gaps
- scoring version
- scoring weights
- score column contract
- architecture class vocabulary
- caveat and quality summaries

## Architecture Signal Contract

The implementation will classify every ranked field into one of these
screening-signal classes:

- `high_access_infill_redevelopment`
- `infrastructure_constrained_activity`
- `mature_harvest`
- `emerging_growth`
- `low_data_confidence`
- `monitor_only`

These are screening labels, not engineered architecture decisions. They will
describe why a field should receive follow-up review and what data blocks a
stronger conclusion.

The first implementation will use these deterministic rules, evaluated in this
order:

1. If field caveats or quality flags include missing lifecycle, missing
   infrastructure access, missing well GIS, or a `not_available`
   infrastructure class, classify as `low_data_confidence` unless production
   scale and activity are both in the top quartile.
2. If production maturity is `growth` or `early_development` and remaining
   activity plus infrastructure access are strong, classify as
   `emerging_growth`.
3. If infrastructure access is `direct_access` or `near_access`, cumulative BOE
   is high, and remaining activity is moderate or high, classify as
   `high_access_infill_redevelopment`.
4. If remaining activity is high but infrastructure access is `regional_access`,
   `remote_access`, `isolated_or_unknown`, or missing, classify as
   `infrastructure_constrained_activity`.
5. If production maturity is `late_life` or `mature_active` and remaining
   activity is low, classify as `mature_harvest`.
6. Otherwise classify as `monitor_only`.

Each row will include `architecture_signal_reason` and `recommended_followup`
text assembled from deterministic reason codes. The text will preserve caveats
such as lease-level production allocation, no per-well production allocation,
RRC GIS screening-only distance, missing well GIS, dominant-county pipeline
filtering, and unavailable water/well-count metrics.

## Plan

### Task 1 - Load and validate opportunity inputs

Write failing tests for a tiny input root with:

- #666 field-atlas summary CSV and manifest JSON
- optional upstream field-development, infrastructure, and production manifests
- missing summary behavior
- stale or unreadable manifest behavior

Create `opportunities/sources.py` with:

```python
@dataclass(frozen=True)
class FieldOpportunityInputs:
    field_atlas_summary: pd.DataFrame
    input_paths: tuple[Path, ...]
    source_gaps: tuple[str, ...]
    upstream_manifests: tuple[Path, ...]

def load_field_opportunity_inputs(root: Path | str) -> FieldOpportunityInputs:
    ...
```

The loader will prefer the #666 Parquet summary and fall back to CSV. It will
record missing inputs as `missing_field_atlas_summary` and unreadable manifests
as `unreadable_manifest`. It will not call PatchOps or fetch network data.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_opportunity_sources.py -q
```

### Task 2 - Build deterministic opportunity scores

Write failing tests that prove:

- score columns are emitted for every input field
- rank/percentile normalization is deterministic for tied values
- missing numeric values become zero component scores and add quality penalty
- source caveats and quality flags increase quality penalty
- `opportunity_score` is clamped to `0..100`
- `opportunity_rank` sorts by descending score, then `district`,
  `field_number`, and `field_name`

Create `opportunities/scoring.py` with:

```python
SCORING_VERSION = "texas_rrc_field_opportunity_v1"

SCORING_WEIGHTS = {
    "production_scale_component_score": 0.35,
    "remaining_activity_component_score": 0.30,
    "infrastructure_component_score": 0.20,
    "operator_concentration_component_score": 0.10,
    "active_well_component_score": 0.05,
}

def build_field_opportunity_rankings(inputs: FieldOpportunityInputs) -> pd.DataFrame:
    ...
```

The scoring code will emit component columns, the final score, rank, class,
driver strings, caveats, and quality flags. It will not drop rows with poor
data quality; poor rows will remain visible with lower confidence and explicit
caveats.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_opportunity_scoring.py -q
```

### Task 3 - Add architecture-signal classification

Write failing tests for each architecture class:

- direct/near infrastructure, high production, and activity will produce
  `high_access_infill_redevelopment`
- high activity with poor access will produce
  `infrastructure_constrained_activity`
- late-life or mature-active fields with low activity will produce
  `mature_harvest`
- growth or early-development fields with strong access/activity will produce
  `emerging_growth`
- missing lifecycle, GIS, or infrastructure evidence will produce
  `low_data_confidence` unless production and activity are both top-quartile
- remaining rows will produce `monitor_only`

Create `opportunities/architecture.py` with:

```python
@dataclass(frozen=True)
class ArchitectureSignal:
    architecture_signal_class: str
    architecture_signal_reason: str
    recommended_followup: str

def classify_architecture_signal(row: Mapping[str, object]) -> ArchitectureSignal:
    ...
```

The classifier will consume component scores, maturity class, infrastructure
class, caveats, and quality flags. It will return deterministic reason text
without implying engineered design, facility sizing, commercial capacity, or
reserves.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_opportunity_architecture.py -q
```

### Task 4 - Persist ranking, quality, manifest, and HTML summary

Write failing tests that prove:

- CSV, Parquet, quality JSON, manifest JSON, and HTML are written under the
  field-opportunity output directory
- non-`/mnt/ace` output roots are rejected unless explicitly allowed for tests
- stale outputs are removed through the same staging/promote pattern used by
  the #666 report writer
- manifest JSON includes scoring version, weights, command, source gaps, input
  paths, upstream manifests, and row count
- quality JSON includes score distribution, architecture class counts,
  opportunity class counts, caveat counts, quality flag counts, and low-data
  confidence counts

Create `opportunities/io.py`, `opportunities/quality.py`, and
`opportunities/html.py`.

The HTML summary will be a deterministic, self-contained report with:

- top-ranked opportunity table
- architecture-signal distribution
- opportunity-score distribution
- caveat and quality summary
- links back to the #666 field deep-dive pages through `report_path`
- visible limitations explaining that rankings are screening heuristics only

Verification:

```bash
uv run --no-sync pytest \
  tests/unit/texas_rrc/test_field_opportunity_io.py \
  tests/unit/texas_rrc/test_field_opportunity_html.py -q
```

### Task 5 - Add CLI support and docs

Write failing tests that prove the CLI calls the support layer with:

- `--root`
- `--output-root`
- `--dry-run`
- `--require-sources`
- `--max-fields`
- `--allow-non-ace-output`

Create `opportunities/cli_support.py` with:

```python
@dataclass(frozen=True)
class FieldOpportunityBuildResult:
    row_count: int
    source_gaps: tuple[str, ...]
    dry_run: bool
    manifest: FieldOpportunityOutputManifest | None

def run_build_field_opportunities(
    root: Path | str = SOURCE_CATALOG_ROOT,
    output_root: Path | str = SOURCE_CATALOG_ROOT,
    dry_run: bool = False,
    require_sources: bool = False,
    allow_non_ace_output: bool = False,
    max_fields: int | None = None,
) -> FieldOpportunityBuildResult:
    ...
```

Add `worldenergydata texas-rrc build-field-opportunities` in
`src/worldenergydata/cli/commands/texas_rrc.py`.

Add `docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md` with:

- lifecycle/source chain from official Texas RRC raw data through #666 summary
- refresh cadence inherited from the Texas RRC source catalog and raw refresh
  commands
- output contract and scoring version
- architecture-signal vocabulary
- direct-source caveats
- explicit limitations: no reserves, no economics, no tariff, no capacity, no
  right-of-way, no engineered facility design

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_opportunity_cli.py -q
```

### Task 6 - Publish to `/mnt/ace` and verify

After the tests pass, run a bounded smoke build:

```bash
uv run --no-sync worldenergydata texas-rrc build-field-opportunities \
  --root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --require-sources \
  --max-fields 100
```

Then run the full publication:

```bash
uv run --no-sync worldenergydata texas-rrc build-field-opportunities \
  --root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --require-sources
```

Verify the output directory:

```bash
test -s /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/field_opportunity_rankings.csv
test -s /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/field_opportunity_rankings.parquet
test -s /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/field_opportunity_summary.html
test -s /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/field_opportunity_quality.json
test -s /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/analysis/field_opportunities/manifest.json
```

Final verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_opportunity_*.py -q
uv run --no-sync pytest tests/unit/texas_rrc -q
```

If `scripts/legal/legal-sanity-scan.sh` is available in the active checkout,
run it before merge. If it is absent, record the absence in the implementation
PR closeout instead of claiming the legal scan passed.

## Risks and Controls

| Risk | Control |
|---|---|
| Heuristic weights can be mistaken for economics. | Emit scoring version, component scores, weights, caveats, and limitations in machine-readable outputs and docs. |
| Architecture labels can be mistaken for engineered design. | Use `architecture_signal_*` naming and visible limitation text; do not emit facility sizing or tie-in design. |
| Missing GIS/lifecycle data can distort ranking. | Keep every row, add quality penalties, classify low-confidence rows, and preserve source caveats. |
| Field names can repeat across districts. | Key and sort by `district, field_number`; keep field name descriptive only. |
| #666 manifest code revision includes `+dirty` because the artifact was generated before merge. | Treat it as provenance, not as a source gap; record it in the downstream manifest. |
| PatchOps could accidentally become an input dependency. | Keep PatchOps out of source loading and docs as validation-only context. |
| Full 67,082-row publication can expose runtime or output-size issues. | Keep `--max-fields` for bounded smoke tests, then run full `/mnt/ace` publication and verify output file presence. |

## Approval Gate

Implementation must not start until:

1. this plan has an adversarial review artifact,
2. [#695](https://github.com/vamseeachanta/worldenergydata/issues/695) is
   moved from `status:needs-plan` to `status:plan-review`, and
3. the user explicitly approves the plan and the issue is labeled
   `status:plan-approved`.
