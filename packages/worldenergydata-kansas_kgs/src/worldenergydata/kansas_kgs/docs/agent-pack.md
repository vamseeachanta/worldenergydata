# Kansas KGS module knowledge pack

| Header | Value |
| --- | --- |
| Module | `kansas_kgs` |
| Repository | `worldenergydata` |
| Package scope | `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs` |
| Pack revision | 2, 2026-10-19 |
| Baseline code revision | `72716499230d3457ce90a5bcd23a8a8367bc0bd3` |
| Analysis family | EC; data ingestion and screening calculations |
| Quality role | Calculations quality manager, interim data-pipeline coverage |
| Status | DRAFT; independent clearance pending |

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-16 | Initial package inventory, regression evidence and open-item register |
| 1 | 2026-10-16 | Publish the eight issue drafts, link their scopes and proposed responsibilities, and record the missing-KID ambiguity |
| 2 | 2026-10-19 | Count ambiguous joins as missing depth and update C18 and S53 for defect 1 of #1352 |

Line-range citations retain the baseline code revision above. Revision 2 updates
C18 and S53 using the current test node IDs and symbol names; other gates and
the execution record remain historical evidence at the baseline revision.

## 1. Purpose and scope

`build_pressure_observation_packet` prepares normalized pressure and well tables, curated observations, county/year coverage and quality metadata from two raw source files. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L33-L85]
The command route is `worldenergydata kansas-kgs build-pressure-observations`; the command calls this package's builder and reports errors with exit status 1. [src/worldenergydata/cli/commands/kansas_kgs.py:L27-L68]
The package tags pressure as `WHP_shut_in`, computes a wellhead-pressure/total-depth screening gradient and labels the result `not_initial_reservoir_pressure`; it does not calculate a bottom-hole correction or a hydrostatic classification. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L89-L132] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L277-L286]
Formation tops are optional catalog metadata and are skipped by `ensure_raw_sources`. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/source_catalog.yml:L8-L11] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L73-L78]
Distribution metadata declares version 0.1.0 and an Alpha classifier; this is packaging metadata, not evidence of engineering qualification. [packages/worldenergydata-kansas_kgs/pyproject.toml:L6-L25]
The separate state-regulator implementation is outside this package's scope and remains a dependency/map follow-up in section 9. [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L151]

## 2. Inputs and outputs

### Inputs

| Input | Unit or format | Accepted range and default | Source and evidence |
| --- | --- | --- | --- |
| `pressure_proration` | Latin-1 CSV text | Header names are stripped; rows with a different field count are skipped and counted | `raw/pressure/kansas_proration_pressures.txt`; [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/source_catalog.yml:L1-L4] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L75-L86] |
| `WELL_KID`, `API_NUMBER`, `YEAR` | Identity strings; calendar year | Required by direct column access; year is coerced to nullable integer; no year interval validation | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L89-L108] |
| `SHUT_IN_PRESS`, `WORKING_PRES` | Treated as psig | Numeric coercion; zero retained in normalized data; only positive shut-in pressure reaches curated data | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L97-L105] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L67-L78] |
| `DAILY_RATE`, `OPEN_FLOW`, `ADJ_DELIVER`, `WATER_PROD` | Unqualified source units; U2 | Numeric coercion; no unit conversion or range check | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L100-L113] |
| `wells_master` | ZIP containing a member ending in `ks_wells.txt`; Latin-1 CSV | Required columns are checked; missing columns raise `ValueError` | `raw/wells/ks_wells.zip`; [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/source_catalog.yml:L5-L7] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L44-L64] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L102-L105] |
| `DEPTH`, `LATITUDE`, `LONGITUDE` | Depth treated as ft; unqualified coordinate datum and angular convention, U3 | Numeric coercion; positive depth required for gradient; no geographic bounds | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L78-L80] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L94-L96] |
| `SPUD`, `COMPLETION`, `PLUGGING`, `MODIFIED` | Oracle-style dates normalized to calendar dates | Invalid populated dates become `NaT` and increment a counter | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L84-L98] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L121-L138] |
| Root, refresh, dry run | Directory; Boolean flags | Configured storage-root guard; refresh and dry run default false; dry run still ensures raw files and writes the raw manifest | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L33-L63] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L58-L100] |

### Outputs

| Output | Unit or format | Rule and limitation | Evidence |
| --- | --- | --- | --- |
| Normalized pressure and wells | Parquet | Separate normalized pressure and well locations | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L18-L20] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L119-L129] |
| `pressure_psig_raw`, `pressure_psia`, `atmospheric_pressure_psi` | psig; psia; psi | Raw pressure retained; absolute pressure adds 14.7 psi and rounds to six decimal places; U1 qualifies the basis | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L9-L9] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L94-L118] |
| `reference_depth_ft`, `gradient_psi_ft` | ft; psi/ft | Positive matched total depth only; gradient rounded to six decimal places; missing/ambiguous depths remain missing | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L94-L96] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L120-L123] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L147-L163] |
| `api14`, `api10`, county codes | Strings, dimensionless | API10 removes dashes and truncates to ten characters; API14 comes from a matched well | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L116-L127] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L104-L108] |
| `test_date`, `test_year`, earliest flag | Null date; calendar year; Boolean or indeterminate | Annual source date remains null; earliest eligible year then retained-row order selects one row per identity | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L97-L99] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L166-L183] |
| Curated observations and coverage | CSV and Parquet; row counts | Coverage groups by county and year with missing keys retained | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L74-L77] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L186-L194] |
| Quality and manifest | JSON | Row counters, source-manifest snapshot, input locators, command, code revision and seven output snapshots | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L141-L180] |

