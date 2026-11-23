# BSEE module knowledge pack

| Header | Value |
| --- | --- |
| Module | `bsee` |
| Repository | `worldenergydata` |
| Path | `packages/worldenergydata-bsee/src/worldenergydata/bsee` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `55991b0def0f90708b3e0c396c0f57d9d1b7f7fb` |
| Analysis family | EC (engineering calculations); data pipeline; AQG r0 section 10, Python calculations |
| QM role | EC quality manager; deputy: data-pipeline quality manager when appointed |
| Status | DRAFT |

## 1. Purpose and scope

The main engine route copies the data and analysis configuration into the result namespace, loads data, then dispatches analysis; the well-benchmark route delegates to the adjacent package instead. [packages/worldenergydata-bsee/src/worldenergydata/bsee/bsee.py:L14-L42]

`BSEEData.router` refreshes first, defaults block, well and lease loading to enabled, and returns `well_data` and `production_data` alongside the configuration. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/bsee_data.py:L17-L37]

This revision documents ingestion, identifier matching, production adapters and lease-layout validation; detailed clearance of reporting, economics, forecasting, paleowells and visualization remains open under issue pending (1). [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/bsee_data.py:L17-L37] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/bsee_analysis.py:L43-L89]

The distribution declares alpha maturity; this is packaging metadata rather than evidence of analytical validation. [packages/worldenergydata-bsee/pyproject.toml:L15-L24]

## 2. Inputs and outputs

### Inputs

| Name | Unit / representation | Range / default | Source and evidence |
| --- | --- | --- | --- |
| `basename`, `data`, `analysis` | Configuration mapping | `basename` required; data/analysis copied with empty-map fallback | Engine configuration. [packages/worldenergydata-bsee/src/worldenergydata/bsee/bsee.py:L14-L29] |
| `meta.mode`, `data.refresh` | Mode string, boolean | Mode defaults to `legacy`; refresh defaults to false; `enhanced` bypasses the legacy refresh flag | Refresh configuration. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/data_refresh.py:L27-L57] |
| `data.production_data` | Boolean | Defaults to false; disabled route returns no production groups | Production router. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/production/router.py:L13-L23] |
| `data.source`, `groups[].api12`, production file list | Source selector; identifiers; paths | `csv` selects local CSV loading; relative files resolve below `Analysis.analysis_root_folder` | Grouped CSV input. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/production/production_data_sources.py:L26-L78] |
| `parameters.filepath.production.zip`, `.bin` | Directory paths | Required mapping entries; direct existing path preferred; library lookup failure falls back to the raw path | ZIP/binary adapter. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L97-L128] |
| `API_WELL_NUMBER` | Identifier, not a physical unit | String normalization strips whitespace and a terminal `.0`, preserves nulls; cannot restore a leading zero already lost to integer storage | Shared normalizer. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/utils/api_well_normalizer.py:L12-L28] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/utils/api_well_normalizer.py:L46-L72] |
| Lease layout and source member | cp1252 text; fixed-width or strict CSV | Exact column count / allowed width; finite decimal values; dates parse from eight digits; `ASSIGNMENT_PCT` in 0–100 percent | `load_table` and scalar validation. [packages/worldenergydata-bsee/src/worldenergydata/bsee/lease_ingest.py:L19-L93] |
| Download body / archive | Bytes; optional member glob patterns | Classifies empty, ZIP, HTML or unknown bodies; extraction returns a DataFrame and member name; configured patterns fail closed | Payload helpers. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py:L90-L106] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py:L125-L158] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py:L175-L203] |
| `PipelineSpecLookup.match_od_wt` | OD and WT in m | OD/WT tolerance defaults to 0.003 m; WT defaults to zero for OD-only selection | Pipe lookup parameters, not licensed table values. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L30-L32] [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L71-L98] |

### Outputs

| Name | Unit / format | Behaviour and evidence |
| --- | --- | --- |
| Production `.bin` | Pickled pandas DataFrame | One binary file per processed ZIP filename stem; positional schema includes monthly volumes, identifiers, dates and days. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L123-L184] |
| CSV-normalized production | DataFrame; `PRODUCTION_DATE` as YYYYMM integer | Missing columns receive defaults; numeric conversion coerces failures to zero; month parsing accepts six-digit text without calendar validation. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/production/production_data_sources.py:L80-L138] |
| Runner production | Nine-column DataFrame | Identifiers are stripped, production year is YYYYMM integer-divided by 100, volumes/days are numeric with invalid values filled with zero. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L123-L178] |
| Report quantity labels | Oil/water bbl, gas mcf, depths ft, monetary columns `$` | These are report labels; this adapter does not establish raw-file measurement conditions or a currency-year basis. [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/report_builder.py:L25-L41] |
| Curated lease tables | Lists of records; ISO date strings; percent; source area-unit code | Separate lease, owner, operator, panel and missing-record outputs preserve history and missing reasons. [packages/worldenergydata-bsee/src/worldenergydata/bsee/lease_ingest.py:L147-L187] [packages/worldenergydata-bsee/src/worldenergydata/bsee/lease_ingest.py:L190-L236] |

UNVERIFIED: Raw production-volume reference conditions, injection-volume units and geospatial frame/origin/sign conventions across the wider package have not been established; do not use report labels as a raw-format contract; issue pending (1).

## 3. Method and governing standards

| Method | Implementation and limit |
| --- | --- |
| Refresh selection | `DataRefresh.router` selects enhanced refresh by mode; otherwise `data.refresh`, `data.apm` and `data.production` control legacy conversion. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/data_refresh.py:L27-L73] |
| Production ingestion | `GetProdDataFromZip.router` downloads when its ZIP directory is empty or forced, returns a download error on empty bytes, then serializes converted frames and counts files. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L21-L65] |
| Payload classification and primary-member extraction | `classify_payload` inspects byte markers; `select_primary_member` uses priority glob patterns or the largest data member, raising on configured-pattern misses; `extract_primary_table` returns the selected table and name. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py:L90-L106] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py:L125-L158] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py:L175-L203] |
| Identifier comparison | `api_matches` normalizes both sides and makes a null request match no rows; `select_by_api` checks the requested column before filtering. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/utils/api_well_normalizer.py:L31-L72] |
| Historical binary adaptation | `load_ogor_bin` rejects absent/unreadable/non-19-column inputs with an empty canonical frame and relabels by position; `to_runner_schema` maps without recovering missing source records. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L83-L120] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L123-L178] |
| Lease curation | `load_table` checks source layout and scalar types; `curate` selects requested identifiers, retains owner/operator history separately, rejects duplicate source leases and emits missing reasons. [packages/worldenergydata-bsee/src/worldenergydata/bsee/lease_ingest.py:L19-L93] [packages/worldenergydata-bsee/src/worldenergydata/bsee/lease_ingest.py:L190-L236] |
| Pipe schedule lookup | `match_od_wt` converts m to mm, filters OD, prefers WT candidates within tolerance when available and sorts by differences; out-of-tolerance WT does not force rejection when OD candidates exist. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L99-L132] |
| Rig-day calculation, coverage lead only | `war_rig_days` describes inclusive week spans and API10 union rather than per-bore summation, with an explicit separate PND bucket; detailed basis clearance remains open, and matching this module's historical output is not independent validation. [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/war_rig_days.py:L10-L62] |

