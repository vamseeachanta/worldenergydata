# mexico_cnh module knowledge pack

| Header | Value |
| --- | --- |
| Module | `mexico_cnh` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `92b13dce6b3121cbe827f17327c6dde7fcd6dc5c` |
| Analysis family | EC; data pipeline; AQG r0 Python calculations gate set |
| Quality manager role | Calculations quality manager, interim data-pipeline coverage |
| Status | DRAFT |

## 1. Purpose and scope

`MexicoCNH.router` validates configuration, routes collection, optionally requests analysis, and writes status and collected-type keys into the returned configuration. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L91-L145]

The seven collection methods currently return empty lists; a completed status therefore does not establish that any source records were acquired. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L110-L150] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L126-L131]

The implemented local paths comprise configurable endpoint metadata, record validation, Excel normalization, PDF table extraction and a separate Selenium export interface. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/endpoints.py:L34-L43] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L396-L488] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L119-L163] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L60-L115] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L573-L630]

`analysis` and `processors` contain empty export lists; enabling the main router's analysis branch requests an unavailable `MexicoCNHAnalysis` symbol. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/analysis/__init__.py:L1-L11] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/processors/__init__.py:L1-L11] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L116-L138]

Package metadata classifies the distribution as Alpha; this is metadata, not a demonstrated live-data maturity level. [packages/worldenergydata-mexico_cnh/pyproject.toml:L15-L24]

Silent-failure coverage includes overwritten browser language preferences, PDF separator conversion that rescales or drops well-formed numbers, and accented headers that bypass mapping and numeric coercion; section 6 records the missing detection checks under #1282, with #431 also tracking browser preferences and the download race. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L218-L236] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L249-L264] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L174-L190] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L233-L286]

### Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-15 | Initial inventory, local regression evidence and open-item register |
| 1 | 2026-10-15 | Add silent-failure coverage and issue links; correct test citations and distinguish range resolution from claim support |

## 2. Inputs and outputs

### Inputs

| Name | Unit / format | Allowed range and default | Source and evidence |
| --- | --- | --- | --- |
| `cfg.data_types` | category list | Default empty; seven accepted categories | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L27-L36] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L47-L48] |
| `cfg.regions`, `cfg.contract_rounds` | category lists | Optional; checked for membership; collection methods do not consume filters | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L179-L197] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L110-L150] |
| `cfg.selenium.timeout`, `headless` | seconds, boolean | Timeout positive; headless boolean when present; helper defaults 60 s and true; helper argument mismatch in section 6 | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L199-L211] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L162-L170] |
| `cfg.output.format` | format token | Accepts csv, json, parquet, excel; collection router has no writer call | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L213-L222] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L47-L80] |
| `cfg.cache`, `continue_on_error` | boolean / directory | Cache disabled unless enabled; continue-on-error defaults true | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L50-L69] |
| Excel workbook | XLSX via openpyxl | Sheet index 0, skip rows 0, normalize true; file must exist | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L119-L163] |
| PDF document / page selection | PDF, zero-based page indices | All pages if selection is None; pdfplumber required | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L43-L58] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L60-L102] |
| Record coordinates | decimal degrees | General bounds latitude 14.53–32.72, longitude -118.40–-86.70; offshore rectangle latitude 18–27, longitude -98–-86 | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L27-L37] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L141-L197] |
| `total_depth` | metres by code comment | 0–15000 when present, checked by `validate_well_data` | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L430-L438] |
| `volume`, `unit`, `max_daily` | caller-labelled volume | Optional None; default unit bbl and limit 500000; no conversion by unit | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L309-L344] |
| Production date | string | Five attempted formats; default min year 1900, maximum current year + 5 | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L346-L394] |

### Outputs

| Name | Unit / structure | Behaviour and evidence |
| --- | --- | --- |
| Main router result | configuration dictionary | `status`, `data_collected`, nested data and analysis mappings | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L95-L101] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L126-L144] |
| Data router result | tuple of config and keyed data dictionary | Includes empty lists; record counts use list length, otherwise 1 | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L55-L80] |
| Excel normalized tables | pandas DataFrame | Spanish column mapping, date coercion, string identifiers; numeric production, coordinates and depths coerced in specialized parsers | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L165-L214] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L233-L286] |
| PDF tables / text / metadata | list of DataFrames, string, dictionary | First row treated as headers; cleaned text; page dimensions copied from the first page | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L129-L179] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L268-L332] |
| Scraper exports / screenshots | filesystem Path | Export methods return downloaded paths; screenshot helper can return None | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L620-L630] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L685-L696] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L754-L777] |
| Validator results / statistics | boolean plus error(s); counts and dimensionless fraction | Individual validations return tuples; aggregate record validation increments counters; statistics divide successes by max(validations, 1) | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L440-L488] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L522-L536] |