UNVERIFIED: U1, upstream gauge-pressure interpretation, total-depth suitability and the atmospheric-pressure basis are implementation assumptions rather than independently qualified measurement metadata; the limitations explicitly flag the conversion, elevation omission and screening use; issue pending (5). [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L277-L286]
UNVERIFIED: U2, rate, deliverability and water-production units have no verified dictionary in this pack; issue pending (5). [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L100-L113]
UNVERIFIED: U3, coordinate frame, datum, origin, sign and phase conventions are not qualified by the numeric coercion; issue pending (5). [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L78-L80]

## 3. Method and governing standards

| Method | Implementation and governing basis |
| --- | --- |
| Raw acquisition | Required catalog entries are downloaded when missing or refreshed, using temporary files and rename; existing files are hashed and manifested; optional entries are omitted. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L58-L119] |
| Pressure parsing | CSV rows are compared with stripped header width; malformed rows are counted and dropped; pressure/rate fields use `pandas.to_numeric(errors="coerce")`. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L75-L113] |
| Well normalization | Required-column validation precedes normalization; API identifiers remain strings, formation at total depth falls back to producing formation, and dates are normalized explicitly. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L44-L57] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L67-L105] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L121-L138] |
| Identity matching | Candidates are grouped by API10; one candidate is used directly, multiple candidates require one matching KID, otherwise depth/gradient and earliest identity are suppressed with flags. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L135-L163] |
| Pressure and gradient | `pressure_psia = round(pressure_psig_raw + 14.7, 6)`; `gradient_psi_ft = round(pressure_psia / reference_depth_ft, 6)` only for positive matched depth; no elevation or gas-column correction. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L89-L123] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L277-L286] |
| Earliest observation | Identity prefers matched API14 then source KID; eligible rows require identity and year, with year/source-row sorting; ambiguity gives an indeterminate flag. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L166-L183] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L261-L268] |
| Quality and serialization | Coverage counts observations, not unique wells; quality reports flag counts and year bounds; CSV loading preserves API key strings. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L186-L217] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L106-L116] |

The numerical conversion is presented as an implementation assumption, not a standards-derived constant; the code emits limitation strings rather than a standards `Citation` sidecar. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L9-L9] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L277-L286]
No governing code edition or licensed clause is asserted by this pack; independent unit/reference qualification remains U1 in section 10. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L277-L286]

## 4. Validated worked examples

Independent validated examples: 0; the cases below are regression examples because their expected values are fixture assertions, not an independently versioned benchmark; independent qualification is issue pending (5). [tests/unit/kansas_kgs/test_observations.py:L8-L24] [tests/unit/kansas_kgs/test_pressure_parser.py:L8-L19]

| Regression case | Source and input | Expected result and tolerance basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| E1 malformed rows | Local pressure fixture | 2 malformed rows counted; 3 retained rows; exact integer assertions | `tests/unit/kansas_kgs/test_pressure_parser.py::test_proration_parser_repairs_malformed_second_line` | PASS at BASE and AFTER; [tests/unit/kansas_kgs/test_pressure_parser.py:L8-L19] |
| E2 depth and dates | Local ZIP fixture | 1 well; 4,470 ft depth; zero date failures; exact assertions | `tests/unit/kansas_kgs/test_wells_parser.py::test_wells_parser_extracts_depth_api14_and_dates` | PASS at BASE and AFTER; [tests/unit/kansas_kgs/test_wells_parser.py:L11-L29] |
| E3 pressure and earliest | Two annual fixture rows | 47.3 psig becomes 62.0 psia; gradient equals `round(62.0 / 4470.0, 6)` psi/ft; exact rounded equality; earliest row true | `tests/unit/kansas_kgs/test_observations.py::test_build_observations_converts_units_and_flags_earliest` | PASS at BASE and AFTER; [tests/unit/kansas_kgs/test_observations.py:L8-L24] |
| E4 ambiguous identity | Duplicated well fixture | Missing API14, depth and gradient; no true earliest flag; both ambiguity flags | `tests/unit/kansas_kgs/test_observations.py::test_build_observations_suppresses_ambiguous_api10_gradient` | PASS at BASE and AFTER; [tests/unit/kansas_kgs/test_observations.py:L27-L39] |
| E5 output packet | Local one-row DataFrame fixture | 1 row in manifest; API strings preserved; CSV digest length 64 characters; zero staging directories | `tests/unit/kansas_kgs/test_io.py::test_output_writer_writes_csv_parquet_quality_manifest` | PASS at BASE and AFTER; [tests/unit/kansas_kgs/test_io.py:L27-L87] |
| E6 dry run | Local raw fixture | Exit status 0; zero curated output directories | `tests/unit/kansas_kgs/test_cli.py::test_cli_dry_run_reports_counts_without_curated_writes` | PASS at BASE and AFTER; [tests/unit/kansas_kgs/test_cli.py:L36-L52] |