### Standards named in source

This table identifies references embedded in software, not regulatory compliance findings. [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_references.py:L12-L25]

| Reference | Located use | Edition / clause status |
| --- | --- | --- |
| 30 CFR 250 | `get_regulatory_references` strings identify sections 250.1160, 250.804, 250.300, 250.1900, 250.188, 250.1700 and 250.130; `war_rig_days` names 250.743 | Regulatory text and current applicability not checked; strings are recorded as source metadata only. [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_references.py:L15-L108] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/war_rig_days.py:L10-L15] |
| 30 CFR 254 | Report reference list; `generate_environmental_actions` embeds 254.47 and 254.50 | Regulatory text and current applicability not checked. [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_references.py:L47-L55] [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_calculations.py:L239-L267] |
| 30 CFR 550 | Report reference string 550.1400 | Regulatory text and current applicability not checked. [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_references.py:L110-L119] |
| 40 CFR 60 Subpart OOOO | `get_regulatory_references` includes an air-quality entry | Regulatory text and current applicability not checked. [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_references.py:L57-L66] |
| API 5L, *Line Pipe*; ISO 3183, *Petroleum and natural gas industries — Steel pipe for pipeline transportation systems*; ASME B36.10M, *Welded and Seamless Wrought Steel Pipe* | Pipe lookup module names these references together; public titles: API, *2024 Publications Catalog*, tubular goods, Spec 5L entry ([catalog](https://www.api.org/-/media/files/publications/2024-catalog/2024-publication-catalog.pdf)); BSI, *BS EN ISO 3183:2019*, public product title ([catalogue](https://knowledge.bsigroup.com/products/petroleum-and-natural-gas-industries-steel-pipe-for-pipeline-transportation-systems)); ASME, *B36.10M*, public product title ([catalogue](https://www.asme.org/codes-standards/find-codes-standards/b36-10m-welded-seamless-wrought-steel-pipe)) | No edition, clause/table or clause title supplied in the cited docstring; the catalogue editions do not establish the code basis; clause text not checked against the licensed copy; no table values reproduced. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L1-L12] |

UNVERIFIED: Editions, clause/table provenance and output Citation sidecars for the named pipe references, and the correctness of the report's regulatory mappings, remain unchecked; no edition reconciliation is claimed; existing issue #361.

## 4. Validated worked examples

Validated examples: **0**; the following **7 regression examples** pin software behaviour without claiming an independent engineering reference; independent reference cases remain under issue pending (1). [tests/unit/bsee/test_bsee.py:L40-L60] [tests/unit/bsee/data/test_ogor_production_loader.py:L74-L99]

Execution record at BASE `33ba32d3cf4df473b44fd700ba6bb3744b435a43`, with unchanged code at the header pin: all seven nodes passed at BASE and on the uncommitted AFTER tree; the test command and non-passing corpus results are recorded in section 10.

| ID | Input / expected value / tolerance basis | Existing test node ID | Offline result |
| --- | --- | --- | --- |
| R1 | Mocked routers, one data dispatch and one analysis dispatch; exact equality, zero extra calls | `tests/unit/bsee/test_bsee.py::TestBSEE::test_router_basic` | BASE PASS; AFTER PASS. [tests/unit/bsee/test_bsee.py:L40-L60] |
| R2 | Four mixed-type identifiers; two normalized strings and two nulls; zero unequal elements | `tests/unit/bsee/data/utils/test_api_well_normalizer.py::TestNormalizeApiWellNumber::test_mixed_types` | BASE PASS; AFTER PASS. [tests/unit/bsee/data/utils/test_api_well_normalizer.py:L38-L44] |
| R3 | Synthetic archive with leading directory and quoted text member; exactly two rows and three columns | `tests/unit/bsee/test_bsee_payload.py::TestExtractPrimaryTable::test_extracts_bsee_style_txt_member` | BASE PASS; AFTER PASS. [tests/unit/bsee/test_bsee_payload.py:L23-L38] [tests/unit/bsee/test_bsee_payload.py:L120-L126] |
| R4 | Header-corrupted synthetic pickle; exactly 19 canonical columns and one surviving row; no lost-row recovery claimed | `tests/unit/bsee/data/test_ogor_production_loader.py::test_load_ogor_bin_relabels_columns` | BASE PASS; AFTER PASS. [tests/unit/bsee/data/test_ogor_production_loader.py:L74-L101] |
| R5 | Two synthetic production rows; oil sum 2,001,000.0 bbl; `pytest.approx` default tolerance, a regression assertion rather than a source-based tolerance | `tests/unit/bsee/data/test_ogor_production_loader.py::test_to_runner_schema_maps_and_types` | BASE PASS; AFTER PASS. [tests/unit/bsee/data/test_ogor_production_loader.py:L24-L71] [tests/unit/bsee/data/test_ogor_production_loader.py:L120-L139] |
| R6 | Empty company input and one absent lease identifier; exactly one missing record and explicit null name/reason | `tests/unit/bsee/data/test_lease_ingest.py::test_missing_source_and_company_are_explicit` | BASE PASS; AFTER PASS. [tests/unit/bsee/data/test_lease_ingest.py:L77-L88] |
| R7 | Exercises the `scripts/bsee` inventory row through `scripts/bsee/fetch_leases.py`; temporary extract and HTML panel from the same rows; manifest byte count and SHA-256 exactly equal output; zero mismatches | `tests/unit/bsee/data/test_lease_ingest.py::test_extract_renders_and_manifests_panel_from_same_rows` | BASE PASS; AFTER PASS. [tests/unit/bsee/data/test_lease_ingest.py:L164-L186] |

## 5. QA gates

Applicable family set: AQG r0, section 10, Python calculations; G0 inputs/units/citations, G1 imports/tests, G2 hand or published check, G5 evidence appendix; G3 and G4 excluded by that family row (AQG r0, sections 9–10).

| Gate | Applicability | Module-specific check, numeric pass criterion and unit | Evidence / current result |
| --- | --- | --- | --- |
| G0 | Applicable | G0.1: `select_by_api` cross-dtype matrix: 9/9 combinations select exactly 1 row with payload 0, and null argument selects 0 rows; unit rows / combinations | Existing parameterized identifier tests; BASE PASS; AFTER PASS. [tests/unit/bsee/data/utils/test_select_by_api.py:L23-L31] [tests/unit/bsee/data/utils/test_select_by_api.py:L53-L58] |
| G0 | Applicable | G0.2: `load_table` rejects 4/4 malformed fixtures (column layout, invalid date, nonfinite number, percentage outside range); unit rejected records | Existing parameterized validation test; BASE PASS; AFTER PASS. [tests/unit/bsee/data/test_lease_ingest.py:L35-L48] |
| G0 | Applicable | G0.3: `classify_payload` identifies 1 HTML response as HTML; `select_primary_member` raises on 1 configured-pattern miss; unit responses / exceptions | Existing payload tests; BASE PASS; AFTER PASS. [tests/unit/bsee/test_bsee_payload.py:L46-L49] [tests/unit/bsee/test_bsee_payload.py:L101-L109] |
| G0 | Applicable | G0.4: `load_ogor_bin` receives a missing file and a 2-column pickle; both return 0 rows and exactly 19 canonical columns; unit rows / columns | Existing fallback tests and direct shape check; BASE PASS; AFTER PASS. [tests/unit/bsee/data/test_ogor_production_loader.py:L104-L117] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L83-L120] |
| G1 | Applicable | G1.1: Python/pytest imports and execution over `tests/unit/bsee`, `tests/modules/bsee`, `tests/integration/modules/bsee`, `tests/integration/cli/test_bsee_cli.py`, `tests/integration/test_bsee_real_execution.py`; expect 3,414 outcomes, 0 collection errors and 0 failed nodes; unit outcomes / errors / test nodes | Local BASE and AFTER: 0 collection errors, 33 failures at cache creation; FAIL in the unchanged environment; issue pending (2). Hosted `Domain unit-bsee` passes at BASE; that shard covers only `tests/unit/bsee`, not the entire corpus (GitHub Actions, CI, `Domain unit-bsee`, run `38748284900`, job `116468179388`, head `33ba32d3`). [scripts/ci/select_test_targets.py:L203-L218] [scripts/ci/select_test_targets.py:L339-L343] [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/data_loader_enhanced.py:L43-L68] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/cache/chunk_manager.py:L89-L105] |
| G2 | Applicable | G2.1: `to_runner_schema` preserves the hand sum 1,000.0 + 2,000,000.0 = 2,001,000.0 bbl from two synthetic rows; absolute error ≤ 0.0 bbl; unit bbl | Exact scalar check BASE PASS; AFTER PASS (absolute error 0.0 bbl); existing test uses `pytest.approx`; this arithmetic identity does not validate upstream measured volumes. [tests/unit/bsee/data/test_ogor_production_loader.py:L24-L71] [tests/unit/bsee/data/test_ogor_production_loader.py:L120-L139] |
| G3 | NOT_APPLICABLE | Python calculations family has no short-dynamics gate | AQG r0, section 10, Python calculations row. |
| G4 | NOT_APPLICABLE | Python calculations family has no diffraction gate | AQG r0, section 10, Python calculations row. |
| G5 | Applicable | G5.1: lease extract manifest size and SHA-256 match panel bytes; 0 mismatches; unit artifacts | Depends on `scripts/bsee/fetch_leases.py` (`scripts/bsee` inventory row), not solely this package; BASE PASS; AFTER PASS. [scripts/bsee/fetch_leases.py:L144-L178] [tests/unit/bsee/data/test_lease_ingest.py:L164-L175] [tests/unit/bsee/data/test_lease_ingest.py:L180-L186] |
| G5 | Applicable | G5.2: R1–R6 cover this package and R7 depends on `scripts/bsee`; each has a source, existing node and before/after status; 7/7 complete records, 0 missing citations or results; unit example records | Local citation / node / execution audit PASS; 7/7 records complete. [tests/unit/bsee/test_bsee.py:L40-L60] [tests/unit/bsee/data/test_lease_ingest.py:L164-L186] |

