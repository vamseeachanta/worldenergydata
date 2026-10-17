# LNG terminals module knowledge pack

| Header | Value |
| --- | --- |
| Module | `lng_terminals` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `285d65c40896b17ccf44568e59f5b789d59c943e` |
| Analysis family | Data pipeline; EC; AQG r0 Python calculations gate set |
| Quality manager role | Calculations quality manager, pending a data-pipeline specialist |
| Status | DRAFT |

## 1. Purpose and scope

The collector route constructs `LNGTerminal` records, enriches them, normalizes and deduplicates them, scores completeness, then exports tables and reports. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L80-L127] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L140-L161] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L178-L203] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L217-L254]

The separate `LngTerminalClient` constructs a pandas table from `_dataset.TERMINALS`, filters it in memory and returns count and capacity totals; it does not load the collector output. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L77-L121]

Engineering sub-models hold hull, pipeline, process, storage and marine attributes; the storage validator computes a missing total capacity, while capacity and timeline analysis summarize records. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L21-L347] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L21-L35] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/timeline_analysis.py:L21-L28]

Use these interfaces for dataset processing, with the limitations in section 6; completeness scoring checks presence rather than independent correctness of values. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/quality_scorer.py:L125-L153]

UNVERIFIED: current real-world dataset completeness, engineering fitness and externally assigned maturity have not been established; issue pending (1).

### Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-15 | Document the pinned collector, processing and query routes and their evidence. |
| 1 | 2026-10-15 | Correct the cache inventory and document cache loss, unit assumptions and other data-loss risks with detection limits. |

## 2. Inputs and outputs

### Inputs

| Name / route | Unit and allowed range | Default | Source and evidence |
| --- | --- | --- | --- |
| `terminal_name`, `country`, `terminal_type`, `function`, `status`, `last_updated` | Text, enumerations and datetime; country is exactly three uppercase letters after stripping and uppercasing, without membership lookup | Required; generated `terminal_id` if empty | `LNGTerminal`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L64-L108] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L176-L204] |
| `latitude`, `longitude` | WGS-84 decimal degrees, latitude -90 to 90, longitude -180 to 180 | `None` | `LNGTerminal`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L85-L96] |
| `capacity_mtpa`, `year_commissioned`, `capex_usd_million` | Million tonnes/year: 0 to 200; year: 1960 to 2040; USD million: nonnegative | `None` | `LNGTerminal`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L109-L137] |
| `hull_design` | LOA 0 to 500 m; beam 0 to 100 m; depth 0 to 50 m; draft 0 to 30 m; displacement nonnegative tonnes | Dimensions `None`; hull type required if model supplied | `HullDesign`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L24-L59] |
| `pipelines` | Diameter 0 to 60 inches; length nonnegative km; thickness 0 to 100 mm; pressure nonnegative barg; temperature degrees Celsius without a numeric bound | Empty list; dimensions `None`; offshore flag false | `PipelineSpec`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L103-L147] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L144-L147] |
| `process_equipment` | Trains 0 to 20; train capacity 0 to 15 MTPA; compressor power nonnegative MW; regasification nonnegative MMSCFD | `None` per optional field | `ProcessEquipment`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L173-L223] |
| `storage` | Tanks 0 to 20; per-tank and total volumes nonnegative cubic metres | `None`; missing total derived when both factors supplied | `StorageSpec`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L251-L289] |
| `marine_infrastructure` | Berth depth 0 to 5000 m; nonnegative counts, loading-arm inches, cubic metres/hour and channel depth metres | Optional fields `None` | `MarineInfrastructure`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L295-L347] |
| Loader file | `.csv`, `.parquet`, `.pq`; field units inherited from model, no general unit conversion in row construction | Source name `curated_seed_dataset` | `TerminalLoader.load` / `_row_to_terminal`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/loaders/terminal_loader.py:L40-L56] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/loaders/terminal_loader.py:L70-L107] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/loaders/terminal_loader.py:L132-L168] |
| Query filters | Lists of regions, country strings, type and status; inclusive min/max MTPA; OR within a list, AND across filters | Every filter `None` | `LngTerminalQuery` / `query`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L18-L40] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L89-L114] |
| Cache / HTTP / matching configuration | Cache age 86400 s; HTTP timeout 30 s, delay 1 s, retry delay 2 s, maximum retries 3; fuzzy threshold 0.85 dimensionless; proximity 50 km | Code defaults, subject to YAML override | `get_config`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/config.py:L31-L76] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/config.py:L97-L114] |

Latitude and longitude are geographic coordinates rather than a local Cartesian frame; the model labels WGS-84 but does not define a local origin, phase convention or vertical datum. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L85-L96] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L295-L300]

UNVERIFIED: the vertical datum for berth/channel depth and the intended interpretation of `boil_off_rate_percent` remain unspecified or ambiguous; the field description calls it a fraction bounded by 0 and 1; issue pending (1). [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L218-L223] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L295-L300] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L339-L343]

### Outputs

