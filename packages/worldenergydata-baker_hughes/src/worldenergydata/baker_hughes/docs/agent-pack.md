# Baker Hughes module knowledge pack

Summary: section 12 defines schema, filter, completeness, collector/export and
distribution contracts for #1335, #1337 and #1338. Sections 1–11 preserve the
earlier evidence; section 12 supersedes their affected current dispositions.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 3 | 2026-10-19 | Added date completeness detection and tests so empty or missing dates cannot imply complete bounds. Earlier revision evidence remains below. |
| 4 | 2026-10-22 | Added schema and completeness diagnostics, independent collector failure checks, a local implementation map and built-archive evidence to resolve the detection gaps. |

| Header | Value |
| --- | --- |
| Module | baker_hughes |
| Repository | worldenergydata |
| Path | packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes |
| Pack revision | 4 |
| Pack date | 2026-10-22 |
| Code revision | b1394197a66f95d78615425b4e1ad4ff78bd9de2 |
| Analysis family | EC; data pipeline; AQG r0 Python calculations gate set |
| Quality role | Calculations quality manager; deputy: to be appointed |
| Status | DRAFT; second-provider clearance pending |

## 1. Purpose and scope

The public API exposes Excel pivot and summary loaders returning pandas DataFrames. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/__init__.py:L4-L12]
The report function produces a dictionary of record counts, date bounds and available dimensions; it does not write a report file. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L11-L42]
The package loaders read supplied files rather than downloading or refreshing them; a separate collector downloads and reads rig-count workbooks without these loaders (section 9). [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L36-L72] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L75-L110] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py:L38-L74]
The distribution declares Alpha maturity; this is metadata rather than evidence of production readiness. [packages/worldenergydata-baker_hughes/pyproject.toml:L15-L23]

## 2. Inputs and outputs

| Input | Unit and range | Default | Source and evidence |
| --- | --- | --- | --- |
| Pivot path; sheet_name | Excel file; required mapped columns | Sheet `Pivot Table` | `pd.read_excel`; column mapping. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L20-L41] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L56-L64] |
| country; basin | Exact string comparison; optional | None; no filtering | No normalization is performed. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L66-L69] |
| Summary path; sheet_name | Excel file; first column identifies state; other headers parse as dates | Sheet `Rigs by State` | No explicit header schema validation. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L75-L106] |
| Report df; source | DataFrame; arbitrary source label | Both required | Report source is copied verbatim. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L11-L25] |

| Output | Unit and convention | Behavior and evidence |
| --- | --- | --- |
| Pivot columns | date; categorical dimensions; rig_count in counts | Twelve mapped column names; numeric count converted to integer. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L20-L33] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L59-L64] |
| well_depth_ft; water_depth_ft | Feet implied by output names; no conversion or datum validation | Numeric coercion only; source-unit qualification remains open. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L30-L31] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L63-L64] |
| Summary | state, date, rig_count in counts | Wide-to-long melt followed by integer coercion. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L94-L110] |
| Report | record_count in rows; date bounds as strings; categorical lists | Count is row count, not the sum of rig_count; lists are sorted, unique and non-null. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L22-L40] |

No spatial frame, origin or phase transformation is implemented in the loaders; the depth columns are converted numerically without geometric processing. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L56-L72] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L92-L110]

## 3. Method and governing standards

| Method | Implementation | Reference and limitation |
| --- | --- | --- |
| Pivot ingestion | Read Excel, rename columns, parse dates, coerce counts/depths, filter, reset index | Implementation-defined transformation; no governing standard is cited by the function. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L36-L72] |
| Summary ingestion | Treat first column as identifier; melt all remaining columns; parse dates; coerce counts; reset index | Implementation-defined transformation; no independent reference is cited by the function. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L75-L110] |
| Ingestion report | len(df), min/max date, sorted unique dimensions | No engineering equation or standards-derived coefficient appears in the function. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L11-L42] |

UNVERIFIED: Source workbook units, source revision and independent expected values have not been qualified; section 10 tracks this limitation as #1336.

## 4. Validated worked examples

Validated examples: 0; no independent expected-value reference is provided by the fixture assertions below. [tests/test_baker_hughes_loader.py:L55-L63] [tests/test_baker_hughes_loader.py:L104-L117]
Regression examples: 3; all results below are PASS in both baseline and documentation-tree runs against the header code revision. [tests/test_baker_hughes_loader.py:L55-L63] [tests/test_baker_hughes_loader.py:L104-L117] [tests/test_baker_hughes_loader.py:L123-L135]

