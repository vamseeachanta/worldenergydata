# HSE module knowledge pack

| Header | Value |
|---|---|
| Module | bsee:hse |
| Repository | worldenergydata |
| Package path | `packages/worldenergydata-bsee/src/worldenergydata/hse` |
| Pack revision | 1 |
| Code revision | `81e159ef57534f2ac4f324992ca3b5cff55d56ad` |
| Analysis family | EC; data pipeline; AQG r0 Python calculations gate set |
| Quality manager role | Calculations quality manager |
| Deputy role | Maintainer-designated independent calculations reviewer |
| Status | DRAFT; clearance pending |

## 1. Purpose and scope

The public interface exports incident ORM models, CSV importers, post-import validation, incident grounding and a query API. [packages/worldenergydata-bsee/src/worldenergydata/hse/__init__.py:L33-L97]
The main ingestion route is `fetch_data → normalize_data → validate_data → is_duplicate → import_record`; invalid records are counted and duplicate identifiers are skipped. [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L269-L321]
The query surfaces are `incidents`, `penalties`, `statistics` and `epa_tri`; an uninjected query session is built from synthetic SQLite records. [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L194-L200] [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L420-L424]
A synthetic query result establishes API behaviour only; live database population, asynchronous access and additional query surfaces remain coverage work under issue 363. [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L12-L17]
Grounding selects recent and severe precedent records; it does not calculate a mechanical failure probability. [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L318-L354]

UNVERIFIED: Module maturity, production-data completeness and engineering fitness are not established by the inventory's test count; qualification remains open under issue 349 and issue pending (2).

## 2. Inputs and outputs

### Inputs

| Name | Unit / representation | Allowed range / default | Source and evidence |
|---|---|---|---|
| Incident CSV | CSV; string identifiers and classifications | File required for `fetch_data`; header-only input yields an empty list | `BSEEIncidentsImporter.fetch_data` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer.py:L29-L85] |
| `incident_date` | Naive datetime; date or date-time text | `%Y-%m-%d` or `%Y-%m-%d %H:%M:%S`; failed parsing retains the input for validation | `normalize_data` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer.py:L111-L133] |
| `bsee_incident_id`, `operator`, `incident_type`, `severity` | Strings; category / identifier (unit 1) | Required with datetime; four incident types and five severity labels | `BaseImporter` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L42-L50] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L137-L201] |
| `latitude`, `longitude` | Degrees; negative longitude retained | Optional; latitude 18–31, longitude −98 to −80; bad numeric text becomes `None` | Code bounds and parser [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L52-L56] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer.py:L173-L210] |
| Raw investigation file | Comma-separated, Latin-1; string columns | `DATE_OCCURRED`, `MILITARY_TIME`, `ACCIDENT_TYPE`; rows without parseable dates are omitted | `BSEEIncInvImporter.load`, `_normalize_row` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L124-L200] |
| Raw compliance counts | Comma-separated, Latin-1; counts | One output record per positive category; invalid count text becomes zero | `BSEEINCSImporter` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py:L112-L141] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py:L175-L214] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py:L251-L266] |
| Grounding corpus | Comma-separated, Latin-1; dates and classification text | Explicit `bsee_path` overrides default resolution; missing input yields an empty incident list | `load_bsee` [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L266-L291] |
| Statistics CSV | Reporting date, counts (unit 1), operational period (days) | Required date and operator; optional integer conversions can become `None` | `BSEEStatisticsImporter` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L42-L57] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L157-L246] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L279-L298] |
| Query session | SQLAlchemy session (unit 1) | Default `None` selects a synthetic in-memory database | `_HSEQuery._get_session` [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L194-L200] |

UNVERIFIED: Coordinate datum, positive geographic axes beyond the numeric bounds, and date timezone are not specified in the cited model or parser; no phase or mechanical coordinate frame is established. Issue pending (2).

### Outputs

| Name | Unit / representation | Meaning / limits | Evidence |
|---|---|---|---|
| `HSEIncident` | ORM row; date, identifier, category and optional location | Unique incident identifier; child injury, spill, violation and equipment relationships | [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L44-L109] |
| `SafetyStatistic` | Counts (unit 1); period (days) | Separate aggregate table rather than an incident subclass | [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L313-L347] |
| Spill conversion | Barrels and gallons | `barrels * 42` or `gallons / 42`; unset input returns `None`; code convention, independent source not qualified | [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L233-L255] |
| `ViolationIncident` | Penalty amount in dollars; status category | Linked to incident; regulation text retained as a string | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer.py:L52-L58] [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L281-L301] |
| `ToxicRelease` | Release quantities in pounds; reporting year | Annual facility/chemical summary rather than individual incident | [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L407-L456] |
| Import statistics | Integer record counts | `imported_count`, `skipped_count`, `error_count`, `total_records`; counters belong to the importer instance | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L58-L67] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L314-L321] |
| Quality report | JSON or HTML; percentages and counts | Report requires prior validation; placeholder subchecks are excluded from qualification | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py:L500-L583] |
| Grounding | Dictionary / Markdown, at most two recent plus two disjoint severe rows | Business-date corpus vintage; area/block and lease location strings, not operator fields | [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L166-L205] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L290-L309] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L338-L354] |
| Query results | pandas DataFrame | Filters and grouping operate on fetched ORM rows; carcinogen passthrough is a no-op | [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L203-L230] [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L360-L375] [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L414-L417] |

