# Spain module knowledge pack

| Header | Value |
| --- | --- |
| Module | `spain` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-spain/src/worldenergydata/spain` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` |
| Analysis family | EC; data pipeline, assessed with AQG r0 Python calculations |
| Quality role | Calculations quality manager; data-pipeline coverage |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

`parse_cores_frame` transforms wide monthly production into long rows; the live loader merges oil and gas and writes normalized CSVs. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L87-L113] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L91-L102] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L189-L193]

The reference chain connects a supplied adapter, FDAS production, sparse concept screening and monthly pre-tax cashflow; its outputs explicitly label screening as wiring only and economics as chain plumbing. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L36-L75]

The report builder reads normalized CSVs and metadata, evaluates only curated metadata entries with positive oil, and optionally writes HTML and JSON. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L73-L117] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L151-L175]

Scope includes the package's production, metadata mapping, reference chain and reports; scheduler and unified-adapter integration are dependencies described in section 9. [packages/worldenergydata-spain/src/worldenergydata/spain/production/__init__.py:L5-L25] [packages/worldenergydata-spain/src/worldenergydata/spain/field_concept.py:L19-L38] [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L36-L75] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/__init__.py:L3-L19]

UNVERIFIED: a routing maturity rating is unavailable because the routing registry is absent at the code pin; issue pending (1).

## 2. Inputs and outputs

### Inputs

| Name | Unit / range | Default | Source and evidence |
| --- | --- | --- | --- |
| `raw`, `product` | DataFrame; `oil` or `gas`; year/month plus production columns | Explicit product | `parse_cores_frame` rejects other products and missing columns. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L87-L113] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L127-L136] |
| Oil workbook values | metric tonnes; numeric non-null values; no nonnegative bound enforced | None | Coerced to numeric before multiplication. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L7-L15] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L151-L179] |
| Gas workbook values | GWh; numeric non-null values; no nonnegative bound enforced | None | Source contract and parser. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L42-L52] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L151-L179] |
| Year / month | Positive numeric year; English or Spanish month names mapped to 1–12 | Unknown months omitted | `_MONTHS`, `_monthly_rows`; integer cast occurs after filtering. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L41-L84] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L143-L148] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L167-L179] |
| `header_row`, `sheet_name` | Zero-based row index; worksheet name/index | Low-level loader: 5 and 0; live loader: 5 and `Production` | Constructor and Excel read. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L209-L240] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L60-L83] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L132-L137] |
| `oil_conversion_audit` | Accepted bbl/tonne factors or explicit defaults | Oil requires an audit | Missing audit raises `CoresParseError`; missing coverage raises instead of substituting silently. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L186-L198] |
| `allow_default_density` | Boolean | False | Strict coverage raises for missing factors; explicit true records defaulted fields. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L243-L279] |
| Density registry entry | API degrees and/or bbl/tonne; accepted factor 5.0–9.5 bbl/tonne | Caller registry or packaged JSON | Requires evidence fields, accepted source class and factor consistency. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L135-L191] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L194-L240] |
| `cache_root`, source HTTP boundary | Caller path; bytes plus headers/status | Standard-library HTTP; 60 s timeout | Downloads and metadata use caller storage. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L72-L84] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L147-L159] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L288-L295] |
| `field_meta` | `field_name` or `field`, optional `water_depth_m`, environment and source | Region `spain`, source `CORES`; onshore missing depth becomes 0.0 m | Sparse concept normalizer. [packages/worldenergydata-spain/src/worldenergydata/spain/field_concept.py:L19-L38] |
| Reference-chain prices | Oil USD/bbl; optional gas dictionary keyed YYYY-MM in USD/Mcf | Oil 75.0; gas None | Explicit signature and cashflow call. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L21-L35] [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L48-L63] |
| Report cache | CSV tables; scheduler metadata/manifest; workbook metadata; optional density audit | Explicit cache root | Required file reads and validations. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L73-L98] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L234-L273] |

### Outputs