| Case | Source; input | Expected; tolerance | Test node ID; offline result |
| --- | --- | --- | --- |
| Filter cardinality | Repository pivot fixture; no independent dataset revision asserted | 7 rows; tolerance 0 rows | `tests/test_baker_hughes_loader.py::TestPivotTableLoader::test_pivot_filters_by_country`; PASS. [tests/test_baker_hughes_loader.py:L55-L63] |
| Melt cardinality | Repository summary fixture; 6 identifiers by 3 dates | 18 rows; tolerance 0 rows | `tests/test_baker_hughes_loader.py::TestSummaryLoader::test_summary_row_count`; PASS. [tests/test_baker_hughes_loader.py:L104-L109] |
| Report structure | Repository pivot fixture | record_count equals input rows; 0 missing required keys | `tests/test_baker_hughes_loader.py::TestIngestionReport::test_generate_report_from_pivot`; PASS. [tests/test_baker_hughes_loader.py:L123-L135] |

## 5. QA gates

The following checks define the proposed evidence route under AQG r0, section 10, Python calculations; G5 also applies under section 9.

| Gate | Applicability | Check ID and executable route | Numeric pass criterion; unit |
| --- | --- | --- | --- |
| G0 | Applicable: input/output schema | C0: `load_pivot_table` output schema; `tests/test_baker_hughes_loader.py::TestPivotTableLoader::test_pivot_standardized_columns` | 12 expected columns, 0 extras; columns. [tests/test_baker_hughes_loader.py:L23-L41] |
| G0 | Applicable: date and count types | C1: `tests/test_baker_hughes_loader.py::TestPivotTableLoader::test_pivot_date_parsed` and `tests/test_baker_hughes_loader.py::TestPivotTableLoader::test_pivot_rig_count_is_numeric` | `load_pivot_table` output `date`/`rig_count`: 0 of 2 columns with the wrong dtype; count. These do not detect value corruption. [tests/test_baker_hughes_loader.py:L43-L53] |
| G1 | Applicable: Python imports and offline tests; no external program loading route | C2: `tests/unit/baker_hughes/test_smoke.py::test_public_api_exported` | `worldenergydata.baker_hughes` exports `load_pivot_table` and `load_summary`: 2 of 2 names resolvable, 0 missing; count. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/__init__.py:L10-L12] [tests/unit/baker_hughes/test_smoke.py:L12-L14] |
| G2 | Applicable: independent hand check of reshape cardinality | C3: `load_summary` output cardinality; calculate 6 times 3 = 18 rows; run `tests/test_baker_hughes_loader.py::TestSummaryLoader::test_summary_row_count` | Absolute difference 0 rows; this validates reshape cardinality only, not source counts. [tests/test_baker_hughes_loader.py:L104-L109] |
| G3 | NOT_APPLICABLE: no dynamic simulation is performed by either loader | No dynamics check | No dynamic outputs. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L36-L72] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L75-L110] |
| G4 | NOT_APPLICABLE: no mesh or hydrodynamic solver is used by either loader | No mesh check | No mesh outputs. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L36-L72] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L75-L110] |
| G5 | Applicable: ingestion report evidence | C4: `generate_report` output `record_count` and required keys; `tests/test_baker_hughes_loader.py::TestIngestionReport::test_generate_report_from_pivot` | record_count difference 0 rows; 0 missing asserted keys. Source fingerprint and signed QA appendix are not tested. [tests/test_baker_hughes_loader.py:L123-L135] |

Five checks are defined: G0 = 2, G1 = 1, G2 = 1, G3 = 0, G4 = 0, G5 = 1; these are evidence checks, not a declaration of full gate clearance.
UNVERIFIED: Independent source-count accuracy and source-unit qualification remain open under G0/G2; #1336.
UNVERIFIED: The ingestion report does not establish signed QA evidence or input fingerprints; #1336.

## 6. Known failure modes and pitfalls

sweep: 19 found

The sweep groups distinct behaviors rather than matching lines; each depth-unit assumption and each dropped report dimension is counted separately. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L30-L31] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L59-L69] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L94-L106] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L27-L40]

