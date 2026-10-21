# eia_us module knowledge pack

| Header | Value |
| --- | --- |
| Module | `eia_us` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-eia_us/src/worldenergydata/eia_us` |
| Pack revision | 1, 2026-10-20 |
| Code revision | `285d65c40896b17ccf44568e59f5b789d59c943e` |
| Analysis family | EC; data pipeline, using AQG r0 Python calculations |
| Quality manager role | Calculations quality manager; deputy: maintainer |
| Status | DRAFT |

## 1. Purpose and scope

The package normalises supplied state, basin, regional and country production records, fits monthly decline curves, calculates simplified fiscal results, and provides a series-oriented API client. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L53-L102] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L64-L92] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L47-L73] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L82-L106] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L157-L219] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L63-L90] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L205-L255]

Scope includes all four subpackages; `DrillingProductivityReport` delegates loading to `BasinProductionLoader` and computes latest-rig and net-change summaries. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L20-L67]

The scheduler's similarly named refresh adapter instantiates the separate `worldenergydata.eia` ingestion pipeline; its success does not exercise these loaders. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L52-L68]

The distribution declares alpha maturity and version `0.1.0`, while the namespace initializer assigns `1.0.0`; treat those as separate declarations rather than an operational-readiness assessment. [packages/worldenergydata-eia_us/pyproject.toml:L7-L19] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L20-L20]

Use supplied records and synthetic test fixtures as computational inputs; neither the client mocks nor the country estimates establish current production values. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L87-L102] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L74]

### Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-15 | Initial pinned module pack, regression examples, QA gates and qualification gaps |
| 1 | 2026-10-20 | Add omitted failure modes and synthetic adapter boundaries; complete test node IDs and issue tracking so the documented limits can be checked |

## 2. Inputs and outputs

### Inputs

| Interface and input | Unit / convention | Accepted shape and handling | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| `EIAApiClient` configuration | rate: requests/hour; TTL: seconds | Constructor key or `EIA_API_KEY`; missing key raises `EIAApiError`; nonpositive rate disables waiting | rate 500; TTL 86400; cache enabled | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L116-L154] |
| `fetch_series(series_id, params, use_mock)` | series ID and API query fields | Cache lookup precedes mock/live selection; API units retained as strings | params empty; mock false | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L205-L255] |
| `StateProductionLoader.load(records, state)` | code assumes thousand barrels; `period` sliced as year/month | `period`, `value`; null preserved, malformed numeric slices skipped; `unit` is not inspected | No state default; empty input produces schema-only frame | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L53-L102] |
| `BasinProductionLoader.load(records)` | `rig_count`: count; production columns: bopd, legacy loss signed negative by convention | `period`, `basin`, `rig_count`, `new_well_ip_bopd`, `legacy_decline_bopd`, `total_production_bopd`; numeric fields cast to float | Missing labels empty; missing numbers zero | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L35-L49] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L55-L92] |
| `AlaskaProductionLoader.load(records)` | `crude_bopd`, `ngl_bopd`: bbl/day | `period`, `field`, crude and NGL; crude clamped to nonnegative, NGL not clamped | Missing labels empty; missing numbers zero | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L27-L39] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L45-L73] |
| `CountryProductionLoader.load(records)` | `production_kbd`: thousand bbl/day; year integer | `country`, `year`, `production_kbd`; float/int conversion | Missing country empty; year and production zero | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L48] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L80-L106] |
| `arps_hyperbolic(t, qi, di, b)` and `HyperbolicDeclineModel` | months; `di`: 1/month; rate in supplied bopd or Mcfd; `b`: dimensionless | No constructor range validation; prediction uses integer month positions beginning at zero | `terminal_b=0.5` | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L104] |
| `ShaleDeclineAnalyzer.fit(production, basin, b_min, b_max)` | monthly rate array; label string | At least 6 values; fitting bounds constrain `qi`, `di`, `b` | b bounds 0.5 to 3.0 | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L157-L200] |
| Fiscal `calculate` / `calculate_oil` / `calculate_gas` | Currency unspecified; caller must use one currency and period for gross revenue, opex and capex | Numeric arguments; no date, exemption or lease input | capex 0 | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L63-L90] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L102-L156] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L169-L200] |
| `GoMCrosscheck.compare` | both inputs kbd; tolerance fraction | Signed difference EIA minus BSEE; absolute relative error uses BSEE, substitutes 1 when BSEE is zero | tolerance 0.05 | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L214-L243] |

### Outputs

| Interface | Output and unit | Empty / aggregation behaviour | Evidence |
| --- | --- | --- | --- |
| `parse_series_response` | list of `period`, float-or-null `value`, `unit` | Missing `response.data` becomes empty; conversion failures become null | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L172-L201] |
| State loader | frame `state, year, month, crude_bbl`; bbl | Multiply non-null values by 1000; `annual_total` sums by state/year; filters return copies | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L69-L121] |
| Basin loader / summaries | frame of six required columns; `BasinRecord`; latest rig count; signed `net_change_bopd` | Exact label/period filters; summary addition is new-well value plus legacy loss | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L94-L116] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L37-L67] |
| Regional loader | frame `period, field, crude_bopd, ngl_bopd`; records; `total_liquids_bopd` | `annual_total` sums monthly daily rates and retains `_bopd` names; it does not integrate volume | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L27-L39] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L83-L112] |
| Country loader | frame `country, year, production_kbd` | `top_producers(n=10, year=None)` takes each country's maximum across selected years, then sorts descending | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L108-L145] |
| Decline fit / prediction | `ShaleDeclineResult(basin, model, r_squared, rmse)`; rate array | R-squared clipped to [0, 1]; RMSE in input rate units; result prediction delegates | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L137-L148] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L208-L229] |
| Fiscal models | `USFiscalResult` monetary fields | Levy floored at zero; net income subtracts levy, opex and capex; state models exclude federal royalty | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L39-L50] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L79-L90] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L118-L156] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L185-L200] |
| Crosscheck | `eia_kbd`, `bsee_kbd`, `difference_kbd`, `pct_difference`, `within_tolerance` | Despite its name, `pct_difference` is a fraction | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L232-L243] |

The interfaces use calendar labels and scalar records rather than spatial coordinates; no coordinate-frame, origin or phase transformation occurs in their record construction. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L74-L102] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L77-L92] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L61-L73] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L96-L106]

## 3. Method and governing standards

| Method | Implementation, reference and limits |
| --- | --- |
| Response parsing and caching | `generate_cache_key` sorts query items, URL-encodes them and uses MD5 for a lookup key; `EIACache` expires against monotonic time; the key is not a provenance digest. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L47-L82] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L163-L168] |
| Live series retrieval | `_fetch_live` makes one `requests.get` call with 30-second timeout, parses JSON, and caches records; 429 has a dedicated exception, other non-200 statuses a generic exception; no pagination or retry loop appears in this method. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L257-L297] |
| Request spacing | `_apply_rate_limit` enforces a minimum interval of 3600/rate seconds; this is sequential spacing, despite the constructor comment calling it a token bucket. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L150-L154] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L299-L306] |
| State normalisation | `STATE_SERIES_ID` uppercases and trims a code, then interpolates it; `load` multiplies values by 1000, and `annual_total` groups and sums. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L34-L44] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L74-L113] |
| Production summaries | `BasinRecord.net_change_bopd` and `DrillingProductivityReport.net_change_summary` each add new-well and legacy terms; `AlaskaFieldRecord.total_liquids_bopd` adds crude and NGL; country ranking uses per-country maxima. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L46-L49] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L53-L67] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L36-L39] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L135-L145] |
| Decline equation | `arps_hyperbolic` evaluates `qi/(1+b*di*t)^(1/b)` and explicitly uses `qi*exp(-di*t)` at `b=0`; the code names Arps (1945), SPE-945228-G as its reference. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L7-L21] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] |
| Forecast switch | `_apply_terminal_switch` places the transition at `max(1, int(n_months*0.6))`, using local nominal decline for an exponential tail; it does not calculate the effective-b criterion described in its docstring. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131] |
| Fitting and diagnostics | `ShaleDeclineAnalyzer.fit` uses bounded SciPy `curve_fit`; `RuntimeError` or `ValueError` returns initial guesses after a warning; diagnostics evaluate the default switched predictor, and R-squared is clipped. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L184-L229] |
| Fiscal arithmetic | Each levy is gross revenue times a stored rate, floored at zero; net income subtracts levy and both costs; the stored source comments name 30 CFR Part 1206, Texas Tax Code Chapters 201/202, and ND Century Code 57-51/57-51.1, without editions or effective dates. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L9-L30] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L79-L90] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L118-L156] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L185-L200] |
| Aggregate comparison | `GoMCrosscheck.compare` uses `abs(eia-bsee)/abs(reference) <= tolerance_pct`; zero BSEE uses reference 1. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L232-L243] |

UNVERIFIED: the external derivation and applicability of the Arps reference, including the terminal-switch claim, were not established from an opened publication; the DOI request returned HTTP 403; #1604. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L16-L21] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131]

UNVERIFIED: current legal applicability, editions and effective dates of the fiscal rates were not checked; output fields contain no citation sidecar; #361 tracks provenance adoption. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L9-L30] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L39-L50]

UNVERIFIED: the production-series units and revision-qualified provenance of built-in country estimates have not been independently established; #1605 and #462. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L1-L4] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L22-L74]

## 4. Validated worked examples

Validated examples: __0__; the cases below are __8 regression examples__, using synthetic fixtures, code-level identities or stored mock data rather than a revision-qualified independent dataset; independent validation remains #1607. [tests/unit/eia_us/test_state_production.py:L13-L28] [tests/unit/eia_us/test_basin_decline.py:L34-L44] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L74]

Offline execution record: code pin from the header; 146 tests passed, 0 failed, 0 skipped, 0 NOT_RUN before and after documentation edits; each node below returned PASS in both runs.

| ID / case | Source and inline input | Expected value and tolerance basis | Existing test node ID | Offline result and evidence |
| --- | --- | --- | --- | --- |
| E1 response parsing | Test response fixture, two monthly string values | 2 records; first value 12345.0 in fixture unit; exact assertions | `tests/unit/eia_us/test_eia_api_client.py::TestEIAApiClientFetch::test_parse_series_response_extracts_data` | PASS / PASS. [tests/unit/eia_us/test_eia_api_client.py:L117-L129] |
| E2 state conversion | Inline fixture: value 10.0, unit thousand barrels | 10000.0 bbl; `pytest.approx` default, no tolerance override in source | `tests/unit/eia_us/test_state_production.py::TestStateProductionLoader::test_load_converts_thousand_barrels_to_bbl` | PASS / PASS. [tests/unit/eia_us/test_state_production.py:L90-L100] |
| E3 basin schema | Synthetic 6-month record list | 6 named required columns; 0 absent columns | `tests/unit/eia_us/test_basin_production.py::TestBasinProductionLoader::test_load_has_required_columns` | PASS / PASS. [tests/unit/eia_us/test_basin_production.py:L96-L107] |
| E4 regional empty input | Empty list | 0 rows; exact empty-frame predicate | `tests/unit/eia_us/test_alaska_production.py::TestAlaskaProductionLoader::test_load_empty_returns_empty_dataframe` | PASS / PASS. [tests/unit/eia_us/test_alaska_production.py:L84-L86] |
| E5 country ranking | Built-in mock-country records | 5 output rows, descending order predicate; not a production-volume validation | `tests/unit/eia_us/test_international_production.py::TestCountryProductionLoader::test_top_n_producers` | PASS / PASS. [tests/unit/eia_us/test_international_production.py:L85-L93] |
| E6 harmonic identity | qi 1000 rate units, di 0.05/month, b 1, t 12 months | 625.0 rate units from `1000/(1+0.05*12)`; relative tolerance `1e-4` (unit 1), explicit in test | `tests/unit/eia_us/test_basin_decline.py::TestArpsHyperbolic::test_b_equals_1_harmonic_case` | PASS / PASS. [tests/unit/eia_us/test_basin_decline.py:L34-L38] |
| E7 signed aggregate difference | EIA 2000.0 kbd, BSEE 1900.0 kbd | 100.0 kbd; `pytest.approx` default, no tolerance override in source | `tests/unit/eia_us/test_us_fiscal.py::TestGoMCrosscheck::test_difference_is_eia_minus_bsee` | PASS / PASS. [tests/unit/eia_us/test_us_fiscal.py:L185-L190] |
| E8 cache expiry | TTL 0.01 s; wait 0.05 s | 0 retained live entries for the selected key; exact null predicate | `tests/unit/eia_us/test_eia_api_client.py::TestEIACache::test_cache_expired_returns_none` | PASS / PASS. [tests/unit/eia_us/test_eia_api_client.py:L30-L34] |

### Reproduction record

Use `uv run --extra test --group benchmark python -m pytest tests/unit/eia_us tests/benchmarks/test_eia_benchmarks.py -q -rA -p no:cacheprovider --basetemp=<scratch-output>` with coverage data and every coverage report explicitly directed to scratch; keep configured `addopts`, and use the repository's `--allow-existing-tree-changes` mode for the after run so pre-existing documentation is checked for preservation. [pyproject.toml:L142-L153] [pyproject.toml:L570-L573] [tests/conftest.py:L405-L455] [tests/conftest.py:L469-L478]

The eight test files contain 144 unit tests and 2 benchmark functions; the benchmark plugin is a declared group dependency, and the benchmarks check 1000 state rows and 500 basin rows. [tests/unit/eia_us/test_state_production.py:L31-L139] [tests/unit/eia_us/test_eia_api_client.py:L19-L181] [tests/unit/eia_us/test_basin_production.py:L32-L138] [tests/unit/eia_us/test_basin_decline.py:L17-L183] [tests/unit/eia_us/test_international_production.py:L13-L104] [tests/unit/eia_us/test_alaska_production.py:L32-L118] [tests/unit/eia_us/test_us_fiscal.py:L21-L190] [tests/benchmarks/test_eia_benchmarks.py:L63-L76] [pyproject.toml:L570-L573]

Revision 1 repeats that selection through an existing dependency environment because `uv run` cannot acquire its required cache lock. The configured `addopts`, scratch output destinations and tree-preservation checks remain enabled. Module-source import digests match the code pin; the installed `assetutilities` revision differs from the lock, so this rerun does not establish locked-environment reproduction.

## 5. QA gates

Gate assignment: AQG r0, section 10, Python calculations; G5 from section 9; the following are pack-specific checks, with observed results limited to the code pin and synthetic inputs.

| Gate | Applicability | Check IDs and route |
| --- | --- | --- |
| G0 | Applicable: record types, units and parsing | C0.1–C0.3; pure Python record transforms |
| G1 | Applicable: imports and tests | C1.1; import through the tests under Python; no external program model is emitted |
| G2 | Applicable: independent arithmetic identities | C2.1–C2.2; hand arithmetic compared with scalar function outputs; no legal-rate or forecast-physics qualification |
| G3 | NOT_APPLICABLE | No time-domain solver integration is performed by these scalar/array implementations. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L88-L104] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L217-L243] |
| G4 | NOT_APPLICABLE | No diffraction body, mesh or hydrodynamic result is produced by the record transformations or calculation functions. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L69-L102] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] |
| G5 | Applicable: traceable evidence appendix | C5.1–C5.2; citation resolution and test-result coverage |

| ID | Module-specific executable check | Numeric pass criterion and unit | Evidence / observed result | Gate |
| --- | --- | --- | --- | --- |
| C0.1 | E2: `StateProductionLoader.load` conversion of 10.0 thousand barrels | Absolute error <= 0.01 bbl against 10000.0 bbl; matches default `approx` at this scale | E2 PASS; unit-label validation remains a gap. [tests/unit/eia_us/test_state_production.py:L90-L100] | G0 |
| C0.2 | E1 and `tests/unit/eia_us/test_eia_api_client.py::TestEIAApiClientFetch::test_parse_series_response_handles_null_value`: `parse_series_response` | Exactly 2 records in E1; 0 changed-null values in null case; unit: records | Both nodes PASS. [tests/unit/eia_us/test_eia_api_client.py:L117-L145] | G0 |
| C0.3 | `tests/unit/eia_us/test_basin_production.py::TestBasinProductionLoader::test_legacy_decline_is_negative`: basin loader sign on supplied fixtures | 0 output rows with `legacy_decline_bopd > 0` bbl/day; unit: rows | PASS; does not establish rejection of a positive input. [tests/unit/eia_us/test_basin_production.py:L135-L138] | G0 |
| C1.1 | Complete unit and benchmark command from section 4 | 146 passed, 0 failed, 0 skipped, 0 NOT_RUN; unit: test cases | PASS before and after; benchmarks require their declared plugin. [tests/benchmarks/test_eia_benchmarks.py:L13-L16] [tests/benchmarks/test_eia_benchmarks.py:L63-L76] | G1 |
| C2.1 | E6: independently reduce b=1 to `1000/1.6`; compare `arps_hyperbolic(12,1000,0.05,1)` | Relative error <= `1e-4`, unit 1; expected 625.0 in chosen bbl/day convention | Hand check error 0.0 bbl/day; E6 PASS; no switched predictor used as reference. [tests/unit/eia_us/test_basin_decline.py:L34-L38] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L56-L60] | G2 |
| C2.2 | E7: subtract 1900.0 from 2000.0; compare `GoMCrosscheck.compare` difference | Absolute error <= `1e-4` kbd against 100.0 kbd | Hand check error 0.0 kbd; E7 PASS; no live EIA/BSEE agreement claimed. [tests/unit/eia_us/test_us_fiscal.py:L185-L190] | G2 |
| C5.1 | Resolve every pack `[path:Lstart-Lend]` using `git show <code-pin>:<path>` | 0 missing files and 0 invalid ranges; unit: citations | Citation resolver record; ten supports read manually at the pin | G5 |
| C5.2 | Join every E1–E8 node to both `-rA` result lists | 0 missing node IDs and 0 absent results; unit: example cases | Eight paired PASS records. [tests/unit/eia_us/test_eia_api_client.py:L117-L129] [tests/unit/eia_us/test_basin_decline.py:L34-L38] | G5 |

Eight checks are defined: G0 3, G1 1, G2 2, G3 0, G4 0, G5 2; passing them covers the listed inputs and algebra, while the broader qualification gaps remain in section 10.

## 6. Known failure modes and pitfalls

Detection recipes below expose current behaviour; they are not acceptance of that behaviour, and no failing module assertion is repaired by this pack.

| Symptom / cause | Detection recipe and current evidence | Tracking / date |
| --- | --- | --- |
| API key travels in the URL query and can reach transport-error text | Capture `requests.get` parameters with a synthetic key and raise a transport exception containing the query: `api_key` is passed in `params`, and `EIAApiError` retains the exception text. Require 0 key-value occurrences in emitted errors or log records; no detection check exists in the shipped suite. Debug logging lists query keys only; it does not redact the propagated exception. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L273-L282] | #431; 2026-10-20 |
| A successful response missing `response.data` is cached as a valid empty series | Mock a 200 response without that path, then fetch the same series twice: parsing returns an empty list and only 1 request is made because the cached list is a hit, until the configured TTL expires (default 86400 s). Require 0 cached empty results from a missing data block; no detection check exists in the shipped suite. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L31-L32] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L172-L182] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L228-L235] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L291-L297] | #1271; #1606; 2026-10-20 |
| Fit failure returns initial guesses after a warning; diagnostics use switched forecasts and clip R-squared | Fit six values with reversed b bounds; check whether a result is returned outside the requested bounds; observed fallback b 1.5. Require 0 unmarked fallback results; no detection check exists in the shipped test suite for fallback status. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L189-L229] | #1604; 2026-10-15 |
| Missing/malformed data can look like valid zero: parser converts invalid values to null, basin/country loaders default missing numbers to zero; all-null state annual sums use the default pandas sum | Check missing-value counts before/after `load` and `annual_total`; observed all-null annual output 0.0 bbl. Require 0 unreported substitutions; C0.2 checks only the parser's null case. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L182-L201] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L81-L88] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L100-L103] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L110-L113] | #1605; 2026-10-15 |
| Unit labels ignored; invalid calendar month accepted | Feed a record labelled bbl into state `load`: output is still multiplied by 1000; `2024-13` yields month 13. Require 0 accepted invalid unit/calendar records; no detection check exists in the shipped suite; C0.1 exercises only the assumed unit. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L76-L95] | #1605; 2026-10-15 |
| Regional annual output sums daily rates without duration weighting; negative crude is hidden by clamping, negative NGL is retained | Supply two months of 1.0 bbl/day and inspect annual result: 2.0 under a `_bopd` column. Require an explicit rate/volume aggregation contract before comparison; no detection check exists in shipped tests for annual totals. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L61-L73] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L83-L98] | #1605; 2026-10-15 |
| Forecast changes its overlapping prefix when horizon changes; switch criterion is a fixed fraction of horizon | Compare `predict(12)` with `predict(24)[:12]` at qi 1000.0 bbl/day, di 0.08/month, b 1.5: 4 mismatched months, maximum difference 11.0 bbl/day. Require 0 horizon-dependent prefix changes for a physical terminal criterion; the named terminal test checks positivity only. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L97-L131] [tests/unit/eia_us/test_basin_decline.py:L87-L98] | #1604; 2026-10-15 |
| Mock and live fetches share a cache namespace; a cache hit precedes the `use_mock` branch | Inspect `generate_cache_key(series_id, params)` and `fetch_series` ordering; mode contributes 0 fields to the key. Require mode isolation before mixing mock and live calls; no detection check exists in the suite. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L163-L168] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L228-L255] | #1606; 2026-10-15 |
| Fiscal and mock-data assertions are mistaken for authority-qualified results | C2.1/C2.2 are algebra checks only; fiscal constant tests compare stored constants, while the result has no provenance field. Require at least 1 revision-qualified independent example before a validated claim; none recorded here. [tests/unit/eia_us/test_us_fiscal.py:L21-L35] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L39-L50] | #361; #1607; 2026-10-15 |
| Substituting 1 for a zero reference permits false acceptance of nonzero production | Compare EIA 40.0 bbl/day, converted to kbd, with BSEE zero at a 5.0 % tolerance: `within_tolerance` is true. Require 0 accepted nonzero comparisons against a zero reference without an explicit absolute tolerance; no detection check exists in the shipped suite. C2.2 checks a nonzero reference only. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L232-L243] [tests/unit/eia_us/test_us_fiscal.py:L159-L190] | #1607; 2026-10-20 |
| Scheduler naming mistaken for direct package coverage | Inspect instantiated class in `EiaUsRefreshJob.run`: `EIAIngestionSync`, not these loaders; no detection check exists for these loaders in that adapter. [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L52-L68] | #462; 2026-10-15 |
| Similarly named production adapter output mistaken for these loaders or measured data | Inspect `EiaUsAdapter`: `region = "eia_us"`, but its own table and generator produce synthetic rows tagged `source: "eia_us_mock"` without importing this package. Require 0 claims of measured provenance or loader coverage from that adapter; no detection check exists in this package's shipped suite. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L14-L29] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L68-L100] | #1608; 2026-10-20 |

Open #431 records API-key exposure, and #1271 records the cached missing-data response. The remaining rows record source inspection and offline checks; they do not assert historical incidents or repaired production behaviour.

## 7. Lessons log

| Date | Change reference | Lesson | Evidence | Pack change / shared-log reference |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | A terminal test's positivity assertion does not check switch timing or overlapping forecast consistency | [tests/unit/eia_us/test_basin_decline.py:L87-L98] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L113-L129] | Sections 3, 5 and 6; #1604 |
| 2026-10-15 | Initial pack | Annual sums of rates require an explicit output quantity contract | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L83-L98] | Sections 2 and 6; #1605 |
| 2026-10-15 | Initial pack | A source-rate constant assertion is regression evidence rather than an effective-date check | [tests/unit/eia_us/test_us_fiscal.py:L21-L35] | Sections 3–5; #361 |

## 8. Ownership

Review contract: calculations quality manager; deputy role: maintainer; producing role: package contributor; clearance requires review by a provider other than the producer (AQG r0, section 11, Sign-off and independence).

Escalation contract: send unresolved unit, reference, tolerance or method classifications to the calculations quality manager; the maintainer coordinates cross-family work (AQG r0, sections 10–11, Family mapping and Sign-off and independence).

Status remains DRAFT; no clearance or completed independent review is asserted.

## 9. Dependencies and implementation overlap

### Runtime and integration boundaries

The member directly declares `worldenergydata-core`, NumPy, pandas and SciPy; live retrieval imports `requests` inside `_fetch_live` and raises a specific error if unavailable, although it is absent from the member's direct dependency list. [packages/worldenergydata-eia_us/pyproject.toml:L30-L36] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L264-L270]

Input collections are caller-supplied records, with in-memory mock series and country estimates available in code; the scheduler uses the separate `eia` ingestion implementation, and its output directory defaults to the `eia` data location. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L87-L102] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L74] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L25-L37] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L52-L68]

The separate production package's `EiaUsAdapter` does not import these loaders: its `eia_us` region label identifies independently generated synthetic rows tagged `eia_us_mock`, rather than measured series or direct package integration. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L14-L29] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L31-L56] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L68-L100]

### Implementation-map inventory and counted-family audit

| Audit field | Recorded value |
| --- | --- |
| Map artifact | `digitalmodel`, `docs/registry/implementation-map.yaml` |
| Map artifact commit | `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407` |
| Map data revision (`revision` field) | `947fa50ff9a9e210de7e8f90e01b37add85c5954` |
| Map families inspected | 13 |
| In-package implementation rows | 0 |
| Module map families / inventory | Empty: no row path lies inside the header package |
| Counted families | 0; ranking and tie-break have an empty input |
| Counted-family grep | NOT_APPLICABLE: no family has an implementation row in the package at this map revision |
| Further second implementations counted | 0; empty counted-family set |
| Inventory / A8 result | PASS for empty inventory; grep NOT_APPLICABLE |
| Map follow-up | #1608 |

Map follow-up scope: series retrieval/cache, record normalisation and aggregation, decline fitting/forecasting/diagnostics, fiscal arithmetic and production crosschecks are the method families covered in section 3; add these to the map before they can become counted families. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L163-L201] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L74-L113] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L157-L229] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L79-L90] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L232-L243]

### Additional repository-wide findings

The additional search covered tracked Python files across the whole repository, including `scripts/`, using `arps_hyperbolic|hyperbolic_decline|MCRFP|INTL\.57-1|class (EIAApiClient|EIAFeedClient|GoMCrosscheck)|new_well_ip_bopd|FEDERAL_ONSHORE_ROYALTY_RATE`, plus a royalty-definition search; these findings are map follow-up only and do not change the empty counted-family result.

| Candidate / classification | Source evidence |
| --- | --- |
| Independent hyperbolic rate function: `ArpsDeclineCurve._rate_fn` returns its own formula | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L260-L277] |
| Independent rate computation: `ProductionForecaster.hyperbolic_decline`; time converted to years | [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L327-L353] |
| Independent fit: `DeclineCurveAnalyzer._fit_hyperbolic` in the two country packages | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L163-L179] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L134-L150] |
| Independent fit: `ProductionForecaster._fit_hyperbolic_decline` in the source-data package | [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L195-L218] |
| Independent forecast formulas in the dashboard and its legacy implementation | [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/views_decline.py:L93-L110] [src/worldenergydata/modules/well_production_dashboard/well_detail_views.py:L633-L652] |
| Separate HTTP implementation: `EIAFeedClient` builds weekly feed URLs, rather than delegating to this series client | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L48-L59] [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L79-L92] |
| Independent synthetic data generator: `EiaUsAdapter` uses its own table and formula, declares region `eia_us` and emits `eia_us_mock`; it does not call these loaders | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L14-L29] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L68-L100] |
| In-package duplicate arithmetic already listed in section 3: `BasinRecord.net_change_bopd` and `DrillingProductivityReport.net_change_summary` | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L46-L49] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L65-L67] |
| Helper: `ShaleDeclineResult.predict` delegates to its stored model; no independent formula | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L146-L148] |
| Script discovery: `_execute_calculate_royalties` only reads and logs a configured rate; it does not compute a royalty result | [scripts/lower_tertiary_analysis.py:L238-L243] [scripts/bsee/lower_tertiary_analysis.py:L238-L243] |

## 10. Coverage and open items

### Coverage index

Source read: all 13 Python files in the header package, including the five initializers; supporting package configuration and README were also read. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L1-L20] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L1-L229] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L1-L243] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L1-L306] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L1-L145] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L1-L112] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L1-L116] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L1-L67] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L1-L121] [packages/worldenergydata-eia_us/README.md:L1-L8] [packages/worldenergydata-eia_us/pyproject.toml:L1-L56]

Test index: `tests/unit/eia_us/test_{state_production,eia_api_client,basin_production,basin_decline,international_production,alaska_production,us_fiscal}.py` and `tests/benchmarks/test_eia_benchmarks.py`; section 4 gives the recount and execution record. [tests/unit/eia_us/test_state_production.py:L31-L139] [tests/unit/eia_us/test_eia_api_client.py:L19-L181] [tests/unit/eia_us/test_basin_production.py:L32-L138] [tests/unit/eia_us/test_basin_decline.py:L17-L183] [tests/unit/eia_us/test_international_production.py:L13-L104] [tests/unit/eia_us/test_alaska_production.py:L32-L118] [tests/unit/eia_us/test_us_fiscal.py:L21-L190] [tests/benchmarks/test_eia_benchmarks.py:L63-L76]

Documentation discovery: 23 existing files under `docs/` name `eia_us` or `eia-us`; the module-relevant passages below were read; historical readiness claims were not promoted to current evidence, and full revalidation of unrelated historical content remains #349.

| Discovered document | Module-relevant passage / evidence |
| --- | --- |
| Package split architecture | [docs/adr/0001-domain-package-split.md:L47-L48] |
| Repository architecture | [docs/modules/repository-architecture.md:L100-L103] |
| Runtime timeout investigation plan | [docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md:L18-L21] |
| Capability index reconciliation plan | [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L68-L70] |
| EIA refresh plan | [docs/plans/2026-05-04-issue-266-eia-scheduler-operationalize.md:L8-L16] |
| Capability audit plan | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L20-L21] |
| Scheduler readiness plan | [docs/plans/2026-05-04-issue-351-scheduler-readiness-matrix.md:L35-L38] |
| Scheduler health plan | [docs/plans/2026-05-04-issue-360-scheduler-health.md:L35-L39] |
| Structure normalisation plan | [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L68-L73] |
| Source refresh contract plan | [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L146-L148] |
| Source refresh integration plan | [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L47-L50] |
| Runtime timeout probe | [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L199-L202] |
| Capability matrix text | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L130-L132] |
| Capability matrix data | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L196-L219] |
| Data completeness summary | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L18-L21] |
| Data completeness text | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L97-L98] |
| Data completeness data | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L133-L147] |
| Capability discovery summary | [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L68-L70] |
| Scheduler commands | [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L165-L166] |
| Scheduler runtime readiness | [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L189-L190] |
| Capability reconciliation assessment | [docs/reports/2026-04-27-plan-354-adversarial-review.md:L17-L19] |
| Freshness scorecard | [docs/reports/data-freshness-scorecard-2026-06-08.md:L8-L10] |
| Scheduler health snapshot | [docs/reports/scheduler-health-2026-W24.md:L12-L14] |

### Open work and unverified claims

The maintainer coordinates the following open work; each item has an assigned issue number.

| Item | Required follow-up / evidence | Tracking |
| --- | --- | --- |
| Decline derivation, terminal switch and fit status | Resolve UNVERIFIED decline applicability; obtain an open reference and test horizon-invariant forecasting, fallback status and unmodified diagnostics; current heuristic and fallback are documented rather than qualified. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L189-L229] | #1604 |
| Source units and revision-qualified production provenance | Resolve UNVERIFIED series units and mock-country provenance; validate dates, units, missingness and annual rate/volume semantics before use; current fixtures do not establish them. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L76-L113] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L83-L98] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L22-L74] | #1605; #462 |
| API key exposure, mode separation and live coverage | Keep key values out of request URLs and emitted errors; separate mock/live cache entries, reject missing `response.data` before caching, declare or document live dependencies, and add mocked-transport checks for status, spacing, response shape and pagination; existing fetch tests use mock/cache routes. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L228-L297] [tests/unit/eia_us/test_eia_api_client.py:L96-L164] | #431; #1271; #1606 |
| Independent examples, uncovered summaries and zero-reference comparisons | Add a revision-qualified independent dataset/closed-form benchmark and direct `DrillingProductivityReport` tests; define a zero-reference contract and test zero/zero and nonzero/zero comparisons without substituting an implicit reference. Only synthetic hand probes cover the summaries here. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L20-L67] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L232-L243] [tests/benchmarks/test_eia_benchmarks.py:L63-L76] | #1607 |
| Fiscal authority and citation sidecars | Resolve UNVERIFIED fiscal applicability: effective-date-qualified legal sources and per-result provenance; no current-law assertion is made. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L9-L30] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L39-L50] | #361 |
| Missing implementation-map families and synthetic adapter boundaries | Add the section-3 method families and repository overlap definitions to the map; label the separate production adapter's synthetic output and lack of loader delegation; then perform counted-family searches at the first qualifying map revision. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L53-L67] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L68-L100] | #1608 |
| Discovery identifiers | Three source/test discovery files contain identifying text; use neutral fixture identifiers before public examples; no identifying strings or source-derived regional fixture values are reproduced here. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L6-L6] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L19-L24] [tests/unit/eia_us/test_alaska_production.py:L13-L17] | #1609 |
| Packaging boundary | The existing member package-data glob includes `**/*.md`, which also matches this pack; wheel exclusion requires a separate packaging change, with no glob changed here. [packages/worldenergydata-eia_us/pyproject.toml:L50-L56] | #529 |
| Historical documentation / readiness | Reconcile the manifest's `stable` declaration with alpha packaging and source-evidence limits; older module paths and scheduler naming require current evidence, not copied readiness assertions. [module-manifest.yaml:L216-L232] [packages/worldenergydata-eia_us/pyproject.toml:L7-L19] [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L196-L219] | #349; historical #354 (closed); #462 |

The calculation-citation contract was readable; no licensed standard was opened and no licensed clause text or tabulated standard value is reproduced. External fiscal verification, live data acquisition and wheel-content verification remain outside this offline record.
