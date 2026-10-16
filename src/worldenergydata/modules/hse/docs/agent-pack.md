# HSE legacy importer knowledge pack

| Header | Value |
| --- | --- |
| Module | modules/hse |
| Repository | worldenergydata |
| Path | `src/worldenergydata/modules/hse` |
| Pack revision | 0 |
| Code revision | `01e65a40ab2f0aa06e663f26b70a94a186efa191` |
| Analysis family | EC — data pipeline; AQG r0 Python calculations gate set |
| Quality manager role | Calculations quality manager |
| Status | DRAFT |

## 1. Purpose and scope

The physical legacy source contains a CSV statistics normalizer and three URL fetch adapters that flatten processor DataFrames into record dictionaries. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L41-L89] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96]

The import namespace is a separate concern: package initialization installs a finder that redirects `worldenergydata.modules.hse` and its children to `worldenergydata.hse`; normal legacy-name imports therefore exercise the current package when that target resolves. [src/worldenergydata/__init__.py:L59-L65] [src/worldenergydata/_compat.py:L25-L31] [src/worldenergydata/_compat.py:L76-L123]

This pack covers the physical header path, including all its importer subfolders; the current package is treated as a dependency and a competing implementation, rather than evidence that the physical files were executed. [src/worldenergydata/_compat.py:L68-L73] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L16-L22]

The legacy statistics normalizer assigns incident-style keys and `equipment_failure`, whereas the current implementation retains reporting-period keys for `SafetyStatistic`; these paths are not interchangeable hand-check references. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L122-L157] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L124-L149]

No solver launch or engineering response calculation is part of the four fetch/normalization methods described here. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L41-L89] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L120-L260] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96]

## 2. Inputs and outputs

### Inputs

| Input | Unit / allowed range | Default | Source / evidence |
| --- | --- | --- | --- |
| `db_session` | SQLAlchemy session; no local type/range check | Required argument | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L30-L39] |
| `csv_file_path` | File locator; missing argument and missing file raise errors | `None` | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L30-L39] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L68-L89] |
| `incident_id`, `operator_name`, `severity` | Identifiers/categories; only presence is tested locally | Omitted if absent | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L122-L124] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L148-L157] |
| `report_date` | Naive date/time; formats `%Y-%m-%d %H:%M:%S`, then `%Y-%m-%d` | Omitted if absent; invalid text preserved | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L126-L146] |
| `facility`, `field` | Optional text; no local range check | `None` if absent | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L159-L169] |
| `operational_period` | Days operating in quarter, per docstring; no bounds enforced | `None` | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L46-L59] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L171-L186] |
| Six incident count fields | Count of events; no nonnegative or integer-type enforcement for non-string values | `None` | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L188-L258] |
| `use_optimized` | Boolean preference; forwarded to processor | `True` | [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L38-L49] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L43-L55] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L40-L51] |
| URL response / processor output | ZIP bytes; mapping values are a DataFrame or a dictionary holding `data` | `None` download raises `ValueError` | [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96] |

The six count fields are `total_incidents`, `fatality_count`, `lost_time_count`, `recordable_count`, `near_miss_count`, and `minor_count`. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L188-L258]

### Outputs

| Output | Unit / convention | Default / error semantics | Evidence |
| --- | --- | --- | --- |
| CSV `fetch_data()` | List of row dictionaries | Empty-data parser exception becomes `[]`; other parser errors become `ValueError` | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L76-L89] |
| URL `fetch_data()` | List of row dictionaries, concatenated in processor iteration order | Empty mapping or empty frames produce zero records | [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L79-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L91-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L83-L96] |
| Statistics `normalize_data()` | Dictionary with `bsee_incident_id`, `incident_date`, `operator`, `severity`, optional text and counts | `incident_type` always `equipment_failure`; invalid integer text becomes `None` | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L122-L169] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L171-L260] |

UNVERIFIED: U1 — Raw URL payload units, coordinate frame, geographic datum, sign and phase conventions are not qualified by an inspected source dataset; the fetch adapters copy columns without unit validation (issue pending (3)). [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L79-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L91-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L83-L96]

## 3. Method and governing standards

