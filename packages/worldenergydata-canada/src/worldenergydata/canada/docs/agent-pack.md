# Canada module knowledge pack

| Header | Value |
|---|---|
| Module | canada |
| Repository | worldenergydata |
| Package path | `packages/worldenergydata-canada/src/worldenergydata/canada` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `285d65c40896b17ccf44568e59f5b789d59c943e` |
| Analysis family | Data pipeline; QA family EC; AQG r0 Python calculations |
| Quality role | Calculations family quality manager |
| Status | DRAFT |

The code revision pins repository citations; test outcomes below are observations on that revision, rather than claims of external data accuracy.

## 1. Purpose and scope

`Canada.router` validates configuration, calls the provincial collection facades, optionally runs analysis, and returns status and record counts in the configuration. [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L65-L116]

The package also implements UWI parsing and record validation, HTTP clients, response/file caches, offshore text/HTML parsing, discovery filtering, and a delegated production-to-economics chain. [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L254-L287] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L733-L825] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L393-L430] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L457-L574] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L374-L395] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L64-L102] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L42-L81]

Scope includes all subpackages; the collection facades return empty lists for unimplemented paths, and cross-provincial comparative analyses return pending markers or zero totals rather than computed production comparisons. [packages/worldenergydata-canada/src/worldenergydata/canada/aer/aer.py:L97-L164] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/bcer.py:L147-L223] [packages/worldenergydata-canada/src/worldenergydata/canada/analysis/analysis.py:L124-L236]

Treat completion status as control-flow completion, with record counts inspected separately; it does not establish successful acquisition. [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L101-L109] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/aer.py:L51-L67]

The member declares development status Alpha; its runtime export declares a different version string from the distribution metadata, so neither is a validation rating. [packages/worldenergydata-canada/pyproject.toml:L5-L18] [packages/worldenergydata-canada/src/worldenergydata/canada/__init__.py:L63-L64]

## 2. Inputs and outputs

### Inputs

| Name / route | Unit / convention | Allowed range / default | Source and evidence |
|---|---|---|---|
| `Canada.router(cfg)` | Configuration mapping; no physical frame | Nonempty; provinces `ab`, `alberta`, `bc`, `british_columbia`; default province list `ab`, `bc` | Caller; validation lowercases for membership but dispatch uses original strings (section 6). [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L77-L89] [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L175-L220] |
| `api.rate_limit`, `api.cache_ttl` | requests/s; s | Router requires rate greater than 0 and TTL at least 0 | Caller configuration; this validation does not connect the stub facades to the HTTP clients. [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L222-L237] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/aer.py:L32-L36] |
| `UWIParser.parse(uwi)` | Identifier text, DLS/NTS; not geographic coordinates | `strict=False`; DLS component integer limits checked after matching | Caller; separated and compact regexes plus component checks. [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L152-L232] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L244-L287] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L525-L578] |
| `validate_coordinates(latitude, longitude, province)` | Decimal degrees, documented NAD83; signed latitude/longitude | Latitude -90 to 90 degrees; longitude -180 to 180 degrees, then approximate national/provincial bounding boxes | Caller; these are bounding-box predicates, not a datum transformation. [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L174-L227] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L329-L451] |
| `BCERClient` bbox | `(xmin, ymin, xmax, ymax)` in WGS84; `inSR=4326` | Four values if supplied; query defaults `where="1=1"`, `out_fields="*"` | Caller; output geometries are assigned EPSG:3005 by `query_wells`. [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L435-L455] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L485-L500] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L687-L705] |
| `AERClient`, `BCERClient` settings | rate requests/s; timeout, delay and TTL s; retries count | Endpoint defaults: rates 5 / 10, TTL 86400 / 86400, timeouts 60 / 30, retries 3 / 3 | Endpoint mappings; AER class timeout is 120 s but constructor selects endpoint timeout by default. [packages/worldenergydata-canada/src/worldenergydata/canada/endpoints.py:L258-L275] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L95-L158] |
| `parse_cnloer_production_text(text, field_name=...)` | Monthly text: oil/water m3 and bbl; gas thousand m3 and MMscf | Month name and positive year; at least three volume numbers; no default field identifier | Caller-supplied extracted text; no raw regulator document is reproduced here. [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L101-L167] |
| `CnloerProductionLoader` | Injected text or historical HTML; otherwise local PDF path | HTML covers the five coded annual modals; PDF wins overlapping periods | Caller; subprocess requires `pdftotext` only for the PDF-path route. [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L321-L347] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L361-L405] |
| `DiscoverySchema` / discovery CSV | `WATER_DEPTH_M` m; `DISCOVERY_YEAR` calendar year; resource estimate text, basis separate | Depth greater than 0 and at most 4000 m; year 1990–2035; enums and required text checked | CSV reader and Pydantic validators; no universal unit is assigned to free-text resource estimates. [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L44-L58] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discovery_schema.py:L48-L167] |
| `run_canada_reference_chain` | Production query dates; oil price USD/bbl; metadata water depth m | `start=None`, `end=None`, oil price 75 USD/bbl | Caller; assumptions and depth classification delegated to downstream modules. [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L32-L70] [packages/worldenergydata-canada/src/worldenergydata/canada/field_concept.py:L35-L57] |

### Outputs