G5.1 depends on the `scripts/bsee` row and checks output traceability only; a signed analytical QA appendix is not established by this test; issue pending (1). [tests/unit/bsee/data/test_lease_ingest.py:L164-L186]

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom / cause | Detection and incident | Evidence |
| --- | --- | --- |
| Invalid CSV numerics silently become zero; absent columns acquire defaults | No detection check exists for rejecting corrupt input instead of zero-filling; review policy under issue pending (1) | `ProductionDataFromSources._normalize_production_csv`. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/production/production_data_sources.py:L89-L125] |
| OD candidates can return a WT outside tolerance with no flag | No detection check exists for rejecting or flagging this fallback; issue pending (1) | `match_od_wt` retains OD candidates when no WT candidate qualifies. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L120-L153] |
| A missing production date becomes 0; any six-digit text bypasses calendar validation | No detection check exists for rejecting these month values; issue pending (1) | `_production_month`. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/production/production_data_sources.py:L129-L138] |
| Invalid runner volumes and days silently become zero | No detection check exists for rejecting corrupt values instead of zero-filling; issue pending (1) | `to_runner_schema`. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L171-L176] |
| Identifier dtype mismatch can look like absent coverage; the binary-array loader still prefilters with dtype-sensitive `isin` before its normalized per-identifier selection | G0.1 covers the shared helper, not this earlier prefilter; no detection check exists for the complete binary-array route; issue pending (4); closed incident #1113 fixed a different WAR-loader site | `get_data_by_api12_array`. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L308-L328] [tests/unit/bsee/data/utils/test_select_by_api.py:L1-L6] |
| Historical pickle header corruption has already removed a source record; positional relabelling does not restore it | R4 detects the surviving-row shape; adjacent readers reconstruct one header record per yearly file, so their counts differ from this loader; no detection check exists here for original-source row reconciliation; issue pending (1) | Limitation is documented and reproduced synthetically. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L3-L19] [tests/unit/bsee/data/test_ogor_production_loader.py:L74-L101] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L130-L167] [scripts/all_fields_economics.py:L32-L35] |
| Missing/unreadable/noncanonical binary input yields an empty canonical frame; absent coverage must be distinguished from zero production | G0.4 pins the missing-file and wrong-column fallback; coverage policy under issue pending (1) | Binary loader fallback tests. [tests/unit/bsee/data/test_ogor_production_loader.py:L104-L117] |
| HTTP success can carry HTML; archives can have a leading directory and text rather than CSV members | G0.3 and R3; incident #267, runtime format compatibility | Source catalog and offline fixtures. [docs/data/bsee-source-catalog.md:L20-L52] [tests/unit/bsee/test_bsee_payload.py:L41-L72] |
| Default report construction initializes enhanced refresh and creates cache directories before report data is supplied | G1.1 detects an environment-dependent write failure, not an assertion defect: local BASE and AFTER each have 33 failures in two reporting files; the same shard passes on the hosted runner; issue pending (2) | Constructor chain reaches `ChunkManager` directory creation. [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/hierarchical_aggregator.py:L64-L78] [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/report_builder.py:L43-L51] [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/data_loader_enhanced.py:L63-L68] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/enhanced/data_refresh_chunked.py:L39-L46] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/cache/chunk_manager.py:L89-L105] |
| PND attribution and inclusive counting are declared conventions, not an independently ratified engineering reference | No detection check exists for authoritative code meanings; existing issues #1065 and #1062; this path is not a hand-check reference | Explicit caveat and withdrawn validation attribution. [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/war_rig_days.py:L20-L62] |
| Pipe references lack edition/table provenance in the lookup docstring; compliance strings do not prove clause correctness | No detection check exists for licensed-source agreement; existing issue #361 | Named references and report reference list. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L1-L12] [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_references.py:L12-L25] |
| Recursive Markdown package-data glob can include this documentation in a built wheel | No wheel-exclusion test exists in the reviewed main path; issue pending (3); packaging configuration remains unchanged | BSEE package-data rule. [packages/worldenergydata-bsee/pyproject.toml:L112-L116] |

## 7. Lessons log

