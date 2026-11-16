# State regulator module knowledge pack

| Header | Value |
| --- | --- |
| Module | state_regulators |
| Repository | worldenergydata |
| Package path | `src/worldenergydata/modules/state_regulators` |
| Pack revision | 2, 2026-10-22 |
| Code revision | `02d6b17c5757852649b27a3191d1d9e736492ba2` |
| Analysis family | EC — data pipelines; AQG r0 Python calculations gate set |
| Quality manager role | Calculations quality manager |
| Status | DRAFT; second-provider clearance pending |

Summary: historical pinned method evidence plus current corrections for response qualification, shared FacilityDetail collection and identity handling. Section 6 records regression nodes for SF1–SF12; source qualification remains open.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial issue recording the module methods, evidence and limits |
| 1 | 2026-10-16 | Correct arithmetic evidence and issue references; record the silent-failure sweep and detection gaps |
| 2 | 2026-10-22 | Add response, identity and parser safeguards with offline regression evidence and a recorded-fixture example |

## 1. Purpose and scope

Kansas ingestion joins annual pressure records to a wells master and writes normalized and curated pressure tables plus coverage statistics. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L189-L223]

Oklahoma ingestion reads completion workbooks and builds pressure observations and quality statistics; Colorado ingestion reads production CSVs and a wells shapefile, with separate FacilityDetail discovery and Form 5A candidate workflows. [src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:L79-L111] [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L88-L125] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_pipeline.py:L78-L100]

The shared fetch package provides bounded, cache-first collection with recorded source permission; the older Oklahoma and Colorado download functions call `urlopen` directly. [src/worldenergydata/modules/state_regulators/fetch/client.py:L87-L116] [src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:L26-L49] [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L33-L56]

Form 5A candidate construction sets both screen eligibility and promotion to false; it does not establish reservoir-pressure suitability. [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_candidates.py:L118-L151]

Scope includes every Python subpackage beneath the header path; physical pressure correction and cross-state screening are downstream responsibilities rather than operations in the Kansas observation builder. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] [src/worldenergydata/analysis/underpressured_screen/observations.py:L26-L43]

## 2. Inputs and outputs

### Inputs

| Input | Unit / range | Default | Route and evidence |
| --- | --- | --- | --- |
| Kansas proration CSV | Pressure columns converted to numeric; missing values coerced; curated shut-in pressure exceeds configured minimum, psig | Minimum supplied in settings | `read_proration_pressures`, then `build_pressure_observations`; [src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py:L67-L90] [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] |
| Kansas wells CSV or ZIP member | Depth numeric; date format `%d-%b-%Y`; positive depth required only for a gradient | ZIP member `ks_wells.txt` | [src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py:L93-L109] [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] |
| Oklahoma completion workbook | Pressure positive, psig; reference depth positive, ft; valid date within configured year bounds | Minimum year 1900; maximum current UTC year plus configured future allowance | [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L130-L206] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L345-L353] |
| Colorado production CSV | Required API/date/pressure columns; gas pressure positive, psig; report date becomes month end | Source name defaults to input basename | [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L35-L53] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L96-L126] |
| Colorado wells shapefile / ZIP | API join keys, facility ID, depth fields in ft; latitude and longitude copied as numbers | No coordinate transformation in reader | [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L70-L93] |
| FacilityDetail HTML | Initial-test measures plus raw text, dates and depths in ft | Missing context uses nullable values | [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py:L16-L42] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py:L72-L105] |
| Form 5A candidate settings | Positive pressure, depth and nonempty field required; atmospheric offset in psi | Offset 14.7 psi when absent | [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_candidates.py:L44-L78] |
| Fetch configuration | Cache root and single-line User-Agent required; interval, window and timeout finite and positive | Interval 2 s; budget 30 requests / 60 s; timeout 15 s; 2 retries; sleep cap 300 s; response cap 5,242,880 bytes | [src/worldenergydata/modules/state_regulators/fetch/policy.py:L49-L89] |
| Source permission | Explicit Boolean permission, matching HTTP(S) origin; checked time UTC and not future | No permission means no uncached request | [src/worldenergydata/modules/state_regulators/fetch/policy.py:L93-L113] [src/worldenergydata/modules/state_regulators/fetch/client.py:L87-L116] |

