# Production module knowledge pack

| Header | Value |
| --- | --- |
| Module | production |
| Repository | worldenergydata |
| Package path | `packages/worldenergydata-production/src/worldenergydata/production` |
| Pack revision | 0; 2026-10-15 |
| Code revision | `13f3b70aa7a87045631b737406c881e4cb5bcfd0` |
| Analysis family | EC; data pipelines and Python calculations |
| Quality manager | Independent calculations quality manager |
| Status | DRAFT; clearance pending |

## 1. Purpose and scope

The package exports `UnifiedProductionClient`, `ArpsDeclineCurve` and `ForecastResult` for cross-regional queries and decline forecasting. [packages/worldenergydata-production/src/worldenergydata/production/__init__.py:L1-L11]

`UnifiedProductionClient.query()` resolves regions, fetches adapter frames, concatenates nonempty frames, validates the merged schema, normalizes numeric columns, and returns summaries and coverage gaps. [packages/worldenergydata-production/src/worldenergydata/production/unified/__init__.py:L58-L104]

`RegionRouter` registers 10 canonical adapters; aliases are stripped and lowercased, and duplicate regions are removed in first-occurrence order. [packages/worldenergydata-production/src/worldenergydata/production/unified/router.py:L90-L154]

The default SODIR, Brazil and UKCS routes generate synthetic profiles unless a loader is supplied; BSEE, EIA US, Mexico and Texas also generate profiles rather than loading measured records. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py:L1-L182] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L1-L177] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py:L1-L167] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/bsee_adapter.py:L1-L105] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L1-L105] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/mexico_cnh_adapter.py:L1-L103] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/texas_rrc_adapter.py:L1-L104]

Australia returns an empty production frame and exposes metadata separately; Canada defaults to a labeled synthetic fixture; Spain uses a fixture loader with an embedded fallback when its source package is unavailable. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/australia_adapter.py:L1-L54] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/canada_adapter.py:L1-L115] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L1-L184]

Package metadata declares alpha maturity; this is a packaging declaration rather than evidence of engineering validation. [packages/worldenergydata-production/pyproject.toml:L15-L23]

## 2. Inputs and outputs

### Inputs

| Name | Unit / convention | Range and default | Source and evidence |
| --- | --- | --- | --- |
| `ProductionQuery.regions` | Region keys, dimensionless | Required list; unknown keys raise `KeyError` | [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L30-L46] [packages/worldenergydata-production/src/worldenergydata/production/unified/router.py:L147-L155] |
| `fields`, `start`, `end` | Text keys; inclusive calendar `YYYY-MM` | Default `None`; field comparison is case-insensitive | [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L34-L46] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/base.py:L1-L123] |
| `parameters` | Stream-column names | Defaults to oil, gas and water; stored in query | [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L43-L46] |
| `production` for `fit()` | `month`: 1-based month; `rate_bbl`: bbl/month | Empty input rejected; no general finite/nonnegative validation at this entry | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L82-L117] |
| `model`, `economic_limit`, `months` | Model key; bbl/month; months | Defaults hyperbolic, 10.0, 120; EUR clamps the limit to at least 1.0 bbl/month | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L71-L77] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L279-L290] |
| Fitting bounds | `qi`: bbl/month; `Di`: 1/month; `b`: dimensionless | Nonnegative `qi`; `Di` at least 0.000001; hyperbolic `b` from 0.000001 to 1.999999 | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L200-L257] |
| Fiscal sensitivity | `oil_price_usd`: USD/bbl | Required price; annual discount constant is converted to a monthly rate | [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L82-L83] [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L167-L175] [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L209-L230] |
| Benchmark depth mapping | Water depth, ft | Missing depth assigned `unknown` through the FDAS classifier | [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L134-L160] |

### Outputs