| Name / route | Unit / format | Range / absent-value semantics | Evidence |
|---|---|---|---|
| Router status and `data_collected` | Mapping; count records | Lists/dicts counted by length; scalar item counts as 1 | [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L101-L106] [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L152-L173] |
| `UWIComponents`, `ValidationResult` | Dataclass/dict; booleans and error/warning lists | Invalid parse may return components; warnings alone preserve validity | [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L82-L126] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L54-L118] |
| HTTP payloads | AER GET bytes / downloaded CSV DataFrame; BCER feature list / GeoDataFrame | BCER conversion requires geopandas; missing dependency raises structured data error | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L413-L430] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L549-L561] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L576-L660] |
| Offshore production rows | `field_name`, `year`, `month`, `oil_bbl`, `gas_mcf`, `water_bbl` | One row per year/month after accumulation, sorted; condensate absent | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L123-L167] |
| Fixture metadata / production | JSON / CSV; source marker `cnloer_fixture_synthetic` | Case-insensitive field filter; fixture, not observed regulator production | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L408-L436] [tests/unit/canada/production/test_cnloer_loader.py:L100-L111] |
| Reference-chain dictionary | Unified and FDAS frames, concept ranking, pre-tax USD metrics and month count | Label `chain_plumbing_pre_tax`; depth classifier provenance retained | [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L72-L101] |

No wave phase or solver coordinate convention is assigned by these routes; the spatial interfaces above use latitude/longitude or CRS-labelled geometry. [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L329-L451] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L827-L872]

## 3. Method and governing standards

| Method | Implementation and limits | Reference basis |
|---|---|---|
| UWI parsing and formatting | Regex identification, DLS integer-range checks, canonical formatting; NTS defaults province to BC, while DLS province is inferred from meridian | Code-defined rules; docstring names AER Directive 059, *Well Drilling and Completion Data Filing Requirements*, and CAPP Well Naming Convention without edition or clause. [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L25-L28] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L289-L370] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L405-L442] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L525-L597] |
| Record validation | Delegates UWI checks; validates coordinate boxes, province/status/fluid enumerations, dates and licence number patterns; merges results | Code predicates, not survey boundary certification. [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L263-L301] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L329-L451] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L589-L799] |
| HTTP retry and paging | Rate interval reciprocal of configured rate; retry loop includes initial attempt; 429 uses Retry-After, server/network errors use exponential delay; BCER accumulates pages | Existing client algorithms; file download uses direct request and status check rather than the retry wrapper. [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L145-L147] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L294-L391] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L468-L509] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L508-L574] |
| Cache expiry | Memory entry expires when elapsed time exceeds TTL; file freshness uses age less than max age; file lookup alone does not test freshness | Implementation conventions; not source identity or integrity verification. [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L22-L32] [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L194-L238] |
| Offshore text transformation | Per-period addition of recognized monthly rows; six or more volume columns select imperial positions, otherwise metric conversion; no parsed rows raises error | Module delegates conversion constants to common units; comment names API MPMS Chapter 11 without edition or clause title. [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L39-L48] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L123-L189] |
| Historical HTML transformation | Checks header units, monthly uniqueness and full annual coverage, selects explicit total rows, excludes cumulative rows, then delegates to text parser | Code-defined modal schema; overlap keeps PDF-derived periods first. [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L248-L268] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L269-L318] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L321-L347] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L374-L395] |
| Discovery query | Validates CSV records, then filters country/block/tier/status exactly, operator by case-insensitive substring, and depth by minimum | Schema and local dataset; missing file returns empty list and is cached as empty. [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L44-L102] |
| Field concept and reference chain | Metadata mapping delegates to FDAS normalizer; chain delegates conversion, recommendation and monthly cash flow, then sums cashflow attributes | This module is a consumer of those algorithms; the depth-only concept is a documented limitation, #815 and #818. [packages/worldenergydata-canada/src/worldenergydata/canada/field_concept.py:L35-L67] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L42-L101] |

UNVERIFIED: U1 — normative editions, clause titles, and independent authority for the UWI conventions and bounding boxes have not been established; clause text not checked against the licensed copy; issue pending (6). [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L25-L28] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L174-L227]

UNVERIFIED: U2 — the conversion comments do not establish a checked standard edition or clause, and tests importing the implementation constants do not independently validate those constants; clause text not checked against the licensed copy; issue pending (6). [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L39-L48] [tests/unit/canada/production/test_cnloer_loader.py:L76-L80]

## 4. Validated worked examples

Validated examples: **0**. The retained cases below are regression examples with synthetic or implementation-derived expectations; an independently sourced physical benchmark remains issue pending (6).

Results record the offline baseline and repeated run at the header code revision; no network retrieval, PDF binary, solver or licensed interface is needed by these six nodes.

| Case | Source / input | Expected result and tolerance basis | Existing test node ID | Offline result |
|---|---|---|---|---|
| R1 imperial selection | Inline synthetic monthly text | 2 monthly rows; selected first oil/water cells retained; gas uses the source MMscf column; existing assertions use `pytest.approx`, not an independent standard | `tests/unit/canada/production/test_cnloer_loader.py::test_parse_prefers_imperial_columns_and_drops_header_and_blank_month` | BASE PASS; AFTER PASS. [tests/unit/canada/production/test_cnloer_loader.py:L45-L63] |
| R2 reservoir addition | Two inline synthetic subrows | 1 row; oil 18870 bbl and water 6290 bbl from addition of source cells; existing assertions use `pytest.approx` | `tests/unit/canada/production/test_cnloer_loader.py::test_parse_sums_reservoir_subrows_per_month` | BASE PASS; AFTER PASS. [tests/unit/canada/production/test_cnloer_loader.py:L66-L73] |
| R3 metric branch | Inline synthetic metric-only text | Oil and gas equal inputs multiplied by imported conversion constants; regression tolerance is the existing `pytest.approx` assertion | `tests/unit/canada/production/test_cnloer_loader.py::test_parse_falls_back_to_metric_columns` | BASE PASS; AFTER PASS. [tests/unit/canada/production/test_cnloer_loader.py:L76-L80] |
| R4 annual HTML normalization | Generated synthetic modal tables | 60 monthly rows; annual total equals 12 times synthetic monthly total times the imported conversion constant; cardinality exact, values use `pytest.approx` | `tests/unit/canada/production/test_cnloer_html.py::test_parser_normalizes_five_modal_tables_and_annual_total` | BASE PASS; AFTER PASS. [tests/unit/canada/production/test_cnloer_html.py:L74-L90] |
| R5 overlap precedence | Generated synthetic HTML plus two inline text rows | 61 rows, 0 duplicate year/month keys; last 2 rows equal text-only parse using `assert_frame_equal` | `tests/unit/canada/production/test_cnloer_html.py::test_combined_loader_preserves_pdf_overlap_and_continuous_junction` | BASE PASS; AFTER PASS. [tests/unit/canada/production/test_cnloer_html.py:L127-L139] |
| R6 delegated-chain repeatability | Injected two-month loader and metadata | 0 differences in ranked concept-type sequence between two calls; no numerical economic benchmark asserted | `tests/unit/canada/test_reference_chain.py::test_reference_chain_is_deterministic` | BASE PASS; AFTER PASS. [tests/unit/canada/test_reference_chain.py:L70-L84] |