| Date | Record | Lesson / evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial documentation | The shared identifier helper tests do not prove that every upstream prefilter is dtype-safe. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L308-L328] [tests/unit/bsee/data/utils/test_select_by_api.py:L23-L31] | Record the binary-array prefilter separately in section 6 | Pending; existing issue #1113 |
| 2026-10-15 | Initial documentation | A synthetic corrupted pickle regression checks relabelling, not source-row completeness. [tests/unit/bsee/data/test_ogor_production_loader.py:L74-L101] | Distinguish R4 from independent validation | Pending; issue pending (1) |
| 2026-10-15 | Identifier follow-up | Closed incident #1113 concerns a different WAR-loader site; the binary-array prefilter remains a separate open defect. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L308-L328] | Track the remaining defect as issue pending (4) in sections 6 and 10 | Pending; issue pending (4) |

## 8. Ownership

Proposed clearance route: EC family quality manager; deputy: data-pipeline quality manager when appointed; contributors: data ingestion and Python calculations maintainers; unresolved basis, tolerance and provenance questions go to the family quality manager, with cross-family questions to the maintainer (AQG r0, section 11).

UNVERIFIED: Role appointments, deputy availability and shared-log/index registration are not established by repository evidence; issue pending (1).

## 9. Dependencies

### Runtime and data dependencies

| Dependency | Route / boundary | Evidence |
| --- | --- | --- |
| `assetutilities` | YAML path resolution and ZIP-to-DataFrame conversion used by production ingestion | Imports and executed adapter calls. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L97-L114] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L160-L175] |
| Common, forecasting, reporting, regional adapters and economics distributions | Declared dependencies include core, sodir, reporting, texas_rrc and fdas | Distribution dependency list. [packages/worldenergydata-bsee/pyproject.toml:L62-L67] |
| Adjacent `lower_tertiary` (inventory row `bsee:lower_tertiary`) | Main router delegates the well-benchmark special route; adjacent package internals are outside this pack's detailed main-path review | Explicit delegation. [packages/worldenergydata-bsee/src/worldenergydata/bsee/bsee.py:L22-L42] |
| BSEE production ZIPs / historical OGOR-A pickles | Production source directories and positional 19-column adaptation; local fixtures do not establish live coverage | Main adapters. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L116-L184] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L83-L120] |
| `scripts/bsee` inventory row | R7 and G5.1 execute `fetch_leases.py` through `runpy`; panel HTML and its manifest digest are produced by the script | Test delegation and renderer. [tests/unit/bsee/data/test_lease_ingest.py:L164-L186] [scripts/bsee/fetch_leases.py:L144-L178] |
| Lease layouts / fixture slices | `source_schema.json` and fixture member/archive names drive the lease loader tests | Test fixture setup. [tests/unit/bsee/data/test_lease_ingest.py:L14-L25] |
| Pipeline reference CSV | Lazy read, cached; missing CSV produces an empty frame and subsequent match returns no result | Lookup dependency, with no table values copied. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L56-L69] [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L99-L101] |

### OrcaFlex text dependency inventory

All three case-insensitive `OrcaFlex` / `OrcFxAPI` text matches in the package at the code pin are listed below; the file imports pandas and uses ordinary CSV lookup, without a licensed-interface call in this path. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L1-L20] [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L56-L69]

| Location | Classification | Evidence |
| --- | --- | --- |
| Module docstring, line 4 | Describes enrichment of extracted line-object dimensions | [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L1-L4] |
| Module docstring, line 6 | Describes an extraction use case and SI dimensions | [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L6-L8] |
| `PipelineSpecLookup` docstring, line 36 | Describes matching OD/WT to a pipe specification | [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L35-L40] |

No solver version or licensed loading route is established here; source references are not evidence of a solver run. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L1-L20]

### Implementation-map audit

Audit metadata (read-only map observation):

```text
Repository: digitalmodel
Map: docs/registry/implementation-map.yaml
Ref commit: b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407
Data revision declared by map: 947fa50ff9a9e210de7e8f90e01b37add85c5954
Map family count: 13
Related map family without in-package rows: api-5ct-5l-grade-tables
Implementations with paths inside this pack's package: 0
Module map-family inventory: empty
Counted families: empty
Counted-family grep: NOT_APPLICABLE (no in-package map rows)
Further second implementations in counted families: 0 (empty set)
```

Map follow-up, issue pending (1): add in-package rows for refresh routing, production ingestion, identifier normalization, historical binary adaptation, lease-layout curation, pipe-spec matching, rig-day aggregation and payload classification and primary-member extraction before counting these families in a later map revision; these are the eight methods listed in section 3. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/data_refresh.py:L27-L73] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/utils/api_well_normalizer.py:L12-L43] [packages/worldenergydata-bsee/src/worldenergydata/bsee/lease_ingest.py:L58-L93] [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/spec_lookup.py:L99-L132] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/war_rig_days.py:L10-L24]

The map follow-up also covers production ingestion and historical binary adaptation at their implementations, plus payload extraction. [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/zip/production_data.py:L21-L65] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/sources/bin/ogor_production_loader.py:L83-L178] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/refresh/payload.py:L90-L203]

### Whole-repository related implementations

Definition-name searches covered tracked Python under the repository, including `scripts/`; the following independently implemented paths are review leads, not independent validation of each other; complete method equivalence remains under issue pending (1). [scripts/refresh_bsee_all.py:L194-L215] [scripts/all_fields_economics.py:L32-L46]

| Definition | Relationship / boundary | Evidence |
| --- | --- | --- |
| `BSEERefreshOrchestrator._process_zip_to_bins` | Separate script-level ZIP member conversion / binary serialization | [scripts/refresh_bsee_all.py:L194-L254] |
| `lower_tertiary.v30_reproducer.load_ogor_production` | Separate adjacent-package ZIP parser using explicit source column names | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L116-L166] |
| `lower_tertiary.ops_timeline.load_ogor_from_bin` | Wrapper returning a copy of a cached result; helper rather than an additional parser | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L109-L127] |
| `lower_tertiary.ops_timeline._load_ogor_from_bin_uncached` | Separate binary parser reconstructs a header row before joining data, unlike the main positional adapter | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L130-L167] |
| `scripts/all_fields_economics._read_bin_year`, `load_ogor` | Separate script reconstructs header data and normalizes production fields | [scripts/all_fields_economics.py:L32-L46] |
| `war_rig_days.normalize_api12` | Validates exactly 12 ASCII digits after trimming whitespace and integral decimal tails; rejects missing, family, completion and malformed keys without padding or truncation. Callers may explicitly quarantine malformed WAR rows with a count warning before aggregation. | [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/war_rig_days.py (`normalize_api12`, `quarantine_war_identifiers`)] [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/utils/api_well_normalizer.py:L24-L28] |

## 10. Coverage and open items

### Coverage record

This revision limits detailed semantic review to the main paths cited in sections 1–6; other discovered source and documentation remain coverage leads, not cleared behaviour; issue pending (1). [packages/worldenergydata-bsee/src/worldenergydata/bsee/bsee.py:L14-L42]

Inventory observations at the code pin:

```text
Package Python files read by static AST inventory: 299
Package Python source lines: 82709
Function / async-function / class definitions: 3059
Documentation candidates discovered by content/path search: 209
Documentation candidate paths listed below: 203
Discovery files with identifying names withheld: 6
Codenaming and semantic review: issue pending (1)
Selected test outcomes at BASE and AFTER: 3414 per command
Executed nodes at BASE and AFTER: 3358 per command
BASE: passed 3325; failed 33; skipped 56; NOT_RUN 0
AFTER: passed 3325; failed 33; skipped 56; NOT_RUN 0
```

