# eia_us module knowledge pack

| Header | Value |
| --- | --- |
| Module | `eia_us` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-eia_us/src/worldenergydata/eia_us` |
| Pack revision | 0 |
| Code revision | `285d65c40896b17ccf44568e59f5b789d59c943e` |
| Analysis family | EC; data pipeline, Python calculations gate set |
| Quality manager role | Calculations quality manager |
| Deputy role | Calculations deputy quality manager; appointment pending |
| Status | DRAFT |

The header establishes this pack's scope and review assignments; proposed checks are requirements of this pack, while executed results are recorded separately below.

## 1. Purpose and scope

The package normalises state, basin and record-level production, summarises drilling productivity, queries country records, fits decline curves and calculates simplified fiscal results. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L1-L17]

`EIAApiClient` supports response parsing, an in-memory cache, explicit mock fetches and a live HTTP branch; offline evidence does not qualify live responses. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L172-L201] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L205-L297]

Scope includes all four subpackages (`analysis`, `client`, `international`, `production`); the separate `worldenergydata.eia` ingestion package is identified as the live-access route by the package documentation. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L11-L17]

The package metadata declares development status Alpha; this is metadata, rather than an engineering qualification. [packages/worldenergydata-eia_us/pyproject.toml:L15-L23]

## 2. Inputs and outputs

### Inputs

| Route / field | Unit | Allowed range / actual handling | Default | Source and evidence |
| --- | --- | --- | --- | --- |
| `EIAApiClient` configuration | requests/hour; cache TTL in s | A key is required; nonpositive rate limits disable the interval calculation | 500 requests/hour; 86400 s; cache enabled | Constructor or environment variable `EIA_API_KEY`; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L24-L30] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L116-L154] |
| `parse_series_response(raw)` | Unit string retained | Reads `response.data`; nonnumeric values become `None` | Missing data becomes an empty list | Caller-supplied response dictionary; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L172-L201] |
| `StateProductionLoader.load(records, state)` | Input thousand bbl; output bbl | Multiplies each non-null value by 1000 without checking `unit`; slices year/month; malformed integer periods are skipped | Missing value becomes `None`; state uppercased and stripped | Parsed records and explicit state; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L47-L51] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L53-L102] |
| `BasinProductionLoader.load(records)` | `rig_count`: count; production fields: bopd | Converts numeric fields to floats; no sign enforcement | Missing numbers 0; missing labels empty strings | Caller dictionaries; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L35-L92] |
| `AlaskaProductionLoader.load(records)` | `crude_bopd`, `ngl_bopd`: bopd | Crude is clamped to at least 0; NGL is converted without a clamp | Missing rates 0; missing labels empty strings | Caller dictionaries; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L45-L73] |
| `CountryProductionLoader.load(records)` | `production_kbd`: thousand bbl/day; `year`: year | Converts year to int and production to float | Missing year/rate 0; missing country empty string | Caller dictionaries; built-in records are labelled mock; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L74] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L80-L106] |
| `arps_hyperbolic(t, qi, di, b)` | t: month; di: 1/month; qi: bopd or Mcfd | Positive decline/exponent described; arithmetic itself has no argument validation | No function defaults | Caller; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L7-L14] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] |
| `ShaleDeclineAnalyzer.fit(production, basin, b_min, b_max)` | Monthly rate samples, same unit as qi | At least 6 samples; bounds qi from 0 to ten times initial guess, di from 0.000001 to 2 per month | b bounds 0.5 to 3; initial di 0.08 per month, b 1.5 | Caller array; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L34-L37] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L157-L206] |
| Fiscal `calculate*` | Consistent caller currency | Taxes clamped to 0; capex is subtracted from net income | capex 0 | Caller gross revenue, opex, capex; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L63-L90] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L102-L156] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L169-L200] |
| `GoMCrosscheck.compare` | Both inputs kbd | Relative difference uses BSEE denominator, substituting 1 when it is zero | Tolerance fraction 0.05 | Caller scalars; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L32-L33] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L214-L243] |

### Outputs and conventions

| Route | Output / unit | Convention and limitation | Evidence |
| --- | --- | --- | --- |
| `STATE_SERIES_ID(state_code)` | EIA series-ID string; no physical unit | Uppercases and strips the code, then formats `PET.MCRFP{code}2.M`; two-letter length is documented but not checked | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L34-L44] |
| State load / annual total | `state`, `year`, `month`, `crude_bbl`; annual bbl | Grouped monthly volumes are summed by state/year | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L90-L121] |
| Basin load / `BasinRecord.net_change_bopd` | Six-column frame; net change bopd | New-well rate plus signed legacy decline | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L35-L62] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L77-L116] |
| Record load / `AlaskaFieldRecord.total_liquids_bopd` | Four-column frame; total liquids bopd | Crude plus NGL; `annual_total` sums monthly rates, without day weighting | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L27-L39] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L83-L98] |
| DPR summaries | Latest rig count by basin; net change bopd per basin-period | Latest is selected by period `idxmax`; net change adds columns | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L37-L67] |
| Country rankings | `country`, `production_kbd` | Optional year filter, then maximum per country, descending; not a multi-year sum | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L116-L145] |
| Decline prediction / fit | Rate array; model, clipped R², RMSE in rate units | Time begins at month 0; fit quality uses the forecast with terminal switching enabled | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L88-L131] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L208-L229] |
| Fiscal result | Revenue, opex, royalty, taxes, income and government take in caller currency | Dataclass does not carry currency or effective-date metadata | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L39-L50] |
| API response | List of `period`, numeric-or-null `value`, `unit` | No geometric coordinate, origin or phase fields are produced by this parser | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L182-L201] |

Before using state output as decline input, the caller shall establish a consistent rate basis: the state loader returns barrel volumes, while the fit interface describes production rates in bopd or Mcfd. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L1-L4] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L164-L170]

UNVERIFIED: production-source vintage, completeness and freshness are not established by mock records or this offline review; obtain a versioned source manifest before downstream use (section 10, item O3).

## 3. Method and governing standards

| Method | Implemented algorithm | Reference status / limitation | Evidence |
| --- | --- | --- | --- |
| Decline rate | q(t) = qi / (1 + b di t)^(1/b); b = 0 uses qi exp(-di t) | Code cites Arps (1945), SPE-945228-G; publication text and bibliographic identity are unverified, rather than asserted as checked | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L7-L21] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] |
| Terminal forecast | For at least 3 rates, with terminal switching enabled and b above its threshold: switch index = max(1, floor(0.6 × horizon)); exponential continuation uses di / (1 + b di × switch index) | Horizon heuristic, not the effective-b criterion described in the docstring; not a hand-check reference | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L88-L104] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131] |
| Decline fitting | SciPy bounded `curve_fit`; initial guesses returned on RuntimeError or ValueError; RMSE and clipped R² returned | Fallback is logged, with no result status flag | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L178-L229] |
| Fiscal arithmetic | Nonnegative rate × gross; income = gross − tax − opex − capex | Code names 30 CFR Part 1206, Texas Tax Code Chapters 201/202 and ND Century Code 57-51/57-51.1; no effective editions or citation sidecars accompany the result | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L9-L30] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L39-L50] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L79-L90] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L118-L156] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L185-L200] |
| Aggregate comparison | Absolute EIA−BSEE difference divided by absolute BSEE reference; fraction compared with configured tolerance | Zero reference uses 1 kbd; retain this qualification when interpreting a percentage | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L217-L243] |
| Normalisation / aggregation | Float coercion, fixed state-volume conversion, group-by sums, exact label filters | These are transformations of supplied records, not evidence of source validity | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L74-L121] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L61-L98] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L96-L145] |
| Cache and throttling | MD5 of series and sorted URL-encoded query parameters; monotonic TTL; minimum request interval | Cache key is not a source-content fingerprint; it omits `use_mock` | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L47-L82] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L163-L168] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L225-L252] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L299-L306] |

UNVERIFIED: fiscal rates' current legal applicability, clause attribution and effective dates have not been checked against the named authorities; do not treat regression assertions as legal validation (O2).

UNVERIFIED: Arps publication identity, applicability of the terminal heuristic and independent real-data decline calibration remain unqualified (O1).

## 4. Validated worked examples and regression examples

Validation here is limited to two closed-form algebraic identities; it does not qualify a real production forecast or fiscal regime. [tests/unit/eia_us/test_basin_decline.py:L17-L46]

Rate examples use the function's documented bopd convention; the tests themselves use scalar rate values without explicit unit objects. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L7-L14] [tests/unit/eia_us/test_basin_decline.py:L17-L46]

| ID / kind | Independent basis or regression source | Inputs and expected value | Tolerance and basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- | --- |
| V1 / validated algebra | Closed form at t = 0: denominator is 1, independently of b and di | t = 0 month, qi = 1000 bopd, di = 0.08 per month, b = 1.5; q = 1000 bopd | `pytest.approx` default tolerance as used by the test | `tests/unit/eia_us/test_basin_decline.py::TestArpsHyperbolic::test_at_t0_equals_qi` | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_basin_decline.py:L17-L20] |
| V2 / validated algebra | Harmonic closed form: 1000 / (1 + 0.05 × 12) = 625 | t = 12 months, qi = 1000 bopd, di = 0.05 per month, b = 1; q = 625 bopd | Relative 0.0001 (0.1 bopd rounded upward); test-defined arithmetic tolerance | `tests/unit/eia_us/test_basin_decline.py::TestArpsHyperbolic::test_b_equals_1_harmonic_case` | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_basin_decline.py:L34-L38] |
| R1 / regression | Synthetic loader record in test | 10 thousand bbl → 10000 bbl | `pytest.approx` default; transformation regression | `tests/unit/eia_us/test_state_production.py::TestStateProductionLoader::test_load_converts_thousand_barrels_to_bbl` | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_state_production.py:L90-L100] |
| R2 / regression | Synthetic API dictionary in test | 2 rows; first value string becomes 12345.0 in retained source unit | Exact numeric equality and row count; parser regression | `tests/unit/eia_us/test_eia_api_client.py::TestEIAApiClientFetch::test_parse_series_response_extracts_data` | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_eia_api_client.py:L117-L129] |
| R3 / regression | Constructed decline model in test | Requested 24 months → 24 forecast elements | Exactly 24 elements; shape regression only | `tests/unit/eia_us/test_basin_decline.py::TestHyperbolicDeclineModel::test_predict_length_matches_horizon` | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_basin_decline.py:L72-L75] |
| R4 / regression | Built-in mock country records | `top_producers(n=5)` → 5 ranked rows | Exactly 5 rows, descending predicate in test | `tests/unit/eia_us/test_international_production.py::TestCountryProductionLoader::test_top_n_producers` | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_international_production.py:L85-L93] |
| R5 / regression | Zero-revenue fiscal fixture | Gross = 0 caller currency; opex = 0; severance = 0 | Exact zero; no current tax-rate qualification | `tests/unit/eia_us/test_us_fiscal.py::TestTexasFiscal::test_zero_revenue_zero_tax` | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_us_fiscal.py:L92-L94] |

The state annual-total test checks the column and year, without asserting the total value; the terminal-switch test checks positivity without asserting the switch location or the claimed relative decline behaviour. [tests/unit/eia_us/test_state_production.py:L119-L124] [tests/unit/eia_us/test_basin_decline.py:L87-L98]

## 5. QA gates

The applied family set is AQG r0, section 10, Python calculations: G0 inputs/units/citations; G1 imports/tests; G2 hand or published check; G3 and G4 not applicable; G5 evidence. (AQG, revision 0, sections 9–11.)

Criteria below are pack requirements; the cited nodes are executable checks, and the result column records execution separately from source behaviour.

| Gate | Applicability | Check ID and executable route | Numeric pass criterion and unit | Evidence / result |
| --- | --- | --- | --- | --- |
| G0 | Applicable | C01: `StateProductionLoader.load`; run R1 | 10000 bbl from 10 thousand bbl; absolute error ≤ 0.01 bbl (test default relative tolerance at this value) | R1 PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_state_production.py:L90-L100] |
| G0 | Applicable | C02: `EIAApiClient.parse_series_response`; run `tests/unit/eia_us/test_eia_api_client.py::TestEIAApiClientFetch::test_parse_series_response_handles_null_value` | 1 returned record; 0 substituted numeric values for its null input | PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_eia_api_client.py:L136-L145] |
| G1 | Applicable | C03: `uv run --extra test --group benchmark python -m pytest tests/unit/eia_us tests/benchmarks/test_eia_benchmarks.py -q -rA -p no:cacheprovider --basetemp=<scratch>` | 146 collected cases; 0 failures, 0 collection errors, 0 skips, 0 NOT_RUN cases; unit: case | Offline Python import and pytest route; no target solver format is written by these tests; [tests/unit/eia_us/test_basin_decline.py:L6-L12] [tests/benchmarks/test_eia_benchmarks.py:L63-L76] |
| G2 | Applicable | C04: run V1 against q(0) = qi; call `arps_hyperbolic` directly, without terminal forecast | 1000 bopd; absolute error ≤ 0.001 bopd (test default relative tolerance) | V1 PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_basin_decline.py:L17-L20] |
| G2 | Applicable | C05: run V2 against harmonic closed form | 625 bopd; relative error ≤ 0.0001; equivalent absolute bound 0.1 bopd rounded upward | V2 PASS at BASE; PASS at AFTER; [tests/unit/eia_us/test_basin_decline.py:L34-L38] |
| G3 | NOT_APPLICABLE | No short dynamics model in the declared calculation and ingestion scope | No dynamic solver case | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L1-L17] |
| G4 | NOT_APPLICABLE | No diffraction mesh or hydrodynamic body model in the declared scope | No diffraction body | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L1-L17] |
| G5 | Applicable | C06: resolve every source citation with `git show <code revision>:<path>`; match section-4 node IDs with pytest output | 0 missing files/ranges; 7 case records with inputs, expected result, tolerance, node and offline result; unit: record | Citation resolver and full test logs retained with review evidence; source examples: [tests/unit/eia_us/test_basin_decline.py:L17-L38] |
| G5 | Applicable | C07: reconcile section-10 issue references and this revision's test record before issuing an analysis | 0 open items without an issue number or numbered issue draft; unit: item | Second-provider clearance and issue-number substitution remain required; AQG r0, sections 9 and 11 |

### Execution record

At code revision `285d65c40896b17ccf44568e59f5b789d59c943e`, the unit command completed 144 cases: 144 PASS, 0 FAIL, 0 SKIP, 0 NOT_RUN. The separate benchmark command completed 2 cases: 2 PASS, 0 FAIL, 0 SKIP, 0 NOT_RUN. Both used the ordinary source-enabled `uv run` form with the declared test extra; benchmarks also enabled the declared benchmark group. Coverage and benchmark outputs were directed to scratch. AFTER combined the same unit and benchmark paths in one command: 146 PASS, 0 FAIL, 0 SKIP, 0 NOT_RUN; every node outcome matches BASE. All three commands exited 0; BASE ran before the documentation edit and AFTER ran on the uncommitted documentation tree at the same code pin. The module source is unchanged.

No production API request, licensed interface or solver was run. Source-content fingerprints, production-source qualification and second-provider gate signatures are not established by this test record; these remain O3 and O6 rather than implied PASS records.

AFTER used the documented `--allow-existing-tree-changes` option: it records initial changed-file content, requires that content to remain identical, and still rejects undeclared mutations. [tests/conftest.py:L383-L461]

## 6. Known failure modes and pitfalls

The following findings are source inspections at the code revision; a proposed detection check is not represented as an existing test.

| Symptom | Cause and evidence | Detection check / coverage | Follow-up | Recorded date |
| --- | --- | --- | --- | --- |
| Fit fallback looks like a fitted result | RuntimeError/ValueError returns initial guesses, followed by ordinary model/metrics construction | Proposed forced-fit-error test: require 1 explicit fallback status; no detection check exists in the current suite | issue pending (1); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L189-L219] | 2026-10-15 |
| Earlier forecast values depend on total requested horizon | Fixed 60% switch index replaces the documented effective-b criterion | Proposed prefix-equality check: same first 24 months for horizons 24 and 120, within 0.000001 bopd; existing positivity assertion does not detect it | issue pending (1); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131] [tests/unit/eia_us/test_basin_decline.py:L87-L98] | 2026-10-15 |
| Live-mode fetch can reuse synthetic data | Cache hit precedes mock-mode branch; cache key does not include mode | Proposed mock→live and live→mock isolation tests: 0 cross-mode cache hits; no detection check exists | issue pending (3); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L163-L168] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L225-L255] | 2026-10-15 |
| Unknown units or malformed months can be accepted; missing annual values can become zero | Fixed multiplier, sliced integer period fields, default pandas sum | C01 covers valid conversion only; proposed mismatch, month-13 and all-null tests require 0 silently accepted invalid records; no rejection test exists | issue pending (2); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L74-L113] | 2026-10-15 |
| Annual record-level rates are summed without a volume conversion | `annual_total` sums `crude_bopd` and `ngl_bopd` | Proposed two-month constant-rate check: require 100 bopd mean or 5900 bbl over 31+28 days, after the intended quantity is specified; no detection check exists | issue pending (2); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L83-L98] | 2026-10-15 |
| Fiscal results lack effective-date and source sidecars | Scalar rate constants and numeric-only result | Proposed provenance check: 0 externally derived rates without a versioned source record; current constant tests check literals rather than authorities | issue 361; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L24-L50] [tests/unit/eia_us/test_us_fiscal.py:L21-L35] | 2026-10-15 |
| Pack matches runtime-data inclusion | Nested Markdown is included by package-data glob | Proposed wheel-member check: 0 `docs/agent-pack.md` members; no wheel exclusion check exists | issue pending (4); [packages/worldenergydata-eia_us/pyproject.toml:L50-L56] | 2026-10-15 |

No incident issue was specified for this module; issue 361 is the existing provenance follow-up, not a newly verified production incident.

## 7. Lessons log

| Date | Entry ID | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | EIA-US-001 | Compare forecast prefixes before treating the terminal forecast as horizon-independent | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131] | Sections 3 and 6 distinguish the heuristic from its docstring | Pending; O1 |
| 2026-10-15 | EIA-US-002 | Keep mock records, regression assertions and qualified source data distinct | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L74] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L225-L252] | Sections 2, 4 and 6 record source and cache limitations | Pending; O3 |

## 8. Ownership

Review assignment: calculations quality manager, covering data pipelines until a data-pipeline quality manager is appointed; the deputy role remains unassigned. The producing role maintains source citations and offline evidence; the reviewing role uses a different provider. (Module agent lifecycle, revision 0, sections 4–6; AQG r0, section 11.)

Escalation requirements: ambiguous source basis, changed numerical criteria and unresolved gate failures go to the quality manager; cross-family and priority questions go to the maintainers. No independent clearance is asserted by this DRAFT pack. (Module agent lifecycle, revision 0, section 4, step E; AQG r0, section 11.)

## 9. Dependencies and implementation inventory

| Relationship | Verified interface / limit | Evidence |
| --- | --- | --- |
| Declared dependencies | `worldenergydata-core`, NumPy, pandas, SciPy | [packages/worldenergydata-eia_us/pyproject.toml:L25-L33] |
| Runtime numerical dependencies | NumPy arrays and SciPy `curve_fit`; pandas frames | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L88-L104] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L189-L212] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L99-L113] |
| Optional live HTTP dependency | `requests` is imported inside `_fetch_live`; missing import raises an API error | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L257-L270] |
| Upstream inputs | Caller dictionaries/arrays; optional EIA response records; built-in country and client mock data are distinct from qualified production data | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L87-L102] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L74] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L53-L67] |
| Related ingestion path | `EiaUsRefreshJob.run` invokes the sibling `EIAIngestionSync`, then writes snapshots and metadata; this does not establish a refresh of these analytic fixtures | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/eia_us_refresh.py:L39-L75] |
| External consumer lead | The architecture decision records external imports of this package; their present runtime state was not checked | [docs/adr/0001-domain-package-split.md:L83-L89] |

### A8 inventory record

External map reference: `digitalmodel`, `docs/registry/implementation-map.yaml`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, declared data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`; map bytes SHA-256 `ff8e59964cf4719b34caca3880e0b213a79c48546b49fb7fcb8ca6394e78001a`.