### Outputs

| Output | Units / convention | Evidence |
| --- | --- | --- |
| Pressure observations | `pressure_psig_reported` in psig; `pressure_psia` in psia; `reference_depth_ft` in ft; `gradient_psi_ft` in psi/ft | [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L130-L206] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L275-L321] |
| Normalized / curated storage | Parquet tables and JSON coverage or quality records under configured storage directories | [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L189-L223] [src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:L79-L111] [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L88-L125] |
| Form 5A outputs | Source list, parsed Parquet/JSON, candidate Parquet, quality and summary JSON; object columns converted to strings for Parquet | [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_pipeline.py:L114-L144] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_pipeline.py:L175-L179] |
| Raw manifests | Source URL, SHA-256, size in bytes, timestamps and refresh metadata | [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L70-L85] [src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:L52-L76] [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L59-L85] |
| Fetch cache | Content-addressed objects, per-URL records and persisted request progress; digest and byte count verified on read | [src/worldenergydata/modules/state_regulators/fetch/storage.py:L81-L149] |

UNVERIFIED: source coordinate reference system, depth datum and full unit semantics of ancillary production columns are not established by the numeric readers; no spatial or datum-sensitive acceptance is supported without source dictionaries (issue pending (2)). [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L70-L93] [src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py:L93-L109]

## 3. Method and governing standards

| Method | Implementing definition and limits |
| --- | --- |
| Kansas header handling | Skip initial unquoted continuation lines, parse fixed column names, coerce numeric values and nullable year; no malformed-row recovery beyond this rule. [src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py:L67-L90] |
| Kansas join and gradient | Join `WELL_KID` to deduplicated `KID`; absolute pressure equals reported gauge pressure plus supplied atmospheric offset; gradient equals absolute pressure / positive total depth; unmatched wells remain; every observation at the minimum year is flagged earliest. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] |
| Oklahoma selection | Prefer positive shut-in pressure over flowing tubing pressure; first positive depth in configured priority; discard unusable pressure/depth/date/year rows; gradient equals absolute pressure / reference depth; earliest flag uses date then completion number. [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L252-L261] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L264-L277] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L130-L206] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L280-L285] |
| Colorado production | Build API10/API12, join wells by API12 with facility fallback, create positive gas tubing/casing candidates, prefer positive TVD then MD, filter years and deduplicate observation identities. [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L56-L67] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L238-L272] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L96-L126] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L324-L331] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L129-L161] |
| Colorado pressure roles | Water pressures contribute quality counts but not gas-screen rows; initial-test casing/tubing measures are candidates; treatment and integrity measures are excluded classes. [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L164-L210] [src/worldenergydata/modules/state_regulators/colorado_ecmc/schema.py:L92-L100] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py:L45-L69] |
| Form 5A candidate depth | Prefer interval bottom, then vertical total depth, then maximum TVD, then maximum MD; this ordering is separate from the production pathway. [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_candidates.py:L11-L17] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_candidates.py:L160-L165] |
| Fetch pacing | Take maximum applicable fallback/server delay; reserve every attempt in a persisted rolling host budget; only HTTP 429 is retried; redirects are refused; cooldown beyond the sleep cap raises `BudgetExceeded` without shortening the persisted wait. `RateLimit-Reset` is interpreted as delta seconds; an epoch value can persist a decades-long wait in `progress.json`, raising `BudgetExceeded` on later attempts until the retained state is explicitly corrected (F3; issue pending (7)). [src/worldenergydata/modules/state_regulators/fetch/policy.py:L128-L175] [src/worldenergydata/modules/state_regulators/fetch/client.py:L54-L75] [src/worldenergydata/modules/state_regulators/fetch/client.py:L87-L116] [src/worldenergydata/modules/state_regulators/fetch/client.py:L25-L29] |
| Fetch integrity | Single-writer cache; JSON and objects use pending files, fsync and replacement; URL, digest and size are checked before cached bytes are returned. [src/worldenergydata/modules/state_regulators/fetch/storage.py:L20-L28] [src/worldenergydata/modules/state_regulators/fetch/storage.py:L81-L149] |

The pressure builders implement arithmetic and selection rules rather than a named standards calculation; their atmospheric offsets are caller settings, so this pack does not attribute those values to a licensed standard. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L130-L206] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L275-L321]

