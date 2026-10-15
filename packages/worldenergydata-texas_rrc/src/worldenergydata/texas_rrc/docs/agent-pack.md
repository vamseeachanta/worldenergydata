# texas_rrc module knowledge pack

| Header | Value |
| --- | --- |
| Module | `texas_rrc` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `81e159ef57534f2ac4f324992ca3b5cff55d56ad` |
| Analysis family | EC; data pipeline, Python calculations gate set |
| Quality manager | Calculations quality manager; data-pipeline role unassigned |
| Status | DRAFT; independent clearance outstanding |

## 1. Purpose and scope

The main router collects configured data types, optionally invokes analysis, and writes district CSV and summary JSON outputs for a local CSV source. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L99-L129]

This revision documents the main local CSV → production processing → district aggregation route; broader source discovery, lifecycle, spatial, pressure and reporting paths remain coverage items in section 10.

The router admits seven data-type strings, whereas the download dispatch table contains five; `leases` and `fields` raise "Unknown data type", caught per type while the outer run can finish `completed` (section 6). [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L27-L36] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L29-L36] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L81-L94] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L148-L166] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L121-L129]

No routing maturity is assigned here: `docs/registry/module-routing.yaml` is absent at the code revision.

## 2. Inputs and outputs

### Inputs

| Input | Unit or type | Range/default and provenance | Evidence |
| --- | --- | --- | --- |
| `data.source` | string | `csv` selects local loading | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L71-L76] |
| `Analysis.analysis_root_folder`, `data.files` | path, mapping | required for CSV loading; joined per data type | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L111-L129] |
| `data_types` | list of strings | default `production`; unconfigured files become errors | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L116-L119] |
| CSV encoding, delimiter | text | UTF-8, comma by default; replacement decoding on file input | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L52-L71] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L121-L126] |
| `district` | categorical code | configured `districts` filter membership is checked; record values take a separate conversion path that loses alphanumeric codes (section 6) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L169-L177] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L43-L44] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L214-L219] |
| `oil_production`, `gas_production` | BBL, MCF by column mapping | CSV malformed values become `None`; raw-record coercion can instead produce zero | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L50-L58] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L332-L351] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L221-L226] |
| `production_date` | calendar month | parsed to `YYYY-MM`; absent values remain missing; unparseable values pass through unchanged | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L363-L396] |
| `validate` | Boolean | `ProductionProcessor.process` defaults to true; CSV output writer explicitly disables validation | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L76-L93] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L219-L222] |

### Outputs

| Output | Unit or type | Construction | Evidence |
| --- | --- | --- | --- |
| Normalized records | list or DataFrame | input container type selects processing path | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L76-L93] |
| `boe_total` | BOE | oil plus converted gas in record processing | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L346-L353] |
| District aggregates | original production units, count | sums present production columns; unique leases counted when present | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L498-L519] |
| Summary JSON | counts, BBL, MCF | total records counts all processed rows; district count and oil/gas totals cover only rows retaining a valid district | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L219-L242] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L506-L519] |
| Collection status | mapping | collected types and per-type errors are separate fields | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L131-L138] |

Coordinate frame, origin, sign and phase qualification is outside this revision's detailed coverage; issue pending (3).

## 3. Method and governing standards

`CSVLoader._process_row` applies an optional field map, normalizes names, and converts values; integer conversion uses `int(float(value))`, numeric conversion uses `float`, and conversion errors become `None`. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L158-L171] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L214-L228]

`ProductionProcessor._process_record` normalizes districts and dates, coerces production values, derives BOE, and normalizes API identifiers; identifiers longer than 14 characters are truncated. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L318-L361] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L245-L261]

`aggregate_by_district` sums available production columns by district and joins distinct lease counts; `aggregate_by_lease` groups by lease with any available name and district columns. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L498-L562]

The implemented gas conversion is `gas_mcf × 0.1714`, added to oil barrels; this is an implementation coefficient, not a checked governing-standard value. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L34-L39] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L346-L353]

UNVERIFIED: the physical basis and applicability of the gas-to-BOE coefficient are not established by an independent reference; do not use this conversion as a qualified energy comparison (section 10, issue pending (2)).

UNVERIFIED: the published basis of the 10-, 12- and 14-digit identifier layout described in the well processor has not been checked; independent identifier provenance remains issue pending (2). [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/well_processor.py:L280-L289]

