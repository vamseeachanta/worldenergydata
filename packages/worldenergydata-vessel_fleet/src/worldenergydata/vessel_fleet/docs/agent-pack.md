# vessel_fleet knowledge pack

| Header | Value |
| --- | --- |
| Module | `vessel_fleet` |
| Repository | `worldenergydata` |
| Module path | `packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet` |
| Pack revision | 2 |
| Code revision | `a8b26875c1d94a138456fbd885043f43307b73b3` |
| Analysis family | EC; data pipeline; use the Python calculations gate set |
| Quality manager role | Calculations quality manager (proposed coverage) |
| Status | DRAFT; independent review pending |

## 1. Purpose and scope

The public API exposes construction-vessel and drilling-riser loaders, domain entries and schemas; the router additionally queries drilling-rig and construction datasets. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/__init__.py:L3-L45] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/router.py:L21-L115]

This revision documents the main path: configured collection, text parsing, schema validation, identity-based record fusion, Parquet/CSV storage and capability queries; the component-CSV preflight is included. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/fleet_page_collector.py:L48-L114] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L10-L20] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L85-L139] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/parquet.py:L25-L61] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L82-L111]

Treat query results as inventory screening: the selection function filters recorded fields, and the legacy bridge drops columns outside its compatibility list. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/selection.py:L90-L129] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/bridge/rig_fleet_bridge.py:L20-L45] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/bridge/rig_fleet_bridge.py:L66-L83]

Distribution metadata declares Alpha; no routing-registry maturity is substituted for that declaration. [packages/worldenergydata-vessel_fleet/pyproject.toml:L16-L24]

## 2. Inputs and outputs

### Inputs

| Name / format | Unit | Allowed range / missing policy | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| `VESSEL_NAME`, schema row | text | Required string; surrounding quotes and whitespace stripped | Required | Tabular headers; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L13-L20] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L63-L68] |
| `IMO_NUMBER`, `MMSI`, provenance fields | text | IMO, when supplied, exactly 7 digits; this is a format check | `None` | Upstream record; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L23-L41] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L165-L170] |
| `LOA_M`, `BEAM_M`, `DEPTH_M`, `DRAFT_M` | m | Non-negative when supplied; blank becomes `None` | `None` | Schema record; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L43-L51] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L106-L142] |
| `DISPLACEMENT_TONNES`, `DEADWEIGHT_TONNES`; `TRANSIT_SPEED_KNOTS` | tonnes; knots | Non-negative when supplied | `None` | Schema record; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L48-L51] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L128-L142] |
| `YEAR_BUILT`; `DP_CLASS`, `QUARTERS_CAPACITY` | year; integer class/count | Year 1900–2035; integer coercion truncates floats; no DP upper bound in this base validator | `None` | Schema record; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L144-L163] |
| Rig depth ratings; equipment ratings | ft; kips, hp, in, psi; `ST` interpretation open (U1) | Numeric fields listed by rig validator reject negatives | `None` | Rig schema; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_rig.py:L25-L55] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_rig.py:L178-L217] |
| Construction capacities and geometry | tonnes, m, m², in, MW according to field suffix | Listed numeric fields reject negatives | `None` | Construction schema; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/construction_vessel.py:L19-L82] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/construction_vessel.py:L151-L180] |
| Component CSV | OD/ID/wall in in; length in ft; weights in kips; pressure in psi | Required columns plus nonblank `DATA_SOURCE` and `NOTES`; every nonempty physical record has header width | Packaged curated CSV | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_riser.py:L10-L37] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L23-L35] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L46-L68] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L96-L108] |
| HTML and PDF text | Source text, no automatic common unit system | Configured field mapping; mapped names required; blank PDF text yields no record | Selectors/mapping optional | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/fleet_page_collector.py:L23-L35] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/fleet_page_collector.py:L75-L114] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/spec_pdf_collector.py:L89-L108] |
| HTTP collector configuration | requests/s; s | Rate limiting disabled when rate ≤ 0 | Rate 1.0, retries 3, timeout 30 s, cache TTL 3600 s | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/base.py:L33-L54] |

Schema coercion and semantic validation are separate stages: the rig validator reports errors for depth outside 0–40000 ft and year above 2030, whereas the base schema accepts years through 2035. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/validator.py:L45-L57] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L158-L163]

UNVERIFIED: U1 — coordinate frame, VCG origin, sign conventions and interpretation of `ST` fields for downstream engineering use are not established by the inspected field declarations; resolve before treating these fields as a loading-condition definition (issue [#1050](https://github.com/vamseeachanta/worldenergydata/issues/1050)). [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_rig.py:L66-L78]

### Outputs

| Name / format | Unit | Range / missing policy | Default | Evidence |
| --- | --- | --- | --- | --- |
| Parquet rows / CSV export | Units inherited from record fields | Empty input writes an empty DataFrame; missing Parquet returns `[]`; no schema model is invoked in `save` | Explicit storage directory / filenames | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/parquet.py:L21-L61] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/parquet.py:L63-L76] |
| Standalone CSV export | Units inherited from fields | Empty list writes empty text; headers come from first record | Explicit output path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/csv.py:L13-L32] |
| `FleetRouter` query lists and counts | records | Type/status equality, case-insensitive substring matching on the `OWNER` field, inclusive minimum ratings | Packaged curated Parquet, lazy cached | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/router.py:L18-L45] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/router.py:L47-L115] |
| Component query DataFrame | in, psi | OD comparison is absolute difference ≤ tolerance; default 0.1 in | Packaged curated CSV; lazy cached | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L157-L176] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L178-L212] |
| Legacy rig inventory DataFrame | Original field units | Missing legacy columns filled; absent/blank rig identity dropped; extra columns discarded | Explicit DataFrame or path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/bridge/rig_fleet_bridge.py:L48-L83] |
| Completeness report | Fraction (dimensionless), record count | Empty list has count 0 and average 0; nonempty aggregate fractions rounded to 4 places | Drilling core-field set | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/completeness.py:L52-L88] |
| Conflict report | Identifiers and source tags, no physical unit | Retained IMO and discarded alternatives reported by the reporting variant | Explicit input record list | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L67-L83] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L173-L199] |

## 3. Method and governing standards