Local inventory result: 13 map families, 2322 implementation rows, 0 rows under the header package path, 0 module map families. The required section-9 inventory is empty. Counted families: 0. Counted grep: `NOT_APPLICABLE`, because no map family has an in-package implementation row. A8 passes the empty-inventory case; no grep-based completeness claim is made. The map reference and counts are recorded review inputs, not source-behaviour assertions at the owning code revision.

Map follow-up: issue pending (5). Add repository-qualified rows and exact search signals for every section-3 family: decline evaluation, terminal continuation, bounded fitting and quality metrics; fiscal arithmetic and aggregate comparison; production normalisation/aggregation and rankings; response parsing, TTL caching and interval throttling. These families are not counted until the map contains in-package rows.

### Further repository search

The supplemental search covered tracked Python paths throughout the repository, including `scripts/`, using definition patterns for hyperbolic decline, decline classes, EIA clients, annual totals and fiscal classes; these findings do not alter A8.

| Definition / classification | Evidence and disposition |
| --- | --- |
| `arps_hyperbolic`; independent rate evaluation, already listed in section 3 | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] |
| `HyperbolicDeclineModel._apply_terminal_switch`; independent continuation, already listed | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131] |
| `ShaleDeclineAnalyzer.fit` and `_r_squared`; fitting / metrics, already listed | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L178-L229] |
| `ShaleDeclineResult.predict`; helper delegation | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L137-L148] |
| `DrillingProductivityReport.load_all_basins`; loader wrapper | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L20-L35] |
| `DrillingProductivityReport.rig_count_summary` and `net_change_summary`; independent summaries | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L37-L67] |
| `ProductionForecaster.hyperbolic_decline`; outside-package independent implementation using time in years | [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L327-L353]; map gap, issue pending (5) |
| `ArpsDeclineCurve`; outside-package fitting/forecasting surface | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L72-L130]; map follow-up, issue pending (5) |
| `EIAFeedClient`; separate weekly-feed client, not a delegation to this client's series route | [packages/worldenergydata-eia/src/worldenergydata/eia/client.py:L48-L92]; map follow-up, issue pending (5) |