| Name | Unit / representation | Range / convention and evidence |
| --- | --- | --- |
| Parser rows | `field_name`, integer `year`, `month`, `oil_bbl` or `gas_mcf` | Monthly rows only; totals and invalid values filtered; volumes multiplied by factors. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L143-L179] |
| Normalized cache | Oil, gas and all-product CSVs; density JSON | Sorted by field/year/month; outer merge on those keys; audit includes used/defaulted/missing lists. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L97-L102] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L151-L193] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L351-L352] |
| Source metadata | JSON, SHA-256, byte count, source URL, HTTP status, source unit and last-modified | Raw paths are relative to cache root; metadata carries refresh time. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L193-L203] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L250-L271] |
| Reference-chain dictionary | Production frames, concept/ranking, development system and pre-tax metrics in USD | Onshore sets `dry` and mismatch flag; missing depth classification also falls back to `dry`; empty production uses 1970-01-01 for first-oil date. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L65-L110] |
| Report summary / HTML / JSON | Monthly bbl/Mcf, totals, metadata, economics and caveats | HTML embeds escaped JSON; JSON refuses NaN. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L120-L148] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L189-L231] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L373-L383] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_html.py:L117-L123] |

Coordinates, origins and phase do not enter the parser's output schema; water depth is supplied in metres to the concept mapping, rather than derived from a coordinate frame. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L167-L179] [packages/worldenergydata-spain/src/worldenergydata/spain/field_concept.py:L19-L38]

## 3. Method and governing standards

| Method | Implementation and basis | Limits |
| --- | --- | --- |
| Filter → melt → convert | Positive-year/month-name filter, melt field columns, numeric coercion, multiplication. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L127-L198] | Unknown months, invalid years and nonnumeric values disappear; integer year cast does not validate integral input. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L143-L179] |
| Oil conversion | `oil_bbl = tonnes × audit factor`; `bbl_per_tonne_from_api` uses specific gravity `141.5 / (API + 131.5)` then reciprocal volume conversion. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L167-L198] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L45-L48] | Explicit fallback is `DEFAULT_OIL_BBL_PER_TONNE = 7.33`; strict coverage is default. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L13-L13] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L114-L124] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L243-L271] |
| Gas conversion | `gas_mcf = GWh × GWH_TO_MCF`, with code constant 3290.0 and an approximate heating-value comment. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L37-L39] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L186-L192] | UNVERIFIED: the gas heating-value assumption and API formula have not been checked against independent published references; issue pending (2). |
| Density evidence | Required provenance, source classes, boolean acceptance, positive/range checks and API-factor discrepancy ≤0.01 bbl/tonne. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L135-L191] | These are code acceptance rules, rather than independent verification of each cited physical measurement. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L135-L191] |
| Workbook acquisition | Link suffix discovery, HTTP/content-type checks, temporary-file replacement, SHA-256 recording. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L86-L114] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L225-L271] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L282-L295] | Nonempty bytes with an accepted content type pass download validation; this does not validate XLSX content. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L232-L246] |
| Economics and screening | Delegates normalization, recommendation and cashflow to downstream modules; optional gas deck is passed through. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L36-L75] | Labels explicitly restrict outputs to wiring and pre-tax plumbing; no national investment appraisal is asserted. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L65-L75] |
| Report audit | Validates counts, refresh metadata and density coverage; serializes evidence and caveats. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L234-L273] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L114-L124] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L268-L313] | Metadata SHA-256 is required as a field, without recomputing the raw workbook digest during report loading. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L256-L273] |

The module's cited calculation basis is its conversion comments and formulas; no governing standard edition or licensed clause is stated in those method definitions. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L32-L39] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L45-L48]

AQG r0, “Analysis QA gates”, revision 0, section 10 “Family mapping” supplies the Python calculations gate set used here; sections 4–9 define gates G0–G5. (AQG r0, sections 4–10.)

## 4. Validated worked examples

Evidence classification: 0 independently validated examples; the following 8 regression cases exercise synthetic data or repository expectations rather than an independently qualified physical benchmark. [tests/unit/spain/test_cores_loader.py:L159-L184] [tests/unit/spain/test_synthetic_gas_reference_chain.py:L24-L63] [tests/unit/spain/test_cores_field_development_report.py:L16-L31]