Test discovery includes `tests/unit/bsee`, `tests/modules/bsee`, `tests/integration/modules/bsee`, the BSEE CLI integration file and the real-execution integration file; default repository collection exclusions remain in effect. [pyproject.toml:L340-L414] [tests/integration/cli/test_bsee_cli.py:L1-L13] [tests/integration/test_bsee_real_execution.py:L1-L20]

The collection count above describes the selected corpus, not a claim about every package test; archive folders, legacy datasets, external workflow/scheduler consumers and tests outside those paths remain coverage work under issue pending (1). [pyproject.toml:L351-L382] [pyproject.toml:L392-L414]

### Open-item register

| Item | Scope / required follow-up | Responsible role | Issue |
| --- | --- | --- | --- |
| COV | Complete semantic review beyond ingestion: analysis, financial, forecasting, paleowells, reporting, visualization, remaining discovered docs/tests and six withheld discovery files requiring codenames; document the three silent fallback policies in section 6; add independent benchmark cases, signed evidence appendix, role/index/shared-log registration and map rows | Data and calculations maintainers | issue pending (1) |
| U1 | UNVERIFIED raw-format units, measurement reference conditions and geospatial conventions from section 2 | Data maintainer | issue pending (1) |
| U2 | UNVERIFIED pipe-standard editions, clauses/tables, Citation sidecars and regulatory reference correctness from section 3 | Calculations maintainer | #361 |
| U3 | UNVERIFIED role appointments and registration from section 8 | Maintainer | issue pending (1) |
| CACHE | Isolate default report-construction cache writes; preserve the local 33-node BASE/AFTER write-failure record and distinguish the passing hosted shard | Data maintainer | issue pending (2) |
| DIST | Resolve recursive Markdown package-data inclusion of knowledge packs without modifying module behaviour | Packaging maintainer | issue pending (3) |
| API | Extend cross-dtype checks through the production binary-array prefilter; closed #1113 is incident evidence only | Data maintainer | issue pending (4) |
| BASIS | Confirm activity-code meanings and keep basis-dependent rig-day results out of independent references | Data maintainer | #1065; #1062 |

### Documentation discovery inventory

The following paths were discovered and read as text by the inventory; a listed match is not a claim that every document was semantically reviewed, and archived counts or validation assertions are not adopted; detailed reading outside the cited main path remains under issue pending (1).