| Name | Unit / convention | Missing/default behavior | Evidence |
| --- | --- | --- | --- |
| `ProductionResult.data` | `region`, `field_name`, calendar year/month, `source`; oil/water/condensate in bbl and gas in Mcf per monthly row | Nine standard columns; numeric values coerced to float64, invalid numeric text becomes NaN | [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L16-L26] [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L53-L76] |
| Summary | Peak monthly oil volume, cumulative oil and mean monthly oil in bbl; non-null month count | Grouped by region and field; peak is not a daily rate | [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L78-L112] |
| Coverage gaps | Missing-month count | Only a list of positive counts is returned; limitations in section 6 | [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L114-L155] |
| `ForecastResult` | `qi` bbl/month, `Di` 1/month, `b` and R² dimensionless, EUR bbl | Confidence frames default to `None` | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L22-L57] |
| Forecast frame | `month` 1-based; `rate_bbl` bbl/month; `cumulative_bbl` bbl | Cumulative is a discrete sum from month 1; the frame restarts at month 1 rather than continuing after the last observed month | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L316-L336] |
| Engine artifacts | Cases CSV and summary JSON | `ProductionForecast.router()` writes fitted parameters and EUR for configured cases | [packages/worldenergydata-production/src/worldenergydata/production/forecast/router.py:L31-L81] |
| CLI artifact | Plotly HTML | Written only with an output option; absent CSV input uses a synthetic profile | [packages/worldenergydata-production/src/worldenergydata/production/forecast/cli.py:L93-L115] [packages/worldenergydata-production/src/worldenergydata/production/forecast/cli.py:L141-L145] |
| Benchmark artifacts | HTML and JSON; cash flow USD and government take percent | Empty regions are screening-only; discounted historical post-tax cash flow excludes capital expenditure | [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L230-L311] [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L537-L586] |

Coordinate axes, spatial origin and phase conventions are not inputs to the query or forecast APIs; their independent coordinates are calendar month and elapsed month respectively. [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L30-L46] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L82-L91]

## 3. Method and governing standards

| Method | Implementation and interpretation | Reference / qualification |
| --- | --- | --- |
| Exponential, harmonic and hyperbolic decline fitting | `ArpsDeclineCurve._fit_params()` uses nonlinear least squares, with separate rate formulas and bounds | Code identifies Arps; no edition or published equation citation is supplied in this implementation. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L1-L6] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L200-L257] |
| EUR | `_compute_eur()` integrates the fitted rate to the clamped economic limit, switches to harmonic near `b=1`, and clips negative output to zero | The exact formula branches are code evidence, not an independently validated reference. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L279-L308] |
| Fit quality | `_r_squared()` computes one minus residual sum of squares divided by total sum of squares; near-constant observations return 1.0 | The constant-data branch does not establish fit quality for arbitrary constant observations. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L310-L316] |
| Adapter filtering | `_filter_by_date()` compares integer year-month keys inclusively; `_filter_by_fields()` lowercases text | No unit conversion occurs in these helpers. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/base.py:L1-L123] |
| Unit conversion | SODIR injected-loader condensate uses `OilUnits.SM3_TO_BBL`; produced water remains NaN, not injected-water volume | The conversion constant is imported from shared units, rather than independently sourced here. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py:L1-L182] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py:L1-L182] |
| Historical cumulative comparison | `compare_cumulative_eur()` sums historical oil and gas, converting gas to oil equivalent using its code constant | The function explicitly distinguishes historical sums from forward-looking EUR. [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L127-L164] |
| Fiscal comparison | `fiscal_sensitivity()` applies royalty, then tax on the remainder, discounts sorted rows by row number, and rounds money to whole USD | Coefficients are illustrative approximations; missing calendar months do not introduce additional discount periods. [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L1-L7] [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L209-L245] |
| Benchmark provenance | `provenance_by_region()` accepts a region as real only when every normalized source tag belongs to its allowlist | This checks labels, not source rights, freshness or measurement provenance. [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L102-L131] |

UNVERIFIED: external validity and current applicability of the fiscal coefficients and gas-to-oil-equivalent convention are not established by the local formulas or tests; issue 361 covers citation sidecars and provenance, and issue pending (3) covers independent validation. [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L15-L83] [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L160-L163]

No licensed standard is used as an independently checked reference in this pack; the decline implementation supplies formulas without a numbered governing standard or a `Citation` sidecar. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L200-L307]

## 4. Validated worked examples

