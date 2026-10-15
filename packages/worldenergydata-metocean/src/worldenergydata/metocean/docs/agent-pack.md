# Metocean module knowledge pack

| Header | Value |
| --- | --- |
| Module | metocean |
| Repository | worldenergydata |
| Path | `packages/worldenergydata-metocean/src/worldenergydata/metocean` |
| Pack revision | 0 |
| Code revision | `a8b26875c1d94a138456fbd885043f43307b73b3` |
| Analysis family | Data pipeline; Python calculations gate set, AQG r0 §10 |
| Quality manager role | Calculations quality manager; data pipeline coverage provisional |
| Status | DRAFT |

## 1. Purpose and scope

The public interface exports observation clients, configuration, quality filtering, unit conversion, caching, database models and NDBC analysis helpers. [packages/worldenergydata-metocean/src/worldenergydata/metocean/__init__.py:L11-L109]
The detailed path covered here is NDBC text ingestion, typed observations, normalization and offline scatter statistics; the facade delegates retrieval to the NDBC client and re-exports pure analysis functions. [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc.py:L34-L47]
The analysis helpers perform no network or database operations; the client path performs HTTP requests through `httpx.Client`. [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L14-L29] [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/base_client.py:L97-L102]
Open-Meteo uses coordinate queries; its station query returns an empty result and its station-based realtime method raises `NotImplementedError`. [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/open_meteo_client.py:L151-L177] [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/open_meteo_client.py:L313-L334]
The package declares an Alpha development classifier; this is package metadata, not evidence of engineering validation. [packages/worldenergydata-metocean/pyproject.toml:L15-L23]
UNVERIFIED: a qualified geographic, water-depth and design-use envelope has not been established by an independent benchmark; coverage item C1.

## 2. Inputs and outputs

### Inputs

| Input | Unit and range | Default / source | Evidence |
| --- | --- | --- | --- |
| NDBC station selection | Longitude/latitude in decimal degrees; bounding tuple ordered longitude minimum, longitude maximum, latitude minimum, latitude maximum | `bbox=None`, `active_only=True`; XML feed | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/ndbc_client.py:L141-L166] |
| NDBC standard text | Timestamp columns then wind direction, speed, gust, Hs, dominant/average period, wave direction, pressure, temperatures, visibility, pressure tendency and tide | Text; missing sentinels become `None` | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L44-L113] |
| Native NDBC observation | Speeds m/s; wave height m; periods s; temperatures Celsius; pressure hPa; visibility nautical miles; water level feet | Optional measurements default `None` | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/ndbc_client.py:L64-L108] |
| Scatter records | `hs` in m, `tp` in s; bins must be supplied in those units | Hs edges 0–10 m by 1 m; Tp edges 0–20 s by 2 s; `normalize=False` | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L33-L36] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L163-L189] |
| Harmonizer quality option | Boolean, dimensionless | `apply_quality_checks=True` | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_harmonizer.py:L219-L227] |
| Open-Meteo forecast query | Documented latitude −90 to 90 degrees and longitude −180 to 180 degrees; forecast days clamped to 1–16 days | 7 days; listed hourly variables; GMT request | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/open_meteo_client.py:L179-L217] |
| HTTP settings | Timeout and retry delay in s; counts dimensionless | Timeout 30 s, 3 retries, retry delay 5 s, request spacing 1 s | [packages/worldenergydata-metocean/src/worldenergydata/metocean/config.py:L53-L64] |
| Licensed CSV input | String cells; names, types and units described by schema, rather than type-converted by loader | Explicit external file takes precedence over configured external directory | [packages/worldenergydata-metocean/src/worldenergydata/metocean/licensed_tables.py:L26-L34] [packages/worldenergydata-metocean/src/worldenergydata/metocean/licensed_tables.py:L52-L71] |

### Outputs

| Output | Units / format / default | Consumer and evidence |
| --- | --- | --- |
| `FetchResult` | Data list, source, fetch timestamp, record count, `had_errors=False`, error list | Fetch consumers must inspect both count and errors. [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/base_client.py:L33-L60] |
| Parsed stdmet dictionary | Timestamp plus `hs`, `dpd`, `apd` and native column keys; optional values are `None` | This format has no `tp` alias; adapt `dpd` explicitly before scatter use. [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L97-L113] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L191-L195] |
| `HarmonizedObservation` | Heights m, speed m/s, Celsius, hPa, direction degrees; optional coordinates and values; ISO timestamp in `to_dict` | Typed storage/serialization representation. [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_harmonizer.py:L29-L122] |
| Unified long table | `timestamp`, `parameter`, `value`, `source`, `unit`; Hs m, Tp/Tm s, speeds m/s, direction degrees | Separate representation from `HarmonizedObservation`; mapped attributes and explicit unit strings. [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L30-L87] [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L129-L160] |
| Scatter matrix | Floating count array, or dimensionless probability when normalized; shape `(len(hs_bins)-1, len(tp_bins)-1)` | Invalid or out-of-bin pairs are omitted. [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L163-L213] |
| Weibull parameters | Shape dimensionless, scale and optional location in input height units | Two parameters fix location at zero; at least 3 samples and parameter count 2 or 3 required. [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L249-L288] |
| CSV | UTF-8 text, configured columns and optional quality flag; returned count in records | Values retain harmonized units; timestamp default format omits timezone offset. [packages/worldenergydata-metocean/src/worldenergydata/metocean/exporters/csv_exporter.py:L57-L88] [packages/worldenergydata-metocean/src/worldenergydata/metocean/exporters/csv_exporter.py:L128-L145] |
| NDBC facade cache | Parquet with native stdmet column names and units | Nonempty observations are cached; cache hits return without a freshness check in this function. [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc.py:L122-L141] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc.py:L162-L191] |