No governing standard or standards-derived Citation sidecar is claimed for this route; independent method provenance remains issue pending (2).

## 4. Validated worked examples

Validated examples: **0**; independent published or benchmark expected values have not been established for the detailed route (issue pending (2)).

The following are regression examples using in-test synthetic inputs, not external validation.

| Case | Input and expected result | Tolerance and basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 CSV numeric conversion | `oil_production="100.5"` → 100.5 BBL | 0 BBL; exact assertion | `tests/unit/texas_rrc/test_csv_loader.py::TestConvertValue::test_numeric_field` | PASS at BASE and AFTER |
| R2 Record conversion | oil 100 BBL, gas 500 MCF → 185.7 BOE | 0 BOE against the test expression; displayed result rounded to one decimal | `tests/unit/texas_rrc/test_production_processor.py::TestProcessRecord::test_basic` | PASS at BASE and AFTER |
| R3 District lease count | two records with distinct lease IDs → 2 leases | 0 leases; exact assertion | `tests/unit/texas_rrc/test_production_processor.py::TestAggregateByDistrict::test_with_lease` | PASS at BASE and AFTER |
| R4 Durable CSV workflow | `examples/workflows/texas-rrc-production-summary/input.yml`; 3 records, 2 districts, oil 600.0 BBL, gas 1700.0 MCF, 2 district CSV rows | 0 records and 0 rows count error; volume errors ≤ 0.0006 BBL and ≤ 0.0017 MCF, computed from the installed pytest 8.4.2 `pytest.approx` comparator used by the existing assertions | `tests/workflows/test_durable_workflows.py::test_registry_workflow_outputs[texas-rrc-production-summary]` | PASS at BASE and AFTER |

The three expected assertions and input values are defined in the existing tests. [tests/unit/texas_rrc/test_csv_loader.py:L78-L80] [tests/unit/texas_rrc/test_production_processor.py:L106-L117] [tests/unit/texas_rrc/test_production_processor.py:L316-L327]

R4 uses bundled synthetic input and registry assertions; the test copies fixtures to a temporary tree, runs the engine, and checks JSON and CSV outputs. [docs/registry/workflows.yaml:L210-L242] [tests/workflows/test_durable_workflows.py:L61-L90] [tests/workflows/test_durable_workflows.py:L110-L144]

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations; G5 follows section 9.

The checks below are proposed acceptance checks, not declarations of signed clearance.

| Gate | Applicability | Check ID and executable route | Numeric pass criterion | Evidence |
| --- | --- | --- | --- | --- |
| G0 | Applicable: inputs, units, citations | C0: run section-4 CSV conversion test for `CSVLoader._convert_value` | absolute error 0 BBL for input 100.5 BBL | node result and input assertion |
| G1 | Applicable: Python imports and tests | C1: run `python -m pytest tests/unit/texas_rrc -q -rA -p no:cacheprovider` | 0 failed tests, 0 collection errors (counts) | complete test summary with writable scratch `HOME` and `XDG_CACHE_HOME`; C1 PASS at BASE and AFTER |
| G2 | Applicable: independent hand check | C2: compare `aggregate_by_district` oil sum for the two-row section-4 lease fixture with hand sum 100 + 200 = 300 BBL | absolute error ≤ 0.000001 BBL; exactly 2 leases | hand-check readback; independent published production benchmark remains open |
| G3 | NOT_APPLICABLE | no dynamic simulation in the detailed CSV route | reason: Python calculations family | AQG r0, section 10 |
| G4 | NOT_APPLICABLE | no diffraction calculation in the detailed CSV route | reason: Python calculations family | AQG r0, section 10 |
| G5 | Applicable: traceability | C5: resolve every bracketed source citation at the code revision; match every section-4 node with its offline result | 0 unresolved citations; 4 of 4 cases linked (counts) | citation resolution record and test summaries |

C0 and C2 inputs are the existing fixture values; the aggregation method sums oil and counts distinct leases. [tests/unit/texas_rrc/test_csv_loader.py:L78-L80] [tests/unit/texas_rrc/test_production_processor.py:L316-L327] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L498-L519]

## 6. Known failure modes and pitfalls