Execution record: all cases below PASS in both offline runs at the header pin; section 10 records the command and counts. This paragraph is the execution attestation; the row citations identify the input and assertion sources.

| Case | Source / input | Expected and tolerance basis | Existing test node ID | Last offline result |
| --- | --- | --- | --- | --- |
| R1 audited oil | Synthetic frame and injected factor | 10.0 tonnes × 6.95 bbl/tonne = 69.5 bbl; node uses `pytest.approx`; supplemental pack check ≤0.0001 bbl absolute error. [tests/unit/spain/test_cores_loader.py:L21-L47] [tests/unit/spain/test_cores_loader.py:L159-L184] | `tests/unit/spain/test_cores_loader.py::test_parse_oil_frame_uses_conversion_audit_factor` | PASS |
| R2 priced gas | Synthetic 1.0 and 2.0 GWh, 3.0 USD/Mcf | 29610.0 USD gross revenue from the retained conversion factor; exact equality in node; this checks revenue arithmetic, not the heating-value assumption. [tests/unit/spain/test_synthetic_gas_reference_chain.py:L24-L54] | `tests/unit/spain/test_synthetic_gas_reference_chain.py::test_synthetic_pure_gas_chain_uses_existing_volume_conversion` | PASS |
| R3 unpriced gas | Same synthetic loader, absent gas deck | 0.0 USD gross revenue, exact equality. [tests/unit/spain/test_synthetic_gas_reference_chain.py:L57-L63] | `tests/unit/spain/test_synthetic_gas_reference_chain.py::test_synthetic_pure_gas_chain_without_deck_retains_zero_revenue` | PASS |
| R4 sparse metadata | Synthetic onshore mapping input | 0.0 m water depth and region/source equality; exact assertions. [tests/unit/spain/test_reference_chain.py:L38-L52] | `tests/unit/spain/test_reference_chain.py::test_spain_field_meta_mapping_builds_sparse_onshore_concept` | PASS |
| R5 missing audit | Synthetic oil frame without audit | 1 `CoresParseError`, exact exception type and matching message. [tests/unit/spain/test_cores_loader.py:L113-L126] | `tests/unit/spain/test_cores_loader.py::test_parse_oil_frame_requires_conversion_audit` | PASS |
| R6 report counts | Synthetic four-row normalized cache | Metadata and manifest both 4 rows; 0-row count discrepancy. [tests/unit/spain/test_cores_field_development_report.py:L16-L31] | `tests/unit/spain/test_cores_field_development_report.py::test_load_report_source_validates_scheduler_cache_and_counts` | PASS |
| R7 JSON evidence | Sparse synthetic product cache; temporary HTML/JSON outputs | 0 NaN tokens; 2 JSON payloads parse with nonstandard constants rejected. [tests/unit/spain/test_cores_field_development_report.py:L201-L224] | `tests/unit/spain/test_cores_field_development_report.py::test_build_report_outputs_strict_json_for_sparse_product_rows` | PASS |
| R8 acquisition provenance | Injected HTTP responses and fixed clock | 2 raw byte streams match; 0 temporary files remain; oil SHA-256 exact and gas byte-count discrepancy 0 bytes. [tests/unit/spain/test_cores_live.py:L61-L93] | `tests/unit/spain/test_cores_live.py::test_download_all_writes_raw_files_atomically_and_records_metadata` | PASS |

## 5. QA gates

Gate applicability follows AQG r0, section 10 “Python calculations”; G5 applies to every family under section 9. (AQG r0, sections 9–10.)