## 3. Method and governing standards

| Method | Implementation and governing basis | Qualification limit |
|---|---|---|
| Required-field, enum and geographic validation | `BaseImporter.validate_data`; explicit code bounds and required fields [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L104-L215] | Code policy, not evidence of regulatory completeness |
| CSV normalization | `BSEEIncidentsImporter.normalize_data`; rename columns, parse datetime and optional coordinates [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer.py:L87-L210] | Unknown coordinate text becomes absent data |
| Identifier deduplication | `BaseImporter.is_duplicate` queries `HSEIncident.bsee_incident_id` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L219-L241] | Identifier identity only |
| Penalty persistence | `BSEEPenaltiesImporter.import_record` flushes parent, writes child, commits [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer.py:L219-L274] | Transaction error propagates |
| Aggregate persistence | `BSEEStatisticsImporter.import_record` writes `SafetyStatistic`; its duplicate check first queries operator/date/facility, then legacy incident IDs [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py:L299-L374] | Composite-key detection precedes the legacy fallback |
| Classification of raw investigation rows | First matching keyword in insertion order; unknown type defaults to equipment failure and unknown severity to minor [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L250-L278] | Classification is a code heuristic; its first-match severity scheme differs from grounding (section 6) [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L65-L82] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L129-L146] |
| Compliance category expansion | Positive warning, component-shut-in and facility-shut-in counts each emit one dictionary carrying `inc_count` [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py:L175-L214] | Output row count differs from incident-count sum |
| Quality score | `run_all_validations`: completeness 40%; range, consistency, outlier and temporal components 15% each [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py:L407-L457] | Outlier and several related-table checks are placeholders; see section 6 |
| Grounding and freshness | `ground` sorts by date, then remaining records by severity/date; `corpus_vintage` takes maximum parseable business date [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L250-L263] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L338-L354] | Highest-rank severity uses a different scheme from raw ingestion (section 6); ranks are ordinal code policy, not risk probabilities [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L129-L146] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L265-L278] |
| Demand logging | `ground_and_log` writes JSONL; unknown and fewer-than-four-record modes are logged as gaps [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding_demand.py:L43-L43] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding_demand.py:L56-L77] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding_demand.py:L84-L120] | Request counts are demand, not incident frequency |
| OSHA normalization | `OSHAImporter` resolves filtered/unfiltered files, normalizes inspection/accident/injury rows and deduplicates incident IDs [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/osha_importer.py:L294-L316] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/osha_importer.py:L468-L658] | Mapping and default severities require source qualification |
| TRI normalization | `EPATRIImporter` maps columns, converts quantities, deduplicates by facility/chemical/year, and commits batches [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/epa_tri_importer.py:L261-L445] | Counters accumulate across calls; failed batch commits roll back |

The model docstring and incident URL importer name **30 CFR 250.188**; the penalty model stores a free-text regulatory citation. [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L24-L29] [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L286-L289] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer_url.py:L24-L26]
The synthetic query fixture also names **30 CFR 250.300**, and the database test fixture names **30 CFR 250.107**; these are stored citation strings rather than implemented clause checks. [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L99-L122] [tests/unit/hse/database/test_models.py:L551-L565]
UNVERIFIED: The edition, section titles and compliance of these 30 CFR Part 250 public regulations have not been checked against a published copy. No regulation-derived value is qualified here. Issue pending (2).
UNVERIFIED: The barrel/gallon conversion and severity mappings lack an independently checked reference and a qualified calculation Citation sidecar in this pack. Issue pending (2).

## 4. Validated worked examples

Validated examples: **0**; independent engineering reference qualification remains issue pending (2).
The following are **regression examples**, with synthetic or repository-fixture expectations; none establishes real-corpus completeness. [tests/hse/test_hse_api.py:L4-L4] [tests/unit/hse/test_grounding.py:L5-L10]