No new physical constant or physical acceptance limit is introduced. Response status and media semantics follow RFC 9110 (2022), sections 8.3 and 15.3.1; Retry-After follows section 10.2.3. Pacing and budgets remain caller inputs with defaults inherited from `fetch/policy.py::FetchConfig`, rather than claims about source capacity.

## 4. Validated worked examples

Validated examples: 0; independent source qualification remains open as issue pending (2).

The following four cases are regression examples, not independent source validation; input fixtures and expected assertions are pinned with the cited tests.

| Case | Source / input | Expected result and tolerance | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 Kansas header continuation | Inline proration fixture; no identifying record text reproduced | Exactly 6 rows; tolerance 0 rows | `tests/unit/state_regulators/test_kansas_kgs.py::TestParsers::test_mangled_header_continuation_skipped` | PASS at BASE and AFTER; [tests/unit/state_regulators/test_kansas_kgs.py:L55-L70] |
| R2 Oklahoma pressure fallback | Inline completion DataFrame and test settings | Flowing pressure 80 psig; exact equality, tolerance 0 psi | `tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py::test_build_pressure_observations_uses_flowing_pressure_when_shut_in_missing` | PASS at BASE and AFTER; [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L130-L156] |
| R3 Colorado water exclusion | Two positive water measures, no gas pressure | 2 water candidates, 0 curated rows; tolerance 0 rows | `tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py::test_water_pressure_columns_are_counted_but_excluded_from_curated_screen_rows` | PASS at BASE and AFTER; [tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py:L57-L81] |
| R4 Retry-After delay | Parameterized synthetic headers | 7 s for Retry-After 7; exact equality, tolerance 0 s | `tests/unit/state_regulators/test_polite_fetch.py::test_header_delay[headers2-7]` | PASS at BASE and AFTER; [tests/unit/state_regulators/test_polite_fetch.py:L105-L117] |

Execution record: at the unchanged code pin, the focused comparison at BASE passed 123 tests, with 0 failed, 0 skipped and 0 NOT_RUN; AFTER also passed 123 tests, with 0 failed, 0 skipped and 0 NOT_RUN; both commands exited 0. From the checkout root, the command is `uv run --no-project --with pytest --with pytest-cov --with pytest-asyncio --with 'pandas>=2.3.3,<3' --with 'numpy>=2.2.6,<3' --with pyyaml --with beautifulsoup4 --with openpyxl --with pyshp --with 'pyarrow>=14,<20' python -m pytest --noconftest tests/unit/modules/state_regulators tests/unit/state_regulators -q -rA -p no:cacheprovider --basetemp=<scratch>` with `PYTHONPATH=src:packages/worldenergydata-core/src`; coverage data and all three configured coverage reports are redirected to scratch. An initial invocation from scratch passed 120 and failed 3 configuration reads because they require the checkout working directory; it was corrected before editing. No solver or regulator collection was performed.

Revision 2 execution: the full offline state-regulator suites passed 175 tests, including 45 added regression cases, with no failures or skips. Black and isort checks passed; Ruff reported only unchanged findings verified against the base revision. These checks ran on the uncommitted tree.

### Recorded-fixture response and identity example (revision 2)

This collection regression is not independent qualification of a pressure measurement. Input bytes are the recorded `tests/fixtures/colorado_ecmc/facility_detail_12339345_excerpt.html`; the opening table states API fragment `12339345` and facility `436953`. The test supplies request rows directly to exercise response validation independently of source-list validation. A local stub supplies those same bytes for each distinct URL; a fake clock applies shared pacing. No regulator is contacted.

| Requested API fragment | Requested facility | Rendered API fragment / facility | Default output | Explicit retention output |
| --- | --- | --- | --- | --- |
| 12339345 | 436953 | 12339345 / 436953 | fetched, matched | fetched, matched |
| 12300001 | 436953 | 12339345 / 436953 | failed, identity_mismatch | fetched, identity_mismatch |
| 12339345 | 999999 | 12339345 / 436953 | failed, identity_mismatch | fetched, identity_mismatch |