| Name / route | Units and representation | Evidence |
| --- | --- | --- |
| `to_flat_dict` / CSV | Scalar units retained; ISO datetime string; nested fields prefixed; at most eight indexed pipeline records; aliases joined by a vertical bar; UTF-8 CSV | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L269-L328] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/csv_exporter.py:L49-L77] |
| Parquet | Same flat fields; object columns coerced to pandas string dtype; PyArrow engine; index omitted | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/parquet_exporter.py:L54-L71] |
| Export metadata JSON | Record counts, timestamp, country set, status/type/region distributions | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/csv_exporter.py:L79-L110] |
| Capacity / timeline summaries | Counts and MTPA grouped by geography/type/status or commissioning year/decade; missing capacity contributes zero; most group totals rounded to two decimal places | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L33-L103] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/timeline_analysis.py:L30-L103] |
| Quality report JSON | Completeness scores 0 to 100 points, counts and distributions; empty unscored list returns an error mapping | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/data_quality.py:L45-L54] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/quality_dashboard.py:L23-L69] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/quality_dashboard.py:L87-L99] |
| HTML map | Geographic coordinates, type groups and capacity-scaled markers; external Plotly script from CDN | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/terminal_map.py:L63-L119] |
| Query result | pandas DataFrame, original query, record count and summed MTPA | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L113-L121] |

## 3. Method and governing standards

| Method | Definition and implementation | Reference status |
| --- | --- | --- |
| Collection and cache | `BaseCollector.collect`: force-cache returns valid nonempty cache or raises; cache-first uses nonempty valid cache; other paths fetch, parse, validate and write cache | Repository algorithm; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L185-L241] |
| Source parsing | FERC maps CSV columns and multiplies Bcf/day by its factor; GIE interprets the selected capacity as million cubic metres/day and annualizes it; GIIGNL parses CSV/PDF tables; web collection uses first regex matches | Repository algorithms; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/ferc_collector.py:L150-L190] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L97-L156] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/giignl_collector.py:L39-L143] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/web_collector.py:L132-L187] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/web_collector.py:L327-L343] |
| Normalization | Country/status/type aliases; Unicode text cleanup; optional region assignment; `bcfd_to_mtpa(x) = x * BCFD_TO_MTPA`, `bcm_to_mtpa(x) = x * BCM_TO_MTPA` | Factors are approximate code constants, not a checked standard; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L21-L25] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L251-L335] |
| Deduplication | Same country, trailing-number exclusion, manual aliases, then bigram Jaccard similarity; coordinate proximity is an additional route; retain most complete member per group | `_is_duplicate`, `_string_similarity`, `_haversine_km`, `deduplicate`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L53-L124] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L148-L217] |
| Enrichment | Match exact terminal IDs; immutable identity fields; concatenate sources/pipelines, union aliases, replace other nonempty values by whole-record maximum source priority; latest timestamp | `_merge_terminals`; despite the sub-model comment, the loop replaces sub-model dictionaries wholesale; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/enricher.py:L17-L37] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/enricher.py:L71-L84] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/enricher.py:L96-L146] |
| Storage | Missing total volume `V = N * v`; supplied total retained without checking consistency | `StorageSpec.compute_total_capacity`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L280-L289] |
| Completeness | Required/optional/engineering category percentages combined with weights 0.50/0.30/0.20; empty category scores 100; round scores to two places | `QualityScore.compute`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/data_quality.py:L57-L122] |
| Aggregation | Sums of populated capacities with missing values treated as zero; commissioning decade uses integer division by ten; planned summary includes planned and construction, excluding proposed | `CapacityAnalysis`, `TimelineAnalysis`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L33-L103] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/timeline_analysis.py:L30-L103] |
| Query | pandas boolean filtering followed by sum and row count; grouped regional summary is a separate direct pandas calculation | `LngTerminalClient.query`, `summary_by_region`; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L89-L144] |

UNVERIFIED: no checked edition, clause or physical basis for the capacity conversion factors or geographic distance constant was established; use them only as implementation assumptions until qualified; issue pending (1). [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L21-L25] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/ferc_collector.py:L51-L52] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L113-L123] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L190-L205]

No standards-derived value is introduced by this pack; the existing `SourceCitation` records source name, URL, access date, sourced fields and reliability rather than a standards clause sidecar. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/data_quality.py:L35-L42]

## 4. Validated worked examples

Evidence record, 2026-10-15: the BASE offline module run at the header code revision passed all 429 tests; no tests failed, skipped or were NOT_RUN. Section-4 results below identify individual nodes from that run.

| Case | Classification / independent basis | Input, expected output and tolerance | Existing node ID | Offline result |
| --- | --- | --- | --- | --- |
| V1 storage multiplication | Validated arithmetic only: closed form total volume equals tank count times equal tank volume, independent of the implementation output | Synthetic inline input: 4 tanks of 160000 cubic metres; 640000 cubic metres; exact equality, 0 cubic metres error for these exactly representable integers | `tests/unit/lng_terminals/models/test_design.py::TestStorageSpec::test_auto_compute_total_capacity` | BASE PASS; AFTER PASS; [tests/unit/lng_terminals/models/test_design.py:L87-L93] |
| R1 capacity aggregation | Regression; repository synthetic fixture and assertion, no external dataset validation | Inline capacities 10.0 and 20.0 MTPA; expected 30.0 MTPA, exact equality | `tests/unit/lng_terminals/test_capacity_timeline.py::TestCapacityAnalysisTotal::test_total_capacity` | BASE PASS; AFTER PASS; [tests/unit/lng_terminals/test_capacity_timeline.py:L40-L47] |
| R2 completeness convention | Regression of configured weights and empty-category convention | All six supplied fields present; required/optional/engineering and total each 100.0 points; source count 3; exact equality | `tests/unit/lng_terminals/models/test_data_quality.py::TestQualityScore::test_compute_all_present` | BASE PASS; AFTER PASS; [tests/unit/lng_terminals/models/test_data_quality.py:L99-L113] |
| R3 cache route | Regression of cache serialization and offline reuse | Warm cache then force-cache; 0 fetches and returned record count exactly equals fixture count | `tests/unit/lng_terminals/test_refresh_modes.py::TestRefreshModeForceCache::test_force_cache_returns_cached_data` | BASE PASS; AFTER PASS; [tests/unit/lng_terminals/test_refresh_modes.py:L260-L273] |
| R4 Parquet row retention | Regression; output reopened by pandas, no independent physical benchmark | Two synthetic inline records; exported and read back count 2 rows; exact equality | `tests/unit/lng_terminals/test_exporters.py::TestParquetExport::test_multiple_terminals` | BASE PASS; AFTER PASS; [tests/unit/lng_terminals/test_exporters.py:L155-L165] |