| Method | Implementation and contract |
| --- | --- |
| Text parsing | `parse_numeric` strips a unit suffix, comparison symbols, trailing plus and commas, then parses a float; unparseable strings become `None`; stripping a unit does not convert it. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/numeric.py:L68-L105] |
| HTML extraction | Table rows are retained only when cell count equals header count; definition lists and two-column tables provide key/value extraction. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/html.py:L61-L83] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/html.py:L88-L118] |
| PDF extraction | Optional `pdfplumber` supplies page text/tables; missing dependency raises `ImportError`; key/value splitting uses the first separator. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/pdf.py:L9-L26] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/pdf.py:L54-L74] |
| Name normalization | Uppercase, one matching prefix removed, punctuation replaced, whitespace collapsed; empty input becomes empty key. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/normalizer.py:L33-L56] |
| Curated fusion | Group by IMO, otherwise normalized name; retain orphans; reconcile same-name IMO conflicts; merge fields in ascending source priority, overwriting only with non-`None` values. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L85-L139] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L173-L199] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L221-L245] Curated drilling/construction Parquet and CSV outputs use this route. [scripts/vessel_fleet/fuse_and_deduplicate.py:L59-L65] [scripts/vessel_fleet/fuse_and_deduplicate.py:L88-L101] |
| Catalog identity resolution | `resolve_identities` uses union-find: exact IMO, then canonical name with operator compatibility, then alternate names with operator compatibility. `dedupe_catalog` collapses clusters for catalog class counts and the identity crosswalk; intervention activity matching reuses `canonicalize_name`. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L211-L282] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L348-L365] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/fleet_catalog.py:L353-L365] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_crosswalk.py:L191-L193] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/rlwi_war_coverage.py:L107-L111] |
| Source precedence | Source priorities are explicit constants; unknown tags use priority 0; stable sorting means later equal-priority non-`None` fields win. The top-level population-based docstring conflicts with this implementation (issue pending (2)). [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L12-L46] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L52-L55] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L230-L245] |
| Completeness | `filled / len(core_fields)`, counting values other than `None`; empty core set returns 0; zero and empty strings count as present. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/completeness.py:L38-L49] [tests/unit/vessel_fleet/quality/test_completeness.py:L28-L41] |
| Mixed units | Shared conversion uses `FT_TO_M = 0.3048` and its reciprocal; record field suffixes retain mixed units rather than enforce one universal file-unit system. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/constants.py:L119-L120] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_rig.py:L25-L55] |
| Component preflight | Read one UTF-8-with-BOM-compatible snapshot; validate strict CSV widths, required columns and provenance before caching the parsed frame. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L46-L68] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L96-L111] |

UNVERIFIED: U2 — a governing engineering standard and edition for the complete module have not been established; the inspected main path implements data-handling policies, and the remaining source/document audit is open (issue pending (1)). [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/validator.py:L25-L64] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L221-L245]

No standards-derived design check is claimed for these methods; the calculation-citation sidecar requirement is conditional on introducing a standards-derived constant or formula, and that applicability assessment remains within U2 (issue pending (1)). [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/completeness.py:L38-L49]

## 4. Validated worked examples

UNVERIFIED: U3 — independently sourced physical-data validation has not been established; the cases below are regression examples and do not qualify a hull, loading condition or capability for analysis (issue [#1050](https://github.com/vamseeachanta/worldenergydata/issues/1050)). [tests/unit/vessel_fleet/test_selection.py:L8-L25] [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L25-L48]

Validated examples: 0; regression examples: 6 in this revision, with expected values from existing test fixtures/assertions rather than an independently versioned benchmark. [tests/unit/vessel_fleet/quality/test_completeness.py:L20-L30] [tests/unit/vessel_fleet/storage/test_parquet.py:L54-L62] [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L41-L48] [tests/unit/vessel_fleet/test_selection.py:L41-L44] [tests/unit/vessel_fleet/test_dedup_deduplicator.py:L46-L51]

| Case | Input / source | Expected value, tolerance and basis | Existing test node ID | Offline result at code revision |
| --- | --- | --- | --- | --- |
| R1 partial completeness | Inline synthetic fields; no input file | 2/3 fraction; `pytest.approx`, no explicit tolerance in test | `tests/unit/vessel_fleet/quality/test_completeness.py::TestCompletenessScore::test_partial_fields` | PASS at BASE and AFTER. [tests/unit/vessel_fleet/quality/test_completeness.py:L20-L22] |
| R2 empty core | Inline synthetic record, empty field tuple | 0.0 fraction; exact equality, implementation contract | `tests/unit/vessel_fleet/quality/test_completeness.py::TestCompletenessScore::test_empty_core_fields` | PASS at BASE and AFTER. [tests/unit/vessel_fleet/quality/test_completeness.py:L28-L30] |
| R3 nullable storage | Temporary synthetic Parquet | 2 fields remain `None`; exact identity checks | `tests/unit/vessel_fleet/storage/test_parquet.py::TestParquetRoundTrip::test_preserves_none_values` | PASS at BASE and AFTER. [tests/unit/vessel_fleet/storage/test_parquet.py:L54-L62] |
| R4 canonical component shape | Packaged `drilling_riser_components.csv` | 36 unique IDs; 31 fields per row; pinned text digest; zero deviations | `tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py::test_canonical_width_and_text_preservation` | PASS at BASE and AFTER. [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L25-L48] |
| R5 unknown is unqualified | Packaged spec Parquet, hookload minimum 1 kip | 0 null hookloads in selected records; exact assertion | `tests/unit/vessel_fleet/test_selection.py::TestFilterRigs::test_missing_field_is_not_qualified` | PASS at BASE and AFTER. [tests/unit/vessel_fleet/test_selection.py:L41-L44] |
| R6 priority merge | Inline synthetic low/high-priority records | 2 asserted fields equal high-priority values; exact assertions | `tests/unit/vessel_fleet/test_dedup_deduplicator.py::TestMergeRecords::test_higher_priority_wins` | PASS at BASE and AFTER. [tests/unit/vessel_fleet/test_dedup_deduplicator.py:L46-L51] |

## 5. QA gates

Gate allocation for this pack: Python calculations G0, G1, G2 and G5 applicable; G3 and G4 NOT_APPLICABLE because this pack covers a data pipeline rather than a dynamics or diffraction computation (AQG r0, sections 10–11). [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/router.py:L47-L115]

The following are pack acceptance criteria, not claims of automatic gate enforcement; retain logs, code revision and input fingerprints with their results (AQG r0, sections 2 and 13).

| Check | Gate / status | Executable detection | Numeric pass criterion and unit | Evidence |
| --- | --- | --- | --- | --- |
| C01 | G0 applicable | Run alignment tests, including malformed widths, missing required columns and provenance | 0 failed assertions; canonical 31 fields/row, 36 unique component IDs | [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L41-L60] [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L84-L119] [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L296-L320] |
| C02 | G0 applicable | Run base-schema and cross-field validation suites; inspect unit declarations | 0 failed assertions; 0 undocumented unit substitutions in the reviewed tables | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L128-L170] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/validator.py:L45-L62] |
| C03 | G0 applicable | Run priority, conflict-reconciliation and missing-field selection tests | 0 failed assertions; 0 null hookloads returned by the R5 case | [tests/unit/vessel_fleet/test_dedup_deduplicator.py:L46-L58] [tests/unit/vessel_fleet/test_dedup_deduplicator.py:L174-L236] [tests/unit/vessel_fleet/test_selection.py:L41-L44] |
| C04 | G1 applicable | Run all module tests plus the 2 discovered consumer test files in the same environment before and after the text change | 0 failures and 0 collection errors; 0 changed per-node outcomes | [pyproject.toml:L334-L353] [tests/unit/vessel_fleet/storage/test_parquet.py:L29-L62] |
| C05 | G0 applicable | Resolve all pack citations at the code pin; confirm the source solver-reference inventory in section 9 by text search | 0 unresolved citations; exactly 1 source occurrence of `OrcaFlex` | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L162-L170] |
| C06 | G2 applicable | Hand-count populated cells for R1 and R2, then compare against the callable result without reading its output as the oracle | Absolute error ≤ 1e-12 fraction for 2/3 and 0; 2 cases | [tests/unit/vessel_fleet/quality/test_completeness.py:L20-L30] |
| — | G3 NOT_APPLICABLE | No dynamics result is produced by the reviewed router/storage path | Reason: inventory queries and serialization | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/router.py:L47-L115] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/parquet.py:L25-L61] |
| — | G4 NOT_APPLICABLE | No diffraction result is produced by the reviewed router/storage path | Reason: no mesh or hydrostatics calculation in that path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/router.py:L47-L115] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/parquet.py:L25-L61] |
| C07 | G5 applicable | Retain `fleet_completeness_report` and `deduplicate_fleet_with_report` records in the QA appendix; map section-4 nodes to before/after records | 6/6 cases mapped; 0 missing output-report rows (count); 0 missing outcomes; 0 unreported skipped cases | [tests/unit/vessel_fleet/quality/test_completeness.py:L20-L30] [tests/unit/vessel_fleet/storage/test_parquet.py:L54-L62] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/completeness.py:L52-L88] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L67-L83] |
| C08 | G5 applicable | Verify header, sections, issue/draft references and neutral public wording before review | 10/10 sections; 0 untracked open items; 0 prohibited identifiers | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/__init__.py:L1-L45] |