Execution record: BASE: 114 run, 114 passed, 0 failed, 0 skipped, 0 NOT_RUN (30 package, 9 legacy, 29 downstream, 46 contracts); AFTER: 114 run, 114 passed, 0 failed, 0 skipped, 0 NOT_RUN; identical 114 test nodes. Code pin: `72716499230d3457ce90a5bcd23a8a8367bc0bd3`. Form: `uv run --extra test python -m pytest <paths> -q -rA -p no:cacheprovider`, repository addopts retained, existing-tree preservation enabled, basetemp and coverage destinations in scratch; no source-resolution fallback and no addopts override. AFTER ran on the uncommitted documentation tree; implementation bytes remained at the code pin.

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations, with G5 from section 9; the module's data-table route is shown by its builder and writer. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L33-L85] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L40-L103]

| Gate | Applicability | Module-specific route |
| --- | --- | --- |
| G0 | Applicable | C01–C04, C14–C16; unit qualification remains U1–U3 |
| G1 | Applicable | C05; Python imports and offline pytest, no model-load program |
| G2 | Applicable | C06–C10, C17–C18; arithmetic hand check and identity/empty-result checks; independent physical basis remains issue pending (5) |
| G3 | NOT_APPLICABLE | The builder produces observation tables, not dynamic solver input. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L48-L85] |
| G4 | NOT_APPLICABLE | The writer produces CSV, Parquet and JSON, not a body or panel mesh. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L73-L91] |
| G5 | Applicable | C11–C13; retain test records, input identity, manifest and output digests for any derived report |

Checks below are executable existing tests except the explicit C06 hand arithmetic; passing regression checks does not qualify the source-unit assumption or close the numbered gaps.

| Check | Gate | Function/output and numeric pass criterion | Executable evidence |
| --- | --- | --- | --- |
| C01 | G0 | `parse_proration_pressure`: exactly 2 malformed and 3 retained rows in E1 | E1; [tests/unit/kansas_kgs/test_pressure_parser.py:L8-L19] |
| C02 | G0 | `parse_wells_master`: exactly 1 `ValueError` for missing required columns | `tests/unit/kansas_kgs/test_wells_parser.py::test_wells_parser_rejects_missing_required_columns`; [tests/unit/kansas_kgs/test_wells_parser.py:L32-L40] |
| C03 | G0 | Well date normalization: exactly 1 date-parse failure for one invalid date | `tests/unit/kansas_kgs/test_wells_parser.py::test_wells_parser_counts_date_parse_failures`; [tests/unit/kansas_kgs/test_wells_parser.py:L43-L51] |
| C04 | G0 | Pressure parser: retain 0.0 psig in normalized data; exactly 1 nonpositive, 0 blank, 0 missing-year and 0 missing-county rows in fixture | `tests/unit/kansas_kgs/test_pressure_parser.py::test_proration_parser_preserves_zero_and_normalizes_api`; `tests/unit/kansas_kgs/test_pressure_parser.py::test_proration_parser_counts_non_observation_pressure_rows`; [tests/unit/kansas_kgs/test_pressure_parser.py:L22-L68] |
| C05 | G1 | Import and execute module, legacy, downstream and contract test paths: 0 failed tests and 0 collection errors | Execution record in section 4; package imports exercised by E1–E6. [tests/unit/kansas_kgs/test_cli.py:L9-L11] [tests/unit/state_regulators/test_kansas_kgs.py:L14-L21] |
| C06 | G2 | `build_pressure_observations`: hand-add 47.3 + 14.7 = 62.0 psi absolute; divide by 4,470 ft and round to 6 decimal places; exactly 0 psi and 0 psi/ft difference from rounded fixture expectations | E3; arithmetic establishes formula agreement only. [tests/unit/kansas_kgs/test_observations.py:L14-L24] |
| C07 | G2 | Ambiguous API10: exactly 3 missing identity/depth/gradient outputs and 0 true earliest flags in E4; zero arbitrary well selections | E4; [tests/unit/kansas_kgs/test_observations.py:L27-L39] |
| C08 | G2 | KID fallback: exactly 1 selected well with 4,470 ft depth and a fallback flag | `tests/unit/kansas_kgs/test_observations.py::test_kid_fallback_disambiguates_api10_join`; [tests/unit/kansas_kgs/test_observations.py:L42-L56] |
| C09 | G2 | No-positive-pressure input: exactly 0 curated rows, 0 flag counters, null year bounds, and exact schema | `tests/unit/kansas_kgs/test_observations.py::test_no_positive_pressures_returns_empty_observations_and_quality`; [tests/unit/kansas_kgs/test_observations.py:L84-L108] |
| C10 | G2 | Missing year: exactly 1 missing-year count, a missing-year flag and 0 true earliest flags for that row | `tests/unit/kansas_kgs/test_observations.py::test_missing_year_positive_pressure_is_flagged_not_fatal`; [tests/unit/kansas_kgs/test_observations.py:L111-L123] |
| C11 | G5 | Manifest: exactly 1 row; CSV digest 64 characters and size greater than 0 bytes; API codes remain strings | E5; [tests/unit/kansas_kgs/test_io.py:L67-L87] |
| C12 | G5 | Curated Parquet failure: exactly 0 normalized output files promoted and 0 staging directories retained at that failure point | `tests/unit/kansas_kgs/test_io.py::test_output_writer_does_not_promote_normalized_files_when_curated_write_fails`; [tests/unit/kansas_kgs/test_io.py:L90-L122] |
| C13 | G5 | Dry-run command: exit code 0 and exactly 0 curated directories, while raw fixtures exist | E6; [tests/unit/kansas_kgs/test_cli.py:L36-L52] |
| C14 | G0 | County mapping: exactly 105 code entries | `tests/unit/kansas_kgs/test_raw_sources.py::test_kansas_county_mapping_covers_all_counties`; [tests/unit/kansas_kgs/test_raw_sources.py:L135-L142] |
| C15 | G0 | Pressure input with only malformed data: exactly 0 normalized rows, exact schema and 1 malformed-row counter | `tests/unit/kansas_kgs/test_pressure_parser.py::test_proration_parser_empty_valid_rows_returns_schema`; [tests/unit/kansas_kgs/test_pressure_parser.py:L84-L100] |
| C16 | G0 | Annual pressure policy: exactly 1 positive fixture row selected, null calendar date and `KS_PRORATION` tag; 0 policy mismatches | `tests/unit/kansas_kgs/test_pressure_parser.py::test_proration_parser_sets_pressure_fields_and_test_policy`; [tests/unit/kansas_kgs/test_pressure_parser.py:L39-L54] |
| C17 | G2 | County and formation fallbacks: exactly 0 differences from each fixture's expected categorical output (count) | `tests/unit/kansas_kgs/test_observations.py::test_unknown_county_falls_back_to_matched_well_county`; `tests/unit/kansas_kgs/test_wells_parser.py::test_wells_parser_uses_producing_formation_when_total_depth_formation_blank`; [tests/unit/kansas_kgs/test_observations.py:L72-L81] [tests/unit/kansas_kgs/test_wells_parser.py:L54-L64] |
| C18 | G2 | Quality flags: exactly 3 missing-depth counts (2 zero-depth observations plus 1 ambiguous join), 1 ambiguous-API count and 1 ambiguous-identity count; each unresolved row carries exactly 1 missing-depth flag | Current tests: `tests/unit/kansas_kgs/test_observations.py::test_observation_quality_counts_join_and_depth_flags`; `tests/unit/kansas_kgs/test_observations.py::test_unresolved_join_counts_each_missing_depth_once`; independent counts in their docstrings; #1352, defect 1 |