| Method | Implementing definition | Algorithm / reference |
| --- | --- | --- |
| CSV ingestion | `BSEEStatisticsImporter.fetch_data` | `pandas.read_csv`, then `to_dict("records")`; no explicit separator, decimal, dtype or unit options. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L76-L89] |
| Date normalization | `BSEEStatisticsImporter.normalize_data` | Two `datetime.strptime` formats; original value retained on failure or non-string input. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L126-L146] |
| Count normalization | Same definition | `int()` on strings only; seven separate conversions; conversion failure becomes `None`; other types pass through. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L171-L258] |
| Incident URL acquisition | `BSEEIncidentsImporterURL.fetch_data` | `BSEE_WELL_DATA_URL`, downloader type `well`, `process_well_data(..., cfg={})`, DataFrame flattening. [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L36-L49] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] |
| Penalty URL acquisition | `BSEEPenaltiesImporterURL.fetch_data` | `BSEE_WAR_DATA_URL`, downloader type `war`, `process_war_data` with `extract_year_month=True`. [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L41-L55] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] |
| Statistics URL acquisition | `BSEEStatisticsImporterURL.fetch_data` | `BSEE_PRODUCTION_DATA_URL`, downloader type `production`, `process_production_data` with `calculate_boe=True`. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L36-L51] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96] |

No governing engineering standard, edition, clause or standards-derived coefficient is specified in these algorithms; no calculation Citation sidecar is emitted by them. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L120-L260] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96]

The URL integration document describes the legacy acquisition routes, while current adapters use generic ZIP processing and incident-specific endpoints; the discrepancy is retained as a documentation/source disposition item rather than reconciled silently (issue pending (1)). [docs/hse/URL_REFRESH_INTEGRATION.md:L40-L44] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer_url.py:L74-L85] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer_url.py:L69-L78] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer_url.py:L73-L86]

UNVERIFIED: U2 — Endpoint availability, payload suitability, update frequency and compressed-size claims have not been independently confirmed; source docstrings and the integration document are not a qualified source revision (issue pending (3)). [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L24-L28] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L24-L33] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L24-L28]

## 4. Validated worked examples

Validated examples: 0; the listed expectations are mocked regression fixtures, not independent benchmark datasets or published engineering answers. [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L132-L156] [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L331-L370] [tests/modules/hse/importers/test_bsee_penalties_importer_url.py:L339-L373]

### Regression examples

Each node below is relative to `tests/modules/hse/importers/`; the namespace redirect limits the result to the current implementation rather than the physical legacy file. [src/worldenergydata/_compat.py:L68-L73] [src/worldenergydata/_compat.py:L103-L123]

| Case | Fixture / expected value | Tolerance / basis | Test node ID | Last offline result |
| --- | --- | --- | --- | --- |
| R1 frame extraction | Inline mocked one-row DataFrame; 1 returned record with matching `id` and `value` | 0 records difference; exact fixture equality | `test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURL::test_fetch_data_processes_dict_with_data_key` | PASS at BASE and final AFTER [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L132-L156] |
| R2 statistics volume | Inline mocked DataFrame; 1000 returned records with first and last fixture IDs retained | 0 records difference; exact fixture equality | `test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURLPerformance::test_large_file_handling` | PASS at BASE and final AFTER [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L331-L370] |
| R3 penalty volume | Inline mocked DataFrame; 5000 returned records with first and last fixture IDs retained | 0 records difference; exact fixture equality | `test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURLPerformance::test_very_large_file_handling` | PASS at BASE and final AFTER [tests/modules/hse/importers/test_bsee_penalties_importer_url.py:L339-L373] |

Execution ledger: BASE and AFTER will use the same pinned source revision and `uv run python -m pytest tests/modules/hse/importers -q -rA -p no:cacheprovider --basetemp=<scratch>` form, with repository addopts retained and temporary/cache/environment outputs outside the source tree. BASE: 39 run, 39 passed, 0 failed, 0 skipped, 0 NOT_RUN; command exit 0. Initial AFTER: the same 39 tests passed, but command exit 1 reported the uncommitted pack as a new tree path. Final AFTER: 85 run, 85 passed (39 module plus 46 contract tests), 0 failed, 0 skipped, 0 NOT_RUN; command exit 0. Test source and expectations: [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L64-L344] [tests/modules/hse/importers/test_bsee_penalties_importer_url.py:L59-L380] [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L69-L370]

The final AFTER command also includes `tests/contracts` and `--allow-existing-tree-changes`: that documented mode hashes initially dirty content and fails on changed bytes or additional dirty paths; the pack digest matched before and after the run. [tests/conftest.py:L385-L420] [tests/conftest.py:L430-L460] [docs/development/index.md:L56-L59]

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations; G5 follows AQG r0, section 9.

