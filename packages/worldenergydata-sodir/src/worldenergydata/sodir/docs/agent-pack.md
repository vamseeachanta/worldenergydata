# SODIR module knowledge pack

| Header | Value |
| --- | --- |
| Module | `sodir` |
| Repository | `worldenergydata` |
| Package | `packages/worldenergydata-sodir/src/worldenergydata/sodir` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `55991b0def0f90708b3e0c396c0f57d9d1b7f7fb` |
| Analysis family | Data pipeline; AQG r0 Python calculations gate set |
| QA family | EC |
| Quality manager role | Calculations quality manager, interim data-pipeline coverage |
| Status | DRAFT; independent clearance pending |

The code revision pins every repository citation below; execution results and search inventories are observations of that tree, rather than upstream data certification.

## 1. Purpose and scope

`Sodir.router` validates configuration, dispatches CSV input to an offline workflow, otherwise collects data and optionally routes analysis, returning configuration with status and collected dataset keys. [packages/worldenergydata-sodir/src/worldenergydata/sodir/sodir.py:L34-L104]

`SodirData` dispatches five dataset IDs (`blocks`, `wellbores`, `fields`, `discoveries`, `surveys`) through processors, optional validation and filesystem storage; the newer `SodirAPIClient.query_entity` separately supports bounded feature queries for `fields`, `wellbores` and `production`. [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L53-L91] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L260-L301] [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L16-L32] [packages/worldenergydata-sodir/src/worldenergydata/sodir/api_client.py:L35-L46]

The package also implements reserve summaries, cross-regional normalization, decline fitting, economic calculations, batch operations and chart generation; these interfaces require different table schemas and are not interchangeable with processed collection lists. [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L245-L282] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cross_regional.py:L103-L140] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L112-L148] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L129-L255] [packages/worldenergydata-sodir/src/worldenergydata/sodir/batch.py:L100-L173] [packages/worldenergydata-sodir/src/worldenergydata/sodir/visualization.py:L214-L310]

The reference chain labels its economic result `chain_plumbing_pre_tax`; it supplies empty drilling costs and a fallback development system when depth classification is unknown. [packages/worldenergydata-sodir/src/worldenergydata/sodir/reference_chain.py:L27-L88]

Distribution metadata declares Alpha; the older module README calls the module production ready, a claim addressed as U3 in section 10. [packages/worldenergydata-sodir/pyproject.toml:L6-L24] [docs/modules/data_sodir/README.md:L1-L8]

## 2. Inputs and outputs

### Inputs

| Input | Unit and accepted shape/range | Default | Source |
| --- | --- | --- | --- |
| `cfg.data_types` | Dataset IDs; validator accepts the five collection IDs plus `facilities`, although the collector has no facilities route | No collection when no IDs supplied | [packages/worldenergydata-sodir/src/worldenergydata/sodir/sodir.py:L106-L163] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L93-L122] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L260-L301] |
| `api.rate_limit`, `cache_ttl`, `timeout`, `max_retries` | Requests/s, s, s, retry count; router requires positive rate and nonnegative TTL; direct transport permits rate zero | 10, 86400, 30, 3 in transport; collection forwards base, timeout and rate only | [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L64-L104] [packages/worldenergydata-sodir/src/worldenergydata/sodir/sodir.py:L106-L163] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L54-L64] |
| Feature query `entity`, `select`, `where`, `page_size`, `max_pages`, `max_bytes` | Schema property names; object ID required in selection; nonempty predicate; positive integer count/byte limits and finite positive timeout | 2 records/page, 1 page, 1048576 bytes; `where="1=1"` | [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L197-L236] [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L239-L247] |
| Raw field reserves | Code assumes million Sm3 liquids and billion Sm3 gas; nonnegative reserve validation; optional values can remain `None` | No reserve estimate substituted | [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L250-L341] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L368-L386] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L388-L406] |
| Monthly `prfYear`, `prfMonth`, liquid/gas keys | Calendar integers, million Sm3 liquids and billion Sm3 gas; legacy parser casts year/month without range validation and replaces absent or invalid volumes with zero | Year/month 0; volumes 0 | [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L86-L110] [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L173-L180] |
| Analysis tables | DataFrames: `fields`, `wellbores`, `production`, `discoveries`; loader tries `sodir_<type>.parquet`, then CSV | Missing files omitted | [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L119-L137] |
| Forecast series | Positive observations; NaNs and nonpositive values removed; at least 3 values required; time is reindexed by observation, with caller-defined period/unit | Exponential model | [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L112-L148] |
| Annual financial profile | `oil_production_mmbbl`, `gas_production_bcf`; parameters label oil price USD/bbl, gas price NOK/Sm3, exchange rate NOK/USD; capital schedule is labelled million USD but used unscaled | See parameter object; dimensional defect in section 6 | [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L30-L69] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L257-L298] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L539-L548] |

### Outputs

| Output | Unit/format and meaning | Source |
| --- | --- | --- |
| Collection result | Dataset/status/timestamp/count/data/metadata dictionary; exceptions become failed status; strict mode drops records marked invalid | [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L124-L204] |
| Field processor row | Liquid reserves MMbbl, gas Bcf, water depth m, recovery fractions rounded to 3 decimal places; cumulative water value copied without conversion | [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L52-L196] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L343-L366] |
| Wellbore row | Depth m and ft, temperature degrees C and F, drilling duration days; decimal latitude/longitude plus UTM values copied from raw keys | [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/wellbore_processor.py:L64-L160] |
| Monthly loader table | Sm3 component volumes, `oil_bbl`, and a column labelled `gas_mcf`; gas scaling and produced-water naming defects are recorded in section 6 | [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L86-L110] [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L143-L149] |
| Feature result / processor adaptation | Source attributes unchanged by query; adapter converts epoch milliseconds to UTC ISO dates; production adaptation preserves nulls and emits `water_produced_sm3` | [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L239-L288] [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L123-L153] [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L92-L120] |
| Storage | Raw JSON; processed Parquet/Snappy, CSV or JSON; analysis JSON; export XLSX, CSV or JSON; filenames include timestamps | [packages/worldenergydata-sodir/src/worldenergydata/sodir/storage.py:L76-L106] [packages/worldenergydata-sodir/src/worldenergydata/sodir/storage.py:L108-L155] [packages/worldenergydata-sodir/src/worldenergydata/sodir/storage.py:L197-L216] [packages/worldenergydata-sodir/src/worldenergydata/sodir/storage.py:L252-L287] |
| Offline workflow | Field CSV, production CSV and portfolio JSON, with output paths returned in configuration | [packages/worldenergydata-sodir/src/worldenergydata/sodir/offline.py:L19-L63] |
| Forecast | Nonnegative array in the input quantity's units; integer periods; nominal 80/95 confidence bands and fit metrics | [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L48-L68] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L82-L101] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L439-L468] |
| Financial result | Cashflow/tax DataFrames, NPV, IRR fraction, payback index and metrics; summary labels NPV million USD despite cashflow arithmetic using USD | [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L102-L113] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L129-L255] |
| Charts | Matplotlib figures and data dictionaries; map axes are longitude degrees east and latitude degrees north; save/export uses requested image format | [packages/worldenergydata-sodir/src/worldenergydata/sodir/visualization.py:L129-L212] [packages/worldenergydata-sodir/src/worldenergydata/sodir/visualization.py:L463-L489] |