Method: qualify response status, media and size; obtain visible HTML text before comparing identifiers; reject unmatched identity unless `keep_identity_mismatch: true`; parse only retained pages and propagate identity flags into candidates. Default output is one fetched page, two rejected rows and seven parsed measures. The seven rows can be counted directly in the fixture: BBLS_H2O, BBLS_OIL, BTU_GAS, CALC_MCF_GAS, CASING_PRESS, MCF_GAS and TUBING_PRESS. Explicit retention yields three pages and six pressure candidates (three pages times two pressure measures), four flagged (two mismatches times two measures). All remain ineligible for screening. There are two distinct URLs, so the retained-cache rerun adds no requests. The synthetic zero atmospheric offset in this identity test is an input for the hand identity `p + 0 = p`, not a claimed physical correction.

Reproduce with `python -m pytest --noconftest tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_recorded_fixture_identity_run -q -p no:cacheprovider -o addopts='' --basetemp=<scratch>` with the module dependencies installed and `PYTHONPATH=src`.

Collection configuration now requires recorded `facility_detail.terms_checks` entries, each containing `origin`, `terms_url`, UTC `checked_at` and Boolean `bulk_allowed`. No recorded permission is assumed by the shipped sample configuration. `facility_detail.fetch` accepts shared budget/window/size/sleep options; `request_delay_seconds`, `timeout_seconds` and `max_retries` map to the corresponding shared settings. An omitted delay inherits the positive shared default from `fetch/policy.py::FetchConfig`; an explicit zero delay is invalid. The older `stop_on_identity_mismatch` setting does not authorize retention; only `keep_identity_mismatch: true` does.

Remaining limits: error-page recognition is conservative, not general semantic validation of arbitrary content. API12 and wellbore-selection mapping remain NOT_EVALUATED without a qualified source mapping; wellbore labels and original source API values are retained. Missing duplicate-count provenance is null with a NOT_EVALUATED warning. Strict decoding and invalid-date errors require source correction rather than silently substituting text. Live permission and reachability remain outside this offline example.

Source: [RFC 9110, HTTP Semantics (2022)](https://www.rfc-editor.org/rfc/rfc9110.html), sections 8.3, 10.2.3 and 15.3.1. Discrete identity and row-count expectations above come from the recorded fixture and the written hand counts, not the implementation under test. Regression node: `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_recorded_fixture_identity_run`.

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations, with G5 applying to every family.

| Gate | Applicability | Module-specific check, numeric pass criterion and evidence |
| --- | --- | --- |
| G0 | Applicable: inputs, units and citations | C0a: R1 `read_proration_pressures` returns 6 rows, deviation 0 rows; C0b: `read_production_csv` raises exactly 1 `ValueError` for missing required columns, 0 returned frames. [tests/unit/state_regulators/test_kansas_kgs.py:L68-L70] [tests/unit/modules/state_regulators/test_colorado_ecmc_parsers.py:L104-L109] |
| G1 | Applicable: Python imports and tests; no external program writer | C1: run both state-regulator test directories with pytest, 0 failed tests and 0 collection errors; import route is the Python package under the header path. Test imports exercise parsers, pipelines and fetch exports. [tests/unit/state_regulators/test_kansas_kgs.py:L14-L22] [tests/unit/state_regulators/test_polite_fetch.py:L11-L21] |
| G2 | Applicable: hand arithmetic, independent source qualification still open | C2: using the coercion test supplied pressure 125 psig and offset 14.7 psi, hand addition gives 139.7 psia; the builder must satisfy the cited `pytest.approx(139.7)` assertion (relative tolerance 1e-6; absolute floor 1e-12 psi). This is an arithmetic check, not a validation of pressure origin or reservoir suitability. [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L88-L128] [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L13-L13] |
| G3 | NOT_APPLICABLE: no dynamic simulation in the covered pressure-observation and fetch methods | No time-domain solver result is produced by these methods. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] [src/worldenergydata/modules/state_regulators/fetch/client.py:L152-L157] |
| G4 | NOT_APPLICABLE: no diffraction model or mesh output in the covered pipelines | Outputs are tables and JSON rather than hydrodynamic meshes. [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L88-L125] |
| G5 | Applicable: retain traceable evidence before use | C5a: `write_manifest` readback equals returned metadata, 0 differing fields and size equal to fixture bytes; C5b: Form 5A summary `usable_candidate_rows` equals 2 rows and promotion is `candidate_only`, 0 promoted rows. Evidence: JSON readback and Parquet existence in temporary test storage. [tests/unit/modules/state_regulators/test_colorado_ecmc_pipeline.py:L82-L124] [tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_pipeline.py:L72-L126] [tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py:L328-L344] |