| Case | Input / expectation / tolerance | Existing test node ID | Offline result |
|---|---|---|---|
| Mixed import accounting | Three input dictionaries; two imports, one error, zero skipped; exact integer equality (records) [tests/unit/hse/importers/test_base_importer.py:L391-L430] [tests/unit/hse/importers/test_base_importer.py:L480-L488] | `tests/unit/hse/importers/test_base_importer.py::TestImportStatisticsTracking::test_full_import_pipeline_with_mixed_data` | PASS at BASE and after; revision-1 comparison |
| Duplicate CSV identifiers | Three rows, two unique IDs; two imported, one skipped; tolerance zero records [tests/unit/hse/importers/test_bsee_incidents_importer.py:L336-L363] | `tests/unit/hse/importers/test_bsee_incidents_importer.py::TestDeduplication::test_import_data_detects_duplicates_in_csv` | PASS at BASE and after; revision-1 comparison |
| Typed incident filter | Synthetic year/severity filter; exactly one row; tolerance zero records [tests/hse/test_hse_api.py:L37-L43] | `tests/hse/test_hse_api.py::test_hse_incidents_year_and_severity_filters` | PASS at BASE and after; revision-1 comparison |
| Grounding separation | Two severe selections are disjoint from recent selections; exact dates and labels, zero overlapping records [tests/unit/hse/test_grounding.py:L47-L53] | `tests/unit/hse/test_grounding.py::test_most_severe_two_are_highest_rank_and_disjoint_from_latest` | PASS at BASE and after; revision-1 comparison |
| Source vintage | Maximum fixture business date equals `2026-01-08`; tolerance zero days [tests/unit/hse/test_source_vintage.py:L23-L25] | `tests/unit/hse/test_source_vintage.py::test_corpus_vintage_is_max_date_from_dataset_field` | PASS at BASE and after; revision-1 comparison |
| Card evidence stamp | Rendered card contains fixture vintage string; zero missing stamps [tests/unit/hse/test_grounding_card.py:L45-L46] | `tests/unit/hse/test_grounding_card.py::test_vintage_stamp_present` | PASS at BASE and after; revision-1 comparison |

## 5. QA gates

Gate selection: **AQG r0**, section 10, Python calculations; G5 applies to every family.
These are proposed executable acceptance checks; defining a check does not certify production input or grant gate clearance.

| Gate | Applicability | Check ID and executable check | Numeric pass criterion and unit | Evidence |
|---|---|---|---|---|
| G0 | Applicable: inputs, units, citations | H0: execute `tests/unit/hse/importers/test_base_importer.py::TestDataValidationFramework::test_validate_data_latitude_outside_gom_range`; `BaseImporter.validate_data` rejects the out-of-bounds example | Zero out-of-bounds accepted records; latitude bounds 18–31 degrees | Assertion and validation error [tests/unit/hse/importers/test_base_importer.py:L161-L179] |
| G1 | Applicable: Python import and offline tests | H1: execute `tests/hse/test_hse_api.py::test_hse_queries_are_typed_query_subclasses` | Four of four query classes satisfy `TypedQuery`; zero assertion failures (classes) | Test result [tests/hse/test_hse_api.py:L14-L23] |
| G2 | Applicable: hand comparison | H2: enumerate the three fixture dictionaries in the mixed accounting case; compare `BaseImporter.import_data` to the hand count 3 = 2 + 1 + 0 | Zero residual records in total minus imported/errors/skipped; exact equality | Input audit and section-4 mixed accounting result [tests/unit/hse/importers/test_base_importer.py:L391-L430] [tests/unit/hse/importers/test_base_importer.py:L480-L488] |
| G3 | NOT_APPLICABLE: no time-domain solver in this Python data route | No short dynamics gate | NOT_APPLICABLE | Pipeline implementation [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L269-L321] |
| G4 | NOT_APPLICABLE: no diffraction body or panel mesh in this route | No diffraction gate | NOT_APPLICABLE | Pipeline implementation [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py:L269-L321] |
| G5 | Applicable: evidence carried into output | H5: execute `tests/unit/hse/test_grounding_card.py::test_vintage_stamp_present` and `tests/unit/hse/test_grounding_card.py::test_no_operator_names_and_attribution`; check `render_html` output | Zero absent vintage strings, zero forbidden fixture names, one source attribution present (occurrences minimum) | Rendered-output assertions [tests/unit/hse/test_grounding_card.py:L45-L46] [tests/unit/hse/test_grounding_card.py:L60-L67] |