`CoordinateTransformer` uses WGS84 ellipsoid constants and UTM zones; its public inverse returns `(latitude, longitude)`, the forward route returns `(easting, northing, zone)`, with false easting and southern false northing applied internally; it selects pyproj when available. [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L18-L60] [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L48-L79] [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L81-L102] [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L189-L282] [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L284-L362]

Block processor coordinate fallback is approximate and supplies fixed coordinates when location keys are absent; its default vertical reference is `MSL`. [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/block_processor.py:L265-L305] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/block_processor.py:L307-L349] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/block_processor.py:L64-L95]

The CSV/Parquet/JSON writers do not attach a universal coordinate, origin, sign or phase declaration; consumers must preserve each column's units and source metadata, and cannot infer a shared spatial frame from the file extension. [packages/worldenergydata-sodir/src/worldenergydata/sodir/storage.py:L108-L155] [packages/worldenergydata-sodir/src/worldenergydata/sodir/offline.py:L19-L63]

## 3. Method and governing standards

This pack treats formulas below as implementation contracts; no licensed standard is used as an independent validation source, and current legal or fiscal applicability is U2 in section 10. [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L30-L69] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L151-L166]

| Method | Implementing definition and reference basis | Limit |
| --- | --- | --- |
| Collection | `SodirData.collect_dataset`: fetch, process, validate, optionally filter; `collect_and_store` persists results | Empty fetch returns success with zero count; inspect completeness separately. [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L124-L204] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L228-L258] |
| Bounded feature ingestion | `query_entity`: stable ascending object IDs, offset paging, cumulative byte cap; fail on unfinished page cap; `_read_response` rejects redirects/errors and pauses between requests | No claim of current live completeness; U1. [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L239-L288] [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L156-L194] |
| Legacy request/cache | `SodirTransport.get`, `_generate_cache_key`, `_rate_limit`, `_execute_request_with_retry`; TTL checked by `SodirCache.get` | Legacy readers expect a `data` envelope; broad exception retry can retry a client error despite the branch comment. [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L135-L173] [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L175-L195] [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L197-L205] [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L207-L296] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cache.py:L39-L49] [packages/worldenergydata-sodir/src/worldenergydata/sodir/api_client.py:L50-L65] |
| Reserve accounting | `FieldProcessor._calculate_recovery_factor`: clamp `(original-remaining)/original` to [0,1], round to 3 places, return `None` for missing/zero original or excess remaining | This measures depletion of stated original reserves; it does not independently establish reservoir recovery. [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L343-L366] |
| Unit transforms and concept normalization | Field/discovery processors multiply source volumes by local conversion constants; monthly loader uses shared unit aliases; `sodir_field_to_concept` combines oil MMbbl and gas Bcf/6 | Energy equivalence is a code convention; section 6 records dimensional conflicts. [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L39-L45] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/discovery_processor.py:L45-L53] [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L12-L25] [packages/worldenergydata-sodir/src/worldenergydata/sodir/field_concept.py:L35-L41] [packages/worldenergydata-sodir/src/worldenergydata/sodir/field_concept.py:L59-L76] |
| Decline prediction | `DeclineCurve.predict`: exponential `qi*exp(-D*t)`, hyperbolic `qi/(1+b*D*t)^(1/b)`, harmonic `qi/(1+D*t)`; otherwise linear `qi*(1-D*t)`, including hyperbolic without `b`; negative predictions clipped | Fitting removes gaps and zeros; fallback can return an assumed curve. [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L48-L68] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L112-L148] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L150-L193] |
| Other forecasts | `_forecast_with_moving_average`, `_forecast_with_polynomial`, `ensemble_forecast`, `scenario_forecast`, `calculate_eur` | Forecast origin and band qualification remain open in section 6. [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L400-L417] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L419-L437] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L470-L553] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L595-L635] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L637-L678] |
| Financial arithmetic | `calculate_npv`: revenue less costs/taxes, working interest, discounted sum from period zero; separate IRR, depreciation, uplift and payback helpers | Simplified fiscal model; economic use requires closing the section-6 defects. [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L129-L255] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L335-L363] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L400-L427] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L378-L398] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L550-L557] |
| Analysis/statistics | Field/portfolio metrics, concentration and Gini, yearly trends; cross-regional normalization and sample-based tests | `compare_regions` significance is threshold-based; actual t, rank and variance tests are a separate API. [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L526-L541] [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L750-L762] [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L621-L635] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cross_regional.py:L142-L225] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cross_regional.py:L491-L527] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cross_regional.py:L790-L838] |
| Dataset preparation | Joins, calendar extraction, cumulative sums and BOE derivation; validation reports missing fields and duplicates | Sort/order and units must be supplied by callers. [packages/worldenergydata-sodir/src/worldenergydata/sodir/datasets.py:L189-L249] [packages/worldenergydata-sodir/src/worldenergydata/sodir/datasets.py:L418-L467] |
| Batch/parallel processing | `SodirBatchProcessor` and `SodirParallelProcessor` aggregate results and failures through executors | No-client fetch can return a mock success; export existence must be checked. [packages/worldenergydata-sodir/src/worldenergydata/sodir/batch.py:L100-L173] [packages/worldenergydata-sodir/src/worldenergydata/sodir/parallel.py:L298-L371] |
| Cache optimization | `SodirCacheOptimizer`: adaptive TTL, priority/frequency eviction and access-pattern prediction | Distinct from transport's simple cache. [packages/worldenergydata-sodir/src/worldenergydata/sodir/cache_optimizer.py:L153-L206] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cache_optimizer.py:L397-L435] [packages/worldenergydata-sodir/src/worldenergydata/sodir/cache_optimizer.py:L248-L280] |
| Coordinate transforms | `CoordinateTransformer`: pyproj when importable, otherwise internal forward/inverse UTM series | Installed packages select the route; record it with results. [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L18-L46] [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L189-L362] |
| Chart aggregation | `create_production_chart`, `create_comparison_dashboard` and `_create_comparison_chart` assemble series and comparison figures | Illustrative values and dashboard composition remain open in section 6. [packages/worldenergydata-sodir/src/worldenergydata/sodir/visualization.py:L214-L310] [packages/worldenergydata-sodir/src/worldenergydata/sodir/visualization.py:L312-L460] |

Citation sidecars are required for newly introduced standards-derived constants by the calculation-output citation contract; this documentation change introduces no constant or formula in module code. (Calculation-output citation contract, requirements 1–8 and applicability exclusions.)

## 4. Validated worked examples

Results below record execution on 2026-10-15 at `c671311959edd24095c9aa40b39c61e46ba1e84b` and its uncommitted documentation update; exercised source and tests match the header code pin. BASE and AFTER results are recorded separately in section 10.

### Validated arithmetic example