The observation docstrings call timestamps UTC, but the stdmet parser constructs a timezone-naive `datetime`; this is a representation convention, not automatic timezone conversion. [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/ndbc_client.py:L74-L90] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L80-L98]
Wave and wind directions in the harmonized record are documented as degrees **from**; the converter offers a separate `(direction + 180) modulo 360` transformation to degrees **to**. [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_harmonizer.py:L47-L54] [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/unit_converter.py:L386-L402]
UNVERIFIED: a common geodetic datum, elevation origin, current-direction sense and phase convention across every source have not been qualified; coverage item C1.

## 3. Method and governing standards

| Operation | Implemented method and limits | Basis |
| --- | --- | --- |
| Parsing | Whitespace columns, short/header/invalid-time rows omitted, missing and nonnumeric values mapped to `None`; two-digit years split at 50 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L62-L113] |
| NDBC normalization | Copies native measurements, converts tide feet to m, wraps wind/wave direction and optionally applies quality checks | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_harmonizer.py:L249-L281] |
| Unit conversion | Multiplication by stored speed, length and pressure factors; temperature affine conversions; direction modulo 360 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/unit_converter.py:L85-L105] [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/unit_converter.py:L258-L267] [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/unit_converter.py:L370-L402] |
| Quality range/spike checks | Inclusive limits; missing and unknown parameters can return a passing result; spike rate uses a minimum interval | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L94-L128] [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L187-L206] |
| Wave consistency | Deep-water wavelength approximation and a steepness threshold; the implementation does not identify a governing publication for these constants | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L248-L282] |
| Scatter | Right-sided insertion into bin edges; only pairs inside both bin ranges count; optional division by included total | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L184-L213] |
| Seasonal filter | Calendar-month membership of a datetime column, returning a copy | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L221-L241] |
| Weibull fit | SciPy `weibull_min.fit`; fixed zero location for two parameters | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L270-L288] |
| Directional breakdown | Wrap direction, group equally spaced sectors, compute per-sector arithmetic mean Hs and record frequency | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L302-L360] |
| Time alignment | Groups by parameter/source/unit; keeps first duplicate timestamp; continuous interpolation uses pandas `linear`, directions use forward-fill/backward-fill | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L302-L338] |
| Retry handling | Retry delays multiply the configured delay by retry count; this is linear backoff, despite the exponential-backoff docstring | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/base_client.py:L130-L134] [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/base_client.py:L169-L219] |
| Statistics backend | Joint probability imports `metocean_stats.stats` unconditionally; a docstring version is not a verified installed-version pin | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/joint_probability.py:L1-L18] |

The data documentation names API RP 2MET, *Derivation of Metocean Design and Operating Conditions*; edition and table titles remain incomplete in that documentation, and clause text was not checked against the licensed copy. [data/modules/metocean/README.md:L20-L23]
The external-table loader enforces column order and row width and refuses repository-local inputs, including resolved symlinks; it returns string cells rather than validating numeric engineering ranges. [packages/worldenergydata-metocean/src/worldenergydata/metocean/licensed_tables.py:L52-L71]
UNVERIFIED: the independent basis of conversion factors, quality thresholds and broader statistics formulas, together with calculation-citation sidecar coverage, requires separate qualification; coverage item C2.

## 4. Validated worked examples

Validated engineering benchmarks: **0**; the cases below exercise synthetic or repository fixture expectations and are retained as regression examples, without asserting independent physical qualification. [tests/test_ndbc.py:L82-L97] [tests/unit/metocean/test_clients.py:L30-L52]