| ID | Symptom and cause at the code pin | Detection; disposition |
| --- | --- | --- |
| F1 | Invalid/missing pivot count becomes true zero through coerce/fillna. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L60-L62] | no detection check exists; C1 checks dtype only; #1334 |
| F2 | Fractional pivot count is cast to integer without an integrality check. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L60-L62] | no detection check exists; #1334 |
| F3 | Invalid well depth becomes missing through numeric coercion. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L63-L63] | no detection check exists; #1334 |
| F4 | Invalid water depth becomes missing through numeric coercion. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L64-L64] | no detection check exists; #1334 |
| F5 | Well depth is labelled feet without source-unit conversion/validation. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L30-L30] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L63-L63] | no detection check exists; #1334 |
| F6 | Water depth is labelled feet without source-unit conversion/validation. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L31-L31] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L64-L64] | no detection check exists; #1334 |
| F7 | Unmatched country filter silently returns no records. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L66-L67] | no detection check exists; the existing fixture checks do not cover empty filters; #1335 |
| F8 | Unmatched basin filter silently returns no records. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L68-L69] | no detection check exists; #1335 |
| F9 | First summary column is assumed to identify state without schema checks. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L94-L103] | no detection check exists; #1335 |
| F10 | Every other summary column is treated as a date column without selecting a date-header schema. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L95-L104] | no detection check exists; #1335 |
| F11 | Invalid/missing summary count becomes true zero. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L105-L107] | no detection check exists; #1334 |
| F12 | Fractional summary count is cast to integer without an integrality check. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L105-L107] | no detection check exists; #1334 |
| F13 | Empty input or absent date column omits date_range from the report without a completeness status. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L27-L31] | no detection check exists; C4 covers populated pivot input only; #1335 |
| F14 | Missing basin values disappear from report dimension inventory. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L33-L34] | no detection check exists; #1335 |
| F15 | Missing state values disappear from report dimension inventory. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L36-L37] | no detection check exists; #1335 |
| F16 | Missing country values disappear from report dimension inventory. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L39-L40] | no detection check exists; #1335 |
| F17 | Missing pivot source columns (`Country`, `County`, `StateProvince`, `BasinName`, `DrillFor`, `Location`, `Trajectory`, `WellType`) are ignored by rename when no corresponding filter accesses them; unmapped extra columns pass through. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L56-L57] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L66-L72] | no detection check exists; C0 checks only the unchanged fixture schema; #1335 |
| F18 | Absent `basin`, `state` or `country` columns omit `basins`, `states` or `countries` from `generate_report` without a completeness status, unlike the missing-value cases F14–F16. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L33-L40] | no detection check exists; C4 covers populated pivot input only; #1335 |
| F19 | Missing pivot dates survive `pd.to_datetime` as `NaT`; `generate_report` ignores them in min/max, and all-missing dates produce `"NaT"` bounds without a completeness status. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L59-L59] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L27-L31] | no detection check exists; C1 checks dtype only and C4 uses populated dates; #1335 |

The following sweep commands cover every Python source file in the header package; results are reviewed against the complete functions rather than treated as confirmed defects solely from a match.

```sh
rg -n 'except|continue|return None|return \[\]|return \{\}|fillna|coerce|astype|int\(|float\(|1970|0\.05|_ft|empty|cache' packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes --glob '*.py'
rg -n '= 0(\.0)?\b|return|dropna|if |read_excel|to_datetime|columns' packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes --glob '*.py'
```

No exception swallowing, explicit record-skipping continue, return-None/error-empty-container path, epoch fallback, percentage fallback or cache writer appears in these complete functions. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L36-L110] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L11-L42]
Historical ingestion references are #228 and #247; neither establishes detection coverage for the behaviors above (read-only issue inspection, 2026-10-17).

## 7. Lessons log

| Date | Record | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-17 | Initial pack | Numeric dtype checks alone do not establish preservation of missing/invalid counts | Coercion precedes integer casting. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L60-L64] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L105-L107] | F1–F6 and F11–F12 recorded | Not assigned; #1334 |
| 2026-10-17 | Revision 1 review | Search outside the package for independent download paths and test missing/extra columns before claiming sweep completeness | Separate collector and permissive rename. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py:L38-L74] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L56-L57] | Collector/export map gap and F17–F19 recorded | Not assigned; #1335 |
| 2026-10-17 | Revision 2: issue references filed | Filed follow-ups provide durable tracking without establishing engineering qualification | #1334–#1338 | Replaced draft references and advanced the pack revision | Not assigned; #1336 |

