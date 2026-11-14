# Marine safety module knowledge pack

| Header | Value |
| --- | --- |
| Module | `marine_safety` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety` |
| Pack revision | 2, 2026-10-22 |
| Code revision | `55991b0def0f90708b3e0c396c0f57d9d1b7f7fb` |
| Analysis family | EC (engineering calculations); data pipeline; AQG r0 section 10, Python calculations |
| Required quality role | EC quality manager; data-pipeline quality manager as deputy when appointed |
| Status | DRAFT |

Summary: the original assessment is retained at its code pin; the collection
and failure audit now has committed issue texts and a per-node result ledger.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- | --- |
| 1 | 2026-10-15 | Initial canonical assessment. |
| 2 | 2026-10-22 | Add committed draft and result references so baseline defects can be filed and collection evidence reproduced. |

Current audit sources: [ISSUES_DRAFT.md](ISSUES_DRAFT.md) preserves every numbered
placeholder in this pack; [BASELINE_RESULTS.md](BASELINE_RESULTS.md) records the
restored collection inventory and current raw failures. Historical results below
remain observations at the original code pin, including its collection gap.
No engineering constant or incident-analysis implementation is changed.

## 1. Purpose and scope

The main path exposes filtered incident DataFrames through `IncidentsQuery`, reads configured source files through `CrossDatabaseAnalyzer`, and computes grouped counts, mean severity scores and source overlap. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L186-L223] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L405-L466] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L572-L630]

This revision documents that query path and the CSV statistics engine route; detailed qualification of the remaining importers, scrapers, classifiers, database administration and report generation is deferred to section 10, item C1. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L19-L73]

The engine route accepts only `incident_stats` with `data.source=csv`, and writes incident-type counts, yearly trends and a JSON summary. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L19-L73]

The analyzer attempts configured `maib`, `imo` and `tsb` file importers, fills other sources from built-in synthetic data, and labels the combined result `live` when any importer succeeds; this label does not establish that every returned row is observed data. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L468-L508]

`IncidentsQuery.query()` returns only the DataFrame, dropping the analyzer result's freshness field; live-source suitability therefore requires separate provenance checks. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L192-L202] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L563-L570]

UNVERIFIED: U1 — maturity is recorded only as a README claim, unverified: the README badge says active development, while its feature list includes coverage and asynchronous-operation claims beyond this main-path assessment; see U1 in section 10. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/README.md:L3-L8] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/README.md:L55-L85]

## 2. Inputs and outputs

### Inputs on the main path

| Name | Unit | Allowed range or handling | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| `source` / `sources` | source identifier | Singular/plural API filters, then exact membership against the loaded rows | `maib`, `imo`, `emsa`, `tsb` | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L56-L63] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L192-L199] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L541-L542] |
| `year`, `start_year`, `end_year` | calendar year | Bounds are inclusive; the analyzer compares derived years without validating order | No bounds | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L108-L110] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L131-L136] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L547-L550] |
| `incident_types`, `vessel_types`, `regions` | category identifier | Exact membership; nonempty filters combine with AND | `None` | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L43-L48] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L541-L552] |
| `importer_config[maib]` | file locator | `occurrences_file` required; `vessels_file` and `persons_file` optional; semicolon CSV, UTF-8 with replacement | No configuration, hence synthetic fallback | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L414-L425] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/maib_importer.py:L142-L155] |
| `importer_config[tsb]` | file locator | `occurrence_file` required; related vessel and injury files optional | No configuration, hence synthetic fallback | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L438-L449] |
| `importer_config[imo]` | file locator | `source_path` required; CSV reader uses UTF-8 with BOM handling and delimiter detection | No configuration, hence synthetic fallback | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L427-L436] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_importer.py:L193-L220] |
| `data.file`, `Analysis.analysis_root_folder`, `Analysis.result_folder` | file locator | CSV resolved from the input root; output folder created recursively | `data.source=csv`; file and analysis directories required | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L34-L48] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L75-L81] |
| `fatalities`, `injuries` in normalized records | persons | Converted to integer with missing values replaced by zero; this path does not reject negative counts | 0 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L269-L279] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L287-L308] |

### Outputs on the main path

| Name | Unit and representation | Range or semantics | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| `result.data` | DataFrame | Ten canonical columns: `source`, `incident_id`, `date`, `incident_type`, `vessel_type`, `region`, `fatalities`, `injuries`, `severity`, `description` | Available schema columns only | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L383-L395] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L560-L569] |
| `total_incidents`, `by_source` | records | Counts after filtering | Empty sources can have zero counts | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L554-L569] |
| `data_freshness` | category | `live` means at least one source loaded; `synthetic` means none loaded | `synthetic` | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L468-L508] |
| `severity` | category | `fatal` for at least 1 fatality; otherwise `very_serious` for at least 3 injuries, `serious` for at least 1 injury, otherwise `moderate` | `moderate` | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L269-L279] |
| `mean_severity_score` | dimensionless score | Arithmetic mean of mapped severity scores within an incident type | No missing-score fill in `correlations()` | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L593-L604] |
| `source_overlap_rate` | dimensionless fraction | Shared type/year/region groups divided by all groups; shared means at least 2 distinct sources | 0.0 for no groups | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L609-L615] |
| `trend_analysis`, `top_incident_types`, `risk_hotspots` | records | Year/source/type counts; descending type counts; zero-filled region/type matrix | Top 10 types | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L632-L676] |
| `incident_type_counts_csv`, `trends_csv`, `summary_json` | CSV counts and JSON integer counts | Output file locators returned to the engine configuration | Label `marine_safety_stats` | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L44-L73] |

Dates from source-normalized records are stringified and truncated to ten characters; derived years use pandas parsing, with coercion in `_add_derived_columns()` but strict parsing in the analytics functions. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L287-L350] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L510-L515] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L593-L595] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L640-L646]

The query output contains categorical regions rather than geometric axes; the separate location model bounds latitude and longitude and names water depth in meters, while matching consumes latitude/longitude in degrees and returns distance in kilometers. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L383-L395] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/database/models.py:L112-L134] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643]

UNVERIFIED: U2 — coordinate datum, longitude sign convention, date timezone and a uniform unit contract across every external input format have not been established; do not assume a global frame or timezone from the numeric bounds, issue pending (1).

## 3. Method and governing standards

| Method family | Implementation and rule | Reference or qualification |
| --- | --- | --- |
| File loading and normalization | `_load_from_importer()` calls `read_source()`, `parse_record()` and a source normalizer; it omits records parsed as `None` or without an incident ID | Implementation contract, with no database write on this route. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L405-L466] |
| Incident and region categories | `_normalize_incident_type()` performs exact then substring lookup; regional normalizers use ordered string rules and source-specific fallback categories | Implementation policy rather than independently qualified incident taxonomy. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L170-L182] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L200-L266] |
| Casualty severity | `_calc_severity()` uses the casualty thresholds in section 2 | An application rule; independent qualification remains U3. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L269-L279] |
| Filtered query | `query()` loads before applying exact membership and inclusive year bounds; it returns counts after filtering and an empty `correlations` dictionary | Filtering does not itself correlate individual incidents. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L539-L570] |
| Descriptive aggregation | `trend_analysis()` groups by year/source/type; `top_incident_types()` groups and ranks by count; `risk_hotspots()` groups by region/type | Counts of records; no exposure denominator is used in these functions. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L632-L676] |
| Source overlap and mean severity | `correlations()` computes the mean mapped score and the fraction of type/year/region groups having multiple sources | Shared groups do not establish that two records describe the same event. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L593-L630] |
| Individual record matching, supplementary route | `IncidentMatcher.calculate_confidence()` returns 1.0 immediately for equal normalized IMO identifiers; otherwise it combines available name/location/date/IMO component scores with renormalized weights | The early return does not require date agreement, so equal vessel identifiers alone are insufficient evidence of duplicate events. `IncidentMatcher` defaults to 3 days, 50 km and name similarity 0.8; `IncidentCorrelator._compare()` is a separate route with defaults 5 days, 100 km and name similarity 0.75. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L40-L49] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L26-L47] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L293-L352] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L491-L523] |
| Matching distances and time, supplementary route | `_haversine_distance()` converts degree differences to radians and multiplies the great-circle angle by `EARTH_RADIUS_KM`; location and date scores decay linearly to zero at their configured thresholds | The separate module-level `incident_correlator._haversine()` implements its own great-circle calculation; `_compare()` uses linear location decay and Jaccard name similarity with the different defaults above. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L175-L218] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L357-L373] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L403-L419] Radius, threshold and weight defaults are implementation constants, not independently validated calibration. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L35-L75] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L195-L196] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L420-L489] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643] |
| Database batch import, supplementary route | `BaseImporter.import_data()` batches model instances; `_commit_batch()` rolls back failed batches and increments `errors` instead of raising | Consumers must inspect returned statistics; the base `is_duplicate()` always returns false. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/base_importer.py:L98-L195] |

The following inventory records the references named by the code; it establishes no clause conformance and reproduces no publication values. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_importer.py:L1-L16] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/emsa_importer.py:L34-L38] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_validators.py:L1-L8]

| Reference named in code | Title and qualification | Evidence |
| --- | --- | --- |
| `MSC-MEPC.3/Circ.4/Rev.1` | U3: public title and clause basis unverified | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_importer.py:L1-L16] |
| `MSC-MEPC.3/Circ.4` | U3: public title and clause basis unverified; taxonomy labels it casualty-investigation guidance | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_taxonomy.py:L32-L37] |
| `MSC-MEPC.3/Circ.3` | U3: public title and clause basis unverified; EMSA importer names a different identifier | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/emsa_importer.py:L34-L38] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/emsa_importer.py:L270-L273] |
| `IMO Resolution A.600(15)` | IMO ship identification number scheme; public title confirmed by IMO, *IMO identification number schemes*, section “IMO ship identification number scheme”, resolution adopted 1987 ([public reference](https://www.imo.org/en/OurWork/MSAS/Pages/IMO-identification-number-scheme.aspx)); checksum clause basis remains U3 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_validators.py:L1-L8] |
| `Directive 2009/18/EC` | U3: public title and provision basis unverified | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/emsa_importer.py:L270-L273] |
| `ISO 3166-1 alpha-2` | U3: edition, public title and clause basis unverified | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/emsa_importer.py:L200-L200] |

UNVERIFIED: U3 — the unconfirmed reference titles, editions, clause bases and conformance, severity calibration, matching calibration and external-source completeness have not been checked against independent published material; clause text not checked against the licensed copy, issue pending (1).

## 4. Validated worked examples

Validated examples: 0; the five selected examples below are regression checks of synthetic data, fixture behavior or a bundled CSV workflow, with expected values specified by repository assertions rather than an independently published dataset. [docs/registry/workflows.yaml:L152-L174] [tests/marine_safety/test_api_on_base.py:L33-L41] [tests/unit/marine_safety/test_cross_database.py:L200-L204] [tests/unit/marine_safety/test_cross_database_live.py:L195-L231]

| Case | Source and input | Expected value, unit and tolerance basis | Existing test node ID | Offline result at the code revision |
| --- | --- | --- | --- | --- |
| R1 API golden | Built-in synthetic records; `source=maib` | 50 records, 10 columns, exact equality; regression contract | `tests/marine_safety/test_api_on_base.py::test_marine_safety_query_unchanged` | PASS at BASE and AFTER. [tests/marine_safety/test_api_on_base.py:L33-L41] |
| R2 year bounds | Built-in synthetic records; start year 2018, end year 2020 | 0 records outside inclusive bounds, exact comparison; filter contract | `tests/unit/marine_safety/test_cross_database.py::TestFilterByYear::test_year_range_combines_start_and_end` | PASS at BASE and AFTER. [tests/unit/marine_safety/test_cross_database.py:L200-L204] |
| R3 failed import | Missing occurrence CSV locator supplied by the test | `data_freshness=synthetic`, 0 label mismatches; fallback contract | `tests/unit/marine_safety/test_cross_database_live.py::TestGracefulFallback::test_fallback_to_synthetic_on_missing_maib_file` | PASS at BASE and AFTER. [tests/unit/marine_safety/test_cross_database_live.py:L195-L203] |
| R4 partial import | Fixture `tests/fixtures/marine_safety/maib_occurrences_sample.csv` plus missing TSB file | `data_freshness=live`, 0 label mismatches; existing behavior, not proof of complete observations | `tests/unit/marine_safety/test_cross_database_live.py::TestGracefulFallback::test_partial_fallback_single_bad_source` | PASS at BASE and AFTER. [tests/unit/marine_safety/test_cross_database_live.py:L221-L231] |
| R5 CSV engine | `examples/workflows/marine-safety-stats/input.yml`, bundled CSV; repository workflow assertions | Total 5 records; source counts 2 and 3; fire 2 records; type-count CSV 4 rows and count sum 5 records; exact repository assertions | `tests/workflows/test_durable_workflows.py::test_registry_workflow_outputs[marine-safety-stats]` | PASS at BASE and AFTER. [docs/registry/workflows.yaml:L152-L174] [tests/workflows/test_durable_workflows.py:L125-L144] |

The hand checks in section 5 use a separately constructed arithmetic fixture and a geometric identity; they are limited sanity checks and do not qualify incident populations or matching accuracy. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L609-L615] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643]

## 5. QA gates

Gate selection: G0 inputs, G1 imports/tests, G2 hand or published checks, G3 and G4 `NOT_APPLICABLE`, and G5 evidence; reference: AQG r0, revision 0, section 10, Python calculations, and section 9, QA appendix.

| Gate | Applicability and route | Required checks and current evidence |
| --- | --- | --- |
| G0 | Applicable: local CSV and DataFrame schema, casualty units and provenance | S0.1, S0.2 and S0.3 below; default and mixed-source behavior have explicit regression assertions. [tests/unit/marine_safety/test_cross_database.py:L84-L112] [tests/unit/marine_safety/test_cross_database_live.py:L221-L231] |
| G1 | Applicable: Python imports and offline pytest; engine output route is local CSV/JSON | S1.1, S1.2, S1.3 and S1.4; the full test set has baseline failures, so no gate clearance is asserted. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L186-L202] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L50-L73] |
| G2 | Applicable: count conservation, group-overlap arithmetic and spherical-distance identities | S2.1 and S2.2; external qualification remains U3. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L609-L676] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643] |
| G3 | NOT_APPLICABLE: this main path aggregates incident records and has no dynamics integration step | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L632-L676] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L34-L73] |
| G4 | NOT_APPLICABLE: this main path emits counts and summaries without a diffraction mesh or hydrodynamic coefficients | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L39-L73] |
| G5 | Applicable: maintain case results, input identity, limits and open-item traceability | S5.1 and S5.2; required evidence follows AQG r0, revision 0, section 9, QA appendix. |


The module CI shard targets the excluded directory, and the selector documents treating no-tests exit 5 as a pass; that pass is not evidence for S1.2. S1.3 measures directory collection separately; it must not be replaced by explicit-file collection. [scripts/ci/select_test_targets.py:L157-L164] [scripts/ci/select_test_targets.py:L216-L218] [tests/conftest.py:L662-L680]

These checks define acceptance criteria for this pack's scope; they do not replace the module's existing assertions or establish family clearance.

| Check | Function, quantity and executable route | Numeric pass criterion and unit | Evidence and gate |
| --- | --- | --- | --- |
| S0.1 | `IncidentsQuery.query(source=maib)` via R1 | 10 schema columns, 0 missing or reordered columns; unit: columns | R1 result; G0. [tests/marine_safety/test_api_on_base.py:L13-L24] [tests/marine_safety/test_api_on_base.py:L33-L41] |
| S0.2 | Analyzer casualty dtypes via `tests/unit/marine_safety/test_cross_database.py::TestSchemaColumns::test_fatalities_is_integer_type` and `test_injuries_is_integer_type` | 2 integer-typed casualty fields, 0 dtype failures; unit: fields/person counts | Two existing pytest results; G0. [tests/unit/marine_safety/test_cross_database.py:L102-L106] |
| S0.3 | `_load_base()` fallback via R3 and R4; inspect mixed-source semantics before interpreting output | 0 mismatches against the two existing freshness assertions; unit: labels; per-source provenance remains a separate gap | Two pytest results; G0. [tests/unit/marine_safety/test_cross_database_live.py:L195-L231] |
| S1.1 | `IncidentsQuery` import and API route via `test_incidents_query_is_typed_query_subclass` and R1 | 2 passing nodes, 0 import/query errors; unit: test nodes | Existing pytest results; G1. [tests/marine_safety/test_api_on_base.py:L27-L41] |
| S1.2 | Complete offline test-file set described below | 0 failed nodes and 0 errors; unit: test outcomes; currently baseline unmet, see section 6 | Baseline and final JUnit results; G1. [tests/unit/marine_safety/test_validators.py:L24-L42] [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14] |
| S1.3 | Directory-mode `pytest tests/unit/marine_safety --collect-only`; compare with explicit-file outcome inventory | At least 2,038 collected test outcomes, 0 excluded dedicated test files; unit: outcomes/files; baseline FAIL, 0 collected instead | Collection log; issue #1239; G1. [tests/conftest.py:L662-L680] |
| S1.4 | `MarineSafety.router()` through R5 and `engine()` | 0 mismatches against total 5, source counts 2 and 3, fire 2, CSV rows 4 and count sum 5; unit: records/rows | R5 workflow output assertions; G1. [docs/registry/workflows.yaml:L152-L174] [tests/workflows/test_durable_workflows.py:L125-L144] |
| S2.1 | `top_incident_types()`, `trend_analysis()`, `risk_hotspots()` and `correlations()` on the arithmetic fixture below | 0 count error in records; 0.0 overlap error in dimensionless fraction | Hand-check output; G2. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L609-L676] |
| S2.2 | `IncidentMatcher._haversine_distance()` on coincident points and a quarter equator | Coincident distance 0.0 km exactly; quarter-circle absolute error at most `1e-9` km, a floating-point allowance against the geometric identity | Hand-check output; G2. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L195-L196] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643] |
| S5.1 | Resolve R1–R5 against the baseline and final result records | 5 matching node IDs; 0 missing results and 0 changed outcomes; unit: case records | Case ledger; G5. [tests/marine_safety/test_api_on_base.py:L33-L41] [tests/unit/marine_safety/test_cross_database_live.py:L195-L231] |
| S5.2 | Hash test-file inputs and compare immutable source bytes with the code pin; resolve citations and item references | 0 source digest mismatches, 0 unresolved citations, 0 unnumbered coverage items; unit: files/references/items | Citation and source audit; G5. |

The arithmetic input has three collision records from two sources and one fire record from a third source, all in one year and region; direct enumeration gives type counts 3 and 1, total count 4, and one shared group out of two groups, or 0.5; the code below is the reproducible audit input rather than a field dataset.

```python
import math
import pandas as pd
from worldenergydata.marine_safety.cross_database import CrossDatabaseAnalyzer
from worldenergydata.marine_safety.analysis.correlation.matcher import IncidentMatcher