## 6. Known failure modes and pitfalls

sweep: 73 found (reviewed sites; intentional fallbacks included).

The inventory below records reviewed behavioural sites, including intentional fallbacks and bookkeeping defaults; a row is not automatically a confirmed defect.
The reproducible package-wide searches were:

```bash
rg -n 'except|continue|return None|return \[\]|return \{\}|= 0(\.0)?\b|1970|\b(int|float)\(|to_numeric|errors=|fillna|\.get\(|round\(|PSI|psig|psia|depth_ft|empty|ignore_errors' packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs --glob '*.py'
rg -n '0\.0|0\.05|1970|cache|to_csv|to_parquet|write_text|replace|NaT|pd.NA|timezone' packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs --glob '*.py'
```

| Site | Symptom and cause | Existing detection or gap | Disposition, 2026-10-16 | Pinned evidence |
| --- | --- | --- | --- | --- |
| S01 | HEAD exceptions return an empty metadata dict without a failure status | no detection check exists | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L127-L128] |
| S02 | Git lookup exceptions return null code revision; caller cannot distinguish unavailable provenance | no detection check exists | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L193-L204] |
| S03 | No valid rows return an empty schema and zero observation counters; no completeness rejection | C15 covers schema, not a completeness rejection | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L47-L58] |
| S04 | Malformed or blank CSV rows are dropped; counter starts at zero; no raw-line rejection ledger | C01 checks the dropped-row count | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L80-L84] |
| S05 | Year numeric coercion can replace malformed text with missing; fractional values may raise on integer cast | C04 covers valid years only; no detection check exists for malformed numeric text | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L97-L97] |
| S06 | Annual records deliberately have no test date; no day or month is inferred | C16 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L98-L99] |
| S07 | Shut-in numeric text is coerced; locale separators may become missing and later be filtered | no detection check exists for locale-formatted pressure | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L100-L100] |
| S08 | Working pressure numeric coercion assumes psig and no locale conversion | no detection check exists for locale-formatted working pressure | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L101-L101] |
| S09 | Daily-rate text is coerced without established unit or locale policy | no detection check exists | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L102-L102] |
| S10 | Open-flow text is coerced without established unit or locale policy | no detection check exists | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L103-L103] |
| S11 | Adjusted-deliverability text is coerced without established unit or locale policy | no detection check exists | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L104-L104] |
| S12 | Water-production text is coerced without established unit or locale policy | no detection check exists | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L105-L105] |
| S13 | Shared numeric conversion uses errors=coerce and optional column lookup; absence need not be a schema error | no detection check exists for missing numeric columns | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L112-L113] |
| S14 | Missing API returns None; other API strings lose dashes and are truncated to ten characters without digit/length validation | no detection check exists for malformed API strings | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L116-L119] |
| S15 | Missing API part returns None; short or undashed strings have no explicit invalid-identity counter | no detection check exists | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L122-L127] |
| S16 | Fallback empty Series exist for identity and descriptive columns, although public parser validates required columns first | C02 checks the public required-column guard | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L70-L77] |
| S17 | Latitude text silently coerces to missing; no missing-coordinate counter or bounds check | no detection check exists | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L78-L78] |
| S18 | Longitude text silently coerces to missing; no missing-coordinate counter or bounds check | no detection check exists | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L79-L79] |
| S19 | Depth text silently coerces to missing and assumes ft; no finite or plausible-depth bounds | no detection check exists for locale separators or infinity | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L80-L80] |
| S20 | Blank total-depth formation falls back to producing formation without a method flag | no detection check exists for provenance; C17 checks the fallback value | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L81-L83] |
| S21 | Date failures start at zero; integer casts count missing identities and depths; bookkeeping counts do not establish source completeness | C03 checks one date failure; no completeness detection check exists | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L84-L98] |
| S22 | Missing API returns None; populated strings are truncated without validating digits or length | no detection check exists | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L108-L111] |
| S23 | Missing/short API yields no county code; mapping failure is not an invalid-API error | no detection check exists | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L114-L118] |
| S24 | Absent date column yields all NaT with a zero failure count; public parser normally rejects missing required columns | C02 covers the public schema guard | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L121-L123] |
| S25 | Invalid populated dates coerce to NaT; int converts the failure count | C03 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L124-L129] |
| S26 | Missing date becomes pd.NA; unrecognized date text is passed through to coercion | C03 covers malformed-date coercion | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L132-L138] |
| S27 | Missing pressure column defaults to all missing; invalid/nonpositive values are excluded from curated data | C09 covers zero pressures; no detection check exists for missing pressure column | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L67-L74] |
| S28 | No surviving observations return empty output and quality rather than a completeness error | C09 checks the empty result, not refusal to publish | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L80-L86] |
| S29 | Fixed 14.7 psi conversion does not adjust for elevation or qualify upstream gauge units | C06 checks arithmetic only | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L9-L9] |
| S30 | float conversion and six-decimal rounding can propagate infinity or alter precision; no finite check | no detection check exists for nonfinite pressure | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L94-L94] |
| S31 | Gradient defaults to missing for nonpositive/no depth; positive infinity is not rejected | C07 covers ambiguous depth; no detection check exists for infinite depth | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L96-L96] |
| S32 | Optional row lookups propagate missing IDs/date; raw pressure is float-cast again | no detection check exists for malformed caller-supplied row schema | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L104-L116] |
| S33 | Wellhead/total-depth method and initial false/missing proxy fields are assigned by convention | C06 checks the stated convention; physical basis remains U1 | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L119-L126] |
| S34 | Optional source-file and row identifiers can remain absent without a provenance rejection | no detection check exists | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L127-L131] |
| S35 | Empty wells or missing api10 returns an empty lookup rather than rejecting an incomplete well table | no detection check exists | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L135-L138] |
| S36 | Wells with missing API are skipped without a dedicated skipped-join-row counter here | no detection check exists | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L139-L143] |
| S37 | No API candidate returns no match with missing-join and missing-depth flags | no detection check exists for the missing-candidate branch | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L151-L153] |
| S38 | Single API candidate is accepted without checking that source KID agrees | no detection check exists for contradictory KIDs | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L154-L155] |
| S39 | Multiple candidates use unique KID fallback; otherwise match is None and ambiguity flags are returned | C07 and C08 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L156-L163] |
| S40 | Missing year/identity rows are excluded from earliest selection; same-year ties use retained-row order | C10 covers missing year; no detection check exists for tie policy | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L171-L178] |
| S41 | Missing identity sets earliest flag to None instead of false | C07 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L179-L183] |
| S42 | Empty observations return a coverage schema; nonempty coverage counts rows, including missing keys | C09 covers empty observations; no dedicated coverage-schema assertion | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L186-L194] |
| S43 | Year coercion and integer min/max have null defaults when no populated year exists | C09 and C10 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L197-L205] |
| S44 | Regional county-subset count is an integer aggregation over a hardcoded set; zero is a count, not source absence | no detection check exists for a changed subset definition | issue pending (5) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L206-L208] |
| S45 | Absent well match returns None depth | C07 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L220-L222] |
| S46 | Depth numeric coercion and float conversion return None for invalid text but admit nonfinite positive depth | no detection check exists for invalid/nonfinite depth | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L223-L226] |
| S47 | Absent match or optional well value becomes pd.NA | C07 covers absent match | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L229-L233] |
| S48 | Missing pressure-row descriptive value falls back to matched well data | no detection check exists for origin tracking | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L236-L241] |
| S49 | Missing pressure county falls back to well county without an origin flag | no detection check exists for origin tracking | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L244-L246] |
| S50 | int converts external test_year; direct callers can supply fractional years that truncate | no detection check exists for fractional direct-call years | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L249-L251] |
| S51 | Empty/missing quality flags yield zero; missing strings fill with empty text before integer counting | C09 covers empty data; no detection check exists for dropped flags column | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L254-L258] |
| S52 | Ambiguous identity returns missing; otherwise API14 falls back to KID or missing | C07 and C08 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L261-L268] |
| S53 | No match returns an empty depth-flag list; `_well_match` now assigns missing_depth for both missing and ambiguous joins | C18 tests both unresolved join paths and excludes duplicate depth flags | Corrected for #1352, defect 1 | Current symbols: `_well_match`, `_depth_flags` in `packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py` |
| S54 | Positive depth returns no depth flags; nonpositive depth adds missing_depth | C18 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L274-L274] |
| S55 | Missing sources mapping defaults to empty catalog; string optional flags use bool rather than strict Boolean validation | no detection check exists | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L35-L48] |
| S56 | Empty county YAML defaults to empty mapping; all county names can become missing | C14 detects a missing mapping count | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L51-L55] |
| S57 | Optional source entries are deliberately skipped rather than fetched | no detection check exists for optional-source exclusion | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L73-L75] |
| S58 | Metadata defaults to empty; existing raw file is reused without prior digest, size or parse acceptance | no detection check exists for empty or tampered cached data | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L76-L85] |
| S59 | A zero-byte download can replace a raw file before parsing; response size/content is not validated | no detection check exists | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L104-L119] |
| S60 | Absent HTTP fields are None; unsuccessful metadata observation has no explicit readiness status | no detection check exists for absent headers | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L131-L139] |
| S61 | Empty YAML loads as empty dict, permitting an empty source catalog | no detection check exists | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L173-L174] |
| S62 | Naive supplied timestamp is assumed UTC without rejecting ambiguity | no detection check exists for naive timestamps | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L177-L181] |
| S63 | Missing well quality attrs defaults to empty dict; merged quality can omit source counters | no detection check exists | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L53-L57] |
| S64 | Empty or schema-deficient observations yield an empty limitations list | no detection check exists | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L88-L90] |
| S65 | Missing limitation cells and empty tokens are dropped when aggregating restrictions | no detection check exists | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L91-L98] |
| S66 | Staging name uses second-resolution time; initial cleanup ignores removal errors and can collide with another writer | no detection check exists for timestamp collision | issue pending (4) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L69-L70] |
| S67 | Normalized staging directory is intentionally skipped after its files are promoted | C11 and C12 | Documented fallback; regression scope as stated | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L97-L100] |
| S68 | Final cleanup ignores errors, so staging residue may survive without a reported cleanup failure | no detection check exists for cleanup failure | issue pending (4) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L102-L103] |
| S69 | Absent source manifest defaults to empty dict; absent code revision falls back to Git rather than requiring provenance | no detection check exists for missing provenance | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L151-L167] |
| S70 | Snapshot size starts at zero and hashes all bytes; an empty file receives a valid digest without a completeness failure | C11 checks one nonempty CSV; no empty-file rejection check exists | issue pending (2) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L183-L190] |
| S71 | Naive output timestamp is assumed UTC | no detection check exists for naive timestamps | issue pending (3) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L211-L215] |
| S72 | Promotion replaces normalized files and curated outputs individually; a later promotion failure can leave a mixed packet | C12 covers failure before promotion only; no detection check exists for late failure | issue pending (4) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L92-L101] |
| S73 | Direct calls with several API10 candidates stringify missing KIDs on both sides; a missing pressure KID can select the one missing well KID and emit kid_fallback_join instead of ambiguity flags | no detection check exists; C08 covers populated KIDs only | issue pending (1) | [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L156-L163] |