| Case | Independent expected value, input and tolerance basis | Existing test node ID | Offline result |
| --- | --- | --- | --- |
| V1: reserve depletion fraction | Closed-form material accounting `(100-30)/100 = 0.7`, dimensionless, with both input volumes in the same unit; exact equality, matching the test assertion; this checks arithmetic rather than reservoir recovery physics. [tests/unit/sodir/processors/test_field_processor.py:L196-L201] | `tests/unit/sodir/processors/test_field_processor.py::TestCalculateRecoveryFactor::test_normal_case` | PASS at BASE and AFTER |

### Regression examples

| Case | Fixture/input and expected behavior | Tolerance basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1: bounded pagination | Synthetic feature dictionaries; 2 records, second offset 1, requested projection retained. [tests/unit/sodir/test_feature_service.py:L118-L133] | Exact counts and strings, 0 mismatches | `tests/unit/sodir/test_feature_service.py::test_paging_and_select` | PASS at BASE and AFTER |
| R2: truncation rejection | Synthetic continued response at the default one-page cap must raise `ValueError`. [tests/unit/sodir/test_feature_service.py:L147-L159] | 1 expected exception | `tests/unit/sodir/test_feature_service.py::test_page_cap` | PASS at BASE and AFTER |
| R3: production schema bridge | Synthetic monthly field row; produced water becomes 1000000 Sm3; absent oil remains `None`; no injection-labelled key. [tests/unit/sodir/test_feature_service.py:L197-L219] | Exact key/value equality, 0 mismatches | `tests/unit/sodir/test_feature_service.py::test_processor_mapping` | PASS at BASE and AFTER |
| R4: deterministic manifest | Curated observations serialize identically to the committed fixture; this does not establish live retrieval provenance. [tests/unit/sodir/test_feature_service.py:L222-L225] | 0 differing bytes | `tests/unit/sodir/test_feature_service.py::test_curated_manifest_deterministic_serialization` | PASS at BASE and AFTER |

No independent live end-to-end benchmark is claimed; U1 and U3 cover that qualification gap, while the fixture and snapshot examples above remain regression evidence. [tests/unit/sodir/test_feature_service.py:L118-L133] [tests/unit/sodir/test_feature_service.py:L222-L225]

## 5. QA gates

Gate selection: AQG r0, section 10, Python calculations; G5 applies to every family. The following are proposed repeatable checks for this package, not a clearance signature.

| Gate | Applicability | Module-specific check, numeric pass criterion and unit | Evidence and current result |
| --- | --- | --- | --- |
| G0 | Applicable: inputs, units, citations | C01: `query_entity` rejects unfinished pages, malformed types and byte overruns; 0 incomplete results accepted (record count), expected exception count 1 per negative case. [tests/unit/sodir/test_feature_service.py:L147-L194] [tests/unit/sodir/test_feature_service.py:L266-L296] | Offline tests: PASS |
| G0 | Applicable | C02: `processor_record` returns 1000000 Sm3 produced water for the synthetic unit input, 0 injection-key aliases and 0 substitutions for missing oil. [tests/unit/sodir/test_feature_service.py:L197-L219] | R3: PASS; legacy loader remains excluded from this water semantics check |
| G1 | Applicable: Python import and tests; no target-program deck is produced by these exercised routes | C03: run `uv run python -m pytest tests/unit/sodir -q -rA -p no:cacheprovider`; 938 passed nodes, 0 failed nodes and 0 collection errors (counts); imports exercised by test collection. [tests/unit/sodir/test_api_client.py:L1-L14] [tests/unit/sodir/test_feature_service.py:L1-L19] | BASE and AFTER: PASS; see section 10 for legacy exceptions |
| G2 | Applicable: independent arithmetic | C04: `FieldProcessor._calculate_recovery_factor(100,30)` equals the hand fraction `(100-30)/100`, absolute error 0.0 dimensionless; never use fiscal, gas-scaling or forecast-origin paths from section 6 as hand references. [tests/unit/sodir/processors/test_field_processor.py:L196-L201] | V1: PASS; no physical dataset validation implied |
| G3 | NOT_APPLICABLE | Short solver dynamics are outside the Python ingestion/calculation gate set. (AQG r0, section 10, Python calculations.) | NOT_APPLICABLE |
| G4 | NOT_APPLICABLE | Diffraction/mesh QA is outside the Python ingestion/calculation gate set. (AQG r0, section 10, Python calculations.) | NOT_APPLICABLE |
| G5 | Applicable: evidence appendix | C05: resolve 100% of repository citations at the header pin, 0 invalid line ranges; each of the 5 section-4 cases must have 1 node result per run (record count); every open item has 1 issue or numbered draft. | Citation resolver, JUnit records and open-item cross-reference; recorded in the accompanying verification summary |
| G5 | Applicable: SODIR input provenance | C06: record SHA-256 for `feature_schemas.json` and the 3 feature fixtures at the pin; require 0 digest mismatches (count) against the exercised tree and 0 differing bytes in R4 serialization. [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L16-L32] [tests/unit/sodir/test_feature_service.py:L222-L225] | PASS: fingerprints below and R4 at BASE/AFTER |

Checks defined: G0 = 2; G1 = 1; G2 = 1; G3 = 0; G4 = 0; G5 = 2; total = 6.

C06 input fingerprints at the code pin and in the exercised tree: 4 files, 0 digest mismatches (count). R4 records deterministic serialization with 0 differing bytes at BASE and AFTER. [tests/unit/sodir/test_feature_service.py:L222-L225]

| Input | SHA-256 |
| --- | --- |
| `packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_schemas.json` | `cb30ba65ad1f8c2dc6a13c17d0564562dd9624e1dabe0be509f57578fddf9b8d` |
| `tests/unit/sodir/fixtures/feature_rows.synthetic.json` | `c6889ad9208be1798c50b38c490962ccbe5bceff94547610c8861cf006d6db93` |
| `tests/unit/sodir/fixtures/service_manifest.json` | `8f41b1a8786ade1190f48794471371826ae8f0342b9212f9c92ca9eaa2548d7b` |
| `tests/unit/sodir/fixtures/service_observations.json` | `e4ee2a7cb2db8df4b79bf1c2073c1d67fba6a5c0d595857df3f1914eb1a74880` |

The following diagnostic checks are specified for follow-up, outside the six gate checks above; their expected criteria expose existing implementation differences rather than justify changing an acceptance tolerance.

| Diagnostic | Reproduction and pass criterion | Recorded disposition |
| --- | --- | --- |
| D01 | `MonthlyProductionLoader.convert_msm3_to_mcf(1)` must equal `GasUnits.MSM3_TO_MMSCF * GasUnits.MMSCF_TO_MCF`, relative error <= 0.000001 (fraction); both factors are shared-unit declarations. [packages/worldenergydata-core/src/worldenergydata/common/units.py:L38-L43] [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L123-L132] | Code inspection mismatch; issue pending (1); not an accepted hand reference |
| D02 | For an exponential history of N periods, both `forecast_production` and `ensemble_forecast` first future predictions must equal `DeclineCurve.predict([N])[0]`, absolute error <= 0.000001 input-volume units, rather than restarting at period 0. [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L48-L68] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L385-L398] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L498-L509] | Code inspection mismatch; issue pending (3) |
| D03 | For `BatchConfig(output_format="csv")`, every returned output path from `_save_batch_data` must exist and parse as CSV, missing-file count 0. [packages/worldenergydata-sodir/src/worldenergydata/sodir/batch.py:L624-L646] | Code inspection mismatch; issue pending (5) |
| D04 | Send failed dataset envelopes through `CollectionWorkflow.execute`; accepted failed-envelope count 0; absent API clients must not qualify as fetched data. [packages/worldenergydata-sodir/src/worldenergydata/sodir/workflows/collection.py:L47-L130] [packages/worldenergydata-sodir/src/worldenergydata/sodir/parallel.py:L298-L371] | Code inspection mismatch; issue pending (1) |

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