The arithmetic totals in R2 describe synthetic cells rather than a field observation; no identifying record value is reproduced from a regulator document. [tests/unit/canada/production/test_cnloer_loader.py:L30-L36] [tests/unit/canada/production/test_cnloer_loader.py:L66-L73]

## 5. QA gates

Apply AQG r0 section 10, Python calculations, using G0 inputs/units/citations, G1 imports/tests, G2 hand or published checks and G5 evidence; G3 and G4 are not applicable to this data pipeline. (AQG r0, sections 9–11, Python calculations.)

Criteria below define checks; a passing documentation check does not clear a failing runtime gate.

| Gate | Applicability and route | Module-specific check and numeric pass criterion | Evidence / observed status |
|---|---|---|---|
| G0 | Applicable; configuration validation | C0.1: `Canada._validate_config` rejects rate 0 requests/s with exactly 1 `ValueError` | Existing test `TestValidateConfig::test_invalid_api_rate_limit_zero`: PASS. [tests/unit/canada/test_canada.py:L59-L62] |
| G0 | Applicable; UWI validation | C0.2: strict `UWIParser.parse` rejects the out-of-range legal subdivision with exactly 1 `UWIParseError` | `TestUWIParserStrictMode::test_strict_invalid_lsd_raises`: PASS. [tests/unit/canada/common/test_uwi_parser.py:L292-L294] |
| G0 | Applicable; degree-range validation | C0.3: `validate_coordinates(100.0, -113.0)` produces at least 1 `COORD_RANGE` error; latitude input unit degrees | `TestCanadaDataValidatorCoordinates::test_latitude_out_of_range`: PASS. [tests/unit/canada/common/test_validators.py:L176-L179] |
| G0 | Applicable; source separation | C0.4: `CnloerFixtureLoader.metadata` includes the synthetic marker and 0 returned records have a source other than `cnloer_fixture_synthetic` | `test_fixture_loader_is_labeled_synthetic_with_licence_provenance`: PASS. [tests/unit/canada/production/test_cnloer_loader.py:L100-L111] |
| G1 | Applicable; Python import and offline pytest, no target solver input | C1.1: module tests and dedicated adapter contract collect 444 nodes and have 0 failed tests | BASE and AFTER: 425 passed, 19 failed during cache-directory creation. This gate remains FAIL for this environment. [tests/unit/canada/aer/test_api_client.py:L13-L55] [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L146-L164] |
| G1 | Applicable; parser rejection | C1.2: malformed HTML variants cause exactly 1 `CnloerParseError` each across 11 parameterized variants | `test_malformed_modal_raises_existing_parse_error`: all 11 PASS. [tests/unit/canada/production/test_cnloer_html.py:L99-L119] |
| G2 | Applicable; independent arithmetic on synthetic cells | C2.1: `parse_cnloer_production_text` R2 totals minus hand additions equal 0.0 bbl for oil and water | Hand check plus R2 PASS; tests alone use approximate equality. This checks accumulation, not unit-factor provenance. [tests/unit/canada/production/test_cnloer_loader.py:L30-L36] [tests/unit/canada/production/test_cnloer_loader.py:L66-L73] |
| G2 | Applicable; period cardinality and precedence | C2.2: HTML-only returns 60 rows; combined loader returns 61 rows with 0 duplicated monthly keys | R4 and R5 PASS. [tests/unit/canada/production/test_cnloer_html.py:L74-L90] [tests/unit/canada/production/test_cnloer_html.py:L127-L139] |
| G2 | Applicable; independent record counting | C2.3: `Canada._summarize_data` returns 3 well records and 2 production records for the inline lists | `TestSummarizeData::test_list_data`: PASS. [tests/unit/canada/test_canada.py:L103-L111] |
| G3 | NOT_APPLICABLE | Short dynamics: 0 dynamic simulation routes in this pack's workflow | Route is collection, parsing and delegated cashflow. [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L77-L106] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L42-L81] |
| G4 | NOT_APPLICABLE | Diffraction: 0 diffraction-model or mesh outputs in this pack's workflow | Outputs are dataframes, concepts and pre-tax metrics. [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L72-L101] |
| G5 | Applicable; evidence and traceability | C5.1: resolve all pack repository citations at the code pin with 0 missing files, 0 invalid line intervals; read 10 supporting passages manually | Citation audit, cited-source byte manifest and ten-passage record retained with review evidence. |
| G5 | Applicable; example accountability | C5.2: 6 of 6 section-4 node IDs have an explicit BASE/AFTER result; baseline and repeated outcome sets differ by 0 nodes | Node results and SHA-256 of sorted source-path/digest lines retained with review evidence. |