These six checks define evidence for review; no independent quality-manager signature or source qualification is claimed.

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection | Incident or follow-up |
| --- | --- | --- |
| Positive production pressure absent despite available columns; an empty curated table is not pressure evidence | R3 plus `test_quality_warns_when_configured_sources_have_no_positive_pressure_values`: 0 curated rows and exactly 1 source warning | #745; [tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py:L84-L106] |
| Initial-test, treatment and integrity values can be conflated | Classifier test requires 0 eligible rows and distinct excluded roles; Form 5A remains candidate-only | #749, #751; [tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py:L108-L156] |
| Wrapped header creates a false data row | C0a / R1; exactly 6 parsed rows | #725; [tests/unit/state_regulators/test_kansas_kgs.py:L68-L70] |
| Missing shut-in pressure invokes flowing pressure fallback, changing observation kind | Existing fallback test requires 80 psig and `WHP_flowing_tubing` | #740; [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L130-L156] |
| Throttling, interrupted collection or damaged cache can invalidate collection evidence | Fetch tests require 2 requests for a retry/cache case, no additional request on cache hit, and an integrity error on tampered payload | #1130; [tests/unit/state_regulators/test_polite_fetch.py:L126-L142] [tests/unit/state_regulators/test_polite_fetch.py:L240-L247] |
| Oklahoma quality counts can disagree with observation filtering for non-default depth priorities: the builder reads `settings["depth_priority"]`, but the statistics function uses a fixed list | No detection check exists for a custom depth-only source; proposed check: one retained observation has 0 rows counted as missing depth | issue pending (5), related to #740; [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L130-L206] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L209-L249] |
| FacilityDetail fetch is described as resumable but does not consult retained status or implement a retry loop; `retry_count` is fixed to 0 | `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_shared_default_delay_budget_and_cache` and `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_shared_retry_records_attempts`: cache suppresses repeat requests; retries are recorded | issue pending (1); [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L79-L105] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L108-L132] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L139-L152] |
| SF1: any successful response, including zero bytes or an HTML error page instead of CSV/ZIP, is cached and reused; integrity checks accept size 0 and do not qualify content | `tests/unit/state_regulators/test_response_validation.py::test_invalid_response_never_mutates_cache`; `tests/unit/state_regulators/test_response_validation.py::test_poisoned_cache_refetched_through_permission_layer` | #1301; [src/worldenergydata/modules/state_regulators/fetch/storage.py:L46-L52] [src/worldenergydata/modules/state_regulators/fetch/storage.py:L121-L149] [src/worldenergydata/modules/state_regulators/fetch/client.py:L92-L94] [src/worldenergydata/modules/state_regulators/fetch/client.py:L113-L115] |
| SF2: FacilityDetail collection defaults to 0 s between requests and uses direct fetching without shared permission, budget or 429 handling | `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_shared_permission_blocks_collection`; `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_shared_default_delay_budget_and_cache`; `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_shared_retry_records_attempts` | #1301; [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L104-L112] |
| SF3: rendered identity mismatches remain in `fetched` unless exclusion is explicitly enabled; missing rendered API text never counts as a mismatch | `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_default_identity_policy`; `tests/unit/modules/state_regulators/test_facility_fetch_controls.py::test_recorded_fixture_identity_run` | #1301; [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L96-L102] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L155-L168] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L223-L228] |
| SF4: parser API12 appends `00`, parsed wellbore is unused, source lists keep the first API fragment and discovery drops sidetrack digits; distinct wellbores can merge | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf4_unknown_sidetrack_is_not_invented`; `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf4_ambiguous_source_rows_are_rejected`; `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf4_distinct_wellbore_contexts_preserved`; `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf4_discovery_does_not_discard_sidetrack` ; wellbore labels retained; API12 mapping NOT_EVALUATED | #1301; [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py:L77-L89] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L63-L69] [src/worldenergydata/modules/state_regulators/colorado_ecmc/source_discovery.py:L36-L39] |
| SF5: missing field names are filled with formation codes, mixing two identities in field-level grouping without a flag | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf5_formation_does_not_become_field` | #1301; [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L297-L297] |
| SF6: dropped-duplicate counts live in `DataFrame.attrs`; a caller that loses those attributes through concatenation or storage reports the default 0; the direct pipeline preserves them | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf6_missing_duplicate_evidence_is_not_zero` ; absent count is null with NOT_EVALUATED warning | #1301; [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L158-L160] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L200-L202] |
| SF7: no workbook header or all filtered Oklahoma rows leads to empty curated storage and a null year range without a warning; the Colorado warning regression above does not cover Oklahoma | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf7_empty_workbook_warns` | #1301; [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L110-L113] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L336-L338] [src/worldenergydata/modules/state_regulators/oklahoma_occ/pipeline.py:L93-L110] |
| SF8: a configured production source with a type other than `production_csv` is downloaded and manifested but silently skipped during parsing | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf8_unknown_source_type_rejected_before_download` | #1301; [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L130-L132] |
| SF9: Kansas decoding replaces invalid bytes; FacilityDetail ingest and parsing ignore invalid bytes, potentially changing identifiers or field names without counts | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf9_kansas_decode_is_strict`; `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf9_facility_decode_is_strict` | #1301; [src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py:L74-L74] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_pipeline.py:L59-L59] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L118-L118] |
| SF10: Kansas dates outside `%d-%b-%Y`, including unrecognized month tokens, become NaT without counts | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf10_bad_date_is_reported` | #1301; [src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py:L105-L108] |
| SF11: county-code extraction assumes a dashed Kansas API string; undashed text yields incorrect digits without validation | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf11_county_handles_both_api_formats`; `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf11_malformed_county_rejected` | #1301; [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L120-L120] |
| SF12: unparseable API parts become missing join keys; pandas matches null keys, so a pressure row can inherit field/depth from an unrelated wells row and retain a null `well_key`, excluded from earliest grouping | `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf12_missing_api_never_inherits_null_key_well`; `tests/unit/modules/state_regulators/test_silent_failure_regressions.py::test_sf12_invalid_api_parts_rejected` | #1301; [src/worldenergydata/modules/state_regulators/colorado_ecmc/normalization.py:L15-L26] [src/worldenergydata/modules/state_regulators/colorado_ecmc/normalization.py:L47-L52] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L59-L66] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L241-L249] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L333-L342] |
| F2: first-number extraction reads `1.2E+3` as 1.2, `<5` as 5 and `1,2345` as 1234; `measure_raw` retains the auditable text | no detection check exists for these numeric syntaxes; proposed check: reject or explicitly interpret all three forms before use | issue pending (7); [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py:L37-L37] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py:L223-L230] |
| F3: epoch-valued reset headers are treated as delta seconds and can persist a decades-long cooldown; this raises an error rather than silently truncating the wait | no detection check exists for epoch-valued resets; proposed check: explicit unit handling and safe retained-state recovery | issue pending (7); [src/worldenergydata/modules/state_regulators/fetch/policy.py:L134-L148] [src/worldenergydata/modules/state_regulators/fetch/client.py:L54-L62] [src/worldenergydata/modules/state_regulators/fetch/client.py:L77-L85] |