## 8. Ownership

Proposed governance: calculations quality manager; deputy quality manager to be appointed; producing desk: data pipelines; unresolved classification and gate evidence will be referred to the quality manager, with cross-family decisions referred to the maintainers.
Draft references have been replaced with filed issue numbers; clearance of this revision will require a different provider.

## 9. Dependencies and implementation inventory

The member declares worldenergydata-core, pandas and openpyxl dependencies, with Python 3.10 or newer. [packages/worldenergydata-baker_hughes/pyproject.toml:L10-L10] [packages/worldenergydata-baker_hughes/pyproject.toml:L30-L34]
The public module re-exports the two loaders; reporting remains a separate module function. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/__init__.py:L10-L12] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L11-L11]
The input datasets used by the tests are repository Excel fixtures; no source revision is asserted by the test definitions. [tests/test_baker_hughes_loader.py:L10-L10] [tests/test_baker_hughes_loader.py:L19-L19] [tests/test_baker_hughes_loader.py:L86-L86]

Implementation-map basis: `docs/registry/implementation-map.yaml` in digitalmodel, ref `origin/codex/implmap-work`, commit `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4`, embedded data revision `270c8759c374b67a7f032953e7fcdb14e0224461`.
Inventory: 0 map families have implementation paths inside this package; counted families: 0; the required counted-family grep is NOT_APPLICABLE because the map has no in-package rows.
Map follow-up: Excel pivot ingestion, summary wide-to-long ingestion and ingestion-report aggregation will need mapping, together with the separate workbook collector and its parquet export caller listed below; #1337.

Repository-wide discovery uses `rg -n 'load_pivot_table|load_summary|def generate_report|RigCount|PublishDate|BakerHughesCollector|download_na_rig_count|download_international_rig_count' --glob '*.py' .`, including scripts; unrelated report-function name hits do not establish duplicate rig-count algorithms.
The in-package implementation inventory is `load_pivot_table`, `load_summary`, `generate_report`; all three methods are listed in section 3. [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L36-L42] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/loader.py:L75-L79] [packages/worldenergydata-baker_hughes/src/worldenergydata/baker_hughes/report.py:L11-L11]

Outside-package map gap: `BakerHughesCollector.download_na_rig_count` and `download_international_rig_count` independently download and parse Excel workbooks with `pd.read_excel`; both catch any exception and return an empty DataFrame. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py:L38-L74]
The export caller `main` saves non-empty results to parquet without `load_pivot_table` or `load_summary`; empty results produce no saved file. This is outside the header package and does not change the counted-family result; #1337. [scripts/vessel_fleet/enrich_from_government.py:L44-L69]

## 10. Coverage and open items

| Item | Coverage or limitation | Tracking |
| --- | --- | --- |
| Numeric qualification | F1–F6, F11–F12; missing, fractional, locale-separated and unit-mismatched inputs lack rejection tests | #1334 |
| Schema and completeness | F7–F10, F13–F19 now have detection tests; section 12 defines current statuses and limits | #1335 |
| Independent evidence | UNVERIFIED: Source workbook revision, depth units, independent counts and signed fingerprinted QA evidence are not established | #1336 |
| Map coverage | BH-map-1 proposes three in-package families and one independent outside-package collector/export family; external registry adoption remains pending | #1337 |
| Distribution boundary | Policy intentionally includes the pack in wheel and source distribution; section 12 records built-archive byte checks and complete file-list evidence. Packaging configuration is unchanged. | #1338 |
| Documentation discovery | Read the member README and all three package Python files; module-naming documentation found in 6 repository discovery documents, including 1 discovery file with identifying names; individual identifying paths are withheld | #1336 |
| Testing coverage | Read all 15 test definitions across the loader tests and smoke tests; 3 regression cases are listed in section 4. [tests/test_baker_hughes_loader.py:L13-L135] [tests/unit/baker_hughes/test_smoke.py:L8-L14] | #1336 |
| Governance | Deputy role and QA evidence indexing still require maintainer action; draft references are filed | #1336 |

Documentation discovery readback:

- Capability-readiness prose identifies the loader and an inventory gap. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L80-L80]
- Capability-readiness YAML records the module and test file. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L694-L697]
- The completeness scorecard includes the module in a grouped row. [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L77-L77]
- The inventory-audit plan lists the module in its discovered tree. [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]
- The package-split ADR lists it among isolated packages. [docs/adr/0001-domain-package-split.md:L47-L47]

These discovery claims will not replace source qualification or current test evidence; #1336.

## 11. Date completeness contract (issue #1335, slice 1)

`generate_report` adds `completeness.date_range` with `status`, `reason` and
`missing_count`. This is a date-only assessment, independent of the source
label. It establishes neither schema completeness nor source accuracy.
The contract is implementation-defined for #1335 (2026-10-19), F13 and F19;
no engineering equation, coefficient or tolerance is used. Counts are direct
row enumeration. Test docstrings independently enumerate synthetic inputs;
they do not qualify a source workbook.

| Input condition, in precedence order | Status | Reason | Missing count | Bounds |
| --- | --- | --- | --- | --- |
| No rows | incomplete | `empty_input` | Count if date column exists; otherwise null | Omitted |
| Rows but no date column | incomplete | `missing_date_column` | null (unknown) | Omitted |
| All dates missing | incomplete | `all_dates_missing` | Number of rows | Omitted |
| Some dates missing | incomplete | `missing_dates` | Number of missing dates | Observed dates only |
| Nonempty input with no missing dates | complete | null | No missing dates | Observed minimum and maximum |

Dates must already be parsed, as returned by the loaders. No dates are filled
or inferred. Available bounds remain calendar-date strings, and existing
record counts and dimension inventories are preserved. All-missing input now
omits `date_range` instead of publishing `"NaT"` strings. Consumers must read
the status before treating partially observed bounds as complete. No overall
report completeness flag is provided because dimension checks remain open.

Detection tests are in `tests/unit/baker_hughes/test_report.py`:

| Case | Detection test or retained limitation |
| --- | --- |
| F7 | Retained: unmatched country filter returns empty data; the report detects empty input but cannot identify the filter cause. |
| F8 | Retained: unmatched basin filter returns empty data; filter-specific diagnostics remain open. |
| F9 | Retained: summary identifier column schema remains unchecked. |
| F10 | Retained: summary date-header selection remains unchecked. |
| F13 | `test_empty_input_reports_incomplete_dates` and `test_missing_date_column_reports_unknown_missing_count`. |
| F14 | Retained: null basin values still disappear from dimension inventory. |
| F15 | Retained: null state values still disappear from dimension inventory. |
| F16 | Retained: null country values still disappear from dimension inventory. |
| F17 | Retained: pivot missing/extra column detection remains open. |
| F18 | Retained: absent dimension columns still omit their inventories. |
| F19 | `test_partial_missing_dates_flag_observed_bounds` and `test_all_missing_dates_omit_bounds`. |

`test_complete_dates_preserve_report_fields` checks complete dates, existing
fields, source-label independence, input preservation and scalar serialization.
Expected values use reversed calendar dates to establish min/max independently;
partial and all-missing cases count the explicitly listed missing entries.
The new file has ten parametrized cases. Together with the existing loader
and package smoke tests, 25 cases pass. Later slices of #1335 address the
retained schema, filter and dimension checks above; #1334 and #1336 retain
numeric and independent source-qualification gaps.

## 12. Current schema, completeness and distribution contracts

This revision supersedes the affected historical dispositions in sections 6,
9–11. Input-domain rules implement #1335 and #1337 (2026); they introduce no
engineering equations, empirical coefficients or acceptance tolerances.
Counts below enumerate fields, families or synthetic rows. Expected values
are derived by enumeration in test docstrings, independently of production
code. Numeric coercion and independent source qualification remain #1334 and
#1336; neither is established by these checks.

### Workbook schemas and filter states

| Loader | Required | Optional | Selection and rejection |
| --- | --- | --- | --- |
| Pivot | `PublishDate`, `RigCount` | `Country`, `StateProvince`, `County`, `BasinName`, `DrillFor`, `Location`, `Trajectory`, `WellType`, `WellDepth`, `WaterDepth` | Extra or duplicate headers and missing required headers raise `SchemaError` with `diagnostics`. Missing optional headers are explicitly listed in `attrs['schema']['missing_optional']`; no columns are invented. |
| Summary | First column exactly `State`, followed by at least one calendar-date header | None | Accepted date headers are full `YYYY-MM-DD`, month-first `M/D/YYYY`, or timezone-naive date/datetime at midnight. Invalid dates, non-date columns, duplicate headers and equivalent duplicate dates are rejected. |