The two swallowed exception sites are S01 and S02; the four explicit `continue` sites are S04, S36, S57 and S67; empty-result persistence and zero defaults are included rather than treated as evidence of successful ingestion. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L73-L85] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L122-L128] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L97-L103] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L193-L204] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L75-L86] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L135-L144]
The related feature record is #725, not a confirmed incident report; its repository plan records malformed rows, pressure/depth assumptions and ambiguous joins as risks addressed by explicit tests. [docs/plans/2026-07-03-issue-725-kansas-kgs-pressure-observations.md:L616-L633]

## 7. Lessons log

| Date | Record | Lesson and evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-16 | Initial pack revision 0 | Empty tables, ambiguous joins and missing provenance have different meanings; zero rows do not establish a successful complete ingest. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L67-L86] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L147-L163] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L193-L204] | Sections 5–6 separate tested fallbacks from missing detection | Not assigned; issue pending (8) |

## 8. Ownership

Proposed review assignment: calculations quality manager for interim data-pipeline coverage; proposed deputy: an independent calculations reviewer; independent-provider review before clearance (AQG r0, sections 10–11; Module agent lifecycle, revision 0, section 6).
Producing role: module documentation contributor; unresolved tolerances, unit assumptions and classification disagreements go to the family quality manager; cross-family decisions go to the maintainers (Module agent lifecycle, revision 0, section 4, step E).
Named appointments, shared-log registration and clearance are pending under issue pending (8); status remains DRAFT.