Validated cases: **0**; the selected existing tests use synthetic profiles or canned fixtures rather than an independently versioned production benchmark. [tests/unit/production/forecast/test_decline.py:L1-L46] [tests/unit/production/unified/test_benchmark_report.py:L43-L115]

The following five cases are regression examples; PASS records refer to the offline runs at the header code revision, not to regulatory-data qualification. [tests/unit/production/forecast/test_decline.py:L49-L60] [tests/unit/production/unified/test_normalizer.py:L114-L132] [tests/unit/production/unified/test_benchmark_report.py:L163-L187] [tests/unit/production/unified/test_benchmark_report.py:L239-L243]

| Case | Source and input | Expected / tolerance | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 exponential fit | Seeded synthetic exponential profile from `_make_synthetic`, 60 months, relative noise 0.02 | `qi` 4000.0 bbl/month; relative error less than 5.0%, the test's criterion | `tests/unit/production/forecast/test_decline.py::TestArpsDeclineCurveFit::test_fit_exponential_recovers_qi` | PASS. [tests/unit/production/forecast/test_decline.py:L17-L60] |
| R2 hyperbolic fit | Seeded synthetic hyperbolic profile from `_make_synthetic` | `qi` 5000.0 bbl/month; relative error less than 5.0%, the test's criterion | `tests/unit/production/forecast/test_decline.py::TestArpsDeclineCurveFit::test_fit_hyperbolic_recovers_qi` | PASS. [tests/unit/production/forecast/test_decline.py:L17-L55] |
| R3 same-year gap | Two fixture rows at calendar months 1 and 3 | One gap record, `gap_months` exactly 1 month; zero tolerance | `tests/unit/production/unified/test_normalizer.py::TestNormalizerCoverageGaps::test_detects_gap_in_series` | PASS. [tests/unit/production/unified/test_normalizer.py:L114-L132] |
| R4 empty source | Fake router with one empty region and one populated region | Empty region omitted from output rows, included in `skipped_empty`, at least 1 warning record | `tests/unit/production/unified/test_benchmark_report.py::test_empty_region_is_skipped_with_warning_not_zero_rows` | PASS. [tests/unit/production/unified/test_benchmark_report.py:L163-L187] |
| R5 unknown provenance | Canned source tag outside the real-source allowlist | Exactly 1 seed classification; zero real classifications | `tests/unit/production/unified/test_benchmark_report.py::test_unknown_source_is_seed` | PASS. [tests/unit/production/unified/test_benchmark_report.py:L239-L243] |

Offline command form: `uv run python -m pytest <paths> -q -rA -p no:cacheprovider --basetemp=<scratch>`; ordinary workspace resolution, original addopts, no extra pytest workers, no source fallback. Production suite: BASE and repeat each 239 passed, 0 failed, 0 skipped, 0 NOT_RUN. Consumer suite: BASE and repeat each 53 passed, 0 failed, 0 skipped, 0 NOT_RUN. The module suite includes parameterized adapter conformance as well as the selected examples. [tests/unit/production/unified/test_adapters.py:L29-L91]

## 5. QA gates

The governing family set is AQG r0, section 10, Python calculations: G0 inputs/units/citations; G1 imports/tests; G2 hand or published check; G3 and G4 not applicable; G5 evidence appendix (AQG r0, sections 9–10).

| Gate | Applicability and route | Check IDs |
| --- | --- | --- |
| G0 | Applicable: schema, month units, missing streams and source labels | C01–C03. [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L16-L46] |
| G1 | Applicable: Python imports and offline pytest; no solver program is written by the forecast CSV/JSON and Plotly HTML routes | C04–C05. [packages/worldenergydata-production/src/worldenergydata/production/forecast/router.py:L55-L73] [packages/worldenergydata-production/src/worldenergydata/production/forecast/cli.py:L141-L145] |
| G2 | Applicable: independent arithmetic check and synthetic parameter recovery; the latter remains regression evidence | C06–C07. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L279-L308] [tests/unit/production/forecast/test_decline.py:L49-L60] |
| G3 | NOT_APPLICABLE: no dynamic simulation in the fitted-rate and query paths | AQG r0 section 10; [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L113-L133] [packages/worldenergydata-production/src/worldenergydata/production/unified/__init__.py:L70-L103] |
| G4 | NOT_APPLICABLE: no diffraction body or mesh is an input to these paths | AQG r0 section 10; [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L30-L46] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L82-L95] |
| G5 | Applicable: report provenance, empty-region disposition and reproducible evidence; clearance signature remains pending | C08–C10; AQG r0 section 9. [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L230-L311] |