UNVERIFIED: The upstream workbooks' physical units, averaging periods, numeric separator conventions, coordinate datum, projected-coordinate origin and axis conventions are not established by the parser's renaming and numeric coercion; require a versioned source specification before engineering use; section 10 item coverage-units. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L27-L58] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L233-L286]

## 3. Method and governing standards

| Method | Implementing definition and evidence | Reference status |
| --- | --- | --- |
| Configuration membership and scalar checks | `MexicoCNH._validate_config` rejects invalid categories, nonpositive timeouts and unknown output-format tokens | Local software criteria; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L147-L224] |
| Collection dispatch | `MexicoCNHData._collect_data_type` dispatches seven keys; unknown keys return None | Placeholder acquisition, not a source-data algorithm; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L93-L150] |
| Header normalization | `CNHExcelLoader.normalize_columns` lowercases, strips, replaces spaces/hyphens with underscores and applies mappings | Local mapping; no accent removal; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L165-L190] |
| Tabular conversion | `_convert_dtypes`, `parse_production_report`, `parse_well_report` coerce dates/numbers, then production parser sorts by date | Local parsing policy; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L201-L253] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L272-L286] |
| PDF extraction | `CNHPDFParser.extract_tables`, `_table_to_dataframe`, `_clean_cell` select pages, clean whitespace and form tables | Local heuristics and pdfplumber; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L87-L179] |
| PDF production selection | `extract_production_data` matches header keywords or falls back to the largest table; `_convert_numeric_columns` replaces commas with periods and converts only above 50% numeric rows | Local heuristics, not a locale-aware unit conversion; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L203-L266] |
| Identifiers and classification | `validate_clave_pozo`, `validate_contract_id`, `validate_hydrocarbon_type`, `normalize_clave_pozo` use patterns, lists and permissive fallbacks | Code policy, not evidence of regulatory acceptance; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L97-L139] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L260-L307] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L500-L520] |
| Geographic and production screening | `validate_mexico_coordinates`, `validate_utm_zone`, `validate_production_volume`, `validate_date_range`, record-level validators | Approximate bounds and local plausibility checks; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L27-L40] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L158-L217] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L309-L488] |
| Statistics | `get_statistics`: `(validation_count - error_count) / max(validation_count, 1)` | Dimensionless local count ratio; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L529-L536] |
| Browser export | `SIHScraper` starts Chrome, applies filters, clicks export and waits for stable nonempty downloads | Local selectors, action delays and file polling; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L245-L301] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L451-L571] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L698-L752] |

No governing engineering standard is asserted here: the methods above are documented as local software policies rather than standards-derived design calculations. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L27-L63] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L203-L266]

UNVERIFIED: Regulatory authority for the hard-coded geographic and production limits, identifier fallback policy and date horizon has not been established; no standards-derived result or Citation sidecar is claimed; section 10 item coverage-rules. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L27-L63] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L130-L139] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L309-L394]

## 4. Validated worked examples

Validated examples: **0**; the cases below use local code policies and synthetic test expectations, without a versioned independent regulator dataset or published benchmark; they are regression examples. [tests/unit/mexico_cnh/test_validators.py:L78-L85] [tests/unit/mexico_cnh/test_validators.py:L264-L296] [tests/unit/mexico_cnh/test_validators.py:L461-L468] [tests/unit/mexico_cnh/data/test_mexico_cnh_data.py:L68-L71]

Offline result record: all five nodes below PASS at BASE `92b13dce6b3121cbe827f17327c6dde7fcd6dc5c`; all five nodes also PASS in the after-edit rerun on the same code pin.