### Sweep record

sweep: 12 found (previously unrecorded silent-failure groups SF1–SF12 at the code pin; all have rows above and share issue pending (6)). The grep returned 396 matching lines across the 21 package Python files. The seven existing incident rows remain; F2 records a separate numeric-interpretation pitfall and F3 a loud cooldown failure, both under issue pending (7). This sweep describes behavior at the historical code pin. Revision 2 detection cells describe the current corrections and remaining NOT_EVALUATED cases; historical method citations still resolve at the header pin.

The exact command, run from the checkout root against the header code revision, is:

```sh
git grep -n -E 'except|continue|return None|return *$|\[\]|\{\}|\b0(\.0)?\b|1970|1900|percent|\bint\(|\bfloat\(|to_numeric|to_datetime|errors=|timeout|delay|offset|head\(|write_text|write_bytes|to_parquet|to_json|\.get\(' 02d6b17c5757852649b27a3191d1d9e736492ba2 -- ':(glob)src/worldenergydata/modules/state_regulators/**/*.py'
```

The matching lines and their enclosing definitions were inspected for the following classes; a hit is not automatically a silent failure.

| Sweep class | Classification and section-6 coverage |
| --- | --- |
| Swallowed exceptions and malformed headers | Cache/network exceptions raise typed or integrity errors. Bad Content-Length falls back to 0 but the read cap still bounds bytes. Malformed delay headers preserve other valid waits. Oklahoma missing headers and bad API-part conversion route to SF7 and SF12. |
| Skipped records and empty results | Unknown production types route to SF8. Candidate skips increment quality exclusions; empty Initial Test pages increment `no_initial_test_pages`. Colorado absent positive pressure is warned by the existing incident row; Oklahoma empty output routes to SF7. Header-row skipping is structural parsing. |
| None returns and empty containers | Identifier cleaners encode blanks as missing values; their null-key join risk routes to SF12. Cache misses and redirect refusal are explicit contracts. Candidate missing pressure/depth returns are counted exclusions. Initial empty lists/dicts and zero counters are accumulators, not error fallback results. |
| Numeric defaults, dates and unit assumptions | Zero delay and duplicate-counter fallback route to SF2 and SF6. Minimum year 1900, zero future-year allowance, atmospheric offsets and ft/psig conventions are configured method limits; source datum and ancillary units remain UNVERIFIED under issue pending (2). No 1970 or percentage default was found. |
| External text conversion and coercion | Content-Length retains a byte cap; first-number parsing routes to F2. Invalid Kansas dates route to SF10; numeric pressure/depth filters are described in sections 2–3 and quality records, with the Oklahoma priority mismatch already recorded above. Decoding routes to SF9; identity assumptions route to SF3, SF4, SF11 and SF12. |
| Cache writes and persistence | Empty or error-page payloads route to SF1; empty Oklahoma curated output routes to SF7. Request-state defaults are initialized counters; reset units and persisted excessive waits route to F3. |