| Gate | Applicability | Executable module check and evidence |
| --- | --- | --- |
| G0 | Applicable: inputs, units and citations | C0a–C0c below; parser, audit and report-input test assertions. [tests/unit/spain/test_cores_loader.py:L113-L126] [tests/unit/spain/test_cores_density.py:L55-L62] [tests/unit/spain/test_cores_field_development_report.py:L47-L56] |
| G1 | Applicable: Python imports and offline tests | C1 below; the target program route is Python/pytest importing the loaders, concept mapping, reference chain and report builder. [tests/unit/spain/test_cores_loader.py:L6-L18] [tests/unit/spain/test_reference_chain.py:L7-L12] [tests/unit/spain/test_cores_field_development_report.py:L16-L23] |
| G2 | Applicable: independent arithmetic check of the pipeline | C2a–C2b below; evaluate multiplication outside the called implementation; physical source qualification remains open in section 10. [tests/unit/spain/test_cores_loader.py:L159-L184] [tests/unit/spain/test_synthetic_gas_reference_chain.py:L38-L54] |
| G3 | NOT_APPLICABLE: no dynamic solver is launched by this reference chain | The chain fetches, normalizes, recommends and generates monthly cashflow. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L36-L75] |
| G4 | NOT_APPLICABLE: no diffraction or mesh analysis in the chain | The chain outputs production/concept/cashflow quantities. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L36-L75] |
| G5 | Applicable: report evidence | C5 below; strict JSON and source/count/density provenance; independent signature is a separate clearance step. [tests/unit/spain/test_cores_field_development_report.py:L176-L224] [tests/unit/spain/test_cores_field_development_density.py:L18-L34] |

Check definitions are acceptance instructions; the cited nodes specify the corresponding repository assertions.

| Check ID | Function / quantity | Numeric pass criterion and unit | Execution / evidence | Gate |
| --- | --- | --- | --- | --- |
| C0a | `parse_cores_frame` oil audit and invalid product | 1 expected exception per invalid call; 0 silently accepted invalid calls (count) | R5 and `test_parse_rejects_unknown_product`. [tests/unit/spain/test_cores_loader.py:L113-L126] [tests/unit/spain/test_cores_loader.py:L374-L378] | G0 |
| C0b | `load_crude_density_factors` required evidence and strict coverage | 1 expected rejection when `source_url` missing; 1 expected rejection for uncovered strict input (exceptions) | `test_density_registry_requires_citation_fields`, `test_oil_conversion_audit_strict_mode_names_missing_fields`. [tests/unit/spain/test_cores_density.py:L55-L62] [tests/unit/spain/test_cores_density.py:L710-L716] | G0 |
| C0c | `load_cores_report_source` metadata/manifest row counts | 0 rows difference on valid fixture; 1 exception on metadata count mismatch | R6 and `test_load_report_source_fails_on_row_count_mismatch`. [tests/unit/spain/test_cores_field_development_report.py:L16-L31] [tests/unit/spain/test_cores_field_development_report.py:L47-L56] | G0 |
| C1 | Python import and test route | 109 collected cases, 109 passes; 0 failures/skips/NOT_RUN (cases) in the selected module and integration scope | Command and per-file counts in section 10; example nodes R1–R8. [tests/unit/spain/test_cores_loader.py:L159-L184] [tests/unit/spain/test_cores_live.py:L61-L93] | G1 |
| C2a | `parse_cores_frame` oil result versus separate scalar multiplication | Absolute error ≤0.0001 bbl for 10.0 × 6.95; 0 row-count difference from 1 row | R1 plus supplemental arithmetic check; synthetic factor, not a physical benchmark. [tests/unit/spain/test_cores_loader.py:L21-L47] [tests/unit/spain/test_cores_loader.py:L159-L184] | G2 |
| C2b | `run_spain_reference_chain` gross gas revenue versus sum(volume × price) | Absolute error 0.0 USD for `(1.0 + 2.0) × 3290.0 × 3.0 = 29610.0`; absent deck gives 0.0 USD | R2/R3 plus supplemental arithmetic check; volume basis remains approximate. [tests/unit/spain/test_synthetic_gas_reference_chain.py:L24-L63] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L37-L39] | G2 |
| C5 | `build_report` and HTML serializer evidence | 2 parseable JSON documents, 0 NaN tokens, 4 rows in count evidence, 0 missing required provenance keys in test cache (count) | R6/R7; source/refresh/digest metadata and density audit assertions. [tests/unit/spain/test_cores_field_development_report.py:L16-L31] [tests/unit/spain/test_cores_field_development_report.py:L176-L224] [tests/unit/spain/test_cores_field_development_density.py:L18-L34] | G5 |