| Case | Input and expected value | Tolerance / basis | Existing test node ID and evidence | BASE |
| --- | --- | --- | --- | --- |
| regression-coordinates | Embedded coordinates 19.4°, -99.1°; valid = true | 0 boolean mismatches; local bounds policy | `tests/unit/mexico_cnh/test_validators.py::TestValidateMexicoCoordinates::test_valid_onshore` [tests/unit/mexico_cnh/test_validators.py:L78-L80] | PASS |
| regression-negative-volume | Embedded volume -100 bbl; valid = false | 0 boolean mismatches; nonnegative input policy | `tests/unit/mexico_cnh/test_validators.py::TestValidateProductionVolume::test_negative` [tests/unit/mexico_cnh/test_validators.py:L262-L265] | PASS |
| regression-statistics | Two record validations, one error; success fraction 0.5 | 0 absolute fraction difference; local counter semantics | `tests/unit/mexico_cnh/test_validators.py::TestGetStatistics::test_after_validations` [tests/unit/mexico_cnh/test_validators.py:L461-L468] | PASS |
| regression-dispatch | Three requested categories; 3 keys in collected-data dictionary | 0 key-count difference; does not check nonempty records | `tests/unit/mexico_cnh/data/test_mexico_cnh_data.py::TestRouter::test_multiple_types` [tests/unit/mexico_cnh/data/test_mexico_cnh_data.py:L68-L71] | PASS |
| regression-timeout | Map portal timeout 90 s | 0 s difference; configured timeout policy | `tests/unit/mexico_cnh/test_endpoints.py::TestDefaultTimeouts::test_maps_has_longest_timeout` [tests/unit/mexico_cnh/test_endpoints.py:L117-L118] | PASS |

The count-ratio hand check in section 5 is an arithmetic check only; it does not validate the scientific or regulatory basis of a production record. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L529-L536]

## 5. QA gates

Gate applicability follows AQG r0, §10 “Family mapping”, Python calculations, and §9 “G5 QA appendix”.

| Gate | Applicability | Module-specific check IDs |
| --- | --- | --- |
| G0 | Applicable: inputs, units and citations | input-coordinates, input-production |
| G1 | Applicable: Python import and offline test route | import-all, unit-suite |
| G2 | Applicable: independent arithmetic and mapping checks | statistics-hand, header-mapping |
| G3 | NOT_APPLICABLE: tabular parsing and scalar validation have no dynamics simulation | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L233-L286] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L309-L344] |
| G4 | NOT_APPLICABLE: these methods have no diffraction body or mesh | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L203-L266] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L396-L488] |
| G5 | Applicable: evidence and traceability for any downstream report | evidence-coverage |

The following are executable acceptance checks defined by this pack; their pass criteria describe local software behaviour, with the domain-validity gaps retained in section 10.

| Check ID | Gate | Procedure and numeric pass criterion | Evidence and observed result |
| --- | --- | --- | --- |
| input-coordinates | G0 | Call `validate_mexico_coordinates(19.4, -99.1)` and `(10, -99)`; exactly 1 accepted and 1 rejected record, 0 boolean mismatches | PASS in scratch check; corresponding test branches [tests/unit/mexico_cnh/test_validators.py:L78-L85] |
| input-production | G0 | Call `validate_production_volume` with 0, -100 and 600000; exactly 1 accepted and 2 rejected records, 0 mismatches; label caller units before using values | PASS in scratch check; default bbl label, no conversion [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L309-L344] [tests/unit/mexico_cnh/test_validators.py:L256-L282] |
| import-all | G1 | Import every Python module under the package; 14 successful module imports, 0 import errors; do not instantiate or start the scraper | PASS in scratch check; public exports and guarded optional imports [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/__init__.py:L44-L52] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/__init__.py:L10-L26] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L23-L47] |
| unit-suite | G1 | Run `uv run --extra test python -m pytest tests/unit/mexico_cnh -q -rA -p no:cacheprovider` with temporary and coverage outputs directed to scratch; 160 passed test nodes, 0 failed nodes, 0 skipped nodes | BASE and after-edit PASS; tests exercise placeholders and constants as well as validators [tests/unit/mexico_cnh/data/test_mexico_cnh_data.py:L15-L54] [tests/unit/mexico_cnh/scrapers/test_sih_scraper.py:L66-L86] |
| statistics-hand | G2 | Validate the two records in `test_after_validations`; compare counters with 2 validations and 1 error, and fraction with the separately counted outcomes `(1 + 0) / 2 = 0.5`; absolute error 0 fraction | PASS in scratch check; no regulatory interpretation implied [tests/unit/mexico_cnh/test_validators.py:L461-L468] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L529-L536] |
| header-mapping | G2 | Normalize a synthetic two-column DataFrame with headers `Produccion Aceite`, `Fecha`; require `oil_production`, `date`, 2 mapped columns and 0 changed data values | PASS in scratch check; mapping and transformation [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L27-L45] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L174-L190] |
| evidence-coverage | G5 | Resolve all citation paths and ranges at the code pin, inspect whether changed citations support their claims, reconcile each example with its executed node, and link each open item; require 0 unresolved ranges, 0 unsupported changed citations, 0 missing result records, 0 unlinked open items, 10 numbered sections | Final evidence check: PASS; for a downstream report also require 0 results without a retained input digest, units and QA record; AQG r0, §9 “G5 QA appendix” |