C06 offline result: PASS for both arithmetic cases; maximum absolute error 0.0 fraction. This checks the metric calculation only. [tests/unit/vessel_fleet/quality/test_completeness.py:L20-L30]

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection / disposition | Incident and evidence |
| --- | --- | --- |
| Missing Parquet or construction data looks like an empty result; loaders cache that result | C04: missing-file tests; require explicit dataset-presence evidence before interpreting zero inventory | Missing-data policy, not a confirmed incident; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/parquet.py:L46-L58] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/construction_vessel_loader.py:L53-L65] |
| PDF exceptions are logged per record and collection continues with a partial result | C04 exercises offline module tests; no detection check exists for complete live-source acquisition; reconcile requested versus collected records before reuse | issue [#1102](https://github.com/vamseeachanta/worldenergydata/issues/1102); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/spec_pdf_collector.py:L56-L69] |
| Numeric parsing removes comparison qualifiers and unit suffixes | C02: keep source text and explicit units when qualifying upstream data; parser tests establish string handling, not source equivalence | Coverage gap, issue pending (1); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/numeric.py:L80-L105] |
| Shifted component columns silently corrupt provenance | C01: strict widths before pandas, required provenance, semantic anchors; issue remains open; detection coverage exists at the pin, but closure and remaining source-data remediation are not established | issue [#1046](https://github.com/vamseeachanta/worldenergydata/issues/1046); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L96-L108] [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L41-L60] [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L210-L246] |
| Population-first prose contradicts source-priority implementation | C03 tests priority behavior; no detection check exists for docstring/implementation consistency; correct prose separately | issue pending (2); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L52-L55] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L221-L245] |
| Equal-priority tie test accepts either value despite its test name | C03; no detection check exists for stable-order tie precedence in that assertion; add an exact oracle separately | issue pending (2); [tests/unit/vessel_fleet/test_dedup_deduplicator.py:L67-L72] |
| Schema and cross-field validator accept different year ranges | C02 runs both; choose and record the applicable validation stage instead of assuming their contracts coincide | issue pending (3); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L158-L163] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/validator.py:L52-L57] |
| Global class counts can be mistaken for regional available supply | C04 catalog regressions; preserve the emitted scope and snapshot caveats | issue [#591](https://github.com/vamseeachanta/worldenergydata/issues/591); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/fleet_catalog.py:L393-L424] |
| Two in-module dedup routes with different identity keys | C04 runs each route's regressions; no detection check exists comparing both on one fixture corpus. Add a differential check: distinct-record counts equal, or every count difference explained; catalog class counts use the resolver | issue pending (4); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L247-L282] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/fleet_catalog.py:L353-L365] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L85-L139] |
| Alternate identity normalization strips former-name parentheticals but does not share the dedup normalizer | No detection check exists for cross-path equivalence; compare matched keys before merging; issue pending (4) | [scripts/vessel_fleet/ingest_contractor_spec_pdfs.py:L119-L126] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/normalizer.py:L33-L56] |
| Direct curated enrichment overwrites present fields outside source-priority fusion | No detection check exists for precedence equivalence; retain before/after field provenance; issue pending (4) | [scripts/vessel_fleet/ingest_contractor_spec_pdfs.py:L174-L210] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L221-L245] |

## 7. Lessons log