| Gate | Applicability | Module-specific check / numeric pass criterion and unit | Evidence / disposition |
| --- | --- | --- | --- |
| G0 | Applicable | C0a: AST-count the string `int()` calls in physical `BSEEStatisticsImporter.normalize_data`; exactly 7 conversion sites (count). | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L171-L258] |
| G0 | Applicable | C0b: inspect all three `fetch_data` routes; exactly 3 downloader-type / processor pairs matching section 3 (count), zero unsupported schema-equivalence claims (count). | [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96] |
| G0 | Applicable | C0c: inventory every handler, missing-field default, external conversion and unit assumption; 0 unmatched sites (count) against section 6. This checks documentation coverage, not data acceptance. | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L76-L89] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L122-L260] |
| G1 | Applicable | C1a: run all 39 discovered offline test nodes; 39 passed, 0 failed, 0 skipped, 0 collection errors (counts) required for a test-suite pass. | [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L64-L344] [tests/modules/hse/importers/test_bsee_penalties_importer_url.py:L59-L380] [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L69-L370] |
| G1 | Applicable | C1b: inspect the imported classes' source locations; all 3 URL classes resolve into the current package, 0 claims of physical-legacy execution (counts). Python imports and pytest are the program load route. | [src/worldenergydata/__init__.py:L59-L65] [src/worldenergydata/_compat.py:L68-L73] |
| G2 | Applicable | C2: hand-sum fixture category counts: `0 + 1 + 2 + 1 + 1 = 5` events; compare with `total_incidents=5`, residual exactly 0 events. This verifies fixture arithmetic only; an independent end-to-end reference remains open. | [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L34-L50] |
| G3 | NOT_APPLICABLE | No time-domain dynamics method or solver run in these methods. | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L120-L260] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96] |
| G4 | NOT_APPLICABLE | No diffraction body, mesh or hydrodynamic response in these methods. | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L120-L260] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96] |
| G5 | Applicable | C5: reconcile 3 example node IDs and all 39 test outcomes to this revision; 0 missing results (count), 6 gate dispositions (count), 0 unlinked open items (count). No signed engineering-result appendix is claimed. | [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L64-L344] [tests/modules/hse/importers/test_bsee_penalties_importer_url.py:L59-L380] [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L69-L370] |

The checks are repeatable by AST/source inspection (C0), the test command and source-location inspection (C1), the displayed addition (C2), and evidence-table reconciliation (C5); a fixture arithmetic pass does not establish source-data completeness or physical-legacy runtime coverage. [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L34-L50] [src/worldenergydata/_compat.py:L68-L73]

## 6. Known failure modes and pitfalls

### Silent-failure and assumption inventory

Every row concerns the physical package at the header pin; defaults are distinguished from proven runtime incidents, and absence of a detection check is stated explicitly. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L76-L89] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L122-L260]