Inspection date for all entries: 2026-10-15. A diagnostic defined above is not claimed to be an existing automated regression test.

| Symptom | Cause and evidence | Detection / issue |
| --- | --- | --- |
| Nominal no-API unit test depends on an external failure | `test_no_api_client_raises` constructs a collector without a transport fixture; `collect_dataset` initializes the client before fetching. [tests/unit/sodir/test_data.py:L163-L171] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L143-L145] | Require 0 outbound requests (count); no detection check exists; issue pending (8) |
| Client HTTP errors are retried | `_execute_request_with_retry` raises HTTP 4xx inside its try block; the broad exception handler retries it. [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L267-L290] | Require exactly 1 transport attempt for a synthetic HTTP 400 response (count); no detection check exists; issue pending (1) |
| Coordinate results depend on installed packages | `CoordinateTransformer` uses pyproj when importable and internal series otherwise; the member dependencies omit pyproj. [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L35-L46] [packages/worldenergydata-sodir/pyproject.toml:L29-L38] | Require 1 recorded route per coordinate result (count); no detection check exists for dependency-independent accuracy; issue pending (1) |
| Failed or empty collection can look successful | Empty fetch yields success; top router reports completion after dataset failures; workflow accepts any truthy dataset envelope; no-client parallel fetch returns mock success. [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L166-L170] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L115-L126] [packages/worldenergydata-sodir/src/worldenergydata/sodir/sodir.py:L92-L101] [packages/worldenergydata-sodir/src/worldenergydata/sodir/workflows/collection.py:L64-L108] [packages/worldenergydata-sodir/src/worldenergydata/sodir/parallel.py:L350-L362] | D04; no detection check exists in the passing suite for the combined failure propagation; issue pending (1) |
| Missing or invalid monthly volume becomes zero; produced water is labelled injection | Legacy `_safe_float` defaults to zero and raw produced-water key feeds `water_injected_sm3`; feature adapter repairs naming and missingness only at its boundary. [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L173-L180] [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L86-L110] [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L92-L120] | C02 detects the repaired boundary only; no detection check exists for the legacy loader; legacy regression asserts the wrong label; issue pending (1). [tests/unit/sodir/test_monthly_loader.py:L128-L132] |
| Gas output labelled Mcf uses the million-cubic-foot factor | The loader aliases `MSM3_TO_MMSCF` without applying shared `MMSCF_TO_MCF`; tests assert that alias, so a green suite preserves the scale error. [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L17-L22] [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L143-L149] [packages/worldenergydata-core/src/worldenergydata/common/units.py:L38-L43] [tests/unit/sodir/test_monthly_loader.py:L139-L142] [tests/unit/sodir/test_monthly_loader.py:L22-L22] | D01; issue pending (1) |
| Processor output is not directly analysis input | `FieldProcessor` emits `recovery_factor_oil` and `production_start_year`, while portfolio analysis requires `recovery_factor`; router passes collected lists into DataFrame-oriented analysis; the main router constructs `SodirAnalysis` without its required configuration argument. [packages/worldenergydata-sodir/src/worldenergydata/sodir/sodir.py:L82-L88] [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L143-L146] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L52-L196] [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L245-L282] [packages/worldenergydata-sodir/src/worldenergydata/sodir/analysis.py:L387-L430] | Compare required columns before analysis; 0 missing required columns (count); no detection check exists for a real collection-to-analysis round trip; issue pending (1) |
| Unsupported ID or legacy envelope yields no usable data | Router accepts `facilities`; collector has no method for it; legacy readers call short endpoints and expect `data`, unlike the bounded reader's `features` contract. [packages/worldenergydata-sodir/src/worldenergydata/sodir/sodir.py:L106-L163] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L260-L301] [packages/worldenergydata-sodir/src/worldenergydata/sodir/api_client.py:L84-L99] [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L239-L288] | C01 covers bounded reader; scheduler endpoint regression relates to #273; no equivalent live detection check exists for every legacy reader; issue pending (1) |
| Coordinate fallback supplies invented location and permissive dates pass through | Block processor returns fixed coordinates on missing keys and approximates UTM conversion; processor date parsing returns unrecognized text unchanged. [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/block_processor.py:L265-L305] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/block_processor.py:L307-L349] [packages/worldenergydata-sodir/src/worldenergydata/sodir/processors/field_processor.py:L442-L465] | Require source coordinate presence and date parsing errors = 0 (record count); no detection check exists rejecting these fallbacks; issue pending (1) |
| Fiscal outputs have inconsistent monetary labels and assumptions | CAPEX is labelled million USD and left unscaled; revenue multiplies volumes into USD; summary labels the raw NPV million USD; taxes compound corporate and special rates although the declared total is a separate unused parameter. [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L34-L69] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L102-L113] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L257-L298] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L539-L548] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L335-L363] | Require one documented money unit and agreement of total/effective tax for a declared regime, 0 mismatches; no independent fiscal detection check exists; issue pending (2); #736 tracks downstream fiscal consumption |
| Profitability index discounts compressed positive periods | `_calculate_profitability_index` filters positive flows before enumerated discounting; payback returns the first positive cumulative index, without interpolation. [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L568-L579] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L550-L557] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L559-L566] | Compare with original-time-index discounting, relative error <= 0.000001 (fraction); no detection check exists; issue pending (2) |
| Future curve restarts from initial production; confidence option does not select bands | Decline and ensemble forecasts call `predict(forecast_years)` from zero; EUR also begins at zero after summing history; band helper always emits 80/95 levels and ignores its confidence argument; failed fitting can silently substitute a curve. [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L385-L398] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L498-L509] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L637-L678] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L439-L468] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L150-L193] | D02; fit fallback is tested but horizon continuity is not; issue pending (3). [tests/unit/sodir/test_forecasting.py:L343-L362] |
| Comparison/dashboard outputs can appear data-derived while using placeholders | Regional significance helper returns threshold-selected constants; production-rate comparison chart uses hard-coded series; dashboard generation does not draw supplied charts into its axes. [packages/worldenergydata-sodir/src/worldenergydata/sodir/cross_regional.py:L491-L527] [packages/worldenergydata-sodir/src/worldenergydata/sodir/visualization.py:L442-L460] [packages/worldenergydata-sodir/src/worldenergydata/sodir/visualization.py:L89-L113] | Compare outputs against changed input samples and require >= 1 changed plotted value and >= 1 artist per populated panel (counts); no detection check exists for this dependence; issue pending (4) |
| Batch CSV path returned without a file | `_save_batch_data` constructs a CSV filename but contains no CSV write; the separate multi-format formatter path does write content. [packages/worldenergydata-sodir/src/worldenergydata/sodir/batch.py:L624-L646] [packages/worldenergydata-sodir/src/worldenergydata/sodir/batch.py:L648-L665] | D03; issue pending (5) |
| Distribution includes documentation and undeclared imports | Recursive Markdown package-data patterns include this pack; `reference_chain` imports project_economics, field-development and production packages absent from the member dependency list. [packages/worldenergydata-sodir/pyproject.toml:L59-L60] [packages/worldenergydata-sodir/pyproject.toml:L29-L38] [packages/worldenergydata-sodir/src/worldenergydata/sodir/reference_chain.py:L16-L23] | Require 0 undeclared dependency import failures (count) in an isolated member install; no detection check exists; issue pending (6) |
| Legacy tests do not collect | Imports name absent `sodir_module.api_client` or `sodir_module.processors`; normal configuration ignores the legacy directory. [tests/modules/sodir-integration/test_api_client.py:L22-L30] [tests/modules/sodir-integration/test_cross_regional_validation.py:L15-L23] [pyproject.toml:L392-L402] | Explicit file-level collection; 0 collection errors (count); no detection check exists in the normal suite; confirmed baseline, existing #313 |

