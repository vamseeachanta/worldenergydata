# texas_rrc module knowledge pack

| Header | Value |
| --- | --- |
| Module | `texas_rrc` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `81e159ef57534f2ac4f324992ca3b5cff55d56ad` |
| Analysis family | EC; data pipeline, Python calculations gate set |
| Quality manager | Calculations quality manager; data-pipeline role unassigned |
| Status | DRAFT; independent clearance outstanding |

## 1. Purpose and scope

The main router collects configured data types, optionally invokes analysis, and writes district CSV and summary JSON outputs for a local CSV source. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L99-L129]

This revision documents the main local CSV → production processing → district aggregation route; broader source discovery, lifecycle, spatial, pressure and reporting paths remain coverage items in section 10.

The router admits seven data-type strings, whereas the download dispatch table contains five; admission alone does not establish download support. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L27-L36] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L29-L36]

No routing maturity is assigned here: `docs/registry/module-routing.yaml` is absent at the code revision.

## 2. Inputs and outputs

### Inputs

| Input | Unit or type | Range/default and provenance | Evidence |
| --- | --- | --- | --- |
| `data.source` | string | `csv` selects local loading | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L71-L76] |
| `Analysis.analysis_root_folder`, `data.files` | path, mapping | required for CSV loading; joined per data type | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L111-L129] |
| `data_types` | list of strings | default `production`; unconfigured files become errors | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L116-L119] |
| CSV encoding, delimiter | text | UTF-8, comma by default; replacement decoding on file input | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L52-L71] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L121-L126] |
| `district` | categorical code | membership in the router's district list is checked when configured | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L169-L177] |
| `oil_production`, `gas_production` | BBL, MCF by column mapping | numeric conversion; malformed values can become zero | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L50-L58] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L332-L351] |
| `production_date` | calendar month | parsed to `YYYY-MM`; absent values remain missing | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L363-L378] |
| `validate` | Boolean | `ProductionProcessor.process` defaults to true; CSV output writer explicitly disables validation | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L76-L93] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L219-L222] |

### Outputs

| Output | Unit or type | Construction | Evidence |
| --- | --- | --- | --- |
| Normalized records | list or DataFrame | input container type selects processing path | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L76-L93] |
| `boe_total` | BOE | oil plus converted gas in record processing | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L346-L353] |
| District aggregates | original production units, count | sums present production columns; unique leases counted when present | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L498-L519] |
| Summary JSON | counts, BBL, MCF | total records, district count, summed oil and gas | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L224-L242] |
| Collection status | mapping | collected types and per-type errors are separate fields | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L131-L138] |

Coordinate frame, origin, sign and phase qualification is outside this revision's detailed coverage; issue pending (3).

## 3. Method and governing standards

`CSVLoader._process_row` applies an optional field map, normalizes names, and converts values; integer conversion uses `int(float(value))`, numeric conversion uses `float`, and conversion errors become `None`. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L158-L171] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L214-L228]

`ProductionProcessor._process_record` normalizes districts and dates, coerces production values, derives BOE, and normalizes API identifiers; identifiers longer than 14 characters are truncated. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L318-L361] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L245-L261]

`aggregate_by_district` sums available production columns by district and joins distinct lease counts; `aggregate_by_lease` groups by lease with any available name and district columns. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L498-L562]

The implemented gas conversion is `gas_mcf × 0.1714`, added to oil barrels; this is an implementation coefficient, not a checked governing-standard value. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L34-L39] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L346-L353]

UNVERIFIED: the physical basis and applicability of the gas-to-BOE coefficient are not established by an independent reference; do not use this conversion as a qualified energy comparison (section 10, issue pending (2)).

No governing standard or standards-derived Citation sidecar is claimed for this route; independent method provenance remains issue pending (2).

## 4. Validated worked examples

Validated examples: **0**; independent published or benchmark expected values have not been established for the detailed route (issue pending (2)).

The following are regression examples using in-test synthetic inputs, not external validation.