| ID | Site / symptom and cause | Detection / follow-up |
| --- | --- | --- |
| SF01 | An empty CSV parser error becomes an empty successful-looking record list. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L85-L87] | no detection check exists; issue pending (2) |
| SF02 | Date-time parse failure retries date-only parsing; failure of both formats preserves the original invalid string. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L131-L143] | no detection check exists; issue pending (2) |
| SF03 | A non-string report date passes through unchanged; the comment assumes it is already datetime. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L144-L146] | no detection check exists; issue pending (2) |
| SF04 | A missing incident identifier is silently omitted from the normalized dictionary. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L122-L124] | no detection check exists; issue pending (2) |
| SF05 | A missing report date is silently omitted. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L126-L146] | no detection check exists; issue pending (2) |
| SF06 | A missing operator field is silently omitted. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L148-L150] | no detection check exists; issue pending (2) |
| SF07 | A missing severity field is silently omitted. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L155-L157] | no detection check exists; issue pending (2) |
| SF08 | Every statistics record is assigned equipment_failure, irrespective of source classification. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L152-L153] | no detection check exists for the physical file; issue pending (1) |
| SF09 | An absent facility becomes None; missing and explicitly null values are not distinguished. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L159-L163] | no detection check exists; issue pending (2) |
| SF10 | An absent field becomes None; missing and explicitly null values are not distinguished. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L165-L169] | no detection check exists; issue pending (2) |
| SF11 | `operational_period`: string int conversion rejects decimal/thousands separators and becomes None on ValueError/TypeError; absent/null also becomes None; non-strings, including fractional/negative values, pass through without range enforcement. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L171-L186] | no detection check exists; issue pending (2) |
| SF12 | `total_incidents`: string int conversion rejects decimal/thousands separators and becomes None on ValueError/TypeError; absent/null also becomes None; non-strings, including fractional/negative values, pass through without range enforcement. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L188-L198] | no detection check exists; issue pending (2) |
| SF13 | `fatality_count`: string int conversion rejects decimal/thousands separators and becomes None on ValueError/TypeError; absent/null also becomes None; non-strings, including fractional/negative values, pass through without range enforcement. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L200-L210] | no detection check exists; issue pending (2) |
| SF14 | `lost_time_count`: string int conversion rejects decimal/thousands separators and becomes None on ValueError/TypeError; absent/null also becomes None; non-strings, including fractional/negative values, pass through without range enforcement. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L212-L222] | no detection check exists; issue pending (2) |
| SF15 | `recordable_count`: string int conversion rejects decimal/thousands separators and becomes None on ValueError/TypeError; absent/null also becomes None; non-strings, including fractional/negative values, pass through without range enforcement. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L224-L234] | no detection check exists; issue pending (2) |
| SF16 | `near_miss_count`: string int conversion rejects decimal/thousands separators and becomes None on ValueError/TypeError; absent/null also becomes None; non-strings, including fractional/negative values, pass through without range enforcement. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L236-L246] | no detection check exists; issue pending (2) |
| SF17 | `minor_count`: string int conversion rejects decimal/thousands separators and becomes None on ValueError/TypeError; absent/null also becomes None; non-strings, including fractional/negative values, pass through without range enforcement. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L248-L258] | no detection check exists; issue pending (2) |
| SF18 | operational_period is described as days operating in a quarter; no local unit or reporting-period bound is enforced. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L46-L59] | no detection check exists; issue pending (3) |
| SF19 | An empty processor mapping or only empty frames returns zero records without a completeness or source-file-count check. [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L79-L92] | no detection check exists for completeness; issue pending (2) |
| SF20 | An empty processor mapping or only empty frames returns zero records without a completeness or source-file-count check. [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L91-L104] | no detection check exists for completeness; issue pending (2) |
| SF21 | An empty processor mapping or only empty frames returns zero records without a completeness or source-file-count check. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L83-L96] | no detection check exists for completeness; issue pending (2) |
| SF22 | use_optimized defaults to True and csv_file_path to None; these select a processor preference and URL route, not a payload qualification. [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L38-L49] | C0b documents the defaults; no detection check exists for payload qualification; issue pending (3) |
| SF23 | use_optimized defaults to True and csv_file_path to None; these select a processor preference and URL route, not a payload qualification. [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L43-L55] | C0b documents the defaults; no detection check exists for payload qualification; issue pending (3) |
| SF24 | use_optimized defaults to True and csv_file_path to None; these select a processor preference and URL route, not a payload qualification. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L40-L51] | C0b documents the defaults; no detection check exists for payload qualification; issue pending (3) |
| SF25 | An empty cfg delegates well-processing assumptions to MemoryProcessor. [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L75-L76] | no detection check exists; issue pending (3) |
| SF26 | extract_year_month=True delegates date interpretation to the WAR processor. [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L86-L89] | no detection check exists; issue pending (3) |
| SF27 | calculate_boe=True enables a production quantity without a local unit/schema check for safety statistics. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L79-L80] | no detection check exists; issue pending (1) |
| SF28 | pandas CSV defaults determine encoding, separator, decimal and dtype interpretation; no explicit external-text dialect is supplied. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L76-L81] | no detection check exists; issue pending (2) |

Sweep coverage: 28 site groups are listed above, including 7 field-specific numeric conversion/fallback groups, 4 empty-result paths and 3 optimization defaults; zero record-skipping `continue` statements, `return None` statements, numeric-zero/1970 defaults, percentage defaults or local cache-write calls occur in these four physical files. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L1-L260] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L1-L100] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L1-L114] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L1-L105]

The broad CSV exception is re-raised as `ValueError`, and the three missing-download guards raise `ValueError`; these are explicit failures rather than swallowed errors. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L88-L89] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L70-L71] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L80-L81] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L72-L75]

Reproduction commands for C0c (source reads only):

```bash
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|\b(int|float)\(|None|cfg=|use_optimized|unit|cache' src/worldenergydata/modules/hse --glob '*.py'
rg -n 'percent|0\.05|5%|write|save|dump|to_csv|to_parquet' src/worldenergydata/modules/hse --glob '*.py'
```

### Historical issue lead and coverage pitfalls