For C2.1, read the two synthetic rows, add their imperial oil and water cells outside the implementation, then compare those sums with the parser output; no unit constant is needed. [tests/unit/canada/production/test_cnloer_loader.py:L30-L36] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L145-L149]

For C5.1, resolve every bracketed repository path and line range through `git show <code revision>:<path>`; retain the source SHA-256 and the ten manually checked passages, then attach the record to the review. For C5.2, compare sorted pytest node/status pairs, rather than comparing console progress lines.

## 6. Known failure modes and pitfalls

The issues below are references and follow-ups, not a claim that each historical request is an unresolved incident.

| Symptom / cause | Detection or missing detection | Incident / tracking | Evidence at the pin |
|---|---|---|---|
| Silent empty provincial collection: facade collectors are stubs; router still marks completed | No live-acquisition detection check exists; add a mocked nonempty route acceptance test requiring at least 1 returned record and surfaced acquisition errors | issue pending (2) | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/aer.py:L97-L164] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/bcer.py:L147-L223] [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L101-L106] |
| Unknown analysis type silently selects summary; comparative routes retain placeholders | Existing placeholder tests verify structure, not production comparison accuracy; no completed-analysis accuracy detection check exists | issue pending (2) | [packages/worldenergydata-canada/src/worldenergydata/canada/analysis/analysis.py:L82-L91] [packages/worldenergydata-canada/src/worldenergydata/canada/analysis/analysis.py:L124-L236] [tests/unit/canada/analysis/test_analysis.py:L87-L117] |
| Router overwrites the caller's basename mapping before processing | No preservation detection check exists; require 0 lost sentinel keys in a mocked router call | #431 | [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L69-L75] |
| Uppercase province passes validation but does not dispatch; pipeline type is mapped for BC but rejected by top-level validator | No case-parity or pipeline-route detection check exists; require equal route counts for uppercase/lowercase and 1 accepted pipeline route | issue pending (2) | [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L82-L89] [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L194-L220] [packages/worldenergydata-canada/src/worldenergydata/canada/endpoints.py:L329-L333] |
| AER default client initialization creates a file cache immediately; restricted directories cause an exception before most assertions | C1.1 exposes 19 BASE failures; exact unsanitized errors remain in local evidence; public error category `OSError: [Errno 30] Read-only file system` | issue pending (1) | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L149-L158] [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L146-L164] [tests/unit/canada/aer/test_api_client.py:L13-L55] |
| AER well lookup strips slashes from requested UWI but not from CSV UWI values; its client validator accepts a broader character set than `UWIParser` | No equivalence detection check exists; require exactly 1 match for equivalent slash/compact inputs and 0 accepted malformed identifiers | issue pending (3) | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L735-L766] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L785-L796] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L155-L180] |
| BCER cache key omits requested output fields, geometry flag and page size; cached path does not trim to the total-record limit | No cache-isolation detection check exists; use mocked pages, demand requested columns and result count at most the caller's limit | issue pending (3) | [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L508-L535] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L549-L566] |
| Retry counts/TTL/rate supplied as zero may select defaults because constructors use `or`; downloads bypass retry wrapper | No zero-override and download-retry detection check exists; request exactly 0 retries and compare calls with 1 initial attempt | issue pending (3); HTTP consolidation context #431 | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L126-L146] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L468-L509] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L137-L165] |
| Text parser sums all same-period numeric rows, including an explicit total if present alongside subrows; short malformed rows drop silently and four/five volume columns enter metric branch | R1 detects a deliberately blank month; no explicit-total double-count or ambiguous-width rejection detection check exists; require 1 total per month and 0 silently accepted ambiguous layouts | issue pending (4) | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L123-L149] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L170-L189] [tests/unit/canada/production/test_cnloer_loader.py:L45-L73] |
| Record validator accepts an empty record and ignores a partial coordinate pair; `strict` is stored without promoting warnings | Existing tests pin empty-record acceptance; no required-fields, partial-coordinate or strict-promotion detection check exists | issue pending (5) | [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L253-L261] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L733-L799] [tests/unit/canada/common/test_validators.py:L427-L429] |
| Missing discovery CSV logs a warning, returns an empty list and keeps that empty result | No missing-then-restored-file detection check exists; require an explicit unavailable-data status rather than accepting 0 records as success | issue pending (5) | [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L44-L58] |
| Depth-only development classification and fallback metadata are incomplete substitutes for actual development concept | No concept-override detection check exists; R6 only checks repeatability | #815, #818 | [packages/worldenergydata-canada/src/worldenergydata/canada/field_concept.py:L46-L57] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L59-L70] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L98-L101] |
| Runtime download/refresh and public redistribution rights remain separate from parser success | C0.4 keeps synthetic source visible; no legal-eligibility detection check exists | #814, #819 | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L15-L23] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L350-L358] |
| Legacy gas-only ingestion and complete gas economics are outside this chain's recorded oil-revenue aggregation | No gas-only chain detection check exists | #816 | [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L54-L70] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L91-L101] |
| Historical modal-parser request already has an implementation and offline synthetic coverage | C1.2, C2.2; do not describe the parser as absent merely because the request remains open | #817 | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L321-L347] [tests/unit/canada/production/test_cnloer_html.py:L74-L119] |

## 7. Lessons log

Append future evidence-backed lessons without replacing earlier entries; use a public change reference and omit identifying dataset names.

| Date | Change reference | Lesson | Evidence | Pack change | Shared entry |
|---|---|---|---|---|---|
| 2026-10-15 | Initial pack revision 0 | Keep collection-facade completion separate from nonempty acquisition | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/aer.py:L97-L125] [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L101-L106] | Sections 1, 5 and 6 distinguish these outcomes | Pending, issue pending (7) |
| 2026-10-15 | Initial pack revision 0 | Synthetic metric conversion checks reuse implementation factors, so do not establish independent validation | [tests/unit/canada/production/test_cnloer_loader.py:L76-L80] | Sections 3–5 identify the validation gap | Pending, issue pending (6) |