#273 describes a historical scheduler invalid-endpoint incident; `test_fetches_current_sodir_featureserver_contract` checks its corrected URL/parameter contract offline, while #271 is output wiring work and #716/#736 describe reference-chain and fiscal scope rather than newly confirmed live incidents. [tests/unit/scheduler/test_sodir_adapter.py:L83-L102] (worldenergydata issues #273, endpoint failure; #271, output-directory wiring; #716, reference chain; #736, fiscal consumption.)

## 7. Lessons log

Append-only record; promote a lesson only with its detection check and an issue or shared evidence identifier. The first revision records observations in section 6 without claiming historical clearance or a shared-log entry.

| Date | Lesson | Evidence | Pack change | Shared record |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Passing alias tests can preserve a wrong unit label; compare dimensional declarations independently. | [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L17-L22] [packages/worldenergydata-core/src/worldenergydata/common/units.py:L38-L43] [tests/unit/sodir/test_monthly_loader.py:L139-L142] | D01 and section-6 gas warning | issue pending (1); no shared entry claimed |

## 8. Ownership

Requested review role: calculations quality manager for interim data-pipeline coverage; deputy review role: calculations reviewer nominated by the maintainer. These are review requirements for this draft, not claims that appointments or clearance have occurred. (AQG r0, section 11, sign-off and independence.)

Producing role: module documentation contributor. Escalate evidence classification and numeric criterion disputes to the family quality manager; cross-family decisions go to the maintainers. Review must use a provider independent of the producer. (AQG r0, section 11, sign-off and independence.)

## 9. Dependencies and implementation inventory

### Runtime and data boundaries

| Dependency or consumer | Contract and inventory basis |
| --- | --- |
| Shared core | Module errors derive from the common SODIR exception; monthly conversions import common unit classes. [packages/worldenergydata-sodir/src/worldenergydata/sodir/errors.py:L31-L36] [packages/worldenergydata-sodir/src/worldenergydata/sodir/production/monthly_loader.py:L12-L22] |
| Python numeric and tabular libraries | Member dependencies declare NumPy, pandas, SciPy, scikit-learn, seaborn, Matplotlib and numpy-financial with version ranges. [packages/worldenergydata-sodir/pyproject.toml:L29-L38] |
| HTTP and projection | Transport conditionally imports requests and provides a fallback response if unavailable; coordinates select pyproj opportunistically. [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L18-L28] [packages/worldenergydata-sodir/src/worldenergydata/sodir/transport.py:L298-L338] [packages/worldenergydata-sodir/src/worldenergydata/sodir/utils/coordinates.py:L39-L59] |
| Production / project_economics / concept screening | Reference chain consumes `ProductionQuery`, project_economics normalization and cashflow, and concept recommendations; field metadata mapping imports project_economics normalizer types. [packages/worldenergydata-sodir/src/worldenergydata/sodir/reference_chain.py:L16-L24] [packages/worldenergydata-sodir/src/worldenergydata/sodir/field_concept.py:L25-L30] |
| Scheduler and other adapters | The BSEE pipeline adapter lazily imports the SODIR API client and processors. [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/adapters/sodir_adapter.py:L76-L93] Scheduler uses a FeatureServer endpoint contract, while the production adapter tests exercise loader normalization into unified and project_economics output schemas. [tests/unit/scheduler/test_sodir_adapter.py:L83-L124] [tests/unit/production/unified/test_sodir_adapter_loader.py:L58-L106] |
| Source and fixture data | Feature schemas are loaded from `feature_schemas.json`; unit tests read curated observation and manifest fixtures, distinct from live retrieval evidence. [packages/worldenergydata-sodir/src/worldenergydata/sodir/feature_service.py:L16-L32] [tests/unit/sodir/test_feature_service.py:L222-L225] |

Inventory cross-reference (Module inventory, 2026-10-15, rows named below; inventory estimates are not test results):

| Boundary | Inventory row and package path |
| --- | --- |
| Shared core | `core:common`, row 98, `packages/worldenergydata-core/src/worldenergydata/common` |
| Financial normalization | `project_economics`, row 101, `packages/worldenergydata-project_economics/src/worldenergydata/project_economics` |
| Concept screening | `field_development`, row 218, `src/worldenergydata/field_development` |
| Production query | `production`, row 230, `packages/worldenergydata-production/src/worldenergydata/production` |
| Scheduler consumer | `scheduler`, row 303, `packages/worldenergydata-scheduler/src/worldenergydata/scheduler` |
| Pipeline consumer | `bsee`, row 207, `packages/worldenergydata-bsee/src/worldenergydata/bsee` |
| Alternative financial method | `economics`, row 100, `packages/worldenergydata-economics/src/worldenergydata/economics` |
| Third-party libraries and source datasets | No owning-repository module inventory row; versions are dependency constraints and data use is fixture-only here |

No solver version is required by the tests recorded here; no solver execution or live source refresh was performed. Dependency inventory covers the package metadata and the cited import/consumer boundaries, not independent inventories of those other domains.

### Map inventory and counted grep