The repository readiness matrix associates the legacy namespace with issue 278; the currently inspected finder redirects HSE, so this issue is a historical discovery lead rather than evidence of a present HSE import failure. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L795-L809] [src/worldenergydata/_compat.py:L25-L31] [src/worldenergydata/_compat.py:L103-L123]

The incident workflow assertion accepts `imported_count >= 0`, including zero imported rows; it is not a detection check for a fully rejected dataset. [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L238-L258]

Duplicate-basename unit URL tests are ignored by the existing collection hook; the explicit module-test directory remains the 39-node regression target rather than evidence for all current HSE functionality. [tests/conftest.py:L645-L649] [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L64-L344] [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L69-L370] [tests/modules/hse/importers/test_bsee_penalties_importer_url.py:L59-L380]

UNVERIFIED: U3 — Direct runtime behavior and database persistence of the four physical legacy files are not established by redirected-import test results (issue pending (1)). [src/worldenergydata/_compat.py:L68-L73] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L11-L16]

## 7. Lessons log

| Date | Pack revision | Lesson / evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-16 | 0 | Legacy namespace tests can resolve to a different physical implementation. [src/worldenergydata/_compat.py:L68-L73] | Scope and example limitations are explicit. | Not assigned; issue pending (1) |
| 2026-10-16 | 0 | Seven count conversions collapse malformed text into None. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L171-L258] | Separate field rows are retained in section 6. | Not assigned; issue pending (2) |

## 8. Ownership

Required review route: calculations quality manager, using AQG r0 Python calculations gates until a data-pipeline quality manager is designated (AQG r0, sections 10–11).

Escalation route: calculations quality manager for criteria and technical classifications; maintainer for scope decisions (Module agent lifecycle, revision 0, section 4, step E).

UNVERIFIED: U4 — A deputy quality manager and a shared-log entry have not been recorded for this pack; no clearance or independent-provider review is asserted (issue pending (5)).

## 9. Dependencies and implementation inventory

### Upstream and downstream

| Dependency / consumer | Relationship and boundary | Evidence |
| --- | --- | --- |
| `pandas`, `datetime`, `pathlib` | CSV parsing, date parsing and path checks | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L68-L89] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L126-L146] |
| `BSEEWebScraper` | Downloader object is created and called; no live endpoint qualification is implied | [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L46-L49] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L71] |
| `MemoryProcessor` | Well, WAR and production routes are invoked with route-specific configuration | [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L75-L77] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L86-L89] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L79-L81] |
| Current HSE parents | Legacy parent imports resolve through the compatibility finder when the target exists | [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L10-L16] [src/worldenergydata/_compat.py:L103-L123] |
| Current database models | Legacy-name test imports request HSEIncident; the current statistics implementation targets SafetyStatistic | [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L10-L13] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L248-L255] |
| Refresh script | Calls current acquirer, investigation importer and INC importer; it does not call the legacy URL classes | [scripts/refresh_bsee_hse.sh:L11-L23] |

### A8 map inventory

Map observation: `digitalmodel`, `docs/registry/implementation-map.yaml`, ref `origin/codex/implmap-work`, commit `21f0a121ffacbd63b97af00f873e8089effa6c3b`; the map's recorded data/code revision is `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407` (implementation map, schema version 1, header `revision` and `families`).

Inventory result: 13 map families inspected; 0 implementation rows under `src/worldenergydata/modules/hse/`; 0 module map families; empty implementation inventory (implementation map at the observation above, every `families[].implementations[].path`).

Counted-family grep: `NOT_APPLICABLE`, because no map family has an implementation row in this package; no search signal is counted, no definition-hit classification or miss allowance is claimed (implementation map at the observation above, every `families[].implementations[].path`).

Map follow-up: CSV ingestion, reporting-date/count normalization, incident ZIP fetch/flattening, penalty ZIP fetch/flattening, and statistics ZIP fetch/flattening will need owning-repository rows before they can become counted families; issue pending (4). [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L76-L89] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L126-L258] [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L65-L92] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L75-L104] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L67-L96]

### Whole-repository supplementary discovery

The search includes tracked source, workspace packages and scripts; these results are map follow-up findings and do not change A8 (implementation map, schema version 1, family membership criterion).

```bash
git grep -n -E 'BSEE(Statistics|Incidents|Penalties)Importer|process_(well|war|production)_data' -- '*.py'
```