| Case | Input and expected result | Tolerance and basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| CSV numeric conversion | `oil_production="100.5"` → 100.5 BBL | 0 BBL; exact assertion | `tests/unit/texas_rrc/test_csv_loader.py::TestConvertValue::test_numeric_field` | PASS at BASE and AFTER |
| Record conversion | oil 100 BBL, gas 500 MCF → 185.7 BOE | 0 BOE against the test expression; displayed result rounded to one decimal | `tests/unit/texas_rrc/test_production_processor.py::TestProcessRecord::test_basic` | PASS at BASE and AFTER |
| District lease count | two records with distinct lease IDs → 2 leases | 0 leases; exact assertion | `tests/unit/texas_rrc/test_production_processor.py::TestAggregateByDistrict::test_with_lease` | PASS at BASE and AFTER |

The three expected assertions and input values are defined in the existing tests. [tests/unit/texas_rrc/test_csv_loader.py:L78-L80] [tests/unit/texas_rrc/test_production_processor.py:L106-L117] [tests/unit/texas_rrc/test_production_processor.py:L316-L327]

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations; G5 follows section 9.

The checks below are proposed acceptance checks, not declarations of signed clearance.

| Gate | Applicability | Check ID and executable route | Numeric pass criterion | Evidence |
| --- | --- | --- | --- | --- |
| G0 | Applicable: inputs, units, citations | C0: run section-4 CSV conversion test for `CSVLoader._convert_value` | absolute error 0 BBL for input 100.5 BBL | node result and input assertion |
| G1 | Applicable: Python imports and tests | C1: run `python -m pytest tests/unit/texas_rrc -q -rA -p no:cacheprovider` | 0 failed tests, 0 collection errors (counts) | complete test summary; baseline failures recorded separately |
| G2 | Applicable: independent hand check | C2: compare `aggregate_by_district` oil sum for the two-row section-4 lease fixture with hand sum 100 + 200 = 300 BBL | absolute error ≤ 0.000001 BBL; exactly 2 leases | hand-check readback; independent published production benchmark remains open |
| G3 | NOT_APPLICABLE | no dynamic simulation in the detailed CSV route | reason: Python calculations family | AQG r0, section 10 |
| G4 | NOT_APPLICABLE | no diffraction calculation in the detailed CSV route | reason: Python calculations family | AQG r0, section 10 |
| G5 | Applicable: traceability | C5: resolve every bracketed source citation at the code revision; match every section-4 node with its offline result | 0 unresolved citations; 3 of 3 cases linked (counts) | citation resolution record and test summaries |

C0 and C2 inputs are the existing fixture values; the aggregation method sums oil and counts distinct leases. [tests/unit/texas_rrc/test_csv_loader.py:L78-L80] [tests/unit/texas_rrc/test_production_processor.py:L316-L327] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L498-L519]

## 6. Known failure modes and pitfalls

| Symptom | Cause and detection | Tracking | Evidence |
| --- | --- | --- | --- |
| Malformed production becomes zero | numeric coercion masks a missing or invalid measurement; C0 must be supplemented by invalid-input rejection checks; no rejection check exists for the CSV writer | issue pending (1) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L153-L157] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L339-L344] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L219-L222] |
| Identifier suffix is silently lost | API values longer than 14 characters are truncated; existing truncation test detects current behavior, not a rejection requirement | issue pending (1) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L255-L261] [tests/unit/texas_rrc/test_production_processor.py:L44-L46] |
| Collection errors coexist with completed status | data router stores per-type errors while the outer router sets completed after return; inspect errors as well as status; no combined detection check exists | issue pending (1) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L116-L138] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L121-L129] |
| Local CSV analysis returns file metadata instead of record aggregates | CSV loader supplies both `file_path` and `records`; production analysis returns early for `file_path` | issue pending (1); no combined detection check exists | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L121-L127] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/analysis/texas_rrc_analysis.py:L187-L202] |

The incident list in the task contains no numbered incident; searched issues are discovery references, not evidence that an incident occurred.