Map source: digitalmodel, `docs/registry/implementation-map.yaml`, ref revision `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `families` and their `implementations.path` entries (read-only snapshot).

Inspection result: 13 map families inspected, 0 implementation rows inside the package in the header, 0 module map families, and an empty implementation inventory. No subpackage is excluded from this pack's scope. No family is counted; the case-sensitive Python-`re` counted grep is `NOT_APPLICABLE` because no family has an in-package row. No search signal was omitted and no counted-family miss total is asserted. A8 inventory passes with this empty inventory; the missing method families are map follow-up, not an alternative counted grep. (digitalmodel, Implementation map, ref and data revisions above, `families`.)

### Repository-wide method search and map follow-up

Search scope: tracked Python sources throughout this repository, including `scripts/`, `packages/`, `src/` and tests; queried definition names for NPV, decline fitting, recovery factors, gas conversion and coordinate transforms, with a further script search for `npv`, `decline`, `35\.3147`, `recovery_factor` and `utm_to_wgs84`. This is a discovery record, not a completeness claim about the absent map families.

| Further implementation or helper | Classification and evidence |
| --- | --- |
| Legacy analysis copy under tests | Independent arithmetic definitions, outside the package; map gap. [tests/modules/sodir-integration/sodir_module/analysis.py:L526-L541] [tests/modules/sodir-integration/sodir_module/analysis.py:L750-L762] |
| Legacy regional-analysis copy under tests | Independent normalization/statistics definitions, outside the package; map gap. [tests/modules/sodir-integration/sodir_module/cross_regional.py:L142-L225] |
| Legacy dataset generator copy under tests | Independent production aggregation, outside the package; map gap. [tests/modules/sodir-integration/sodir_module/datasets.py:L191-L251] |
| project_economics NPV | Separate financial implementation, outside the package; map gap, with period convention to compare before consolidation. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L118-L166] |
| Economics NPV | Separate financial implementation, outside the package; map gap. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L137-L182] |
| Concept alias | `build_norway_field_concept` delegates to `sodir_field_to_concept`; helper, not an independent implementation. [packages/worldenergydata-sodir/src/worldenergydata/sodir/field_concept.py:L84-L86] |

Map follow-up must name ingestion/paging, retry and rate limiting, schema and unit normalization, coordinate transforms, reserve/depletion accounting, field/portfolio concentration, temporal statistics and cross-regional two-sample tests, decline/ensemble/EUR forecasting, discounted cashflow/fiscal schedules, dataset aggregation, batch execution, cache eviction/TTL and chart aggregation; these correspond to the section-3 methods. Record package rows before counting them in a future map revision; issue pending (7).

## 10. Coverage and open items

### Execution record

Execution BASE: `c671311959edd24095c9aa40b39c61e46ba1e84b`; AFTER: the uncommitted documentation update on that commit. Source and test files exercised are byte-identical to the header code pin. Every target was rerun at BASE and AFTER on 2026-10-15. Commands used ordinary `uv run python -m pytest <target> -q -rA -p no:cacheprovider --basetemp=<scratch>`, with repository addopts retained and coverage/JUnit destinations redirected to scratch. The documented `--allow-existing-tree-changes` option was used consistently for the additional BASE targets and all AFTER targets; it preserves initial pack bytes while detecting new tree changes. The canonical BASE run began clean. The environment was built in scratch. No collection-ignore entry, skip mark or assertion changed.

| Target (one command per row) | BASE passed / failed / skipped | AFTER passed / failed / skipped | Collection result |
| --- | --- | --- | --- |
| `tests/unit/sodir` | 938 / 0 / 0 | 938 / 0 / 0 | 0 |
| `tests/modules/sodir-integration/test_analysis.py` | 26 / 0 / 0 | 26 / 0 / 0 | 0 |
| `tests/modules/sodir-integration/test_api_client.py` | 0 / 0 / 0 | 0 / 0 / 0 | ERROR at collection: `ModuleNotFoundError: No module named 'sodir_module.api_client'`; 24 definitions not collected; existing #313 |
| `tests/modules/sodir-integration/test_cross_regional_validation.py` | 0 / 0 / 0 | 0 / 0 / 0 | ERROR at collection: `ModuleNotFoundError: No module named 'sodir_module.processors'`; 15 definitions not collected; existing #313 |
| `tests/modules/sodir-integration/test_data_collection.py` | 9 / 0 / 19 | 9 / 0 / 19 | 0 |
| `tests/modules/sodir-integration/test_integration.py` | 0 / 0 / 0 | 0 / 0 / 0 | ERROR at collection: `ModuleNotFoundError: No module named 'sodir_module.api_client'`; 13 definitions not collected; existing #313 |
| `tests/modules/sodir-integration/test_performance.py` | 0 / 0 / 0 | 0 / 0 / 0 | ERROR at collection: `ModuleNotFoundError: No module named 'sodir_module.api_client'`; 13 definitions not collected; existing #313 |
| `tests/modules/sodir-integration/test_processors.py` | 24 / 0 / 0 | 24 / 0 / 0 | 0 |
| `tests/modules/sodir-integration/test_sodir_module.py` | 16 / 0 / 1 | 16 / 0 / 1 | 0 |
| `tests/unit/scheduler/test_sodir_adapter.py` | 7 / 0 / 0 | 7 / 0 / 0 | 0 |
| `tests/unit/production/unified/test_sodir_adapter_loader.py` | 3 / 0 / 0 | 3 / 0 / 0 | 0 |
| `tests/unit/bsee/pipeline/adapters/test_sodir_adapter.py` | 53 / 0 / 0 | 53 / 0 / 0 | 0 |
| `tests/unit/bsee/analysis/test_decline_analysis.py` | 24 / 0 / 0 | 24 / 0 / 0 | 0 |
| `tests/contracts` | 8 / 0 / 0 | 8 / 0 / 0 | 0 |

BASE totals: 1108 passed, 0 assertion failures, 20 existing skips, 4 collection errors affecting 65 test definitions (not collected parametrized-node counts). The canonical package domain accounts for 938 passed nodes, re-counted rather than copied from an inventory estimate. AFTER assertions: 1108 passed, 0 assertion failures, 20 existing skips, and the same 4 collection errors affecting 65 definitions. NOT_RUN: 0 at BASE and AFTER.

The two BSEE targets above belong to the BSEE package's test tree and are also evidence for its pack (#1235); shared test evidence does not extend this pack's package scope.

The four collection errors are baseline: their import lines and absent package modules are identical in the pinned tree and `origin/main`; #313 already records stale imports. Normal configuration excludes these files, but each was invoked explicitly to expose its result. [tests/modules/sodir-integration/test_api_client.py:L22-L30] [tests/modules/sodir-integration/test_cross_regional_validation.py:L15-L23] [tests/modules/sodir-integration/test_integration.py:L18-L31] [tests/modules/sodir-integration/test_performance.py:L24-L38] [pyproject.toml:L392-L402]

Existing skips, recorded without adding or changing skip marks:

- `tests/modules/sodir-integration/test_data_collection.py::TestDataCollectionWorkflow::test_parallel_dataset_collection` — legacy SODIR workflow tests require long-running/live collection integration.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataCollectionWorkflow::test_workflow_error_recovery` — legacy SODIR workflow tests require long-running/live collection integration.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataCollectionWorkflow::test_workflow_execution` — legacy SODIR workflow tests require long-running/live collection integration.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataCollectionWorkflow::test_workflow_filters` — legacy SODIR workflow tests require long-running/live collection integration.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataCollectionWorkflow::test_workflow_initialization` — legacy SODIR workflow tests require long-running/live collection integration.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataStorage::test_cleanup_old_data` — legacy SODIR storage tests target retired helper methods not present in current storage API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataStorage::test_compression_support` — legacy SODIR storage tests target retired helper methods not present in current storage API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataStorage::test_hierarchical_structure` — legacy SODIR storage tests target retired helper methods not present in current storage API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataStorage::test_list_available_datasets` — legacy SODIR storage tests target retired helper methods not present in current storage API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataStorage::test_load_data` — legacy SODIR storage tests target retired helper methods not present in current storage API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataStorage::test_save_data` — legacy SODIR storage tests target retired helper methods not present in current storage API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataStorage::test_storage_initialization` — legacy SODIR storage tests target retired helper methods not present in current storage API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDatasetGeneration::test_create_analysis_dataset` — legacy SODIR dataset-generation tests target retired helper methods not present in current dataset API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDatasetGeneration::test_cross_reference_data` — legacy SODIR dataset-generation tests target retired helper methods not present in current dataset API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDatasetGeneration::test_export_formats` — legacy SODIR dataset-generation tests target retired helper methods not present in current dataset API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDatasetGeneration::test_filtering_and_sorting` — legacy SODIR dataset-generation tests target retired helper methods not present in current dataset API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDatasetGeneration::test_summary_statistics` — legacy SODIR dataset-generation tests target retired helper methods not present in current dataset API.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataValidationIntegration::test_validate_collected_data` — legacy SODIR validation-integration tests expect retired validator semantics.
- `tests/modules/sodir-integration/test_data_collection.py::TestDataValidationIntegration::test_validation_report_generation` — legacy SODIR validation-integration tests expect retired validator semantics.
- `tests/modules/sodir-integration/test_sodir_module.py::TestSodirRouter::test_router_handles_errors` — legacy sodir_module router was retired; current package uses worldenergydata.sodir.data.SodirData.