The `header-mapping` check uses unaccented headers only and cannot detect accented-header loss. No detection check exists for the three #1282 paths: browser preference replacement, locale-dependent PDF numeric corruption or accented headers bypassing parser coercion. Passing the seven checks does not establish their absence; section 6 records each separately.

These checks provide no live portal acceptance record; browser navigation, export selectors, downloaded-source fingerprints and a production QA-appendix generator remain outside the demonstrated offline results; issue #720 and issue pending (4). [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L405-L449] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L573-L752]

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

The following findings were confirmed against the code pin. Executed checks are distinguished from prospective criteria and paths for which no detection check exists; the focused suite does not cover all findings.

| Symptom / cause | Detection check and observed evidence | Tracking / date |
| --- | --- | --- |
| SF1: a second Chrome `prefs` option replaces the language dictionary with download preferences; `intl.accept_languages` is lost without a message, leaving only `--lang=es-MX` | no detection check exists; `unit-suite` covers scraper constants and errors, not combined browser preference keys | #1282; #431; 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L218-L236] [tests/unit/mexico_cnh/scrapers/test_sih_scraper.py:L19-L86] |
| SF2: PDF comma-to-period replacement turns `1,234` into 1.234, a factor of 1000.0 too small; `12,345,678`, `1,234.5` and `1.234,5` become NaN; only simple decimal-comma input such as `1234,5` converts as intended. Converted columns replace originals when more than half the rows parse. DataFrame construction failures drop the table with only a warning and no rejected-table count | no detection check exists; `header-mapping` does not exercise PDF values, separator conventions or rejected-table accounting | #1282; issue pending (4); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L151-L156] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L103-L115] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L249-L264] |
| SF3: exact mapping leaves `Producción Aceite` as `producción_aceite` and `Año` as `año`; only matched renames are logged, at debug level. Production and well parsers then skip coercion of columns whose mapped English names are absent | no detection check exists; `header-mapping` uses unaccented input and provides no accented-header or parser-coercion coverage | #1282; issue pending (4); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L27-L46] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L65-L68] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L174-L190] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L233-L247] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L272-L286] |
| Empty collections can be reported completed; all seven collectors return `[]`, exceptions continue by default | Invoke `MexicoCNH.router` with the seven accepted categories; observed 7 zero record counts and completed status; require at least 1 acquired record before a future live-data claim; `unit-suite` currently preserves placeholders. Collector exceptions log an error but omit the requested type from `collected_types` and `record_counts`, while the main router still completes; no detection check exists for this omission; prospective criterion: 0 requested types missing from `collected_types` (count) | #720; 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L55-L80] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L110-L150] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L126-L131] |
| Filters can be silently unapplied; date and field selector loops exhaust without an explicit failure; download polling snapshots files after export is initiated; absent well-tab selectors do not stop export, and absent well-export selectors fall back to the general production export, returning it as well data | Prospective isolated browser-fixture check: 0 silent filter failures, 0 missed completed downloads and 0 production exports returned as well data; no detection check exists in the dedicated suite for these paths | #720; #431; 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L468-L523] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L620-L624] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L655-L689] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L717-L749] [tests/unit/mexico_cnh/scrapers/test_sih_scraper.py:L1-L86] |
| PDF fallback may select an unrelated largest table; failed Excel sheets can disappear from results | `header-mapping` covers only renaming; future loader fixtures should require 0 unexpected tables, missing values or omitted sheets; no detection check exists in the dedicated suite for parser loss | issue pending (4); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L222-L264] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L245-L247] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L318-L329] |
| NaN coordinates and volumes are accepted; an English-key zero latitude can be lost through truth-value fallback; empty records are accepted | Offline probes returned true for `(NaN, -99)`, NaN volume, `{'latitude': 0, 'longitude': -99}` and `{}`; future finite/required-field criterion is 0 invalid accepted records; `input-coordinates` and `input-production` do not yet cover these cases | issue pending (1); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L161-L197] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L329-L344] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L408-L444] |
| Data helper passes unsupported `timeout`; cleanup calls nonexistent `close` while scraper exposes `stop` | `inspect.signature(SIHScraper).bind(headless=True, timeout=60)` raises `TypeError: got an unexpected keyword argument 'timeout'`; inspect members: close absent, stop present; no detection check exists in the dedicated suite | issue pending (2); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L162-L177] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L136-L143] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L291-L301] |
| Enabling analysis raises ImportError for `MexicoCNHAnalysis` | Call router with empty data types and analysis enabled; observed ImportError; require 0 import errors before enabling analysis in a workflow; no detection check exists in the dedicated suite | #720; 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L116-L138] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/analysis/__init__.py:L1-L11] |
| Router and validator contract-round lists differ by the additional validator token `FMP` | Compare lists: 1 extra token; require an explicitly agreed list before treating record and configuration validation as interchangeable | issue pending (1); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L38-L46] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L42-L51] |
| Separate exception hierarchies: browser errors inherit `Exception`; structured module errors inherit `ModuleError` | Import and compare bases; require 0 missed exceptions in a consumer's intended catch path; `unit-suite` checks the hierarchies separately | issue pending (2); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L62-L91] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/errors.py:L30-L60] [tests/unit/mexico_cnh/test_errors.py:L14-L24] |
| CLI scrape/download can print success and a save path with no records or writer; scrape passes `scraper` instead of `selenium` and an unread `date_range`; commands read `data_scraped`/`data_downloaded` instead of `data_collected` | no detection check exists; require 0 success/save messages without nonempty collected records and a verified output file; `unit-suite` does not run the CLI | #720; issue pending (4); 2026-10-15 [src/worldenergydata/cli/commands/mexico_cnh.py:L202-L231] [src/worldenergydata/cli/commands/mexico_cnh.py:L258-L269] [src/worldenergydata/cli/commands/mexico_cnh.py:L398-L445] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L126-L131] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L47-L80] |
| Identifier fallbacks accept a 24-letter key and `A_B_C` even without a strict pattern match; the boolean expression accepts alphabetic starts, and contract IDs without the `CNH-` prefix are accepted; messages are debug-only | no detection check exists for these fallback cases; prospective criterion: 0 nonstandard identifiers accepted without an explicit warning or invalid result, including both key fixtures and a contract ID without a recognized prefix or round | issue pending (1); 2026-10-15 [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L116-L134] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L260-L281] |