| Case | Source / input | Expected value and tolerance basis | Existing test node ID | Offline result at code revision |
| --- | --- | --- | --- | --- |
| REG-1 scatter tally | Three literal Hs/Tp pairs in the test; repository expectation, with a separate hand tally in G2 | 3 included records, exact integer equality | `tests/test_ndbc.py::test_scatter_matrix_counts_without_normalization` | PASS before and after. [tests/test_ndbc.py:L89-L97] |
| REG-2 probability sum | Two literal pairs in the test; repository invariant | Dimensionless total 1.0; absolute error below 0.000001 as asserted | `tests/test_ndbc.py::test_scatter_matrix_normalization` | PASS before and after. [tests/test_ndbc.py:L82-L86] |
| REG-3 native text parsing | Embedded standard-text fixture, no remote request | One observation, wave height 1.2 m and dominant period 8.0 s; exact literal equality | `tests/unit/metocean/test_clients.py::TestNDBCClient::test_parse_realtime_data` | PASS before and after. [tests/unit/metocean/test_clients.py:L30-L52] |
| REG-4 foot conversion | Literal 1 foot; stored conversion expectation, no independent source opened | 0.3048 m; absolute error below 0.001 m as asserted | `tests/unit/metocean/processors/test_unit_converter.py::TestLengthConversion::test_ft_to_m` | PASS before and after. [tests/unit/metocean/processors/test_unit_converter.py:L90-L92] |
| REG-5 missing-value flag | Literal missing wave height | One MISSING flag and passing check result, exact categorical equality | `tests/unit/metocean/processors/test_quality_filter.py::TestCheckRange::test_none_value_returns_missing` | PASS before and after. [tests/unit/metocean/processors/test_quality_filter.py:L27-L31] |
| REG-6 scheduler output | Mocked forecast and temporary output directory | 1 updated record, stored wave height 1.2 m, one forecast call | `tests/unit/scheduler/test_metocean_adapter.py::test_metocean_writes_forecast_parquet_for_configured_locations` | PASS before and after. [tests/unit/scheduler/test_metocean_adapter.py:L38-L65] |

## 5. QA gates

Use the Python calculations family mapping: G0 inputs/units/citations, G1 imports/tests, G2 hand/published check; G3 and G4 do not apply, and G5 applies to the evidence record. (AQG r0, §§5, 9–11, Python calculations row.)

These are proposed repeatable checks, not clearance signatures; diagnostic failures below remain open in section 10.

| Gate | Applicability | Check IDs |
| --- | --- | --- |
| G0 | APPLICABLE: input units, record contracts, time and provenance | MET-01, MET-04, MET-05, MET-06, MET-07, MET-08, MET-09 |
| G1 | APPLICABLE: Python import and offline test results | MET-02 |
| G2 | APPLICABLE: independent hand tally of synthetic scatter inputs | MET-03 |
| G3 | NOT_APPLICABLE: Python data transformations do not run time-domain dynamics in this scope | None; AQG r0 §10 |
| G4 | NOT_APPLICABLE: this scope contains no diffraction body or mesh calculation | None; AQG r0 §10 |
| G5 | APPLICABLE: traceable evidence and complete result accounting | MET-10 |

| ID / gate | Executable check | Numeric pass criterion and unit | Evidence and observed status |
| --- | --- | --- | --- |
| MET-01 / G0 | Run REG-3, REG-4 and REG-5; inspect source-native versus harmonized unit mapping | 0 failed assertions; length error less than 0.001 m | PASS for these fixtures; missing input can carry a passing quality result. [tests/unit/metocean/processors/test_unit_converter.py:L90-L92] [tests/unit/metocean/processors/test_quality_filter.py:L27-L31] |
| MET-02 / G1 | Execute the offline test-file inventory with collection errors reported and compare node outcomes before/after | 0 newly failing or missing test nodes; absolute health additionally requires 0 collection errors | No introduced failures; absolute health NOT_RUN for 7 statistics modules due to `ModuleNotFoundError: No module named 'metocean_stats'`; existing CLI skip is separate. [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/joint_probability.py:L14-L18] [tests/unit/metocean/test_cli.py:L14-L18] |
| MET-03 / G2 | Hand-count REG-1 pairs: first bin has 2 records, second has 1; total 2 + 1 = 3; compare REG-1 and REG-2 | Count error 0 records; probability-sum error below 0.000001 dimensionless | PASS; arithmetic checks counting only, not physical sea-state modelling. [tests/test_ndbc.py:L82-L97] |
| MET-04 / G0 | Parse REG-3-like text and feed the returned dictionary directly to scatter; compare included pair count with valid wave-pair count | Lost valid pairs 0 records | FAIL at the pin: parser emits `dpd`, scatter reads `tp`; issue pending (3). [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L97-L113] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L191-L195] |
| MET-05 / G0 | Harmonize a timezone-aware observation with a nonzero UTC offset; compare output instant after UTC conversion | Timestamp shift 0 s | FAIL at the pin: `tz_localize(None)` removes the offset without UTC conversion; issue pending (5). [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L129-L135] |
| MET-06 / G0 | Call batch harmonization with one record and an unsupported source; require an error or accounted rejected record | Unaccounted losses 0 records | FAIL at the pin: broad exception suppression returns an empty list; issue pending (4). [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_harmonizer.py:L460-L489] |
| MET-07 / G0 | Compare quality-filter acceptance with database pressure constraint over their boundary interval | Accepted-but-unpersistable inputs 0 records | FAIL at the pin: the quality-filter upper pressure bound exceeds the database bound; issue pending (6). [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L72-L83] [packages/worldenergydata-metocean/src/worldenergydata/metocean/database/models.py:L223-L225] |
| MET-08 / G0 | Check each calendar month against the facade's constructed end date, without calling HTTP | Invalid end dates 0 dates per year | FAIL at the pin: the end date uses day 31 for every explicit month; issue pending (8). [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc.py:L131-L133] |
| MET-09 / G0 | Compare documented nearest-neighbour direction alignment with a target hour closer to the later sample | Angular error 0 degrees relative to the nearest sample | FAIL at the pin: the implementation forward-fills before backward-filling; issue pending (5). [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L278-L282] [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L319-L324] |
| MET-10 / G5 | Resolve every citation against the pin; map every section-4 node to a saved offline outcome and input-defining source | Missing citation spans 0; missing case outcomes 0; accounted examples 100 % | PASS for this draft's local evidence; independent clearance remains pending. [tests/test_ndbc.py:L82-L97] [tests/unit/scheduler/test_metocean_adapter.py:L38-L65] |