data = pd.DataFrame({
    "source": ["maib", "imo", "maib", "tsb"],
    "date": ["2020-01-01"] * 4,
    "incident_type": ["collision", "collision", "collision", "fire"],
    "vessel_type": ["other"] * 4,
    "region": ["other"] * 4,
    "severity": ["moderate"] * 4,
})
a = CrossDatabaseAnalyzer()
assert dict(a.top_incident_types(data).itertuples(index=False, name=None)) == {
    "collision": 3, "fire": 1,
}
assert a.trend_analysis(data)["count"].sum() == 4
assert a.risk_hotspots(data).to_numpy().sum() == 4
assert a.correlations(data)["source_overlap_rate"] == 0.5
m = IncidentMatcher()
assert m._haversine_distance(0.0, 0.0, 0.0, 0.0) == 0.0
expected = math.pi * m.EARTH_RADIUS_KM / 2
assert abs(m._haversine_distance(0.0, 0.0, 0.0, 90.0) - expected) <= 1e-9
```

Offline hand-check result on the code pin: S2.1 PASS with 0 record count error and 0.0 fraction overlap error; S2.2 PASS at the stated kilometer tolerances; this establishes the enumerated fixture and geometric identities only. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L609-L676] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643]

Reproduction of the complete offline test set uses the repository's uv environment, the following explicit test-file discovery, and the same flags before and after this documentation change:

```bash
mapfile -t targets < <(
  rg --files tests/unit/marine_safety tests/modules/marine_safety tests/marine_safety |
    rg '/test_[^/]+\.py$' | sort
)
export COVERAGE_FILE="$TMPDIR/coverage"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HOME="$TMPDIR/huggingface" XDG_CACHE_HOME="$TMPDIR/xdg-cache"
uv run --extra llm python -m pytest "${targets[@]}" \
  tests/integration/cli/test_marine_safety_cli.py \
  'tests/workflows/test_durable_workflows.py::test_registry_workflow_outputs[marine-safety-stats]' \
  -q -rA -p no:cacheprovider --basetemp="$TMPDIR/test-temp" \
  --runslow --allow-existing-tree-changes --continue-on-collection-errors \
  --cov-report=term --cov-report=html:"$TMPDIR/coverage-html" \
  --cov-report=xml:"$TMPDIR/coverage.xml" \
  --cov-report=json:"$TMPDIR/coverage.json" \
  --junitxml="$TMPDIR/results.xml"
