# Plan: Issue #669 - Texas RRC GoDrive directory refresh

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/669
**Status:** plan-review
**Tier:** T2 (direct-source transport, raw refresh planner, CLI, docs, tests)
**Client:** N/A
**Project:** worldenergydata onshore field development

## Resource Intelligence Summary

### Execution mode

Implementation will use `single-lane` development in an isolated worktree from
`origin/main`. The work will stay behind the issue approval gate until the plan
is approved by the user. The implementation will use TDD, with parser and
refresh tests written before production code.

### Official source evidence

The implementation will use only official Texas RRC direct-source URLs from
`mft.rrc.texas.gov`. Planning verified the four cataloged
`official_godrive_directory` URLs on 2026-06-30:

| Source ID | Official URL | Observed listing |
|---|---|---|
| `completion_data` | `https://mft.rrc.texas.gov/link/ed7ab066-879f-40b6-8144-2ae4b6810c04` | `rowCount=1965`; samples `01-01-2022.zip`, `01-01-2023.zip`; `Showing 1 - 250 of 1965` |
| `directional_surveys` | `https://mft.rrc.texas.gov/link/01769aa7-dee8-4121-bb25-e7557307f6bd` | `rowCount=2128`; samples `01-01-2021.zip`, `01-01-2022.zip`; `Showing 1 - 250 of 2128` |
| `well_gis_layers` | `https://mft.rrc.texas.gov/link/d551fb20-442e-4b67-84fa-ac3f23ecabb4` | `rowCount=255`; samples `well001.zip`, `well003.zip`; includes `wellFED.zip` |
| `pipeline_gis_layers` | `https://mft.rrc.texas.gov/link/c7cbab0c-afe2-4f6f-91ae-e6ed7d3a7ab6` | `rowCount=255`; samples `pipeline001.zip`, `pipeline003.zip` |

The GoDrive pages are JSF/PrimeFaces directory listings. A verified pagination
request will POST to `/webclient/godrive/PublicGoDrive.xhtml` with:

```text
javax.faces.partial.ajax=true
javax.faces.source=fileTable
javax.faces.partial.execute=fileTable
javax.faces.partial.render=fileTable
javax.faces.behavior.event=page
javax.faces.partial.event=page
fileList=fileList
fileTable_pagination=true
fileTable_first=<offset>
fileTable_rows=<rows_per_page>
fileTable_skipChildren=true
fileTable_encodeFeature=true
fileList_SUBMIT=1
javax.faces.ViewState=<latest view state>
```

Planning verified `fileTable_first=250` returns the next `completion_data`
page and `fileTable_rows=1000` returns all 255 `well_gis_layers` rows in one
page. The implementation will keep this request isolated in the transport
layer and covered by fixture tests.

### Current code shape

- `source_catalog.yml` catalogs the four directory datasets with
  `download_strategy: official_godrive_directory`.
- `source_catalog.py` validates the strategy and official GoDrive host.
- `godrive.py` and `raw_transport.py` support one named GoDrive file today.
- `raw_refresh.py` and the Texas RRC CLI skip directory entries today.

### Gaps this plan will close

- Parse official GoDrive directory rows, row counts, file command ids, modified
  timestamps, and size labels.
- Page through JSF/PrimeFaces directory listings without relying on third-party
  services.
- Select directory files safely:
  - `completion_data` and `directional_surveys`: default to latest
    filename-date snapshot, with explicit date-window support.
  - `well_gis_layers` and `pipeline_gis_layers`: default to all listed files
    for a complete county-layer snapshot.
- Download selected directory files via official GoDrive form posts.
- Write multi-file manifests with per-file checksum, byte size, effective URL,
  source modified timestamp, and retrieval timestamp.
- Preserve atomic write behavior so failed batches do not leave valid-looking
  partial snapshots.
- Surface directory fanout counts and selected files in CLI dry-run output.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-06-30-issue-669-texas-rrc-godrive-directory-refresh.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review | `scripts/review/results/2026-06-30-plan-669-codex-inline.md` |
| Directory parser | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/godrive.py` |
| Transport | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/raw_transport.py` |
| Refresh planner/executor | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/raw_refresh.py` |
| CLI | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Catalog policy fields | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/source_catalog.yml` |
| Unit tests | `tests/unit/texas_rrc/test_godrive_directory.py` |
| Refresh tests | `tests/unit/texas_rrc/test_raw_refresh.py` |
| CLI tests | `tests/unit/texas_rrc/test_raw_refresh.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/raw-refresh.md` |