## 6. Known failure modes and pitfalls

| Symptom (silent failures first) | Cause / detection | Incident or follow-up / date | Evidence |
| --- | --- | --- | --- |
| Parsed wave pairs contribute no scatter counts | `dpd`/`tp` contract mismatch; MET-04; no existing end-to-end detection test identified | issue pending (3); observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L97-L113] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L191-L195] |
| Batch input disappears without error | Exceptions, including unsupported-source errors, are caught; MET-06 | issue pending (4); observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_harmonizer.py:L460-L489] |
| Missing file or malformed text produces empty/partial data | Parser returns empty on absent/unreadable file and ignores malformed rows; compare accepted count with input row count | issue pending (1); observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L62-L95] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L132-L155] |
| Timezone-offset data shifts instant | Offset stripped without conversion; MET-05; no existing offset-conversion detection test identified | issue pending (5); observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L129-L135] [tests/unit/metocean/unified/test_harmonizer.py:L155-L161] |
| Direction alignment differs from documented nearest neighbour | Forward-fill/backward-fill is used; MET-09 | issue pending (5); observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L278-L282] [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L319-L324] |
| Quality-accepted pressure cannot satisfy persistence constraint | Upper bounds disagree; MET-07; no existing cross-layer detection test identified | issue pending (6); observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L72-L83] [packages/worldenergydata-metocean/src/worldenergydata/metocean/database/models.py:L223-L225] |
| Explicit monthly facade request raises before retrieval | Month endpoint constructed with day 31; MET-08 | issue pending (8); observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc.py:L131-L133] |
| Cache hit does not establish freshness | Facade returns cached Parquet immediately; no detection check exists for expiry in this facade | #462; observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc.py:L122-L139] |
| Synchronized retries / inaccurate backoff description | Linear delays without jitter; static detection is absence of randomized delay in retry branches; no runtime jitter detection check exists | #431; observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/base_client.py:L169-L219] |
| Scheduler's success can include failed locations | Success depends on some records being written; failures remain in error text; detection is the existing partial-failure test | #268; observed 2026-10-15 | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/metocean_refresh.py:L69-L92] [tests/unit/scheduler/test_metocean_adapter.py:L68-L91] |
| Statistics cannot collect; CLI coverage absent | Missing unconditional backend dependency; CLI test module explicitly skips itself; MET-02 | issue pending (2), #349; observed 2026-10-15 | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/joint_probability.py:L14-L18] [tests/unit/metocean/test_cli.py:L14-L18] |

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Pack revision 0 | Keep ingestion dictionaries and scatter dictionaries distinct; do not equate a quality check's Boolean with complete input | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L97-L113] [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L191-L195] [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L110-L118] | Sections 2, 5 and 6 | Pending maintainer entry, issue pending (1) |

## 8. Ownership

Proposed review responsibility: calculations quality manager; deputy to be designated by the maintainer; producing role: documentation contributor; escalation: maintainer for unresolved qualification and missing evidence.
Independent clearance and reviewer signatures are required before treating the draft as cleared. (AQG r0, §11, Sign-off and independence.)

## 9. Dependencies

