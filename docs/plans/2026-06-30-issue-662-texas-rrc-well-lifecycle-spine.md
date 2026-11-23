# Plan: Issue #662 - Texas RRC well lifecycle spine

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/662
**Status:** plan-review
**Tier:** T2 (multi-source normalization, CLI, `/mnt/ace` output contract, tests)
**Client:** N/A
**Project:** worldenergydata onshore field development

## Resource Intelligence Summary

### Execution mode

Implementation will use single-lane development from `origin/main` after user
approval. The work will remain behind the issue approval gate until this plan
is reviewed and approved by the user. Implementation will use TDD, with
lifecycle key, source-normalization, join, quality-report, I/O, and CLI tests
written before production code.

### Dependency and source status

Issue dependencies [#660](https://github.com/vamseeachanta/worldenergydata/issues/660)
and [#661](https://github.com/vamseeachanta/worldenergydata/issues/661) are closed
as completed. The implementation will consume only official Texas RRC raw
snapshots refreshed into `/mnt/ace/worldenergydata/data/modules/texas_rrc`; it
will not depend on PatchOps, EWA scraping, LinkedIn content, or third-party
scraper code for durable outputs.

Official Texas RRC source coverage to preserve in the lifecycle spine:

| Source ID | Lifecycle role | Official refresh | Current catalog path |
|---|---|---|---|
| `wellbore_query` | API, district, lease, county, field, operator, permit, schedule, well type, status | monthly / beginning of month | `raw/wellbore/query` |
| `drilling_permits` | permit number, issued/amended/extended dates, lease, location, spud-in date, latitude/longitude | nightly for daily master/trailer | `raw/permits/drilling` |
| `completion_data` | completion/recompletion forms, G-1, W-2, P-4, G-5, G-10, P-15, W-12, L-1 signals | nightly | `raw/completions` |
| `directional_surveys` | directional survey evidence from daily zipped PDFs | daily | `raw/directional_surveys` |

The Railroad Commission source page states that wellbore records are keyed by
API number and include completion, plugging, formation, and related wellbore
information; the Wellbore Query dataset supports searches by district, lease,
county, field, operator, drilling permit number, API number, schedule, and well
type. The same source page identifies drilling permit daily files with
latitude/longitude and current-month cumulation, and completion data as nightly
zipped data for submitted or approved completion forms. The implementation will
capture these lifecycle signals without joining production volumes.

### Current code shape

- `source_catalog.yml` already defines official source IDs, refresh cadence,
  raw paths, normalized paths, and curated paths under `/mnt/ace`.
- `raw_refresh.py`, `raw_directory.py`, `godrive.py`, and the Texas RRC CLI
  already refresh official single-file and directory snapshots.
- `WellProcessor` and `PermitProcessor` already contain useful API, date,
  coordinate, status, type, and field/lease normalization behavior.
- Existing processors are row processors. They do not build an API14-centered
  multi-source lifecycle table, do not emit a quality report, and do not write
  curated outputs under `curated/well_lifecycle/spine`.

### Gaps this plan will close

- Create one API14-centered lifecycle spine with original RRC identifiers
  retained for auditability.
- Join wellbore, drilling permit, and completion signals without requiring
  production data.
- Normalize API10/API12/API14 variants consistently and preserve sidetrack and
  completion codes.
- Report duplicate APIs, missing field/lease/operator IDs, invalid coordinates,
  impossible date ordering, and partial-source gaps.
- Write offline-loadable curated CSV and JSON manifest outputs under the Texas
  RRC `/mnt/ace` tree.
- Add a CLI command that normalizes already-refreshed raw snapshots without
  touching the network.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review | `scripts/review/results/2026-06-30-plan-662-codex-inline.md` |
| Lifecycle package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/__init__.py` |
| Lifecycle keys | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/keys.py` |
| Lifecycle source readers | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/sources.py` |
| Lifecycle spine builder | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/spine.py` |
| Lifecycle quality checks | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/quality.py` |
| Lifecycle output writer | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/io.py` |
| Column alias contract | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/lifecycle_column_aliases.yml` |
| CLI | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_lifecycle_keys.py` |
| Unit tests | `tests/unit/texas_rrc/test_lifecycle_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_lifecycle_spine.py` |
| Unit tests | `tests/unit/texas_rrc/test_lifecycle_quality.py` |
| Unit tests | `tests/unit/texas_rrc/test_lifecycle_io.py` |
| CLI tests | `tests/unit/texas_rrc/test_lifecycle_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md` |

## Deliverable

The deliverable will produce a deterministic Texas RRC well lifecycle spine
from local official raw snapshots, centered on `api14`, written under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/well_lifecycle/spine/
  well_lifecycle_spine.csv
  well_lifecycle_quality.json
  manifest.json
```

The spine will be loadable offline by downstream production, field atlas,
infrastructure, and field-development analysis issues. It will not allocate
production volumes, derive field economics, compute pipeline proximity, or
publish reports.

## Output Contract

The lifecycle spine will include these stable columns:

| Column | Purpose |
|---|---|
| `api14` | Primary key for the wellbore/completion record |
| `api10` | Original Texas API base key when derivable |
| `county_code` | API county segment |
| `well_unique_number` | API unique well segment |
| `sidetrack_code` | API digits 11-12 |
| `completion_code` | API digits 13-14 |
| `district` | RRC district |
| `field_number`, `field_name` | Field identifiers and names from source records |
| `lease_number`, `lease_name` | Lease identifiers and names from source records |
| `operator_number`, `operator_name` | Operator identifiers and names from source records |
| `permit_number`, `permit_status`, `permit_type` | Permit linkage and status |
| `permit_issued_date`, `permit_amended_date`, `permit_extended_date` | Permit lifecycle dates |
| `spud_date`, `completion_date`, `plug_date` | Well lifecycle dates |
| `well_status`, `well_type`, `wellbore_profile` | Operational and physical status signals |
| `total_depth`, `latitude`, `longitude`, `coordinates_valid` | Depth and location signals |
| `has_wellbore`, `has_permit`, `has_completion` | Source-presence flags |
| `source_ids` | Pipe-delimited list of source IDs contributing to the row |
| `quality_flags` | Pipe-delimited row-level warning codes |

The quality JSON will include counts for `duplicate_api14`,
`missing_field_id`, `missing_lease_id`, `missing_operator_id`,
`invalid_coordinates`, `impossible_dates`, `permit_without_wellbore`,
`completion_without_wellbore`, and `wellbore_without_completion`.

## Plan

### Task 1 - Add lifecycle API key normalization

Create `tests/unit/texas_rrc/test_lifecycle_keys.py` with failing tests for:

- `42-001-00001`, `4200100001`, `420010000100`, and `42001000010102`
  normalizing to valid API14 values.
- non-Texas state codes, short inputs, and non-numeric inputs returning `None`.
- sidetrack and completion codes being extracted from API14.
- API10 being derived from API14 for field and lease joins.

Create `lifecycle/keys.py` with these public interfaces:

- `normalize_api14(value: object) -> str | None`
- `derive_api10(api14: str | None) -> str | None`
- `split_api14(api14: str) -> dict[str, str]`

The implementation will share behavior with the existing processors where
possible, but `lifecycle/keys.py` will be the canonical API normalization
surface for lifecycle joins. The task will pass with:

```bash
uv run pytest tests/unit/texas_rrc/test_lifecycle_keys.py -q
```

### Task 2 - Add lifecycle source readers and alias contract

Create `data/lifecycle_column_aliases.yml` with required and optional aliases
for `wellbore_query`, `drilling_permits`, and `completion_data`. Required
aliases will cover API, district, field, lease, operator, and lifecycle dates;
optional aliases will cover depth, status, type, coordinates, and profile
signals.

Create `tests/unit/texas_rrc/test_lifecycle_sources.py` with fixture raw files:

- a zipped wellbore CSV/TXT file with API, district, field, lease, operator,
  status, well type, completion date, and plug date columns
- an ASCII drilling permit fixture with permit number, API, issue/amend/extend
  dates, lease, location, spud date, latitude, and longitude columns
- a zipped completion fixture with API, completion date, form type, field,
  lease, and operator columns
- a missing-source fixture that will return an empty frame and a source gap
  rather than failing the entire run

Create `lifecycle/sources.py` with a frozen `LifecycleInputFrames` dataclass
containing `wellbores: pd.DataFrame`, `permits: pd.DataFrame`,
`completions: pd.DataFrame`, and `source_gaps: Sequence[str]`, plus the public
function `load_lifecycle_inputs(raw_root: Path) -> LifecycleInputFrames`.

The readers will only inspect local files under the configured `/mnt/ace`
root. They will reject network URLs and paths outside the configured root. ZIP
readers will process CSV, TXT, DAT, and tabular ASCII members with delimiter
sniffing; unknown non-tabular members will be skipped and reported in the
manifest. The task will pass with:

```bash
uv run pytest tests/unit/texas_rrc/test_lifecycle_sources.py -q
```

### Task 3 - Build canonical lifecycle source frames

Create tests in `test_lifecycle_spine.py` that assert each source frame is
normalized before joining:

- wellbore rows will produce one canonical row per API14 with field, lease,
  operator, status, well type, total depth, completion date, and plug date
  candidates.
- permit rows will preserve original permit numbers and dates, and will create
  permit, field, lease, operator, depth, location, and spud-date candidates.
- completion rows will preserve original completion form types and will create
  completion-date and recompletion evidence by API14.
- duplicate records from the same source will retain the most complete row and
  count the duplicate in quality metrics.

Extend `lifecycle/spine.py` with these public interfaces:

- `normalize_wellbore_frame(frame: pd.DataFrame) -> pd.DataFrame`
- `normalize_permit_frame(frame: pd.DataFrame) -> pd.DataFrame`
- `normalize_completion_frame(frame: pd.DataFrame) -> pd.DataFrame`

The normalization will preserve original source columns prefixed with
`wellbore__`, `permit__`, or `completion__` only when the value is needed for
traceability. The task will pass with:

```bash
uv run pytest tests/unit/texas_rrc/test_lifecycle_spine.py -q
```

### Task 4 - Join the API14-centered lifecycle spine

Extend `test_lifecycle_spine.py` with join tests that assert:

- a well present in all three sources produces one API14 row with
  `has_wellbore`, `has_permit`, and `has_completion` set to true.
- a permit-only well remains in the output with `has_permit=true` and a
  partial-source quality flag.
- a completion-only well remains in the output with `has_completion=true` and a
  partial-source quality flag.
- field, lease, and operator IDs prefer wellbore values, then completion
  values, then permit values.
- permit dates will not overwrite later completion or plugging dates.

Extend `lifecycle/spine.py` with
`build_lifecycle_spine(inputs: LifecycleInputFrames) -> pd.DataFrame`.

The join will be an outer join on `api14` so partial-source gaps remain visible
to downstream users. The task will pass with:

```bash
uv run pytest tests/unit/texas_rrc/test_lifecycle_spine.py -q
```

### Task 5 - Add lifecycle quality checks

Create `tests/unit/texas_rrc/test_lifecycle_quality.py` with failing tests for:

- duplicate API14 values after normalization
- missing field, lease, and operator identifiers
- coordinates outside Texas bounds
- `spud_date > completion_date`, `completion_date > plug_date`, and
  `permit_issued_date > spud_date`
- permit-only, completion-only, and wellbore-only partial-source gaps

Create `lifecycle/quality.py` with a frozen `LifecycleQualityReport` dataclass
containing the listed count fields and `source_gaps: Sequence[str]`, plus the
public function
`assess_lifecycle_quality(spine: pd.DataFrame, source_gaps: Sequence[str] = ()) -> LifecycleQualityReport`.

The quality checker will append row-level `quality_flags` before the output is
written. The task will pass with:

```bash
uv run pytest tests/unit/texas_rrc/test_lifecycle_quality.py -q
```

### Task 6 - Write curated `/mnt/ace` outputs atomically

Create `tests/unit/texas_rrc/test_lifecycle_io.py` with failing tests that
assert:

- outputs are written under
  `curated/well_lifecycle/spine/` relative to the configured Texas RRC root.
- a root outside `/mnt/ace/worldenergydata/data/modules/texas_rrc` is rejected
  unless tests pass an explicit temporary root override.
- writes stage into `.staging-lifecycle-spine-*` and promote only after CSV,
  quality JSON, and manifest JSON are all complete.
- the manifest records input raw paths, row count, quality-report path,
  retrieved/generated timestamp, and source IDs.

Create `lifecycle/io.py` with these public interfaces:

- `write_lifecycle_outputs(spine: pd.DataFrame, quality: LifecycleQualityReport, output_root: Path, input_paths: Sequence[Path], generated_at: str | None = None) -> dict[str, Path]`
- `load_lifecycle_spine(path: Path) -> pd.DataFrame`

The implementation will use CSV and JSON to avoid adding a new dependency to
the `worldenergydata-texas_rrc` workspace member. The task will pass with:

```bash
uv run pytest tests/unit/texas_rrc/test_lifecycle_io.py -q
```

### Task 7 - Add CLI command and docs

Create `tests/unit/texas_rrc/test_lifecycle_cli.py` with failing tests for:

- `worldenergydata texas-rrc normalize-lifecycle --dry-run` reading local raw
  inputs and printing row counts and quality counts without writing files.
- `worldenergydata texas-rrc normalize-lifecycle --output-root <tmp>` writing
  the three output artifacts under the temp Texas RRC root.
- missing raw sources returning a non-zero exit only when
  `--require-sources wellbore_query,drilling_permits,completion_data` is used.
- CLI output never listing raw data from the git worktree.

Extend `src/worldenergydata/cli/commands/texas_rrc.py` with the
`normalize-lifecycle` Typer command. It will accept `--raw-root`, `--output-root`,
`--dry-run`, and `--require-sources` options.

Add `docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md` documenting:

- lifecycle refresh order: `refresh` raw snapshots first, then
  `normalize-lifecycle`
- official source families and refresh cycles
- `/mnt/ace` output paths
- offline loading command
- quality JSON meaning
- known exclusions for production allocation, GIS/pipeline metrics, and
  reports

The task will pass with:

```bash
uv run pytest tests/unit/texas_rrc/test_lifecycle_cli.py -q
```

### Task 8 - Run acceptance verification

Run the focused Texas RRC lifecycle tests:

```bash
uv run pytest \
  tests/unit/texas_rrc/test_lifecycle_keys.py \
  tests/unit/texas_rrc/test_lifecycle_sources.py \
  tests/unit/texas_rrc/test_lifecycle_spine.py \
  tests/unit/texas_rrc/test_lifecycle_quality.py \
  tests/unit/texas_rrc/test_lifecycle_io.py \
  tests/unit/texas_rrc/test_lifecycle_cli.py \
  -q
```

Run the existing Texas RRC regression suite:

```bash
uv run pytest tests/unit/texas_rrc -q
```

Run the package import smoke:

```bash
uv run python -c "from worldenergydata.texas_rrc.lifecycle import build_lifecycle_spine; print(build_lifecycle_spine)"
```

Run the lifecycle dry-run against the configured `/mnt/ace` root when raw
snapshots are available:

```bash
uv run worldenergydata texas-rrc normalize-lifecycle --dry-run
```

If the repository-level legal scan script is absent or non-executable, the
implementation closeout will report that explicitly instead of claiming it
passed.

## Out of Scope

- Production-volume normalization, field atlas aggregation, and economic
  metrics; those will remain in [#663](https://github.com/vamseeachanta/worldenergydata/issues/663)
  and [#664](https://github.com/vamseeachanta/worldenergydata/issues/664).
- Pipeline and well GIS access metrics; those will remain in
  [#665](https://github.com/vamseeachanta/worldenergydata/issues/665).
- Report publication and deep-dive HTML/PDF artifacts; those will remain in
  [#666](https://github.com/vamseeachanta/worldenergydata/issues/666).
- PDF extraction from directional survey or imaged completion files. This plan
  will preserve those source gaps for follow-on work.