G5 report tests establish serialization/provenance behavior; they do not supply an independent signature or certify external workbook contents. [tests/unit/spain/test_cores_field_development_report.py:L176-L224] [tests/unit/spain/test_cores_live.py:L61-L93]

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection check | Incident or tracking reference; evidence |
| --- | --- | --- |
| Rows silently disappear when year/month/value coercion fails; positive fractional years are cast to integers | C0a covers invalid product/audit, but no detection check exists for rejected-row accounting or integral-year validation | Parser behavior in #763; issue pending (4). [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L143-L179] |
| No gas deck produces zero revenue; the report excludes gas-only economics even though the reference chain accepts a deck | C2b detects the zero/deck distinction; no detection check exists requiring report-level gas-deck support | #808; report selection and call omit `gas_prices`. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L21-L35] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L151-L175] [tests/unit/spain/test_synthetic_gas_reference_chain.py:L57-L63] |
| Strict live oil parsing blocks an uncovered density entry; explicit defaults are usable but approximate | C0b; `test_live_loader_default_registry_fails_closed_on_source_gaps`; `test_report_preserves_defaulted_density_limitations` | #807 records conversion work; independent source follow-up is issue pending (2). [tests/unit/spain/test_cores_live_density.py:L61-L72] [tests/unit/spain/test_cores_field_development_density.py:L37-L64] |
| Choosing the first worksheet reads a landing sheet; live loader explicitly selects `Production` | `test_loader_can_select_real_cores_production_sheet`, requiring 1 parsed row and correct converted volume | #806; header/sheet controls differ between low-level and live loaders. [tests/unit/spain/test_cores_loader.py:L323-L358] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L60-L83] |
| Unknown development-system classification falls back to `dry`; onshore estimates retain the mismatch flag | `test_reference_chain_forces_onshore_dry_system_and_mismatch_flag`, requiring host capex 0.0 USD and flag true; no independent suitability check exists | #763; do not use this path as a financial design reference. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L79-L92] [tests/unit/spain/test_reference_chain.py:L55-L72] |
| Cached source metadata can be reused without rehashing cached bytes; report validates digest presence rather than byte agreement | R8 checks a fresh fake download; no detection check exists for cache tampering or normalized/raw digest agreement | Issue pending (5). [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L147-L175] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L256-L273] |
| Historical adapter coverage/conversion expectations diverged | Integration test file is included in C1; require 8 cases passing | #983 is a closed historical incident; both fixture audit and live-density integration now have assertions. [tests/unit/production/unified/test_spain_cores_adapter_loader.py:L166-L272] |

Dates for the code observations are the pack revision date; issue histories are read-only context, and current code/test evidence governs the descriptions above.

## 7. Lessons log

| Date | Entry | Lesson | Evidence | Pack update | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Initial documentation | Distinguish a priced synthetic gas calculation from the report's deferred gas-only path | Reference chain accepts a gas deck, while the report's economics call does not pass one. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L21-L35] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L151-L175] | Sections 3–6 distinguish arithmetic evidence and report coverage | Pending; issue pending (1) |
| 2026-10-15 | Initial documentation | A recorded digest is insufficient to establish cache integrity | Existing cache metadata is returned without recomputation; report requires a nonempty digest field. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L161-L175] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L256-L273] | Sections 6 and 10 record the detection gap | Pending; issue pending (5) |

## 8. Ownership

Review role: calculations quality manager covering data pipelines; producing role: module contributor; escalation route: quality manager for engineering evidence and acceptance, maintainer for cross-family or publication decisions. (AQG r0, section 11 “Sign-off and independence”.)

UNVERIFIED: a named deputy and a durable pack-index/shared-log assignment have not been established from this repository; the maintainer should assign them before clearance; issue pending (1).

## 9. Dependencies and implementation inventory