| Relationship | Code evidence | Inventory qualification |
| --- | --- | --- |
| Upstream shared core | Logging and data-root resolver imports. [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L17-L22] [packages/worldenergydata-metocean/src/worldenergydata/metocean/config.py:L9-L12] | Package dependency declared. [packages/worldenergydata-metocean/pyproject.toml:L29-L48] |
| HTTP, numeric, dataframe, plotting, SQL and configuration libraries | Declared dependencies include httpx, numpy, pandas, scipy, plotly, SQLAlchemy, pydantic and pydantic-settings. [packages/worldenergydata-metocean/pyproject.toml:L29-L42] | Version ranges are declarations, not an independently validated compatibility matrix. [packages/worldenergydata-metocean/pyproject.toml:L29-L42] |
| Statistics backend | Unconditional `metocean_stats` import. [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/joint_probability.py:L14-L18] | Not declared in this member's dependency list; issue pending (2). [packages/worldenergydata-metocean/pyproject.toml:L29-L42] |
| Observation sources | NDBC and Open-Meteo clients delegate to the shared HTTP base. [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/ndbc_client.py:L133-L139] [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/open_meteo_client.py:L143-L149] | Live availability and source rights are outside the offline evidence; #462. |
| Downstream scheduler | Uses `OpenMeteoClient`, serializes forecast/source/fetch timestamps and writes Parquet. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/metocean_refresh.py:L94-L119] | Scheduler integration has mocked tests, not a live refresh claim. [tests/unit/scheduler/test_metocean_adapter.py:L38-L65] |

Dependency inventory-row reconciliation and a complete downstream-consumer audit remain coverage item C3, issue pending (1).

## 10. Coverage and open items

| Item | Coverage gap / next action | Responsibility | Tracking |
| --- | --- | --- | --- |
| C1 | Qualify both UNVERIFIED claims in sections 1 and 2: design-use envelope, coordinate datum/origin, current-direction/phase convention and source time/units contracts | Maintainer | issue pending (1) |
| C2 | Qualify the UNVERIFIED claim in section 3: independent conversion/QC/statistics basis and citation sidecars; complete API RP 2MET edition and table-title references without reproducing licensed values | Maintainer | issue pending (1) |
| C3 | Resolve the empty initializer line-evidence limitation and complete detailed review of the inventoried secondary clients, CLI, storage, exporters, extrapolation, statistics, examples and remaining docs/tests; add independently sourced engineering examples and dependency inventory rows, designate the deputy reviewer and record the shared lesson entry | Maintainer | issue pending (1) |
| C4 | Restore statistics test collectability; record actual compatible backend versions and re-run 102 declared statistics test functions | Maintainer | issue pending (2) |
| C5 | Correct parser/scatter record compatibility and add end-to-end detection | Maintainer | issue pending (3) |
| C6 | Account for failed batch records and unsupported sources | Maintainer | issue pending (4) |
| C7 | Resolve offset conversion and nearest-neighbour documentation/implementation mismatch | Maintainer | issue pending (5) |
| C8 | Reconcile quality acceptance with persistence constraints | Maintainer | issue pending (6) |
| C9 | Reconcile documentation-only intent with the recursive Markdown package-data glob; no packaging setting changed here | Maintainer | issue pending (7) |
| C10 | Correct calendar-month endpoints in the facade | Maintainer | issue pending (8) |
| C11 | Complete live source freshness/rights/acceptance evidence and facade cache-expiry detection; 11 network-dependent test functions NOT_RUN | Maintainer | #462 |
| C12 | Update the explicitly skipped CLI tests and avoid treating skipped tests as validation | Maintainer | #349 |
| C13 | Address linear backoff without jitter and its inaccurate description | Maintainer | #431 |

The external-table documentation explicitly leaves edition and table titles incomplete; no licensed table values or licensed text were used for this pack. [data/modules/metocean/README.md:L20-L23]
The current package-data glob includes nested Markdown; this pack can consequently be included in built wheels until C9 is resolved. [packages/worldenergydata-metocean/pyproject.toml:L63-L64]

### Test inventory and execution record

Recorded execution uses ordinary `uv run python -m pytest`, the repository-documented `--noconftest` form, `-q -rA -p no:cacheprovider`, explicit scratch basetemp and coverage destinations; configured addopts were retained.
The first broad BASE command stopped at collection: 0 executed, 0 passed, 0 failed test calls, 1 skipped module, 7 collection errors; collected tests were NOT_RUN by that command.
The explicit offline-file command adds `--continue-on-collection-errors` to execute collectable tests while preserving every collection error; it excludes the live API integration file from offline scope, rather than modifying tests or markers. [tests/unit/metocean/test_integration.py:L1-L14]
Before and after at the header revision: **685 executed / 685 passed / 0 failed calls / 1 skipped module / 7 collection errors**; **102 statistics test functions NOT_RUN** for `ModuleNotFoundError: No module named 'metocean_stats'`, and **11 live API integration functions NOT_RUN** because network fetching is outside offline scope. [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/joint_probability.py:L14-L18] [tests/unit/metocean/test_cli.py:L14-L18] [tests/unit/metocean/test_integration.py:L1-L14]
The static inventory contains 784 test-function declarations across 37 files in the selected scope; two eight-way parameterized licensed-table tests add 14 cases, giving 798 potential cases, including 53 cases from the NDBC facade and scheduler test files outside the module test folder. [tests/unit/metocean/test_licensed_tables.py:L15-L24] [tests/unit/metocean/test_licensed_tables.py:L48-L75]
These are distinct measures: the module test folder contributes 745 potential cases, the NDBC facade file 50 and the scheduler adapter file 3; the observed 685 passing cases do not establish that all 798 potential cases ran.