- [docs/AI_USAGE_GUIDELINES.md:L38-L38]
- [docs/CLI.md:L33-L33]
- [docs/COMMANDS.md:L4-L4]
- [docs/MIGRATION_GUIDE.md:L26-L26]
- [docs/PHASE_2_TIER_1_COVERAGE_EXPANSION.md:L62-L62]
- [docs/adr/0001-domain-package-split.md:L22-L22]
- [docs/analysis-guides/index.md:L93-L93]
- [docs/ci/flake8-inventory-2026-04-23.md:L76-L76]
- [docs/data-outputs-site.md:L17-L17]
- [docs/data-sources/FINAL_DATA_ACQUISITION_SUMMARY.md:L260-L260]
- [docs/data-sources/INDUSTRIAL_MARITIME_DATA_SOURCES.md:L14-L14]
- [docs/data-sources/MANUAL_DOWNLOAD_GUIDE.md:L10-L10]
- [docs/data-sources/MARINE_SAFETY_IMPORT_STATUS.md:L122-L122]
- [docs/data-sources/README.md:L9-L9]
- [docs/data-sources/bsee/_legacy/data_for_analysis_legacy.md:L10-L10]
- [docs/data-sources/bsee/analysis/economics/NPV/NPV_REFACTORING_SUMMARY.md:L61-L61]
- [docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.md:L15-L15]
- [docs/data-sources/bsee/analysis/well-identifier-grain.md:L6-L6]
- [docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md:L12-L12]
- [docs/data-sources/bsee/data/WELL_ACTIVITY_CD/well_activity_cd_description.md:L4-L4]
- [docs/data-sources/bsee/data/analysis_data.md:L35-L35]
- [docs/data-sources/bsee/data/apm_data_rev1.md:L10-L10]
- [docs/data-sources/bsee/data/clean_up/data_explaination.md:L3-L3]
- [docs/data-sources/bsee/data/clean_up/data_for_analysis.md:L7-L7]
- [docs/data-sources/bsee/data/data_rev1.md:L10-L10]
- [docs/data-sources/bsee/data/drilling_data_rev1.md:L10-L10]
- [docs/data-sources/bsee/data/field_engineering_package_contract.md:L13-L13]
- [docs/data-sources/bsee/data/field_infrastructure_bundle_contract.md:L5-L5]
- [docs/data-sources/bsee/data/local_field_development_sources.md:L10-L10]
- [docs/data-sources/bsee/data/production/notes.md:L5-L5]
- [docs/data-sources/bsee/data/well/well_count.md:L12-L12]
- [docs/data-sources/index.md:L12-L12]
- [docs/data-sources/onshore/texas-rrc/field-development-metrics.md:L4-L4]
- [docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md:L3-L3]
- [docs/data/DATA_INVENTORY_ANALYSIS.md:L9-L9]
- [docs/data/DATA_MAP.md:L13-L13]
- [docs/data/LOCAL_DATA_PATTERN.md:L7-L7]
- [docs/data/TWO_TIER_DATA.md:L30-L30]
- [docs/data/bsee-source-catalog.md:L1-L1]
- [docs/development/coverage_strategy.md:L13-L13]
- [docs/development/development_history.md:L63-L63]
- [docs/development/index.md:L74-L74]
- [docs/development/refactoring_guide.md:L5-L5]
- [docs/domains/bsee/infrastructure_data_catalog.md:L1-L1]
- [docs/domains/bsee/paleowells-readme.md:L1-L1]
- [docs/domains/field-development/README.md:L54-L54]
- [docs/examples/index.md:L36-L36]
- [docs/guides/PHASE_1_TEST_DEVELOPMENT_PLAN.md:L30-L30]
- [docs/guides/QUICK_START.md:L26-L26]
- [docs/guides/user_prompt.md:L11-L11]
- [docs/hse/URL_REFRESH_INTEGRATION.md:L3-L3]
- [docs/hse/grounding-riser-matches.md:L16-L16]
- [docs/intervention-db/data-quality.md:L19-L19]
- [docs/intervention-db/intervention-stats-brief.generated.md:L1-L1]
- [docs/knowledge-base/bsee/README.md:L1-L1]
- [docs/knowledge-base/bsee/data-dictionaries/common/api-number-format.md:L93-L93]
- [docs/knowledge-base/bsee/data-dictionaries/common/date-formats.md:L3-L3]
- [docs/knowledge-base/bsee/data-dictionaries/common/nad-projections.md:L3-L3]
- [docs/knowledge-base/bsee/data-dictionaries/common/region-codes.md:L72-L72]
- [docs/knowledge-base/bsee/data-dictionaries/common/unit-conversions.md:L3-L3]
- [docs/knowledge-base/bsee/data-dictionaries/index.md:L1-L1]
- [docs/knowledge-base/bsee/data-dictionaries/leasing/lease-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/pipelines/location-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/platforms/structure-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/production/production-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/wells/apd-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/wells/borehole-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/wells/completion-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/wells/status-codes.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/wells/type-codes.md:L4-L4]
- [docs/knowledge-base/bsee/data-dictionaries/wells/war-fields.md:L4-L4]
- [docs/knowledge-base/bsee/data-sources/index.md:L1-L1]
- [docs/knowledge-base/bsee/data-sources/raw-data-downloads.md:L1-L1]
- [docs/knowledge-base/bsee/data-sources/update-schedule.md:L1-L1]
- [docs/knowledge-base/bsee/gis-catalog/index.md:L1-L1]
- [docs/knowledge-base/bsee/integration/codebase-mapping.md:L3-L3]
- [docs/knowledge-base/bsee/query-interfaces/borehole-query.md:L3-L3]
- [docs/knowledge-base/bsee/query-interfaces/export-formats.md:L3-L3]
- [docs/knowledge-base/bsee/query-interfaces/index.md:L1-L1]
- [docs/knowledge-base/bsee/query-interfaces/pipeline-query.md:L3-L3]
- [docs/knowledge-base/bsee/query-interfaces/platform-query.md:L3-L3]
- [docs/knowledge-base/bsee/query-interfaces/production-query.md:L3-L3]
- [docs/knowledge-base/bsee/regions/alaska.md:L6-L6]
- [docs/knowledge-base/bsee/regions/atlantic.md:L6-L6]
- [docs/knowledge-base/bsee/regions/gulf-of-america.md:L6-L6]
- [docs/knowledge-base/bsee/regions/index.md:L1-L1]
- [docs/knowledge-base/bsee/regions/pacific.md:L6-L6]
- [docs/marine-safety-data-sources-comprehensive.md:L149-L149]
- [docs/modules/bsee/PRODUCTION_DATA_RETRIEVAL_GUIDE.md:L1-L1]
- [docs/modules/bsee/analysis/production/FDAS_V30/PRICE_DECKS_SOURCE.md:L3-L3]
- [docs/modules/bsee/analysis/production/FDAS_V30/QUICKSTART.md:L14-L14]
- [docs/modules/bsee/analysis/production/FDAS_V30/README_PRODUCTION_RETRIEVAL.md:L26-L26]
- [docs/modules/bsee/analysis/production/lt_v30_v50_code_reconciliation.md:L4-L4]
- [docs/modules/bsee/chunk_refresh_mechanism.md:L5-L5]
- [docs/modules/bsee/communications/email-review/reviewed/2025-08-01.md:L27-L27]
- [docs/modules/bsee/communications/email-review/reviewed/2026-07-08-fdas-canonicalization.md:L3-L3]
- [docs/modules/bsee/comprehensive-report-system/README.md:L1-L1]
- [docs/modules/bsee/comprehensive-report-system/api-documentation.md:L17-L17]
- [docs/modules/bsee/comprehensive-report-system/performance-tuning-guide.md:L17-L17]
- [docs/modules/bsee/comprehensive-report-system/template-configuration-guide.md:L14-L14]
- [docs/modules/bsee/comprehensive-report-system/user-guide.md:L1-L1]
- [docs/modules/bsee/data-refresh-architecture/README.md:L5-L5]
- [docs/modules/bsee/data-refresh-architecture/data-flow-diagram.md:L20-L20]
- [docs/modules/bsee/data-refresh-architecture/module-documentation.md:L7-L7]
- [docs/modules/bsee/data-refresh-architecture/web-scraping-libraries.md:L11-L11]
- [docs/modules/bsee/well-path-3d-plotly.md:L1-L1]
- [docs/modules/bsee/well-path-3d-threejs.md:L1-L1]
- [docs/modules/bsee/well_data_verification/bsee_integration.md:L1-L1]
- [docs/modules/bsee/well_data_verification/configuration_guide.md:L63-L63]
- [docs/modules/bsee/well_data_verification/troubleshooting.md:L386-L386]
- [docs/modules/bsee/well_data_verification/user_guide.md:L16-L16]
- [docs/modules/bsee/well_data_verification/workflow_tutorial.md:L298-L298]
- [docs/modules/data-procurement/api-catalog.md:L8-L8]
- [docs/modules/data-procurement/api-decision-matrix.md:L29-L29]
- [docs/modules/data_sodir/README.md:L11-L11]
- [docs/modules/data_sodir/api_guide.md:L471-L471]
- [docs/modules/data_sodir/config_guide.md:L346-L346]
- [docs/modules/data_sodir/cross_regional_tutorial.md:L23-L23]
- [docs/modules/fdas/DEPLOYMENT-CHECKLIST.md:L88-L88]
- [docs/modules/fdas/USER-GUIDE.md:L13-L13]
- [docs/modules/fdas/VALIDATION-REPORT.md:L317-L317]
- [docs/modules/fdas/country-adapter-checklist.md:L41-L41]
- [docs/modules/marine_safety/INCIDENT_CAUSE_ANALYSIS_MODULE.md:L33-L33]
- [docs/modules/repository-architecture.md:L6-L6]
- [docs/modules/well-production-dashboard/USER_GUIDE.md:L334-L334]
- [docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md:L30-L30]
- [docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md:L16-L16]
- [docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md:L18-L18]
- [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L14-L14]
- [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L14-L14]
- [docs/plans/2026-05-03-issue-375-per-field-economics-10-lt-fields.md:L30-L30]
- [docs/plans/2026-05-03-issue-376-cross-field-analytics-lt.md:L30-L30]
- [docs/plans/2026-05-04-issue-129-boem-bsee-cli-refresh.md:L1-L1]
- [docs/plans/2026-05-04-issue-143-bsee-field-econ-calibrated.md:L1-L1]
- [docs/plans/2026-05-04-issue-172-lt-rev30-reproducibility.md:L1-L1]
- [docs/plans/2026-05-04-issue-267-bsee-scheduler-compat.md:L1-L1]
- [docs/plans/2026-05-04-issue-270-lng-terminals-scheduler-wire.md:L19-L19]
- [docs/plans/2026-05-04-issue-271-scheduler-output-dir.md:L26-L26]
- [docs/plans/2026-05-04-issue-274-bandit-remove-or-true.md:L18-L18]
- [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L1-L1]
- [docs/plans/2026-05-04-issue-313-test-infra-cleanup.md:L28-L28]
- [docs/plans/2026-05-04-issue-325-xfail-bugs.md:L8-L8]
- [docs/plans/2026-05-04-issue-326-prepare-production-data-missing.md:L1-L1]
- [docs/plans/2026-05-04-issue-339-legacy-npv-test-resolution.md:L16-L16]
- [docs/plans/2026-05-04-issue-341-npv-suite-drift.md:L9-L9]
- [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L17-L17]
- [docs/plans/2026-05-04-issue-351-scheduler-readiness-matrix.md:L35-L35]
- [docs/plans/2026-05-04-issue-352-cli-smoke-verification.md:L27-L27]
- [docs/plans/2026-05-04-issue-360-scheduler-health.md:L38-L38]
- [docs/plans/2026-05-04-issue-361-calc-citation-contract.md:L14-L14]
- [docs/plans/2026-05-04-issue-362-operator-cost-benchmarking-report.md:L31-L31]
- [docs/plans/2026-05-04-issue-363-hse-query-api.md:L26-L26]
- [docs/plans/2026-05-04-issue-365-bsee-binary-ingest.md:L1-L1]
- [docs/plans/2026-05-04-issue-367-api12-npv-migration.md:L9-L9]
- [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L71-L71]
- [docs/plans/2026-05-15-issue-411-bsee-war-bridge.md:L2-L2]
- [docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md:L16-L16]
- [docs/plans/2026-05-18-issue-423-marketing-pipeline-umbrella.md:L14-L14]
- [docs/plans/2026-05-18-issue-424-decommissioning-market-outlook.md:L15-L15]
- [docs/plans/2026-05-18-issue-425-operator-hse-benchmarking.md:L15-L15]
- [docs/plans/2026-05-18-issue-426-drilling-hse-patterns.md:L18-L18]
- [docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md:L19-L19]
- [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L27-L27]
- [docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md:L48-L48]
- [docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md:L57-L57]
- [docs/plans/2026-07-03-issue-714-fdas-source-agnostic.md:L9-L9]
- [docs/plans/2026-07-04-issue-715-adapter-contract.md:L11-L11]
- [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L49-L49]
- [docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md:L358-L358]
- [docs/plans/2026-07-06-issue-847-boem-reserves-discovery-ingest.md:L17-L17]
- [docs/plans/2026-07-11-issue-927-bsee-hf-pilot.md:L1-L1]
- [docs/plans/2026-07-16-issue-1038-cost-map-program.md:L16-L16]
- [docs/plans/2026-07-18-issue-1039-manifest-lineage-hotfix.md:L220-L220]
- [docs/plans/README.md:L11-L11]
- [docs/reference/index.md:L81-L81]
- [docs/reference/petrophysics_MERGED_INTO_normalization_for_laterals.txt:L1-L1]
- [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L122-L122]
- [docs/reports/2026-04-26-plan-353-codex.md:L10-L10]
- [docs/reports/2026-04-26-plan-353-gemini.md:L18-L18]
- [docs/reports/2026-04-26-plan-353-rerun-gemini.md:L8-L8]
- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L13-L13]
- [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L14-L14]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L13-L13]
- [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L33-L33]
- [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L34-L34]
- [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L12-L12]
- [docs/reports/2026-04-26-worldenergydata-scheduler-safe-probe-results.md:L17-L17]
- [docs/reports/2026-05-11-issue-353-scheduler-timeout-validation.md:L9-L9]
- [docs/reports/cli-smoke-report-2026-05-11.md:L14-L14]
- [docs/reports/data-freshness-scorecard-2026-06-08.md:L6-L6]
- [docs/reports/scheduler-health-2026-W16.md:L12-L12]
- [docs/reports/scheduler-health-2026-W24.md:L11-L11]
- [docs/research/bsee-fdas-integration-summary.md:L1-L1]
- [docs/research/docs/research/FDAS-INTEGRATION-STATUS.md:L18-L18]
- [docs/research/docs/research/fdas-documentation-review-summary.md:L18-L18]
- [docs/research/docs/research/fdas-integration-index.md:L10-L10]
- [docs/research/fdas-code-comparison.md:L216-L216]
- [docs/research/fdas-executive-summary.md:L11-L11]
- [docs/research/fdas-implementation-plan.md:L9-L9]
- [docs/research/fdas-quick-reference.md:L27-L27]
- [docs/user-guide/index.md:L35-L35]
- [packages/worldenergydata-bsee/README.md:L1-L1]