The schema is also tabulated in both loader docstrings. Header validation
precedes transformation; unexpected fields do not pass through. Exact pivot
filters do not normalize strings. Filtering an absent dimension raises
`ValueError` naming `absent_dimension`. Loader `attrs['ingestion']` records
input/output row counts, requested filters, source null-dimension counts and
one of `loaded`, `matched`, `no_match`, or `empty_input`. Empty input takes
precedence over an unmatched filter. Summary uses loaded/empty_input states.

### Completeness

`generate_report` adds an overall `completeness.status`, assessments for all
three dimensions, `omitted_fields`, and copies any loader schema/ingestion
diagnostics. It preserves the date reason and missing-count fields introduced
in section 11 and adds `bounds_status=observed|undefined`. Missing/all-missing
dates do not produce `NaT` bounds. Partially observed bounds remain incomplete.
Missing dimension columns have undefined status and unknown missing counts;
null values in existing dimensions have incomplete status and enumerated
missing counts. Available inventories still contain sorted unique non-null
values. Summary therefore explicitly lists absent basin and country inventories.

Overall completeness is incomplete for deficient dates, dimensions, schema,
empty input or no match. A complete result means these observed fields are
populated; it does not qualify counts, units, workbook authenticity or source
coverage. Bare frames without loader attrs do not receive a workbook schema
assessment. Dates must already be parsed and dimension values comparable.
Attrs are transient; callers needing persistent diagnostics must save the
returned report separately. No signed QA claim is made.

### Detection index and final dispositions

All paths in this table are test node identifiers. Parametrization covers both
filters, all three dimensions, missing/extra headers and date selection forms.

| Case | Current detection evidence | Disposition |
| --- | --- | --- |
| F7 | `tests/unit/baker_hughes/test_ingestion_status.py::test_unmatched_filter` | Country no match explicitly recorded. |
| F8 | `tests/unit/baker_hughes/test_ingestion_status.py::test_unmatched_filter` | Basin no match explicitly recorded. |
| F9 | `tests/unit/baker_hughes/test_schema_contract.py::test_summary_wrong_identifier` | First identifier header validated. |
| F10 | `tests/unit/baker_hughes/test_schema_contract.py::test_summary_non_date_headers`; `tests/unit/baker_hughes/test_schema_contract.py::test_summary_date_header_selection` | Full date headers selected; other columns rejected. |
| F13 | `tests/unit/baker_hughes/test_report.py::test_empty_input_reports_incomplete_dates`; `tests/unit/baker_hughes/test_report.py::test_missing_date_column_reports_unknown_missing_count` | Empty input and absent dates explicitly incomplete. |
| F14 | `tests/unit/baker_hughes/test_ingestion_status.py::test_dimension_completeness` | Missing basin values counted. |
| F15 | `tests/unit/baker_hughes/test_ingestion_status.py::test_dimension_completeness` | Missing state values counted. |
| F16 | `tests/unit/baker_hughes/test_ingestion_status.py::test_dimension_completeness` | Missing country values counted. |
| F17 | `tests/unit/baker_hughes/test_schema_contract.py::test_pivot_missing_required`; `tests/unit/baker_hughes/test_schema_contract.py::test_pivot_extra_rejected`; `tests/unit/baker_hughes/test_schema_contract.py::test_pivot_missing_optional_reported` | Required/extra fields rejected; missing optional fields reported. |
| F18 | `tests/unit/baker_hughes/test_ingestion_status.py::test_dimension_completeness`; `tests/unit/baker_hughes/test_ingestion_status.py::test_summary_dimensions_explicitly_omitted` | Absent dimensions explicitly listed. |
| F19 | `tests/unit/baker_hughes/test_report.py::test_partial_missing_dates_flag_observed_bounds`; `tests/unit/baker_hughes/test_report.py::test_all_missing_dates_omit_bounds`; `tests/unit/baker_hughes/test_ingestion_status.py::test_undefined_bounds`; `tests/unit/baker_hughes/test_worked_ingestion.py::test_pivot_missing_dates_survive_to_report` | Missing dates counted, undefined bounds explicit, no NaT strings. |

