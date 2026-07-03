# Plan: Issue #725 - Kansas KGS Hugoton pressure observations

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/725
**Status:** plan-review
**Tier:** T2 (new source package, direct-source raw manifests, parsers, curated pressure table, CLI, tests, docs)
**Client:** N/A
**Project:** worldenergydata onshore pressure screen
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Planning uses `parallel-readonly` resource intelligence. Implementation will use
single-lane development from `origin/main` after this plan is reviewed, pushed,
marked `status:plan-review`, and explicitly approved by the user. The approved
implementation will use TDD: tests will be written before production code for
source manifests, parser quirks, API normalization, pressure/depth joins,
quality reporting, output persistence, and CLI behavior.

### Reproduction proofs

N/A. Issue #725 proposes a new Kansas KGS ingest and curated pressure table. It
does not allege a failing test, broken import, missing method, regression, or
incorrect numeric output.

### Issue and dependency status

Planning-time issue probes on 2026-07-03T01:38Z found:

| Issue | State | Current role |
|---|---|---|
| [#708](https://github.com/vamseeachanta/worldenergydata/issues/708) | open, `status:needs-plan` | Parent pressure-screen epic |
| [#709](https://github.com/vamseeachanta/worldenergydata/issues/709) | open, `status:needs-plan` | Texas RRC pressure extraction; issue body says it is blocked by RRC raw refresh |
| [#710](https://github.com/vamseeachanta/worldenergydata/issues/710) | open, `status:needs-plan` | Under-pressured field ranking; blocked by a pressure-observation table |
| [#725](https://github.com/vamseeachanta/worldenergydata/issues/725) | open, `status:needs-plan` | Kansas KGS pressure ingest; issue body says sources are live and free |

The next executable slice is #725, not #709 or #710. #725 gives the pressure
screen a direct, structured Hugoton analog dataset while the Texas pressure
source remains blocked.

### Direct-source inventory

The implementation will use official Kansas Geological Survey sources only. It
will not scrape Collide, PatchOps, commercial vendors, or third-party mirrors.

Planning-time direct-source probes on 2026-07-03T01:37Z found:

| Source | Probe result | Current metadata | Planned use |
|---|---|---|---|
| KGS gas proration pressure file | `curl -L -I https://www.kgs.ku.edu/PRS/Ora_Archive/kansas_proration_pressures.txt` returned HTTP 200 | `Content-Length: 14017158`; `Last-Modified: Thu, 27 Mar 2025 17:32:01 GMT`; `Content-Type: text/plain` | Raw pressure/deliverability source |
| KGS pressure sample | `curl -L -r 0-4096 .../kansas_proration_pressures.txt` returned the documented header and data rows | Header includes `SHUT_IN_PRESS`, `WORKING_PRES`, `OPEN_FLOW`, `ADJ_DELIVER`; line 2 is the stray fragment `RES","DIFFERENT","COEFF"` | Parser fixture and malformed-header repair test |
| KGS wells master | `curl -L -I https://www.kgs.ku.edu/PRS/Ora_Archive/ks_wells.zip` returned HTTP 200 | `Content-Length: 43773721`; `Last-Modified: Fri, 05 Jun 2026 19:31:21 GMT`; `Content-Type: application/zip` | API/depth/formation/field join source |
| KGS formation tops, optional | `curl -L -I https://www.kgs.ku.edu/PRS/Ora_Archive/ks_tops.zip` returned HTTP 200 | `Content-Length: 27025896`; `Last-Modified: Fri, 05 Jun 2026 19:31:33 GMT`; `Content-Type: application/zip` | Optional fallback if total depth quality is inadequate; not required for v1 |

The live pressure sample begins with:

```text
WELL_KID, LEASE, API_NUMBER, OPERATOR, TOWNSHIP, TWN_DIR, RANGE, RANGE_DIR, SECTION, LATITUDE, LONGITUDE, YEAR, ACREAGE, SHUT_IN_PRESS, WORKING_PRES,DAILY_RATE, OPEN_FLOW, ADJ_DELIVER, WATER_PROD,METER_PRES, DIFFERENT, COEFF
RES","DIFFERENT","COEFF"
"1001232609","POWELL 2-31","15-067-20048","MESA PETROLEUM C","29","S","37","W","31","37.4789143","-101.4114608","1996","636","0","0","0","0","1297","0","0","0","0"
"1001232609","POWELL 2-31","15-067-20048","MESA PETROLEUM C","29","S","37","W","31","37.4789143","-101.4114608","1997","636","47.3","38.8","337.26","1022","645","0","38.3","10.58","12.1"
```

The implementation will derive the actual observation window from parsed
`YEAR` values and will write that `min_year`/`max_year` into quality output and
documentation. It will not infer cadence solely from the issue body's
"frozen 2013" wording because the direct-source HTTP metadata shows a 2025
`Last-Modified` timestamp for the pressure file.

### `/mnt/ace` storage inventory

Planning-time local probes found the Kansas module root already exists under
the storage-contract extension:

```text
/mnt/ace/worldenergydata/data/modules/kansas_kgs/
  raw/pressure/kansas_proration_pressures.txt  14017158 bytes
  raw/wells/ks_wells.zip                       43773721 bytes
```

`ks_wells.zip` contains one file, `ks_wells.txt`, with uncompressed length
203,293,781 bytes. The first row confirms useful join/depth fields:

```text
"KID","API_NUMBER","API_NUM_NODASH","LEASE","WELL","FIELD","LATITUDE","LONGITUDE",...,"DEPTH","FORMATION_AT_TOTAL_DEPTH","PRODUCE_FORM",...
"1001184201","15-007-20008","15007200080000","Kirkbride 'B'","1","MEDICINE LODGE NORTH",...,"4470",...
```

The implementation will hash and manifest the existing raw files when present.
If a raw file is missing or the user passes `--refresh`, the CLI will fetch it
from the official KGS URL into the same raw path.

### Current code shape

- No `packages/worldenergydata-kansas_kgs` workspace member exists.
- No `tests/unit/kansas_kgs` test directory exists.
- No `docs/data-sources/onshore/kansas-kgs` documentation directory exists.
- Root `pyproject.toml` uses `packages/*` as workspace members, but root
  runtime dependencies and `[tool.uv.sources]` are enumerated. A new package
  must be added to the root dependency list and `[tool.uv.sources]`.
- `src/worldenergydata/cli/main.py` registers command modules explicitly with
  `app.add_typer(...)`.
- `src/worldenergydata/cli/commands/__init__.py` maintains an explicit lazy
  command-module allowlist.
- The Texas RRC onshore packages provide the closest local patterns for
  storage-root guards, staged writes, manifest/quality JSON, and CLI tests.

The implementation will create a narrow `worldenergydata-kansas_kgs` package.
It will not create a generic multi-state `state_regulators` abstraction in this
slice. That abstraction should wait until at least the Kansas and Texas pressure
tables exist and the shared contract is based on real differences rather than
guesswork.

### Schema and interpretation contract

The curated output will follow the #709 pressure-observation schema where the
Kansas data can support it:

```text
api14, api10, api_state_code, api_county_code, county_name, state,
source_agency, field_name, test_date, test_year, test_type, pressure_psig_raw,
pressure_psia, atmospheric_pressure_psi, pressure_kind, reference_depth_ft,
reference_depth_method, gradient_psi_ft, gradient_method, formation,
is_earliest_observation_for_well, virgin_pressure_proxy_method,
source_file, source_row_id, quality_flags, limitations
```

Kansas-specific policy:

- `test_type` will be `KS_PRORATION`.
- `test_date` will be null because the proration file has only annual `YEAR`.
  `test_year` will drive temporal ordering and earliest-observation logic.
- `pressure_kind` will be `WHP_shut_in` because KGS `SHUT_IN_PRESS` is a
  shut-in wellhead pressure, not a measured bottom-hole pressure.
- KGS proration pressure units will be treated as gauge pressure unless the
  implementation finds official contrary metadata. Normalized outputs will
  retain `pressure_psig_raw`; curated outputs will emit `pressure_psia =
  pressure_psig_raw + atmospheric_pressure_psi` with
  `atmospheric_pressure_psi = 14.7` and a `psig_to_psia_assumption` limitation.
  That limitation will explicitly state that 14.7 psi is a sea-level screening
  constant and does not adjust for Hugoton-area elevation.
- `gradient_psi_ft` will be computed only when `pressure_psia` is positive and
  a positive, unambiguous reference depth is available from `ks_wells.DEPTH`.
- `gradient_method` will be `whp_over_total_depth_screening_only`; downstream
  #710 can apply a static gas-column correction before hydrostatic tiering.
- `api10` will be normalized from the proration `API_NUMBER` by stripping
  dashes. `api14` will come from the wells master `API_NUM_NODASH` only when
  the API10 join is unique. Ambiguous joins will keep `api14`,
  `reference_depth_ft`, and `gradient_psi_ft` null and carry explicit quality
  flags so no gradient is computed from an arbitrary sidetrack/depth.
- `api_state_code` and `api_county_code` will be parsed from the dashed API
  number. `county_name` will come from a packaged Kansas county-code mapping
  only after the implementation verifies the code scheme against sampled KGS
  rows and location evidence. Unknown or unverified county codes will be
  retained as codes, leave `county_name` null, and be counted in quality output.
- Zero or blank pressure values will remain in the normalized proration table
  but will not become curated pressure observations.
- Dates in `ks_wells.txt` use Oracle-style `DD-MON-YYYY`; parsing failures will
  be counted in quality output instead of silently coercing to misleading
  dates.
- `is_earliest_observation_for_well` will be true for the earliest positive
  proration observation per defensible well identity, using `test_year` and
  then source row order as a deterministic tie-break. The implementation will
  prefer unique `api14`, then unique KGS `WELL_KID`/`KID` identity if available.
  If identity remains ambiguous, the flag will be suppressed or marked
  indeterminate with an `ambiguous_identity_for_virgin_proxy` quality flag.
  This is the #725 virgin-pressure proxy flag consumed by #710, but
  `virgin_pressure_proxy_method` will be `earliest_available_proration_year`
  and limitations will state that this is not measured initial reservoir
  pressure.

### Out of scope

The implementation will not:

- estimate bottom-hole pressure from shut-in wellhead pressure
- classify hydrostatic tiers or rank fields; that belongs to #710
- ingest post-2013 KCC orders, dockets, or scanned forms
- scrape per-well DST web pages
- parse `ks_tops.zip` unless the v1 total-depth join proves inadequate during
  implementation
- create a generic state-regulator framework
- commit raw KGS data or generated parquet/CSV outputs to git

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-03-issue-725-kansas-kgs-pressure-observations.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Claude initial | `scripts/review/results/2026-07-03-plan-725-claude.md` |
| Plan review - Claude focused availability | `scripts/review/results/2026-07-03-plan-725-claude-r2.md` |
| Plan review - Claude focused r3 | `scripts/review/results/2026-07-03-plan-725-claude-r3.md` |
| Plan review - Codex | `scripts/review/results/2026-07-03-plan-725-codex.md` |
| Plan review - Gemini availability | `scripts/review/results/2026-07-03-plan-725-gemini-unavailable.md` |
| Package metadata | `packages/worldenergydata-kansas_kgs/pyproject.toml` |
| Package init | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/__init__.py` |
| Source catalog/config | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/source_catalog.yml` |
| County code mapping | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/kansas_counties.yml` |
| Raw download/manifest support | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py` |
| Pressure parser | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py` |
| Wells parser | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py` |
| Curated model/join logic | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py` |
| Quality reporting | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/quality.py` |
| Output persistence | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py` |
| CLI support | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py` |
| CLI command module | `src/worldenergydata/cli/commands/kansas_kgs.py` |
| CLI registry | `src/worldenergydata/cli/main.py`; `src/worldenergydata/cli/commands/__init__.py` |
| Unit tests | `tests/unit/kansas_kgs/test_raw_sources.py` |
| Unit tests | `tests/unit/kansas_kgs/test_pressure_parser.py` |
| Unit tests | `tests/unit/kansas_kgs/test_wells_parser.py` |
| Unit tests | `tests/unit/kansas_kgs/test_observations.py` |
| Unit tests | `tests/unit/kansas_kgs/test_io.py` |
| CLI tests | `tests/unit/kansas_kgs/test_cli.py` |
| Docs | `docs/data-sources/onshore/kansas-kgs/pressure-observations.md` |

## Deliverable

The deliverable will publish a Kansas KGS pressure-observation packet under:

```text
/mnt/ace/worldenergydata/data/modules/kansas_kgs/
  raw/
    manifest.json
    pressure/kansas_proration_pressures.txt
    wells/ks_wells.zip
  normalized/
    pressure/kansas_proration_pressures.parquet
    wells/ks_wells.parquet
  curated/
    pressure/well_pressure_observations/
      well_pressure_observations.csv
      well_pressure_observations.parquet
      coverage_by_county_year.csv
      coverage_by_county_year.parquet
      quality.json
      manifest.json
```

The CLI will expose:

```bash
worldenergydata kansas-kgs build-pressure-observations \
  --root /mnt/ace/worldenergydata/data/modules/kansas_kgs
```

The default root will be `/mnt/ace/worldenergydata/data/modules/kansas_kgs`.
Writes outside that root will be rejected unless a test-only
`allow_non_ace_root` code path is used.

## Pseudocode

```python
def load_source_catalog():
    read package data/source_catalog.yml
    validate raw, normalized, and curated paths stay under kansas_kgs ACE root
    return source records for proration_pressure, wells_master, optional tops
```

```python
def ensure_raw_sources(root, refresh=False):
    for required source in proration_pressure, wells_master:
        if refresh or raw file missing:
            download from official KGS URL with timeout and atomic temp rename
        compute sha256, size, last_modified/source_url metadata
    write raw/manifest.json through staged rename
    return raw file references
```

```python
def parse_proration_pressure(path):
    open text as CSV
    keep first header line
    strip whitespace from header tokens
    skip malformed rows whose field count does not match the header
    parse all remaining rows as strings first
    normalize numeric columns and year
    normalize api10 from API_NUMBER
    parse api_state_code and api_county_code from API_NUMBER
    map api_county_code to county_name through package data
    keep zero/blank pressures in normalized table
    return normalized proration dataframe plus parser quality counts
```

```python
def parse_wells_master(zip_path):
    open ks_wells.zip
    stream ks_wells.txt with pandas/csv chunks
    normalize API_NUMBER to api10 and API_NUM_NODASH to api14
    parse DEPTH as numeric reference_depth_ft
    parse Oracle-style date fields where needed
    return wells dataframe with api10, api14, field, county-like location keys,
    depth, formation, status, lat/lon
```

```python
def build_pressure_observations(proration, wells):
    filter proration rows where SHUT_IN_PRESS is positive
    convert raw pressure from psig to psia with documented atmospheric constant
    left join wells on api10, using unique KGS KID fallback where needed
    mark missing or ambiguous well joins and suppress depth/gradient for them
    set pressure_kind = WHP_shut_in
    set reference_depth_method = total_depth_ft when DEPTH is positive
    compute gradient only for positive pressure and positive depth
    mark earliest positive observation per defensible well identity as proxy
    add screening-only limitation text for WHP/depth gradient
    derive min/max observation year from parsed YEAR values
    return curated observations and coverage summaries
```

```python
def write_outputs(root, normalized_tables, curated_tables, quality):
    enforce root is /mnt/ace/.../kansas_kgs unless allow_non_ace_root
    write parquet and CSV through staged temp paths
    write quality.json and manifest.json with inputs, outputs, sha256, row counts,
    parser repairs, source metadata, command, code revision, and limitations
```

## Plan

### Task 1 - Add Kansas package shell and source catalog

Write failing tests for:

- source catalog paths under the Kansas ACE root
- rejection of raw/normalized/curated paths outside the Kansas root
- package import surface
- setuptools package discovery uses an explicit
  `include = ["worldenergydata.kansas_kgs*"]`, `namespaces = true`, and package
  data globs that ship YAML files
- county-code mapping covers all 105 Kansas counties and mapping use is gated
  by a documented verification fixture for sampled KGS rows

Create `packages/worldenergydata-kansas_kgs` as a PEP 420 namespace package
with a minimal dependency set matching repo pin style:
`worldenergydata-core`, `pandas>=2.3.3,<3.0`, `pyarrow>=14.0.0,<20.0`, and
`pyyaml>=6.0,<7.0`.

Update root `pyproject.toml` so the root package depends on
`worldenergydata-kansas_kgs` and resolves it through `[tool.uv.sources]`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest tests/unit/kansas_kgs/test_raw_sources.py -q
```

### Task 2 - Raw source manifest and optional refresh

Write failing tests for:

- hashing existing raw files under `/mnt/ace`
- manifest entries with source URL, size, sha256, fetched/observed timestamp,
  and HTTP metadata
- staged writes for `raw/manifest.json`
- no network call when files already exist and `refresh=False`
- refresh path using a mocked HTTP/file transport

Create `raw_sources.py` and source-catalog metadata for:

- `pressure_proration`: `raw/pressure/kansas_proration_pressures.txt`
- `wells_master`: `raw/wells/ks_wells.zip`
- `formation_tops`: optional `raw/tops/ks_tops.zip`

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest tests/unit/kansas_kgs/test_raw_sources.py -q
```

### Task 3 - Parse KGS pressure and wells files

Write failing tests for:

- repairing the malformed second line by dropping rows whose field count does
  not match the header
- preserving zero/blank pressure rows in normalized output
- keeping only positive `SHUT_IN_PRESS` rows for curated observations
- stripping whitespace from malformed pressure-file header tokens
- dropping malformed rows by field-count mismatch instead of exact string match
- numeric parsing of `SHUT_IN_PRESS`, `WORKING_PRES`, `OPEN_FLOW`,
  `ADJ_DELIVER`, and `YEAR`
- API10 normalization from dashed KGS API strings
- parsing and retaining `WELL_KID` as source well identity and KID fallback
- API state/county code parsing and county-name mapping
- raw `SHUT_IN_PRESS` retained as `pressure_psig_raw` and curated
  `pressure_psia` converted with `14.7` psi atmospheric pressure
- `test_type=KS_PRORATION`
- `test_date` remains null and `test_year` is populated
- reading `ks_wells.zip` and extracting `API_NUMBER`, `API_NUM_NODASH`, `FIELD`,
  `DEPTH`, `FORMATION_AT_TOTAL_DEPTH`, location, and status
- Oracle-style date parsing for `SPUD`, `COMPLETION`, `PLUGGING`, and
  `MODIFIED`

Create `pressure.py` and `wells.py`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest \
    tests/unit/kansas_kgs/test_pressure_parser.py \
    tests/unit/kansas_kgs/test_wells_parser.py -q
```

### Task 4 - Build curated pressure observations and coverage summaries

Write failing tests for:

- positive shut-in pressures produce curated observation rows
- WHP rows use `pressure_kind=WHP_shut_in`
- gradients are null when depth is missing, zero, or non-positive
- gradients are computed only for positive pressure, positive depth, and an
  unambiguous well-depth join
- unique API10 joins emit `api14`; ambiguous joins add a quality flag and keep
  `api14`, reference depth, and gradient null
- KGS KID fallback can disambiguate API10 joins when both files carry a unique
  KID match
- earliest positive observation per defensible well identity is flagged as the
  virgin-pressure proxy
- ambiguous well identity suppresses or marks the virgin-pressure proxy flag as
  indeterminate and records a quality flag
- coverage summary groups by county/location proxy and test year
- Hugoton/Panoma county dominance is visible from the available location fields
  without hardcoding production data into the implementation

Create `observations.py` and `quality.py`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest tests/unit/kansas_kgs/test_observations.py -q
```

### Task 5 - Persist outputs and wire CLI

Write failing tests for:

- ACE-root guard and non-ACE sandbox override
- staged CSV/parquet/JSON writes
- manifest contains input paths, output paths, source URLs, sha256 values,
  row counts, quality counts, command, code revision, and limitations
- CLI dry-run returns row counts without writing curated outputs
- CLI build writes the full packet to a temporary root in tests

Create `io.py`, `cli_support.py`, and `src/worldenergydata/cli/commands/kansas_kgs.py`.
Register the command in `src/worldenergydata/cli/main.py` and
`src/worldenergydata/cli/commands/__init__.py`. The implementation must update
all CLI registry/display sites: the `main.py` import tuple, the `main.py`
`app.add_typer(...)` call, the `main.py info()` module table, the
`_COMMAND_MODULES` set, and the `__all__` list.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest \
    tests/unit/kansas_kgs/test_io.py \
    tests/unit/kansas_kgs/test_cli.py -q
```

### Task 6 - Documentation and `/mnt/ace` smoke

Write `docs/data-sources/onshore/kansas-kgs/pressure-observations.md` with:

- official KGS source URLs and data-window/refresh cadence derived from parsed
  `YEAR` range plus manifest HTTP metadata
- storage layout
- command usage
- output schema
- WHP-vs-BHP limitation
- relationship to [#708](https://github.com/vamseeachanta/worldenergydata/issues/708),
  [#709](https://github.com/vamseeachanta/worldenergydata/issues/709), and
  [#710](https://github.com/vamseeachanta/worldenergydata/issues/710)

Run the CLI against `/mnt/ace/worldenergydata/data/modules/kansas_kgs` and
record row counts, parser repairs, join coverage, and quality gaps in the issue
closeout comment. Generated data remains outside git.

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `packages/worldenergydata-kansas_kgs/pyproject.toml` | new source package metadata, namespace discovery, and YAML package data |
| Create | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/` | Kansas KGS source package |
| Create | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/source_catalog.yml` | official source metadata and storage paths |
| Create | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/kansas_counties.yml` | API county-code to county-name coverage output |
| Modify | `pyproject.toml` | add root dependency and uv workspace source entry |
| Create | `src/worldenergydata/cli/commands/kansas_kgs.py` | CLI command module |
| Modify | `src/worldenergydata/cli/main.py` | add command import, register `kansas-kgs` command group, and update `info()` table |
| Modify | `src/worldenergydata/cli/commands/__init__.py` | add `_COMMAND_MODULES` and `__all__` entries |
| Create | `tests/unit/kansas_kgs/` | TDD coverage for new package |
| Create | `docs/data-sources/onshore/kansas-kgs/pressure-observations.md` | user-facing source and output documentation |
| Update | `docs/plans/README.md` | add #725 plan row |

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_source_catalog_paths_stay_under_kansas_ace_root` | storage contract guard | package source catalog | all paths below `/mnt/ace/.../kansas_kgs` |
| `test_source_catalog_rejects_out_of_root_path` | fail-closed path validation | catalog with bad path | `ValueError` |
| `test_existing_raw_files_are_hashed_into_manifest` | raw manifest from present files | temp raw pressure/wells files | sha256, size, URL metadata |
| `test_refresh_not_called_when_raw_files_present` | no unnecessary network use | present raw files, mocked fetcher | fetcher not called |
| `test_proration_parser_repairs_malformed_second_line` | KGS header repair | sample first lines from live source | data rows parse with expected columns |
| `test_proration_parser_strips_header_whitespace` | robust column names | live-style header spacing | `WORKING_PRES`, not `" WORKING_PRES"` |
| `test_proration_parser_drops_bad_field_count_rows` | malformed-row guard | row with wrong field count | row dropped and counted |
| `test_proration_parser_keeps_zero_pressure_in_normalized_table` | raw fidelity | zero-pressure row | normalized row retained |
| `test_curated_observations_drop_blank_or_zero_pressures` | usable observation filter | zero, blank, positive pressure rows | only positive pressure curated |
| `test_pressure_psig_converts_to_pressure_psia` | unit contract | raw pressure 47.3 psig | curated pressure 62.0 psia with limitation |
| `test_atmospheric_constant_limitation_mentions_elevation` | unit limitation | converted pressure row | sea-level 14.7/elevation caveat present |
| `test_test_date_policy_for_annual_rows` | annual proration date policy | row with `YEAR=1997` | `test_year=1997`, `test_date` null |
| `test_observation_window_uses_parsed_year_range` | data-window provenance | rows spanning multiple years | quality reports min/max parsed years |
| `test_api_county_code_maps_to_verified_county_name` | county coverage contract | verified API/location fixture | county name only when code scheme is verified |
| `test_wells_parser_extracts_depth_and_api14` | well master parsing | small zipped `ks_wells.txt` fixture | api10, api14, depth, field columns |
| `test_kid_fallback_disambiguates_api10_join` | KGS identity fallback | ambiguous API10 with unique KID | populated unique well identity |
| `test_observations_join_unique_api10_to_api14` | pressure/well join | one pressure row, one well row | populated api14 |
| `test_observations_flag_ambiguous_api10_join` | ambiguous join behavior | one pressure row, two well rows | null api14, null depth, null gradient, quality flag |
| `test_gradient_requires_positive_depth` | gradient guard | missing/zero/depth rows | gradient only for positive depth |
| `test_earliest_positive_observation_is_virgin_proxy` | #725 proxy flag | two positive yearly rows for one well | earliest row flagged true |
| `test_virgin_proxy_suppressed_when_identity_ambiguous` | #725 proxy safety | ambiguous API10 without unique KID | proxy flag false/null and quality flag |
| `test_hugoton_counties_dominate_coverage_summary` | source sanity check | representative coverage fixture | Grant/Stevens/Morton-style counties rank visibly high |
| `test_quality_counts_parser_repairs_and_join_gaps` | quality report | sample parser/join issues | expected counts |
| `test_output_writer_enforces_ace_root` | storage guard | non-ACE root | `ValueError` |
| `test_output_writer_writes_csv_parquet_quality_manifest` | output packet | sample observations | expected files and row counts |
| `test_cli_dry_run_reports_counts_without_curated_writes` | dry-run CLI behavior | temp root with raw fixtures | no curated files written |
| `test_cli_build_writes_packet` | CLI build behavior | temp root with raw fixtures | manifest and datasets written |
| `test_cli_info_lists_kansas_kgs_module` | CLI discovery text | `worldenergydata info` | Kansas KGS module row visible |

## Acceptance Criteria

- [ ] A new `worldenergydata-kansas_kgs` workspace package imports cleanly.
- [ ] Official KGS raw pressure and wells sources are represented in a package
      source catalog with `/mnt/ace` path validation.
- [ ] Existing or refreshed raw files are hashed into `raw/manifest.json`.
- [ ] Normalized pressure and wells parquet outputs are written under
      `/mnt/ace/worldenergydata/data/modules/kansas_kgs/normalized/`.
- [ ] Curated pressure observations are written under
      `/mnt/ace/worldenergydata/data/modules/kansas_kgs/curated/pressure/well_pressure_observations/`.
- [ ] Curated rows preserve `pressure_kind=WHP_shut_in` and do not represent
      KGS shut-in wellhead pressure as measured BHP.
- [ ] Curated rows carry both raw gauge-pressure provenance and converted
      `pressure_psia` with a documented sea-level atmospheric-pressure
      assumption and elevation caveat.
- [ ] `test_type=KS_PRORATION`, `test_year` is populated, and `test_date`
      policy for year-only rows is explicit.
- [ ] Gradient computation is guarded by positive pressure and defensible
      positive reference depth, with `gradient_method` carried in each row.
- [ ] Ambiguous API10 joins suppress `api14`, reference depth, and gradient and
      are counted in quality output.
- [ ] Earliest positive observation per defensible well identity is flagged as
      the virgin-pressure proxy for #710, with `virgin_pressure_proxy_method =
      earliest_available_proration_year` and limitations explaining that it is
      not measured initial reservoir pressure.
- [ ] Ambiguous well identity suppresses or marks the virgin-pressure proxy
      flag as indeterminate and records a quality flag.
- [ ] Quality output reports malformed-header repair, zero/blank pressure
      counts, missing/ambiguous API joins, missing depth, and row counts.
- [ ] Quality output reports parsed pressure-observation `min_year` and
      `max_year`; docs derive cadence from these values and HTTP metadata.
- [ ] Coverage stats by county/location proxy and year are emitted.
- [ ] Coverage stats include a Hugoton/Panoma dominance sanity check in tests
      and quality output.
- [ ] County coverage uses a packaged Kansas county-code mapping; unknown codes
      are retained and counted rather than dropped.
- [ ] Documentation explains source URLs, observed data window, refresh cadence,
      storage layout, schema, command usage, and limitations.
- [ ] Focused tests pass:
      `PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest tests/unit/kansas_kgs -q`
- [ ] Formatting/lint pass for touched Python:
      `uv run --no-sync black --check --diff src tests packages/worldenergydata-kansas_kgs/src`
      and `uv run --no-sync isort --check-only --diff src tests packages/worldenergydata-kansas_kgs/src`
      and `uv run --no-sync ruff check packages/worldenergydata-kansas_kgs/src src/worldenergydata/cli/commands/kansas_kgs.py tests/unit/kansas_kgs`
- [ ] `scripts/legal/legal-sanity-scan.sh` passes before commit.
- [ ] Heavy raw, normalized, and curated data stays under `/mnt/ace` and is not
      committed to git.

## Adversarial Review Summary

This plan has completed no-MAJOR post-remediation review and is ready for
`status:plan-review`. Implementation remains blocked until explicit user
approval moves the issue to `status:plan-approved`.

| Provider | Verdict | Key findings |
|---|---|---|
| Claude | MAJOR initial; r2 unavailable; r3 MINOR | Initial review found blockers: missing virgin proxy flag, psig/psia unit ambiguity, ambiguous depth/gradient join, county-code verification, package-data config, annual test-date policy, parser robustness, CLI edit sites, dependency pins. The plan was patched to address these. Two focused r2 attempts timed out with no verdict. Focused r3 verified the prior MAJOR findings were remediated and returned only non-blocking documentation/test-scope cautions, which are now patched into this plan. |
| Codex | APPROVE with minor implementation cautions | Verified the revised plan addresses the Claude MAJOR classes. Remaining cautions are implementation evidence items: preserve KGS unit metadata search, county-code verification evidence, and `/mnt/ace` raw hash/length comparison. |
| Gemini | UNAVAILABLE | Gemini CLI failed before review with `IneligibleTierError`; no verdict produced. |

**Overall result:** PLAN-REVIEW READY - no MAJOR review findings remain.

Revisions made based on review:

- Added earliest positive observation / virgin-pressure proxy fields and tests.
- Added raw gauge-pressure provenance and `pressure_psia` conversion policy.
- Required ambiguous API10 joins to suppress `api14`, reference depth, and
  gradient.
- Reworked county coverage around verified API county-code mapping, not an
  implicit county-name column.
- Added package-data and namespace-discovery requirements for YAML files.
- Pinned `test_type=KS_PRORATION` and annual `test_date`/`test_year` policy.
- Replaced exact malformed-line matching with header trimming and field-count
  row repair.
- Enumerated all CLI registry/display edit sites and aligned dependency pins
  with sibling package convention.
- Added parsed observation-window reporting instead of trusting the issue's
  frozen-2013 cadence wording.
- Clarified `virgin_pressure_proxy_method =
  earliest_available_proration_year`, identity ambiguity handling, KGS KID
  fallback, Hugoton coverage sanity testing, and the sea-level atmospheric
  pressure/elevation limitation.

## Risks and Open Questions

- **Risk:** `SHUT_IN_PRESS` is wellhead pressure. The plan deliberately carries
  it as `WHP_shut_in`; #710 must not apply hydrostatic tier thresholds until it
  performs or explicitly declines a gas-column correction.
- **Risk:** API10 to API14 joins may be ambiguous. The implementation will
  fail soft at the row level with quality flags rather than fabricating API14.
- **Risk:** The issue body says the pressure data is frozen at 2013, but the
  direct-source HTTP metadata has a 2025 `Last-Modified` timestamp. The
  implementation will derive the actual observation window from parsed `YEAR`
  values, manifest both that window and the HTTP metadata, and will not imply
  current pressure coverage beyond parsed observations.
- **Risk:** `ks_wells.txt` is about 203 MB uncompressed. Parser tests should
  use tiny zip fixtures; production parsing should support chunking if memory
  pressure appears during the `/mnt/ace` smoke.
- **Open:** Whether `ks_tops.zip` should be pulled into v1 depends on the
  measured depth-join coverage from `ks_wells.DEPTH`. The plan treats tops as
  optional and out of v1 unless depth quality blocks acceptance.

## Complexity

**T2** - this creates a new but narrow source package, source manifests, parsers,
curated outputs, CLI wiring, tests, and docs. It is not cross-provider
architecture work and does not include #710 analysis/ranking.