V1 establishes multiplication on synthetic inputs only; it does not establish terminal data accuracy or a physical design check. [tests/unit/lng_terminals/models/test_design.py:L87-L93]

## 5. QA gates

Gate selection: AQG r0, section 10, Python calculations, with G5 from section 9; the following are pack-specific acceptance checks rather than a claim of external clearance.

| Gate | Applicability | Check ID and executable check | Numeric pass criterion / unit | Evidence and current result |
| --- | --- | --- | --- | --- |
| G0 | Applicable: record inputs, units and evidence | C01 construct `LNGTerminal` with invalid two-letter country and capacity outside model range; require validation rejection; preserve documented units | 0 invalid records accepted, records | Offline schema probe PASS; model constraints [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L109-L119] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L183-L192] |
| G0 | Applicable: reproducibility | C02 hash pinned Python inputs and module tests in sorted relative-path order; recompute source-file digests before/after | 0 source or test digest mismatches, files | Source manifest PASS; cache fixture isolates collector writes [tests/unit/lng_terminals/conftest.py:L8-L15] |
| G1 | Applicable: Python imports and offline tests | C03 run the complete `tests/unit/lng_terminals` directory with `uv run python -m pytest`; importing collectors uses test cache redirection | 429 passed nodes, 0 failures/errors/skips/NOT_RUN, tests | BASE PASS; AFTER PASS; fixture [tests/unit/lng_terminals/conftest.py:L8-L15] |
| G2 | Applicable: independent arithmetic | C04 repeat V1 from its inline input; compare `StorageSpec.total_capacity_m3` with separate multiplication | Absolute error 0 cubic metres for 640000 cubic metres | V1 BASE PASS; AFTER PASS; [tests/unit/lng_terminals/models/test_design.py:L87-L93] |
| G2 | Applicable: missing-capacity convention | C05 run `tests/unit/lng_terminals/test_capacity_timeline.py::TestCapacityAnalysisTotal::test_total_capacity_with_none`, compare one 10.0 MTPA value plus missing capacity with 10.0 | Absolute error 0 MTPA | BASE PASS; AFTER PASS; [tests/unit/lng_terminals/test_capacity_timeline.py:L49-L55] |
| G3 | NOT_APPLICABLE: no time integration in the collector/process/export route | No dynamics check | NOT_APPLICABLE | Pipeline calls data export and reports [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L258-L274] |
| G4 | NOT_APPLICABLE: the route exports tabular records rather than a diffraction model | No diffraction check | NOT_APPLICABLE | CSV and Parquet write flattened rows [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/csv_exporter.py:L49-L69] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/parquet_exporter.py:L54-L65] |
| G5 | Applicable: evidence accompanying this pack | C06 resolve every citation at the pin; require a test node and BASE/AFTER result for every section-4 case; verify manifest | 0 broken citations, citations; 5/5 cases accounted for, cases; 0 digest mismatches, files | Self-check record PASS; report exports alone supply no gate/signature record [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/quality_dashboard.py:L87-L99] |
| G0 | Applicable: tracked cache exposure | C07 run `git ls-files -- 'packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/*_cache.json'` and count paths | 0 tracked collector cache files, files | FAIL at the pin: 5 tracked cache files; test isolation does not untrack them; incident #1209 |
| G1 | Applicable: collector test isolation | C08 run `tests/ci/test_tree_preservation.py::test_collector_cache_redirect_applies_to_new_modules` | 1 passed node, 0 failures, tests | BASE PASS; AFTER PASS; [tests/ci/test_tree_preservation.py:L432-L449] [tests/unit/lng_terminals/conftest.py:L8-L15] |
| G2 | Applicable: conversion arithmetic under the mcm/d assumption | C09 execute the arithmetic probe below; compare Bcf/day conversion factors and GIE annualisation | Factor difference at most 0.1 %; GIE rounding error at most 0.1 MTPA | BASE PASS; AFTER PASS; checks arithmetic only, not source units; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L21-L25] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/ferc_collector.py:L51-L52] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L113-L123] |

C09 executable probe (offline; repository sources and declared dependencies required):