## 8. Ownership

Review assignment: calculations family quality manager; deputy role to be designated by the maintainer; producing discipline: data pipelines and calculations. Submit unresolved criteria, provenance and reference-data questions to that quality role, then refer cross-family scope questions to the maintainer. This is a proposed assignment, not a completed clearance; issue pending (7).

Keep status DRAFT until independent review, missing issue numbers and reference limitations are disposed of; do not infer clearance from passing regression examples.

## 9. Dependencies and implementation inventory

### Runtime dependencies and consumers

| Relationship | Concrete dependency / route | Version or dataset basis | Evidence |
|---|---|---|---|
| Distribution upstream | `worldenergydata-core`, pandas | Member requires pandas at least 2.3.3 and below 3.0, Python at least 3.10 | [packages/worldenergydata-canada/pyproject.toml:L5-L10] [packages/worldenergydata-canada/pyproject.toml:L28-L35] |
| Runtime imports | requests, optional geopandas/shapely, Pydantic | Requests and geopandas are guarded imports; discovery schema requires Pydantic | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L30-L40] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L29-L45] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discovery_schema.py:L19-L21] |
| Common units/errors/data lookup | Shared units registry, `ModuleError`, safe module-data resolver | Code pinned with this pack, not an independently qualified standard sidecar | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L39-L48] [packages/worldenergydata-canada/src/worldenergydata/canada/errors.py:L35-L53] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L27-L34] |
| Local production fixture | `cnloer_fixture_synthetic` | CSV and metadata through package resources; not live observations | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L88-L90] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L408-L436] |
| Discovery dataset | `frontier_basins` dataset ID | CSV through common resolver; schema validates records, not source freshness | [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L27-L58] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discovery_schema.py:L70-L73] |
| PDF-path optional executable | `pdftotext -layout` | Version not constrained by this wrapper; injected-text route avoids executable | [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L397-L405] |
| Downstream adapter | `CanadaAdapter` | Loads injected rows or synthetic fixture, normalizes standard columns and filters query | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/canada_adapter.py:L28-L35] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/canada_adapter.py:L57-L101] |
| Downstream calculations | FDAS production conversion, metadata normalizer, cashflow engine; development recommendation | Called by reference chain; cashflow assumptions are delegated | [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L42-L81] [packages/worldenergydata-canada/src/worldenergydata/canada/field_concept.py:L46-L67] |

### Map inventory and counted-family audit