| Other implementation / caller | Classification and disposition | Evidence |
| --- | --- | --- |
| Current `BSEEStatisticsImporter.normalize_data` | Further implementation outside the physical package, with different schema behavior; map gap, issue pending (1) and (4) | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L124-L155] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L157-L246] |
| Current `BSEEIncidentsImporterURL.fetch_data` | Further acquisition implementation with incident-specific endpoint and generic ZIP processor; map gap | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer_url.py:L74-L97] |
| Current `BSEEPenaltiesImporterURL.fetch_data` | Further acquisition implementation with INC endpoint and generic ZIP processor; map gap | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer_url.py:L69-L90] |
| Current `BSEEStatisticsImporterURL.fetch_data` | Further acquisition implementation with statistics endpoint and generic ZIP processor; map gap | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer_url.py:L73-L101] |
| Current refresh script | Delegating workflow, not a further implementation of the legacy URL algorithms | [scripts/refresh_bsee_hse.sh:L11-L23] |
| Database bridge script | Imports distinct investigation and INC importers; separate ingestion route, not an alias of the legacy adapters | [scripts/import_bsee_hse_to_db.py:L49-L50] |

## 10. Coverage and open items

### Read inventory

All four physical Python files were read, including their docstrings and all importer subfolders. [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L1-L100] [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L1-L114] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L1-L260] [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L1-L105]

The three module test files define 13 incident, 14 penalty and 12 statistics test functions: 39 definitions total; the source fixtures and expected assertions were read. [tests/modules/hse/importers/test_bsee_incidents_importer_url.py:L64-L344] [tests/modules/hse/importers/test_bsee_penalties_importer_url.py:L59-L380] [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L69-L370]

The discovered documentation and module-relevant portions read are listed below; historical coverage and readiness claims are not adopted as current measured results. [docs/PHASE_2_TIER_1_COVERAGE_EXPANSION.md:L73-L106] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L795-L809]

| Documentation read | Evidence location |
| --- | --- |
| URL integration architecture, usage, error handling and references | [docs/hse/URL_REFRESH_INTEGRATION.md:L1-L640] |
| Legacy importer coverage plan | [docs/PHASE_2_TIER_1_COVERAGE_EXPANSION.md:L73-L106] |
| BSEE integration mapping | [docs/knowledge-base/bsee/integration/codebase-mapping.md:L158-L166] |
| Legacy namespace readiness row | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L795-L809] |
| HSE completeness row | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L163-L179] |
| Data-location architecture | [docs/data/TWO_TIER_DATA.md:L1-L38] |
| Grounding source revision metadata | [docs/hse/grounding-riser-revisions.json:L1-L26] |
| Bulk ingestion plan | [docs/plans/2026-05-04-issue-366-hse-bulk-dedup-ingest.md:L1-L52] |
| Intervention synthesis plan | [docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md:L13-L44] |
| Aggregate benchmarking plan | [docs/plans/2026-05-18-issue-425-operator-hse-benchmarking.md:L13-L32] |
| Drilling patterns plan | [docs/plans/2026-05-18-issue-426-drilling-hse-patterns.md:L13-L34] |

Registry observation at the code pin: requested `docs/registry/module-routing.yaml` absent; no registry edit or maturity assignment is supplied (Git tree enumeration at the header revision).

The calculation-citation contract was readable as an external governance input; no standard-derived constant is introduced in this documentation change. [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L120-L260]

### Open-item register

| Item | Missing evidence / work | Responsible role | Tracking |
| --- | --- | --- | --- |
| O1 / U3 | Reconcile physical legacy files, current-package redirects, stale source-route documentation and schema differences; add physical-source coverage or disposition | Maintainer | issue pending (1) |
| O2 | Add detection for every SF01–SF28 parse/default/completeness path where none exists; preserve invalid-versus-missing distinctions and test rejected input counts | Maintainer | issue pending (2) |
| O3 / U1 / U2 | Qualify raw dataset units, date/time conventions, source vintage, endpoints, payload schemas and independent end-to-end fixtures; no independently validated worked example is supplied | Maintainer | issue 462; issue pending (3) |
| O4 | Coordinate implementation-map rows and current/legacy duplicate disposition; resolve absent routing maturity without inventing a registry entry | Maintainer | issue pending (4) |
| O5 / U4 | Assign deputy, create shared-log references, obtain independent review and replace draft references with issue numbers before clearance | Maintainer | issue pending (5) |

No independent validated data-to-database benchmark is claimed: section 4 remains a regression catalogue, and G2 remains limited to fixture arithmetic. [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L34-L50] [tests/modules/hse/importers/test_bsee_statistics_importer_url.py:L150-L181]