```

Explicit files retain the existing collection hooks while allowing individual targets to be exercised despite the directory exclusion; `--continue-on-collection-errors` preserves the error result while running collectable tests, and the existing-tree option verifies that pre-existing documentation edits stay intact. [tests/conftest.py:L480-L493] [tests/conftest.py:L662-L682]

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom, with silent fallbacks first | Cause and detection | Incident or follow-up |
| --- | --- | --- |
| Directory/CI collection silently omits 52 of the 57 dedicated test files | Root `pytest_ignore_collect` excludes the unit directory; S1.3 FAIL: 0 collected, against at least 2,038 explicit-file outcome entries | #1239 (open); 2026-10-15. [tests/conftest.py:L662-L680] [scripts/ci/select_test_targets.py:L157-L164] |
| Reversed year bounds return an empty result without an error | `query()` applies both bounds independently; no detection check exists for rejecting `start_year > end_year` | Issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L547-L550] |
| Negative casualty counts survive normalization | Integer conversion has no nonnegative constraint on this path; no detection check exists for negative counts on source normalization | Issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L269-L279] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L287-L292] |
| Base duplicate detection never rejects a record | `BaseImporter.is_duplicate()` returns false; no detection check exists for duplicate rejection by this base implementation | Issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/base_importer.py:L184-L195] |
| Hatch integration remains skipped with the optional extra installed | Unconditional module mark says “LLM integration tests require --with-llm flag and transformers/torch installed”; S1.2 records 16 SKIP outcomes; no detection check exists for executing those assertions through that flag | Issue pending (7). [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L554-L558] |
| Unit database model file skips at collection | Module-level skip says “Investigation and Personnel models not yet implemented”; S1.2 records one module SKIP, with no measured database result | Issue pending (1). [tests/unit/marine_safety/test_models.py:L9-L14] |
| Three classifier initialization guards previously skipped when the dependency was absent | Existing guards say “transformers library not installed”; with `llm` installed these nodes now run and FAIL at unavailable local model loading or the error-message assertion; S1.2 records the outcomes | Issue pending (7). [tests/unit/marine_safety/analysis/test_llm_classifier.py:L50-L118] |
| Mixed synthetic/observed results labeled `live`; API does not return the freshness metadata | Any successful importer sets the global label; other source rows remain synthetic, and the API returns only `result.data`; S0.3 reproduces current behavior, but no detection check exists for per-row provenance in this API | Related implementation history #207; issue pending (6) for per-source provenance. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L481-L508] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L192-L202] |
| Importer exceptions disappear and invalid records are omitted from the query path | `_load_base()` catches all importer exceptions; `_load_from_importer()` skips `None` and missing IDs; S0.3 detects full fallback, while rejected-row accounting has no detection check in this path | Issue pending (6). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L454-L464] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L481-L489] |
| Failed database batches do not raise from `_commit_batch()` | Rollback and error-count increment; inspect returned statistics before accepting completeness; S1.2 does not independently prove database persistence | No detection check exists for complete persistence on this supplementary route; issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/base_importer.py:L167-L195] |
| Missing related-person data becomes zero casualties in the MAIB importer | `_count_casualties()` returns zero when the occurrence is absent from its cache; S0.2 checks dtype, not missingness semantics | No detection check exists for distinguishing unknown casualties from true zero on this route; issue pending (6). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/maib_importer.py:L226-L247] |
| One vessel identifier can link distinct events | Exact normalized IMO match returns confidence 1.0 before date/location scores; matching needs event-level qualification | No detection check exists for same identifier on different dates in the reviewed main-path tests; issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L296-L309] |
| Missing fixture imports prevent collecting the hatch-analysis file and leave two lazy fixtures unusable | Test file imports `tests.modules.marine_safety.fixtures`; `sample_incident_batch` and `performance_test_data` retain lazy imports of it; S1.2 records the file collection ERROR; no detection check exists for those unused fixtures | #327 is closed history; issue pending (9) for remaining imports; #1239 tracks the directory exclusion. [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14] [tests/unit/marine_safety/conftest.py:L87-L96] [tests/unit/marine_safety/conftest.py:L236-L245] |
| Fifteen scraper tests fail on absent method names | Tests call `fetch_page`, `parse_incident_html`, `scrape_incidents`, PDF download/extraction/metadata methods; S1.2 detects API-contract mismatch | Issue pending (3); distinguish test-contract defects from a verified live acquisition failure. [tests/unit/marine_safety/test_uscg_scraper.py:L77-L139] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/uscg_scraper.py:L277-L350] |
| Thirteen validator tests fail before their intended assertions | Tests construct empty Pydantic models although required data fields are declared; S1.2 detects construction errors | Issue pending (4). [tests/unit/marine_safety/test_validators.py:L24-L42] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/utils/validators.py:L20-L27] |
| Correlation test helper finds no qualifying pair | The test implements its own weighted name/identifier formula instead of calling `IncidentMatcher`; S1.2 detects its failing expectation | Issue pending (5); this test helper is not a reference implementation. [tests/unit/marine_safety/test_correlation.py:L764-L803] |
| Optional classifier tests fail or error at local model loading | The `llm` extra is installed; offline cache has no model fixture; S1.2 records 5 FAIL and 27 setup ERROR outcomes, with no measured classification result | Error suffix: “We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.”; issue pending (7). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/llm_classifier.py:L106-L123] [tests/unit/marine_safety/analysis/test_llm_classifier.py:L50-L142] |
| Statistical report test expects standard output but receives none | `print_report()` logs through the logger; test inspects `capsys.readouterr().out`; S1.2 detects the mismatch | Issue pending (8). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/cause_statistics.py:L250-L275] [tests/unit/marine_safety/analysis/test_cause_statistics.py:L195-L201] |
| PostgreSQL model tests skip on the offline configuration | Repository decorators declare unsupported enum/schema fixtures and field mismatches; S1.2 records the reasons | SKIP with no measured database result; issue pending (1). [tests/modules/marine_safety/test_models.py:L73-L78] [tests/modules/marine_safety/test_models.py:L327-L331] |
| Query output with an unparseable date makes analytics raise | `_add_derived_columns()` coerces dates, but `correlations()` and `trend_analysis()` parse strictly; no detection check exists for invalid-date analytics on query output | Issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L510-L515] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L593-L595] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L640-L646] |
| Reporting identifiers differ across importers and taxonomy | Code names `MSC-MEPC.3/Circ.4/Rev.1`, `MSC-MEPC.3/Circ.4` and `MSC-MEPC.3/Circ.3`; no detection check exists for a consistent publication/edition basis, and no reconciliation is asserted | U3; issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_importer.py:L1-L16] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_taxonomy.py:L32-L37] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/emsa_importer.py:L34-L38] |

Incident observations above were recorded on 2026-10-15 against the header code revision; no source, test, configuration or data correction is included in this pack.

## 7. Lessons log

| Date | Pack record | Lesson | Evidence | Pack change | Shared record |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Initial revision | Distinguish source configuration, successful file loading and mixed synthetic results; do not infer dataset completeness from a global freshness label | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L481-L508] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L192-L202] | Main-path limits, regression R4 and provenance follow-up | Pending, issue pending (1) |
| 2026-10-15 | Initial revision | Compare collection results with discovered files; a directory exclusion can hide nested tests | [tests/conftest.py:L662-L682] | Explicit-file reproduction and test inventory | Pending, issue pending (1) |
| 2026-10-15 | Revision 1 | Install declared extras before interpreting classifier outcomes; preserve ERROR, FAIL and SKIP as measured categories, and distinguish directory collection from explicit-file execution | [pyproject.toml:L161-L166] [tests/conftest.py:L662-L680] | Extra-enabled results, S1.3 and collection defect #1239 | Pending, issue pending (1) |

## 8. Ownership

Required review role: EC quality manager for the data-pipeline scope, using AQG r0, revision 0, section 10, Python calculations; independent sign-off follows AQG r0, revision 0, section 11.

Required producing function: data-pipeline maintainers; numerical-method or classification disagreements go to the EC quality manager, and unresolved scope or assignment decisions go to the maintainers.

UNVERIFIED: U5 — data-pipeline deputy quality-manager assignment, EC index-row update and shared lessons-log registration have not been established, issue pending (1).

## 9. Dependencies and implementation inventory

| Relationship | Source and boundary |
| --- | --- |
| Shared query API | `IncidentsQuery` inherits `TypedQuery` and declares source/category/year filters; normalization is delegated to the shared query base. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L32-L63] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L169-L184] |
| Compatibility inventory row `modules/marine_safety` | One-line re-export of this package; implementation remains here. [src/worldenergydata/modules/marine_safety/__init__.py:L1-L1] |
| Script inventory row `scripts/marine_safety` | Separate consumer and SQL aggregation route; assessed here only as an implementation-map lead, not as package code. [scripts/marine_safety/analyze_marine_safety_database.py:L49-L85] |
| Python dependencies | The domain declares core, NumPy, pandas, SciPy, Plotly, Pydantic, settings, SQLAlchemy, HTTPX, HTML/PDF parsing, rapidfuzz, retry and CLI dependencies. [packages/worldenergydata-marine_safety/pyproject.toml:L31-L48] |
| Source-file importers | The analyzer instantiates MAIB, IMO and TSB file parsers; there is no EMSA live branch in this loader. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L414-L452] |
| Synthetic input | Built-in records and the severity-score mapping live in `_cross_database_data.py`; they supply default and missing-source rows. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/_cross_database_data.py:L1-L23] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L491-L508] |
| Engine consumer | `engine()` routes basename `marine_safety` to `MarineSafety.router()`; the workflow registry also records the bundled CSV statistics workflow. [src/worldenergydata/engine.py:L167-L171] [docs/registry/workflows.yaml:L152-L174] |
| Database route | SQLAlchemy models define relational entities and constraints, separately from the DataFrame query loader. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/database/models.py:L112-L159] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L454-L466] |

### Map revision and counted-family audit

External audit input: digitalmodel, *Implementation map*, `docs/registry/implementation-map.yaml`, map-file commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, embedded data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `families` inventory.

| Audit quantity | Result |
| --- | --- |
| Package boundary | Header package path, including its subpackages |
| Map families with an implementation row inside that package | 0 |
| Required section-9 implementation inventory | Empty: no row belongs to this package |
| Counted families after row-count ranking | 0; ranking and tie-breaking have no members |
| Exact case-sensitive Python `re` signal grep | NOT_APPLICABLE: no map family has an in-package row |
| Further second implementations counted by that grep | NOT_APPLICABLE, rather than a measured zero |
| A8 inventory and grep outcome | PASS for empty inventory; method-family map follow-up remains required |

The audit above is an observation of the named external map revision, not a claim that this package has no algorithms or duplicates.

Map follow-up, issue pending (1): add or assess the section-3 method families before they become counted families: file loading/normalization, incident/region categories, casualty severity, filtered query, descriptive aggregation, source overlap/mean severity, individual record matching (both `IncidentMatcher` and `IncidentCorrelator._compare()`), matching distances/time (both great-circle implementations), database batch import, and the CSV engine summary and further descriptive aggregations inventoried below.

### Repository-wide additional search

The supplementary search covered tracked and nonignored Python sources throughout the repository, including `scripts/`, using `haversine`, `source_overlap_rate`, `_calc_severity`, `normalize_severity`, `calculate_severity`, `IncidentMatcher`, `IncidentCorrelator`, `6371`, `radians`, `asin`, `distance`, `get_severity_distribution`, `calculate_cause_severity_crosstab`, `top_incident_types` and `trend_analysis`; this exploratory vocabulary is separate from the absent counted-family search.

| Definition or route | Classification and evidence |
| --- | --- |
| `IncidentsQuery.trends`, `top_types`, `correlations`, `risk_hotspots` | Helpers delegating to the listed analyzer; no independent aggregation implementation. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L204-L291] |
| `MarineSafety._run_incident_stats` | Delegates trend and type counts; independently builds summary source counts by `value_counts()`, already listed in section 1. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L39-L66] |
| `IncidentCorrelator._compare` and module-level `_haversine` | Second in-package matching and great-circle implementations, using linear location scoring and Jaccard name similarity with different defaults from `IncidentMatcher`; map follow-up issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L26-L47] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L175-L218] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L357-L373] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L403-L419] |
| `HatchStatistics.get_severity_distribution`, `DataQualityDashboard._calculate_severity_distribution`, `CauseStatistics.calculate_cause_severity_crosstab` | Further descriptive aggregations of existing severity labels, not casualty-severity formulas; map follow-up issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/hatch_statistics.py:L94-L112] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/reports/quality_dashboard.py:L860-L881] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/cause_statistics.py:L632-L678] |
| `DataNormalizer.normalize_severity` | Further in-package numeric severity policy; separate from `_calc_severity()`, now inventoried here, map follow-up issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/processors/data_normalizer.py:L274-L330] |
| `imo_parser.calculate_severity` | Further in-package casualty-severity calculation, now inventoried here; its importer re-exports are helpers, map follow-up issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_parser.py:L299-L328] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_importer.py:L57-L67] |
| `NTSBImporter._calculate_severity`, `ATSBImporter._calculate_severity` | Further in-package severity calculations, now inventoried here; map follow-up issue pending (1). [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/ntsb_importer.py:L563-L598] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/atsb_importer.py:L725-L763] |
| `haversine_nm` in the marine domain | Independent nautical-mile distance implementation outside this package; map gap, not an A8 miss. [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L42-L67] |
| `haversine_miles` in the infrastructure spatial module | Independent mile distance implementation outside this package; map gap, not an A8 miss. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/spatial.py:L39-L54] |
| `scripts/marine_safety/analyze_marine_safety_database.py::analyze_database` | Independent SQL counts by source and type outside this package; map follow-up, with no equivalence claim for its database inputs. [scripts/marine_safety/analyze_marine_safety_database.py:L49-L85] |
| `tests/unit/marine_safety/test_correlation.py` helpers | Test-local formulas and scoring are test evidence, not production misses; the failing helper expectation is in section 6. [tests/unit/marine_safety/test_correlation.py:L764-L803] |

## 10. Coverage and open items

This revision completes sections 1–6 for the main query/aggregation path and records the remaining detailed coverage explicitly; no live acquisition, production database population or external-source census was performed.

### Open-item register

| Item | Scope or limitation | Responsible function | Issue |
| --- | --- | --- | --- |
| C1 | Finish method-by-method assessment of the inventory below, source-format units, invalid dates, reversed year bounds, negative casualties, base duplicate detection, inconsistent reference identifiers, supplementary database/import/classification/report paths, shared tests and all discovered documentation; add independent worked examples, method-map coverage and review assignments | Data-pipeline maintainers | issue pending (1) |
| C2 | Complete source dataset acquisition and document observed population, date range and freshness; no inferred record-count target is adopted here | Data-pipeline maintainers | #153; [docs/data-sources/DATA_ACQUISITION_GUIDE.md:L35-L48] |
| C3 | Verify knowledge-pack exclusion from wheel payloads; existing recursive Markdown glob is a packaging concern | Package maintainers | issue pending (2); [packages/worldenergydata-marine_safety/pyproject.toml:L69-L70] |
| C4 | Resolve scraper test/API mismatch and rerun the 15 failures | Data-pipeline maintainers | issue pending (3); [tests/unit/marine_safety/test_uscg_scraper.py:L77-L139] |
| C5 | Resolve validator construction/API mismatch and rerun the 13 failures | Data-pipeline maintainers | issue pending (4); [tests/unit/marine_safety/test_validators.py:L24-L42] |
| C6 | Replace or qualify the test-local correlation helper expectation | Data-pipeline maintainers | issue pending (5); [tests/unit/marine_safety/test_correlation.py:L764-L803] |
| C7 | Expose per-source provenance, fallback reasons and unknown-casualty handling to query consumers | Data-pipeline maintainers | issue pending (6); [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L454-L508] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L192-L202] |
| C8 | Restore directory-mode collection and the hatch test-file import; correct lazy imports in `sample_incident_batch` and `performance_test_data`; closed #327 remains history | Test maintainers | #1239; issue pending (9). [tests/conftest.py:L662-L680] [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14] [tests/unit/marine_safety/conftest.py:L87-L96] [tests/unit/marine_safety/conftest.py:L236-L245] |
| C9 | Establish optional classifier dependency tests without requiring unrecorded model downloads | Test maintainers | issue pending (7); [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/llm_classifier.py:L106-L123] |
| C10 | Reconcile report logging with standard-output assertions | Test maintainers | issue pending (8); [tests/unit/marine_safety/analysis/test_cause_statistics.py:L195-L201] |
| U1 | UNVERIFIED: README maturity, capability counts and asynchronous-operation claims outside the assessed main path | Data-pipeline maintainers | issue pending (1); [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/README.md:L3-L8] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/README.md:L55-L85] |
| U2 | UNVERIFIED: coordinate datum, longitude sign, timezone and complete per-format unit contracts | Data-pipeline maintainers | issue pending (1); [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/database/models.py:L112-L134] |
| U3 | UNVERIFIED: independent taxonomy, severity/matching calibration, unconfirmed publication titles, editions and clause bases and source completeness | EC quality manager | issue pending (1); [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_importer.py:L1-L16] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L269-L279] |
| U4 | UNVERIFIED: exclusion of this knowledge pack from a rebuilt wheel | Package maintainers | issue pending (2); [packages/worldenergydata-marine_safety/pyproject.toml:L69-L70] |
| U5 | UNVERIFIED: data-pipeline deputy assignment, EC index-row update and shared lessons-log registration | Maintainers | issue pending (1) |

The calculation-output citation contract was readable as a supporting instruction; this change introduces no standards-derived runtime constant or numerical payload sidecar, and U3 retains the unresolved publication basis rather than inventing one.

### Python source inventory

All 85 Python files were read for syntax-tree inventory; full line-by-line assessment is claimed only for the three main-path files, with inspected supporting excerpts distinguished below and remaining detailed coverage assigned to C1, issue pending (1).

| File | Coverage | Evidence at the code pin |
| --- | --- | --- |
| `__init__.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/__init__.py:L1-L8] |
| `_cross_database_data.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/_cross_database_data.py:L1-L8] |
| `acquirers/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/acquirers/__init__.py:L1-L8] |
| `acquirers/ntsb_carol_acquirer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/acquirers/ntsb_carol_acquirer.py:L1-L8] |
| `acquirers/uscg_misle_acquirer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/acquirers/uscg_misle_acquirer.py:L1-L8] |
| `analysis/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/__init__.py:L1-L8] |
| `analysis/cause_analyzer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/cause_analyzer.py:L1-L8] |
| `analysis/cause_report.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/cause_report.py:L1-L8] |
| `analysis/cause_statistics.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/cause_statistics.py:L1-L8] |
| `analysis/cause_visualizations.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/cause_visualizations.py:L1-L8] |
| `analysis/correlation/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/__init__.py:L1-L8] |
| `analysis/correlation/deduplicator.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/deduplicator.py:L1-L8] |
| `analysis/correlation/matcher.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L1-L8] |
| `analysis/incidents/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/__init__.py:L1-L8] |
| `analysis/incidents/column_maps.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/column_maps.py:L1-L8] |
| `analysis/incidents/hatch_analysis.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/hatch_analysis.py:L1-L8] |
| `analysis/incidents/hatch_detection.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/hatch_detection.py:L1-L8] |
| `analysis/incidents/hatch_maloperation_analysis.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/hatch_maloperation_analysis.py:L1-L8] |
| `analysis/incidents/hatch_patterns.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/hatch_patterns.py:L1-L8] |
| `analysis/incidents/hatch_reports.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/hatch_reports.py:L1-L8] |
| `analysis/incidents/hatch_statistics.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/hatch_statistics.py:L1-L8] |
| `analysis/incidents/incident_correlator.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L1-L8] |
| `analysis/incidents/incident_taxonomy.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_taxonomy.py:L1-L8] |
| `analysis/incidents/maib_loader.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/maib_loader.py:L1-L8] |
| `analysis/incidents/ntsb_marine_loader.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/ntsb_marine_loader.py:L1-L8] |
| `analysis/incidents/operation_phase.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/operation_phase.py:L1-L8] |
| `analysis/incidents/uscg_client.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/uscg_client.py:L1-L8] |
| `analysis/llm_classifier.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/llm_classifier.py:L1-L8] |
| `api.py` | Main path assessed | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/api.py:L1-L8] |
| `cli.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli.py:L1-L8] |
| `cli_correlate.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_correlate.py:L1-L8] |
| `cli_db.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_db.py:L1-L8] |
| `cli_export.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_export.py:L1-L8] |
| `cli_import.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_import.py:L1-L8] |
| `cli_refresh.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_refresh.py:L1-L8] |
| `cli_scrape.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_scrape.py:L1-L8] |
| `cli_stats.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_stats.py:L1-L8] |
| `cli_utils.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cli_utils.py:L1-L8] |
| `config.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/config.py:L1-L8] |
| `constants.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/constants.py:L1-L8] |
| `cross_database.py` | Main path assessed | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/cross_database.py:L1-L8] |
| `database/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/database/__init__.py:L1-L8] |
| `database/db_manager.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/database/db_manager.py:L1-L8] |
| `database/init_db.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/database/init_db.py:L1-L8] |
| `database/models.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/database/models.py:L1-L8] |
| `examples/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/examples/__init__.py:L1-L1] |
| `examples/cross_database_case_study.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/examples/cross_database_case_study.py:L1-L8] |
| `exceptions.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/exceptions.py:L1-L8] |
| `importers/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/__init__.py:L1-L8] |
| `importers/atsb_importer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/atsb_importer.py:L1-L8] |
| `importers/base_importer.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/base_importer.py:L1-L8] |
| `importers/boating_importer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/boating_importer.py:L1-L8] |
| `importers/emsa_importer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/emsa_importer.py:L1-L8] |
| `importers/imo_importer.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_importer.py:L1-L8] |
| `importers/imo_mappings.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_mappings.py:L1-L8] |
| `importers/imo_normalizers.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_normalizers.py:L1-L8] |
| `importers/imo_parser.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_parser.py:L1-L8] |
| `importers/imo_validators.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/imo_validators.py:L1-L8] |
| `importers/maib_importer.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/maib_importer.py:L1-L8] |
| `importers/misle_importer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/misle_importer.py:L1-L8] |
| `importers/noaa_importer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/noaa_importer.py:L1-L8] |
| `importers/ntsb_importer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/ntsb_importer.py:L1-L8] |
| `importers/tsb_importer.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/importers/tsb_importer.py:L1-L8] |
| `marine_safety.py` | Main path assessed | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/marine_safety.py:L1-L8] |
| `processors/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/processors/__init__.py:L1-L8] |
| `processors/base_processor.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/processors/base_processor.py:L1-L8] |
| `processors/data_cleaner.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/processors/data_cleaner.py:L1-L8] |
| `processors/data_normalizer.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/processors/data_normalizer.py:L1-L8] |
| `reports/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/reports/__init__.py:L1-L8] |
| `reports/quality_dashboard.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/reports/quality_dashboard.py:L1-L8] |
| `scrapers/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/__init__.py:L1-L8] |
| `scrapers/atsb_checkpoint.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_checkpoint.py:L1-L8] |
| `scrapers/atsb_constants.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_constants.py:L1-L8] |
| `scrapers/atsb_exceptions.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_exceptions.py:L1-L8] |
| `scrapers/atsb_extractor.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_extractor.py:L1-L8] |
| `scrapers/atsb_parser.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_parser.py:L1-L8] |
| `scrapers/atsb_scraper.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_scraper.py:L1-L8] |
| `scrapers/atsb_transformer.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_transformer.py:L1-L8] |
| `scrapers/atsb_validator.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/atsb_validator.py:L1-L8] |
| `scrapers/base_scraper.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/base_scraper.py:L1-L8] |
| `scrapers/ntsb_scraper.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/ntsb_scraper.py:L1-L8] |
| `scrapers/uscg_scraper.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/scrapers/uscg_scraper.py:L1-L8] |
| `utils/__init__.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/utils/__init__.py:L1-L8] |
| `utils/logger.py` | Inventoried; detailed assessment C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/utils/logger.py:L1-L8] |
| `utils/validators.py` | Supporting excerpts assessed; remainder C1 | [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/utils/validators.py:L1-L8] |

### Test inventory and offline results

The current BASE and AFTER commands use 56 discovered test files plus the dedicated CLI integration file and the single R5 workflow node (58 files). Both commands ran against `de90ed1413b3f291f60fba625a8b8bac3233122c`, with AFTER using the uncommitted documentation tree; package and test source bytes match the preserved header code pin and `origin/main`. JUnit records 2,143 individual collected nodes, one module collection skip and one module collection error: 2,145 entries comprising 2,046 PASS, 35 FAIL, 28 ERROR and 36 SKIP outcomes. NOT_RUN: 0. The 28 errors comprise 27 setup errors and one collection error; the 36 skips comprise 35 individual skips and one module collection skip.

The `llm` optional extra is installed in both runs. Classification has no measured result for model-loading failures or setup errors; these remain FAIL and ERROR outcomes, rather than additional NOT_RUN entries. Relative to the prior environment, three initialization guards now run instead of skipping, and R5 adds one passing workflow node. The unconditional 16-test integration skip remains despite the installed extra. [pyproject.toml:L161-L166] [tests/unit/marine_safety/analysis/test_llm_classifier.py:L50-L142] [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L554-L558]

The model-loading error suffix is quoted in section 6; the collection error is `ModuleNotFoundError: No module named 'tests.modules.marine_safety.fixtures'`. Model access stays offline through `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; no solver, licensed interface or source-data download was used. [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14]