```python
from worldenergydata.lng_terminals.collectors.ferc_collector import (
    _BCFD_TO_MTPA as FERC_BCFD_TO_MTPA,
)
from worldenergydata.lng_terminals.collectors.gie_collector import GIECollector
from worldenergydata.lng_terminals.processors.normalizer import (
    BCM_TO_MTPA,
    BCFD_TO_MTPA as NORMALIZER_BCFD_TO_MTPA,
)

# Hand conversion basis for this comparison, not a qualified physical reference.
expected = 28316847 / 10**9 * 365 * BCM_TO_MTPA
assert FERC_BCFD_TO_MTPA == NORMALIZER_BCFD_TO_MTPA
assert abs(FERC_BCFD_TO_MTPA - expected) / expected * 100 <= 0.1
collector = GIECollector()
try:
    record = collector._parse_record(
        {"name": "Synthetic A", "country": "FRA", "maxCapacity": "100"}
    )
    assert record is not None
    assert abs(record.capacity_mtpa - 100 * 365 / 1000 * BCM_TO_MTPA) <= 0.1
finally:
    collector.client.close()
```

For a production refresh, additionally require a source-qualified dataset revision, input fingerprints, successful scheduler manifest and signed gate evidence; the current scheduler adapter returns skipped with zero records. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/lng_terminals_refresh.py:L33-L54]

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom and cause | Detection / limitation | Incident or follow-up | Evidence |
| --- | --- | --- | --- |
| Collector failure can look like an empty result: missing URL or caught collection error returns empty content; CLI catches further exceptions at debug level | C03 covers existing fallbacks, but no end-to-end source-loss rejection check exists; require nonempty, source-qualified output before accepting freshness | #458 and #462 | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L59-L82] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L85-L124] |
| Cache deserialization failure returns an empty list, and zero-length valid caches are not usable in force-cache mode | C03: existing corrupt-cache and force-cache tests; do not interpret an empty cache as a successful refresh | #462 | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L159-L170] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L201-L215] |
| Tracked-cache incident: test runs rewrote package cache JSON; the default cache directory is inside the package | C07 detects tracked files (5 at the pin, criterion 0); C08 proves test cache redirection, but does not protect CLI or production runs | #1209 | [tests/unit/lng_terminals/conftest.py:L8-L15] [tests/ci/test_tree_preservation.py:L432-L449] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/config.py:L19-L23] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/config.py:L82-L94] |
| Empty-result cache overwrite: collection writes the validated list even when empty; `_write_cache` replaces data and metadata without checking for an earlier nonempty cache | no detection check exists for CLI or production runs; C08 tests isolation only. An empty cache makes CACHE_FIRST refetch and FORCE_CACHE raise; a fresh timestamp alone does not establish source freshness | #1265 | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L125-L157] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L201-L231] |
| GIE unit misread: the comment allows mcm/d or GWh/d, but `maxCapacity` or fallback `dtmi` is always interpreted as mcm/d without reading a unit field | no detection check exists for wrong or unknown source units; C09 checks only the assumed mcm/d arithmetic. A GWh/d value can be mis-scaled and still satisfy model bounds | #1265 | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L113-L123] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L109-L119] |
| Extra pipeline records disappear from flat output after the eighth entry | Diagnostic: construct 9 pipelines and compare input count with indexed output count; current result 9 versus 8; no detection check exists | issue pending (3) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L292-L301] |
| Partial higher-priority engineering sub-model replaces existing sub-model fields rather than filling missing nested fields | Diagnostic: merge matching records with base storage tank count and incoming total only; verify tank count survives; no detection check exists in the shipped tests | issue pending (2) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/enricher.py:L96-L139] |
| Zero latitude or longitude disappears from map selection; GIE also converts a numeric zero coordinate to missing; deduplication bypasses proximity at zero | Diagnostic: construct valid zero-coordinate records and check retained count; no detection check exists in the shipped tests | issue pending (4) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/terminal_map.py:L36-L40] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L158-L166] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L114-L122] |
| Dashboard median uses the upper middle score for an even number of records | Diagnostic: compare generated median with the mean of the central pair; no detection check exists in the shipped tests | issue pending (5) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/quality_dashboard.py:L38-L51] |
| Missing category scores 100 points; source count counts citation objects without distinct-source deduplication | C03 covers the convention; a high score alone does not establish source independence | #462; qualification issue pending (1) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/data_quality.py:L99-L119] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/quality_scorer.py:L150-L153] |
| Scheduler registration is not refresh implementation: enabled job returns skipped and zero records | Detection: inspect adapter result for `success`, positive records and a manifest; no detection check exists that proves this adapter can refresh successfully | #458; #270 is historical configuration work | [config/scheduler/scheduler_config.yml:L59-L63] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/lng_terminals_refresh.py:L33-L54] |
| Query country/type/region encodings differ from model records; query lowercases exact strings without alias translation | C03 covers each interface independently; do not interchange the two datasets as a single canonical source | issue pending (1) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L89-L105] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L77-L108] |
| Incremental collection still calls fresh fetch, without an incremental cursor in the base lifecycle | C03: `tests/unit/lng_terminals/test_refresh_modes.py::TestRefreshModeIncremental::test_incremental_fetches_fresh`; no selective-update guarantee | #462 | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L217-L231] [tests/unit/lng_terminals/test_refresh_modes.py:L290-L308] |
| Deduplication retains one most-complete group member and discards other members' values and citations without merging | no detection check exists for loss of complementary values or citations; C03 tests the existing retention convention | issue pending (7) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L74-L83] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L209-L217] |
| Loader and collector parsers skip invalid records; normalization can retain partial in-place mutation; scoring exceptions leave records unscored, with warnings rather than returned failure counts | no detection check exists for a caller-visible accounting of dropped, partially normalized or unscored records | issue pending (8) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/loaders/terminal_loader.py:L87-L107] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/ferc_collector.py:L99-L105] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L87-L94] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/giignl_collector.py:L153-L156] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/web_collector.py:L122-L125] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L238-L249] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/quality_scorer.py:L104-L108] |
| Alias matching can falsely merge same-country records when stripping generic words leaves an empty name: the empty string is a substring of every alias | no detection check exists for rejecting empty normalized names before alias matching | issue pending (9) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L18-L27] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L129-L146] |
| Enrichment unions aliases through a set, so alias order and serialized CSV bytes can vary between processes | no detection check exists for stable alias ordering across processes | issue pending (10) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/enricher.py:L113-L123] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L269-L274] |
| Total capacity sums import and export capacities across every status; the CLI labels this mixed sum as total capacity | C03 verifies the sum convention, but no detection check exists that prevents interpreting it as operational liquefaction capacity | issue pending (11) | [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L33-L35] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L217-L233] |