| Dependency | Relationship and evidence |
| --- | --- |
| `worldenergydata-core`, `worldenergydata-fdas`, `worldenergydata-production`, pandas, openpyxl | Declared package requirements; Python ≥3.10. [packages/worldenergydata-spain/pyproject.toml:L10-L10] [packages/worldenergydata-spain/pyproject.toml:L25-L31] |
| FDAS production, concept normalizer, cashflow and assumption manager; field-development recommendation | Called by the reference chain or metadata mapping. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L36-L63] [packages/worldenergydata-spain/src/worldenergydata/spain/field_concept.py:L29-L38] |
| CORES oil and gas workbook datasets | Acquisition contract identifies source units and normalized columns; current public workbook content was not fetched for this pack. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L30-L53] |
| Unified production adapter | Reads injected loaders, merges separate products and maps standard columns. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L48-L103] |
| Scheduler refresh job | Adjacent tests exercise caller output, metadata, fixture controls and retry classification. [tests/unit/scheduler/test_spain_cores_refresh.py:L106-L135] [tests/unit/scheduler/test_spain_cores_refresh.py:L243-L284] [tests/unit/scheduler/test_spain_cores_refresh.py:L305-L341] |
| Report CLI | Delegates the caller's cache and output paths to `build_report`. [scripts/spain/build_cores_field_development_report.py:L15-L25] |

### Implementation-map audit

| Audit field | Recorded value |
| --- | --- |
| Map source | `digitalmodel`, `docs/registry/implementation-map.yaml`, schema 1 |
| Map ref pin | `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407` |
| Map data revision | `947fa50ff9a9e210de7e8f90e01b37add85c5954` |
| Package boundary | Header package; all its subpackages included |
| Families inspected / in-package rows | 13 / 0 |
| Module families / inventory rows | 0 / 0; empty inventory |
| Counted families / signal exclusions | 0 / 0 |
| Counted-family grep | NOT_APPLICABLE: no map implementation row lies in this package |
| Further second implementations in counted families | NOT_APPLICABLE: no counted families |
| Acceptance outcome | PASS for empty inventory; method families below remain map follow-up |

Map evidence: digitalmodel maintainers, “Implementation map”, schema 1, ref pin and data revision above, `families[].implementations[].path`; the audit compared every implementation path with the complete header package boundary.

### Repository-wide method discovery and map follow-up

Supplemental discovery searched repository Python files, including `scripts/`, for `parse_cores_frame`, `bbl_per_tonne_from_api`, `GWH_TO_MCF`, `3290.0`, `run_spain_reference_chain`, `_is_onshore`, `CoresLiveProductionLoader` and the report module reference; the implementations below distinguish independent calculations from helpers. This supplemental discovery does not alter the counted-family result.

| Method family / definitions | Classification and evidence |
| --- | --- |
| Monthly filter/melt/conversion: `parse_cores_frame`, `_monthly_rows`, `_melt_field_values`, `_parsed_output`, `_conversion_factor` | One composed implementation with local helpers. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L87-L113] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L143-L198] |
| API density conversion: `bbl_per_tonne_from_api`; validation and audit lookup | Formula implementation; `validate_crude_density_factor` calls it, and the audit lookup delegates factor selection. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L45-L48] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L114-L124] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L188-L191] |
| Onshore classification: `_is_onshore` in concept mapping and reference chain | Two local implementations of the same environment-membership criterion. [packages/worldenergydata-spain/src/worldenergydata/spain/field_concept.py:L51-L53] [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L88-L92] |
| Outer product merge: `CoresLiveProductionLoader.load_all_production`; adapter `_merge_product_frames` | Independent merge implementations inside and outside the package, respectively. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L97-L102] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L70-L83] |
| Unified row mapping: report `_to_unified`; adapter `_loader_to_standard_columns` | Separate implementations with different missing-value defaults; report fills missing quantities with zero, adapter retains unknown water/condensate as NaN. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L276-L297] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L85-L103] |
| HTTP discovery/cache, source metadata and report audit validation | Acquisition/criteria implementations in `CoresWorkbookSource`, `_validate_workbook_response`, `_workbook_metadata`, `_validated_oil_conversion_audit` and its coverage helpers; report factor validation delegates to the density dataclass. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L86-L114] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L147-L175] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L232-L271] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L114-L124] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L268-L313] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L368-L391] |
| Reference chain, report assembler, renderer, CLI and adapter fallback | Chain delegates cashflow/recommendation; report summarizes/exports; CLI wraps the report; embedded adapter fallback holds data/constants rather than calculating conversion from source tonnes. [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L36-L75] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L101-L148] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_html.py:L10-L45] [scripts/spain/build_cores_field_development_report.py:L15-L25] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L131-L184] |