### Source coverage inventory

Complete reading is distinguished from partial reading and inventory-only scanning; the latter remain C3, issue pending (1).

| File at the pin | Reading scope | Evidence |
| --- | --- | --- |
| `__init__.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/__init__.py:L1-L187] |
| `cache/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cache/__init__.py:L1-L18] |
| `cache/cache_manager.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cache/cache_manager.py:L1-L460] |
| `cache/offline_store.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cache/offline_store.py:L1-L489] |
| `cli.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cli.py:L1-L265] |
| `cli_cache.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cli_cache.py:L1-L99] |
| `cli_db.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cli_db.py:L1-L102] |
| `cli_export.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cli_export.py:L1-L199] |
| `cli_fetch.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cli_fetch.py:L1-L347] |
| `cli_stations.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cli_stations.py:L1-L271] |
| `cli_utils.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/cli_utils.py:L1-L143] |
| `clients/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/__init__.py:L1-L61] |
| `clients/base_client.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/base_client.py:L1-L340] |
| `clients/coops_client.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/coops_client.py:L1-L816] |
| `clients/erddap_client.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/erddap_client.py:L1-L570] |
| `clients/met_norway_client.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/met_norway_client.py:L1-L516] |
| `clients/ndbc_client.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/ndbc_client.py:L1-L617] |
| `clients/open_meteo_client.py` | Partial reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/clients/open_meteo_client.py:L1-L503] |
| `config.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/config.py:L1-L238] |
| `constants.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/constants.py:L1-L281] |
| `database/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/database/__init__.py:L1-L50] |
| `database/db_manager.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/database/db_manager.py:L1-L367] |
| `database/init_db.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/database/init_db.py:L1-L338] |
| `database/models.py` | Partial reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/database/models.py:L1-L628] |
| `exceptions.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/exceptions.py:L1-L334] |
| `exporters/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/exporters/__init__.py:L1-L21] |
| `exporters/csv_exporter.py` | Partial reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/exporters/csv_exporter.py:L1-L300] |
| `exporters/json_exporter.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/exporters/json_exporter.py:L1-L338] |
| `exporters/netcdf_exporter.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/exporters/netcdf_exporter.py:L1-L402] |
| `extrapolation/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/extrapolation/__init__.py:L1-L288] |
| `extrapolation/models.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/extrapolation/models.py:L1-L282] |
| `extrapolation/source_catalog.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/extrapolation/source_catalog.py:L1-L329] |
| `extrapolation/spatial.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/extrapolation/spatial.py:L1-L233] |
| `extrapolation/visualization.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/extrapolation/visualization.py:L1-L170] |
| `licensed_tables.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/licensed_tables.py:L1-L71] |
| `ndbc.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc.py:L1-L204] |
| `ndbc_analysis.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/ndbc_analysis.py:L1-L370] |
| `processors/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/__init__.py:L1-L48] |
| `processors/data_fusion.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_fusion.py:L1-L829] |
| `processors/data_harmonizer.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/data_harmonizer.py:L1-L619] |
| `processors/quality_filter.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/quality_filter.py:L1-L416] |
| `processors/unit_converter.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/processors/unit_converter.py:L1-L402] |
| `statistics/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/__init__.py:L1-L69] |
| `statistics/environmental_contours.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/environmental_contours.py:L1-L283] |
| `statistics/eva.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/eva.py:L1-L418] |
| `statistics/examples/__init__.py` | Inventory scan; detailed reading open | UNVERIFIED: line-level evidence unavailable for the empty initializer; C3 |
| `statistics/examples/gom_example.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/examples/gom_example.py:L1-L152] |
| `statistics/examples/north_sea_example.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/examples/north_sea_example.py:L1-L181] |
| `statistics/joint_probability.py` | Partial reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/joint_probability.py:L1-L269] |
| `statistics/reporting.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/reporting.py:L1-L301] |
| `statistics/scatter_diagram.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/scatter_diagram.py:L1-L167] |
| `statistics/wave_spectra.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/wave_spectra.py:L1-L242] |
| `statistics/weather_windows.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/statistics/weather_windows.py:L1-L244] |
| `unified/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/__init__.py:L1-L29] |
| `unified/coverage.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/coverage.py:L1-L108] |
| `unified/dashboard.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/dashboard.py:L1-L391] |
| `unified/harmonizer.py` | Complete reading | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/harmonizer.py:L1-L361] |
| `unified/unified_query.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/unified/unified_query.py:L1-L460] |
| `utils/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/utils/__init__.py:L1-L50] |
| `utils/coordinates.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/utils/coordinates.py:L1-L269] |
| `utils/validators.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/utils/validators.py:L1-L290] |
| `well_datasets/__init__.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/well_datasets/__init__.py:L1-L27] |
| `well_datasets/planetswe_loader.py` | Inventory scan; detailed reading open | [packages/worldenergydata-metocean/src/worldenergydata/metocean/well_datasets/planetswe_loader.py:L1-L125] |