## 9. Dependencies and implementation inventory

| Dependency or boundary | Evidence |
| --- | --- |
| Runtime | Distribution requires Python >=3.10, the core distribution, pandas >=2.3.3,<3.0, pyarrow >=14,<20 and PyYAML >=6,<7. [packages/worldenergydata-kansas_kgs/pyproject.toml:L10-L29] |
| Source identities | `pressure_proration`, `wells_master`, optional `formation_tops`; URLs are catalogued metadata, not a freshness or rights determination. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/source_catalog.yml:L1-L11] |
| County dictionary | Packaged YAML mapping used by both parsers; C14 counts 105 entries. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L51-L55] [tests/unit/kansas_kgs/test_raw_sources.py:L135-L142] |
| CLI caller | Command delegates to `build_pressure_observation_packet`, which delegates parsing, joining and output writes. [src/worldenergydata/cli/commands/kansas_kgs.py:L50-L68] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L40-L85] |
| Downstream screen boundary | The screen requires `well_key` and `field`; this package emits `api10` and `field_name`; direct compatibility without an adapter is not established. [src/worldenergydata/analysis/underpressured_screen/observations.py:L10-L54] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L22-L49] |

### Map basis and counted-family audit

Audit record, 2026-10-16: implementation map from `digitalmodel`, `docs/registry/implementation-map.yaml`, ref `codex/implmap-work`, map commit `3256bab95f84da3d9fadce8d5dcf8458d66d1eb4`, declared code/data revision `270c8759c374b67a7f032953e7fcdb14e0224461`.
The audit inspected all 13 map families and every nested implementation `path`, using exact package-prefix matching against the header scope: 0 in-package rows, 0 module map families, and an empty section-9 inventory.
A8 inventory: PASS, empty inventory; counted-family grep: NOT_APPLICABLE because no map family has an implementation row inside this package; no search signal is counted or filtered, and no further-implementation miss count is asserted.
The map follow-up is issue pending (6): add the section-3 method families for CSV normalization, ZIP well normalization, API/KID resolution, gauge-to-absolute conversion, pressure/depth screening, earliest selection, coverage aggregation and output provenance before a subsequent map revision counts them.