The target runtime for G1 is Python with SQLAlchemy/pandas and the shared query base; no external solver load route is used by these checks. [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L28-L35] [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L42-L58]
G2 is an ingestion accounting check only; physical-unit and regulatory qualification remain open under issue pending (2).

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom | Cause and detection | Tracking / date |
|---|---|---|
| A zero violation count can be mistaken for a completed check | `negative_penalty_violations`, `negative_count_violations`, compliance consistency and outlier outputs are fixed placeholders; no detection check exists for related-table violations | Issue 366; observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py:L197-L203] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py:L254-L294] |
| Query success can conceal absent real data | `_get_session` creates synthetic rows when no session is injected; no detection check exists for live population; `tests/hse/test_hse_api.py::test_hse_incidents_query_returns_typed_df` checks only synthetic rows [tests/hse/test_hse_api.py:L26-L34] | Issue 363; observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L194-L200] |
| A requested chemical flag is not applied | `EpaTriQuery._execute` ignores the carcinogen passthrough; no detection check exists for that filter | Issue 363; observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L414-L417] |
| Invalid raw values become defaults or disappear | Bad investigation dates are skipped; unknown severity becomes minor; invalid compliance counts become zero; no detection check exists for an upstream reconciliation threshold | Issue 366; observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L165-L176] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L265-L278] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py:L251-L266] |
| Guide source table differs from current code | Guide associates incident/statistics/penalty importers with unrelated data categories; URL subclasses now use different constants; no detection check exists for guide/code drift | Issue pending (1); observed 2026-10-15 [docs/hse/URL_REFRESH_INTEGRATION.md:L41-L45] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer_url.py:L39-L42] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer_url.py:L40-L42] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer_url.py:L39-L39] |
| Acquisition cache existence is mistaken for integrity | Existing extraction directory skips acquisition without content validation; `verify_data` only counts text-file lines; no detection check exists for content integrity; `tests/unit/scheduler/test_hse_refresh.py::test_zero_rows_is_failure` detects zero rows using a fake acquirer [tests/unit/scheduler/test_hse_refresh.py:L15-L24] [tests/unit/scheduler/test_hse_refresh.py:L36-L39] [tests/unit/scheduler/test_hse_refresh.py:L64-L67] | Issue 462; observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/bsee_acquirer.py:L107-L114] [packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/bsee_acquirer.py:L240-L267] |
| Metadata refresh is mistaken for source vintage | H5 and `tests/unit/hse/test_source_vintage.py::test_committed_contract_hse_row_has_proven_vintage` guard dataset business dates rather than file modification time | Fixed under closed #489; observed 2026-10-15 [tests/unit/hse/test_source_vintage.py:L23-L42] |
| Parser documentation describes a different delimiter | Investigation/compliance loader docstrings and acquisition documentation say tab-delimited while both loaders read comma-separated input; no detection check exists for parser-docstring drift | Issue pending (1); observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L7-L10] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L124-L130] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py:L69-L74] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py:L116-L122] [packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/bsee_acquirer.py:L1-L8] |
| TRI directory import over-counts imported/skipped/error totals across files | `import_file` returns cumulative instance counters and `import_directory` adds those cumulative values for each file; `total_records` remains per-file; no detection check exists | Issue pending (5); observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/epa_tri_importer.py:L146-L151] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/epa_tri_importer.py:L179-L206] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/epa_tri_importer.py:L240-L259] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/epa_tri_importer.py:L437-L445] |
| The same accident text receives incompatible severity labels | Raw ingestion uses the first matching keyword; grounding takes the highest rank: explosion is recordable/catastrophic, blowout lost_time/catastrophic and pollution minor/environmental, respectively; no detection check exists for cross-route agreement | Issue pending (6); observed 2026-10-15 [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L65-L82] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py:L265-L278] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L129-L146] |
| Stale unit URL-importer copies fail 24 nodes and are excluded from default collection | Expectations predate the current constants and processor call; detection: run the three unit URL-importer files listed below with `--import-mode=importlib`; no new code defect is inferred from the stale expectations alone | Issue pending (4); observed 2026-10-15 [tests/conftest.py:L644-L649] [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L59-L71] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer_url.py:L37-L39] |

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change | Shared entry |
|---|---|---|---|---|---|
| 2026-10-15 | Initial pack revision 0 | Fixed-zero quality outputs do not establish related-table checks | [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py:L197-L203] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py:L278-L294] | Sections 3 and 6 separate implemented checks from placeholders | Issue 366 |

## 8. Ownership

Proposed review assignment: calculations quality manager; deputy: maintainer-designated independent calculations reviewer; producer: documentation contributor.
Clearance is pending independent review; unresolved criteria and regulatory interpretations will be referred to the calculations quality manager, with cross-family scope referred to the maintainers.

## 9. Dependencies and implementation inventory

