# State regulator module knowledge pack

| Header | Value |
| --- | --- |
| Module | state_regulators |
| Repository | worldenergydata |
| Package path | `src/worldenergydata/modules/state_regulators` |
| Pack revision | 0, 2026-10-16 |
| Code revision | `02d6b17c5757852649b27a3191d1d9e736492ba2` |
| Analysis family | EC — data pipelines; AQG r0 Python calculations gate set |
| Quality manager role | Calculations quality manager |
| Status | DRAFT; second-provider clearance pending |

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
| Fetch pacing | Take maximum applicable fallback/server delay; reserve every attempt in a persisted rolling host budget; only HTTP 429 is retried; redirects are refused; cooldown beyond the sleep cap raises `BudgetExceeded` without shortening the persisted wait. [src/worldenergydata/modules/state_regulators/fetch/policy.py:L128-L175] [src/worldenergydata/modules/state_regulators/fetch/client.py:L54-L75] [src/worldenergydata/modules/state_regulators/fetch/client.py:L87-L116] [src/worldenergydata/modules/state_regulators/fetch/client.py:L25-L29] |
| Fetch integrity | Single-writer cache; JSON and objects use pending files, fsync and replacement; URL, digest and size are checked before cached bytes are returned. [src/worldenergydata/modules/state_regulators/fetch/storage.py:L20-L28] [src/worldenergydata/modules/state_regulators/fetch/storage.py:L81-L149] |

The pressure builders implement arithmetic and selection rules rather than a named standards calculation; their atmospheric offsets are caller settings, so this pack does not attribute those values to a licensed standard. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L130-L206] [src/worldenergydata/modules/state_regulators/colorado_ecmc/parsers.py:L275-L321]

No standards-derived constant or Citation sidecar is introduced by this documentation change.

## 4. Validated worked examples

Validated examples: 0; independent source qualification remains open as issue pending (2).

The following four cases are regression examples, not independent source validation; input fixtures and expected assertions are pinned with the cited tests.

| Case | Source / input | Expected result and tolerance | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 Kansas header continuation | Inline proration fixture; no identifying record text reproduced | Exactly 6 rows; tolerance 0 rows | `tests/unit/state_regulators/test_kansas_kgs.py::TestParsers::test_mangled_header_continuation_skipped` | PASS at BASE and AFTER; [tests/unit/state_regulators/test_kansas_kgs.py:L55-L70] |
| R2 Oklahoma pressure fallback | Inline completion DataFrame and test settings | Flowing pressure 80 psig; exact equality, tolerance 0 psi | `tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py::test_build_pressure_observations_uses_flowing_pressure_when_shut_in_missing` | PASS at BASE and AFTER; [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L130-L156] |
| R3 Colorado water exclusion | Two positive water measures, no gas pressure | 2 water candidates, 0 curated rows; tolerance 0 rows | `tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py::test_water_pressure_columns_are_counted_but_excluded_from_curated_screen_rows` | PASS at BASE and AFTER; [tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py:L57-L81] |
| R4 Retry-After delay | Parameterized synthetic headers | 7 s for Retry-After 7; exact equality, tolerance 0 s | `tests/unit/state_regulators/test_polite_fetch.py::test_header_delay[headers2-7]` | PASS at BASE and AFTER; [tests/unit/state_regulators/test_polite_fetch.py:L105-L117] |

Execution record: comparison BASE reported 123 passed tests, with 0 failed, 0 skipped and 0 NOT_RUN on the header revision; AFTER also passed 123 tests, with 0 failed, 0 skipped and 0 NOT_RUN; its command exited 0. The command is `uv run python -m pytest --noconftest tests/unit/modules/state_regulators tests/unit/state_regulators -q -rA -p no:cacheprovider --basetemp=<scratch>`, with the repository-documented `PYTHONPATH=src:../assetutilities/src` and unchanged addopts. An additional ordinary run without `--noconftest` also passed 123 tests. The ordinary run exited 0; the comparison BASE exit code was not retained, but its complete node-level PASS summary was read back. No solver or regulator collection was performed.

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations, with G5 applying to every family.

| Gate | Applicability | Module-specific check, numeric pass criterion and evidence |
| --- | --- | --- |
| G0 | Applicable: inputs, units and citations | C0a: R1 `read_proration_pressures` returns 6 rows, deviation 0 rows; C0b: `read_production_csv` raises exactly 1 `ValueError` for missing required columns, 0 returned frames. [tests/unit/state_regulators/test_kansas_kgs.py:L68-L70] [tests/unit/modules/state_regulators/test_colorado_ecmc_parsers.py:L104-L109] |
| G1 | Applicable: Python imports and tests; no external program writer | C1: run both state-regulator test directories with pytest, 0 failed tests and 0 collection errors; import route is the Python package under the header path. Test imports exercise parsers, pipelines and fetch exports. [tests/unit/state_regulators/test_kansas_kgs.py:L14-L22] [tests/unit/state_regulators/test_polite_fetch.py:L11-L21] |
| G2 | Applicable: hand arithmetic, independent source qualification still open | C2: using the coercion test supplied pressure 125 psig and offset 14.7 psi, hand addition gives 139.7 psia; builder absolute error at most 1e-9 psi. This is an arithmetic check, not a validation of pressure origin or reservoir suitability. [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L15-L24] [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L130-L156] |
| G3 | NOT_APPLICABLE: no dynamic simulation in the covered pressure-observation and fetch methods | No time-domain solver result is produced by these methods. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151] [src/worldenergydata/modules/state_regulators/fetch/client.py:L152-L157] |
| G4 | NOT_APPLICABLE: no diffraction model or mesh output in the covered pipelines | Outputs are tables and JSON rather than hydrodynamic meshes. [src/worldenergydata/modules/state_regulators/colorado_ecmc/pipeline.py:L88-L125] |
| G5 | Applicable: retain traceable evidence before use | C5a: `write_manifest` readback equals returned metadata, 0 differing fields and size equal to fixture bytes; C5b: Form 5A summary `usable_candidate_rows` equals 2 rows and promotion is `candidate_only`, 0 promoted rows. Evidence: JSON readback and Parquet existence in temporary test storage. [tests/unit/modules/state_regulators/test_colorado_ecmc_pipeline.py:L82-L124] [tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_pipeline.py:L72-L126] [tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail_ingest.py:L328-L344] |