Append future entries as date, evidence reference, lesson, pack change and shared-log reference; do not insert private record identities.

| Date | Evidence reference | Lesson | Pack change | Shared-log reference |
| --- | --- | --- | --- | --- |
| 2026-10-15 | issue [#1046](https://github.com/vamseeachanta/worldenergydata/issues/1046) | Require CSV width and semantic checks before counting components | Sections 2, 4–6 include C01 and R4 | Pending; issue pending (1). [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L41-L60] |
| 2026-10-15 | issue pending (2) | Source precedence must be read from implementation and assertions rather than population-based prose | Sections 3 and 6 distinguish the contracts | Pending; issue pending (1). [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L52-L55] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L230-L245] |

## 8. Ownership

Proposed review responsibility: calculations quality manager for G0–G2 and G5; escalate ambiguous units, source identity and acceptance criteria to that role, with cross-family questions for the maintainer (AQG r0, sections 10–11).

UNVERIFIED: U4 — deputy quality-manager assignment, permanent data-pipeline review responsibility and shared-log destination remain to be recorded (issue pending (1)).

## 9. Dependencies

The package declares the shared core, pandas, Pydantic, pyarrow, openpyxl and requests; HTML/PDF helpers additionally use optional BeautifulSoup and pdfplumber imports. [packages/worldenergydata-vessel_fleet/pyproject.toml:L32-L39] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/html.py:L11-L15] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/pdf.py:L9-L18]

The legacy bridge produces the BSEE-compatible column set, while selection loads packaged `raw/spec_pdf_dimensions` Parquet files and fails when no files are found. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/bridge/rig_fleet_bridge.py:L20-L45] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/selection.py:L77-L87]

| Solver-name occurrence in source | Dependency interpretation |
| --- | --- |
| `OrcaFlex` in `DrillingRiserLoader.filter_by_size` docstring, line 165 | Describes possible converted OD input; the method reads a DataFrame and compares OD numerically; no solver version is specified there. Text inspected only. [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L157-L176] |

The associated offline regression also names that conversion in its test name and docstring; it supplies numeric OD values to the loader. [tests/unit/vessel_fleet/loaders/test_drilling_riser_loader.py:L179-L187]

### Parallel implementations and consumers