Issue #1282 tracks SF1–SF3, and open #431 records overwritten browser preferences and race-prone download polling in this module. Issues #720 and #713 remain ingestion/chain work references; none establishes independently validated parser examples. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L110-L150]

## 7. Lessons log

| Date | Entry | Lesson | Evidence | Pack change / shared record |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | A passing placeholder-collection test and completed status do not prove source acquisition | [tests/unit/mexico_cnh/data/test_mexico_cnh_data.py:L15-L49] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L126-L131] | Sections 1, 4–6 distinguish regression evidence from live-data evidence; #720 |
| 2026-10-15 | Initial pack | Bounds comparisons need separate nonfinite and missing-data checks before engineering use | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L161-L197] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L329-L344] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L408-L444] | Sections 5, 6 and 10 retain the gap; issue pending (1) |

## 8. Ownership

Review assignment: calculations quality manager for interim data-pipeline review; producing role: module documentation contributor; unresolved module checks go to that quality manager, with cross-family scope decisions reserved to the maintainer (AQG r0, §11 “Sign-off and independence”).

UNVERIFIED: A permanent data-pipeline quality manager and named deputy role are not established by the inspected module files; retain interim calculations review and ask the maintainer to record the deputy assignment; section 10 item coverage-review; issue pending (4).

## 9. Dependencies and implementation inventory