| Symptom | Cause and detection | Tracking | Evidence |
| --- | --- | --- | --- |
| District production silently disappears for 7B, 7C and 8A | CSV integer conversion makes these valid district codes `None`; record normalization retains missing district keys and district grouping drops them; record count includes the lost production; no detection check exists | #1246 (open, confirmed 2026-10-15) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L43-L44] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L214-L219] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L39-L52] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L318-L324] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/validators.py:L563-L575] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L506-L519] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L219-L237] |
| Malformed CSV production becomes missing and can vanish from totals | loader numeric conversion returns `None`; record coercion skips it, BOE treats it as zero and aggregation sums available values; `tests/unit/texas_rrc/test_csv_loader.py::TestConvertValue::test_numeric_field_invalid` detects current loader behavior; no rejection check exists for the CSV writer | issue pending (1) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L221-L226] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L339-L353] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L498-L519] [tests/unit/texas_rrc/test_csv_loader.py:L82-L84] |
| Identifier suffix is silently lost | production, well, permit and GIS normalizers truncate beyond 14 characters; `tests/unit/texas_rrc/test_production_processor.py::TestNormalizeApi14::test_long_truncated` detects current behavior, not a rejection requirement; section 9 records the differing rules | issue pending (1) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L245-L261] [tests/unit/texas_rrc/test_production_processor.py:L44-L46] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/well_processor.py:L300-L314] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/permit_processor.py:L324-L338] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/gis_sources.py:L130-L139] |
| Collection errors coexist with completed status | data router stores per-type errors while the outer router sets completed after return; this includes admitted `leases` and `fields` without download support; inspect errors as well as status; no combined detection check exists | issue pending (1) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L81-L94] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L116-L138] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L148-L166] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L121-L129] |
| Local CSV analysis returns file metadata instead of record aggregates | CSV loading supplies both `file_path` and `records`; production analysis returns early for `file_path`; R4 enables production analysis and exercises this path but does not assert the analysis result; no detection check exists; an assertion on the production analysis result would detect it | issue pending (1) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L121-L127] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/analysis/texas_rrc_analysis.py:L187-L202] [examples/workflows/texas-rrc-production-summary/input.yml:L18-L22] [docs/registry/workflows.yaml:L217-L232] |
| Construction fails with an unwritable home; tests write into the user cache | `TexasRRCClient` constructs `FileDownloadCache`; the default creates a home-cache directory despite its temporary-directory docstring; API-client tests supply no isolated cache directory; C1 with a read-only home detects this environment dependency; writable-home C1 passes | issue pending (5), test isolation and docstring mismatch | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/cache.py:L162-L172] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/api_client.py:L121-L123] [tests/unit/texas_rrc/test_api_client.py:L15-L52] |

The district-code defect is tracked by #1246; the remaining failure modes await numbered issue creation from drafts (1) and (5).

## 7. Lessons log

| Date | Record | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | Distinguish recorded completion from per-type data readiness | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L131-L138] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L124-L129] | section 6 | issue pending (1) |

## 8. Ownership

Calculations quality manager: family review and ambiguous method classification; deputy quality manager: unassigned, issue pending (3).

Maintainers: issue creation, coverage prioritization and publication; producing agents: pack updates and evidence records; independent clearance is outstanding.

Escalation: checks unresolved after two attempts, changed criteria, ambiguous methods or contradictory inputs go to the calculations quality manager; cross-family conflicts and review assignments go to the maintainer.

## 9. Dependencies and implementation inventory

The local data router delegates CSV parsing to `CSVLoader`; the main output writer delegates processing and aggregation to `ProductionProcessor`. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/texas_rrc_data.py:L108-L127] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/texas_rrc.py:L217-L222]

The optional analysis router supports summary, production, well, permit and trend dispatch; detailed production analysis uses processor filtering and aggregation. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/analysis/texas_rrc_analysis.py:L127-L139] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/analysis/texas_rrc_analysis.py:L201-L223]