Map evidence: `digitalmodel`, `docs/registry/implementation-map.yaml`, ref `origin/codex/implmap-work` at commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, map data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`; record the ref commit and data revision separately when repeating this audit.

The parsed map has 13 families and **0 implementation rows** whose path lies inside this pack's package; therefore the module-family inventory is empty, ranking selects 0 counted families, and the counted-family search is **NOT_APPLICABLE** because no family has an in-package row. The audit result is PASS for the empty inventory; this does not certify method completeness in the map. (Implementation-map inventory audit at the map revision above; issue pending (7).)

| Module map family | Listed in-package implementations | Counted-family search |
|---|---|---|
| None at the recorded map revision | Empty inventory | NOT_APPLICABLE: no in-package implementation rows |

Map follow-up: add UWI parsing/validation, record and coordinate validation, HTTP retry/pagination, TTL caches, production text/HTML parsing and unit conversion, discovery schema/filtering, summary counting, and delegated-chain aggregation from section 3 before they can become counted families; issue pending (7). [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L254-L287] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L733-L825] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L294-L391] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L457-L574] [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L22-L88] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L101-L189] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L321-L347] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L44-L102] [packages/worldenergydata-canada/src/worldenergydata/canada/analysis/analysis.py:L93-L122] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L91-L101]

### Supplementary repository search

A supplementary pinned search of every tracked Python file, including `scripts/`, used `parse_cnloer_production|CnloerProductionLoader|UWIParser|SM3_TO_BBL|def .*uwi|def .*canada`; these are discovery terms, not substituted map search signals. Findings below are map follow-up and do not change the empty-inventory result.

| Definition / location | Classification | Evidence and follow-up |
|---|---|---|
| `UWIParser` and `AERClient._validate_uwi` | Two independent validation criteria within the package; both inventoried in section 3 | The latter only checks allowed characters, not component semantics; issue pending (3). [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L525-L578] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L785-L796] |
| `common.uwi` wrappers and `CanadaDataValidator.validate_uwi` | Helpers delegating to `UWIParser` | Not further UWI parsers. [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi.py:L33-L48] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi.py:L64-L95] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L284-L299] |
| CLI `validate_uwi` | Independent parser outside package: fixed slicing and its own numeric/range checks | Map gap; issue pending (7). [src/worldenergydata/cli/commands/canada.py:L464-L505] [src/worldenergydata/cli/commands/canada.py:L523-L556] |
| Production HTML helper and `CnloerProductionLoader.load` | Distinct HTML schema check, followed by delegation to text parser | Not a second implementation of text volume extraction. [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L321-L347] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L374-L395] |
| `CanadaAdapter._loader_to_standard_columns` | Serialization/normalization helper outside package | Not a second source text parser. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/canada_adapter.py:L74-L93] |
| Core units registry and pipeline adapter `m3_to_barrels` | Shared conversion registry and another conversion implementation outside package | No numerical equivalence claimed; map gap, issue pending (7). [packages/worldenergydata-core/src/worldenergydata/common/units.py:L14-L25] [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/adapters/units.py:L45-L60] |
| `canada_field_to_concept`, `build_canada_field_concept`, reference chain | Delegation to FDAS normalizer, classifier and cashflow engine, plus local attribute summation | Keep downstream formulas out of this module's independent-implementation count. [packages/worldenergydata-canada/src/worldenergydata/canada/field_concept.py:L46-L67] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L42-L101] |

## 10. Coverage and open items

### Read coverage

All 28 package Python files were inspected at the code pin; the following inventory lists leaf implementations and package exports separately.

| Area | Files / inspected content | Evidence |
|---|---|---|
| Top level | `__init__.py`, `canada.py`, `cache.py`, `endpoints.py`, `errors.py`, `field_concept.py`, `reference_chain.py` | [packages/worldenergydata-canada/src/worldenergydata/canada/__init__.py:L34-L89] [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L45-L276] [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L22-L318] [packages/worldenergydata-canada/src/worldenergydata/canada/endpoints.py:L258-L333] [packages/worldenergydata-canada/src/worldenergydata/canada/errors.py:L38-L605] [packages/worldenergydata-canada/src/worldenergydata/canada/field_concept.py:L35-L67] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L32-L101] |
| AER | `aer/__init__.py`, `aer.py`, `api_client.py`, `data/__init__.py` | [packages/worldenergydata-canada/src/worldenergydata/canada/aer/__init__.py:L23-L26] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/aer.py:L20-L238] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L56-L888] [packages/worldenergydata-canada/src/worldenergydata/canada/aer/data/__init__.py:L19-L20] |
| BCER | `bcer/__init__.py`, `bcer.py`, `api_client.py`, `data/__init__.py` | [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/__init__.py:L22-L25] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/bcer.py:L22-L357] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L60-L943] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/data/__init__.py:L19-L20] |
| Common | `common/__init__.py`, `uwi.py`, `uwi_parser.py`, `validators.py` | [packages/worldenergydata-canada/src/worldenergydata/canada/common/__init__.py:L13-L25] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi.py:L17-L111] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L129-L641] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L121-L825] |
| Analysis and processors | `analysis/__init__.py`, `analysis.py`, `processors/__init__.py` | [packages/worldenergydata-canada/src/worldenergydata/canada/analysis/__init__.py:L22-L24] [packages/worldenergydata-canada/src/worldenergydata/canada/analysis/analysis.py:L17-L260] [packages/worldenergydata-canada/src/worldenergydata/canada/processors/__init__.py:L20-L21] |
| Production | `production/__init__.py`, `cnloer_loader.py` | [packages/worldenergydata-canada/src/worldenergydata/canada/production/__init__.py:L6-L16] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L97-L436] |
| Emerging basins | `emerging_basins/__init__.py`, `discoveries.py`, `discovery_schema.py`, `watch_list.py` | [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/__init__.py:L15-L33] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L37-L102] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discovery_schema.py:L48-L167] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/watch_list.py:L22-L46] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/watch_list.py:L129-L154] |

Package README and watch-list documentation were inspected; identifying record names and estimates are intentionally not transcribed. [packages/worldenergydata-canada/README.md:L1-L8] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/WATCH_LIST.md:L1-L5]

The documentation search included country-name matches to avoid missing renamed module references; only module-related passages inform this pack, while geographic references in other domains supply no module-behavior evidence.

| Documentation search hit | Pinned passage |
|---|---|
| `docs/CLI.md` | [docs/CLI.md:L561-L565] |
| `docs/research/marine_safety_data_sources_verification_report.md` | [docs/research/marine_safety_data_sources_verification_report.md:L458-L462] |
| `docs/guides/user_prompt.md` | [docs/guides/user_prompt.md:L157-L161] |
| `docs/ci/flake8-inventory-2026-04-23.md` | [docs/ci/flake8-inventory-2026-04-23.md:L78-L82] |
| `docs/data-sources/MARINE_SAFETY_IMPORT_STATUS.md` | [docs/data-sources/MARINE_SAFETY_IMPORT_STATUS.md:L130-L134] |
| `docs/data-sources/PHASE_2_IMPORT_COMPLETE.md` | [docs/data-sources/PHASE_2_IMPORT_COMPLETE.md:L3-L7] |
| `docs/modules/lng/lng_market.md` | [docs/modules/lng/lng_market.md:L34-L38] |
| `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md` | [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L125-L129] |
| `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L19-L23] |
| `docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md` | [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L13-L17] |
| `docs/modules/repository-architecture.md` | [docs/modules/repository-architecture.md:L117-L121] |
| `docs/adr/0001-domain-package-split.md` | [docs/adr/0001-domain-package-split.md:L46-L50] |
| `docs/modules/marine_safety/cause_mapping_reference.md` | [docs/modules/marine_safety/cause_mapping_reference.md:L610-L614] |
| `docs/plans/2026-05-04-issue-275-ast-aware-logger-script.md` | [docs/plans/2026-05-04-issue-275-ast-aware-logger-script.md:L29-L33] |
| `docs/modules/marine_safety/incident_cause_research.md` | [docs/modules/marine_safety/incident_cause_research.md:L4-L8] |
| `docs/modules/marine_safety/INCIDENT_CAUSE_ANALYSIS_MODULE.md` | [docs/modules/marine_safety/INCIDENT_CAUSE_ANALYSIS_MODULE.md:L14-L18] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L14-L18] |
| `docs/modules/marine_safety/LLM_INTEGRATION_COMPLETE.md` | [docs/modules/marine_safety/LLM_INTEGRATION_COMPLETE.md:L252-L256] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L30-L34] |
| `docs/reports/cli-smoke-report-2026-05-11.md` | [docs/reports/cli-smoke-report-2026-05-11.md:L23-L27] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L99-L103] |
| `docs/reports/data-freshness-scorecard-2026-06-08.md` | [docs/reports/data-freshness-scorecard-2026-06-08.md:L5-L9] |
| `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` | [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L66-L70] |
| `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` | [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L10-L14] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L16-L20] |
| `docs/marine-safety-data-sources-comprehensive.md` | [docs/marine-safety-data-sources-comprehensive.md:L477-L481] |
| `docs/data-sources/FINAL_DATA_ACQUISITION_SUMMARY.md` | [docs/data-sources/FINAL_DATA_ACQUISITION_SUMMARY.md:L241-L245] |
| `docs/data-sources/INDUSTRIAL_MARITIME_DATA_SOURCES.md` | [docs/data-sources/INDUSTRIAL_MARITIME_DATA_SOURCES.md:L361-L365] |