| Test file | Passed | Failed | Setup/collection errors | Skipped | Evidence |
| --- | --- | --- | --- | --- | --- |
| `tests/integration/cli/test_marine_safety_cli.py` | 28 | 0 | 0 | 0 | [tests/integration/cli/test_marine_safety_cli.py:L1-L8] |
| `tests/marine_safety/test_api_on_base.py` | 5 | 0 | 0 | 0 | [tests/marine_safety/test_api_on_base.py:L1-L8] |
| `tests/modules/marine_safety/analysis/test_cause_analyzer.py` | 28 | 0 | 0 | 0 | [tests/modules/marine_safety/analysis/test_cause_analyzer.py:L1-L8] |
| `tests/modules/marine_safety/analysis/test_cause_report.py` | 26 | 0 | 0 | 0 | [tests/modules/marine_safety/analysis/test_cause_report.py:L1-L8] |
| `tests/modules/marine_safety/test_models.py` | 0 | 0 | 0 | 19 | [tests/modules/marine_safety/test_models.py:L1-L8] |
| `tests/unit/marine_safety/analysis/incidents/test_hatch_analysis.py` | 42 | 0 | 0 | 0 | [tests/unit/marine_safety/analysis/incidents/test_hatch_analysis.py:L1-L8] |
| `tests/unit/marine_safety/analysis/incidents/test_hatch_patterns.py` | 25 | 0 | 0 | 0 | [tests/unit/marine_safety/analysis/incidents/test_hatch_patterns.py:L1-L8] |
| `tests/unit/marine_safety/analysis/incidents/test_incident_taxonomy.py` | 115 | 0 | 0 | 0 | [tests/unit/marine_safety/analysis/incidents/test_incident_taxonomy.py:L1-L8] |
| `tests/unit/marine_safety/analysis/incidents/test_maib_loader.py` | 44 | 0 | 0 | 0 | [tests/unit/marine_safety/analysis/incidents/test_maib_loader.py:L1-L8] |
| `tests/unit/marine_safety/analysis/incidents/test_ntsb_marine_loader.py` | 62 | 0 | 0 | 0 | [tests/unit/marine_safety/analysis/incidents/test_ntsb_marine_loader.py:L1-L8] |
| `tests/unit/marine_safety/analysis/test_cause_analyzer.py` | 50 | 0 | 0 | 0 | [tests/unit/marine_safety/analysis/test_cause_analyzer.py:L1-L8] |
| `tests/unit/marine_safety/analysis/test_cause_report.py` | 20 | 0 | 0 | 0 | [tests/unit/marine_safety/analysis/test_cause_report.py:L1-L8] |
| `tests/unit/marine_safety/analysis/test_cause_statistics.py` | 13 | 1 | 0 | 0 | [tests/unit/marine_safety/analysis/test_cause_statistics.py:L1-L8] |
| `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py` | 0 | 0 | 0 | 16 | [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L1-L8] |
| `tests/unit/marine_safety/analysis/test_llm_classifier.py` | 0 | 5 | 27 | 0 | [tests/unit/marine_safety/analysis/test_llm_classifier.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_atsb_importer.py` | 65 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_atsb_importer.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_boating_importer.py` | 67 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_boating_importer.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_emsa_importer.py` | 19 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_emsa_importer.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_imo_importer.py` | 16 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_imo_importer.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_imo_normalizers.py` | 31 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_imo_normalizers.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_imo_parser.py` | 48 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_imo_parser.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_imo_validators.py` | 27 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_imo_validators.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_maib_importer.py` | 12 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_maib_importer.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_noaa_importer.py` | 31 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_noaa_importer.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_ntsb_importer.py` | 43 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_ntsb_importer.py:L1-L8] |
| `tests/unit/marine_safety/importers/test_tsb_importer.py` | 13 | 0 | 0 | 0 | [tests/unit/marine_safety/importers/test_tsb_importer.py:L1-L8] |
| `tests/unit/marine_safety/processors/test_base_processor.py` | 10 | 0 | 0 | 0 | [tests/unit/marine_safety/processors/test_base_processor.py:L1-L8] |
| `tests/unit/marine_safety/processors/test_data_cleaner.py` | 52 | 0 | 0 | 0 | [tests/unit/marine_safety/processors/test_data_cleaner.py:L1-L8] |
| `tests/unit/marine_safety/processors/test_data_normalizer.py` | 73 | 0 | 0 | 0 | [tests/unit/marine_safety/processors/test_data_normalizer.py:L1-L8] |
| `tests/unit/marine_safety/reports/test_quality_dashboard.py` | 20 | 0 | 0 | 0 | [tests/unit/marine_safety/reports/test_quality_dashboard.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_atsb_checkpoint.py` | 17 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_atsb_checkpoint.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_atsb_constants.py` | 33 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_atsb_constants.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_atsb_exceptions.py` | 8 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_atsb_exceptions.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_atsb_extractor.py` | 19 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_atsb_extractor.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_atsb_parser.py` | 17 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_atsb_parser.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_atsb_transformer.py` | 16 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_atsb_transformer.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_atsb_validator.py` | 16 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_atsb_validator.py:L1-L8] |
| `tests/unit/marine_safety/scrapers/test_ntsb_scraper.py` | 29 | 0 | 0 | 0 | [tests/unit/marine_safety/scrapers/test_ntsb_scraper.py:L1-L8] |
| `tests/unit/marine_safety/test_atsb_importer.py` | 202 | 0 | 0 | 0 | [tests/unit/marine_safety/test_atsb_importer.py:L1-L8] |
| `tests/unit/marine_safety/test_cause_statistics.py` | 17 | 0 | 0 | 0 | [tests/unit/marine_safety/test_cause_statistics.py:L1-L8] |
| `tests/unit/marine_safety/test_cause_visualizations.py` | 31 | 0 | 0 | 0 | [tests/unit/marine_safety/test_cause_visualizations.py:L1-L8] |
| `tests/unit/marine_safety/test_cli_commands.py` | 20 | 0 | 0 | 0 | [tests/unit/marine_safety/test_cli_commands.py:L1-L8] |
| `tests/unit/marine_safety/test_cli_utils.py` | 12 | 0 | 0 | 0 | [tests/unit/marine_safety/test_cli_utils.py:L1-L8] |
| `tests/unit/marine_safety/test_constants.py` | 34 | 0 | 0 | 0 | [tests/unit/marine_safety/test_constants.py:L1-L8] |
| `tests/unit/marine_safety/test_correlation.py` | 71 | 1 | 0 | 0 | [tests/unit/marine_safety/test_correlation.py:L1-L8] |
| `tests/unit/marine_safety/test_cross_database.py` | 54 | 0 | 0 | 0 | [tests/unit/marine_safety/test_cross_database.py:L1-L8] |
| `tests/unit/marine_safety/test_cross_database_live.py` | 55 | 0 | 0 | 0 | [tests/unit/marine_safety/test_cross_database_live.py:L1-L8] |
| `tests/unit/marine_safety/test_exceptions.py` | 42 | 0 | 0 | 0 | [tests/unit/marine_safety/test_exceptions.py:L1-L8] |
| `tests/unit/marine_safety/test_hatch_maloperation_analysis.py` | 0 | 0 | 1 | 0 | [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L1-L8] |
| `tests/unit/marine_safety/test_imo_importer.py` | 149 | 0 | 0 | 0 | [tests/unit/marine_safety/test_imo_importer.py:L1-L8] |
| `tests/unit/marine_safety/test_models.py` | 0 | 0 | 0 | 1 | [tests/unit/marine_safety/test_models.py:L1-L8] |
| `tests/unit/marine_safety/test_ntsb_importer.py` | 76 | 0 | 0 | 0 | [tests/unit/marine_safety/test_ntsb_importer.py:L1-L8] |
| `tests/unit/marine_safety/test_refresh_cli.py` | 48 | 0 | 0 | 0 | [tests/unit/marine_safety/test_refresh_cli.py:L1-L8] |
| `tests/unit/marine_safety/test_report_verification.py` | 48 | 0 | 0 | 0 | [tests/unit/marine_safety/test_report_verification.py:L1-L8] |
| `tests/unit/marine_safety/test_uscg_scraper.py` | 3 | 15 | 0 | 0 | [tests/unit/marine_safety/test_uscg_scraper.py:L1-L8] |
| `tests/unit/marine_safety/test_validators.py` | 0 | 13 | 0 | 0 | [tests/unit/marine_safety/test_validators.py:L1-L8] |
| `tests/unit/marine_safety/utils/test_validators.py` | 43 | 0 | 0 | 0 | [tests/unit/marine_safety/utils/test_validators.py:L1-L8] |
| `tests/workflows/test_durable_workflows.py` (R5 only) | 1 | 0 | 0 | 0 | [tests/workflows/test_durable_workflows.py:L125-L144] |

Every nonpassing node in the baseline is recorded below; dependency and database skips retain their existing decorators and configuration, with no new skip or quarantine entry.

#### Failed

- `tests/unit/marine_safety/analysis/test_cause_statistics.py::TestStatisticalSummary::test_print_report` [tests/unit/marine_safety/analysis/test_cause_statistics.py:L195-L201]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_llm_classifier_initialization` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L51-L68]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_model_loading_with_cache` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L70-L92]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_fallback_on_model_load_failure` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L94-L118]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestLLMClassifierInitialization::test_custom_model_path` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L120-L129]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_repeated_initialization` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L603-L617]
- `tests/unit/marine_safety/test_correlation.py::TestIncidentMatcherConfidence::test_find_matches_returns_above_threshold` [tests/unit/marine_safety/test_correlation.py:L764-L803]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_success` [tests/unit/marine_safety/test_uscg_scraper.py:L78-L86]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_timeout` [tests/unit/marine_safety/test_uscg_scraper.py:L90-L95]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_fetch_page_connection_error` [tests/unit/marine_safety/test_uscg_scraper.py:L99-L104]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_retry_on_failure` [tests/unit/marine_safety/test_uscg_scraper.py:L108-L120]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_max_retries_exceeded` [tests/unit/marine_safety/test_uscg_scraper.py:L124-L132]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_html` [tests/unit/marine_safety/test_uscg_scraper.py:L135-L143]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_empty_html` [tests/unit/marine_safety/test_uscg_scraper.py:L146-L151]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_parse_malformed_html` [tests/unit/marine_safety/test_uscg_scraper.py:L154-L160]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestUSCGScraper::test_scrape_incidents_date_range` [tests/unit/marine_safety/test_uscg_scraper.py:L164-L177]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_download_pdf_success` [tests/unit/marine_safety/test_uscg_scraper.py:L185-L195]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_extract_pdf_text` [tests/unit/marine_safety/test_uscg_scraper.py:L210-L221]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestPDFExtraction::test_parse_pdf_metadata` [tests/unit/marine_safety/test_uscg_scraper.py:L224-L239]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_http_500_error` [tests/unit/marine_safety/test_uscg_scraper.py:L247-L255]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_invalid_ssl_certificate` [tests/unit/marine_safety/test_uscg_scraper.py:L259-L264]
- `tests/unit/marine_safety/test_uscg_scraper.py::TestErrorHandling::test_network_timeout_recovery` [tests/unit/marine_safety/test_uscg_scraper.py:L274-L281]
- `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_valid_incident_data` [tests/unit/marine_safety/test_validators.py:L25-L42]
- `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_missing_required_fields` [tests/unit/marine_safety/test_validators.py:L45-L57]
- `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_casualties_validation` [tests/unit/marine_safety/test_validators.py:L60-L72]
- `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_negative_casualties` [tests/unit/marine_safety/test_validators.py:L75-L82]
- `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_severity_type_consistency` [tests/unit/marine_safety/test_validators.py:L85-L97]
- `tests/unit/marine_safety/test_validators.py::TestIncidentValidator::test_location_validation` [tests/unit/marine_safety/test_validators.py:L100-L116]
- `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_valid_vessel_data` [tests/unit/marine_safety/test_validators.py:L123-L137]
- `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_vessel_name_required` [tests/unit/marine_safety/test_validators.py:L140-L147]
- `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_gross_tonnage_positive` [tests/unit/marine_safety/test_validators.py:L150-L157]
- `tests/unit/marine_safety/test_validators.py::TestVesselValidator::test_year_built_range` [tests/unit/marine_safety/test_validators.py:L160-L174]
- `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_pollution_environmental_impact` [tests/unit/marine_safety/test_validators.py:L181-L196]
- `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_critical_severity_requires_investigation` [tests/unit/marine_safety/test_validators.py:L199-L211]
- `tests/unit/marine_safety/test_validators.py::TestCrossFieldValidation::test_vessel_incident_consistency` [tests/unit/marine_safety/test_validators.py:L214-L223]

