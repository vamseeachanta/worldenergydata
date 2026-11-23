# Plan: Issue #666 - Texas RRC onshore field atlas and deep-dive reports

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/666
**Status:** plan-approved
**Tier:** T2 (HTML report generation, field-page fanout, manifest/provenance, `/mnt/ace` output contract, CLI, tests)
**Client:** N/A
**Project:** worldenergydata onshore field development

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after user
approval. The work will remain behind the issue approval gate until this plan
is reviewed and approved by the user. Implementation will use TDD, with failing
tests written before production code for source loading, summary assembly, HTML
rendering, stable filenames/links, output persistence, and CLI behavior.

### Dependency and source status

Issues [#663](https://github.com/vamseeachanta/worldenergydata/issues/663),
[#664](https://github.com/vamseeachanta/worldenergydata/issues/664), and
[#665](https://github.com/vamseeachanta/worldenergydata/issues/665) are closed
and will be treated as required source-code prerequisites. Implementation will
still verify the live `/mnt/ace` filesystem before building reports because the
report output depends on curated data artifacts, not only merged source code.

The current direct-source artifact inventory on `/mnt/ace` is:

| Input | Current rows | Expected path | Planned use |
|---|---:|---|---|
| Field-development metrics | 67,082 | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/field_development/metrics/field_development_metrics.csv` | Field list, rankings, lifecycle summary, operator/lease context, maturity, activity score |
| Infrastructure access metrics | 61,518 | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/infrastructure/access/field_infrastructure_access.csv` | Pipeline-access class, distances, nearby pipeline counts, GIS caveats |
| Production atlas | 470,505 | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/production_field_atlas.csv` | Field rows and lease rows for production and top lease/operator detail |

PatchOps will remain validation-only. Report content will use direct Texas RRC
source-derived artifacts only.

### Current code shape

- `worldenergydata.texas_rrc.field_development` persists field metrics and can
  load CSV/Parquet outputs.
- `worldenergydata.texas_rrc.infrastructure` persists field infrastructure
  access metrics and can load CSV/Parquet outputs.
- `worldenergydata.texas_rrc.production_atlas` persists field, lease,
  district, operator, and statewide production atlas rows.
- `worldenergydata texas-rrc` already hosts the onshore build commands.
- BSEE report modules provide useful precedent for all-fields and per-field
  HTML pages, but the Texas RRC implementation will live inside the Texas RRC
  package and will not import BSEE-specific OGOR loaders or offshore field
  assumptions.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review | `scripts/review/results/2026-07-01-plan-666-codex-inline.md` |
| Report package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/__init__.py` |
| Source loading | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/sources.py` |
| Report models/assembly | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/field_atlas.py` |
| HTML rendering | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/html.py` |
| Report quality/provenance | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/quality.py` |
| Report I/O | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/io.py` |
| CLI support | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports/cli_support.py` |
| CLI command | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_atlas_report_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_atlas_report_models.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_atlas_report_html.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_atlas_report_io.py` |
| CLI tests | `tests/unit/texas_rrc/test_field_atlas_report_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/field-atlas-reports.md` |

## Deliverable

The deliverable will publish a Texas RRC onshore field atlas under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/
  index.html
  fields/
    <district>-<field_number>-<field_slug>.html
  field_atlas_summary.csv
  field_atlas_summary.parquet
  field_atlas_report_quality.json
  manifest.json
```

The report will be a deterministic, self-contained HTML artifact set. It will
not require network access, external JavaScript, PatchOps, or browser-side data
fetching to render.

The output will preserve the direct-source caveats from #663, #664, and #665.
It will not claim reserves, economics, commercial pipeline capacity, pipeline
tariff availability, engineered tie-in feasibility, or survey-grade distances.

## Output Contract

`field_atlas_summary.csv` and `.parquet` will include one row per reportable
field, keyed by `district, field_number`, with stable columns:

- `district`
- `field_number`
- `field_name`
- `field_slug`
- `report_path`
- `field_page_filename`
- `well_count`
- `active_well_count`
- `permit_count`
- `completion_count`
- `production_maturity_class`
- `remaining_activity_score`
- `rank_cumulative_boe`
- `rank_remaining_activity`
- `rank_well_density_proxy`
- `cumulative_oil_bbl`
- `cumulative_gas_mcf`
- `cumulative_condensate_bbl`
- `cumulative_boe`
- `production_per_well_boe`
- `lease_count`
- `operator_count`
- `top_operator_number`
- `top_operator_name`
- `top_operator_share`
- `infrastructure_access_class`
- `infrastructure_access_score`
- `nearest_pipeline_distance_miles`
- `nearby_pipeline_count_1mi`
- `nearby_pipeline_count_5mi`
- `nearby_pipeline_count_10mi`
- `source_caveats`
- `quality_flags`

`manifest.json` will include:

- generated timestamp
- code revision
- command
- output paths
- input artifact paths and upstream manifest paths
- row/page counts
- source gaps
- caveat vocabulary
- quality summary

## Report Content Contract

### All-fields `index.html`

The all-fields page will include:

- top-level summary cards for field count, cumulative BOE, producing fields,
  reportable fields with infrastructure access, and source-gap counts
- sortable/scannable top-field table by cumulative BOE and remaining activity
- operator concentration table using `top_operator_name` and cumulative BOE
- infrastructure-access distribution
- maturity-class distribution
- links to every generated field deep-dive page
- visible caveat block explaining direct-source grain and screening limitations

### Per-field pages

Each field page will include:

- field identity: district, field number, field name, page generation timestamp
- lifecycle summary: well count, active/plugged wells, permit/completion counts,
  horizontal/directional share, lifecycle timing
- production summary: cumulative oil, gas, condensate, BOE, production per well,
  first/last production month, still-producing flag, maturity class
- lease/operator context: lease count, operator count, top operator and share
- infrastructure access: access class, score, nearest pipeline distance,
  nearby pipeline counts, GIS caveats
- source provenance: input artifacts and upstream manifest references
- quality/caveat block: source caveats and quality flags for the field

The first implementation will use compact HTML tables and inline SVG/CSS bar
visuals generated from the summary data. It will not add a JavaScript charting
dependency unless implementation discovery finds an already-approved local
reporting helper that supports fully self-contained HTML output.

## Plan

### Task 1 - Load and validate report inputs

Write failing tests for a tiny report input root with:

- field-development metrics CSV
- infrastructure access CSV
- production atlas CSV with field and lease rows
- upstream manifests for each curated input

Create `reports/sources.py` with:

```python
@dataclass(frozen=True)
class FieldAtlasReportInputs:
    field_development: pd.DataFrame
    infrastructure_access: pd.DataFrame
    production_atlas: pd.DataFrame
    input_paths: tuple[str, ...]
    source_gaps: tuple[str, ...]

def load_field_atlas_report_inputs(root: Path | str) -> FieldAtlasReportInputs:
    ...
```

The loader will prefer Parquet when available and fall back to CSV. It will
record missing inputs as `field_development_metrics`,
`infrastructure_access_metrics`, and `production_field_atlas`.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_atlas_report_sources.py -q
```

### Task 2 - Assemble field report summary rows

Write failing tests that prove:

- fields from #664 remain reportable even when #665 infrastructure rows are
  missing
- infrastructure rows join by `district, field_number`
- lease rows from the production atlas are filtered to the field page context
- source caveats from field-development and infrastructure inputs are merged
  without duplicates
- slugs and filenames are stable for names with spaces, punctuation, and empty
  names

Create `reports/field_atlas.py` with:

```python
@dataclass(frozen=True)
class FieldAtlasPage:
    district: str
    field_number: str
    field_name: str
    filename: str
    summary: dict[str, object]
    leases: tuple[dict[str, object], ...]
    source_caveats: tuple[str, ...]
    quality_flags: tuple[str, ...]

def build_field_atlas_pages(inputs: FieldAtlasReportInputs) -> tuple[FieldAtlasPage, ...]:
    ...

def build_field_atlas_summary(pages: tuple[FieldAtlasPage, ...]) -> pd.DataFrame:
    ...
```

Summary rows will sort by `rank_cumulative_boe`, then district, field number,
and field name.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_atlas_report_models.py -q
```

### Task 3 - Render deterministic self-contained HTML

Write failing tests that assert generated HTML contains:

- `<!doctype html>`, `<html>`, and closing `</html>`
- all-fields report title and summary cards
- per-field links with stable relative paths
- per-field production, lifecycle, operator, and infrastructure sections
- direct-source caveat copy
- no remote `http://` or `https://` script/style dependencies

Create `reports/html.py` with:

```python
def render_index_html(summary: pd.DataFrame, pages: tuple[FieldAtlasPage, ...]) -> str:
    ...

def render_field_html(page: FieldAtlasPage) -> str:
    ...
```

HTML will escape field names, operator names, and caveats. Empty/null metrics
will render as `Not available` rather than `nan`.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_atlas_report_html.py -q
```

### Task 4 - Persist report outputs with manifest and quality

Write failing tests that assert:

- writes are staged before promotion
- non-ACE output roots are rejected by default
- `allow_non_ace_root=True` allows isolated test output
- index and field pages are written with relative links
- summary CSV/Parquet, quality JSON, and manifest JSON are written
- manifest references all input artifacts

Create `reports/quality.py` with a `FieldAtlasReportQualityReport` dataclass
and `reports/io.py` with:

```python
FIELD_ATLAS_REPORT_DIR = Path("curated") / "reports" / "field_atlas"

def write_field_atlas_report_outputs(
    pages: tuple[FieldAtlasPage, ...],
    summary: pd.DataFrame,
    quality: FieldAtlasReportQualityReport,
    output_root: Path | str,
    input_paths: Iterable[str | Path],
    allow_non_ace_root: bool = False,
    command: str | None = None,
    code_revision: str | None = None,
) -> FieldAtlasReportOutputManifest:
    ...
```

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_atlas_report_io.py -q
```

### Task 5 - Add CLI command

Write failing CLI tests for:

- missing source behavior with `--require-sources`
- dry-run row/page counts without writes
- sandbox writes with `--allow-non-ace-output`
- normal write output paths

Create `reports/cli_support.py` and extend `src/worldenergydata/cli/commands/texas_rrc.py`
with:

```bash
worldenergydata texas-rrc publish-field-atlas-reports
```

CLI options will include:

- `--root`
- `--output-root`
- `--dry-run`
- `--require-sources`
- `--allow-non-ace-output`
- `--max-fields` for bounded fixture/smoke runs

The command will not refresh or rebuild upstream sources implicitly. It will
report missing upstream artifacts and will document the prerequisite commands.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_atlas_report_cli.py -q
```

### Task 6 - Documentation and direct `/mnt/ace` publication run

Add `docs/data-sources/onshore/texas-rrc/field-atlas-reports.md` documenting:

- direct-source inputs
- prerequisite build commands
- report generation command
- output paths
- stable output columns
- report caveats
- refresh cycle inherited from upstream RRC sources

After tests pass, run:

```bash
uv run --no-sync worldenergydata texas-rrc publish-field-atlas-reports --require-sources
```

The run will write the report artifacts under `/mnt/ace`. If the repository
virtual environment is slow or unavailable, implementation may use a temporary
Python target outside the repo, but it must remove that target before closeout
and must record the exact command used in the PR.

Verification:

```bash
test -f /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/index.html
test -f /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/field_atlas_summary.csv
test -f /mnt/ace/worldenergydata/data/modules/texas_rrc/curated/reports/field_atlas/manifest.json
```

## Acceptance Criteria Mapping

| Acceptance criterion | Planned evidence |
|---|---|
| Report generation produces an all-fields HTML index and per-field deep-dive HTML pages from local curated inputs. | Tasks 2, 3, 4, and 5 tests plus `/mnt/ace` publication run |
| Reports include production profile, lifecycle summary, infrastructure access metrics, operator/lease context, source provenance, and data caveats. | Tasks 2 and 3 rendering tests |
| Machine-readable outputs include field summary CSV/Parquet and manifest/provenance files. | Task 4 I/O tests and manifest assertions |
| Tests cover report rendering from fixtures, missing-domain caveats, and stable links/filenames. | Tasks 1, 2, 3, 4, and 5 tests |
| Documentation includes the exact regenerate command and expected output locations. | Task 6 docs |

## Verification Plan

Run focused tests:

```bash
uv run --no-sync pytest \
  tests/unit/texas_rrc/test_field_atlas_report_sources.py \
  tests/unit/texas_rrc/test_field_atlas_report_models.py \
  tests/unit/texas_rrc/test_field_atlas_report_html.py \
  tests/unit/texas_rrc/test_field_atlas_report_io.py \
  tests/unit/texas_rrc/test_field_atlas_report_cli.py \
  -q
```

Run Texas RRC regression tests:

```bash
uv run --no-sync pytest tests/unit/texas_rrc -q
```

Run formatting and lint checks on touched files:

```bash
uv run --no-sync black --check \
  packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports \
  tests/unit/texas_rrc/test_field_atlas_report_*.py \
  src/worldenergydata/cli/commands/texas_rrc.py
uv run --no-sync isort --check-only \
  packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports \
  tests/unit/texas_rrc/test_field_atlas_report_*.py \
  src/worldenergydata/cli/commands/texas_rrc.py
uv run --no-sync flake8 \
  packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/reports \
  tests/unit/texas_rrc/test_field_atlas_report_*.py \
  src/worldenergydata/cli/commands/texas_rrc.py
```

Run available repository enforcement checks:

```bash
test -x scripts/enforcement/check-no-conflict-markers.sh && scripts/enforcement/check-no-conflict-markers.sh
test -x scripts/legal/legal-sanity-scan.sh && scripts/legal/legal-sanity-scan.sh
```

## Out Of Scope

- New source refresh logic for #663, #664, or #665 inputs.
- PatchOps ingestion.
- Economics, reserves, tariff, right-of-way, pipeline-capacity, or engineered
  tie-in claims.
- PDF export.
- Web deployment or GitHub Pages publishing.
- Interactive maps requiring external tiles or network access.

## Risk Controls

- The implementation will fail closed on missing required sources when
  `--require-sources` is passed.
- The report output root will default to `/mnt/ace` and reject non-ACE writes
  unless tests explicitly pass `allow_non_ace_root=True`.
- All generated links will be relative and stable.
- Null metrics will be visible as missing, not silently converted to zero.
- Source caveats will be shown in both all-fields and per-field pages.
- Generated HTML will be self-contained and will not load remote scripts.

## Approval Gate

This plan is ready for adversarial review and user approval. Implementation
must not begin until the user approves [#666](https://github.com/vamseeachanta/worldenergydata/issues/666)
for `status:plan-approved`.