## Deliverable

The deliverable will refresh official Texas RRC GoDrive directory datasets into
`/mnt/ace/worldenergydata/data/modules/texas_rrc` with deterministic selection
rules, no repo-local raw output, atomic batch promotion, and manifests that can
support downstream well lifecycle, GIS, production, field development, and
architecture analysis.

## Plan

### Task 1 - Add directory parsing fixtures and parser

Create `tests/unit/texas_rrc/test_godrive_directory.py` with fixture HTML for:

- a full GoDrive directory page containing two zip rows, `rowCount:255`, a
  paginator, and five `javax.faces.ViewState` inputs
- a JSF partial response containing a `fileTable` update with two zip rows and
  a new view state
- a non-data row and a non-zip row that must be ignored

Extend `godrive.py` with:

```python
@dataclass(frozen=True)
class GoDriveDirectoryEntry:
    filename: str
    command_id: str
    modified_label: str
    size_label: str
    row_key: str | None
    page_first: int


@dataclass(frozen=True)
class GoDriveDirectoryPage:
    entries: tuple[GoDriveDirectoryEntry, ...]
    view_state: str
    row_count: int
    page_first: int
    rows_per_page: int
```

Add parser functions:

- `parse_godrive_directory_page(html_text, page_first, rows_per_page)`
- `parse_godrive_partial_directory_page(xml_text, page_first, rows_per_page)`

The parser will use Python standard-library parsers only. It will raise
`ValueError` when a view state is missing, when row count cannot be inferred
from either `rowCount:<n>` or `Showing ... of <n>`, or when no zip rows are
present.

### Task 2 - Add official GoDrive directory pagination transport

Write failing tests that inject a fake opener/transport and assert:

- the landing page is fetched once from the official `mft.rrc.texas.gov/link/*`
  URL
- the second page request uses the verified JSF pagination payload
- `rows_per_page=1000` is honored
- only `mft.rrc.texas.gov` URLs are accepted for directory listing

Extend `UrlLibTransport` with:

```python
def list_godrive_directory(
    self,
    url: str,
    rows_per_page: int = 1000,
) -> tuple[GoDriveDirectoryPage, ...]:
    ...
```

The method will keep one cookie-aware opener per listing, parse the landing
page, then request page offsets `rows_per_page`, `2 * rows_per_page`, and so on
until the accumulated entry count reaches `row_count`. It will update the view
state from each response before the next pagination POST.

### Task 3 - Add directory selection policy

Extend the source catalog entries with a small policy field:

```yaml
directory_refresh_policy: "latest_by_filename_date"
```

for `completion_data` and `directional_surveys`, and:

```yaml
directory_refresh_policy: "all_files"
```

for `well_gis_layers` and `pipeline_gis_layers`.

Add tests that assert:

- `completion_data` selects the max `MM-DD-YYYY.zip` filename by parsed date
  when no date window is supplied
- `directional_surveys` selects only files inside `--since-date` and
  `--through-date`
- GIS sources select all files matching the expected prefix, including
  `wellFED.zip`
- malformed completion/directional filenames are ignored unless every candidate
  is malformed, in which case the selection raises `ValueError`

Implement selector helpers in `raw_refresh.py`:

```python
@dataclass(frozen=True)
class DirectorySelection:
    since_date: date | None = None
    through_date: date | None = None
    mode: str = "catalog_default"


@dataclass(frozen=True)
class DirectoryRefreshFile:
    filename: str
    command_id: str
    modified_label: str
    size_label: str
    page_first: int
    target_path: Path
```

The selector will not download data. It will return a deterministic list sorted
by filename.

### Task 4 - Extend refresh planning and dry-run output

Keep `RawSnapshotRefresher.plan_sources()` network-free. Add:

```python
def discover_directory_source(
    self,
    source_id: str,
    selection: DirectorySelection,
    rows_per_page: int = 1000,
) -> DirectoryRefreshPlan:
    ...
```

`DirectoryRefreshPlan` will include source id, download strategy, source URL,
row count, selected file count, target directory, skip reason, and selected
files. Tests will assert dry-run discovery does not write files and reports:

- total official row count
- selected file count
- target directory
- selected filenames

Update the CLI with `--since-date YYYY-MM-DD`, `--through-date YYYY-MM-DD`,
`--selection latest|all|catalog-default`, and `--rows-per-page 1000`.

The CLI will require date-window options only for directory sources and will
reject date windows for single-file sources.

### Task 5 - Download directory files atomically

Add a transport method:

```python
def download_godrive_directory_file_to(
    self,
    url: str,
    entry: GoDriveDirectoryEntry,
    output_path: Path,
    rows_per_page: int = 1000,
) -> DownloadedArtifact:
    ...
```

The method will navigate to `entry.page_first`, post the entry command id with
the current view state, and stream the returned artifact. It will validate
non-HTML content, status, content length, and content disposition when present.

Extend `RawSnapshotRefresher.refresh_source()` so directory sources write to:

```text
<output_root>/raw/.../.staging-<source_id>-<timestamp>/
```

Each selected file will be written as `<filename>.part` inside staging, renamed
within staging after content validation, and promoted into the final raw
directory only after every selected file succeeds. If any file fails, the
staging directory will be removed and the manifest status will be `error`.
Existing final raw files will not be modified on a failed batch.

### Task 6 - Write multi-file manifests

Extend `SnapshotManifest` with an optional `artifacts` field:

```python
@dataclass(frozen=True)
class SnapshotArtifactManifest:
    filename: str
    raw_path: str
    effective_url: str | None
    retrieved_at: str
    source_modified_label: str | None
    source_size_label: str | None
    checksum_sha256: str | None
    byte_size: int
    status: str
    error: str | None = None
```

Single-file manifests will keep their current top-level fields unchanged.
Directory manifests will set top-level `raw_path` to the target directory,
top-level `byte_size` to the sum of artifact byte sizes, top-level
`checksum_sha256` to `None`, and `artifacts` to one entry per selected file.

Tests will assert:

- successful multi-file refresh writes every final file and a manifest with all
  artifact checksums
- failed file two of three removes staging and does not leave final files from
  the failed batch
- manifest names remain unique for same-second attempts

### Task 7 - Update docs

Update `docs/data-sources/onshore/texas-rrc/raw-refresh.md` so it documents:

- official GoDrive directory support
- selection defaults for completion, directional survey, well GIS, and pipeline
  GIS datasets
- dry-run discovery behavior
- date-window examples
- multi-file manifest fields
- the rule that PatchOps and EWA remain validation-only and not raw refresh
  sources of record

### Task 8 - Verify

Run focused verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -m pytest -o addopts='' --noconftest \
  tests/unit/texas_rrc/test_godrive_directory.py \
  tests/unit/texas_rrc/test_raw_refresh.py \
  tests/unit/texas_rrc/test_source_catalog.py -q
```

Run formatter/linter checks for changed Python files:

```bash
uv run ruff check \
  packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/godrive.py \
  packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/raw_transport.py \
  packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/raw_refresh.py \
  src/worldenergydata/cli/commands/texas_rrc.py \
  tests/unit/texas_rrc/test_godrive_directory.py \
  tests/unit/texas_rrc/test_raw_refresh.py
```

Run a live no-download smoke against the official source:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
python -m worldenergydata.cli.main texas-rrc refresh \
  --source well_gis_layers \
  --dry-run \
  --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc
```

The live smoke will list the official row count and selected files without
downloading raw data.

## Acceptance

- Directory refresh will use official Texas RRC GoDrive URLs only.
- `completion_data` and `directional_surveys` will support latest-file and
  date-window refresh selection.
- `well_gis_layers` and `pipeline_gis_layers` will select all listed files by
  default.
- CLI dry-run will show directory fanout count and selected files without
  downloads.
- Refresh will write raw files only under
  `/mnt/ace/worldenergydata/data/modules/texas_rrc`.
- A failed batch will not leave valid-looking partial data in the final raw
  directory.
- Multi-file manifests will include per-file checksum, byte size, effective
  URL, source modified label, source size label, and retrieval timestamp.
- Tests will cover parser, pagination, selection, per-file manifest fields,
  atomic failure behavior, CLI dry-run, and repo-local raw output rejection.
