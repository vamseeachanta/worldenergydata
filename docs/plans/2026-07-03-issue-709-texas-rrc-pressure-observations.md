# Plan: Issue #709 - Texas RRC well pressure observations

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/709
**Status:** plan-review
**Tier:** T2 (existing Texas RRC package, direct-source packet parser extension, curated pressure table, CLI, tests, docs)
**Client:** N/A
**Project:** worldenergydata onshore pressure screen
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

Planning will use direct-source resource intelligence from official Texas RRC
datasets, the existing Texas RRC package, and local `/mnt/ace` raw snapshots.
Implementation will use single-lane development from `origin/main` after this
plan is reviewed, pushed, marked `status:plan-review`, and explicitly approved
by the user. The approved implementation will use TDD: tests will be written
before production code for packet parsing, pressure-kind semantics, API
normalization, depth selection, gradient gating, quality reporting, output
persistence, and CLI behavior.

### Reproduction proofs

N/A. Issue #709 proposes a new pressure-observation extraction surface. It does
not allege a failing test, broken import, missing method, regression, or
incorrect numeric output.

### Issue and dependency status

Planning-time issue probes on 2026-07-03 found:

| Issue | State | Current role |
|---|---|---|
| [#708](https://github.com/vamseeachanta/worldenergydata/issues/708) | open, `status:needs-plan` | Parent under-pressured / low-BHP screen epic |
| [#709](https://github.com/vamseeachanta/worldenergydata/issues/709) | open, `status:needs-plan` | This Texas RRC pressure-observation slice |
| [#710](https://github.com/vamseeachanta/worldenergydata/issues/710) | open, `status:needs-plan` | Downstream ranking and hydrostatic-tier analysis |
| [#725](https://github.com/vamseeachanta/worldenergydata/issues/725) | closed, `status:done` | Kansas KGS analog pressure table completed |
| [#669](https://github.com/vamseeachanta/worldenergydata/issues/669) | closed, `status:plan-approved` | Texas RRC official GoDrive raw refresh completed enough to unblock this plan |

The "Blocked by TX RRC raw refresh" note in #709 will be treated as stale for
implementation planning. The implementation will still reconcile raw manifests
because the local completion ZIP exists while the completion-data manifest
records an error.

### Direct-source inventory

The implementation will use official Texas RRC sources as the durable source of
record. It will not use PatchOps, Collide, commercial vendors, or historical
third-party scrapers as production inputs. The historical `rrc-scraper`
reference will remain endpoint-intelligence only; no code will be copied.

Official RRC source evidence:

| Source | Official evidence | Planned use |
|---|---|---|
| Data Sets Available for Download | RRC lists Wellbore Query Data, Statewide Oil and Gas Well Data, Oil Detail Well, Oil Well Status (26 Month W-10), Gas Well Status (26 Month G-10), and Completion Information in Data Format. Completion data includes Form G-1, W-2, G-5, G-10, P-4, P-15, W-12, and L-1. | Source catalog, raw refresh, and source caveats |
| Completion Data Subscriptions user manual | RRC defines packet records and field names for G-1, G-1 Measurement Data, G-1 Field Data, W-2, G-5, G-10, production intervals, and formation rows. | Parser field maps and pressure-kind contract |
| RRC Well Status Report Query announcement | RRC states G-10/W-10 electronic filings from 2013-09-01 onward are available through the Well Status Report Query in PDF form and support capability/status/shut-in updates. | Follow-up scope and validation path for reports not in structured packet bulk |
| RRC imaged-records menu | RRC lists historical W-10 and G-10 well status reports and historical gas well test indexes under imaged records. | Explicit out-of-scope catalog for non-structured historical pressure evidence |

Existing package catalog entries will supply:

| Catalog entry | Current direct source | Refresh cadence | Planned role |
|---|---|---|---|
| `completion_data` | `https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/#completion-data-table` with official GoDrive directory URL | nightly | Primary structured G-1/G-10/W-2 packet source |
| `wellbore_query` | `https://www.rrc.texas.gov/media/kywh5qsj/wellboredump.zip` with official GoDrive file URL | monthly beginning | API/depth/field/lease/operator reference |
| `production_pdq` | official PDQ dump | monthly last Saturday | Downstream coverage context only; not required to build raw pressure rows |

### `/mnt/ace` storage inventory

Planning-time local probes show these relevant files under the Texas RRC
storage contract:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/completions/06-29-2026.zip
  174415 bytes
/mnt/ace/worldenergydata/data/modules/texas_rrc/raw/wellbore/query/OG_WELLBORE_EWA_Report.csv
  479101960 bytes
```

The manifest summary currently reports:

```text
completion_data  error       2026-07-01T00:36:55Z  0          raw/completions
wellbore_query   downloaded  2026-07-01T00:36:12Z  479101960  raw/wellbore/query/OG_WELLBORE_EWA_Report.csv
production_pdq   downloaded  2026-06-30T15:55:07Z  3679665630 raw/production/pdq/PDQ_DSV.zip
```

The implementation will not trust raw-file presence alone. It will add a
quality/manifests check that reports:

- raw completion ZIP exists but latest completion manifest status is `error`
- ZIP byte size and SHA256 for every input file used
- RRC retrieved/source timestamps where available
- whether the run proceeds under an explicit `raw_manifest_warning` flag

The current completion ZIP contains these structured pressure-relevant record
counts:

```text
G-1                         82
G-1 Field Data              64
G-1 Formation Data          706
G-1 Measurement Data        36
G-1 Production Interval Data 85
G-10                        28
W-2                         85
W-2 Formation Data          1126
W-2 Production Interval Data 78
```

### Current code shape

- The Texas RRC package already exists at
  `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc`.
- `source_catalog.py` enforces official RRC hosts and `/mnt/ace` storage paths.
- `raw_refresh.py` and `raw_directory.py` implement official GoDrive refresh
  and manifest writing.
- `lifecycle/sources.py` reads local raw snapshots and already recognizes
  official headerless Wellbore Query rows and brace-delimited completion packet
  text.
- `lifecycle/completion_packets.py` currently extracts only coarse G-1/W-2
  completion context. It does not preserve child pressure/test/interval/
  formation records needed by #709.
- `lifecycle/keys.py` normalizes 8-, 10-, 12-, and 14-digit Texas API values to
  API14 and API10.
- Existing output writers use staged writes under `/mnt/ace`, CSV/Parquet,
  quality JSON, manifests, command text, and code revision metadata.
- `src/worldenergydata/cli/commands/texas_rrc.py` already contains the Typer
  command group for Texas RRC raw refresh, lifecycle, production atlas, field
  development, infrastructure, reports, opportunities, dossiers, and portfolio
  products.
- `tests/unit/texas_rrc` has focused unit tests for source loading, API keys,
  staged writes, CLI behavior, and downstream Texas RRC products.

### Schema and interpretation contract

The curated pressure table will target the #709 schema and add explicit
provenance fields needed to prevent false BHP interpretation:

```text
api14, api10, state, county_code, district, field_no, field_name,
lease_number, lease_name, operator_number, operator_name, well_number,
test_date, test_year, test_type, source_pressure_field, pressure_raw_psi,
pressure_unit_basis, pressure_psia, atmospheric_pressure_psi,
pressure_kind, pressure_method, reference_depth_ft, reference_depth_method,
gradient_psi_ft, gradient_method, formation, source_file,
source_record_type, source_tracking_no, source_packet_id, source_form_id,
source_row_no, source_row_id, usable_for_virgin_pressure_proxy,
is_earliest_observation_for_well, virgin_pressure_proxy_method,
quality_flags, limitations
```

Pressure-kind policy:

- `G-1.BOTTOM_HOLE_PRESS` will produce `pressure_kind=BHP_measured` only as an
  operator/RRC-reported bottom-hole pressure. The row will retain
  `source_pressure_field=BOTTOM_HOLE_PRESS` and a limitation that it has not
  been independently recalculated.
- `G-10.XBHOLE_PRESSURE` will be treated as a reported bottom-hole pressure
  candidate. It will become a curated `pressure_kind=BHP_measured` row only if
  official source semantics support that classification. If semantics remain
  ambiguous during implementation, the row will remain in normalized candidates
  and will be counted as `uncurated_ambiguous_bhp_field` rather than silently
  forcing it into the curated BHP schema.
- `G-1 Field Data` rows with `ROW_NO=SHUT-IN` and a positive `WELLHEAD_PRESS`
  will produce `pressure_kind=WHP_shut_in`.
- `G-10.SIWH_PRESSURE` will produce `pressure_kind=WHP_shut_in`.
- `G-1 Measurement Data.STATIC_CHOKE_PRESS`, `G-10.FLOWING_PRESSURE`,
  `G-5.FLOWING_TUBING_PRESSURE`, and W-2 casing/flow/fracturing pressures will
  be normalized as pressure candidates but will not be eligible for virgin BHP
  screening unless the implementation can classify the value defensibly.
- W-2 pressure-like fields will be cataloged and counted. They will become
  curated observations only when a source field maps to an accepted
  `pressure_kind`; otherwise they will remain in normalized candidate output and
  quality output will report `w2_pressure_candidates_not_curated`.

Unit policy:

- Raw pressure will always be preserved as `pressure_raw_psi`.
- `pressure_unit_basis` will record `source_psi_unspecified`,
  `psig_assumed`, `psia_reported`, or `psia_screening_conversion`.
- For surface/casing/wellhead pressure fields treated as gauge pressure, the
  curated `pressure_psia` will use
  `pressure_raw_psi + atmospheric_pressure_psi`, with
  `atmospheric_pressure_psi=14.7` and a screening limitation. If official RRC
  documentation contradicts this assumption, implementation will update tests
  and docs before publishing `/mnt/ace` outputs.
- For bottom-hole pressure fields where official units remain unspecified,
  implementation will either find source-unit evidence or mark
  `pressure_psia` as source-reported psi with a limitation. It will not drop
  `pressure_raw_psi`.

Depth and gradient policy:

- Reference depth will prefer the midpoint of the source form's producing
  interval (`G-1/W-2 Production Interval Data FROM` and `TO`) when available
  and linked to the parent pressure record.
- Fallback depth order will be: reported G-1 bottom-hole depth, reported
  vertical depth, measured depth, plug-back depth, then Wellbore Query total
  depth.
- `reference_depth_method` will record the selected denominator.
- `gradient_psi_ft` will be computed only when pressure is positive, depth is
  positive, and the API/depth join is unambiguous.
- If pressure is WHP or casing pressure, `gradient_method` will be
  `surface_pressure_over_reference_depth_screening_only`.
- If pressure is BHP reported, `gradient_method` will be
  `reported_bhp_over_reference_depth`.
- No row will be allowed to carry a numeric gradient from an ambiguous depth
  source.

API and linkage policy:

- `PACKET.api_number` values will normalize through the existing
  `normalize_api14` helper. Eight-digit RRC values will become Texas API14 via
  the existing `42` prefix and `0000` suffix convention.
- Packet parent rows will be linked to child records by `TRACKING_NO`,
  `PACKET_ID`, and `G1_ID`/`G10_ID`/`W2_ID` as applicable.
- If a pressure row lacks a parent packet context or API, it will be counted in
  quality output and excluded from curated observations.
- If multiple parent/depth contexts compete for one pressure row, the row will
  be retained as a normalized candidate and excluded from curated observations
  unless deterministic linkage can be proven by source IDs.

Virgin-pressure proxy policy:

- `is_earliest_observation_for_well` will identify the earliest usable
  pressure row per defensible well identity using `test_date`, then source
  order as deterministic tie-break.
- `usable_for_virgin_pressure_proxy` will be true only for reported BHP and
  shut-in WHP rows with defensible date, API, pressure, and reference depth.
- `virgin_pressure_proxy_method` will distinguish
  `earliest_reported_bhp`, `earliest_shut_in_whp_screening`, and
  `not_eligible`.
- #710 must continue to treat WHP-derived gradients as screening-only until it
  performs or explicitly declines a gas-column correction.

### Out of scope

The implementation will not:

- scrape PatchOps, Collide, or commercial services
- copy code from the historical `rrc-scraper` repository
- OCR imaged completion PDFs or historical microfilm scans
- scrape the Well Status Report Query PDF interface as a production source
- classify hydrostatic tiers or rank fields; that belongs to #710
- perform reserves, economics, tariff, or engineered architecture decisions
- commit raw, normalized, or curated pressure datasets to git

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-03-issue-709-texas-rrc-pressure-observations.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex inline | `scripts/review/results/2026-07-03-plan-709-codex-inline.md` |
| Pressure package init | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/__init__.py` |
| Packet field maps | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/packet_schema.py` |
| Packet parser | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/packets.py` |
| Source loading | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/sources.py` |
| Observation builder | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/observations.py` |
| Quality reporting | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/quality.py` |
| Output persistence | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/io.py` |
| CLI support | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/cli_support.py` |
| CLI command | `src/worldenergydata/cli/commands/texas_rrc.py` |
| Unit tests | `tests/unit/texas_rrc/test_pressure_observation_packet_schema.py` |
| Unit tests | `tests/unit/texas_rrc/test_pressure_observation_packets.py` |
| Unit tests | `tests/unit/texas_rrc/test_pressure_observation_sources.py` |
| Unit tests | `tests/unit/texas_rrc/test_pressure_observations.py` |
| Unit tests | `tests/unit/texas_rrc/test_pressure_observation_io.py` |
| CLI tests | `tests/unit/texas_rrc/test_pressure_observation_cli.py` |
| Docs | `docs/data-sources/onshore/texas-rrc/pressure-observations.md` |

## Deliverable

The deliverable will publish Texas RRC pressure-observation artifacts under:

```text
/mnt/ace/worldenergydata/data/modules/texas_rrc/
  normalized/
    pressure/
      packet_pressure_candidates.csv
      packet_pressure_candidates.parquet
  curated/
    pressure/
      well_pressure_observations/
        well_pressure_observations.csv
        well_pressure_observations.parquet
        coverage_by_district_decade.csv
        coverage_by_district_decade.parquet
        coverage_by_field_decade.csv
        coverage_by_field_decade.parquet
        quality.json
        manifest.json
```

The CLI will expose:

```bash
worldenergydata texas-rrc build-pressure-observations \
  --raw-root /mnt/ace/worldenergydata/data/modules/texas_rrc \
  --output-root /mnt/ace/worldenergydata/data/modules/texas_rrc
```

Writes outside the Texas RRC `/mnt/ace` module root will be rejected unless a
test-only `--allow-non-ace-output` path is used.

## Pseudocode

```python
def load_pressure_sources(raw_root):
    read raw/completions zip files and wellbore query csv
    read manifests under raw_root/manifests
    report source gaps and manifest warnings
    return completion archives, wellbore reference frame, manifest evidence
```

```python
def parse_completion_packet_archive(zip_path):
    for packetData file in the zip:
        parse brace-delimited records
        collect PACKET context rows
        collect G-1, G-1 Field Data, G-1 Measurement Data, G-10, W-2,
        production interval, and formation records
        link children to parents by tracking/packet/form ids
        emit normalized pressure candidates with source_file and row ids
```

```python
def classify_pressure_candidate(row):
    preserve pressure_raw_psi and source_pressure_field
    assign pressure_kind only when source field semantics are defensible
    convert surface pressures to pressure_psia with documented 14.7 psi
    assumption where applicable
    retain uncurated candidates with quality flags
```

```python
def select_reference_depth(candidate, intervals, formations, wellbore):
    prefer linked production interval midpoint
    fallback through G-1 bottom-hole depth, vertical depth, measured depth,
    plug-back depth, then Wellbore Query total depth
    suppress depth and gradient when the source linkage is ambiguous
```

```python
def build_pressure_observations(candidates, wellbore):
    normalize api14/api10
    filter to positive pressure and defensible pressure_kind
    join depth and field context
    compute gradients only under pressure/depth/linkage guardrails
    mark earliest usable row per well as the virgin-pressure proxy
    compute coverage by district, field, and decade
    return observations, coverage tables, quality report
```

```python
def write_pressure_outputs(root, candidates, observations, coverage, quality):
    enforce /mnt/ace root unless allow_non_ace_root
    write normalized candidates and curated observations as CSV and Parquet
    write quality.json and manifest.json through staged paths
    include input manifests, hashes, row counts, command, code revision, and
    source limitation metadata
```

## Plan

### Task 1 - Add pressure-observation package shell and schema maps

Write failing tests for:

- pressure-observation package imports cleanly
- field maps include every pressure-source record type planned for v1
- G-1 field map exposes `BOTTOM_HOLE_PRESS` and `BOTTOM_HOLE_DEPTH`
- G-1 Field Data map exposes `ROW_NO` and `WELLHEAD_PRESS`
- G-1 Measurement Data map exposes `STATIC_CHOKE_PRESS`
- G-10 map exposes `XBHOLE_PRESSURE`, `SIWH_PRESSURE`, `FLOWING_PRESSURE`,
  `DATE_TESTED`, and `REASON_CODE`
- W-2 pressure-like fields are flagged as candidates until classified
- production interval and formation maps expose depth and formation fields

Create `pressure_observations/packet_schema.py` and a package init. The schema
maps will be derived from the official RRC Completion Data Subscriptions
manual and will be tested with tiny packet fixtures.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest \
    tests/unit/texas_rrc/test_pressure_observation_packet_schema.py -q
```

### Task 2 - Parse packet records into normalized pressure candidates

Write failing tests for:

- brace-delimited packet files with PACKET, G-1, G-1 Field Data, G-1
  Measurement Data, G-10, W-2, production interval, and formation rows
- parent/child linkage by `TRACKING_NO`, `PACKET_ID`, and form ID
- source row IDs that remain stable across ZIP ordering
- API normalization through existing Texas API helper
- malformed rows counted in quality rather than crashing the run
- candidate rows preserving raw pressure values, source field names, source
  file names, and packet IDs
- unlinked child pressure rows excluded from curated observations and counted

Create `pressure_observations/packets.py`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest \
    tests/unit/texas_rrc/test_pressure_observation_packets.py -q
```

### Task 3 - Load direct sources and reconcile manifests

Write failing tests for:

- existing completion ZIPs under `raw/completions` are discovered
- headerless Wellbore Query CSV is loaded through existing source semantics
- missing completion ZIP reports a blocking `completion_data` source gap
- completion ZIP present with manifest `status=error` reports a non-blocking
  `raw_manifest_warning`
- input file byte sizes and SHA256 values appear in pressure output manifest
- no network or third-party validation source is required to build from local
  official snapshots

Create `pressure_observations/sources.py`. The implementation will reuse the
existing source catalog and raw manifest conventions instead of introducing a
new source registry.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest \
    tests/unit/texas_rrc/test_pressure_observation_sources.py -q
```

### Task 4 - Classify pressures, select depths, and build observations

Write failing tests for:

- G-1 `BOTTOM_HOLE_PRESS` emits reported BHP with raw/source provenance
- G-1 Field Data `ROW_NO=SHUT-IN` plus `WELLHEAD_PRESS` emits shut-in WHP
- G-10 `SIWH_PRESSURE` emits shut-in WHP
- G-10 `XBHOLE_PRESSURE` emits curated BHP only with explicit source-field
  provenance and source semantics; otherwise it remains an uncurated candidate
- W-2 pressure candidates are counted and not misclassified as BHP without a
  defensible pressure-kind map
- pressure values of zero, blank, or non-numeric do not become curated rows
- gauge surface pressures convert to `pressure_psia` with 14.7 psi and a
  limitation
- raw pressure and unit basis are retained for every curated row
- interval midpoint depth is preferred over Wellbore Query total depth
- fallback depth order is deterministic and reflected in
  `reference_depth_method`
- gradient is null when pressure, depth, API, or depth linkage is invalid
- WHP-derived gradients use `surface_pressure_over_reference_depth_screening_only`
- reported-BHP gradients use `reported_bhp_over_reference_depth`
- earliest usable pressure per well is flagged as the virgin-pressure proxy
- ineligible pressure candidates carry `usable_for_virgin_pressure_proxy=false`
- coverage summaries group by district and decade and by field and decade

Create `pressure_observations/observations.py` and
`pressure_observations/quality.py`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest \
    tests/unit/texas_rrc/test_pressure_observations.py -q
```

### Task 5 - Persist outputs and wire CLI

Write failing tests for:

- ACE-root guard rejects non-ACE output roots by default
- test-only non-ACE override works for isolated fixtures
- staged writes produce normalized candidate CSV/Parquet, curated observation
  CSV/Parquet, coverage CSV/Parquet, quality JSON, and manifest JSON
- manifest contains input paths, source URLs, raw manifest metadata, file
  hashes, row counts, command text, code revision, and limitations
- CLI dry-run reports candidate, curated, and coverage counts without writing
- CLI build writes the complete output packet to a temporary root in tests
- `--require-sources` fails when direct official raw sources are missing

Create `pressure_observations/io.py`,
`pressure_observations/cli_support.py`, and a new Typer command inside
`src/worldenergydata/cli/commands/texas_rrc.py`.

Verification:

```bash
PYTHONPATH="$(printf '%s:' packages/*/src)src" \
  uv run --no-sync pytest \
    tests/unit/texas_rrc/test_pressure_observation_io.py \
    tests/unit/texas_rrc/test_pressure_observation_cli.py -q
```

### Task 6 - Documentation and `/mnt/ace` smoke

Write `docs/data-sources/onshore/texas-rrc/pressure-observations.md` with:

- official RRC source URLs and refresh cadences
- storage layout
- command usage
- output schema
- pressure-kind and unit policy
- WHP-vs-BHP and screening-gradient limitations
- manifest-warning behavior for current completion-data raw snapshots
- relationship to [#708](https://github.com/vamseeachanta/worldenergydata/issues/708),
  [#710](https://github.com/vamseeachanta/worldenergydata/issues/710), and
  completed [#725](https://github.com/vamseeachanta/worldenergydata/issues/725)

Run the CLI against `/mnt/ace/worldenergydata/data/modules/texas_rrc` and
record candidate rows, curated rows, district/decade coverage, field/decade
coverage, and quality warnings in the issue closeout comment. Generated data
will remain outside git.

## Files to Change

| Action | Path | Reason |
|---|---|---|
| Create | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/` | pressure-observation parser, builder, quality, IO, CLI support |
| Modify | `src/worldenergydata/cli/commands/texas_rrc.py` | add `build-pressure-observations` command |
| Create | `tests/unit/texas_rrc/test_pressure_observation_packet_schema.py` | schema-map TDD |
| Create | `tests/unit/texas_rrc/test_pressure_observation_packets.py` | packet parsing TDD |
| Create | `tests/unit/texas_rrc/test_pressure_observation_sources.py` | direct-source and manifest TDD |
| Create | `tests/unit/texas_rrc/test_pressure_observations.py` | pressure/depth/gradient/proxy TDD |
| Create | `tests/unit/texas_rrc/test_pressure_observation_io.py` | output writer TDD |
| Create | `tests/unit/texas_rrc/test_pressure_observation_cli.py` | CLI TDD |
| Create | `docs/data-sources/onshore/texas-rrc/pressure-observations.md` | user-facing source and output documentation |
| Update | `docs/plans/README.md` | add #709 plan row and move closed #725 out of active list |

## TDD Test List

| Test name | What it verifies | Expected input | Expected output |
|---|---|---|---|
| `test_packet_schema_maps_g1_pressure_fields` | official G-1 field map | schema map | BHP/depth fields present |
| `test_packet_schema_maps_g1_field_pressure_rows` | shut-in wellhead map | schema map | `ROW_NO`, `WELLHEAD_PRESS` present |
| `test_packet_schema_maps_g10_pressure_fields` | G-10 pressure map | schema map | `XBHOLE_PRESSURE`, `SIWH_PRESSURE`, date fields present |
| `test_packet_parser_links_g1_children_to_packet_context` | parent/child linkage | tiny G-1 packet | API, field, child pressure row linked |
| `test_packet_parser_links_g10_rows_to_packet_context` | G-10 linkage | tiny G-10 packet | date, SIWH, API linked |
| `test_packet_parser_counts_malformed_rows` | parser fail-soft | bad brace row | quality count, no crash |
| `test_sources_discover_completion_zip_and_wellbore_csv` | local official source discovery | temp raw tree | source inputs returned |
| `test_sources_report_manifest_warning_for_error_manifest_with_present_zip` | current `/mnt/ace` hazard | present ZIP plus error manifest | non-blocking warning |
| `test_g1_bottom_hole_pressure_builds_reported_bhp_row` | reported BHP mapping | G-1 BHP fixture | curated BHP row |
| `test_g1_shut_in_field_data_builds_whp_row` | shut-in WHP mapping | G-1 Field Data fixture | WHP row with source field |
| `test_g10_siwh_builds_whp_row` | G-10 shut-in mapping | G-10 fixture | WHP row |
| `test_w2_pressure_candidates_are_not_misclassified_as_bhp` | W-2 semantic guard | W-2 pressure fixture | candidate count, no BHP row |
| `test_surface_pressure_psig_converts_to_psia_with_limitation` | unit policy | WHP 100 psig | pressure_psia 114.7 and limitation |
| `test_gradient_prefers_producing_interval_midpoint` | depth priority | interval 1000-1200 | reference depth 1100 |
| `test_gradient_suppressed_for_ambiguous_depth_join` | no arbitrary denominator | ambiguous depth rows | null depth/gradient with flag |
| `test_reported_bhp_gradient_uses_reported_bhp_method` | gradient method | BHP plus depth | reported-BHP method |
| `test_whp_gradient_is_screening_only` | WHP limitation | WHP plus depth | screening-only method |
| `test_earliest_usable_observation_is_virgin_proxy` | #710 dependency | two dated rows | earliest flagged |
| `test_ineligible_candidate_not_virgin_proxy` | proxy guard | flowing pressure row | proxy false |
| `test_coverage_groups_by_district_and_decade` | required stats | sample observations | grouped counts |
| `test_output_writer_enforces_ace_root` | storage guard | non-ACE root | `ValueError` |
| `test_output_writer_writes_packet_with_manifest` | output persistence | sample dataframes | all output files present |
| `test_cli_dry_run_reports_counts_without_writes` | CLI dry-run | temp raw fixtures | no curated output |
| `test_cli_build_writes_pressure_packet` | CLI build | temp raw fixtures | manifest and datasets written |

## Acceptance Criteria

- [ ] `worldenergydata.texas_rrc.pressure_observations` imports cleanly.
- [ ] Official RRC completion packet and wellbore sources are loaded from the
      existing `/mnt/ace` storage contract.
- [ ] Completion raw manifest warnings are surfaced when a ZIP exists but the
      latest manifest status is `error`.
- [ ] Structured G-1, G-1 Field Data, G-1 Measurement Data, G-10, W-2,
      production interval, and formation rows are parsed into normalized
      pressure candidates.
- [ ] Curated pressure observations are written under
      `/mnt/ace/worldenergydata/data/modules/texas_rrc/curated/pressure/well_pressure_observations/`.
- [ ] Normalized pressure candidates are written under
      `/mnt/ace/worldenergydata/data/modules/texas_rrc/normalized/pressure/`.
- [ ] Curated rows preserve raw pressure, source pressure field, unit basis,
      pressure kind, pressure method, and limitations.
- [ ] Wellhead/casing gauge-pressure conversions to `pressure_psia` use an
      explicit atmospheric-pressure assumption and limitation.
- [ ] W-2 pressure candidates are not silently represented as BHP.
- [ ] Gradient computation is guarded by positive pressure, positive reference
      depth, defensible pressure kind, and unambiguous source/depth linkage.
- [ ] Earliest usable pressure per well is flagged as the virgin-pressure proxy
      for #710, with method and eligibility fields.
- [ ] Coverage stats report how many wells have at least one pressure
      observation by district and decade, and by field and decade.
- [ ] Quality output reports candidate counts, curated counts, pressure-kind
      counts, uncurated candidate reasons, missing API, missing depth,
      ambiguous linkage, unit assumptions, manifest warnings, and source gaps.
- [ ] Documentation explains source URLs, refresh cadences, storage layout,
      schema, command usage, and WHP/BHP limitations.
- [ ] Focused tests pass:
      `PYTHONPATH="$(printf '%s:' packages/*/src)src" uv run --no-sync pytest tests/unit/texas_rrc/test_pressure_observation_packet_schema.py tests/unit/texas_rrc/test_pressure_observation_packets.py tests/unit/texas_rrc/test_pressure_observation_sources.py tests/unit/texas_rrc/test_pressure_observations.py tests/unit/texas_rrc/test_pressure_observation_io.py tests/unit/texas_rrc/test_pressure_observation_cli.py -q`
- [ ] Formatting/lint pass for touched Python:
      `uv run --no-sync black --check --diff packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations src/worldenergydata/cli/commands/texas_rrc.py tests/unit/texas_rrc/test_pressure_observation*.py`
      and
      `uv run --no-sync isort --check-only --diff packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations src/worldenergydata/cli/commands/texas_rrc.py tests/unit/texas_rrc/test_pressure_observation*.py`
      and
      `uv run --no-sync ruff check packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations src/worldenergydata/cli/commands/texas_rrc.py tests/unit/texas_rrc/test_pressure_observation*.py`
- [ ] `scripts/legal/legal-sanity-scan.sh` passes before commit.
- [ ] Heavy raw, normalized, and curated data stays under `/mnt/ace` and is not
      committed to git.
- [ ] Code-stage adversarial review is recorded before closeout.

## Adversarial Review Summary

Plan-stage inline review is recorded at
`scripts/review/results/2026-07-03-plan-709-codex-inline.md`.

| Reviewer | Verdict | Disposition |
|---|---|---|
| Codex inline | MINOR | Plan includes source-of-record guardrails, manifest reconciliation, pressure-unit provenance, W-2 non-BHP guardrails, depth/gradient gating, virgin-proxy fields, and code-stage review acceptance. |

Implementation remains blocked until explicit user approval moves
[#709](https://github.com/vamseeachanta/worldenergydata/issues/709) to
`status:plan-approved`.

## Risks and Open Questions

- **Risk:** Official RRC packet pressure fields do not always state gauge vs
  absolute units. The implementation will retain raw values, unit basis, and
  limitations instead of emitting undocumented pressure semantics.
- **Risk:** W-2 records contain pressure-like fields that may not represent
  reservoir or shut-in pressure. The plan will keep them as candidates unless a
  defensible pressure-kind map exists.
- **Risk:** The current completion ZIP is small and daily. It will seed the
  parser and smoke output, but statewide historical pressure coverage may need
  the separate 26-month G-10/W-10 datasets or imaged-status workflow in a
  follow-up issue.
- **Open:** Whether G-10 `XBHOLE_PRESSURE` should map to `BHP_measured` or
  remain an uncurated candidate depends on implementation-time source-unit and
  field-definition evidence.
- **Open:** Whether #710 should use WHP rows directly, gas-column-correct them,
  or restrict ranking to reported BHP rows remains downstream analysis policy.

## Complexity

**T2** - this extends an existing Texas RRC package with a bounded parser,
curated output product, CLI command, tests, and docs. It does not include
statewide pressure ranking, PDF/OCR extraction, or a generic state-regulator
framework.