| ID | Module-specific executable check | Numeric pass criterion and unit | Evidence / current result |
| --- | --- | --- | --- |
| C01 / G0 | `TestAdapterSchemaCompliance::test_fetch_returns_standard_columns` over the nine volume-producing adapter classes | 0 absent columns from the 9-column `STANDARD_COLUMNS` contract | PASS; parameterized test results. [tests/unit/production/unified/test_adapters.py:L29-L51] |
| C02 / G0 | `TestAdapterSchemaCompliance::test_month_values_in_range` | Every calendar month in [1, 12] months; 0 out-of-range rows | PASS. [tests/unit/production/unified/test_adapters.py:L87-L91] |
| C03 / G0 | `test_fetch_transforms_loader_output_to_standard_columns` in the SODIR adapter suite | 1 filtered row; 1 unknown produced-water value; 0 injected-water columns | PASS; conversion assertions additionally use `pytest.approx`. [tests/unit/production/unified/test_sodir_adapter_loader.py:L58-L84] |
| C04 / G1 | Import package through the production suite, run `tests/unit/production` | 239 passing test cases; 0 failures and 0 skipped cases | PASS at BASE and repeat; no solver required by these tests. [tests/unit/production/forecast/test_decline.py:L9-L14] [tests/unit/production/unified/test_unified_client.py:L6-L14] |
| C05 / G1 | Run the ten discovered importing consumer test files listed in section 10 | 53 passing test cases; 0 failures and 0 skipped cases | PASS at BASE and repeat; consumer contract route includes `to_fdas_production`. [tests/unit/production/unified/test_sodir_adapter_loader.py:L87-L95] |
| C06 / G2 | R1 and R2: fit synthetic profiles with independently specified `qi` inputs | Relative initial-rate error less than 5.0% (dimensionless) for each case | PASS; regression evidence, not real-data validation. [tests/unit/production/forecast/test_decline.py:L49-L60] |
| C07 / G2 | Hand integral of exponential profile: integral from 0 to `ln(qi/q_limit)/Di` equals `(qi-q_limit)/Di`; compare `_compute_eur(4000,0.1,0,10,'exponential')` | Expected 39900.0 bbl; absolute error at most 0.00000001 bbl | PASS: actual 39900.0 bbl, error 0.0 bbl; calculation recorded separately from pytest; input basis is R1 and the default limit. [tests/unit/production/forecast/test_decline.py:L57-L60] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L71-L77] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L289-L296] |
| C08 / G5 | `test_render_row_badge_matches_provenance` | 0 mismatches between visible badge and row provenance; at least 1 rendered row | PASS. [tests/unit/production/unified/test_benchmark_report.py:L259-L279] |
| C09 / G5 | R4 plus `TestRegionStatus::test_region_status_covers_every_requested_region` | 0 fabricated rows for empty source; exactly 3 requested-region statuses in fixture | PASS. [tests/unit/production/unified/test_benchmark_report.py:L163-L187] [tests/unit/production/unified/test_benchmark_report.py:L331-L336] |
| C10 / G5 | `test_discount_rate_mismatch_raises` | Exactly 1 `ValueError` for unsupported annual discount 0.15 (dimensionless) | PASS; report cannot silently claim an unsupported rate. [tests/unit/production/unified/test_benchmark_report.py:L294-L299] |

The hand integral covers one exponential EUR branch only; harmonic and hyperbolic independent benchmark coverage remains issue pending (3), and G5 clearance is not established by these producer checks (AQG r0, sections 9 and 11). [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L298-L307]

## 6. Known failure modes and pitfalls