| Direction | Dependency or consumer | Inventory row | Evidence |
| --- | --- | --- | --- |
| Upstream | `worldenergydata-core`, pandas, pyarrow, pyyaml, pyshp | no rows for these distributions or external libraries in the supplied module inventory | [packages/worldenergydata-texas_rrc/pyproject.toml:L29-L35] |
| Downstream | CLI collection and raw-refresh commands import the router and refresher | `cli`, `worldenergydata`, `src/worldenergydata/cli` | [src/worldenergydata/cli/commands/texas_rrc.py:L179-L180] [src/worldenergydata/cli/commands/texas_rrc.py:L451-L458] |
| Downstream | BSEE pipeline adapter imports the well, permit and production processors; distribution declares this package | `bsee`, `worldenergydata`, `packages/worldenergydata-bsee/src/worldenergydata/bsee` | [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/adapters/rrc_adapter.py:L130-L155] [packages/worldenergydata-bsee/pyproject.toml:L53-L66] |
| Configuration | `config/texas_rrc.yml` and `src/worldenergydata/base_configs/modules/texas_rrc/texas_rrc.yml` | no separate inventory rows | [config/texas_rrc.yml:L1-L15] [src/worldenergydata/base_configs/modules/texas_rrc/texas_rrc.yml:L1-L7] |
| Workflow | `texas-rrc-production-summary` reads bundled CSV through the engine; regression R4 | no separate inventory row | [docs/registry/workflows.yaml:L210-L242] [tests/workflows/test_durable_workflows.py:L110-L144] |
| Separate source | production distribution's Texas adapter generates synthetic records and does not import this package | `production`, `worldenergydata`, `packages/worldenergydata-production/src/worldenergydata/production` | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/texas_rrc_adapter.py:L8-L16] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/texas_rrc_adapter.py:L30-L58] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/texas_rrc_adapter.py:L66-L100] |