## 7. Lessons log

| Date | Record | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | Distinguish recorded completion from per-type data readiness | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L131-L138] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L124-L129] | section 6 | issue pending (1) |

## 8. Ownership

Calculations quality manager: family review and ambiguous method classification; deputy quality manager: unassigned, issue pending (3).

Maintainers: issue creation, coverage prioritization and publication; producing agents: pack updates and evidence records; independent clearance is outstanding.

## 9. Dependencies and implementation inventory

The local data router delegates CSV parsing to `CSVLoader`; the main output writer delegates processing and aggregation to `ProductionProcessor`. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L108-L127] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L217-L222]

The optional analysis router supports summary, production, well, permit and trend dispatch; detailed production analysis uses processor filtering and aggregation. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/analysis/texas_rrc_analysis.py:L127-L139] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/analysis/texas_rrc_analysis.py:L201-L223]

Implementation-map data revision: `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, map-declared code revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `docs/registry/implementation-map.yaml` in the engineering-method repository.

A8 inventory: **empty**; 13 map families were inspected and none has an implementation path inside this package. Counted families: **0**. Signal grep: **NOT_APPLICABLE**, because there is no in-package map family.

Map follow-up, issue pending (3): add CSV normalization and typed conversion, production-unit conversion, identifier normalization, district and lease aggregation, and analysis dispatch families before counting them under A8.

Additional repository-wide discovery used `0\.1714|def aggregate_by_district|def _normalize_api_to_14_digit` over Python files, including `scripts/`: 12 hit lines in 5 files, all in this package or its tests. This bounded discovery does not establish absence of differently named implementations; issue pending (3).

| Further definition | Classification | Evidence |
| --- | --- | --- |
| `WellProcessor._normalize_api_to_14_digit` | independent identifier-normalization algorithm | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/well_processor.py:L297-L314] |
| `PermitProcessor._normalize_api_to_14_digit` | independent identifier-normalization algorithm | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/permit_processor.py:L321-L338] |
| `normalize_production_frame` | separate BOE formula including condensate; shares the processor conversion coefficient | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/production_atlas/atlas.py:L118-L136] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/production_atlas/atlas.py:L18-L18] |

These definitions are map follow-up findings, not counted-family A8 misses; issue pending (3).

## 10. Coverage and open items

| Item | Disposition and accountable role | Tracking |
| --- | --- | --- |
| Registry metadata | routing registry absent at the pin, so no routing entry is changed; maintainers | issue pending (3) |
| Detailed main-path reading | main router, CSV loader, data-router CSV path, production-processing and production-analysis paths; calculations quality manager | issue pending (3): finish full-file review outside these ranges |
| Wider module | 87 Python files inventoried; lifecycle, production atlas, infrastructure, pressure, opportunities, dossiers, portfolio, raw refresh, API, cache, well and permit processing need detailed coverage; calculations quality manager | issue pending (3) |
| Tests | 62 module test files discovered under `tests/unit/texas_rrc`; BASE and AFTER results recorded below; broader adapter tests remain outside this main-path review | issue pending (3) |
| Documentation discovery | 46 Markdown files found; names below identify discovery coverage, not factual endorsement; maintainers | issue pending (3) |
| Independent physical reference | UNVERIFIED gas-to-BOE basis; 0 independently validated examples; calculations quality manager | issue pending (2) |
| Failure modes | malformed input, identifier truncation, partial completion and metadata short-circuit require explicit dispositions; maintainers | issue pending (1) |
| Packaging | nested Markdown package-data glob includes the pack location; no packaging change is included; maintainers | issue pending (4) [packages/worldenergydata-texas_rrc/pyproject.toml:L56-L57] |
| Baseline cache initialization | default user cache writes prevent 24 API-client tests from passing; maintainers | issue pending (5) |
| Map and responsibility | empty package inventory; method families, deputy and complete source coverage need assignments; maintainers | issue pending (3) |

### Offline evidence

BASE: 583 run, 559 passed, 24 failed, 0 skipped, 0 NOT_RUN; ordinary `uv run python -m pytest tests/unit/texas_rrc -q -rA -p no:cacheprovider --basetemp=<scratch>` at the code revision. AFTER: 583 run, 559 passed, 24 failed, 0 skipped, 0 NOT_RUN; the same test form and code revision, with `--allow-existing-tree-changes` to compare the existing pack bytes while retaining the repository tree-preservation check. The failed node sets match exactly. C1 remains below its zero-failure criterion; issue pending (5).

The 24 failures raise `OSError: [Errno 30] Read-only file system` while initializing a default user cache directory outside the writable test area; no cache-location workaround is applied (issue pending (5)). [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/cache.py:L162-L172]

Failed nodes at BASE:

- `tests/unit/texas_rrc/test_api_client.py::TestTexasRRCClientInit::test_default_values`.
- `tests/unit/texas_rrc/test_api_client.py::TestTexasRRCClientInit::test_custom_rate_limit`.
- `tests/unit/texas_rrc/test_api_client.py::TestTexasRRCClientInit::test_custom_params`.
- `tests/unit/texas_rrc/test_api_client.py::TestTexasRRCClientInit::test_disable_rate_limit`.
- `tests/unit/texas_rrc/test_api_client.py::TestSetupHeaders::test_default_headers`.
- `tests/unit/texas_rrc/test_api_client.py::TestSetupHeaders::test_custom_headers_merged`.
- `tests/unit/texas_rrc/test_api_client.py::TestSetupHeaders::test_custom_headers_override`.
- `tests/unit/texas_rrc/test_api_client.py::TestGenerateCacheKey::test_without_params`.
- `tests/unit/texas_rrc/test_api_client.py::TestGenerateCacheKey::test_with_params`.
- `tests/unit/texas_rrc/test_api_client.py::TestGenerateCacheKey::test_same_params_same_key`.
- `tests/unit/texas_rrc/test_api_client.py::TestGenerateCacheKey::test_different_params_different_key`.
- `tests/unit/texas_rrc/test_api_client.py::TestValidateApiNumber::test_valid_with_dashes`.
- `tests/unit/texas_rrc/test_api_client.py::TestValidateApiNumber::test_valid_no_dashes`.
- `tests/unit/texas_rrc/test_api_client.py::TestValidateApiNumber::test_valid_with_spaces`.
- `tests/unit/texas_rrc/test_api_client.py::TestValidateApiNumber::test_too_short`.
- `tests/unit/texas_rrc/test_api_client.py::TestValidateApiNumber::test_non_texas`.
- `tests/unit/texas_rrc/test_api_client.py::TestValidateApiNumber::test_non_digits`.
- `tests/unit/texas_rrc/test_api_client.py::TestParseWellResponse::test_basic_structure`.
- `tests/unit/texas_rrc/test_api_client.py::TestParseWellResponse::test_extracts_lease_name`.
- `tests/unit/texas_rrc/test_api_client.py::TestParseWellResponse::test_extracts_operator`.
- `tests/unit/texas_rrc/test_api_client.py::TestParseWellResponse::test_extracts_district`.
- `tests/unit/texas_rrc/test_api_client.py::TestContextManager::test_enter_exit`.
- `tests/unit/texas_rrc/test_api_client.py::TestContextManager::test_close`.
- `tests/unit/texas_rrc/test_api_client.py::TestContextManager::test_double_close`.

C2 hand-check readback: district oil sum 300.0 BBL against hand sum 300.0 BBL, absolute error 0.0 BBL; distinct lease count 2 against expected 2, count error 0. The synthetic inputs are the section-4 lease fixture. [tests/unit/texas_rrc/test_production_processor.py:L316-L327]

### Documentation discovery inventory

- `packages/worldenergydata-texas_rrc/README.md`. [packages/worldenergydata-texas_rrc/README.md:L1-L3]
- `docs/CLI.md`. [docs/CLI.md:L1-L3]
- `docs/adr/0001-domain-package-split.md`. [docs/adr/0001-domain-package-split.md:L1-L3]
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`. [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L1-L3]
- `docs/reports/data-freshness-scorecard-2026-06-08.md`. [docs/reports/data-freshness-scorecard-2026-06-08.md:L1-L3]
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`. [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L1-L3]
- `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md`. [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L1-L3]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L1-L3]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L1-L3]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L1-L3]
- `docs/ci/flake8-inventory-2026-04-23.md`. [docs/ci/flake8-inventory-2026-04-23.md:L1-L3]
- `docs/data-sources/onshore/state-well-databases/source-catalog.md`. [docs/data-sources/onshore/state-well-databases/source-catalog.md:L1-L3]
- `docs/data-sources/onshore/state-well-databases/kansas-kgs-ingest.md`. [docs/data-sources/onshore/state-well-databases/kansas-kgs-ingest.md:L1-L3]
- `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md`. [docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md`. [docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/pressure-observations.md`. [docs/data-sources/onshore/texas-rrc/pressure-observations.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md`. [docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/source-catalog.md`. [docs/data-sources/onshore/texas-rrc/source-catalog.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/storage-contract.md`. [docs/data-sources/onshore/texas-rrc/storage-contract.md:L1-L3]
- `docs/data-sources/onshore/kansas-kgs/pressure-observations.md`. [docs/data-sources/onshore/kansas-kgs/pressure-observations.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/raw-refresh.md`. [docs/data-sources/onshore/texas-rrc/raw-refresh.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md`. [docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md:L1-L3]
- `docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md`. [docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md`. [docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md`. [docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/field-atlas-reports.md`. [docs/data-sources/onshore/texas-rrc/field-atlas-reports.md:L1-L3]
- `docs/modules/repository-architecture.md`. [docs/modules/repository-architecture.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/field-development-metrics.md`. [docs/data-sources/onshore/texas-rrc/field-development-metrics.md:L1-L3]
- `docs/data-sources/onshore/texas-rrc/production-field-atlas.md`. [docs/data-sources/onshore/texas-rrc/production-field-atlas.md:L1-L3]
- `docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md`. [docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md:L1-L3]
- `docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md`. [docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md:L1-L3]
- `docs/plans/2026-07-02-issue-702-texas-rrc-field-architecture-dossiers.md`. [docs/plans/2026-07-02-issue-702-texas-rrc-field-architecture-dossiers.md:L1-L3]
- `docs/plans/2026-07-03-issue-709-texas-rrc-pressure-observations.md`. [docs/plans/2026-07-03-issue-709-texas-rrc-pressure-observations.md:L1-L3]
- `docs/plans/2026-07-02-issue-707-texas-rrc-field-architecture-portfolio.md`. [docs/plans/2026-07-02-issue-707-texas-rrc-field-architecture-portfolio.md:L1-L3]
- `docs/plans/2026-06-30-issue-663-texas-rrc-production-field-atlas.md`. [docs/plans/2026-06-30-issue-663-texas-rrc-production-field-atlas.md:L1-L3]
- `docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md`. [docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md:L1-L3]
- `docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md`. [docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md:L1-L3]
- `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md`. [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L1-L3]
- `docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md`. [docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md:L1-L3]
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`. [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L1-L3]
- `docs/plans/2026-06-30-issue-669-texas-rrc-godrive-directory-refresh.md`. [docs/plans/2026-06-30-issue-669-texas-rrc-godrive-directory-refresh.md:L1-L3]
- `docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md`. [docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md:L1-L3]
- `docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md`. [docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md:L1-L3]
- `docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md`. [docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md:L1-L3]
- `docs/plans/2026-07-03-issue-725-kansas-kgs-pressure-observations.md`. [docs/plans/2026-07-03-issue-725-kansas-kgs-pressure-observations.md:L1-L3]
- `docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md`. [docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md:L1-L3]