### Offline execution record

```text
Code pin: 55991b0def0f90708b3e0c396c0f57d9d1b7f7fb
Execution BASE: 33ba32d3cf4df473b44fd700ba6bb3744b435a43
Execution AFTER: same BASE plus uncommitted pack revision 1
Form: uv run --with weasyprint --with folium; existing addopts and conftest retained
Environment: unchanged home; no licensed interface imported
Command: uv run --with weasyprint --with folium python -m pytest <selected paths> -q -rA
         -p no:cacheprovider --basetemp=<scratch>
Selected paths:
  tests/unit/bsee
  tests/modules/bsee
  tests/integration/modules/bsee
  tests/integration/cli/test_bsee_cli.py
  tests/integration/test_bsee_real_execution.py
BASE: 3414 outcomes; 3325 passed; 33 failed; 56 skipped; NOT_RUN 0
AFTER: 3414 outcomes; 3325 passed; 33 failed; 56 skipped; NOT_RUN 0
Initial ordinary-uv BASE: 3323 passed; 33 failed; 58 skipped; NOT_RUN 0
The two optional-renderer tests pass with the added runtime packages
Failing-node identities: identical before and after
Extra scalar check: G2.1 PASS; absolute conservation error 0.0 bbl
```

Both recorded augmented runs used unchanged module code at the source pin; the AFTER run included this uncommitted documentation, and no module source was changed; baseline failure sources and both failing test files were read from `origin/main` and matched the worktree byte for byte; issue pending (2).

#### Failing nodes at BASE and AFTER

All following failures reach the cache-construction path described in section 6; issue pending (2). [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/cache/chunk_manager.py:L89-L105]

- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestBaseAggregatorInstance::test_aggregate_raises` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L209-L216]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestBaseAggregatorInstance::test_calculate_costs` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L188-L207]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestBaseAggregatorInstance::test_calculate_revenue` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L163-L176]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestBaseAggregatorInstance::test_calculate_revenue_empty` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L178-L186]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestBaseAggregatorInstance::test_custom_init` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L152-L161]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestBaseAggregatorInstance::test_default_init` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L143-L150]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestGenerateSummary::test_aggregate_hierarchy_invalid_level` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L308-L315]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestGenerateSummary::test_empty_data` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L225-L232]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestGenerateSummary::test_multiple_entities` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L259-L287]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestGenerateSummary::test_single_entity` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L234-L257]
- `tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py::TestGenerateSummary::test_zero_revenue_profit_margin` [tests/unit/bsee/reports/comprehensive/test_hierarchical_aggregator.py:L289-L306]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestApplyGobyFormatting::test_empty_rows` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L356-L360]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestApplyGobyFormatting::test_formats_production_volumes` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L323-L354]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildAggregationSection::test_block_aggregation` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L210-L231]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildAggregationSection::test_lease_aggregation` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L233-L251]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildAggregationSection::test_no_data` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L205-L208]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildDetailRows::test_block_report` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L176-L196]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildDetailRows::test_field_report` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L159-L174]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildDetailRows::test_lease_report` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L143-L157]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildDetailRows::test_no_data` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L138-L141]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildMetadata::test_basic` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L32-L41]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildSummarySection::test_empty_summary` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L77-L81]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildSummarySection::test_no_data` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L50-L54]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestBuildSummarySection::test_with_summary` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L56-L75]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestCreateWellRow::test_full_data` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L90-L114]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestCreateWellRow::test_missing_values` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L124-L129]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestCreateWellRow::test_no_field` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L116-L122]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestGoByReportBuilderInit::test_defaults` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L15-L18]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestPrepareChartData::test_no_data` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L260-L263]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestPrepareChartData::test_with_summary` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L265-L280]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestValidateReportData::test_complete_report` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L289-L298]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestValidateReportData::test_missing_sections_warns` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L300-L303]
- `tests/unit/bsee/reports/comprehensive/test_report_builder.py::TestValidateReportData::test_row_length_mismatch` [tests/unit/bsee/reports/comprehensive/test_report_builder.py:L305-L314]

#### Existing skips at BASE and AFTER

The 56 existing skips below were retained; no test was newly skipped or deselected. Missing data/templates, unsupported planned interfaces and pre-existing compatibility skips remain coverage limits under issue pending (1).

| Existing skip site / definition | Count | Existing reason category |
| --- | --- | --- |
| `TestConfigRouter` [tests/unit/bsee/data/config/test_config_router.py:L24-L26] | 15 | Planned interface not implemented |
| `test_plotting_methods` [tests/integration/test_bsee_real_execution.py:L319-L321] | 1 | Required data or templates unavailable |
| `test_full_pipeline_execution` [tests/integration/test_bsee_real_execution.py:L346-L348] | 1 | Required data or templates unavailable |
| `test_load_actual_files` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_actual_data_loading.py:L22-L25] | 1 | Required data or templates unavailable |
| `test_analyze_data_sources` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_analyze_date_calculations` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_analyze_drilling_completion_logic` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_compare_methodologies` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_extract_business_rules` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_analyze_script_complexity` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_identify_key_differences` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_generate_methodology_summary` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_analyze_script_imports` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_analyze_function_definitions` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_code_analysis.py:L33-L36] | 1 | Required data or templates unavailable |
| `test_excel_vs_task8_comparison` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_excel_vs_task8_comparison.py:L353-L356] | 1 | Required data or templates unavailable |
| `test_export_field_analysis` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_field_analysis.py:L25-L28] | 1 | Required data or templates unavailable |
| `test_field_analysis_with_actual_data` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_field_analysis.py:L25-L28] | 1 | Required data or templates unavailable |
| `test_get_wells_by_specific_fields` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_field_analysis.py:L25-L28] | 1 | Required data or templates unavailable |
| `test_comprehensive_summary_generation` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_representative_wells.py:L27-L30] | 1 | Required data or templates unavailable |
| `test_save_selected_wells_info` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_representative_wells.py:L27-L30] | 1 | Required data or templates unavailable |
| `test_select_high_and_low_difference_wells` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_representative_wells.py:L27-L30] | 1 | Required data or templates unavailable |
| `test_detailed_well_comparison` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/test_representative_wells.py:L27-L30] | 1 | Required data or templates unavailable |
| `test_run_process` [tests/modules/bsee/data/refresh/data_refresh_test.py:L32-L40] | 1 | Required data or templates unavailable |
| `test_real_data_sane_structure` [tests/unit/bsee/analysis/intervention/test_activity_by_band.py:L212-L214] | 1 | Required data or templates unavailable |
| `test_real_data_sane_structure` [tests/unit/bsee/analysis/intervention/test_intervention_demand.py:L170-L172] | 1 | Required data or templates unavailable |
| `test_real_data_confirms_no_light_intervention_in_deepwater` [tests/unit/bsee/analysis/intervention/test_rlwi_war_coverage.py:L278-L280] | 1 | Required data or templates unavailable |
| `test_real_data_sane_structure` [tests/unit/bsee/analysis/intervention/test_war_vessel_crossref.py:L176-L178] | 1 | Required data or templates unavailable |
| `test_known_on_record_band_counts` [tests/unit/bsee/analysis/intervention/test_well_inventory_by_band.py:L112-L115] | 1 | Required data or templates unavailable |
| `test_run_production_analysis_without_data` [tests/unit/bsee/analysis/test_production_api12.py:L100-L102] | 1 | Existing fixture/configuration mismatch |
| `test_error_handling_invalid_data` [tests/unit/bsee/analysis/test_production_api12.py:L245-L247] | 1 | Existing fixture/configuration mismatch |
| `test_run_production_analysis_with_data` [tests/unit/bsee/analysis/test_production_api12.py:L75-L77] | 1 | Existing fixture/configuration mismatch |
| `test_basic_kpis` [tests/unit/bsee/reports/comprehensive/visualizations/test_dashboard_builder.py:L139-L139] | 1 | Optional dashboard/mock incompatibility |
| `test_empty_kpis` [tests/unit/bsee/reports/comprehensive/visualizations/test_dashboard_builder.py:L150-L150] | 1 | Optional dashboard/mock incompatibility |
| `test_with_dropdown` [tests/unit/bsee/reports/comprehensive/visualizations/test_dashboard_builder.py:L163-L163] | 1 | Optional dashboard/mock incompatibility |
| `test_with_date_filter` [tests/unit/bsee/reports/comprehensive/visualizations/test_dashboard_builder.py:L170-L170] | 1 | Optional dashboard/mock incompatibility |
| `test_empty_filters` [tests/unit/bsee/reports/comprehensive/visualizations/test_dashboard_builder.py:L177-L177] | 1 | Optional dashboard/mock incompatibility |
| `test_basic` [tests/unit/bsee/reports/comprehensive/visualizations/test_geographic_charts.py:L124-L126] | 1 | Existing dependency API incompatibility |
| `test_custom_columns` [tests/unit/bsee/reports/comprehensive/visualizations/test_geographic_charts.py:L139-L141] | 1 | Existing dependency API incompatibility |
| `test_custom_title` [tests/unit/bsee/reports/comprehensive/visualizations/test_geographic_charts.py:L156-L158] | 1 | Existing dependency API incompatibility |
| `test_basic` [tests/unit/bsee/reports/comprehensive/visualizations/test_production_charts.py:L205-L207] | 1 | Existing dependency API incompatibility |
| `test_npv_accuracy_requirements_validation` [tests/modules/bsee/analysis/npv-data-source-comparison/test_npv_integration_workflow.py:L439-L447] | 2 | Required data or templates unavailable |

Skipped class-level nodes for the planned configuration interface (15 existing tests):

- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_init_with_config_file` [tests/unit/bsee/data/config/test_config_router.py:L49-L54]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_init_without_config_file` [tests/unit/bsee/data/config/test_config_router.py:L56-L60]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_load_config` [tests/unit/bsee/data/config/test_config_router.py:L62-L69]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_load_config_invalid_file` [tests/unit/bsee/data/config/test_config_router.py:L71-L76]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_get_config_value` [tests/unit/bsee/data/config/test_config_router.py:L78-L85]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_get_config_value_with_default` [tests/unit/bsee/data/config/test_config_router.py:L87-L96]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_set_config_value` [tests/unit/bsee/data/config/test_config_router.py:L98-L108]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_validate_config` [tests/unit/bsee/data/config/test_config_router.py:L110-L120]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_merge_configs` [tests/unit/bsee/data/config/test_config_router.py:L122-L139]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_export_config` [tests/unit/bsee/data/config/test_config_router.py:L141-L155]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_config_sections` [tests/unit/bsee/data/config/test_config_router.py:L157-L168]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_config_iteration` [tests/unit/bsee/data/config/test_config_router.py:L170-L178]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_config_update_and_reload` [tests/unit/bsee/data/config/test_config_router.py:L180-L191]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_config_with_environment_variables` [tests/unit/bsee/data/config/test_config_router.py:L193-L202]
- `tests/unit/bsee/data/config/test_config_router.py::TestConfigRouter::test_config_type_conversion` [tests/unit/bsee/data/config/test_config_router.py:L205-L219]