Additional nodes test absent filter dimensions, empty inputs, duplicate columns,
equivalent date headers, complete reports, schema propagation and the worked
example. `docs/examples/baker-hughes-ingestion.md` gives inputs, method and
independently enumerated answers; its executable counterpart is
`tests/unit/baker_hughes/test_worked_ingestion.py::test_worked_ingestion`.

### Implementation map BH-map-1

`docs/modules/baker_hughes-implementation-map.json` is the named local map
revision **BH-map-1**, dated 2026-10-22. It proposes explicit coverage without
claiming adoption by the external implementation registry cited in section 9.

| Scope | Families | Entry points | Detection evidence |
| --- | --- | --- | --- |
| In-package | Three: pivot-ingestion, summary-ingestion, ingestion-report | `load_pivot_table`, `load_summary`, `generate_report` | Schema, filter, date and dimension tests indexed in the map. |
| Outside-package | One: independent-workbook-export | Two `BakerHughesCollector` download methods plus `export_baker_hughes` and `main` in the export script | `tests/unit/baker_hughes/test_collector_export.py::test_collector_surfaces_failure`; `tests/unit/baker_hughes/test_collector_export.py::test_export_states`; `tests/unit/baker_hughes/test_collector_export.py::test_main_exit_status` |

Recount evidence: `tests/unit/baker_hughes/test_implementation_map.py::test_map_covers_entry_points`
asserts exact family and callable sets and resolves every implementation and
test symbol by parsing source. In-package and outside-package counts remain
distinct. The collector independently parses downloaded Excel; it does not
delegate to either loader and does not inherit their schema checks.

Collector access/parse failures now raise `DownloadError` instead of returning
an empty frame. Fake downloaders distinguish failed downloads from valid empty
frames and parse errors. The export helper attempts both sources and records
`download_failed`, `empty_result`, `missing_export`, or `exported`. A write
exception or absent output path is missing_export. The caller returns success
only when both exports exist; tests enumerate both-fail, either-fail and both-
success cases. File existence does not establish parquet validity or freshness;
real remote endpoint availability and live downloads remain untested. BOEM
collection behavior is outside this change.

### Distribution boundary: intentional inclusion

The intended policy is to **include** this module knowledge pack unchanged in
both wheel and source distribution. It documents API limits and carries no
qualification clearance. No exclusion or packaging configuration change is
required. The README remains a source-distribution build input and supplies
wheel metadata, rather than a separate runtime README file.

`tests/unit/baker_hughes/test_distribution.py::test_wheel_documentation_policy`
and `tests/unit/baker_hughes/test_distribution.py::test_sdist_documentation_policy`
build a disposable member copy, produce a source distribution, build its wheel,
open the archives with `zipfile`/`tarfile`, assert the exact owned payload set,
and compare every payload byte with its source. The source distribution also
preserves README and pyproject bytes. Temporary build logs remain outside the
repository. Complete inspected member lists and tool versions are recorded in
`docs/modules/baker_hughes-distribution-contents.json`.

The runtime payload is `__init__.py`, `loader.py`, `report.py` and
`docs/agent-pack.md`, all under `worldenergydata/baker_hughes/`. No namespace-root
initializer or sibling module is shipped. Evidence is for setuptools 84.2.1;
minimum-backend execution and installed dependency closure are not established.
Archive inclusion establishes documentation distribution only, not source or
engineering qualification. Changes to the payload require updating the explicit
policy assertion and re-inspecting artifacts.

### Sources

Opened on 2026-10-22 with HTTP 200; responses, addresses and access times are
retained with the external build evidence:

- [pandas 2.3.3 to_datetime](https://pandas.pydata.org/pandas-docs/version/2.3.3/reference/api/pandas.to_datetime.html): explicit date formats and missing dates.
- [pandas 2.3.3 DataFrame.melt](https://pandas.pydata.org/pandas-docs/version/2.3.3/reference/api/pandas.DataFrame.melt.html): explicit identifier and value columns.
- [setuptools 84.2.1 Data Files Support](https://setuptools.pypa.io/en/stable/userguide/datafiles.html): package-data patterns and distribution content.

No licensed publication values or external workbook data are used. Synthetic
input values and their expectations are written out in the test docstrings.