Uncollected definitions (collection ERROR, existing #313), with the file-specific missing-module error above:

- `tests/modules/sodir-integration/test_api_client.py::TestSodirAPIClient::test_api_client_initialization`.
- `tests/modules/sodir-integration/test_api_client.py::TestSodirAPIClient::test_api_client_removes_trailing_slash`.
- `tests/modules/sodir-integration/test_api_client.py::TestSodirAPIClient::test_get_request_basic`.
- `tests/modules/sodir-integration/test_api_client.py::TestSodirAPIClient::test_get_request_with_params`.
- `tests/modules/sodir-integration/test_api_client.py::TestRateLimiting::test_rate_limit_calculation`.
- `tests/modules/sodir-integration/test_api_client.py::TestRateLimiting::test_rate_limiting_enforced`.
- `tests/modules/sodir-integration/test_api_client.py::TestRateLimiting::test_no_rate_limiting_when_disabled`.
- `tests/modules/sodir-integration/test_api_client.py::TestCaching::test_cache_hit`.
- `tests/modules/sodir-integration/test_api_client.py::TestCaching::test_cache_expiration`.
- `tests/modules/sodir-integration/test_api_client.py::TestCaching::test_cache_key_includes_params`.
- `tests/modules/sodir-integration/test_api_client.py::TestCaching::test_cache_can_be_cleared`.
- `tests/modules/sodir-integration/test_api_client.py::TestErrorHandling::test_retry_on_server_error`.
- `tests/modules/sodir-integration/test_api_client.py::TestErrorHandling::test_retry_on_rate_limit`.
- `tests/modules/sodir-integration/test_api_client.py::TestErrorHandling::test_max_retries_exceeded`.
- `tests/modules/sodir-integration/test_api_client.py::TestErrorHandling::test_exponential_backoff`.
- `tests/modules/sodir-integration/test_api_client.py::TestErrorHandling::test_no_retry_on_client_error`.
- `tests/modules/sodir-integration/test_api_client.py::TestSODIREndpoints::test_get_blocks`.
- `tests/modules/sodir-integration/test_api_client.py::TestSODIREndpoints::test_get_wellbores`.
- `tests/modules/sodir-integration/test_api_client.py::TestSODIREndpoints::test_get_fields`.
- `tests/modules/sodir-integration/test_api_client.py::TestSODIREndpoints::test_get_discoveries`.
- `tests/modules/sodir-integration/test_api_client.py::TestSODIREndpoints::test_get_surveys`.
- `tests/modules/sodir-integration/test_api_client.py::TestRequestHeaders::test_default_headers`.
- `tests/modules/sodir-integration/test_api_client.py::TestRequestHeaders::test_custom_headers`.
- `tests/modules/sodir-integration/test_api_client.py::TestRequestHeaders::test_headers_sent_with_request`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_data_normalization`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_wellbore_data_compatibility`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_block_data_compatibility`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_production_data_alignment`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_cross_regional_metrics`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_discovery_timeline_compatibility`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_operator_mapping`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_data_quality_validation`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_cross_regional_aggregation`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_unit_conversion_accuracy`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_statistical_comparison`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestCrossRegionalValidation::test_temporal_alignment`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestDataIntegrityValidation::test_referential_integrity`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestDataIntegrityValidation::test_duplicate_detection`.
- `tests/modules/sodir-integration/test_cross_regional_validation.py::TestDataIntegrityValidation::test_data_consistency`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_complete_data_collection_workflow`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_data_processing_pipeline`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_storage_and_retrieval`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_analysis_integration`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_caching_integration`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_parallel_processing_integration`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_batch_processing_integration`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_dataset_generation_integration`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_error_handling_integration`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_workflow_orchestration`.
- `tests/modules/sodir-integration/test_integration.py::TestSodirIntegration::test_performance_optimization_integration`.
- `tests/modules/sodir-integration/test_integration.py::TestModuleIntegration::test_module_initialization`.
- `tests/modules/sodir-integration/test_integration.py::TestModuleIntegration::test_component_communication`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_large_scale_data_processing`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_parallel_processing_performance`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_cache_performance_under_load`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_batch_processing_performance`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_storage_performance`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_analysis_performance`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_concurrent_api_simulation`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_memory_efficiency`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_scalability_limits`.
- `tests/modules/sodir-integration/test_performance.py::TestPerformance::test_production_data_processing`.
- `tests/modules/sodir-integration/test_performance.py::TestStressConditions::test_api_timeout_handling`.
- `tests/modules/sodir-integration/test_performance.py::TestStressConditions::test_cache_eviction_under_pressure`.
- `tests/modules/sodir-integration/test_performance.py::TestStressConditions::test_error_recovery`.

### Read inventory

Source review includes every Python file and subfolder in the header package, both module documents, feature schemas, and the package README/metadata. Example filenames containing data-record names are represented by patterns to keep this inventory free of those names.

- `__init__.py`.
- `analysis.py`.
- `api_client.py`.
- `batch.py`.
- `cache.py`.
- `cache_optimizer.py`.
- `cross_regional.py`.
- `data.py`.
- `datasets.py`.
- `endpoints.py`.
- `errors.py`.
- `examples/__init__.py`.
- `examples/decline_curve_examples.py`.
- `examples/*_npv_example.py`.
- `feature_service.py`.
- `field_concept.py`.
- `forecasting.py`.
- `npv_norway.py`.
- `offline.py`.
- `parallel.py`.
- `processors/__init__.py`.
- `processors/block_processor.py`.
- `processors/discovery_processor.py`.
- `processors/field_processor.py`.
- `processors/survey_processor.py`.
- `processors/wellbore_processor.py`.
- `production/__init__.py`.
- `production/monthly_loader.py`.
- `reference_chain.py`.
- `sodir.py`.
- `storage.py`.
- `transport.py`.
- `utils/__init__.py`.
- `utils/coordinates.py`.
- `validators.py`.
- `visualization.py`.
- `workflows/__init__.py`.
- `workflows/collection.py`.

- `DATA_DICTIONARY.md`, `feature_schemas.json`, package `README.md` and `pyproject.toml`.

Module test files read (paths relative to `tests/unit/sodir`); all legacy test files and their supporting Python subfolders were also read:

- `processors/test_discovery_processor.py`.
- `processors/test_field_processor.py`.
- `processors/test_survey_processor.py`.
- `processors/test_wellbore_processor.py`.
- `test_analysis.py`.
- `test_api_client.py`.
- `test_batch.py`.
- `test_cache.py`.
- `test_cache_optimizer.py`.
- `test_collection_workflow.py`.
- `test_cross_regional.py`.
- `test_data.py`.
- `test_datasets.py`.
- `test_decline_curve_examples.py`.
- `test_errors.py`.
- `test_feature_service.py`.
- `test_field_processor_water_injection.py`.
- `test_forecasting.py`.
- `test_monthly_loader.py`.
- `test_norway_716.py`.
- `test_norway_reference_chain.py`.
- `test_npv_norway.py`.
- `test_parallel.py`.
- `test_*_npv_example.py`.
- `test_storage.py`.
- `test_validators.py`.
- `test_visualization.py`.
- `utils/test_coordinates.py`.
- `workflows/test_collection.py`.

Documentation found by case-insensitive module-name search under `docs/`, read as documentary leads rather than readiness evidence; 2 discovery files with identifying names are withheld for codenaming, issue pending (9):

- [docs/CLI.md:L487-L487]
- [docs/adr/0001-domain-package-split.md:L41-L41]
- [docs/ci/flake8-inventory-2026-04-23.md:L110-L110]
- [docs/data-sources/README.md:L48-L48]
- [docs/data-sources/index.md:L27-L27]
- [docs/data-sources/sodir/sodir.md:L1-L1]
- [docs/data/DATA_INVENTORY_ANALYSIS.md:L9-L9]
- [docs/data/DATA_MAP.md:L14-L14]
- [docs/development/index.md:L94-L94]

- [docs/modules/data_sodir/README.md:L1-L1]
- [docs/modules/data_sodir/api_guide.md:L1-L1]
- [docs/modules/data_sodir/config_guide.md:L1-L1]
- [docs/modules/data_sodir/cross_regional_tutorial.md:L3-L3]
- [docs/modules/project_economics/country-adapter-checklist.md:L47-L47]

- [docs/modules/repository-architecture.md:L92-L92]
- [docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md:L19-L19]
- [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L126-L126]
- [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L15-L15]
- [docs/plans/2026-05-04-issue-269-sodir-brazil-ukcs-adapters.md:L1-L1]
- [docs/plans/2026-05-04-issue-273-sodir-endpoint-fix.md:L1-L1]
- [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]
- [docs/plans/2026-05-04-issue-351-scheduler-readiness-matrix.md:L36-L36]
- [docs/plans/2026-05-04-issue-360-scheduler-health.md:L38-L38]
- [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L72-L72]
- [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L27-L27]
- [docs/plans/2026-07-04-issue-716-norway-sodir-reference-chain.md:L1-L1]
- [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L49-L49]
- [docs/plans/README.md:L18-L18]
- [docs/raw_data/sodir/sodir.md:L1-L1]
- [docs/reference/index.md:L82-L82]
- [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L198-L198]
- [docs/reports/2026-04-26-plan-353-codex.md:L16-L16]
- [docs/reports/2026-04-26-plan-353-gemini.md:L24-L24]
- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L69-L69]
- [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L15-L15]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L16-L16]
- [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L34-L34]
- [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L41-L41]
- [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L12-L12]
- [docs/reports/2026-04-26-worldenergydata-scheduler-safe-probe-results.md:L52-L52]
- [docs/reports/cli-smoke-report-2026-05-11.md:L21-L21]
- [docs/reports/data-freshness-scorecard-2026-06-08.md:L26-L26]
- [docs/reports/scheduler-health-2026-W16.md:L13-L13]
- [docs/reports/scheduler-health-2026-W24.md:L12-L12]
- [docs/user-guide/index.md:L36-L36]

### Open-item register

All items below are assigned to the maintainer for issue routing; technical acceptance belongs to the calculations quality manager. Each open item has an existing issue or a numbered accompanying draft; pending markers satisfy this draft register, with issue creation assigned to the maintainer before merge.

| Item | Remaining work / limit | Issue or draft |
| --- | --- | --- |
| U1 | UNVERIFIED: present live endpoint behavior, completeness, freshness and upstream coordinate/volume interpretation; fixtures and stored schema were checked; the unintended unit-test HTTP 403 result does not qualify a live data contract. | #273 (closed historical incident); open follow-ups #1098 and #462 |
| U2 | UNVERIFIED: financial parameter defaults represent the currently applicable fiscal regime; no authoritative fiscal publication was opened. | #736; issue pending (2) |
| U3 | UNVERIFIED: README production-readiness, performance and coverage claims; no independent live end-to-end benchmark or timing campaign was run. | #349 |
| F1 | Normalize gas units, produced-water semantics, missingness, schema bridges, failed-envelope propagation, coordinate/date fallbacks, optional projection routes and legacy retry behavior before accepting data-derived outputs. | issue pending (1) |
| F2 | Define and test cashflow currency/scale, tax basis and original-period profitability discounting. | issue pending (2); #736 |
| F3 | Correct and independently test forecast continuation, EUR origin, fallback visibility and confidence-level behavior. | issue pending (3) |
| F4 | Remove or explicitly identify illustrative chart/significance values and compose dashboard panels from actual inputs. | issue pending (4) |
| F5 | Require CSV persistence before batch export success. | issue pending (5) |
| F6 | Reconcile the member distribution contract: recursive Markdown package-data patterns include this documentation; direct runtime imports also cross package boundaries beyond its declared member dependencies. No packaging configuration was changed. [packages/worldenergydata-sodir/pyproject.toml:L29-L38] [packages/worldenergydata-sodir/pyproject.toml:L59-L60] [packages/worldenergydata-sodir/src/worldenergydata/sodir/reference_chain.py:L16-L24] | issue pending (6) |
| F7 | Add the section-3 method families and independent/copy relationships to the implementation map; counted grep stays inapplicable until package rows exist. | issue pending (7) |
| F8 | Restore legacy collection and qualify the 20 existing skips; their definitions and skip marks were left unchanged. | #313 |
| F9 | Replace stale asynchronous/legacy-import documentation and re-derive maturity and test claims from current contracts. [docs/modules/data_sodir/README.md:L32-L49] [docs/modules/data_sodir/README.md:L290-L350] | #313 and #349 |
| F10 | Keep the nominal no-API collection test offline: it initializes a real client and only passes when the external request fails; observed logs contain HTTP 403. [tests/unit/sodir/test_data.py:L163-L171] [packages/worldenergydata-sodir/src/worldenergydata/sodir/data.py:L143-L145] | issue pending (8) |
| F11 | Codename the 2 discovery files with identifying names before listing their paths. | issue pending (9) |

Registry observation: `docs/registry/module-routing.yaml` does not exist at the pinned revision, so no routing entry was added. No private dataset values, additional data files or private-sidecar entry were introduced.