#### Setup and collection errors

- `tests/unit/marine_safety/test_hatch_maloperation_analysis.py` [tests/unit/marine_safety/test_hatch_maloperation_analysis.py:L11-L14]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classify_hatch_maloperation_positive` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L144-L153]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classify_hatch_maloperation_negative` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L155-L164]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_confidence_scores_returned` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L166-L173]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_batch_classification` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L175-L188]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestBasicClassification::test_classification_determinism` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L190-L199]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_hatch_not_closed` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L214-L228]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_opening_maloperation` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L230-L244]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_engine_room_access_failure` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L246-L260]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_detect_watertight_door_issue` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L262-L276]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestHatchDetectionPatterns::test_negative_case_no_hatch_incident` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L278-L286]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_empty_text_handling` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L301-L308]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_none_value_handling` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L310-L318]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_whitespace_only_handling` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L320-L325]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_very_long_text_handling` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L327-L333]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_multilingual_text` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L335-L346]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_special_characters_handling` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L348-L358]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestEdgeCases::test_numeric_only_text` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L360-L365]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_batch_processing_faster_than_individual` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L380-L398]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_classification_within_time_limit` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L400-L410]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_batch_throughput` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L412-L424]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestPerformance::test_memory_usage_stability` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L427-L452]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_positive_case_accuracy` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L467-L478]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_negative_case_accuracy` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L480-L491]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_confidence_calibration` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L493-L506]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestClassificationAccuracy::test_f1_score_calculation` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L508-L553]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_concurrent_classification` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L568-L579]
- `tests/unit/marine_safety/analysis/test_llm_classifier.py::TestRobustness::test_error_recovery` [tests/unit/marine_safety/analysis/test_llm_classifier.py:L581-L601]