| Symptom | Cause / limit | Detection and disposition | Incident / tracking |
| --- | --- | --- | --- |
| False missing-month counts across year boundaries | `find_coverage_gaps()` combines separate year and month extrema; contiguous December/January rows report 22 gaps instead of 0 | C02 does not catch this; no detection check exists in the existing same-year regression. A separate arithmetic probe reproduced the 22-month excess; add a paired-year and duplicate-period regression | issue pending (1). [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L139-L155] [tests/unit/production/unified/test_normalizer.py:L107-L138] |
| Missing rows and NaN gaps remain undisclosed | `normalize()` only casts/sorts; gap detection uses row count rather than distinct valid periods, contrary to the fill/NaN promises in its docstrings | No detection check exists for inserted rows or NaN-only gaps; C03 only checks one adapter's unknown-water handling | issue pending (1). [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L1-L10] [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L53-L76] [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L114-L155] |
| A synthetic default can be mistaken for measured production | Default adapters generate rows; benchmark code distinguishes allowed source tags from seed tags | C08 and R5; retain explicit synthetic/seed labels, never use test success as source qualification | issue 819 preserves the Canada public-data restriction; no legal clearance is asserted. [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L68-L90] [tests/unit/production/unified/test_canada_cnloer_adapter_loader.py:L106-L114] |
| Injected UKCS condensate absent | Mapping explicitly assigns NaN | `test_fetch_transforms_nsta_loader_output_to_standard_columns` checks 1 unknown condensate value; preserve unknown status | issue 796. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py:L1-L167] [tests/unit/production/unified/test_ukcs_adapter_loader.py:L79-L90] |
| Empty-region economics fabricated as zeros | Benchmark deliberately skips empty adapter output with warning and screening-only status | C09 and R4 | Existing lesson is recorded in code and tests; issue 823 tracks the missing Australia production feed. [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L230-L241] [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L282-L292] |
| Generic fiscal values silently substituted | Named fallback is observable with `fiscal_regime_source`; routed-region coverage is tested | `TestFiscalRegimeCoverage::test_every_routed_region_has_a_country_specific_regime`, criterion 0 missing region regimes | issue 831; this is a regression incident, not fiscal validation. [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L69-L100] [tests/unit/production/unified/test_cross_basin.py:L278-L288] |
| Pack included in built distribution | Member package-data glob includes `**/*.md`; the proposed documentation path matches it | Static glob check; no existing exclusion test was found; package configuration remains unchanged | issue pending (2). [packages/worldenergydata-production/pyproject.toml:L54-L59] |

No specific incident issue was supplied in the module brief; the issue counts in discovery are not treated as an incident inventory. Confirmed incidents and limits above are bound to the cited implementation and test evidence. [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L139-L155] [tests/unit/production/unified/test_cross_basin.py:L255-L288]

## 7. Lessons log

| Date | Record | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | Separate synthetic-regression success from measured-data validation | [tests/unit/production/forecast/test_decline.py:L1-L46] [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L102-L131] | Sections 1, 4 and 6 distinguish source status | Not assigned; issue pending (3) |
| 2026-10-15 | Initial pack | A same-year missing-month test does not cover paired-year boundaries | [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L139-L155] [tests/unit/production/unified/test_normalizer.py:L114-L132] | Section 6 records the cross-year defect | Not assigned; issue pending (1) |

## 8. Ownership

Required review assignment: independent calculations quality manager, with an independent calculations reviewer as deputy to be designated by the maintainer; producing discipline: production data pipelines and calculations. Clearance remains pending, and unresolved criteria, tolerances or source qualifications go to the calculations quality manager (AQG r0, sections 10–11).

No dedicated data-pipeline quality manager or deputy appointment is established by repository code; issue pending (3) tracks the assignment and clearance evidence (AQG r0, section 11).

## 9. Dependencies and alternative implementations

The member declares shared core, NumPy, pandas, Plotly, Rich, SciPy and Typer dependencies; source loaders are imported at adapter boundaries. [packages/worldenergydata-production/pyproject.toml:L29-L37] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/canada_adapter.py:L1-L115] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L1-L184] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/australia_adapter.py:L1-L54]