### Upstream and downstream routes

| Relationship | Verified dependency or boundary | Evidence |
| --- | --- | --- |
| Distribution | Workspace member depends on core, pandas and openpyxl; distribution version 0.1.0 differs from module `__version__` 1.0.0 | [packages/worldenergydata-mexico_cnh/pyproject.toml:L5-L10] [packages/worldenergydata-mexico_cnh/pyproject.toml:L29-L33] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/__init__.py:L49-L52] |
| Common layer | Package initialization uses common logging; structured errors use common `ModuleError` | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/__init__.py:L44-L49] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/errors.py:L28-L45] |
| Optional parsers and browser | PDF constructor requires pdfplumber; browser constructor requires Selenium and startup attempts Chrome WebDriver | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L13-L47] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L157-L170] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L259-L271] |
| Source metadata | Endpoint constants and scraper URLs describe intended portals; endpoint enum/defaults do not establish live availability | [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/endpoints.py:L54-L112] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L112-L130] |
| Main engine and CLI | Engine dispatch constructs `MexicoCNH`; CLI scrape constructs the module and reads `data_scraped`, whereas router writes `data_collected` | [src/worldenergydata/engine.py:L137-L141] [src/worldenergydata/cli/commands/mexico_cnh.py:L225-L231] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L126-L131] |
| Pipeline adapter | `CNHAdapter.adapt` emits empty metadata/warnings rather than normalized production data | [packages/worldenergydata-bsee/src/worldenergydata/bsee/pipeline/adapters/cnh_adapter.py:L50-L87] |
| Unified production adapter | `MexicoCnhAdapter._generate_field_rows` generates synthetic rates with source token `mexico_cnh_mock`; it is not evidence of this package ingesting observations | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/mexico_cnh_adapter.py:L66-L103] |

UNVERIFIED: Upstream source dataset revisions and browser/driver compatibility are not validated in this offline pack; no live source, solver version or acquired-data freshness is certified; section 10 item coverage-source; #720. [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L259-L271] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/endpoints.py:L102-L112]

### Map inventory and counted-family audit

Audit source: `digitalmodel`, `docs/registry/implementation-map.yaml`, ref `origin/codex/implmap-work`, file revision `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; the map names data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954` (implementation map, header and families inventory at that revision).

Computed inventory: 13 map families examined, **0 families with an implementation path inside this package**, **0 in-package implementation rows**; the section-9 map inventory is therefore empty (implementation map, families inventory at the source revision above).

A8 counted-family grep: **NOT_APPLICABLE**, because no map family has an in-package row; counted families 0, eligible additional-implementation misses 0; no family is admitted solely by a vocabulary match (implementation map, families inventory at the source revision above).

Map follow-up: add the local families from section 3 first: configuration validation, collection dispatch, Excel header/type normalization, PDF extraction/selection, identifier screening, geographic/production/date screening, validation statistics and browser export/polling; issue pending (4). [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L147-L224] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L93-L150] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L165-L286] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L87-L266] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L83-L536] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L573-L752]

Repository-wide discovery included tracked Python files under `scripts/`, `src/`, `packages/` and `tests/`; the additional independent CLI well-key criterion parses numeric region/basin/area components instead of delegating to `MexicoCNHValidator`, while validator convenience functions delegate to the listed class. [src/worldenergydata/cli/commands/mexico_cnh.py:L488-L570] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L539-L558]

The CLI criterion and the separate synthetic production generator are map follow-up findings outside the package; neither changes the empty-package A8 outcome; issue pending (4). [src/worldenergydata/cli/commands/mexico_cnh.py:L517-L570] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/mexico_cnh_adapter.py:L66-L103]

## 10. Coverage and open items

### Read coverage

Code read: all 14 Python files in the package, including subpackages; no subpackage was excluded from the package scope.