#### Existing skips

- `tests/unit/marine_safety/test_models.py` [tests/unit/marine_safety/test_models.py:L11-L14]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_create_incident_minimal` [tests/modules/marine_safety/test_models.py:L81-L97]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_create_incident_full` [tests/modules/marine_safety/test_models.py:L100-L125]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_incident_date_required` [tests/modules/marine_safety/test_models.py:L128-L139]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_vessel_relationship` [tests/modules/marine_safety/test_models.py:L142-L157]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_latitude_constraint_valid` [tests/modules/marine_safety/test_models.py:L160-L173]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_longitude_constraint_valid` [tests/modules/marine_safety/test_models.py:L176-L189]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_created_at_auto_generated` [tests/modules/marine_safety/test_models.py:L192-L206]
- `tests/modules/marine_safety/test_models.py::TestMarineIncidentModel::test_updated_at_auto_updated` [tests/modules/marine_safety/test_models.py:L209-L228]
- `tests/modules/marine_safety/test_models.py::TestVesselModel::test_create_vessel_minimal` [tests/modules/marine_safety/test_models.py:L239-L249]
- `tests/modules/marine_safety/test_models.py::TestVesselModel::test_vessel_company_relationship` [tests/modules/marine_safety/test_models.py:L252-L262]
- `tests/modules/marine_safety/test_models.py::TestVesselModel::test_vessel_incidents_relationship` [tests/modules/marine_safety/test_models.py:L265-L286]
- `tests/modules/marine_safety/test_models.py::TestVesselModel::test_imo_number_unique` [tests/modules/marine_safety/test_models.py:L289-L310]
- `tests/modules/marine_safety/test_models.py::TestVesselModel::test_gross_tonnage_positive` [tests/modules/marine_safety/test_models.py:L313-L324]
- `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_create_company_minimal` [tests/modules/marine_safety/test_models.py:L335-L344]
- `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_company_vessels_relationship` [tests/modules/marine_safety/test_models.py:L347-L360]
- `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_imo_number_unique_company` [tests/modules/marine_safety/test_models.py:L363-L374]
- `tests/modules/marine_safety/test_models.py::TestCompanyModel::test_company_active_default` [tests/modules/marine_safety/test_models.py:L377-L384]
- `tests/modules/marine_safety/test_models.py::TestEnums::test_incident_type_enum` [tests/modules/marine_safety/test_models.py:L394-L400]
- `tests/modules/marine_safety/test_models.py::TestEnums::test_severity_level_enum` [tests/modules/marine_safety/test_models.py:L403-L408]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_hatch_analyzer_with_llm_enabled` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L52-L73]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_hatch_analyzer_llm_vs_regex_comparison` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L75-L102]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_hybrid_detection_fallback` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L104-L140]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_llm_confidence_threshold` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L142-L168]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestHatchAnalyzerWithLLM::test_batch_processing_consistency` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L170-L194]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMPerformanceIntegration::test_large_dataset_processing_time` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L226-L242]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMPerformanceIntegration::test_memory_efficiency_large_dataset` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L244-L270]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMErrorHandling::test_graceful_handling_of_null_narratives` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L301-L317]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMErrorHandling::test_handling_of_malformed_data` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L319-L341]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestLLMErrorHandling::test_partial_llm_failure_handling` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L343-L370]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestAnalysisReportGeneration::test_generate_analysis_report_with_confidence` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L427-L443]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestAnalysisReportGeneration::test_confidence_distribution_in_report` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L445-L457]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestAnalysisReportGeneration::test_temporal_analysis_with_llm_results` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L459-L469]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestConfigurationOptions::test_custom_model_configuration` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L492-L503]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestConfigurationOptions::test_disable_llm_configuration` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L505-L519]
- `tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py::TestConfigurationOptions::test_batch_size_configuration` [tests/unit/marine_safety/analysis/test_hatch_maloperation_integration.py:L521-L538]