### Test-file inventory

The inventory below records test-function declarations, rather than pretending that uncollected parameterizations were executed.

| File | Declared test functions | Execution scope | Evidence |
| --- | --- | --- | --- |
| `tests/unit/metocean/cache/test_offline_store.py` | 25 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/cache/test_offline_store.py:L1-L206] |
| `tests/unit/metocean/clients/test_coops_client.py` | 16 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/clients/test_coops_client.py:L1-L221] |
| `tests/unit/metocean/exporters/test_csv_exporter.py` | 18 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/exporters/test_csv_exporter.py:L1-L196] |
| `tests/unit/metocean/exporters/test_json_exporter.py` | 24 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/exporters/test_json_exporter.py:L1-L261] |
| `tests/unit/metocean/extrapolation/test_extrapolation.py` | 26 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/extrapolation/test_extrapolation.py:L1-L247] |
| `tests/unit/metocean/extrapolation/test_models.py` | 33 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/extrapolation/test_models.py:L1-L286] |
| `tests/unit/metocean/extrapolation/test_source_catalog.py` | 24 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/extrapolation/test_source_catalog.py:L1-L197] |
| `tests/unit/metocean/extrapolation/test_spatial.py` | 17 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/extrapolation/test_spatial.py:L1-L221] |
| `tests/unit/metocean/processors/test_quality_filter.py` | 49 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/processors/test_quality_filter.py:L1-L278] |
| `tests/unit/metocean/processors/test_unit_converter.py` | 51 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/processors/test_unit_converter.py:L1-L226] |
| `tests/unit/metocean/statistics/test_environmental_contours.py` | 15 | NOT_RUN: missing backend | [tests/unit/metocean/statistics/test_environmental_contours.py:L1-L139] |
| `tests/unit/metocean/statistics/test_eva.py` | 23 | NOT_RUN: missing backend | [tests/unit/metocean/statistics/test_eva.py:L1-L185] |
| `tests/unit/metocean/statistics/test_joint_probability.py` | 13 | NOT_RUN: missing backend | [tests/unit/metocean/statistics/test_joint_probability.py:L1-L119] |
| `tests/unit/metocean/statistics/test_reporting.py` | 9 | NOT_RUN: missing backend | [tests/unit/metocean/statistics/test_reporting.py:L1-L159] |
| `tests/unit/metocean/statistics/test_scatter_diagram.py` | 9 | NOT_RUN: missing backend | [tests/unit/metocean/statistics/test_scatter_diagram.py:L1-L73] |
| `tests/unit/metocean/statistics/test_wave_spectra.py` | 19 | NOT_RUN: missing backend | [tests/unit/metocean/statistics/test_wave_spectra.py:L1-L135] |
| `tests/unit/metocean/statistics/test_weather_windows.py` | 14 | NOT_RUN: missing backend | [tests/unit/metocean/statistics/test_weather_windows.py:L1-L125] |
| `tests/unit/metocean/test_cli.py` | 0 | Existing module-level skip | [tests/unit/metocean/test_cli.py:L1-L18] |
| `tests/unit/metocean/test_clients.py` | 14 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_clients.py:L1-L239] |
| `tests/unit/metocean/test_config.py` | 11 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_config.py:L1-L166] |
| `tests/unit/metocean/test_constants.py` | 38 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_constants.py:L1-L185] |
| `tests/unit/metocean/test_exceptions.py` | 36 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_exceptions.py:L1-L217] |
| `tests/unit/metocean/test_integration.py` | 11 | NOT_RUN: live API scope | [tests/unit/metocean/test_integration.py:L1-L214] |
| `tests/unit/metocean/test_licensed_tables.py` | 10 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_licensed_tables.py:L1-L206] |
| `tests/unit/metocean/test_planetswe_loader.py` | 19 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_planetswe_loader.py:L1-L265] |
| `tests/unit/metocean/test_skill_data_fetcher.py` | 0 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_skill_data_fetcher.py:L1-L269] |
| `tests/unit/metocean/test_skill_statistics.py` | 11 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_skill_statistics.py:L1-L545] |
| `tests/unit/metocean/test_skill_visualizer.py` | 0 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_skill_visualizer.py:L1-L234] |
| `tests/unit/metocean/test_unit_converter.py` | 46 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/test_unit_converter.py:L1-L270] |
| `tests/unit/metocean/unified/test_coverage.py` | 19 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/unified/test_coverage.py:L1-L130] |
| `tests/unit/metocean/unified/test_dashboard.py` | 12 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/unified/test_dashboard.py:L1-L157] |
| `tests/unit/metocean/unified/test_harmonizer.py` | 20 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/unified/test_harmonizer.py:L1-L276] |
| `tests/unit/metocean/unified/test_unified_query.py` | 22 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/unified/test_unified_query.py:L1-L253] |
| `tests/unit/metocean/utils/test_coordinates.py` | 31 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/utils/test_coordinates.py:L1-L199] |
| `tests/unit/metocean/utils/test_validators.py` | 46 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/metocean/utils/test_validators.py:L1-L233] |
| `tests/test_ndbc.py` | 50 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/test_ndbc.py:L1-L458] |
| `tests/unit/scheduler/test_metocean_adapter.py` | 3 | Offline execution; assertions sampled, remaining detailed reading C3 | [tests/unit/scheduler/test_metocean_adapter.py:L1-L111] |