These six checks define evidence for review; no independent quality-manager signature or source qualification is claimed.

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection | Incident or follow-up |
| --- | --- | --- |
| Positive production pressure absent despite available columns; an empty curated table is not pressure evidence | R3 plus `test_quality_warns_when_configured_sources_have_no_positive_pressure_values`: 0 curated rows and exactly 1 source warning | [Issue 745](https://github.com/vamseeachanta/worldenergydata/issues/745); [tests/unit/modules/state_regulators/test_colorado_ecmc_observations.py:L84-L106] |
| Initial-test, treatment and integrity values can be conflated | Classifier test requires 0 eligible rows and distinct excluded roles; Form 5A remains candidate-only | [Issue 749](https://github.com/vamseeachanta/worldenergydata/issues/749), [issue 751](https://github.com/vamseeachanta/worldenergydata/issues/751); [tests/unit/modules/state_regulators/test_colorado_ecmc_facility_detail.py:L108-L156] |
| Wrapped header creates a false data row | C0a / R1; exactly 6 parsed rows | [Issue 725](https://github.com/vamseeachanta/worldenergydata/issues/725); [tests/unit/state_regulators/test_kansas_kgs.py:L68-L70] |
| Missing shut-in pressure invokes flowing pressure fallback, changing observation kind | Existing fallback test requires 80 psig and `WHP_flowing_tubing` | [Issue 740](https://github.com/vamseeachanta/worldenergydata/issues/740); [tests/unit/modules/state_regulators/test_oklahoma_occ_parsers.py:L130-L156] |
| Throttling, interrupted collection or damaged cache can invalidate collection evidence | Fetch tests require 2 requests for a retry/cache case, no additional request on cache hit, and an integrity error on tampered payload | [Issue 1130](https://github.com/vamseeachanta/worldenergydata/issues/1130); [tests/unit/state_regulators/test_polite_fetch.py:L126-L142] [tests/unit/state_regulators/test_polite_fetch.py:L240-L247] |
| Oklahoma quality counts can disagree with observation filtering for non-default depth priorities: the builder reads `settings["depth_priority"]`, but the statistics function uses a fixed list | No detection check exists for a custom depth-only source; proposed check: one retained observation has 0 rows counted as missing depth | issue pending (5), related to [issue 740](https://github.com/vamseeachanta/worldenergydata/issues/740); [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L130-L206] [src/worldenergydata/modules/state_regulators/oklahoma_occ/parsers.py:L209-L249] |
| FacilityDetail fetch is described as resumable but does not consult retained status or implement a retry loop; `retry_count` is fixed to 0 | No detection check exists for second-run request suppression or transient retry success; proposed check: identical second run makes 0 requests and a transient 429 succeeds within the configured retry count | issue pending (1); [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L79-L105] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L108-L132] [src/worldenergydata/modules/state_regulators/colorado_ecmc/facility_detail_ingest.py:L139-L152] |

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
| FacilityDetail resume/retry gap | Maintainers will add a retained-status read path and retry tests or narrow the documented contract; no module code changed here | issue pending (1) |
| UNVERIFIED source CRS, depth datum and ancillary units; independent validation absent | Maintainers will qualify source dictionaries and a codenamed benchmark before source-sensitive acceptance; G2 arithmetic alone does not establish it | issue pending (2) |
| Method-map coverage | Maintainers will register the section-3 families with in-package implementations and search signals | issue pending (3) |
| Historical docs and full documentation reconciliation | Maintainers will reconcile acquisition claims against retained manifests; documentation discovery does not establish present data freshness | issue pending (2) |
| Pack and shared-lesson indexing | Maintainers will add the pack and candidate-only lesson to the durable shared index | issue pending (4) |
| Oklahoma depth-priority quality counters | Maintainers will align quality accounting with configured observation depth selection and add a non-default-priority regression | issue pending (5) |
| Source terms and current reachability | Actual permissions and live collection are outside the offline evidence; retain explicit per-origin checks before any uncached request | [Issue 1130](https://github.com/vamseeachanta/worldenergydata/issues/1130); [src/worldenergydata/modules/state_regulators/fetch/client.py:L87-L116] |

The calculations citation contract was readable during preparation; no licensed standard was read or reproduced. Routing-registry update is NOT_APPLICABLE: `docs/registry/module-routing.yaml` is absent at the header pin. Issue-pending markers require issue numbers before final quality-manager clearance.