### Shared tests discovered outside the dedicated module test set

These shared-domain files mention the module and were discovered for follow-up; only the marine-safety-stats output node is executed here from the workflow file; complete cross-domain suites remain outside this revision's executed test set, C1, issue pending (1).

- [tests/workflows/test_durable_workflows.py:L178-L178]
- [tests/modules/marketing/test_hurricane_mooring_risk_infographic.py:L18-L18]
- [tests/test_query_api.py:L1-L1]
- [tests/integration/test_data_symlink.py:L5-L5]
- [tests/integration/cli/test_main_cli.py:L59-L59]
- [tests/unit/ci/test_flake8_inventory_report.py:L22-L22]
- [tests/unit/cli/test_cli_smoke.py:L71-L71]
- [tests/unit/cli/test_docs_coverage.py:L20-L20]
- [tests/unit/cli/test_cli_smoke_verify_script.py:L33-L33]
- [tests/unit/safety_analysis/risk_index/test_data_assembler.py:L515-L515]
- [tests/unit/safety_analysis/taxonomy/test_incident_classifier.py:L132-L132]
- [tests/unit/safety_analysis/taxonomy/test_taxonomy_cli.py:L51-L51]

### Documentation discovered

The package README and the following Markdown files under `docs/` were found by a case-insensitive search for the module name with underscore, hyphen or space; matching passages were inspected for discovery, while complete reconciliation of their capability and data claims is C1, issue pending (1).