Observation date for the diagnostic rows: 2026-10-15; their source locations are pinned above. These are documentation findings, with implementation corrections left to the linked follow-ups.

## 7. Lessons log

| Date | Evidence entry | Lesson | Pack change | Shared entry |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pinned inspection | Keep query data and collector data distinct; enrichment uses whole-record priority and flat export has a fixed pipeline limit | Sections 1, 3 and 6 document the separate routes and loss risks | Shared-log entry pending, issue pending (12); [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L77-L78] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/enricher.py:L103-L132] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L292-L301] |

## 8. Ownership

Proposed review responsibility: calculations quality manager; deputy: an independent calculations reviewer appointed by the maintainers; producing role: data-pipeline maintainer; unresolved evidence, criteria and classification questions go to the quality manager, and cross-family scope questions to the maintainers. (AQG r0, section 11, Sign-off and independence.)

Clearance remains pending; this pack records no reviewer approval. (Pack status: DRAFT.)

## 9. Dependencies and implementation inventory

The package declares shared core, pandas, Pydantic, PyArrow, PyYAML, HTTPX, Beautiful Soup and Typer dependencies; Plotly is loaded when generating maps, and pdfplumber is loaded for PDF extraction. [packages/worldenergydata-lng_terminals/pyproject.toml:L29-L39] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/terminal_map.py:L51-L57] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/giignl_collector.py:L69-L89]

Dataset inputs have separate authorities: `_dataset.TERMINALS` feeds the query client; `_SEED_TERMINALS` feeds `SeedCollector`; the curated file feeds `TerminalLoader`; only `seed_dataset_cache.json` contains serialized model records (119); the FERC, GIE, GIIGNL and web cache files each contain `[]` (0 records, 2 bytes). Their metadata also records 0; cache presence is not evidence of successful collection. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L77-L78] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/seed_collector.py:L1485-L1491] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/loaders/terminal_loader.py:L70-L107] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L125-L148] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/ferc_cache.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/gie_cache.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/giignl_cache.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/web_cache.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/seed_dataset_meta.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/ferc_meta.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/gie_meta.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/giignl_meta.json:L1-L1] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_data/cache/web_meta.json:L1-L1]

The downstream scheduler adapter exists but returns skipped rather than invoking the collector route; no solver-version dependency is involved in that adapter. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/lng_terminals_refresh.py:L33-L54]

### Map inventory and counted families

Map evidence record: repository `digitalmodel`, ref `origin/codex/implmap-work`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, declared data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, file `docs/registry/implementation-map.yaml`; all 13 families and their implementation rows were read programmatically at that ref.

Inventory result: 0 map families have implementation rows under the header package path, so the required implementation inventory is empty, there are 0 counted families, and the counted-family grep is `NOT_APPLICABLE` for that reason; no in-package search signals or path-matching exclusions apply. This is absence of map coverage, not evidence that these methods are unique.

Map follow-up, issue pending (1): add the section-3 families with in-package rows before counting them: collector/cache lifecycle, source parsing, capacity conversion, text/country normalization, fuzzy/geographic deduplication, source-priority enrichment, storage multiplication, completeness scoring, capacity/timeline aggregation and query aggregation.

Map follow-up also covers parallel great-circle calculations in `marine_safety`, `metocean`, `texas_rrc` and `marine`, and record matching/source-priority merge in `vessel_fleet` (#1227); group these by result family rather than treating package-specific symbols as unique. These are map gaps outside this package, not counted-family misses. [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/correlation/matcher.py:L613-L643] [packages/worldenergydata-marine_safety/src/worldenergydata/marine_safety/analysis/incidents/incident_correlator.py:L357-L373] [packages/worldenergydata-metocean/src/worldenergydata/metocean/utils/coordinates.py:L76-L101] [packages/worldenergydata-texas_rrc/src/worldenergydata/texas_rrc/infrastructure/spatial.py:L39-L54] [packages/worldenergydata-marine/src/worldenergydata/marine/vessel_gis.py:L42-L67]

### Repository-wide supplemental search

A supplemental search across tracked Python sources including `scripts/` used `BCFD_TO_MTPA|BCM_TO_MTPA|def _haversine_km|def bcfd_to_mtpa|def bcm_to_mtpa|def _string_similarity|class QualityScore|def compute_total_capacity`; matches were confined to this package. The search is a symbol-oriented follow-up, not the counted-family grep, and does not establish exhaustive uniqueness.

The following direct calculations are already covered in section 3 and must be registered separately; callers that merely delegate or serialize are helpers. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/ferc_collector.py:L170-L178] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L327-L335] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L113-L123] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L113-L144] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L33-L35]