- `__init__.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/__init__.py:L1-L52]
- `analysis/__init__.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/analysis/__init__.py:L1-L11]
- `data/__init__.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/__init__.py:L1-L26]
- `data/loaders/__init__.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/__init__.py:L1-L26]
- `data/loaders/excel_loader.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L1-L329]
- `data/loaders/pdf_parser.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L1-L372]
- `data/mexico_cnh_data.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L1-L177]
- `endpoints.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/endpoints.py:L1-L347]
- `errors.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/errors.py:L1-L518]
- `mexico_cnh.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/mexico_cnh.py:L1-L236]
- `processors/__init__.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/processors/__init__.py:L1-L11]
- `scrapers/__init__.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/__init__.py:L1-L27]
- `scrapers/sih_scraper.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L1-L833]
- `validators.py` [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L1-L558]

Dedicated tests read and run: 5 files, 160 passing nodes in the BASE command; zero failures, skips or NOT_RUN nodes. The earlier approximate count was not used.

| Test file | Collected / passed at BASE | Source |
| --- | --- | --- |
| `tests/unit/mexico_cnh/data/test_mexico_cnh_data.py` | 14 / 14 | [tests/unit/mexico_cnh/data/test_mexico_cnh_data.py:L8-L89] |
| `tests/unit/mexico_cnh/scrapers/test_sih_scraper.py` | 10 / 10 | [tests/unit/mexico_cnh/scrapers/test_sih_scraper.py:L19-L86] |
| `tests/unit/mexico_cnh/test_endpoints.py` | 20 / 20 | [tests/unit/mexico_cnh/test_endpoints.py:L12-L128] |
| `tests/unit/mexico_cnh/test_errors.py` | 30 / 30 | [tests/unit/mexico_cnh/test_errors.py:L14-L181] |
| `tests/unit/mexico_cnh/test_validators.py` | 86 / 86 | [tests/unit/mexico_cnh/test_validators.py:L11-L490] |

Initial execution record: ordinary `uv run --extra test python -m pytest tests/unit/mexico_cnh -q -rA -p no:cacheprovider`, with `--allow-existing-tree-changes`, explicit scratch `--basetemp`, coverage data and report destinations; canonical addopts retained, no `--no-sources`, no addopts override and no parallel workers. BASE code pin: `92b13dce6b3121cbe827f17327c6dde7fcd6dc5c`. After-edit result: 160 run, 160 passed, 0 failed, 0 skipped, 0 NOT_RUN, on the uncommitted documentation tree with the same code pin; BASE counts are identical.

Initial supplemental contract-domain execution on the same code pin and uncommitted documentation tree: `uv run --extra test python -m pytest tests/contracts -q -rA -p no:cacheprovider`, with the same scratch-output and existing-tree options; 46 run, 46 passed, 0 failed, 0 skipped, 0 NOT_RUN. [tests/contracts/test_assetutilities_engine_contract.py:L14-L31] [tests/contracts/test_flaky_register_schema.py:L115-L127]

Revision-1 verification: BASE `408167671b9797d0d7223a8ff8cff62fb08d66a0` and the uncommitted documentation tree each ran the dedicated selection: 160 passed, 0 failed, 0 skipped. The isolated `uv run --no-project --with pytest` route supplied the declared test/import dependencies, retained canonical pytest configuration and directed temporary, coverage and performance outputs to scratch; the after-edit command used `--allow-existing-tree-changes`. All five section-4 nodes passed in each selection. Offline checks imported all 14 modules and repeated the coordinate, volume, statistics and unaccented-header criteria. Separate diagnostic probes reproduced SF1–SF3 and the identifier fallback; these observations provide no corrected-behaviour acceptance fixture in the dedicated suite. The initial 46 contract-test results above were not rerun for this documentation correction.

Other discovery references are in the common exception, CLI smoke/documentation, unified production and adapter-registration test domains; they are outside this package's dedicated test result count; full consumer-domain test review is deferred under coverage-consumers; issue pending (4).

Package documentation read: workspace-member README and metadata. [packages/worldenergydata-mexico_cnh/README.md:L1-L8] [packages/worldenergydata-mexico_cnh/pyproject.toml:L5-L10]

Documentation discovery below records the module-related passages inspected; historical readiness and source-access claims are not adopted as live evidence, and full-document reconciliation remains coverage-docs; issue pending (4).

- `docs/CLI.md` [docs/CLI.md:L582-L582]
- `docs/adr/0001-domain-package-split.md` [docs/adr/0001-domain-package-split.md:L48-L48]
- `docs/modules/repository-architecture.md` [docs/modules/repository-architecture.md:L119-L119]
- `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md` [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L19-L19]
- `docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md` [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L15-L15]
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L17-L17]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml` [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L122-L122]
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12]
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml` [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml:L296-L296]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md` [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L18-L18]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L16-L16]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml` [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L91-L91]
- `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L69-L69]
- `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md` [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L170-L170]
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L16-L16]
- `docs/reports/cli-smoke-report-2026-05-11.md` [docs/reports/cli-smoke-report-2026-05-11.md:L26-L26]
- `docs/reports/data-freshness-scorecard-2026-06-08.md` [docs/reports/data-freshness-scorecard-2026-06-08.md:L17-L17]