Coverage note (U5): the implementation map on `codex/implmap-work`, file commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, names data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`. Its 13 families contain 0 implementation rows inside the header package path. The module's map-family inventory is therefore empty (0 families, 0 rows); the counted-family grep is NOT_APPLICABLE because no map family has an in-package implementation. The repository-local inventory below records parallel routes and consumers separately; it does not assert equivalence.

Map follow-up: the uncovered method families are collection, numeric/HTML/PDF parsing, name normalization, schema/semantic validation, identity resolution and record fusion, source precedence and direct enrichment, completeness, unit conversion, component preflight, storage/export and inventory querying/aggregation (section 3 and the table below). These families are not counted until a map revision includes in-package rows. Differential checks within this repository remain open under U5, issue pending (4).

| Implementation / symbol and line | Method and relation | Key-control agreement | Covering pack / evidence |
| --- | --- | --- | --- |
| `identity_resolver.canonicalize_name`, line 58 | Parallel in-module name normalizer used by resolver clusters and intervention activity matching | No: strips trailing parentheticals and rejoins short alpha/numeric hull tokens in addition to prefix/punctuation handling | This pack, sections 3 and 6; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L58-L96] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/rlwi_war_coverage.py:L107-L111] |
| `identity_resolver.resolve_identities`, line 211 | Parallel in-module identity implementation feeding catalog counts and crosswalk clusters | No: exact IMO, canonical name plus operator compatibility, then alternate names plus operator compatibility | This pack, section 3; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L211-L282] |
| `identity_resolver.dedupe_catalog`, line 348 | In-module collapse/report helper for the parallel resolver route | Delegates clustering to `resolve_identities`; first nonempty scalar wins, unlike source-priority fusion | This pack, section 3; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L348-L382] |
| `fleet_catalog.build_fleet_catalog`, lines 353–365 | In-module consumer of the parallel resolver route; emits distinct class counts | Uses `dedupe_catalog`, replacing additive raw counts with distinct-record counts | This pack, section 6; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/fleet_catalog.py:L353-L365] |
| `identity_crosswalk.build_identity_crosswalk`, line 180 | In-module consumer of the parallel resolver route; emits aggregate identity crosswalk | Uses both `dedupe_catalog` and `resolve_identities`; no independent clustering algorithm | This pack; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_crosswalk.py:L180-L210] |
| Intervention `_vessel_key`, line 107 | External consumer of `identity_resolver.canonicalize_name` for activity matching | Uses IMO when present, otherwise canonical name; no operator compatibility test in this key | None; [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/rlwi_war_coverage.py:L28-L30] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/rlwi_war_coverage.py:L107-L111] |
| `BaseVesselEntry.vessel_key` / `normalised_name`, lines 65–78 | Parallel in-module name normalizers for domain entries | No: key lowercases and replaces spaces with underscores; display normalization uses its own prefix list, preserving punctuation | This pack; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/base.py:L13-L20] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/base.py:L65-L78] |
| Marine-safety `_normalize_vessel_name`, line 550 | Parallel external name normalizer used by name-similarity scoring | Equivalence not established: independent prefix list, punctuation removal and whitespace collapse | None; [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L403-L405] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L550-L611] |
| BSEE `RigFleetLoader.build_fleet_from_war`, line 90 | Legacy independent unique-rig aggregation; filters non-rig operations | Yes for non-rig filter only; other controls not checked | None; [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/loaders/rig_fleet/rig_fleet_loader.py:L90-L165] |
| BSEE `RigFleetSchema`, line 14 | Legacy independent record schema | Not checked | None; [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/schemas/rig_fleet.py:L14-L45] |
| BSEE router, line 14 | Legacy query interface | Not checked | None; [packages/worldenergydata-bsee/src/worldenergydata/bsee/data/loaders/rig_fleet/router.py:L14-L46] |
| `_match_key`, line 119 | Parallel normalization; not a byte-identical copy | No: parenthetical removal differs | This pack, section 6; [scripts/vessel_fleet/ingest_contractor_spec_pdfs.py:L119-L126] |
| `apply_to_curated`, line 174 | Parallel enrichment; not a byte-identical copy | No: direct overwrite bypasses source priorities | This pack, section 6; [scripts/vessel_fleet/ingest_contractor_spec_pdfs.py:L174-L210] |
| WAR builder script, line 84 | Caller of legacy loader | Not checked | None; [scripts/build_rig_fleet_from_war.py:L23-L24] [scripts/build_rig_fleet_from_war.py:L80-L90] |
| WAR exporter, line 43 | Parallel non-rig filtering | Yes for filter only | This pack; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/exporters/war_export.py:L38-L60] |
| `scripts/vessel_fleet/build_expanded_rig_fleet.py` · `main`, line 71 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/build_expanded_rig_fleet.py:L71-L159] |
| `scripts/vessel_fleet/build_rig_selector.py` · `build`, line 56 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/build_rig_selector.py:L56-L85] |
| `scripts/vessel_fleet/collect_construction_fleet.py` · `main`, line 59 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/collect_construction_fleet.py:L59-L83] |
| `scripts/vessel_fleet/collect_drilling_fleet.py` · `main`, line 189 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/collect_drilling_fleet.py:L189-L231] |
| `scripts/vessel_fleet/collect_from_scrape.py` · `main`, line 44 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/collect_from_scrape.py:L44-L65] |
| `scripts/vessel_fleet/enrich_from_government.py` · `main`, line 28 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/enrich_from_government.py:L28-L72] |
| `scripts/vessel_fleet/enrich_from_registries.py` · `main`, line 28 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/enrich_from_registries.py:L28-L101] |
| `scripts/vessel_fleet/export_fleet.py` · `main`, line 24 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/export_fleet.py:L24-L41] |
| `scripts/vessel_fleet/export_war_to_vessel_fleet.py` · `main`, line 74 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/export_war_to_vessel_fleet.py:L74-L116] |
| `scripts/vessel_fleet/fuse_and_deduplicate.py` · `main`, line 30 | Consumer of the curated deduplicator route; writes curated Parquet/CSV | Uses IMO-first fusion, otherwise normalized name; independent of resolver operator/alternate-name rules | This pack, section 3; [scripts/vessel_fleet/fuse_and_deduplicate.py:L59-L65] [scripts/vessel_fleet/fuse_and_deduplicate.py:L88-L101] |
| `scripts/vessel_fleet/ingest_contractor_spec_pdfs.py` · `main`, line 294 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/ingest_contractor_spec_pdfs.py:L294-L326] |
| `scripts/vessel_fleet/ingest_myshiptracking.py` · `main`, line 64 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/ingest_myshiptracking.py:L64-L138] |
| Operator-specific PDF ingestion script (1 file) | Pipeline consumer; named source identity withheld, sidecar entry: to be created (issue pending (1)) | Not checked | None; [scripts/vessel_fleet/] |
| `scripts/vessel_fleet/ingest_offrepo_construction_vessels.py` · `main`, line 71 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/ingest_offrepo_construction_vessels.py:L71-L172] |
| `scripts/vessel_fleet/ingest_xls_historical.py` · `main`, line 35 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/ingest_xls_historical.py:L35-L61] |
| `scripts/vessel_fleet/populate_hull_forms.py` · `main`, line 34 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/populate_hull_forms.py:L34-L69] |
| `scripts/vessel_fleet/run_full_pipeline.py` · `main`, line 48 | Pipeline consumer / orchestration | Not checked | None; [scripts/vessel_fleet/run_full_pipeline.py:L48-L86] |

Downstream users also include intervention activity matching (a consumer of `identity_resolver.canonicalize_name`), economics, catalog access and taxonomy consumers; these are data dependencies rather than solver calls. Hull-model loading also resolves this package’s curated resources. [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/rlwi_war_coverage.py:L28-L30] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/rlwi_war_coverage.py:L107-L111] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/intervention_economics.py:L160-L175] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/brief_generator.py:L42-L55] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/serviceability_matrix.py:L62-L70] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/intervention/access_gap.py:L145-L160] [packages/worldenergydata-vessel_hull_models/src/worldenergydata/vessel_hull_models/rig_hulls/hull_loader.py:L25-L48]

The field-development feasibility adapter calls `ConstructionVesselLoader` and applies capability filters to the loaded inventory. [src/worldenergydata/field_development/integrations.py:L175-L215]

## 10. Coverage and open items

### Evidence coverage

Main-path source and example assertions cited above were inspected; broader coverage is explicitly deferred below, rather than represented as an exhaustive audit.

Current evidence was rerun on revision `44857f28472341267e3238ce7bd7bb6bb16f4e1f` before and after the uncommitted documentation change. The discovered module suite contains 1099 collected cases: BASE and AFTER each 1089 passed, 0 failed, 10 skipped; all 10 cases were attempted and reached shipped missing-fixture skips; none requires a solver or licence. The 2 discovered consumer files add 27 cases: BASE and AFTER each 26 passed, 0 failed, 1 shipped missing-fixture skip for absent WAR data. AFTER outcomes match BASE for every recorded test node and skipped-case summary. [tests/unit/vessel_fleet/loaders/test_historical_xlsx_loader.py:L111-L117] [tests/unit/vessel_fleet/loaders/] [tests/unit/vessel_fleet/parsers/test_xls.py:L163-L185] [tests/unit/vessel_fleet/test_fleet_catalog.py:L281-L289] [tests/unit/vessel_fleet/test_rig_summary_parser.py:L601-L622] [tests/unit/bsee/analysis/intervention/test_rlwi_war_coverage.py:L275-L282]

Both command forms, before and after, used `uv run python -m pytest <targets> --noconftest -q -rA -p no:cacheprovider --basetemp=<scratch>` with `PYTHONPATH` including repository source and the sibling utility source; ordinary sources and repository `addopts` were retained. No solver was invoked by this work. [AGENTS.md:L5-L7] [pyproject.toml:L392-L410]

The discovered consumer tests are `tests/modules/field_development/test_integrations.py` and `tests/unit/bsee/analysis/intervention/test_rlwi_war_coverage.py`; these exercise inventory feasibility and identity-based activity matching. [tests/modules/field_development/test_integrations.py:L86-L101] [tests/unit/bsee/analysis/intervention/test_rlwi_war_coverage.py:L1-L8]

### Missing-fixture case inventory

These cases are attempted in both phases and reach existing missing-fixture skips; NOT_RUN is 0; no skip marker was added (issue pending (1)).

| Test locator | Cases | Reason | Evidence |
| --- | --- | --- | --- |
| `loaders/test_historical_xlsx_loader.py::test_load_real_drive_fleet_spreadsheets` | 1 | Historical spreadsheet fixture absent | [tests/unit/vessel_fleet/loaders/test_historical_xlsx_loader.py:L115-L126] |
| External brochure-derived loader real-data case | 1 | External brochure-derived data absent | [tests/unit/vessel_fleet/loaders/] |
| `parsers/test_xls.py` real-output methods | 5 | Derived `floaters.parquet` absent; count, hull-form, identity, length and type checks not executed | [tests/unit/vessel_fleet/parsers/test_xls.py:L163-L187] |
| `test_fleet_catalog.py::test_real_build` | 1 | Catalog seed/curated input unavailable at configured location | [tests/unit/vessel_fleet/test_fleet_catalog.py:L284-L295] |
| `test_rig_summary_parser.py` native-PDF methods at lines 592 and 598 | 2 | Spec PDF fixtures absent; record identities omitted here | [tests/unit/vessel_fleet/test_rig_summary_parser.py:L590-L620] |
| Consumer `test_rlwi_war_coverage.py::test_real_data_confirms_no_light_intervention_in_deepwater` | 1 | External WAR binary absent | [tests/unit/bsee/analysis/intervention/test_rlwi_war_coverage.py:L275-L282] |

### Open items

| Item | Required next evidence / responsibility | Tracking |
| --- | --- | --- |
| U1 coordinate/loading conventions; U3 independent physical benchmark | Maintainer: qualify one source-bound physical record, loading condition, units and independent expected values before analysis reuse | issue [#1050](https://github.com/vamseeachanta/worldenergydata/issues/1050); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_rig.py:L66-L78] |
| U2 standards audit; broader source/docs review | Maintainer: complete file-by-file collector, configuration, identity, catalog, specialized parser/loader and documentation audit; record standards applicability without assuming standards from schema names | issue pending (1); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/validator.py:L25-L64] |
| U4 deputy and permanent review responsibility | Maintainer: record deputy, data-pipeline review responsibility and shared-log references | issue pending (1) |
| Source freshness, live completeness and upstream rights not checked | Maintainer: source-by-source acquisition and qualification evidence; do not treat offline tests as live-source validation | issues #1102 and #1050; [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/spec_pdf_collector.py:L56-L69] |
| Missing-fixture runs | Maintainer: supply approved historical spreadsheets, derived XLS Parquet, catalog curated input, 2 spec PDFs and WAR fixture; rerun the shipped skipped nodes | issue pending (1); [tests/unit/vessel_fleet/parsers/test_xls.py:L163-L185] [tests/unit/vessel_fleet/test_rig_summary_parser.py:L601-L622] |
| Merge contract and tie assertion | Maintainer: align the population-first docstring with the implemented policy; make the equal-priority assertion exact | issue pending (2); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L52-L55] [tests/unit/vessel_fleet/test_dedup_deduplicator.py:L67-L72] |
| Inconsistent year bounds | Maintainer: document intended schema versus semantic ranges, or align them with boundary tests | issue pending (3); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L158-L163] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/validator.py:L52-L57] |
| U5 parallel normalization, dedup routes and direct enrichment | Maintainer: compare `dedup.normalizer`, `identity_resolver.canonicalize_name`, `BaseVesselEntry.vessel_key` / `normalised_name`, `_match_key` and marine-safety `_normalize_vessel_name` on one synthetic corpus; explain each key difference. Compare `dedupe_catalog` with `deduplicate_fleet`: distinct-record counts equal or each difference explained (count); compare direct enrichment with source-priority fusion | issue pending (4); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L58-L96] [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/base.py:L65-L78] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L550-L611] [scripts/vessel_fleet/ingest_contractor_spec_pdfs.py:L119-L126] [scripts/vessel_fleet/ingest_contractor_spec_pdfs.py:L174-L210] |
| Broader component taxonomy | Maintainer: resolve non-drilling classes and material-grade interpretation separately from this inventory pack | issue [#1138](https://github.com/vamseeachanta/worldenergydata/issues/1138); [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_riser.py:L19-L37] |

### Documentation discovered for the remaining audit

The following repository documents mention the module; discovery does not validate their counts or maturity claims (issue pending (1)).

- `docs/adr/0001-domain-package-split.md` — [docs/adr/0001-domain-package-split.md:L48-L48]
- `docs/data/rig-fleet-website-validation.md` — [docs/data/rig-fleet-website-validation.md:L68-L68]
- `docs/domains/field-development/README.md` — [docs/domains/field-development/README.md:L54-L54]
- `docs/intervention-db/identity-enrichment-sources.md` — [docs/intervention-db/identity-enrichment-sources.md:L25-L25]
- `docs/intervention-db/intervention-stats-brief.generated.md` — [docs/intervention-db/intervention-stats-brief.generated.md:L48-L48]
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` — [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]
- `docs/plans/2026-05-15-issue-411-bsee-war-bridge.md` — [docs/plans/2026-05-15-issue-411-bsee-war-bridge.md:L2-L2]
- `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` — [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L112-L112]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` — [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L16-L16]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` — [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L69-L69]
- `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` — [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L69-L69]
- `docs/reports/data-freshness-scorecard-2026-06-08.md` — [docs/reports/data-freshness-scorecard-2026-06-08.md:L32-L32]