Additional regional and dashboard decline candidates were returned by the supplemental search; equivalence, consolidation and exhaustive outside-package coverage remain O5, rather than an inferred implementation inventory.

## 10. Coverage and open items

### Files read and test coverage

All 13 Python files in the package were inspected, including the root and four subpackage initialisers; all seven unit-test files and the loader benchmark file were read. The source inventory below binds the inspection scope to the code pin.

| Scope | Pinned evidence |
| --- | --- |
| Package declaration | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/__init__.py:L1-L20] |
| Analysis initialiser, decline, fiscal | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L1-L229] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L1-L243] |
| Client initialiser and client | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L1-L306] |
| International initialiser and loader | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L1-L145] |
| Production initialiser and four modules | [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/__init__.py:L1-L1] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L1-L112] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/basin_production.py:L1-L116] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L1-L67] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L1-L121] |
| Package README and packaging | [packages/worldenergydata-eia_us/README.md:L1-L8] [packages/worldenergydata-eia_us/pyproject.toml:L1-L56] |
| API tests: 25 functions | [tests/unit/eia_us/test_eia_api_client.py:L1-L181] |
| State tests: 19 functions | [tests/unit/eia_us/test_state_production.py:L1-L139] |
| Basin tests: 17 functions | [tests/unit/eia_us/test_basin_production.py:L1-L138] |
| Record-level tests: 13 functions | [tests/unit/eia_us/test_alaska_production.py:L1-L118] |
| Country tests: 19 functions | [tests/unit/eia_us/test_international_production.py:L1-L104] |
| Decline tests: 22 functions | [tests/unit/eia_us/test_basin_decline.py:L1-L183] |
| Fiscal tests: 29 functions | [tests/unit/eia_us/test_us_fiscal.py:L1-L190] |
| Loader benchmarks: 2 functions | [tests/benchmarks/test_eia_benchmarks.py:L63-L76] |