### Offline test inventory and results

Command form: `uv run --extra test python -m pytest --noconftest tests/unit/canada tests/unit/production/unified/test_canada_cnloer_adapter_loader.py -q -rA -p no:cacheprovider --basetemp=<scratch>`, with coverage data and HTML/XML/JSON reports redirected to scratch. The documented `--noconftest` form was used; normal sources resolved, no `--no-sources` fallback or addopts override was used. The code pin is the header revision; both checks run on the uncommitted tree.

| Run | Collected / run | Passed | Failed | Skipped | NOT_RUN |
|---|---|---|---|---|---|
| BASE | 444 / 444 | 425 | 19 | 0 | 0 |
| AFTER | 444 / 444 | 425 | 19 | 0 | 0 |

Additional contracts check: `uv run --extra test python -m pytest --noconftest tests/contracts -q -rA -p no:cacheprovider --basetemp=<scratch>` with the same coverage-output redirection: 46 run, 46 passed, 0 failed, 0 skipped, 0 NOT_RUN at the header pin on the uncommitted tree.

The inventory below gives all 15 module test files plus the dedicated consumer file; it replaces the earlier inventory estimate with the collected count. No test file is present under this workspace member's own `tests/` folder at the pin.

| Test file | BASE passed | BASE failed | Evidence |
|---|---|---|---|
| `tests/unit/canada/aer/test_api_client.py` | 3 | 19 | [tests/unit/canada/aer/test_api_client.py:L1-L194] |
| `tests/unit/canada/analysis/test_analysis.py` | 15 | 0 | [tests/unit/canada/analysis/test_analysis.py:L1-L130] |
| `tests/unit/canada/bcer/test_api_client.py` | 26 | 0 | [tests/unit/canada/bcer/test_api_client.py:L1-L223] |
| `tests/unit/canada/bcer/test_bcer.py` | 41 | 0 | [tests/unit/canada/bcer/test_bcer.py:L1-L256] |
| `tests/unit/canada/common/test_uwi.py` | 16 | 0 | [tests/unit/canada/common/test_uwi.py:L1-L138] |
| `tests/unit/canada/common/test_uwi_parser.py` | 43 | 0 | [tests/unit/canada/common/test_uwi_parser.py:L1-L344] |
| `tests/unit/canada/common/test_validators.py` | 69 | 0 | [tests/unit/canada/common/test_validators.py:L1-L477] |
| `tests/unit/canada/emerging_basins/test_emerging_basins.py` | 54 | 0 | [tests/unit/canada/emerging_basins/test_emerging_basins.py:L1-L162] |
| `tests/unit/canada/emerging_basins/test_frontier_discoveries.py` | 19 | 0 | [tests/unit/canada/emerging_basins/test_frontier_discoveries.py:L1-L193] |
| `tests/unit/canada/production/test_cnloer_html.py` | 22 | 0 | [tests/unit/canada/production/test_cnloer_html.py:L1-L170] |
| `tests/unit/canada/production/test_cnloer_loader.py` | 7 | 0 | [tests/unit/canada/production/test_cnloer_loader.py:L1-L111] |
| `tests/unit/canada/test_cache.py` | 39 | 0 | [tests/unit/canada/test_cache.py:L1-L262] |
| `tests/unit/canada/test_canada.py` | 24 | 0 | [tests/unit/canada/test_canada.py:L1-L146] |
| `tests/unit/canada/test_errors.py` | 39 | 0 | [tests/unit/canada/test_errors.py:L1-L249] |
| `tests/unit/canada/test_reference_chain.py` | 3 | 0 | [tests/unit/canada/test_reference_chain.py:L1-L84] |
| `tests/unit/production/unified/test_canada_cnloer_adapter_loader.py` | 5 | 0 | [tests/unit/production/unified/test_canada_cnloer_adapter_loader.py:L1-L122] |

All 19 failing nodes are in `tests/unit/canada/aer/test_api_client.py`; each reaches default file-cache creation before its intended assertion. The same constructor and test calls are present at the code pin and on the inspected default-branch ref.

| Failed node suffix (append to the file above with `::`) | BASE / AFTER |
|---|---|
| `TestAERClientInit::test_default_values` | FAIL / FAIL |
| `TestAERClientInit::test_custom_rate_limit` | FAIL / FAIL |
| `TestAERClientInit::test_min_interval_positive` | FAIL / FAIL |
| `TestAERClientInit::test_custom_params` | FAIL / FAIL |
| `TestAERClientInit::test_config_dict` | FAIL / FAIL |
| `TestSetupHeaders::test_default_headers` | FAIL / FAIL |
| `TestSetupHeaders::test_custom_headers_merged` | FAIL / FAIL |
| `TestSetupHeaders::test_custom_headers_override` | FAIL / FAIL |
| `TestGenerateCacheKey::test_without_params` | FAIL / FAIL |
| `TestGenerateCacheKey::test_with_params` | FAIL / FAIL |
| `TestGenerateCacheKey::test_same_params_same_key` | FAIL / FAIL |
| `TestGenerateCacheKey::test_different_params_different_key` | FAIL / FAIL |
| `TestValidateUWI::test_valid_uwi` | FAIL / FAIL |
| `TestValidateUWI::test_strips_whitespace` | FAIL / FAIL |
| `TestValidateUWI::test_invalid_uwi` | FAIL / FAIL |
| `TestValidateUWI::test_uwi_with_e_direction` | FAIL / FAIL |
| `TestContextManager::test_enter_exit` | FAIL / FAIL |
| `TestContextManager::test_close` | FAIL / FAIL |
| `TestContextManager::test_double_close` | FAIL / FAIL |