### Repository-wide additional discovery

The additional search included `src/`, `packages/` and `scripts/` at the code pin:

```bash
rg -n 'def (parse_proration_pressure|read_proration_pressures|parse_wells_master|read_wells_master|build_pressure_observations)|kansas_kgs' src scripts packages --glob '*.py'
rg -n 'SHUT_IN_PRESS|ks_wells\.zip|kansas_proration' src scripts packages --glob '*.py'
```

| Further implementation | Classification and map follow-up |
| --- | --- |
| `src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py` | Computes CSV/ZIP parsing itself, rather than delegating to this package; outside-package map gap, issue pending (6). [src/worldenergydata/modules/state_regulators/kansas_kgs/parsers.py:L67-L109] |
| `src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py` | Computes KID joins, pressure conversion, gradient, earliest flag and coverage itself; outside-package map gap, issue pending (6). [src/worldenergydata/modules/state_regulators/kansas_kgs/pipeline.py:L88-L185] |
| `src/worldenergydata/cli/commands/kansas_kgs.py` | Delegates the build and formats a summary; helper, not another calculation. [src/worldenergydata/cli/commands/kansas_kgs.py:L50-L83] |
| `cli_support.py`, `io.py` | Orchestration, serialization and manifest helpers; formulas and joins are listed in section 3. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L40-L85] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L40-L103] |

## 10. Coverage and open items

### Reading coverage

The package scope comprises seven Python files and two YAML resources; module-specific reading covered every Python function, both data resources, the package README and distribution metadata. [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/__init__.py:L1-L4] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/cli_support.py:L1-L98] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/io.py:L1-L219] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/observations.py:L1-L286] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/pressure.py:L1-L129] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/raw_sources.py:L1-L181] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/wells.py:L1-L138] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/source_catalog.yml:L1-L11] [packages/worldenergydata-kansas_kgs/src/worldenergydata/kansas_kgs/data/kansas_counties.yml:L1-L105] [packages/worldenergydata-kansas_kgs/README.md:L1-L4] [packages/worldenergydata-kansas_kgs/pyproject.toml:L1-L41]

