# Plan: Issue #751 - Colorado ECMC Form 5A initial-test pressure ingest

**Issue:** https://github.com/vamseeachanta/worldenergydata/issues/751
**Status:** plan-review
**Tier:** T3 (production-grade direct-source HTML ingest, resumable `/mnt/ace` writes, pressure-screen contract risk)
**Client:** N/A
**Project:** worldenergydata onshore pressure screen
**Lane:** codex

## Resource Intelligence Summary

### Execution mode

The planning stage will use `parallel-readonly` evidence gathering where
possible. The implementation stage will use `single-lane` because it will touch
shared Colorado ECMC modules, underpressured-screen normalization contracts, and
large `/mnt/ace` data outputs that should not race across workers.

Implementation will not begin until this plan is reviewed, pushed, moved to
`status:plan-review`, and explicitly approved by the user as
`status:plan-approved`.

### Issue and dependency status

Planning-time probes on 2026-07-04 show:

| Issue | State | Current role |
|---|---|---|
| [#745](https://github.com/vamseeachanta/worldenergydata/issues/745) | closed, `status:done` | Colorado bulk Form 7 production + WELLS GIS spine |
| [#749](https://github.com/vamseeachanta/worldenergydata/issues/749) | closed, `status:done` | FacilityDetail/Form 5A source-discovery scout |
| [#751](https://github.com/vamseeachanta/worldenergydata/issues/751) | open, `status:needs-plan` | This production-grade FacilityDetail/Form 5A ingest |
| [#708](https://github.com/vamseeachanta/worldenergydata/issues/708) | open parent epic | Multi-state underpressured-screen lifecycle |

[#751](https://github.com/vamseeachanta/worldenergydata/issues/751) will build
from the official source proof in [#749](https://github.com/vamseeachanta/worldenergydata/issues/749).
It will not reinterpret the [#745](https://github.com/vamseeachanta/worldenergydata/issues/745)
Form 7 pressure columns as usable Colorado pressure evidence.

### Parallel work check

Active process checks on 2026-07-04 showed unrelated Claude work in other
worktrees, including `worldenergydata-autorun`, and no active job using
`/mnt/local-analysis/wt-wed-669`. This plan branch is
`plan/colorado-ecmc-form5a-ingest-751`.

Implementation will avoid unrelated Texas RRC, FDAS, pages, and field-portfolio
work. The expected write surfaces are limited to:

- `config/colorado_ecmc_facility_detail_ingest.yml`
- `src/worldenergydata/modules/state_regulators/colorado_ecmc/`
- `src/worldenergydata/analysis/underpressured_screen/observations.py` only if
  a reviewed schema adapter is required
- `tests/unit/modules/state_regulators/`
- `tests/unit/analysis/`
- `docs/data-sources/onshore/state-well-databases/`
- `docs/plans/`
- `scripts/review/results/`

### Reproduction proofs

N/A as a failure reproduction: [#751](https://github.com/vamseeachanta/worldenergydata/issues/751)
is a feature/ingest issue, not a reported regression.

Planning-time source proofs will be used instead:

```text
Command: /usr/bin/python3 urlopen FacilityDetail api=12339345
Result: HTTP status 200, 50,740 bytes,
        Initial Test Data=True, CASING_PRESS=True,
        TUBING_PRESS=True, FacilityID=True
```

```text
Command: jq . /mnt/ace/.../source_discovery/reports/colorado_ecmc_pressure_source_discovery.json
Result: request_count=1, parsed_row_count=11,
        candidate_pressure_count=2,
        decision=facility_detail_candidate_for_follow_up
```

```text
Command: /usr/bin/python3 read_parquet /mnt/ace/.../colorado_ecmc/normalized/wells/wells.parquet
Result: 124,332 wells; columns include api12, api10, api_label,
        facility_id, field, max_md_ft, max_tvd_ft, latitude, longitude
```

```text
Command: /usr/bin/python3 read_parquet /mnt/ace/.../colorado_ecmc/normalized/production/production_pressure_rows.parquet
Result: 1,060,209 production rows
Quality: zero positive GasPressureTubing/GasPressureCasing/
         WaterPressureTubing/WaterPressureCasing values
```

### Direct-source and identifier evidence

The official source path is:

```text
https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx?api={API_FRAGMENT}
```

The [#749](https://github.com/vamseeachanta/worldenergydata/issues/749) scout
proved that `api=12339345` renders Form 5A-like Initial Test Data. The raw
HTML and parsed output remain under:

```text
/mnt/ace/worldenergydata/data/modules/colorado_ecmc/source_discovery/
```

The raw WELLS shapefile is the approved source-list spine. Planning probes
showed the raw DBF fields include:

```text
API, API_County, API_Seq, API_Label, Facil_Id, Field_Name, Max_MD, Max_TVD
```

and the first raw rows look like:

```text
API='12332498', API_Label='05-123-32498', Facil_Id=420193
API='12324638', API_Label='05-123-24638', Facil_Id=288652
```

This matters because FacilityDetail expects the 8-digit county+sequence
fragment, while downstream screen contracts require the `05`-prefixed API10/12.
The implementation will therefore derive the request key from raw `API` or
`API_County` + `API_Seq`, validate it against `API_Label`, and keep separate
full API keys for joins. It will not blindly use any one normalized parquet
identifier without validation.

### Existing code state

Current Colorado modules provide:

- `pipeline.py`: direct-source downloads, raw manifesting, production/wells
  normalization, and `/mnt/ace` output for [#745](https://github.com/vamseeachanta/worldenergydata/issues/745).
- `facility_detail.py`: fixture-backed parser and candidate-pressure
  classifier for Initial Test Data.
- `source_discovery.py`: capped one-page scout that writes raw HTML, parsed
  JSON/parquet, and a decision report.
- `observations.py`: underpressured-screen adapters for Texas, Oklahoma, and
  Colorado Form 7 production pressure rows.

Current gaps for [#751](https://github.com/vamseeachanta/worldenergydata/issues/751):

- no approved source-list builder for FacilityDetail pages;
- no resumable downloader with retry/backoff and per-page status sidecars;
- no parser-drift policy for pages with missing or changed Initial Test Data;
- no statewide coverage accounting by API/facility/field;
- no curated Form 5A initial-test pressure observation table;
- no screen promotion gate separating candidate output from active
  underpressured-screen participation;
- no shut-in-vs-flowing interpretation gate for FacilityDetail Initial Test
  Data pressure fields.

## Artifact Map

| Artifact | Path |
|---|---|
| Plan | `docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md` |
| Plan index row | `docs/plans/README.md` |
| Plan review - Codex inline | `scripts/review/results/2026-07-04-plan-751-codex-inline.md` |
| Plan review - external provider if available | `scripts/review/results/2026-07-04-plan-751-<provider>.md` |
| Ingest config | `config/colorado_ecmc_facility_detail_ingest.yml` |
| Source-list and ingest module | `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py` |
| Parser hardening | `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py` |
| Optional screen adapter | `src/worldenergydata/analysis/underpressured_screen/observations.py` |
| Unit tests | `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py` |
| Parser regression tests | `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py` |
| Optional screen tests | `tests/unit/analysis/test_underpressured_observations.py` |
| Source docs | `docs/data-sources/onshore/state-well-databases/colorado-ecmc-pressure-source-discovery.md`, `docs/data-sources/onshore/state-well-databases/source-catalog.md` |

## Deliverable

The approved implementation will add a production-grade but controlled
FacilityDetail/Form 5A ingest lane. Heavy source data will remain under
`/mnt/ace`, with repo-tracked code, config, tests, and docs only.

Planned `/mnt/ace` layout:

```text
/mnt/ace/worldenergydata/data/modules/colorado_ecmc/facility_detail_ingest/
  source_lists/
    facility_detail_source_list.parquet
    facility_detail_source_list_quality.json
  raw/
    facility_detail/
      manifest.jsonl
      status/
        fetched.jsonl
        skipped.jsonl
        failed.jsonl
      html/
        {api_fragment}.html
  parsed/
    facility_detail_initial_tests.parquet
    facility_detail_initial_tests.json
    parser_quality.json
  curated/
    pressure/
      well_pressure_observations.parquet
      colorado_ecmc_form5a_pressure_observation_quality.json
  reports/
    colorado_ecmc_form5a_ingest_summary.json
```

The default config will be conservative: it will support a configured
`max_requests` cap and will not run an unbounded statewide crawl unless the
operator explicitly supplies an approved full source list and cap settings.

## Implementation Plan

### Task 1: Define the production ingest config and source-list builder

**Files:**

- Create: `config/colorado_ecmc_facility_detail_ingest.yml`
- Create: `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py`

**Work:**

1. Add config sections for storage, source-list input, FacilityDetail endpoint,
   request throttle, retry/backoff, timeout, resume behavior, and hard caps.
2. Build `build_facility_detail_source_list(wells, config)` that will:
   - require `API`, `API_County`, `API_Seq`, `API_Label`, `Facil_Id`,
     `Field_Name`, `Max_MD`, and `Max_TVD` when reading raw WELLS DBF data;
   - derive `api_fragment` as an 8-digit county+sequence key;
   - derive `api10` as `05` + `api_fragment`;
   - keep `api12` null unless a verified sidetrack/API12 source is available;
     the implementation will not invent a default `00` sidetrack for screen
     joins;
   - validate `API_Label` against the derived API;
   - deduplicate by `api_fragment`;
   - preserve `facility_id`, field, depth, and coordinates for later joins;
   - write source-list quality counts under `/mnt/ace`.
3. Add guardrails that fail closed when the source list is empty, identifiers
   cannot be validated, or `max_requests` exceeds an explicitly approved list
   size without `allow_full_source_list: true`.
4. Add staged-run controls for production scale:
   - `dry_run_source_list_only`;
   - `max_requests`;
   - `max_failures`;
   - `max_parser_drift_fraction`;
   - `stop_on_identity_mismatch`;
   - a run summary that estimates requested page count before any fetch starts.

**TDD tests:**

- config requires direct ECMC URL, `/mnt/ace` output root, throttle, retry, and
  cap fields;
- source-list builder derives `12332498` and `0512332498` correctly from raw
  WELLS rows;
- API-label mismatch raises a clear error;
- duplicate API fragments collapse to one request row with coverage counts;
- unbounded full-population mode fails closed unless explicitly configured;
- source-list output leaves `api12` null when no verified sidetrack/API12
  source exists.

### Task 2: Add a resumable FacilityDetail downloader

**Files:**

- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py`

**Work:**

1. Implement a downloader that iterates the approved source list, sends a
   polite configured User-Agent, sleeps between requests, and writes each raw
   page to a deterministic path by `api_fragment`.
2. Record request metadata in append-safe JSONL status files:
   `source_url`, `api_fragment`, `facility_id`, `status_code`, `raw_path`,
   `size_bytes`, `sha256`, `downloaded_at`, retry count, and error text.
3. Support resume:
   - skip already fetched non-empty HTML with matching status metadata;
   - retry failed rows only when requested;
   - never delete previous raw evidence during a resume.
4. Implement bounded retry/backoff for transient network and HTTP failures.
   HTTP 403/404 and rendered "not found" pages will be terminal, non-retryable
   statuses; 5xx/timeouts will be retryable.
5. Parse each fetched page enough to verify that the rendered API/facility
   identity matches the requested source-list row. Mismatches will be
   `identity_mismatch`, excluded from parsed/curated pressure outputs, and
   counted as fail-closed quality defects.
6. Keep a default serial fetch mode; no parallel downloader will be introduced
   in this issue.

**TDD tests:**

- mocked HTTP success writes raw HTML and fetched status rows;
- existing raw HTML is skipped on resume and counted as skipped;
- transient errors retry up to the configured limit and then write failed
  status;
- non-200 or empty pages are kept out of parsed pressure outputs;
- HTTP 403/404 are terminal and not retried;
- rendered page API/facility identity mismatch is excluded and counted;
- request delay is called between requests when more than one row is fetched.

### Task 3: Harden parsing and parser-drift detection

**Files:**

- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py`
- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py`

**Work:**

1. Keep the existing structured HTML parser but add page-level parse status:
   `parsed`, `no_initial_test_data`, `missing_required_context`, or
   `parser_drift`.
2. Enumerate every Initial Test Data block on a page. Each parsed block will be
   paired with the nearest completed interval/formation/wellbore context; if
   this pairing cannot be established, the block will be counted as
   `missing_required_context` and excluded.
3. Require context fields needed for screen candidates: API, facility id,
   field, formation, interval/depth context, test date, and measure rows.
4. Add quality sidecar counts by parse status, pressure kind, field, source
   list denominator, missing depth, missing field, and missing test date.
5. Keep MIT/Form 21, Form 17/bradenhead, and treatment pressures excluded.
6. Add regression fixtures for:
   - a valid Initial Test Data block;
   - a page with multiple Initial Test Data blocks;
   - a page with no Initial Test Data;
   - a malformed or renamed table that should fail closed as parser drift.

**TDD tests:**

- valid fixture parses candidate `CASING_PRESS` and `TUBING_PRESS`;
- multi-block fixture emits one row set per completed interval and does not
  pair pressures with the wrong interval/depth;
- no-initial-test page is a non-error coverage outcome;
- malformed table increments `parser_drift_count` and does not emit pressure
  observations;
- treatment/MIT/bradenhead lanes remain excluded.

### Task 4: Build curated Form 5A pressure observations and quality gates

**Files:**

- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py`
- Optional modify: `src/worldenergydata/analysis/underpressured_screen/observations.py`
- Test: `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py`
- Optional test: `tests/unit/analysis/test_underpressured_observations.py`

**Work:**

1. Convert classified candidate rows into a curated candidate-observation table
   only for Initial Test Data `CASING_PRESS` and `TUBING_PRESS`.
2. Preserve reported pressure as psig and add psia using configured
   `atmospheric_psi`.
3. Add an explicit interpretation model:
   - `TUBING_PRESS` will be tagged as `flowing_tubing_initial_test` and will
     not be screen-promotable in this issue.
   - `CASING_PRESS` will be tagged as `initial_test_casing_pressure_unverified`
     and will remain candidate-only unless a reviewed interpretation rule can
     prove it is a shut-in wellhead datum.
   - only measurements explicitly mapped to `WHP_shut_in` by a future reviewed
     rule may use the underpressured screen's static gas-column correction.
   - the promotion report will include gradient-distribution sanity checks
     before any future screen activation.
4. Select reference depth in a documented order:
   interval bottom, vertical TD, WELLS `Max_TVD`, then WELLS `Max_MD`; rows
   without positive depth will be counted and excluded from screen-ready output.
5. Add `test_year`, `test_type`, `source_name`,
   `source_discovery_sha256`/raw lineage, `era=completion_initial_test`, and
   `screen_observation_priority`.
6. Add a concrete `colorado_ecmc_form5a_v1` normalization contract if any
   screen adapter is introduced:
   - `well_key`: `CO_ECMC_FACILITY:{facility_id}` when facility id is present,
     else `CO_ECMC_API10:{api10}`;
   - `state`: `CO`;
   - `field`: parsed FacilityDetail field;
   - `test_year`: parsed Initial Test Data year;
   - `pressure_kind`: candidate kind, with screen-promotable rows limited to
     future `WHP_shut_in` mappings;
   - `pressure_psia`: reported psig plus atmospheric pressure;
   - `reference_depth_ft`: selected depth after the documented quality gate.
7. Keep the underpressured-screen config unchanged unless the quality and
   interpretation gates pass a reviewed threshold. The implementation may add a
   schema adapter for candidate output, but it will not silently turn Colorado
   participation on in `config/underpressured_screen.yml`.
8. Write a promotion report that states whether the output is:
   `candidate_only`, `screen_ready_but_not_configured`, or `configured_for_screen`.
   The expected result for this issue is `candidate_only` unless the
   implementation proves a shut-in datum and passes the sanity checks.

**TDD tests:**

- candidate casing/tubing rows become curated rows with psig/psia/depth fields;
- flowing tubing rows are excluded from screen promotion;
- no row is fed to the screen's static gas-column correction unless it is
  explicitly mapped to `WHP_shut_in`;
- rows with missing depth or missing field are excluded and counted;
- earliest-observation flags prefer earliest test date and pressure priority;
- Form 5A adapter normalizes to `colorado_ecmc_form5a_v1` if added;
- `near_vacuum` behavior is documented as shut-in-only and not applied to
  candidate initial-test pressure kinds;
- screen config remains unchanged unless promotion criteria are explicitly met.

### Task 5: Add CLI, documentation, and closeout reporting

**Files:**

- Modify: `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py`
- Modify: `docs/data-sources/onshore/state-well-databases/colorado-ecmc-pressure-source-discovery.md`
- Modify: `docs/data-sources/onshore/state-well-databases/source-catalog.md`

**Work:**

1. Add a CLI entry point to run the source-list, download, parse, curate, and
   report stages from one config.
2. Document refresh cadence:
   - WELLS source list is daily from the official GIS ZIP;
   - FacilityDetail is a live COGIS page and will require a polite refresh
     cadence, not a blind daily statewide crawl;
   - production pressure columns remain monthly/annual but are not the Form 5A
     target.
3. Document `/mnt/ace` outputs and expected report fields.
4. Add a short operational note that local Miniforge `python3` may lack parquet
   support; verified test/runtime commands should use `/usr/bin/python3` or the
   repo CI environment when writing parquet.

## Pseudocode

```python
def run_facility_detail_ingest(config_path):
    config = load_config(config_path)
    wells = read_raw_wells_source(config["source_list"])
    source_list, source_quality = build_facility_detail_source_list(wells, config)
    write_source_list_outputs(source_list, source_quality, config)

    fetch_manifest = fetch_facility_detail_pages(source_list, config)
    parsed_pages = parse_facility_detail_pages(fetch_manifest, config)
    classified = classify_facility_detail_pressures(parsed_pages.initial_tests)
    candidates, quality = build_form5a_pressure_candidates(
        classified,
        source_list,
        config["pressure_observations"],
    )
    promotion = evaluate_screen_promotion(candidates, quality, config)
    write_outputs(fetch_manifest, parsed_pages, candidates, quality, promotion, config)
    return build_ingest_summary(source_quality, fetch_manifest, quality)
```

## Files to Change

- `config/colorado_ecmc_facility_detail_ingest.yml`
- `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py`
- `src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py`
- `src/worldenergydata/analysis/underpressured_screen/observations.py` only if a
  reviewed schema adapter is needed
- `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py`
- `tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py`
- `tests/unit/analysis/test_underpressured_observations.py` only if the adapter
  is added
- `docs/data-sources/onshore/state-well-databases/colorado-ecmc-pressure-source-discovery.md`
- `docs/data-sources/onshore/state-well-databases/source-catalog.md`

## TDD Test List

The implementation will start by writing failing tests for:

1. ingest config safety fields and direct-source URL;
2. source-list API derivation from raw WELLS rows;
3. source-list identifier mismatch fail-closed behavior;
4. resumable downloader success/skip/failure status rows;
5. retry/backoff and throttle behavior;
6. parser statuses for valid, no-initial-test, and parser-drift pages;
7. enumeration of multiple Initial Test Data blocks per page;
8. page identity checks matching rendered API/facility to the request;
9. classification of `CASING_PRESS` and `TUBING_PRESS` only;
10. exclusion of treatment, MIT/Form 21, and Form 17/bradenhead pressure lanes;
11. curated candidate psig-to-psia conversion and depth selection;
12. shut-in-vs-flowing interpretation and no static correction for flowing rows;
13. quality sidecar counts and promotion decision;
14. `colorado_ecmc_form5a_v1` adapter normalization if added.

Expected RED workflow before implementation:

```bash
# after adding failing assertions, not just relying on collection failure
PYTHONPATH=src:packages/worldenergydata-core/src /usr/bin/python3 -m pytest \
  tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py \
  tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py \
  -q
```

Expected GREEN/regression command after implementation:

```bash
PYTHONPATH=src:packages/worldenergydata-core/src /usr/bin/python3 -m pytest \
  tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py \
  tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py \
  tests/unit/modules/state_regulators/test_colorado_ecmc_pipeline.py \
  tests/unit/modules/state_regulators/test_colorado_ecmc_parsers.py \
  tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py \
  tests/unit/analysis/test_underpressured_observations.py \
  tests/unit/analysis/test_underpressured_screen.py \
  -q
```

## Acceptance Criteria

- A reviewed plan will be posted before implementation.
- The ingest will use an approved source list from official ECMC WELLS data and
  will not start from a hidden full-population scrape.
- The default config will include throttle, retry/backoff, timeout, resume, and
  hard-cap controls.
- Raw/source data will be written under `/mnt/ace`; the repo will carry only
  code, tests, config, docs, and review artifacts.
- The downloader will be resumable and will preserve per-page status/provenance.
- Parser drift will fail closed and will be counted in a quality sidecar.
- Coverage accounting will report source-list denominator, fetched/skipped/failed
  pages, parse statuses, candidate rows, curated rows, and excluded rows.
- Only Initial Test Data `CASING_PRESS` and `TUBING_PRESS` will become Form 5A
  candidate pressure observations.
- `TUBING_PRESS` will remain flowing-pressure candidate evidence and will not
  be screen-promoted by this issue.
- `CASING_PRESS` will remain candidate-only unless a reviewed rule proves a
  shut-in datum and the resulting gradient sanity checks pass.
- Multiple Initial Test Data blocks on one page will be parsed separately or
  counted as excluded when interval pairing is ambiguous.
- Page identity mismatches and terminal 403/404/no-data pages will fail closed.
- MIT/Form 21, treatment pressure, and Form 17/bradenhead lanes will remain
  excluded unless a later approved issue changes the interpretation contract.
- The underpressured-screen config will not silently activate Colorado Form 5A
  output without a quality/promotion decision.

## Risks and Controls

| Risk | Control |
|---|---|
| Unbounded public HTML crawl | Configured source list, hard request cap, throttle, resume, no default full-run mode |
| Wrong API key used for FacilityDetail | Derive from raw `API`/`API_County` + `API_Seq`, validate against `API_Label`, preserve full API keys separately, verify rendered page identity |
| False API12 join | Do not synthesize `00` sidetrack; use facility-id/API10 well keys unless a real API12 source exists |
| Flowing pressure treated as shut-in pressure | Keep `TUBING_PRESS` out of screen promotion; require a reviewed `WHP_shut_in` mapping and gradient sanity checks before any static gas-column correction |
| Multiple completion blocks mispaired to one interval | Enumerate Initial Test Data blocks and pair each to nearest interval context, or exclude and count ambiguous pages |
| Parser drift silently emits bad pressure rows | Required marker checks, parser status sidecars, fail-closed drift classification |
| Treatment/MIT/bradenhead pressures contaminate screen | Explicit classification/exclusion tests |
| Large `/mnt/ace` run leaves unverifiable data | Raw manifest JSONL, sha256, status files, summary report, no raw data committed |
| Local interpreter lacks parquet support | Use `/usr/bin/python3` or CI environment for parquet-producing verification |
| Colorado screen participation over-claims source maturity | Candidate output and promotion report separate from `underpressured_screen.yml` activation |

## Adversarial Review Summary

Review artifacts:

- `scripts/review/results/2026-07-04-plan-751-claude.md`
- `scripts/review/results/2026-07-04-plan-751-claude-r2-unavailable.md`
- `scripts/review/results/2026-07-04-plan-751-codex-inline.md`
- `scripts/review/results/2026-07-04-plan-751-gemini-unavailable.md`

Verdicts:

| Reviewer | Verdict | Result |
|---|---|---|
| Claude r1 | MAJOR | Found flowing-pressure promotion and single-table parsing blockers. The plan was patched to add shut-in-only promotion, candidate-only Form 5A output, multi-block parsing, identity checks, User-Agent/403 handling, API12 fail-closed handling, adapter contract, near-vacuum gating, and assertion-level RED tests. |
| Claude r2 | UNAVAILABLE | Two noninteractive reruns timed out with zero-byte output, so no post-patch Claude verdict is claimed. |
| Codex inline | APPROVE | Re-checked the revised plan against the known code risks and found no unresolved MAJOR plan blocker. |
| Gemini | UNAVAILABLE | CLI returned an ineligible-tier error before producing a review. |

The current plan has no unresolved MAJOR finding in the available review
evidence. Implementation remains blocked until the user explicitly approves
[#751](https://github.com/vamseeachanta/worldenergydata/issues/751) and moves
it to `status:plan-approved`.