Map follow-up: monthly production normalization, density conversion and acceptance, environment classification, product merging, schema mapping, source acquisition/cache integrity, reference-chain/report aggregation require source-repository-aware map rows before counted review can apply; issue pending (6). Existing rows from other repositories are not evidence that these methods are mapped here. (Implementation map, data revision above, `families[].implementations[].path`.)

## 10. Coverage and open items

### Coverage record

All 12 package Python files were read, including the empty package initializer; no subpackage is excluded from this pack. Package dependency/export evidence is in the following file inventory. [packages/worldenergydata-spain/pyproject.toml:L37-L49] [packages/worldenergydata-spain/src/worldenergydata/spain/production/__init__.py:L5-L25] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/__init__.py:L3-L19]

| Files read | Evidence anchor |
| --- | --- |
| `__init__.py` (empty), `field_concept.py`, `reference_chain.py` | Mapping and runner behavior. [packages/worldenergydata-spain/src/worldenergydata/spain/field_concept.py:L19-L53] [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L21-L110] |
| `production/__init__.py`, `cores_loader.py`, `cores_density.py`, `cores_live.py`, `cores_source.py` | Public exports, parser, density criteria, normalization and source metadata. [packages/worldenergydata-spain/src/worldenergydata/spain/production/__init__.py:L5-L25] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L87-L113] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L135-L191] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L112-L149] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L250-L271] |
| `reports/__init__.py`, `cores_field_development.py`, `cores_density_audit.py`, `cores_html.py` | Report exports, assembly, evidence validation and rendering. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/__init__.py:L3-L19] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L101-L148] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_density_audit.py:L114-L124] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_html.py:L10-L45] |
| Package README and packaging metadata | Workbook/report interfaces; the package-data patterns do not include `docs/agent-pack.md`. [packages/worldenergydata-spain/README.md:L13-L21] [packages/worldenergydata-spain/README.md:L50-L66] [packages/worldenergydata-spain/pyproject.toml:L42-L49] |
| Data records | Metadata and density-registry structures inspected; 1 discovery file with identifying name is omitted from this public inventory, issue pending (3). [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L74-L76] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L194-L240] |

Documentation discovered under `docs/` by the module-name search:

| Documentation | Relevance |
| --- | --- |
| `docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md` | Acquisition/layout history. [docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md:L41-L79] |
| `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` | Scheduler/fixture controls. [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L99-L144] |
| `docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md` | Report input/output and economic selection. [docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md:L161-L208] |
| `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md` | Density source acceptance and explicit defaults. [docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md:L124-L159] |
| `docs/plans/README.md` | Historical plan status index; not current acceptance evidence. [docs/plans/README.md:L95-L98] |
| `docs/modules/repository-architecture.md` | Scheduler and report routing entries. [docs/modules/repository-architecture.md:L106-L106] [docs/modules/repository-architecture.md:L220-L220] |
| `docs/domains/field-development/gas-revenue.md` | Current gas-price contract and sparse-model caveat. [docs/domains/field-development/gas-revenue.md:L3-L20] [docs/domains/field-development/gas-revenue.md:L31-L42] |

### Offline execution record

Code pin for both runs: `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746`; AFTER ran against the uncommitted documentation tree. The selected scope contains 86 module cases and 23 adjacent integration cases, rather than relying on an inventory estimate.

Command form used in both runs (the documented `--noconftest` form; source and sibling dependency directories supplied through `PYTHONPATH`; shared cache, coverage database and base temporary directory configured externally):

```bash
uv run --extra test python -m pytest --noconftest \
  tests/unit/spain \
  tests/unit/production/unified/test_spain_cores_adapter_loader.py \
  tests/unit/scheduler/test_spain_cores_refresh.py \
  -q -rA -p no:cacheprovider --basetemp="$TMPDIR/bt-<run>" \
  --cov-report= --cov-report=term
```