Inspection date for the limitations above: 2026-10-16; historical issue evidence is not a fresh regulator-data measurement.

## 7. Lessons log

| Date | Record | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-16 | Initial pack | Candidate availability does not establish screen eligibility | [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_candidates.py:L118-L151] | Explicit boundary in sections 1, 3, 5 and 6 | issue pending (4) |

## 8. Ownership

Review assignment: calculations quality manager; deputy: data-pipeline quality-manager role when appointed. Production responsibility: module maintainers. Classification disagreements will go to the family quality manager; cross-family scope decisions will go to the maintainers. These are review assignments for this draft, not claims that a review occurred.

## 9. Dependencies and implementation inventory

The parser and pipeline imports establish pandas, NumPy, PyYAML, openpyxl, pyshp and BeautifulSoup dependencies; the fetch layer uses Python standard-library HTTP, JSON, filesystem and hashing services. [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L5-L9] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L5-L11] [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L5-L13] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail.py:L5-L8] [src/worldenergydata/modules/state_regulators/fetch/client.py:L3-L10] [src/worldenergydata/modules/state_regulators/fetch/storage.py:L3-L11]

The downstream observation normalizer dispatches Kansas, Oklahoma and Colorado production schemas; this does not itself promote Form 5A candidates. [src/worldenergydata/analysis/underpressured_screen/observations.py:L26-L43] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_candidates.py:L118-L151]

Implementation-map evidence record: `digitalmodel` map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, map data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `docs/registry/implementation-map.yaml`. The parsed map has 13 families and 0 implementation rows under this pack's package path. Inventory: empty; counted families: 0; A8 signal grep: NOT_APPLICABLE because no map family has an in-package row. No absence-of-duplicate conclusion follows from that result.

Map follow-up, issue pending (3): add pressure-observation joins and gauge-to-absolute/depth-gradient calculations; HTML initial-test extraction and pressure-role classification; source-list identity normalization; bounded permission-aware fetch, pacing and cache integrity. These are section-3 methods missing from the supplied map, so they do not alter A8 until in-package rows exist.

Additional repository-wide search, including `packages/` and `scripts/`, finds independent pressure calculations outside this package: Kansas `_observation` computes absolute pressure and a depth gradient, while Texas `_classify_pressure` and `_gradient` compute their own pressure conversion and gradient. These are method-map follow-up candidates, not counted A8 misses. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L89-L132] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/observations.py:L134-L158] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/pressure_observations/observations.py:L275-L279]

