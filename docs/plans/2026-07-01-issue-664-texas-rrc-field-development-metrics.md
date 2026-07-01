# Plan: Issue #664 - Texas RRC field-development metrics

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/664
**Status:** plan-review
**Tier:** T2 (direct-source hardening, lifecycle-production join, `/mnt/ace` output contract, CLI, tests)
**Client:** N/A
**Project:** worldenergydata onshore field development

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after user
approval. The work will remain behind the issue approval gate until this plan is
reviewed and approved by the user. Implementation will use TDD, with failing
tests written before production code for direct-source hardening, source
loading, metric classification, output persistence, and CLI behavior.

### Dependency and source status

Issues [#660](https://github.com/vamseeachanta/worldenergydata/issues/660),
[#661](https://github.com/vamseeachanta/worldenergydata/issues/661),
[#662](https://github.com/vamseeachanta/worldenergydata/issues/662),
[#663](https://github.com/vamseeachanta/worldenergydata/issues/663), and
[#669](https://github.com/vamseeachanta/worldenergydata/issues/669) will be
treated as completed prerequisite code. Implementation will still verify the
actual `/mnt/ace` filesystem before building metrics because the field metrics
join depends on curated lifecycle and production artifacts, not only merged
source code.

Implementation will use these direct Texas RRC source-derived artifacts:

| Input | Expected path | Required behavior |
|---|---|---|
| Lifecycle spine | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/well_lifecycle/spine/well_lifecycle_spine.csv` | Load as the well/API source of record and fail closed if absent unless `--build-missing-lifecycle` is passed |
| Production atlas | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/production_field_atlas.parquet` | Load field-level atlas rows and preserve PDQ lease-level caveats |
| Lifecycle quality | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/well_lifecycle/spine/well_lifecycle_quality.json` | Copy source gaps into the field-development quality report |
| Production quality | `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/production/field_atlas/production_field_atlas_quality.json` | Copy unavailable water/well-count metric gaps into the field-development quality report |

PatchOps, EWA web forms, and third-party scraper code will remain validation
surfaces only. They will not be durable inputs for this issue.

### Current code shape

- `worldenergydata.texas_rrc.lifecycle` can normalize local raw lifecycle
  snapshots and write the curated lifecycle spine.
- `worldenergydata.texas_rrc.production_atlas` can build and load field,
  lease, district, operator, and statewide production atlas rows.
- `worldenergydata texas-rrc normalize-lifecycle` and
  `worldenergydata texas-rrc build-production-atlas` already define the
  upstream command pattern, output-root policy, and test override behavior.
- No `worldenergydata.texas_rrc.field_development` package exists yet.
- No CLI command joins lifecycle and production into engineering-facing field
  development metrics.

### Pre-implementation data hardening to include

Implementation will first make the upstream direct-source prerequisites
repeatable enough for #664:

- GoDrive directory refresh will deduplicate selected directory entries by
  target filename before download/promotion so repeated completion ZIP entries
  do not fail a refresh.
- The lifecycle wellbore reader will handle the official headerless Wellbore
  Query CSV shape by applying an explicit RRC wellbore column map for the
  columns needed by the lifecycle spine.
- The lifecycle reader will report malformed source rows in quality metadata
  rather than silently dropping direct-source coverage.

These fixes will stay scoped to direct-source reliability needed to build the
field-development metrics. They will not introduce PatchOps or EWA as durable
data sources.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review | `scripts/review/results/2026-07-01-plan-664-codex-inline.md` |
| Directory refresh hardening tests | `tests/unit/texas_rrc/test_raw_refresh_directory.py` |
| Lifecycle direct-source tests | `tests/unit/texas_rrc/test_lifecycle_sources.py` |
| Directory refresh hardening | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/raw_directory.py` |
| Lifecycle source reader hardening | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/sources.py` |
| Lifecycle alias/schema contract | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/lifecycle_column_aliases.yml` |
| Field-development package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/field_development/__init__.py` |
| Field-development source loading | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/field_development/sources.py` |
| Field-development metrics | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/field_development/metrics.py` |
| Field-development quality | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/field_development/quality.py` |
| Field-development I/O | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/field_development/io.py` |
| CLI | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_development_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_development_metrics.py` |
| Unit tests | `tests/unit/texas_rrc/test_field_development_io.py` |
| CLI tests | `tests/unit/texas_rrc/test_field_development_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/field-development-metrics.md` |

## Deliverable

The deliverable will build deterministic Texas RRC field-development metrics by
joining the curated lifecycle spine and the field-level production atlas. It
will write:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/field_development/metrics/
  field_development_metrics.csv
  field_development_metrics.parquet
  field_development_metrics_quality.json
  manifest.json
```

The output will rank fields by cumulative production, remaining activity, well
density proxy, and development maturity. It will preserve source caveats for
lease-level production and partial per-well allocation. It will not compute
pipeline proximity, GIS acreage density, field economics, or publish HTML/PDF
reports; those remain in [#665](https://github.com/vamseeachanta/worldenergydata/issues/665)
and [#666](https://github.com/vamseeachanta/worldenergydata/issues/666).

## Output Contract

Stable output columns will include:

- `district`
- `field_number`, `field_name`
- `well_count`
- `active_well_count`, `plugged_well_count`
- `permit_count`, `completion_count`
- `horizontal_well_count`, `directional_well_count`
- `horizontal_directional_share`
- `median_permit_to_completion_days`
- `median_completion_to_first_production_days`
- `first_production_month`, `last_production_month`
- `still_producing`
- `production_maturity_class`
- `cumulative_oil_bbl`, `cumulative_gas_mcf`,
  `cumulative_condensate_bbl`, `cumulative_boe`
- `production_per_well_boe`
- `lease_count`, `operator_count`
- `well_density_proxy`, `well_density_basis`
- `remaining_activity_score`
- `rank_cumulative_boe`
- `rank_remaining_activity`
- `rank_well_density_proxy`
- `rank_development_maturity`
- `top_operator_number`, `top_operator_name`, `top_operator_share`
- `source_caveats`
- `quality_flags`

`well_density_proxy` will use `well_count / lease_count` with
`well_density_basis = wells_per_lease` until GIS acreage from
[#665](https://github.com/vamseeachanta/worldenergydata/issues/665) is
available. It will not be presented as a true surface-area density.

`source_caveats` will include pipe-delimited values such as
`lease_level_production`, `no_per_well_allocation`,
`missing_lifecycle_dates`, `missing_production`, `missing_lifecycle`, and
`water_and_well_count_unavailable_from_pdq`.

## Plan

### Task 1 - Harden direct lifecycle source refresh and parsing

Write failing tests in `tests/unit/texas_rrc/test_raw_refresh_directory.py`
for a GoDrive directory page that contains duplicate entries with the same
filename and command ID. The expected refresh plan will contain one selected
file per target filename.

Write failing tests in `tests/unit/texas_rrc/test_lifecycle_sources.py` for
the official headerless Wellbore Query CSV row shape. The fixture will include
the fields needed by the lifecycle spine: district, county, API unique number,
oil/gas type, lease name, field number/name, lease number, operator
number/name, total depth, well status, completion date, plug date, and profile
signals.

Modify `raw_directory.py` so `_select_by_filename_date` returns unique selected
files by `(filename, target_path)` while preserving deterministic order.

Modify `lifecycle/sources.py` and `lifecycle_column_aliases.yml` so
`wellbore_query` can load both headed fixture CSVs and the official headerless
RRC CSV. The parser will assign explicit column names only when the first row
does not look like a header.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_raw_refresh_directory.py tests/unit/texas_rrc/test_lifecycle_sources.py -q
```

### Task 2 - Add field-development source loader

Create `field_development/sources.py` with these public interfaces:

```python
@dataclass(frozen=True)
class FieldDevelopmentInputs:
    lifecycle: pd.DataFrame
    production: pd.DataFrame
    lifecycle_quality: dict[str, object]
    production_quality: dict[str, object]
    source_gaps: tuple[str, ...]

def load_field_development_inputs(root: Path | str) -> FieldDevelopmentInputs:
    """Load curated lifecycle and production inputs from a local Texas RRC root."""
```

The loader will read the lifecycle spine CSV with lifecycle API key dtypes and
the production atlas Parquet when available, falling back to CSV only when the
Parquet file is absent. It will filter production to `aggregation_level ==
"field"`. It will return source gaps instead of raising when lifecycle,
production, or quality files are missing.

Create `tests/unit/texas_rrc/test_field_development_sources.py` with fixtures
covering complete inputs, missing lifecycle, missing production, missing
quality JSON, and CSV fallback.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_development_sources.py -q
```

### Task 3 - Build lifecycle-production field metrics

Create `field_development/metrics.py` with this public interface:

```python
def build_field_development_metrics(inputs: FieldDevelopmentInputs) -> pd.DataFrame:
    """Join lifecycle and production inputs into field-level development metrics."""
```

The implementation will aggregate lifecycle rows by `district` and
`field_number`, then left/full join production field rows on the same keys.
Lifecycle-only fields will remain in the output with `missing_production` in
`source_caveats`. Production-only fields will remain with `missing_lifecycle`.

Metric definitions:

- `well_count`: count of lifecycle rows by field.
- `active_well_count`: count of lifecycle rows whose status contains
  `PRODUCING`, `ACTIVE`, `FLOWING`, or `SHUT IN`.
- `plugged_well_count`: count of lifecycle rows whose status contains
  `PLUG`.
- `horizontal_well_count` and `directional_well_count`: counts from
  `wellbore_profile` and `well_type` text signals.
- `horizontal_directional_share`: horizontal plus directional count divided by
  `well_count`, null when `well_count` is zero.
- `median_permit_to_completion_days`: median days from `permit_issued_date` to
  `completion_date` for rows with valid date ordering.
- `median_completion_to_first_production_days`: median days from lifecycle
  `completion_date` to the field's `first_production_month`.
- `production_per_well_boe`: field `cumulative_boe / well_count`, null when no
  lifecycle well count exists.
- `remaining_activity_score`: average of active-well share and production
  currentness indicator, bounded to `0.0..1.0`.
- `well_density_proxy`: `well_count / lease_count`, null when `lease_count` is
  zero or missing.

Maturity classes:

| Class | Rule |
|---|---|
| `pre_production` | lifecycle exists and cumulative BOE is missing or zero |
| `early_development` | first production exists and production span is under 24 months |
| `growth` | still producing and span is 24 to 84 months |
| `mature_active` | still producing and span is over 84 months |
| `late_life` | production exists but `still_producing` is false |
| `unknown` | neither lifecycle nor production evidence is sufficient |

Create `tests/unit/texas_rrc/test_field_development_metrics.py` covering:

- lifecycle-production joins by field key
- missing production
- missing lifecycle
- missing lifecycle dates
- invalid date ordering
- production maturity classification
- rank output ordering
- well-density proxy caveat
- no per-well allocation caveat

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_development_metrics.py -q
```

### Task 4 - Add quality report and `/mnt/ace` output writer

Create `field_development/quality.py` with:

```python
@dataclass(frozen=True)
class FieldDevelopmentQualityReport:
    row_count: int
    source_gaps: tuple[str, ...]
    caveat_counts: dict[str, int]
    maturity_counts: dict[str, int]

def assess_field_development_quality(
    metrics: pd.DataFrame,
    inputs: FieldDevelopmentInputs,
) -> FieldDevelopmentQualityReport:
    """Summarize field-development caveats, maturity mix, and source gaps."""
```

Create `field_development/io.py` with
`write_field_development_outputs(metrics: pd.DataFrame, quality:
FieldDevelopmentQualityReport, output_root: Path | str = SOURCE_CATALOG_ROOT,
generated_at: datetime | None = None, input_paths: Iterable[str | Path] = (),
allow_non_ace_root: bool = False, command: str | None = None, code_revision:
str | None = None) -> FieldDevelopmentOutputManifest` and
`load_field_development_metrics(path: Path | str) -> pd.DataFrame`. Writes will
stage under `.staging-field-development-metrics-*` and then promote CSV,
Parquet, quality JSON, and manifest JSON. The manifest will include input
paths, upstream row counts, source gaps, command, and git revision.

Create `tests/unit/texas_rrc/test_field_development_io.py` covering ACE root
enforcement, non-ACE test override, stable CSV/Parquet reload, quality payload,
and manifest contents.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_development_io.py -q
```

### Task 5 - Add CLI command and docs

Extend `src/worldenergydata/cli/commands/texas_rrc.py` with
`build-field-development-metrics`, accepting:

- `--root`
- `--output-root`
- `--dry-run`
- `--require-sources`
- `--build-missing-lifecycle`
- `--build-missing-production`
- `--allow-non-ace-output`

The command will default to fail-closed when required curated inputs are
missing. The `--build-missing-*` flags will call the existing lifecycle and
production builders from local raw snapshots only; they will not touch the
network.

Create `tests/unit/texas_rrc/test_field_development_cli.py` covering dry run,
missing required sources, non-ACE output override, and successful writes.

Add `docs/data-sources/onshore/texas-rrc/field-development-metrics.md`
documenting source lifecycle, refresh cadence, output contract, known caveats,
ranking columns, and CLI usage.

Verification:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_field_development_cli.py -q
```

### Task 6 - Build and verify `/mnt/ace` artifacts

Run focused and module-level checks:

```bash
uv run --no-sync pytest tests/unit/texas_rrc/test_raw_refresh_directory.py tests/unit/texas_rrc/test_lifecycle_sources.py -q
uv run --no-sync pytest tests/unit/texas_rrc/test_field_development_sources.py tests/unit/texas_rrc/test_field_development_metrics.py tests/unit/texas_rrc/test_field_development_io.py tests/unit/texas_rrc/test_field_development_cli.py -q
uv run --no-sync pytest tests/unit/texas_rrc -q
uv run --no-sync black --check --diff src/ tests/ packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc
uv run --no-sync isort --check-only --diff src/ tests/ packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc
uv run --no-sync flake8 src/ --max-line-length=100 --extend-ignore=E203,W503 --exclude=__pycache__,*.egg-info,.git,.venv
uv run --no-sync ruff check packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc src/worldenergydata/cli/commands/texas_rrc.py tests/unit/texas_rrc
```

If `scripts/legal/legal-sanity-scan.sh` is available, run it. If absent,
closeout will report the script as unavailable.

Then build local direct-source artifacts in order:

```bash
uv run --no-sync worldenergydata texas-rrc refresh --source wellbore_query
uv run --no-sync worldenergydata texas-rrc refresh --source drilling_permits
uv run --no-sync worldenergydata texas-rrc refresh --source completion_data
uv run --no-sync worldenergydata texas-rrc normalize-lifecycle --require-sources
uv run --no-sync worldenergydata texas-rrc build-production-atlas --require-sources
uv run --no-sync worldenergydata texas-rrc build-field-development-metrics --require-sources
```

If the CLI startup path remains slow because unrelated subcommands import heavy
scientific stacks, implementation will either lazy-load those unrelated
subcommands in a separate issue or run this API equivalent for the raw refresh
step and file a follow-on CLI-startup issue:

```bash
uv run --no-sync python - <<'PY'
from worldenergydata.texas_rrc.raw_refresh import RawSnapshotRefresher

refresher = RawSnapshotRefresher()
for source_id in ("wellbore_query", "drilling_permits", "completion_data"):
    manifest = refresher.refresh_source(source_id)
    print(source_id, manifest.status, manifest.raw_path)
PY
```

## Out of Scope

- Pipeline and GIS infrastructure access metrics.
- Surface-area well density from GIS acreage.
- Per-well production allocation from lease-level PDQ volumes.
- Economics, reserves, or type-curve forecasting.
- HTML/PDF field atlas publication.