| Result family | Direct implementations | Helper distinction |
| --- | --- | --- |
| Capacity conversion | `Normalizer.bcfd_to_mtpa`, `Normalizer.bcm_to_mtpa`, `FERCCollector._parse_capacity`, `GIECollector._parse_record` | Each computes its own product; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L327-L335] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/ferc_collector.py:L170-L178] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L113-L123] |
| Capacity aggregation | `CapacityAnalysis._total_capacity`, grouped methods, `TimelineAnalysis.planned_capacity`, `LngTerminalClient.query` and `summary_by_region` | Summary methods delegate to their component calculations; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L21-L35] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L37-L103] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/timeline_analysis.py:L79-L103] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L113-L144] |
| Completeness | `QualityScore.compute` | `QualityScorer.score_terminal` constructs field presence and delegates; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/data_quality.py:L82-L122] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/quality_scorer.py:L125-L153] |
| Flat exports | `LNGTerminal.to_flat_dict` | CSV/Parquet exporters delegate flattening and serialize; [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L251-L328] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/csv_exporter.py:L49-L69] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/parquet_exporter.py:L54-L65] |

## 10. Coverage and open items

### Evidence coverage

The following source inventory covers all 35 Python files in the package; code review and schema inspection covered the main collection, model, processing, export and query routes, including the two embedded datasets. The embedded dataset record counts were re-derived by parsing their list expressions: query 44 records and seed collector 119 records; those counts measure embedded entries rather than current terminal coverage. [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_dataset.py:L6-L587] [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/seed_collector.py:L33-L1447]

- `__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/__init__.py:L1-L15]
- `__main__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/__main__.py:L1-L5]
- `_dataset.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/_dataset.py:L1-L587]
- `analysis/__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/__init__.py:L1-L6]
- `analysis/capacity_analysis.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/capacity_analysis.py:L1-L113]
- `analysis/timeline_analysis.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/analysis/timeline_analysis.py:L1-L103]
- `cli.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/cli.py:L1-L283]
- `collectors/__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/__init__.py:L1-L17]
- `collectors/base_collector.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/base_collector.py:L1-L386]
- `collectors/ferc_collector.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/ferc_collector.py:L1-L190]
- `collectors/gie_collector.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/gie_collector.py:L1-L166]
- `collectors/giignl_collector.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/giignl_collector.py:L1-L232]
- `collectors/seed_collector.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/seed_collector.py:L1-L1537]
- `collectors/web_collector.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/collectors/web_collector.py:L1-L343]
- `config.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/config.py:L1-L114]
- `constants.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/constants.py:L1-L103]
- `exceptions.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exceptions.py:L1-L194]
- `exporters/__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/__init__.py:L1-L6]
- `exporters/csv_exporter.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/csv_exporter.py:L1-L119]
- `exporters/parquet_exporter.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/exporters/parquet_exporter.py:L1-L71]
- `loaders/__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/loaders/__init__.py:L1-L5]
- `loaders/terminal_loader.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/loaders/terminal_loader.py:L1-L357]
- `models/__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/__init__.py:L1-L22]
- `models/data_quality.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/data_quality.py:L1-L122]
- `models/design.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/design.py:L1-L347]
- `models/terminal.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/models/terminal.py:L1-L362]
- `processors/__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/__init__.py:L1-L8]
- `processors/deduplicator.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/deduplicator.py:L1-L217]
- `processors/enricher.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/enricher.py:L1-L146]
- `processors/normalizer.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/normalizer.py:L1-L351]
- `processors/quality_scorer.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/processors/quality_scorer.py:L1-L153]
- `query.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/query.py:L1-L144]
- `reports/__init__.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/__init__.py:L1-L6]
- `reports/quality_dashboard.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/quality_dashboard.py:L1-L99]
- `reports/terminal_map.py` [packages/worldenergydata-lng_terminals/src/worldenergydata/lng_terminals/reports/terminal_map.py:L1-L119]

Module tests executed: every collected node in `tests/unit/lng_terminals`, including nested `models` and `reports` tests; 429 passed at BASE, with AFTER results recorded below. Directory collection follows the repository configuration, including its existing directory exclusions. [pyproject.toml:L334-L377]

Test-file inventory:

- `tests/unit/lng_terminals/models/test_data_quality.py` [tests/unit/lng_terminals/models/test_data_quality.py:L1-L172]
- `tests/unit/lng_terminals/models/test_design.py` [tests/unit/lng_terminals/models/test_design.py:L1-L132]
- `tests/unit/lng_terminals/models/test_design_extended.py` [tests/unit/lng_terminals/models/test_design_extended.py:L1-L199]
- `tests/unit/lng_terminals/models/test_terminal.py` [tests/unit/lng_terminals/models/test_terminal.py:L1-L139]
- `tests/unit/lng_terminals/reports/test_quality_dashboard.py` [tests/unit/lng_terminals/reports/test_quality_dashboard.py:L1-L79]
- `tests/unit/lng_terminals/test_analysis.py` [tests/unit/lng_terminals/test_analysis.py:L1-L114]
- `tests/unit/lng_terminals/test_capacity_timeline.py` [tests/unit/lng_terminals/test_capacity_timeline.py:L1-L231]
- `tests/unit/lng_terminals/test_cli.py` [tests/unit/lng_terminals/test_cli.py:L1-L70]
- `tests/unit/lng_terminals/test_config.py` [tests/unit/lng_terminals/test_config.py:L1-L90]
- `tests/unit/lng_terminals/test_constants.py` [tests/unit/lng_terminals/test_constants.py:L1-L105]
- `tests/unit/lng_terminals/test_dedup_numbered.py` [tests/unit/lng_terminals/test_dedup_numbered.py:L1-L116]
- `tests/unit/lng_terminals/test_deduplicator.py` [tests/unit/lng_terminals/test_deduplicator.py:L1-L122]
- `tests/unit/lng_terminals/test_enricher.py` [tests/unit/lng_terminals/test_enricher.py:L1-L90]
- `tests/unit/lng_terminals/test_exceptions.py` [tests/unit/lng_terminals/test_exceptions.py:L1-L129]
- `tests/unit/lng_terminals/test_exporters.py` [tests/unit/lng_terminals/test_exporters.py:L1-L165]
- `tests/unit/lng_terminals/test_ferc_collector.py` [tests/unit/lng_terminals/test_ferc_collector.py:L1-L83]
- `tests/unit/lng_terminals/test_models.py` [tests/unit/lng_terminals/test_models.py:L1-L307]
- `tests/unit/lng_terminals/test_normalizer.py` [tests/unit/lng_terminals/test_normalizer.py:L1-L205]
- `tests/unit/lng_terminals/test_quality_dashboard.py` [tests/unit/lng_terminals/test_quality_dashboard.py:L1-L70]
- `tests/unit/lng_terminals/test_quality_scorer.py` [tests/unit/lng_terminals/test_quality_scorer.py:L1-L101]
- `tests/unit/lng_terminals/test_query.py` [tests/unit/lng_terminals/test_query.py:L1-L280]
- `tests/unit/lng_terminals/test_refresh_modes.py` [tests/unit/lng_terminals/test_refresh_modes.py:L1-L559]
- `tests/unit/lng_terminals/test_seed_collector.py` [tests/unit/lng_terminals/test_seed_collector.py:L1-L111]
- `tests/unit/lng_terminals/test_terminal_loader.py` [tests/unit/lng_terminals/test_terminal_loader.py:L1-L210]
- `tests/unit/lng_terminals/test_terminal_schema.py` [tests/unit/lng_terminals/test_terminal_schema.py:L1-L481]
- `tests/unit/lng_terminals/test_web_collector.py` [tests/unit/lng_terminals/test_web_collector.py:L1-L107]

Documentation discovery used case-insensitive `lng[ _-]?terminals` under `docs/`; the following files were read for module-bearing context. Historical claims were not adopted as current evidence. Full revalidation of their unrelated content is deferred to issue pending (1).