### Documentation discovery

The member README and the data README were read; the former documents package extraction and the latter describes external licensed-table handling. [packages/worldenergydata-metocean/README.md:L1-L8] [data/modules/metocean/README.md:L1-L23]
The paths below were found by a case-insensitive module-name search under `docs/`; relevant passages were sampled in the CLI, architecture and adapter plan, and the remaining detailed reading is C3, issue pending (1).

| Documentation path | First module-name occurrence |
| --- | --- |
| `docs/CLI.md` | [docs/CLI.md:L506-L506] |
| `docs/adr/0001-domain-package-split.md` | [docs/adr/0001-domain-package-split.md:L20-L20] |
| `docs/ci/flake8-inventory-2026-04-23.md` | [docs/ci/flake8-inventory-2026-04-23.md:L127-L127] |
| `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` | [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L36-L36] |
| `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` | [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L12] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L12-L12] |
| `docs/reports/cli-smoke-report-2026-05-11.md` | [docs/reports/cli-smoke-report-2026-05-11.md:L22-L22] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L15-L15] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L22-L22] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L16-L16] |
| `docs/reports/data-freshness-scorecard-2026-06-08.md` | [docs/reports/data-freshness-scorecard-2026-06-08.md:L16-L16] |
| `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` | [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L206-L206] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L41-L41] |
| `docs/reports/scheduler-health-2026-W24.md` | [docs/reports/scheduler-health-2026-W24.md:L14-L14] |
| `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` | [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L49-L49] |
| `docs/plans/2026-05-04-issue-268-metocean-adapter.md` | [docs/plans/2026-05-04-issue-268-metocean-adapter.md:L1-L1] |
| `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md` | [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L126-L126] |
| `docs/plans/README.md` | [docs/plans/README.md:L17-L17] |
| `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` | [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L27-L27] |
| `docs/plans/2026-05-04-issue-360-scheduler-health.md` | [docs/plans/2026-05-04-issue-360-scheduler-health.md:L38-L38] |
| `docs/plans/2026-05-08-issue-394-repo-structure-normalization.md` | [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L75-L75] |
| `docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md` | [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L15-L15] |
| `docs/plans/2026-05-04-issue-270-lng-terminals-scheduler-wire.md` | [docs/plans/2026-05-04-issue-270-lng-terminals-scheduler-wire.md:L19-L19] |
| `docs/plans/2026-05-06-issue-387-pywasp-evaluation.md` | [docs/plans/2026-05-06-issue-387-pywasp-evaluation.md:L12-L12] |
| `docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md` | [docs/plans/2026-05-18-issue-427-seasonal-intervention-risk.md:L59-L59] |
| `docs/domains/field-development/concept-selection-and-ai-cad-briefing.md` | [docs/domains/field-development/concept-selection-and-ai-cad-briefing.md:L38-L38] |
| `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21] |
| `docs/modules/repository-architecture.md` | [docs/modules/repository-architecture.md:L103-L103] |
| `docs/modules/equipment/spm/spm-cost-estimate-conversation.md` | [docs/modules/equipment/spm/spm-cost-estimate-conversation.md:L173-L173] |

The historical adapter plan describes proposed paths and JSON outputs; current scheduler code instead writes Parquet, so implementation claims here use the code rather than the plan. [docs/plans/2026-05-04-issue-268-metocean-adapter.md:L26-L36] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/metocean_refresh.py:L55-L64]