- [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/README.md:L1-L8]
- [docs/AI_USAGE_GUIDELINES.md:L53-L53]
- [docs/CLI.md:L133-L133]
- [docs/IMO_GISIS_DOWNLOAD_SETUP.md:L179-L179]
- [docs/MIGRATION_GUIDE.md:L57-L57]
- [docs/adr/0001-domain-package-split.md:L42-L42]
- [docs/ci/flake8-inventory-2026-04-23.md:L20-L20]
- [docs/data-sources/AVAILABLE_DATA_SOURCES.md:L46-L46]
- [docs/data-sources/DATA_ACQUISITION_GUIDE.md:L1-L1]
- [docs/data-sources/DOWNLOAD_INSTRUCTIONS.md:L35-L35]
- [docs/data-sources/FINAL_DATA_ACQUISITION_SUMMARY.md:L1-L1]
- [docs/data-sources/IMPORT_DEMONSTRATION.md:L186-L186]
- [docs/data-sources/INDUSTRIAL_MARITIME_DATA_SOURCES.md:L931-L931]
- [docs/data-sources/MANUAL_DOWNLOAD_GUIDE.md:L1-L1]
- [docs/data-sources/MANUAL_DOWNLOAD_REQUIRED.md:L38-L38]
- [docs/data-sources/MARINE_SAFETY_IMPORT_STATUS.md:L1-L1]
- [docs/data-sources/PHASE_2_IMPORT_COMPLETE.md:L1-L1]
- [docs/guides/QUICK_START.md:L32-L32]
- [docs/guides/QUICK_START_MARINE_REPORTS.md:L1-L1]
- [docs/guides/user_prompt.md:L11-L11]
- [docs/marine-safety-data-sources-comprehensive.md:L1-L1]
- [docs/modules/marine_safety/CAUSE_REPORT_MODULE.md:L5-L5]
- [docs/modules/marine_safety/COMMAND_LINE_ANALYSIS.md:L1-L1]
- [docs/modules/marine_safety/COMMAND_LINE_REPORT_SYSTEM_COMPLETE.md:L1-L1]
- [docs/modules/marine_safety/INCIDENT_CAUSE_ANALYSIS_MODULE.md:L1-L1]
- [docs/modules/marine_safety/LLM_DOCUMENTATION_SUMMARY.md:L4-L4]
- [docs/modules/marine_safety/LLM_INTEGRATION_COMPLETE.md:L1-L1]
- [docs/modules/marine_safety/LLM_INTEGRATION_GUIDE.md:L1-L1]
- [docs/modules/marine_safety/analysis/IMPLEMENTATION_SUMMARY.md:L4-L4]
- [docs/modules/marine_safety/analysis/cause_report_summary.md:L5-L5]
- [docs/modules/marine_safety/cause_mapping_reference.md:L481-L481]
- [docs/modules/marine_safety/hatch_maloperation_analysis.md:L5-L5]
- [docs/modules/marine_safety/incident_cause_research.md:L1-L1]
- [docs/modules/repository-architecture.md:L31-L31]
- [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L14-L14]
- [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L14-L14]
- [docs/plans/2026-05-03-issue-376-cross-field-analytics-lt.md:L16-L16]
- [docs/plans/2026-05-04-issue-153-uscg-misle-dataset.md:L6-L6]
- [docs/plans/2026-05-04-issue-278-compatibility-shims.md:L1-L1]
- [docs/plans/2026-05-04-issue-327-conftest-marine-safety-fix.md:L1-L1]
- [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L17-L17]
- [docs/plans/2026-05-04-issue-352-cli-smoke-verification.md:L26-L26]
- [docs/plans/2026-05-04-issue-363-hse-query-api.md:L5-L5]
- [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L92-L92]
- [docs/plans/2026-05-12-issue-403-hurricane-mooring-risk-infographic.md:L14-L14]
- [docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md:L18-L18]
- [docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md:L18-L18]
- [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L112-L112]
- [docs/plans/README.md:L32-L32]
- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L13-L13]
- [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L14-L14]
- [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L13-L13]
- [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L49-L49]
- [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L88-L88]
- [docs/reports/cli-smoke-report-2026-05-11.md:L17-L17]
- [docs/reports/data-freshness-scorecard-2026-06-08.md:L15-L15]
- [docs/research/llm_model_evaluation_marine_incidents.md:L5-L5]
- [docs/research/marine_safety_data_sources_verification_report.md:L1-L1]

### Verification status

The supplemental dependency-contract command `uv run --extra llm python -m pytest tests/contracts -q -rA -p no:cacheprovider` with scratch output destinations and the existing-tree integrity option passed all 8 nodes at BASE and AFTER on the uncommitted tree, based on `de90ed1413b3f291f60fba625a8b8bac3233122c` with the preserved header code pin; no nodes failed, skipped or were NOT_RUN. [tests/contracts/test_assetutilities_data_contract.py:L1-L51] [tests/contracts/test_assetutilities_engine_contract.py:L1-L31]

BASE and AFTER test results, citation resolution, ten manual citation checks, file hygiene, public-wording scans and implementation-map selection are recorded in the accompanying change description; clearance remains pending independent review.