- `docs/CLI.md` [docs/CLI.md:L620-L620]
- `docs/adr/0001-domain-package-split.md` [docs/adr/0001-domain-package-split.md:L48-L48]
- `docs/modules/repository-architecture.md` [docs/modules/repository-architecture.md:L107-L107]
- `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md` [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L19-L19]
- `docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md` [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L15-L15]
- `docs/plans/2026-05-04-issue-270-lng-terminals-scheduler-wire.md` [docs/plans/2026-05-04-issue-270-lng-terminals-scheduler-wire.md:L1-L1]
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21]
- `docs/plans/2026-05-04-issue-360-scheduler-health.md` [docs/plans/2026-05-04-issue-360-scheduler-health.md:L38-L38]
- `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L27-L27]
- `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L49-L49]
- `docs/plans/README.md` [docs/plans/README.md:L19-L19]
- `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L208-L208]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L17-L17]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml` [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L420-L420]
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12]
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml` [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.yaml:L314-L314]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md` [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L34-L34]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L68-L68]
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml` [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L263-L263]
- `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L37-L37]
- `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md` [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L41-L41]
- `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L12-L12]
- `docs/reports/cli-smoke-report-2026-05-11.json` [docs/reports/cli-smoke-report-2026-05-11.json:L168-L168]
- `docs/reports/cli-smoke-report-2026-05-11.md` [docs/reports/cli-smoke-report-2026-05-11.md:L28-L28]
- `docs/reports/data-freshness-scorecard-2026-06-08.md` [docs/reports/data-freshness-scorecard-2026-06-08.md:L13-L13]
- `docs/reports/scheduler-health-2026-W24.md` [docs/reports/scheduler-health-2026-W24.md:L17-L17]

Package README and packaging configuration were also read. The existing recursive Markdown package-data pattern matches this documentation path; wheel exclusion requires packaging follow-up, not a claim that the pack is excluded. [packages/worldenergydata-lng_terminals/README.md:L1-L16] [packages/worldenergydata-lng_terminals/pyproject.toml:L54-L65]

Related cross-cutting test discovery also found scheduler, source-refresh audit and tree-preservation consumers outside this module test directory; full-domain runs are outside the module baseline. The nine LNG scheduler cases and the C08 cache-redirection node were additionally selected for the focused execution record below; the source-refresh audit was not run. [tests/unit/scheduler/test_jobs.py:L15-L15] [tests/unit/audit/test_source_refresh_contract.py:L189-L198] [tests/ci/test_tree_preservation.py:L1-L30]

### Open-item register

Every item is assigned to the maintainers for issue assignment and review; pending numbers refer to the accompanying numbered issue drafts.

| Item | Work remaining | Tracking |
| --- | --- | --- |
| Evidence qualification | Resolve all three `UNVERIFIED:` claims from sections 1 to 3: real-world coverage/maturity/fitness, depth datum and boil-off interpretation, conversion/distance reference basis; add independently versioned real-data examples; complete historical-doc and cross-domain validation; add section-3 method families to the implementation map | issue pending (1) |
| Nested enrichment | Preserve populated nested storage/hull/process/marine fields during partial enrichment; add an explicit data-loss regression | issue pending (2) |
| Export overflow | Reject or preserve pipeline entries beyond eight; test that no entry is silently lost | issue pending (3) |
| Coordinate handling | Preserve valid zero coordinates in GIE parsing, map selection and proximity matching | issue pending (4) |
| Even-sample median | Implement the conventional median or name the upper-middle statistic explicitly; add a two-score case | issue pending (5) |
| Documentation packaging | Exclude this pack from wheel data without removing curated data; verify the built artifact | issue pending (6) |
| Refresh readiness | Replace skipped scheduler result with a source-qualified successful refresh and manifest; retain distinct source-vintage and refresh-time evidence | #458 and #462 |
| Cache overwrite and source units | Preserve a good cache after empty collection; validate GIE capacity units explicitly | #1265 |
| Deduplication data retention | Retain complementary fields and citations from non-selected group members | issue pending (7) |
| Record accounting | Return dropped, partially normalized and unscored counts to callers | issue pending (8) |
| Empty-name alias matching | Reject empty normalized names before substring matching | issue pending (9) |
| Alias ordering | Make alias union order stable across processes | issue pending (10) |
| Mixed capacity total | Label import/export and status scope explicitly | issue pending (11) |
| Shared lesson | Add the cache-loss and unit-assumption findings to the shared lessons log | issue pending (12) |

### Test execution record

BASE: `uv run python -m pytest tests/unit/lng_terminals -q -rA -p no:cacheprovider --basetemp=<scratch>`; ordinary workspace sources, repository addopts unchanged; code revision `285d65c40896b17ccf44568e59f5b789d59c943e`; 429 run, 429 passed, 0 failed, 0 skipped, 0 NOT_RUN.

AFTER: same test form and code revision; the documented `--allow-existing-tree-changes` option preserved and compared the existing pack bytes; 429 run, 429 passed, 0 failed, 0 skipped, 0 NOT_RUN. Every individual node outcome matched BASE. Checks ran against the uncommitted documentation tree; no implementation file changed. [docs/development/index.md:L56-L60]

Contracts: `uv run python -m pytest tests/contracts -q -rA -p no:cacheprovider --basetemp=<scratch> --allow-existing-tree-changes`; ordinary workspace sources and unchanged addopts; 46 run, 46 passed, 0 failed, 0 skipped, 0 NOT_RUN at the same code revision.

Initial self-check record: A1 through A8 passed the producer checks; citation resolution covered every repository citation, with ten selected citations additionally read against pinned source text. All five example nodes passed at BASE and AFTER, the source/test manifest contained 65 files with zero byte mismatches, and the publication/name scan had zero findings. A7 uses pending draft numbers until issue numbers are assigned; A8 inventory is empty and its counted-family grep is `NOT_APPLICABLE`. These are producer results, not independent clearance.

Documentation revision 1 checks: BASE at `9ea85ef95440fb5c4fe87915a530770812f003cc`, AFTER on the uncommitted documentation tree. The complete module directory passed 429/429 at BASE and AFTER, with 0 failed, skipped or NOT_RUN. The focused consumer selection passed 10/10 at BASE and AFTER (nine `LngTerminalsRefreshJob` cases plus C08); 68 unrelated scheduler cases were deselected. C09 passed at BASE and AFTER; the two Bcf/day factors agree within 0.1 %, and 100 mcm/d gives 26.8 MTPA. These checks establish arithmetic under the assumed units, not unit correctness or physical qualification.

Execution form: `uv run --no-project --with pytest python -m pytest <selection> -q -rA -p no:cacheprovider --basetemp=<scratch>` with the required declared dependencies supplied, root and workspace package sources on `PYTHONPATH`, unchanged repository addopts, and coverage outputs redirected to scratch. AFTER used `--allow-existing-tree-changes` to compare the pre-existing documentation bytes. The consumer selection was `tests/unit/scheduler/test_jobs.py tests/ci/test_tree_preservation.py::test_collector_cache_redirect_applies_to_new_modules -k 'LngTerminalsRefreshJob or test_collector_cache_redirect_applies_to_new_modules'`. Initial collection errors from missing dependencies were resolved before counting results.

Revision 1 self-check: all 266 citation occurrences (234 distinct ranges, 111 files) resolve at the header code pin; the 56 occurrences on changed lines (51 distinct ranges) were additionally read for claim support. All 65 source/test manifest entries match BASE and the initial bytes. C07 reports the pre-existing 5 tracked collector cache files against a criterion of 0; this documented exposure remains unresolved by test isolation. A5 producer check: the tracked-cache incident, empty-result overwrite and GIE unit assumption each have a section-6 row with a section-5 detection check or an explicit detection gap. Independent clearance remains pending.