The Kansas and Texas CLI commands delegate to packet-building functions; they are wrappers rather than additional pressure formulas. Their entrypoints are distinct from this package's state pipelines. [src/worldenergydata/cli/commands/kansas_kgs.py:L28-L69] [src/worldenergydata/cli/commands/texas_rrc.py:L655-L689]

The search also finds downstream normalization and an atlas renderer, without establishing source freshness or equivalence of the separate implementations. [src/worldenergydata/analysis/underpressured_screen/observations.py:L26-L43] [scripts/pressure_atlas/build_pressure_atlas.py:L1-L25]

## 10. Coverage and open items

Evidence inventory: all 21 package Python files and 13 test/support Python files across `tests/unit/modules/state_regulators` and `tests/unit/state_regulators` were inspected at the header pin. Source inventories are enumerated below; execution results belong to section 4.

- Package: root `__init__.py`; `kansas_kgs/` (`__init__.py`, `parsers.py`, `pipeline.py`); `oklahoma_occ/` (same three); `colorado_ecmc/` (`__init__.py`, `schema.py`, `normalization.py`, `parsers.py`, `pipeline.py`, `facility_detail.py`, `facility_detail_candidates.py`, `facility_detail_ingest.py`, `facility_detail_pipeline.py`, `source_discovery.py`); `fetch/` (`__init__.py`, `policy.py`, `client.py`, `storage.py`).
- Tests: nine `test_colorado_ecmc_*` / `test_oklahoma_occ_*` files under `tests/unit/modules/state_regulators`; `test_kansas_kgs.py`, `test_polite_fetch.py`, `fetch_cases.py` and empty `__init__.py` under `tests/unit/state_regulators`.
- Documentation discovered by module-name search: `docs/data-sources/onshore/state-well-databases/source-catalog.md`, `docs/data-sources/onshore/state-well-databases/kansas-kgs-ingest.md`, `docs/data-sources/state-regulator-fetch.html`, `docs/modules/repository-architecture.md`, and five plans for issues 725, 740, 745, 749 and 751 under `docs/plans/`; coverage is limited to module-related sections, and full historical-document review is deferred under issue pending (2); numerical acquisition claims are not adopted as current measurements.

| Item | Disposition / responsible role | Tracking |
| --- | --- | --- |
| FacilityDetail resume/retry gap | Shared verified cache now suppresses repeated requests, and shared retries record successful retry counts; append-only status files remain an audit trail rather than the resume authority | #1301 |
| UNVERIFIED source CRS, depth datum and ancillary units; independent validation absent | Maintainers will qualify source dictionaries and a codenamed benchmark before source-sensitive acceptance; G2 arithmetic alone does not establish it | issue pending (2) |
| Method-map coverage | Maintainers will register the section-3 families with in-package implementations and search signals | issue pending (3) |
| Historical docs and full documentation reconciliation | Maintainers will reconcile acquisition claims against retained manifests; documentation discovery does not establish present data freshness | issue pending (2) |
| Pack and shared-lesson indexing | Maintainers will add the pack and candidate-only lesson to the durable shared index | issue pending (4) |
| Oklahoma depth-priority quality counters | Maintainers will align quality accounting with configured observation depth selection and add a non-default-priority regression | issue pending (5) |
| SF1–SF12 detection gaps | Section 6 names current regression nodes; API12 mapping and unavailable duplicate-count provenance remain explicitly NOT_EVALUATED rather than inferred | #1301 |
| Numeric-token interpretation and reset-header units | Maintainers will qualify first-number parsing, define reset-header units and test explicit cooldown recovery | issue pending (7) |
| Source terms and current reachability | Actual permissions and live collection are outside the offline evidence; retain explicit per-origin checks before any uncached request | #1130; [src/worldenergydata/modules/state_regulators/fetch/client.py:L87-L116] |

The calculations citation contract was readable during preparation; no licensed standard was read or reproduced. Routing-registry update is NOT_APPLICABLE: `docs/registry/module-routing.yaml` is absent at the header pin. Issue-pending markers require issue numbers before final quality-manager clearance.