### Open-item register

Every item below is assigned to the maintainer for issue tracking; issue-pending numbers refer to the accompanying issue drafts, pending creation and insertion of public issue numbers before clearance.

| Item | Gap / required follow-up | Tracking and evidence |
| --- | --- | --- |
| coverage-units | UNVERIFIED claim from section 2: establish a versioned workbook/PDF unit basis, averaging periods and coordinate reference conventions before engineering use; establish numeric separator locale as well as units | #720; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/excel_loader.py:L27-L58] |
| coverage-rules | UNVERIFIED claim from section 3: establish authority for geographic/production/date/identifier policies; add finite, zero and required-field tests; reconcile contract-round tokens and make identifier fallbacks explicit with warning-or-invalid fixtures | issue pending (1); [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L27-L63] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/validators.py:L408-L444] |
| coverage-live | Wire collection, reconcile CLI configuration/result keys and unread date filters, require persisted output before success/save messages, define analysis support and detect missing requested types | #720; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L110-L150] [src/worldenergydata/cli/commands/mexico_cnh.py:L202-L231] |
| coverage-scraper | Retain combined language/download preferences; remove download races and require well-specific navigation/export rather than returning a production file as well data; add browser fixtures | #431; #1282; #720; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L218-L236] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L655-L689] [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/scrapers/sih_scraper.py:L717-L749] |
| coverage-lifecycle | Align scraper constructor and cleanup calls; define the intended catch contract for browser versus structured errors | issue pending (2); [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/mexico_cnh_data.py:L162-L177] |
| coverage-packaging | Existing recursive Markdown package-data glob can include this pack in distributions; packaging exclusions are not changed here | issue pending (3); [packages/worldenergydata-mexico_cnh/pyproject.toml:L49-L55] |
| coverage-source | UNVERIFIED claim from section 9: establish current source revisions, availability, fingerprints and browser/driver compatibility; no network acquisition was performed | #720; [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/endpoints.py:L102-L112] |
| coverage-benchmark | Add independently sourced, versioned worked examples and file-loader fixtures; local regression examples establish neither regulatory validity nor source accuracy | issue pending (4); [tests/unit/mexico_cnh/test_validators.py:L461-L468] |
| coverage-evidence | Add locale-aware numeric fixtures, rejected-table counts and accented production/well header fixtures; retain missing detection coverage for SF2 and SF3; generate downstream QA evidence with source digests, units and dispositions | #1282; issue pending (4); [packages/worldenergydata-mexico_cnh/src/worldenergydata/mexico_cnh/data/loaders/pdf_parser.py:L222-L264] |
| coverage-map | Add section-3 method families to the implementation map; include the independent external CLI criterion and synthetic adapter as follow-up findings | issue pending (4); [src/worldenergydata/cli/commands/mexico_cnh.py:L517-L570] |
| coverage-review | UNVERIFIED claim from section 8: record the permanent data-pipeline reviewer and deputy assignment | issue pending (4) |
| coverage-docs | Reconcile full historical documents against present code instead of importing readiness counts; inspect the remaining non-module portions of discovered documents | issue pending (4); [docs/reports/data-freshness-scorecard-2026-06-08.md:L17-L17] |
| coverage-consumers | Review and run the wider common, CLI, unified production and adapter-registration domains separately; this pack's test counts cover the dedicated module suite only | issue pending (4); [tests/unit/common/test_exceptions.py:L314-L317] [tests/unit/fdas/adapters/test_registration_checklist.py:L68-L70] |

No client-derived dataset or private-sidecar value is included; the regression examples use the embedded inputs of their cited tests. [tests/unit/mexico_cnh/test_validators.py:L78-L85] [tests/unit/mexico_cnh/test_validators.py:L262-L265] [tests/unit/mexico_cnh/test_validators.py:L461-L468]