The FDAS production bridge is a downstream consumer of unified frames, and benchmark concept classification delegates to `classify_dev_system_by_depth`; neither delegation is a second implementation of that delegated method. [tests/unit/production/unified/test_brazil_anp_adapter_loader.py:L95-L103] [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L150-L160]

Implementation-map data pin: `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, `docs/registry/implementation-map.yaml` in repository digitalmodel; its header names code revision `947fa50ff9a9e210de7e8f90e01b37add85c5954` (implementation map, schema version 1, header and families, data pin above).

The map contains 13 families and **0** implementation rows inside this pack's package, so the section-9 map inventory is empty; counted families are empty and the counted-family signal grep is **NOT_APPLICABLE**, because no family has an in-package row (implementation map, schema version 1, families/implementations, data pin above).

Map follow-up: add the section-3 families—Arps decline fitting and EUR, date/field filtering, monthly normalization and coverage, unit conversions, historical cumulative comparison, fiscal sensitivity, and provenance classification—before counting them in a later map revision; issue pending (4) (implementation map, schema version 1, families, data pin above).

A separate whole-repository Python search, including `scripts/`, found the following alternatives and delegates; these findings do not change the empty counted-family result. [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L300-L353] [scripts/gtm/generate_fdas_gtm_report.py:L138-L158]

| Definition | Classification and reason | Follow-up |
| --- | --- | --- |
| `ProductionForecaster.exponential_decline` and `.hyperbolic_decline` | Independent forecast formulas; annual-to-monthly timing differs from this pack's elapsed-month input | issue 1104; map gap, outside this package. [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L300-L353] |
| Legacy `DeclineCurveAnalyzer.fit_exponential_decline`, `.forecast_production`, `.calculate_eur` | Independent log-linear fit and EUR formulas | issue 1104; map gap, outside this package. [src/worldenergydata/modules/well_production_dashboard/well_detail_views.py:L562-L686] |
| `run_decline_curve_demo` | Synthetic input builder delegates fitting to `ArpsDeclineCurve.fit`; helper, not a further fitted-model implementation | issue 1104 covers consolidation boundaries. [scripts/gtm/generate_fdas_gtm_report.py:L138-L158] |
| `_fit_params` nested rate functions and `_rate_fn` nested functions | Parallel evaluators of the same three rate formulas within the package; both are explicitly inventoried here and in section 3 | issue pending (4), map enrollment; no unlisted counted-family miss. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L200-L277] |
| Adapter `_generate_field_rows` methods | Synthetic profile algorithms, not measured-data loaders; explicitly covered by section 1's synthetic route inventory | issue pending (4), map enrollment. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/bsee_adapter.py:L1-L105] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L1-L105] |

## 10. Coverage and open items

### Source coverage

The source inventory below covers every Python file in the package; subpackages are included in this pack. [packages/worldenergydata-production/src/worldenergydata/production/__init__.py:L1-L11] [packages/worldenergydata-production/src/worldenergydata/production/forecast/__init__.py:L1-L16] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/__init__.py:L1-L37]

- `packages/worldenergydata-production/src/worldenergydata/production/__init__.py`. [packages/worldenergydata-production/src/worldenergydata/production/__init__.py:L1-L11]
- `packages/worldenergydata-production/src/worldenergydata/production/forecast/__init__.py`. [packages/worldenergydata-production/src/worldenergydata/production/forecast/__init__.py:L1-L16]
- `packages/worldenergydata-production/src/worldenergydata/production/forecast/cli.py`. [packages/worldenergydata-production/src/worldenergydata/production/forecast/cli.py:L1-L145]
- `packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py`. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L1-L336]
- `packages/worldenergydata-production/src/worldenergydata/production/forecast/router.py`. [packages/worldenergydata-production/src/worldenergydata/production/forecast/router.py:L1-L81]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/__init__.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/__init__.py:L1-L117]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/__init__.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/__init__.py:L1-L37]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/australia_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/australia_adapter.py:L1-L54]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/base.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/base.py:L1-L123]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L1-L177]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/bsee_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/bsee_adapter.py:L1-L105]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/canada_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/canada_adapter.py:L1-L115]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/eia_us_adapter.py:L1-L105]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/mexico_cnh_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/mexico_cnh_adapter.py:L1-L103]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/sodir_adapter.py:L1-L182]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/spain_cores_adapter.py:L1-L184]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/texas_rrc_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/texas_rrc_adapter.py:L1-L104]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py:L1-L167]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L1-L596]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L1-L245]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L1-L155]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/query.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/query.py:L1-L74]
- `packages/worldenergydata-production/src/worldenergydata/production/unified/router.py`. [packages/worldenergydata-production/src/worldenergydata/production/unified/router.py:L1-L155]

The package README and member metadata were read; the README describes the namespace split and shared-core dependency. [packages/worldenergydata-production/README.md:L1-L8]

Documentation discovery used `worldenergydata.production`, `production/unified`, `production/forecast` and `production_forecast`; relevant passages in these files were read, with historical plan counts treated as leads rather than present results:

- `docs/analysis-guides/index.md`. [docs/analysis-guides/index.md:L98-L101]
- `docs/examples/index.md`. [docs/examples/index.md:L81-L84]
- `docs/modules/bsee/comprehensive-report-system/template-configuration-guide.md`. [docs/modules/bsee/comprehensive-report-system/template-configuration-guide.md:L73-L76]
- `docs/modules/data_sodir/api_guide.md`. [docs/modules/data_sodir/api_guide.md:L509-L512]
- `docs/modules/fdas/country-adapter-checklist.md`. [docs/modules/fdas/country-adapter-checklist.md:L4-L7]
- `docs/plans/2026-07-04-issue-715-adapter-contract.md`. [docs/plans/2026-07-04-issue-715-adapter-contract.md:L7-L10]
- `docs/plans/2026-07-04-issue-716-norway-sodir-reference-chain.md`. [docs/plans/2026-07-04-issue-716-norway-sodir-reference-chain.md:L11-L14]
- `docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md`. [docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md:L16-L19]
- `docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md`. [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L23-L26]
- `docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md`. [docs/plans/2026-07-04-issue-806-spain-live-cores-xlsx.md:L108-L111]
- `docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md`. [docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md:L138-L141]
- `docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md`. [docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md:L54-L57]
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L122-L125]
- `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md`. [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L111-L114]

### Test coverage

- `tests/unit/production/forecast/test_decline.py`. [tests/unit/production/forecast/test_decline.py:L1-L115]
- `tests/unit/production/unified/test_adapters.py`. [tests/unit/production/unified/test_adapters.py:L1-L205]
- `tests/unit/production/unified/test_australia_adapter.py`. [tests/unit/production/unified/test_australia_adapter.py:L1-L37]
- `tests/unit/production/unified/test_benchmark_report.py`. [tests/unit/production/unified/test_benchmark_report.py:L1-L390]
- `tests/unit/production/unified/test_brazil_anp_adapter_loader.py`. [tests/unit/production/unified/test_brazil_anp_adapter_loader.py:L1-L124]
- `tests/unit/production/unified/test_canada_cnloer_adapter_loader.py`. [tests/unit/production/unified/test_canada_cnloer_adapter_loader.py:L1-L122]
- `tests/unit/production/unified/test_cross_basin.py`. [tests/unit/production/unified/test_cross_basin.py:L1-L307]
- `tests/unit/production/unified/test_normalizer.py`. [tests/unit/production/unified/test_normalizer.py:L1-L138]
- `tests/unit/production/unified/test_query.py`. [tests/unit/production/unified/test_query.py:L1-L100]
- `tests/unit/production/unified/test_router.py`. [tests/unit/production/unified/test_router.py:L1-L109]
- `tests/unit/production/unified/test_sodir_adapter_loader.py`. [tests/unit/production/unified/test_sodir_adapter_loader.py:L1-L106]
- `tests/unit/production/unified/test_spain_cores_adapter_loader.py`. [tests/unit/production/unified/test_spain_cores_adapter_loader.py:L1-L330]
- `tests/unit/production/unified/test_ukcs_adapter_loader.py`. [tests/unit/production/unified/test_ukcs_adapter_loader.py:L1-L128]
- `tests/unit/production/unified/test_unified_client.py`. [tests/unit/production/unified/test_unified_client.py:L1-L137]

Additional importing consumer files were executed as one offline suite:

- `tests/unit/australia/test_field_concept_and_chain.py`. [tests/unit/australia/test_field_concept_and_chain.py:L11-L14]
- `tests/unit/brazil_anp/test_reference_chain.py`. [tests/unit/brazil_anp/test_reference_chain.py:L8-L11]
- `tests/unit/canada/test_reference_chain.py`. [tests/unit/canada/test_reference_chain.py:L10-L13]
- `tests/unit/fdas/adapters/test_registration_checklist.py`. [tests/unit/fdas/adapters/test_registration_checklist.py:L59-L62]
- `tests/unit/sodir/test_norway_716.py`. [tests/unit/sodir/test_norway_716.py:L18-L21]
- `tests/unit/sodir/test_norway_reference_chain.py`. [tests/unit/sodir/test_norway_reference_chain.py:L10-L13]
- `tests/unit/spain/test_cores_field_development_report.py`. [tests/unit/spain/test_cores_field_development_report.py:L111-L114]
- `tests/unit/spain/test_reference_chain.py`. [tests/unit/spain/test_reference_chain.py:L8-L11]
- `tests/unit/spain/test_synthetic_gas_reference_chain.py`. [tests/unit/spain/test_synthetic_gas_reference_chain.py:L8-L11]
- `tests/unit/ukcs/test_reference_chain.py`. [tests/unit/ukcs/test_reference_chain.py:L9-L12]

### Open items

Every item below remains with the maintainer until an issue or independent clearance record closes its stated criterion; issue-pending references identify numbered drafts, not existing issues (AQG r0, section 11).

| Item | Evidence / limit | Tracking and closure criterion |
| --- | --- | --- |
| Coverage-gap correctness | Cross-year extrema, NaN gaps, duplicate periods and absent inserted rows are not covered by the current same-year tests | issue pending (1); add regressions with 0 false gaps for contiguous paired-year periods and explicit unknown-month accounting. [packages/worldenergydata-production/src/worldenergydata/production/unified/normalizer.py:L139-L155] [tests/unit/production/unified/test_normalizer.py:L107-L138] |
| Documentation distribution | Existing member glob includes nested Markdown | issue pending (2); establish the intended packaging disposition and test wheel contents before asserting the pack is excluded. [packages/worldenergydata-production/pyproject.toml:L54-L59] |
| Independent validation and review evidence | Five regression examples and one hand-integral branch do not validate the other EUR branches or measured source ingestion; no reviewer clearance is claimed | issue pending (3); add independently versioned benchmarks and record calculations reviewer/deputy assignments and signed G5 evidence. [tests/unit/production/forecast/test_decline.py:L17-L84] |
| UNVERIFIED claim from section 3 | Fiscal/BOE external validity is not established; illustrative coefficients and a code comment are not an editioned source | issue 361 and issue pending (3); establish published basis, applicability and sidecars before engineering use. [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L1-L7] [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L160-L164] |
| Map enrollment | No in-package map rows; all section-3 method families need enrollment before a counted-family audit applies | issue pending (4); add source paths, definitions and case-sensitive Python search signals to the map (implementation map, schema version 1, families, data pin in section 9). |
| Missing production feed | Australia returns no volumes | issue 823; preserve screening-only status until a qualified feed exists. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/australia_adapter.py:L1-L54] |
| Missing component | UKCS loader-backed condensate remains unknown | issue 796; require source-backed mapping without converting absent streams to measured zero. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py:L1-L167] |
| Public-data rights | Canada sources remain outside benchmark real-source allowlist | issue 819; public qualification remains pending, with no source values reproduced here. [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L68-L90] |
| Alternative implementations | Repository-wide decline variants retain distinct time conventions | issue 1104; reconcile interfaces and units before consolidation. [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L300-L353] |

A routing registry is absent at the code pin, so no `agent_pack` or `qa_family` registry fields are changed; indexing and independent clearance remain part of issue pending (3). The member metadata is the available package declaration. [packages/worldenergydata-production/pyproject.toml:L7-L12]