The URL subclasses delegate normalization and persistence to their CSV parents and use `BSEEWebScraper` plus `MemoryProcessor` for downloads/extraction. [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer_url.py:L45-L97] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer_url.py:L45-L97] [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer_url.py:L41-L90]
The package imports shared logging, data resolution and the typed query base; persistence uses SQLAlchemy and pandas. [packages/worldenergydata-bsee/src/worldenergydata/hse/importers/osha_importer.py:L41-L47] [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L28-L35] [packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py:L5-L19]
The grounding card takes a supplied analysis summary and grounding dictionary; its browser plotting script is loaded from a CDN. [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding_card.py:L26-L42] [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding_card.py:L104-L136]
The downstream scheduler's `HseRefreshJob._acquirer` constructs `BSEEAcquirer`; scheduler orchestration remains outside this package. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/hse_refresh.py:L32-L42]
The downstream note builder imports grounding and uses its corpus selection/vintage; its generated note is adjacent documentation rather than independent validation. [scripts/build_hse_grounding_matches.py:L11-L17] [scripts/build_hse_grounding_matches.py:L43-L57]
The root `hse_api` lazy accessor exposes this package's API without its own query implementation. [src/worldenergydata/__init__.py:L100-L103]
Distribution dependencies include shared domain packages, assetutilities, numerical/plotting/HTTP libraries and SQLAlchemy; these declarations cover the whole distribution, while its coupling note specifically records `hse --> bsee`. [packages/worldenergydata-bsee/pyproject.toml:L62-L86] [packages/worldenergydata-bsee/pyproject.toml:L28-L38]