| Test file | BASE run/pass/fail/skip/NOT_RUN | AFTER run/pass/fail/skip/NOT_RUN |
| --- | --- | --- |
| `tests/unit/spain/test_cores_density.py` | 24 / 24 / 0 / 0 / 0 | 24 / 24 / 0 / 0 / 0 |
| `tests/unit/spain/test_cores_field_development_density.py` | 19 / 19 / 0 / 0 / 0 | 19 / 19 / 0 / 0 / 0 |
| `tests/unit/spain/test_cores_field_development_report.py` | 13 / 13 / 0 / 0 / 0 | 13 / 13 / 0 / 0 / 0 |
| `tests/unit/spain/test_cores_live.py` | 5 / 5 / 0 / 0 / 0 | 5 / 5 / 0 / 0 / 0 |
| `tests/unit/spain/test_cores_live_density.py` | 8 / 8 / 0 / 0 / 0 | 8 / 8 / 0 / 0 / 0 |
| `tests/unit/spain/test_cores_loader.py` | 12 / 12 / 0 / 0 / 0 | 12 / 12 / 0 / 0 / 0 |
| `tests/unit/spain/test_reference_chain.py` | 3 / 3 / 0 / 0 / 0 | 3 / 3 / 0 / 0 / 0 |
| `tests/unit/spain/test_synthetic_gas_reference_chain.py` | 2 / 2 / 0 / 0 / 0 | 2 / 2 / 0 / 0 / 0 |
| `tests/unit/production/unified/test_spain_cores_adapter_loader.py` | 8 / 8 / 0 / 0 / 0 | 8 / 8 / 0 / 0 / 0 |
| `tests/unit/scheduler/test_spain_cores_refresh.py` | 15 / 15 / 0 / 0 / 0 | 15 / 15 / 0 / 0 / 0 |
| Total | 109 / 109 / 0 / 0 / 0 | 109 / 109 / 0 / 0 / 0 |

The table is the execution attestation, not a claim that code citations alone prove a test run. Supplemental C2a/C2b scalar checks passed; synthetic characterization reproduced the input and digest limitations in section 6. Reference-source qualification, live refresh and independent clearance were not performed.

### Open items

| ID | Item / evidence | Responsible role | Tracking |
| --- | --- | --- | --- |
| U1 | Routing maturity remains unverified because no routing registry exists at the pin; use the existing pack-index surface rather than adding a new registry | Maintainer | issue pending (1) |
| U2 | Independent physical references and validated benchmark missing; API formula and approximate gas heating-value basis require qualification, as do source terms and accepted density measurements. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L32-L39] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L45-L48] | Calculations quality manager | issue pending (2) |
| U3 | Deputy, durable index/shared-log assignment and independent gate clearance remain unverified; no signed production QA appendix is claimed | Maintainer | issue pending (1) |
| O1 | Codenaming needed for 1 discovery file with identifying name and identifying labels in code/test data; no such names are reproduced in this pack. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L74-L76] | Maintainer | issue pending (3) |
| O2 | Rejected-row counts, fractional years and negative input policy lack explicit validation/accounting; synthetic characterization recorded truncation, omission and retained negative gas. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_loader.py:L143-L179] | Module contributor | issue pending (4) |
| O3 | Cache bytes are not rehashed on reuse; report accepts nonempty invalid digest markers and does not recompute normalized/raw agreement. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_source.py:L147-L175] [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L256-L273] | Module contributor | issue pending (5) |
| O4 | Add section-3 method families and independent/wrapper classifications to the implementation map with owning-repository identity | Maintainer | issue pending (6) |
| O5 | Report-level gas-deck support and broader curated field metadata remain incomplete; onshore economics remain plumbing only. [packages/worldenergydata-spain/src/worldenergydata/spain/reports/cores_field_development.py:L139-L175] [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L65-L75] | Module contributor | #808 and #763 |
| O6 | Current live materialization, source freshness and readiness badges are outside this offline evidence; no current production-data coverage is claimed. [docs/modules/repository-architecture.md:L100-L109] | Maintainer | #917 and #918 |

No new standards-derived constant or formula is introduced by this documentation; the current density audit records source metadata, while independent method/source qualification is U2. [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_density.py:L51-L68] [packages/worldenergydata-spain/src/worldenergydata/spain/production/cores_live.py:L164-L181]