| Test file coverage | Scope and evidence |
| --- | --- |
| `tests/unit/kansas_kgs/test_pressure_parser.py` | Parser quirks, zero pressure, date policy, quality counters, Latin-1 and empty schema. [tests/unit/kansas_kgs/test_pressure_parser.py:L8-L100] |
| `tests/unit/kansas_kgs/test_wells_parser.py` | ZIP normalization, required columns, dates and formation fallback. [tests/unit/kansas_kgs/test_wells_parser.py:L11-L64] |
| `tests/unit/kansas_kgs/test_observations.py` | Unit-convention arithmetic, identity ambiguity, KID fallback, coverage, county fallback, empty data and missing years. [tests/unit/kansas_kgs/test_observations.py:L8-L158] |
| `tests/unit/kansas_kgs/test_raw_sources.py` | Root guards, successful source manifests, supplied metadata, cache reuse and county dictionary. [tests/unit/kansas_kgs/test_raw_sources.py:L12-L142] |
| `tests/unit/kansas_kgs/test_io.py` | Writer guard, serialization, manifest and early write-failure preservation. [tests/unit/kansas_kgs/test_io.py:L13-L122] |
| `tests/unit/kansas_kgs/test_cli.py` | Build, dry run and CLI discovery. [tests/unit/kansas_kgs/test_cli.py:L14-L62] |
| `tests/unit/state_regulators/test_kansas_kgs.py` | Separate legacy route; not evidence of package equivalence. [tests/unit/state_regulators/test_kansas_kgs.py:L67-L129] |
| Downstream and contract tests | `tests/unit/analysis/test_underpressured_observations.py`, `tests/unit/analysis/test_underpressured_screen.py`, `tests/contracts/`; execution counts recorded in section 4 |

Documentation discovery used `rg -l -i 'kansas[-_ ]kgs' docs README*`; the following files were found, with module-specific passages reviewed; unrelated sections of wider plans remain outside this pack's main path, issue pending (8).

- `docs/data-sources/onshore/kansas-kgs/pressure-observations.md`
- `docs/data-sources/onshore/state-well-databases/kansas-kgs-ingest.md`
- `docs/data-sources/onshore/state-well-databases/source-catalog.md`
- `docs/data-sources/onshore/state-well-databases/underpressured-gas-fields.md`
- `docs/modules/repository-architecture.md`
- `docs/plans/2026-07-03-issue-709-texas-rrc-pressure-observations.md`
- `docs/plans/2026-07-03-issue-725-kansas-kgs-pressure-observations.md`
- `docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md`
- `docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md`
- `docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md`
- `docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md`
- `docs/plans/README.md`

There are 0 module-local README or documentation files at the code pin; the distribution README is outside the package, and the new pack is the package documentation entry.

### Open-item register

Every item below is assigned to the maintainers for issue creation or assignment; draft numbers refer to [ISSUES_DRAFT.md](ISSUES_DRAFT.md) and must be replaced with issue numbers before independent clearance.

| Item | Required evidence or disposition | Proposed responsible role | Tracking |
| --- | --- | --- | --- |
| U1: pressure/depth basis | Qualify gauge units, depth datum, atmospheric assumption and independent benchmark; regression arithmetic is not independent physical validation | Calculations reviewer | issue pending (5) |
| U2: ancillary numeric units | Versioned dictionary for rate, deliverability and water-production columns | Calculations reviewer | issue pending (5) |
| U3: spatial conventions | Coordinate datum, origin, sign convention and unit metadata | Calculations reviewer | issue pending (5) |
| U4: live source readiness | Re-derive source coverage/freshness, retain content digests and rights/readiness metadata; historical docs counts are not adopted | Calculations reviewer | issue pending (5) |
| Input validation gaps | Section-6 numeric/identity/coercion gaps, including nonfinite values and direct-call schema gaps | Data-pipeline maintainer | issue pending (1) |
| Empty/completeness gaps | Section-6 empty tables, optional missing counters and fallback-origin gaps | Data-pipeline maintainer | issue pending (2) |
| Provenance gaps | Section-6 raw validation, metadata exceptions, timestamp assumptions and revision/source-manifest gaps | Data-pipeline maintainer | issue pending (3) |
| Promotion gaps | Section-6 cleanup suppression, timestamp collision and partial-promotion cases | Data-pipeline maintainer | issue pending (4) |
| Parallel paths and map | Inventory missing method families; reconcile legacy/package schema and source documentation routes | Implementation-map maintainer | issue pending (6) |
| Distribution inclusion | Existing nested Markdown package-data glob also matches this pack; wheel exclusion is not established. [packages/worldenergydata-kansas_kgs/pyproject.toml:L40-L41] | Packaging maintainer | issue pending (7) |
| Documentation codenaming | Identifying record terminology in 7 discovered documentation files and fixture contents are not repeated; a separate content change is needed | Documentation maintainer | issue pending (8) |
| Review and reading boundary | Independent clearance, family/deputy appointments, shared-log registration, remaining wider-document reading and conversion of drafts to issues | Documentation maintainer | issue pending (8) |

UNVERIFIED: U4, live source freshness, complete raw-data row counts, distribution-wide readiness and external source rights were not established by offline fixture tests; issue pending (5). [docs/data-sources/onshore/kansas-kgs/pressure-observations.md:L46-L50]
Historical documentation records a prior production run; its counts and year range are not current-run validation. [docs/data-sources/onshore/kansas-kgs/pressure-observations.md:L46-L50]
This revision changes documentation only; no raw dataset, solver run, private sidecar or engineering acceptance is supplied.