The recount is 144 unit-test functions plus 2 benchmark functions, rather than a qualification inferred from an inventory label. No dedicated drilling-productivity summary test appears in these files; follow-up O6.

The following 23 matching documents under `docs/` were discovered and their module-related passages inspected; historical counts, refresh outcomes and readiness claims were not adopted as current findings. Documentation reconciliation remains O7.

| Document | Module passage |
| --- | --- |
| `docs/adr/0001-domain-package-split.md` | [docs/adr/0001-domain-package-split.md:L46-L48] |
| `docs/modules/repository-architecture.md` | [docs/modules/repository-architecture.md:L101-L103] |
| `docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md` | [docs/plans/2026-04-26-issue-353-diagnose-uv-scheduler-noop-timeouts.md:L19-L21] |
| `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md` | [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L68-L70] |
| `docs/plans/2026-05-04-issue-266-eia-scheduler-operationalize.md` | [docs/plans/2026-05-04-issue-266-eia-scheduler-operationalize.md:L10-L12] |
| `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L20-L22] |
| `docs/plans/2026-05-04-issue-351-scheduler-readiness-matrix.md` | [docs/plans/2026-05-04-issue-351-scheduler-readiness-matrix.md:L36-L38] |
| `docs/plans/2026-05-04-issue-360-scheduler-health.md` | [docs/plans/2026-05-04-issue-360-scheduler-health.md:L37-L39] |
| `docs/plans/2026-05-08-issue-394-repo-structure-normalization.md` | [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L69-L71] |
| `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` | [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L26-L28] |
| `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` | [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L48-L50] |
| `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` | [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L199-L201] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L15-L17] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L195-L197] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L14-L16] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L15-L17] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.yaml:L132-L134] |
| `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` | [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L68-L70] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L40-L42] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L11-L13] |
| `docs/reports/2026-04-27-plan-354-adversarial-review.md` | [docs/reports/2026-04-27-plan-354-adversarial-review.md:L8-L10] |
| `docs/reports/data-freshness-scorecard-2026-06-08.md` | [docs/reports/data-freshness-scorecard-2026-06-08.md:L8-L10] |
| `docs/reports/scheduler-health-2026-W24.md` | [docs/reports/scheduler-health-2026-W24.md:L12-L14] |

No routing registry is present at `docs/registry/module-routing.yaml` at the code pin; no replacement registry or top-level domain entry is created. The existing package README identifies the workspace-member relationship. [packages/worldenergydata-eia_us/README.md:L1-L8]

### Open-item register

| ID | Gap / required next evidence | Responsible role | Issue |
| --- | --- | --- | --- |
| O1 | UNVERIFIED reference applicability: confirm the Arps publication identity, replace or qualify horizon switching, expose fit fallback, and obtain an independent decline dataset | Calculations quality manager / maintainer | issue pending (1); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L16-L21] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L106-L131] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L189-L219] |
| O2 | UNVERIFIED fiscal authority: effective editions, applicable rates, clause attribution and result Citation sidecars; do not use literal-value tests as legal acceptance | Maintainer / calculations quality manager | issue 361; [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L9-L50] [tests/unit/eia_us/test_us_fiscal.py:L21-L35] |
| O3 | UNVERIFIED production readiness: versioned source manifest, freshness, completeness and source digests; distinguish fixtures from observations and isolate mock/live caching | Data maintainer | issue 462 and issue pending (3); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/international/country_production.py:L47-L74] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/client/eia_api.py:L225-L252] |
| O4 | Specify units and reject invalid records; qualify annual-rate aggregation and missing-value treatment | Data maintainer / calculations quality manager | issue pending (2); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/state_production.py:L74-L113] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/alaska_production.py:L83-L98] |
| O5 | Populate implementation-map families and classify outside-package decline candidates before any consolidation | Maintainer | issue pending (5); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] |
| O6 | Add independently sourced end-to-end examples and direct summary tests; appoint the deputy, obtain independent clearance and replace draft references with issue numbers | Calculations quality manager / maintainer | issue pending (6); [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/production/drilling_productivity.py:L37-L67] |
| O7 | Reconcile historical documentation, test counts and namespace/readiness descriptions against present code rather than inheriting report claims | Documentation maintainer | issue 349; [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L129-L159] |
| O8 | Exclude this documentation from wheel data; current nested-Markdown inclusion is unchanged by this pack | Package maintainer | issue pending (4); [packages/worldenergydata-eia_us/pyproject.toml:L50-L56] |

The calculation citation contract was read as a reference; no new formula or standards-derived constant is introduced by this documentation change. Existing numeric-only fiscal outputs remain O2. [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L24-L50]