Implementation-map data revision: `947fa50ff9a9e210de7e8f90e01b37add85c5954`; inspected map commit: `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; source: `digitalmodel`, `docs/registry/implementation-map.yaml`.
A8 inventory: **empty**. The inspected map has 13 families, zero implementation rows within the header package path, and therefore zero counted families; the counted-family grep is **NOT_APPLICABLE** for that reason.
Map follow-up, issue pending (2): add the section-3 families for required-field/enum/geographic validation, CSV normalization, identifier deduplication, parent/child persistence, aggregate persistence, keyword classification (including the outside-package `_severity` map gap below), compliance expansion, barrel/gallon conversion, quality scoring, grounding/vintage, demand aggregation, OSHA normalization and TRI normalization before counting them in a future map revision.

Repository-wide discovery includes `scripts/import_bsee_hse_to_db.py`, which validates and persists loader outputs, and `scripts/hse/stamp_source_vintage.py`, which consumes corpus vintage. [scripts/import_bsee_hse_to_db.py:L1-L17] [scripts/hse/stamp_source_vintage.py:L1-L15]
The exploratory grounding script implements its own severity ranking and selection rather than delegating to the package; this is an outside-package map gap, excluded from the counted-family result, and is included in issue pending (2). [scripts/exploration/hse_incident_grounding.py:L52-L69] [scripts/exploration/hse_incident_grounding.py:L147-L179]

The bridge also implements required-field and enum validation independently in `validate_record`; this outside-package map gap is included in issue pending (2). [scripts/import_bsee_hse_to_db.py:L86-L113]

Residual legacy source files are listed as outside-package sources, not claimed as a package by this pack; compatibility loading redirects old imports to the canonical package, so their presence alone does not establish duplicate runtime execution. [src/worldenergydata/_compat.py:L26-L32] [src/worldenergydata/_compat.py:L67-L73]

| Outside-package source | Classification / map follow-up |
|---|---|
| Public refresh `_severity` | Analyst-defined first-match severity proxy in the HSE package; regulatory context and vocabulary basis are recorded in `CLASSIFICATION_BASIS`. This report method requires map follow-up, issue pending (2). Source: `packages/worldenergydata-bsee/src/worldenergydata/hse/public_refresh.py::_severity`. |
| Legacy statistics `normalize_data` | Own column conversion algorithm; map gap, issue pending (2) [src/worldenergydata/modules/hse/importers/bsee_statistics_importer.py:L91-L260] |
| Legacy incident URL `fetch_data` | Download/processor wrapper; alternative source route to inventory, issue pending (2) [src/worldenergydata/modules/hse/importers/bsee_incidents_importer_url.py:L51-L92] |
| Legacy penalty URL `fetch_data` | Download/processor wrapper; alternative source route to inventory, issue pending (2) [src/worldenergydata/modules/hse/importers/bsee_penalties_importer_url.py:L57-L104] |
| Legacy statistics URL `fetch_data` | Download/processor wrapper; alternative source route to inventory, issue pending (2) [src/worldenergydata/modules/hse/importers/bsee_statistics_importer_url.py:L53-L96] |

UNVERIFIED: Full duplicate-method classification across the repository and scripts, upstream dataset inventory rows and dependency version qualification remain issue pending (2); the empty-map result does not establish method uniqueness.

## 10. Coverage and open items

| Item | Coverage / remaining evidence | Responsible role | Tracking |
|---|---|---|---|
| Main route | CSV incident/penalty/statistics ingestion, ORM models, query fallback, grounding, demand log and card are described above; source acquisition is described as code behaviour only | Maintainer | Issue 349 |
| Full-method qualification | Acquisition, OSHA/TRI edge cases, raw-loader classification, units/timezone/datum, independent examples, Citation sidecars and map enrichment require further qualification; includes all UNVERIFIED statements in sections 1–3 and 9 | Calculations quality manager | Issue pending (2) |
| Guide drift | Source table and parser docstrings require correction against implementation; URL availability has not been checked | Maintainer | Issue pending (1) |
| TRI directory accounting | Cumulative per-instance counters are summed as per-file totals; section 6 records the defect | Maintainer | Issue pending (5) |
| Severity policy agreement | Raw-loader and grounding schemes classify identical accident text differently; section 6 records the defect | Maintainer | Issue pending (6) |
| Distribution boundary | Package-data includes `**/*.md`, so a nested pack can be included in the wheel; exclusion is outside the allowed documentation-only files | Maintainer | Issue pending (3) [packages/worldenergydata-bsee/pyproject.toml:L112-L116] |
| Live-data readiness | No live corpus, private reference data, operator records or client-derived values were qualified; synthetic API tests are insufficient | Maintainer | Issues 363 and 366 [packages/worldenergydata-bsee/src/worldenergydata/hse/api.py:L12-L17] |
| Omitted URL tests | Explicit baseline execution reports 24 failures; existing exclusions conceal stale source/processor expectations | Maintainer | Issue pending (4) [tests/conftest.py:L644-L649] |
| Independent clearance | This pack remains DRAFT pending second-provider review and replacement of pending draft references with issue numbers | Calculations quality manager | Issue pending (2) |

### Source and test coverage record

Source inventory: 25 Python files, 7804 lines; all files were parsed for definitions and the main routes above were inspected. Detailed independent qualification of all branches remains issue pending (2).

- `packages/worldenergydata-bsee/src/worldenergydata/hse/__init__.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/__init__.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/bsee_acquirer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/epa_tri_acquirer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/osha_acquirer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/acquirers/osha_fatalities_acquirer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/api.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/database/__init__.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/database/models.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/grounding_card.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/grounding_demand.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/__init__.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/base_importer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incidents_importer_url.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incinv_importer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_incs_importer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_penalties_importer_url.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/bsee_statistics_importer_url.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/data_quality_validator.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/epa_tri_importer.py`
- `packages/worldenergydata-bsee/src/worldenergydata/hse/importers/osha_importer.py`

Content-based documentation discovery found 31 Markdown files naming HSE; the generated note `docs/hse/grounding-riser-matches.md` adds one adjacent path without that content match. The integration guide, generated note and relevant source passages were read; broader adjacent workflows remain issue pending (2). [docs/hse/grounding-riser-matches.md:L1-L16] [scripts/build_hse_grounding_matches.py:L43-L57] Discovered files:

- `docs/knowledge-base/bsee/integration/codebase-mapping.md`
- `docs/CLI.md`
- `docs/adr/0001-domain-package-split.md`
- `docs/hse/URL_REFRESH_INTEGRATION.md`
- `docs/hse/grounding-riser-matches.md`
- `docs/data/TWO_TIER_DATA.md`
- `docs/PHASE_2_TIER_1_COVERAGE_EXPANSION.md`
- `docs/knowledge-base/bsee/README.md`
- `docs/reference/index.md`
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md`
- `docs/reports/data-freshness-scorecard-2026-06-08.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md`
- `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `docs/modules/repository-architecture.md`
- `docs/plans/2026-05-18-issue-423-marketing-pipeline-umbrella.md`
- `docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md`
- `docs/plans/2026-05-03-issue-376-cross-field-analytics-lt.md`
- `docs/plans/README.md`
- `docs/plans/2026-05-04-issue-275-ast-aware-logger-script.md`
- `docs/plans/2026-05-04-issue-363-hse-query-api.md`
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`
- `docs/plans/2026-05-03-issue-375-per-field-economics-10-lt-fields.md`
- `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md`
- `docs/plans/2026-05-18-issue-425-operator-hse-benchmarking.md`
- `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md`
- `docs/plans/2026-05-03-issue-377-lt-comprehensive-report-assembly.md`
- `docs/plans/2026-05-04-issue-366-hse-bulk-dedup-ingest.md`
- `docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md`
- `docs/plans/2026-05-08-issue-394-repo-structure-normalization.md`
- `docs/plans/2026-05-18-issue-426-drilling-hse-patterns.md`

Test files discovered (27):

- `tests/hse/test_hse_api.py`
- `tests/modules/hse/importers/test_bsee_incidents_importer_url.py`
- `tests/modules/hse/importers/test_bsee_penalties_importer_url.py`
- `tests/modules/hse/importers/test_bsee_statistics_importer_url.py`
- `tests/unit/hse/database/test_models.py`
- `tests/unit/hse/importers/test_base_importer.py`
- `tests/unit/hse/importers/test_bsee_importers_url_integration.py`
- `tests/unit/hse/importers/test_bsee_incidents_importer.py`
- `tests/unit/hse/importers/test_bsee_incidents_importer_url.py`
- `tests/unit/hse/importers/test_bsee_penalties_importer.py`
- `tests/unit/hse/importers/test_bsee_penalties_importer_url.py`
- `tests/unit/hse/importers/test_bsee_statistics_importer.py`
- `tests/unit/hse/importers/test_bsee_statistics_importer_url.py`
- `tests/unit/hse/importers/test_data_quality_validators.py`
- `tests/unit/hse/importers/test_osha_importer.py`
- `tests/unit/hse/test_bsee_hse_db_import.py`
- `tests/unit/hse/test_bsee_incinv_importer.py`
- `tests/unit/hse/test_bsee_incs_importer.py`
- `tests/unit/hse/test_epa_tri_acquirer.py`
- `tests/unit/hse/test_grounding.py`
- `tests/unit/hse/test_grounding_card.py`
- `tests/unit/hse/test_grounding_demand.py`
- `tests/unit/hse/test_grounding_riser_modes.py`
- `tests/unit/hse/test_osha_fatalities_acquirer.py`
- `tests/unit/hse/test_osha_severity_mapping.py`
- `tests/unit/hse/test_source_vintage.py`
- `tests/unit/scheduler/test_hse_refresh.py`

Revision-1 comparison: BASE `78cd9abefd993c9897a37f04f6930472a981124f` and its uncommitted after-edit tree each collected **500** tests: **469 passed, 24 failed, 2 marker skips, 5 not exercised, NOT_RUN 0** (pytest reports seven skips in total). Normal directory run: **431 passed, 0 failed, 5 not exercised** (436 collected). Explicit four-file importlib run: **38 passed, 24 failed, 2 marker skips** (64 collected). All pass/fail node IDs and skip reasons/counts matched before and after. Only the pack differs between BASE and the header code pin, so both comparisons exercise the pinned implementation and tests. The after-edit runs used the repository's `--allow-existing-tree-changes` option to compare the uncommitted pack bytes; new tree changes remain checked. [tests/conftest.py:L412-L460]

Hosted coverage at `78cd9abe` was the `tests/unit/hse` shard only: **384 collected, 379 passed, 5 skipped**; the other 52 normal-run tests and 64 supplemental tests rely on the local comparison above. [Hosted test log](../../../../../../../../actions/runs/38791699632/job/116618027391)

Normal form: `uv run python -m pytest tests/unit/hse tests/hse tests/modules/hse tests/unit/scheduler/test_hse_refresh.py -q -rA -p no:cacheprovider --basetemp=<scratch>`. Supplemental form: `uv run python -m pytest tests/unit/hse/database/test_models.py tests/unit/hse/importers/test_bsee_incidents_importer_url.py tests/unit/hse/importers/test_bsee_penalties_importer_url.py tests/unit/hse/importers/test_bsee_statistics_importer_url.py --import-mode=importlib -q -rA -p no:cacheprovider --basetemp=<scratch>`. Coverage data/reports were directed to scratch after the initial BASE normal run; its generated reports were removed. No source fallback, extra installation or addopts override was used.

Nonpassing baseline node IDs (failures remain issue pending (4)):

- FAIL `tests/unit/hse/importers/test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURL::test_importer_initialization`. [tests/unit/hse/importers/test_bsee_incidents_importer_url.py:L64-L76]
- FAIL `tests/unit/hse/importers/test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURL::test_fetch_data_downloads_from_url`. [tests/unit/hse/importers/test_bsee_incidents_importer_url.py:L84-L116]
- FAIL `tests/unit/hse/importers/test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURL::test_fetch_data_processes_dict_with_data_key`. [tests/unit/hse/importers/test_bsee_incidents_importer_url.py:L128-L152]
- FAIL `tests/unit/hse/importers/test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURL::test_fetch_data_processes_direct_dataframe`. [tests/unit/hse/importers/test_bsee_incidents_importer_url.py:L154-L173]
- FAIL `tests/unit/hse/importers/test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURL::test_fetch_data_aggregates_multiple_files`. [tests/unit/hse/importers/test_bsee_incidents_importer_url.py:L175-L199]
- FAIL `tests/unit/hse/importers/test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURL::test_normalize_data_inherited_from_parent`. [tests/unit/hse/importers/test_bsee_incidents_importer_url.py:L201-L232]
- FAIL `tests/unit/hse/importers/test_bsee_incidents_importer_url.py::TestBSEEIncidentsImporterURLIntegration::test_no_duplicate_import`. [tests/unit/hse/importers/test_bsee_incidents_importer_url.py:L281-L321]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_importer_initialization`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L59-L71]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_fetch_data_downloads_from_war_url`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L81-L113]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_fetch_data_uses_longest_timeout`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L125-L144]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_normalize_data_converts_penalty_amount_to_float`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L146-L170]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_normalize_data_converts_compliance_deadline_to_datetime`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L172-L195]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_normalize_data_converts_compliance_achieved_to_boolean`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L197-L222]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_normalize_data_sets_incident_type_violation`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L224-L245]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURL::test_importer_handles_multiple_war_files`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L265-L309]
- FAIL `tests/unit/hse/importers/test_bsee_penalties_importer_url.py::TestBSEEPenaltiesImporterURLPerformance::test_very_large_file_handling`. [tests/unit/hse/importers/test_bsee_penalties_importer_url.py:L327-L361]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURL::test_importer_initialization`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L69-L81]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURL::test_fetch_data_downloads_from_url`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L83-L117]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURL::test_fetch_data_uses_longer_timeout`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L129-L150]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURL::test_normalize_data_converts_string_integers`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L152-L183]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURL::test_normalize_data_sets_incident_type_equipment_failure`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L185-L208]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURL::test_normalize_data_maps_report_date_to_incident_date`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L210-L234]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURL::test_importer_handles_multiple_csv_files`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L256-L310]
- FAIL `tests/unit/hse/importers/test_bsee_statistics_importer_url.py::TestBSEEStatisticsImporterURLPerformance::test_large_file_handling`. [tests/unit/hse/importers/test_bsee_statistics_importer_url.py:L333-L372]

Missing-reference cases are **not exercised: 5**, each with its absent file; **NOT_RUN: 0**. Pytest reports these five as skipped. The two SQLite marker skips remain **SKIP: 2**.

| Node ID | Offline result / reason | Evidence |
|---|---|---|
| `tests/unit/hse/test_grounding_riser_modes.py::test_live_corpus_candidate_counts[riser_viv_fatigue-7]` | not exercised: `mv_acc_investigations.txt` absent | [tests/unit/hse/test_grounding_riser_modes.py:L83-L92] |
| `tests/unit/hse/test_grounding_riser_modes.py::test_live_corpus_candidate_counts[structural_overpressure-45]` | not exercised: `mv_acc_investigations.txt` absent | [tests/unit/hse/test_grounding_riser_modes.py:L83-L92] |
| `tests/unit/hse/test_grounding_riser_modes.py::test_fixture_records_are_source_exact` | not exercised: `mv_acc_investigations.txt` absent | [tests/unit/hse/test_grounding_riser_modes.py:L119-L122] |
| `tests/unit/hse/test_osha_severity_mapping.py::TestLookupTableLoading::test_load_real_lookup_file` | not exercised: `data/modules/hse/raw/osha/osha_accident_lookup2.csv` absent | [tests/unit/hse/test_osha_severity_mapping.py:L91-L98] |
| `tests/unit/hse/test_osha_severity_mapping.py::TestLookupTableLoading::test_lookup_has_expected_code_types` | not exercised: `data/modules/hse/raw/osha/osha_accident_lookup2.csv` absent | [tests/unit/hse/test_osha_severity_mapping.py:L117-L124] |
| `tests/unit/hse/database/test_models.py::TestHSEIncidentBaseModel::test_hse_incident_type_enum_invalid_value` | SKIP: SQLite does not enforce Enum constraints | [tests/unit/hse/database/test_models.py:L144-L149] |
| `tests/unit/hse/database/test_models.py::TestHSEIncidentBaseModel::test_hse_incident_severity_enum_invalid_value` | SKIP: SQLite does not enforce Enum constraints | [tests/unit/hse/database/test_models.py:L182-L187] |

The incident corpus resolver tries `$WED_HSE_DATA_ROOT/hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt`, then `data/modules/hse/raw/bsee/IncInvRawData/mv_acc_investigations.txt`, then a fixed external default; none supplies the missing corpus in these runs. [packages/worldenergydata-bsee/src/worldenergydata/hse/grounding.py:L221-L238]


No routing registry was found at `docs/registry/module-routing.yaml`; no registry entry is added.