The package README describes the domain split and packaged data; its size claim has not been adopted as a measured result. [packages/worldenergydata-vessel_fleet/README.md:L1-L16]

### Source reading inventory

Reading states distinguish main-path inspection from the remaining audit (issue pending (1)); a citation in this inventory establishes file identity and extent, not complete behavior coverage.

| Source file | Reading state | Pinned extent |
| --- | --- | --- |
| `__init__.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/__init__.py:L1-L45] |
| `bridge/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/bridge/__init__.py:L1-L8] |
| `bridge/rig_fleet_bridge.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/bridge/rig_fleet_bridge.py:L1-L83] |
| `collectors/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/__init__.py:L1-L1] |
| Off-repository particulars collector 1 of 2 | Remaining audit open; file identity withheld; sidecar entry: to be created (issue pending (1)) | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/] |
| `collectors/baker_hughes_collector.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/baker_hughes_collector.py:L1-L74] |
| `collectors/base.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/base.py:L1-L144] |
| `collectors/boem_collector.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/boem_collector.py:L1-L67] |
| `collectors/classification_collector.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/classification_collector.py:L1-L119] |
| `collectors/equasis_collector.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/equasis_collector.py:L1-L182] |
| `collectors/fleet_page_collector.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/fleet_page_collector.py:L1-L114] |
| Off-repository particulars collector 2 of 2 | Remaining audit open; file identity withheld; sidecar entry: to be created (issue pending (1)) | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/] |
| `collectors/scrape_parser.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/scrape_parser.py:L1-L342] |
| `collectors/spec_pdf_collector.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/collectors/spec_pdf_collector.py:L1-L108] |
| `config/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/config/__init__.py:L1-L1] |
| `config/construction/` | 11 Python files; 475 lines; remaining audit open; file-level identities withheld, sidecar entry: to be created (issue pending (1)) | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/config/construction/] |
| `config/drilling/` | 14 Python files; 887 lines; remaining audit open; file-level identities withheld, sidecar entry: to be created (issue pending (1)) | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/config/drilling/] |
| `config/intervention/` | 7 Python files; 427 lines; remaining audit open; file-level identities withheld, sidecar entry: to be created (issue pending (1)) | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/config/intervention/] |
| `constants.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/constants.py:L1-L120] |
| `dayrate_snapshot.py` | Partial; remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dayrate_snapshot.py:L1-L214] |
| `dedup/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/__init__.py:L1-L1] |
| `dedup/deduplicator.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/deduplicator.py:L1-L245] |
| `dedup/normalizer.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/dedup/normalizer.py:L1-L65] |
| `exporters/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/exporters/__init__.py:L1-L1] |
| `exporters/war_export.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/exporters/war_export.py:L1-L71] |
| `fleet_catalog.py` | Partial; remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/fleet_catalog.py:L1-L446] |
| `identity_crosswalk.py` | Partial; remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_crosswalk.py:L1-L262] |
| `identity_resolver.py` | Partial; remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/identity_resolver.py:L1-L455] |
| `loaders/__init__.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/__init__.py:L1-L10] |
| `loaders/construction_vessel_loader.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/construction_vessel_loader.py:L1-L395] |
| `loaders/drilling_riser_loader.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/drilling_riser_loader.py:L1-L257] |
| `loaders/historical_xlsx_loader.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/historical_xlsx_loader.py:L1-L464] |
| `loaders/intervention_osv_loader.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/intervention_osv_loader.py:L1-L102] |
| External brochure-derived loader | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/loaders/] |
| `models/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/__init__.py:L1-L1] |
| `models/base.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/base.py:L1-L92] |
| `models/construction_vessel.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/construction_vessel.py:L1-L101] |
| `models/drilling_rig.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/drilling_rig.py:L1-L132] |
| `models/drilling_riser.py` | Partial; remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/models/drilling_riser.py:L1-L191] |
| `parsers/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/__init__.py:L1-L1] |
| `parsers/html.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/html.py:L1-L123] |
| `parsers/myshiptracking.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/myshiptracking.py:L1-L77] |
| `parsers/numeric.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/numeric.py:L1-L175] |
| `parsers/pdf.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/pdf.py:L1-L74] |
| `parsers/rig_summary.py` | Partial; remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/rig_summary.py:L1-L977] |
| `parsers/xls.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/parsers/xls.py:L1-L248] |
| `quality/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/__init__.py:L1-L1] |
| `quality/completeness.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/completeness.py:L1-L98] |
| `quality/validator.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/quality/validator.py:L1-L122] |
| `router.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/router.py:L1-L115] |
| `schemas/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/__init__.py:L1-L1] |
| `schemas/base.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/base.py:L1-L170] |
| `schemas/construction_vessel.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/construction_vessel.py:L1-L202] |
| `schemas/drilling_rig.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_rig.py:L1-L237] |
| `schemas/drilling_riser.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/drilling_riser.py:L1-L409] |
| `schemas/intervention_vessel.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/schemas/intervention_vessel.py:L1-L73] |
| `selection.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/selection.py:L1-L167] |
| `spec_pdf_root.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/spec_pdf_root.py:L1-L20] |
| `storage/__init__.py` | Remaining audit open | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/__init__.py:L1-L1] |
| `storage/csv.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/csv.py:L1-L35] |
| `storage/parquet.py` | Inspected main path | [packages/worldenergydata-vessel_fleet/src/worldenergydata/vessel_fleet/storage/parquet.py:L1-L80] |

### Module test-file inventory

Executed assertions originate in the following 49 files; full assertion-by-assertion review beyond the cited examples remains open (issue pending (1)).

- Off-repository particulars collector 1 of 2 test — Remaining audit open; file identity withheld; sidecar entry: to be created (issue pending (1)); [tests/unit/vessel_fleet/collectors/]
- `tests/unit/vessel_fleet/collectors/test_base.py` — [tests/unit/vessel_fleet/collectors/test_base.py:L1-L126]
- Off-repository particulars collector 2 of 2 test — Remaining audit open; file identity withheld; sidecar entry: to be created (issue pending (1)); [tests/unit/vessel_fleet/collectors/]
- `tests/unit/vessel_fleet/collectors/test_scrape_parser.py` — [tests/unit/vessel_fleet/collectors/test_scrape_parser.py:L1-L241]
- `tests/unit/vessel_fleet/config/construction/test_configs.py` — [tests/unit/vessel_fleet/config/construction/test_configs.py:L1-L64]
- `tests/unit/vessel_fleet/config/drilling/test_configs.py` — [tests/unit/vessel_fleet/config/drilling/test_configs.py:L1-L67]
- `tests/unit/vessel_fleet/dedup/test_deduplicator.py` — [tests/unit/vessel_fleet/dedup/test_deduplicator.py:L1-L63]
- `tests/unit/vessel_fleet/dedup/test_normalizer.py` — [tests/unit/vessel_fleet/dedup/test_normalizer.py:L1-L104]
- `tests/unit/vessel_fleet/loaders/test_construction_vessel_loader.py` — [tests/unit/vessel_fleet/loaders/test_construction_vessel_loader.py:L1-L275]
- `tests/unit/vessel_fleet/loaders/test_construction_vessel_loader_integration.py` — [tests/unit/vessel_fleet/loaders/test_construction_vessel_loader_integration.py:L1-L125]
- `tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py` — [tests/unit/vessel_fleet/loaders/test_drilling_riser_alignment.py:L1-L320]
- `tests/unit/vessel_fleet/loaders/test_drilling_riser_loader.py` — [tests/unit/vessel_fleet/loaders/test_drilling_riser_loader.py:L1-L319]
- `tests/unit/vessel_fleet/loaders/test_historical_xlsx_loader.py` — [tests/unit/vessel_fleet/loaders/test_historical_xlsx_loader.py:L1-L126]
- `tests/unit/vessel_fleet/loaders/test_intervention_osv_loader.py` — [tests/unit/vessel_fleet/loaders/test_intervention_osv_loader.py:L1-L96]
- External brochure-derived loader test — [tests/unit/vessel_fleet/loaders/]
- `tests/unit/vessel_fleet/loaders/test_public_api.py` — [tests/unit/vessel_fleet/loaders/test_public_api.py:L1-L33]
- `tests/unit/vessel_fleet/models/test_base.py` — [tests/unit/vessel_fleet/models/test_base.py:L1-L118]
- `tests/unit/vessel_fleet/models/test_construction_vessel.py` — [tests/unit/vessel_fleet/models/test_construction_vessel.py:L1-L130]
- `tests/unit/vessel_fleet/models/test_drilling_rig.py` — [tests/unit/vessel_fleet/models/test_drilling_rig.py:L1-L141]
- `tests/unit/vessel_fleet/models/test_drilling_riser.py` — [tests/unit/vessel_fleet/models/test_drilling_riser.py:L1-L192]
- `tests/unit/vessel_fleet/models/test_drilling_riser_model.py` — [tests/unit/vessel_fleet/models/test_drilling_riser_model.py:L1-L128]
- `tests/unit/vessel_fleet/parsers/test_numeric.py` — [tests/unit/vessel_fleet/parsers/test_numeric.py:L1-L288]
- `tests/unit/vessel_fleet/parsers/test_xls.py` — [tests/unit/vessel_fleet/parsers/test_xls.py:L1-L221]
- `tests/unit/vessel_fleet/quality/test_completeness.py` — [tests/unit/vessel_fleet/quality/test_completeness.py:L1-L132]
- `tests/unit/vessel_fleet/quality/test_validator.py` — [tests/unit/vessel_fleet/quality/test_validator.py:L1-L191]
- `tests/unit/vessel_fleet/schemas/test_base.py` — [tests/unit/vessel_fleet/schemas/test_base.py:L1-L93]
- `tests/unit/vessel_fleet/schemas/test_construction.py` — [tests/unit/vessel_fleet/schemas/test_construction.py:L1-L148]
- `tests/unit/vessel_fleet/schemas/test_drilling_rig.py` — [tests/unit/vessel_fleet/schemas/test_drilling_rig.py:L1-L140]
- `tests/unit/vessel_fleet/schemas/test_drilling_riser.py` — [tests/unit/vessel_fleet/schemas/test_drilling_riser.py:L1-L174]
- `tests/unit/vessel_fleet/schemas/test_drilling_riser_schema.py` — [tests/unit/vessel_fleet/schemas/test_drilling_riser_schema.py:L1-L108]
- `tests/unit/vessel_fleet/schemas/test_intervention.py` — [tests/unit/vessel_fleet/schemas/test_intervention.py:L1-L144]
- `tests/unit/vessel_fleet/schemas/test_schemas.py` — [tests/unit/vessel_fleet/schemas/test_schemas.py:L1-L247]
- `tests/unit/vessel_fleet/storage/test_parquet.py` — [tests/unit/vessel_fleet/storage/test_parquet.py:L1-L93]
- `tests/unit/vessel_fleet/test_collect_drilling_fleet.py` — [tests/unit/vessel_fleet/test_collect_drilling_fleet.py:L1-L267]
- `tests/unit/vessel_fleet/test_constants.py` — [tests/unit/vessel_fleet/test_constants.py:L1-L154]
- `tests/unit/vessel_fleet/test_dayrate_snapshot.py` — [tests/unit/vessel_fleet/test_dayrate_snapshot.py:L1-L193]
- `tests/unit/vessel_fleet/test_dedup_deduplicator.py` — [tests/unit/vessel_fleet/test_dedup_deduplicator.py:L1-L236]
- `tests/unit/vessel_fleet/test_fleet_catalog.py` — [tests/unit/vessel_fleet/test_fleet_catalog.py:L1-L295]
- `tests/unit/vessel_fleet/test_identity_enrichment.py` — [tests/unit/vessel_fleet/test_identity_enrichment.py:L1-L80]
- `tests/unit/vessel_fleet/test_identity_resolver.py` — [tests/unit/vessel_fleet/test_identity_resolver.py:L1-L186]
- `tests/unit/vessel_fleet/test_myshiptracking_parser.py` — [tests/unit/vessel_fleet/test_myshiptracking_parser.py:L1-L58]
- `tests/unit/vessel_fleet/test_rig_fleet_bridge.py` — [tests/unit/vessel_fleet/test_rig_fleet_bridge.py:L1-L92]
- `tests/unit/vessel_fleet/test_rig_summary_parser.py` — [tests/unit/vessel_fleet/test_rig_summary_parser.py:L1-L633]
- `tests/unit/vessel_fleet/test_router.py` — [tests/unit/vessel_fleet/test_router.py:L1-L113]
- `tests/unit/vessel_fleet/test_selection.py` — [tests/unit/vessel_fleet/test_selection.py:L1-L112]
- `tests/unit/vessel_fleet/test_spec_pdf_root.py` — [tests/unit/vessel_fleet/test_spec_pdf_root.py:L1-L273]
- `tests/unit/vessel_fleet/test_storage_csv.py` — [tests/unit/vessel_fleet/test_storage_csv.py:L1-L48]
- `tests/unit/vessel_fleet/test_storage_parquet.py` — [tests/unit/vessel_fleet/test_storage_parquet.py:L1-L95]
- `tests/unit/vessel_fleet/test_war_export.py` — [tests/unit/vessel_fleet/test_war_export.py:L1-L66]