Failure evidence: cache construction is immediate in `AERClient.__init__`, the cache constructor creates its directory, and the affected tests supply no custom directory. [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L149-L151] [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L146-L164] [tests/unit/canada/aer/test_api_client.py:L13-L55] [tests/unit/canada/aer/test_api_client.py:L87-L194]

Cited-source fingerprint: SHA-256 `f35cd12028740333e055abaf065b74e2d1912166c071eccd547508436eb326ea`, computed over sorted repository-relative cited-file paths and their pinned-byte SHA-256 values; it covers 79 cited files, not the entire installed environment. The ten manual passage checks matched the router overwrite, NTS province default, coordinate boxes, endpoint defaults, monthly addition, volume-width dispatch, HTML completeness, pre-tax aggregation, UWI normalization and missing-CSV handling.

### Open items

Each item below is assigned to the maintainer for issue assignment; a draft reference must be replaced by its eventual issue number before final clearance.

| Item | Scope and required follow-up | Tracking |
|---|---|---|
| Cache-test portability | Make default-client tests use explicit temporary caches; retain the 19 failure results and original error evidence | issue pending (1); [tests/unit/canada/aer/test_api_client.py:L13-L55] [packages/worldenergydata-canada/src/worldenergydata/canada/cache.py:L146-L164] |
| Collection/control-flow gaps | Nonempty provincial acquisition, case-normalized routing, accepted type parity and non-placeholder analysis; preserve caller configuration | issue pending (2), #431; [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L69-L89] [packages/worldenergydata-canada/src/worldenergydata/canada/canada.py:L194-L220] [packages/worldenergydata-canada/src/worldenergydata/canada/analysis/analysis.py:L124-L236] |
| Client correctness | Canonical UWI comparison, cache-key isolation, limit trimming and zero-option semantics | issue pending (3); [packages/worldenergydata-canada/src/worldenergydata/canada/aer/api_client.py:L735-L796] [packages/worldenergydata-canada/src/worldenergydata/canada/bcer/api_client.py:L508-L566] |
| Text-parser integrity | Explicit totals versus subrow duplication, malformed rows, ambiguous numeric widths and missing-month visibility | issue pending (4); [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L123-L189] |
| Validation/data-availability semantics | Strict warnings, required/partial records, unavailable discovery data, geographic inference limits | issue pending (5); [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L253-L261] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L733-L799] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L364-L365] [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L580-L597] [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discoveries.py:L44-L58] |
| U1 | UNVERIFIED: normative references, editions/clauses and coordinate-box authority; no independent authority is asserted | issue pending (6); [packages/worldenergydata-canada/src/worldenergydata/canada/common/uwi_parser.py:L25-L28] [packages/worldenergydata-canada/src/worldenergydata/canada/common/validators.py:L174-L227] |
| U2 | UNVERIFIED: conversion provenance and independently sourced benchmark; tests use implementation constants | issue pending (6); [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L39-L48] [tests/unit/canada/production/test_cnloer_loader.py:L76-L80] |
| U3 | UNVERIFIED: discovery/watch-list estimate accuracy and freshness; schema validity and source URL presence do not establish current observations | issue pending (6); [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discovery_schema.py:L63-L73] [tests/unit/canada/emerging_basins/test_frontier_discoveries.py:L139-L153] |
| Review/index/map coverage | Assign deputy, link cleared pack and lessons, map every section-3 method family; register external CLI parser and independent conversion route | issue pending (7); [src/worldenergydata/cli/commands/canada.py:L464-L505] [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/adapters/units.py:L45-L60] |
| Package-data exclusion | Existing recursive Markdown glob covers documentation; exclude knowledge packs in a separate packaging change, without changing dependencies here | issue pending (8); [packages/worldenergydata-canada/pyproject.toml:L48-L54] |
| Identifying discovery content | Use dataset IDs and schema fields in public pack updates; establish codenames before naming individual discovery records or identifying discovery files | issue pending (6); [packages/worldenergydata-canada/src/worldenergydata/canada/emerging_basins/discovery_schema.py:L53-L61] |
| Live retrieval and rights | Source retrieval, refresh and permission for redistribution are not demonstrated by synthetic parser results | #814, #819; [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L15-L23] [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L350-L358] |
| Concept/depth and gas coverage | Replace fallback metadata/depth-only development choice where appropriate; extend legacy gas ingestion and economics | #815, #816, #818; [packages/worldenergydata-canada/src/worldenergydata/canada/field_concept.py:L46-L57] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L54-L101] |
| Historical HTML disposition | Reconcile the open request with the already implemented offline parser; live source completeness remains separate | #817; [packages/worldenergydata-canada/src/worldenergydata/canada/production/cnloer_loader.py:L321-L347] [tests/unit/canada/production/test_cnloer_html.py:L74-L90] |
| Inventory/readiness documentation | Reconcile historical readiness summaries with current nonempty routes and evidence rather than adopting their maturity labels | #349, #918; [docs/reports/data-freshness-scorecard-2026-06-08.md:L1-L7] [docs/modules/repository-architecture.md:L113-L120] |

Registry observation: `docs/registry/module-routing.yaml` is absent at the code pin, so this change adds no routing entry; the pack index remains follow-up under issue pending (7). No private sidecar entry is needed for the synthetic examples retained here.