Implementation-map branch head: `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `docs/registry/implementation-map.yaml` in the engineering-method repository.

A8 inventory: **empty**; 13 map families were inspected and none has an implementation path inside this package. Counted families: **0**. Signal grep: **NOT_APPLICABLE**, because there is no in-package map family.

Map follow-up, issue pending (3): add CSV normalization and typed conversion, production-unit conversion, identifier normalization, district-code and production-month normalization, district and lease aggregation, and analysis dispatch families before counting them under A8.

Additional repository-wide discovery used `0\.1714|def aggregate_by_district|def _normalize_api_to_14_digit` over Python files, including `scripts/`: 12 hit lines in 5 files, all in this package or its tests. This bounded discovery does not establish absence of differently named implementations; issue pending (3).

| Further definition | Classification | Evidence |
| --- | --- | --- |
| `WellProcessor._normalize_api_to_14_digit` | independent identifier-normalization algorithm | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/well_processor.py:L297-L314] |
| `PermitProcessor._normalize_api_to_14_digit` | independent identifier-normalization algorithm | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/permit_processor.py:L321-L338] |
| `normalize_production_frame` | separate BOE formula including condensate; shares the processor conversion coefficient | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/production_atlas/atlas.py:L118-L136] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/production_atlas/atlas.py:L18-L18] |
| `lifecycle.keys.normalize_api14` | independent identifier normalization; strips non-digits, requires prefix 42, rejects more than 14 digits | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/keys.py:L8-L26] |
| `infrastructure.gis_sources.normalize_api_number` | independent identifier normalization; accepts 8 digits and truncates at 14 or more | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/gis_sources.py:L119-L139] |
| `TexasDataValidator.normalize_api_number` | independent identifier normalization; requires 10 digits and prefix 42, returns dashed form | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/validators.py:L525-L551] |
| `production_atlas._normalize_districts` | independent district normalization; invalid codes become an empty string | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/production_atlas/atlas.py:L897-L901] |
| `CSVLoader._convert_value` for `district` | independent integer conversion; loses alphanumeric district codes (#1246) | [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L43-L44] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/data/loaders/csv_loader.py:L214-L219] |
| `RRCAdapter._norm_district` | outside-package district normalization; map gap | [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/adapters/rrc_adapter.py:L163-L166] |

These definitions are map follow-up findings, not counted-family A8 misses; issue pending (3). The listed identifier and district normalizers belong in that follow-up. The lifecycle normalizer rejects an 18-digit key while the production, well, permit and GIS normalizers truncate it; production removes dashes and spaces, while well and permit also strip other non-digits. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/lifecycle/keys.py:L8-L26] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/production_processor.py:L245-L261] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/well_processor.py:L300-L314] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/processors/permit_processor.py:L324-L338] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/gis_sources.py:L130-L139]

## 10. Coverage and open items

| Item | Disposition and accountable role | Tracking |
| --- | --- | --- |
| Registry metadata | routing registry absent at the pin, so no routing entry is changed; maintainers | issue pending (3) |
| Detailed main-path reading | main router, CSV loader, data-router CSV path, production-processing and production-analysis paths; calculations quality manager | issue pending (3): finish full-file review outside these ranges |
| Wider module | 87 Python files inventoried; lifecycle, production atlas, infrastructure, pressure, opportunities, dossiers, portfolio, raw refresh, API, cache, well and permit processing; `field_development/` (7 Python files) and `reports/` (7 Python files); `godrive.py`, `source_catalog.py`, `endpoints.py`, `errors.py`, `validators.py` and `data/loaders/pdq_loader.py` need detailed coverage; `texas_rrc/field_development/` belongs to this pack, distinct from the root module; calculations quality manager | issue pending (3) |
| Tests | 62 module test files discovered under `tests/unit/texas_rrc`; BASE and AFTER results recorded below; R4 workflow node also run; broader adapter tests remain outside this main-path review | issue pending (3) |
| Documentation discovery | 47 Markdown files listed: package README and module mentions under `docs/`, plus the workflow README under `examples/`; names identify discovery coverage, not factual endorsement; maintainers | issue pending (3) |
| Independent physical reference | UNVERIFIED gas-to-BOE basis and identifier-layout provenance; 0 independently validated examples; calculations quality manager | issue pending (2) |
| Failure modes | malformed input, identifier truncation, partial completion and metadata short-circuit require explicit dispositions; district-code loss tracked separately by #1246; maintainers | issue pending (1) |
| Packaging | nested Markdown package-data glob includes the pack location; no packaging change is included; maintainers | issue pending (4) [packages/worldenergydata-texas_rrc/pyproject.toml:L56-L57] |
| Cache test isolation | API-client tests write into the default home cache and fail when home is not writable; writable-home runs pass; maintainers | issue pending (5) |
| Map and source coverage | empty package inventory; method families and complete source coverage need assignments; maintainers | issue pending (3) |
| Coordinate conventions | coordinate frame, origin, signs and phases remain outside detailed coverage; calculations quality manager | issue pending (3) |
| Deputy assignment | deputy quality manager remains unassigned; maintainers | issue pending (3) |

### Offline evidence

BASE and AFTER each ran 584 tests: 584 passed, 0 failed, 0 skipped, 0 collection errors, 0 NOT_RUN (583 module unit tests plus R4). Both runs used ordinary `uv run python -m pytest tests/unit/texas_rrc 'tests/workflows/test_durable_workflows.py::test_registry_workflow_outputs[texas-rrc-production-summary]' -q -rA -p no:cacheprovider --basetemp=<scratch> --cov-report= --cov-report=term`, with writable scratch `HOME` and `XDG_CACHE_HOME`, an environment and coverage-data file in scratch, and the configured addopts retained. BASE is `af4cb68aa14d6e97fb799d75aef3f5c4edcb3ae3`; AFTER ran its uncommitted documentation changes with `--allow-existing-tree-changes`, retaining the tree-preservation check. Module code is unchanged from the header pin. C1 PASS: 0 failed tests and 0 collection errors; all four section-4 nodes pass at both stages.

Hosted `Domain unit-texas_rrc` at `af4cb68a` reported 583 passed (run 38784809747, job 116594537657); the second-provider review records this result. Hosted checks at the next head remain unverified.

The earlier read-only-home run's 24 API-client failures are environment evidence for section 6 and issue pending (5), not current code-test failures: default cache creation raised `OSError: [Errno 30] Read-only file system`. [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/cache.py:L162-L172]

The following 24 nodes now each record PASS at BASE and AFTER:

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

- `packages/worldenergydata-texas_rrc/README.md`. [packages/worldenergydata-texas_rrc/README.md:L1-L1]
- `docs/CLI.md`. [docs/CLI.md:L544-L544]
- `docs/adr/0001-domain-package-split.md`. [docs/adr/0001-domain-package-split.md:L42-L42]
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`. [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L32-L32]
- `docs/reports/data-freshness-scorecard-2026-06-08.md`. [docs/reports/data-freshness-scorecard-2026-06-08.md:L29-L29]
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`. [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12]
- `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md`. [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L69-L69]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L17-L17]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L16-L16]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md`. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L18-L18]
- `docs/ci/flake8-inventory-2026-04-23.md`. [docs/ci/flake8-inventory-2026-04-23.md:L131-L131]
- `docs/data-sources/onshore/state-well-databases/source-catalog.md`. [docs/data-sources/onshore/state-well-databases/source-catalog.md:L6-L6]
- `docs/data-sources/onshore/state-well-databases/kansas-kgs-ingest.md`. [docs/data-sources/onshore/state-well-databases/kansas-kgs-ingest.md:L10-L10]
- `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md`. [docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md:L13-L13]
- `docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md`. [docs/data-sources/onshore/texas-rrc/infrastructure-access-metrics.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/pressure-observations.md`. [docs/data-sources/onshore/texas-rrc/pressure-observations.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md`. [docs/data-sources/onshore/texas-rrc/field-opportunity-ranking.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/source-catalog.md`. [docs/data-sources/onshore/texas-rrc/source-catalog.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/storage-contract.md`. [docs/data-sources/onshore/texas-rrc/storage-contract.md:L1-L1]
- `docs/data-sources/onshore/kansas-kgs/pressure-observations.md`. [docs/data-sources/onshore/kansas-kgs/pressure-observations.md:L81-L81]
- `docs/data-sources/onshore/texas-rrc/raw-refresh.md`. [docs/data-sources/onshore/texas-rrc/raw-refresh.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md`. [docs/data-sources/onshore/texas-rrc/field-architecture-portfolio.md:L1-L1]
- `docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md`. [docs/plans/2026-07-01-issue-664-texas-rrc-field-development-metrics.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md`. [docs/data-sources/onshore/texas-rrc/field-architecture-dossiers.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md`. [docs/data-sources/onshore/texas-rrc/well-lifecycle-spine.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/field-atlas-reports.md`. [docs/data-sources/onshore/texas-rrc/field-atlas-reports.md:L1-L1]
- `docs/modules/repository-architecture.md`. [docs/modules/repository-architecture.md:L108-L108]
- `docs/data-sources/onshore/texas-rrc/field-development-metrics.md`. [docs/data-sources/onshore/texas-rrc/field-development-metrics.md:L1-L1]
- `docs/data-sources/onshore/texas-rrc/production-field-atlas.md`. [docs/data-sources/onshore/texas-rrc/production-field-atlas.md:L1-L1]
- `docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md`. [docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md:L1-L1]
- `docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md`. [docs/plans/2026-07-02-issue-695-texas-rrc-field-opportunity-architecture-ranking.md:L1-L1]
- `docs/plans/2026-07-02-issue-702-texas-rrc-field-architecture-dossiers.md`. [docs/plans/2026-07-02-issue-702-texas-rrc-field-architecture-dossiers.md:L1-L1]
- `docs/plans/2026-07-03-issue-709-texas-rrc-pressure-observations.md`. [docs/plans/2026-07-03-issue-709-texas-rrc-pressure-observations.md:L1-L1]
- `docs/plans/2026-07-02-issue-707-texas-rrc-field-architecture-portfolio.md`. [docs/plans/2026-07-02-issue-707-texas-rrc-field-architecture-portfolio.md:L1-L1]
- `docs/plans/2026-06-30-issue-663-texas-rrc-production-field-atlas.md`. [docs/plans/2026-06-30-issue-663-texas-rrc-production-field-atlas.md:L1-L1]
- `docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md`. [docs/plans/2026-06-30-issue-662-texas-rrc-well-lifecycle-spine.md:L1-L1]
- `docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md`. [docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md:L28-L28]
- `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md`. [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L19-L19]
- `docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md`. [docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md:L30-L30]
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`. [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]
- `docs/plans/2026-06-30-issue-669-texas-rrc-godrive-directory-refresh.md`. [docs/plans/2026-06-30-issue-669-texas-rrc-godrive-directory-refresh.md:L1-L1]
- `docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md`. [docs/plans/2026-07-01-issue-666-texas-rrc-onshore-field-atlas-reports.md:L1-L1]
- `docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md`. [docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md:L27-L27]
- `docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md`. [docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md:L46-L46]
- `docs/plans/2026-07-03-issue-725-kansas-kgs-pressure-observations.md`. [docs/plans/2026-07-03-issue-725-kansas-kgs-pressure-observations.md:L34-L34]
- `docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md`. [docs/plans/2026-07-01-issue-665-texas-rrc-pipeline-gis-infrastructure-access.md:L1-L1]
- `examples/workflows/texas-rrc-production-summary/README.md`. [examples/workflows/texas-rrc-production-summary/README.md:L1-L1]
