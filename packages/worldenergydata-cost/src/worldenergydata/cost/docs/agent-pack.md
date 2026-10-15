# Cost module knowledge pack

| Header | Value |
| --- | --- |
| Module | `cost` |
| Repository | `worldenergydata` |
| Path | `packages/worldenergydata-cost/src/worldenergydata/cost` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `e73bda871798429eeb6dda0d16ed5520548d6cad` |
| Analysis family | Data pipeline; AQG r0 Python calculations gate set |
| Quality role | Calculations quality manager; deputy assignment pending |
| Status | DRAFT; clearance not established |

## 1. Purpose and scope

`CostPredictor.fit` fits a preprocessed linear model to the logarithm of escalation-adjusted `cost_usd_mm`; `predict` reverses those transformations and returns a point estimate and bootstrap bounds. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L198-L249] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L251-L279] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L358-L410]

`load_project_cost_revision_view` and `load_operator_annual_capex_view` produce separate disclosure views; `build_cost_disclosure_benchmark` compares a supplied prediction scalar with a matching row marked `comparable`, selecting the latest matching fiscal year unless a year is specified. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L132-L205] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L207-L266]

The benchmark hook does not fit the predictor or establish a common currency, ownership, scope or price basis: its implemented eligibility condition is the caller-supplied `comparability_status`, identity and optional fiscal year. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L236-L256]

The adjoining time-series path filters annual observations, normalizes money with explicit deflators, fits trend candidates and allocates disclosed totals with stated priors. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/series.py:L60-L104] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/normalization.py:L223-L243] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L146-L271] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/back_allocation.py:L328-L402]

Coverage boundary: sections 1–6 qualify the prediction, disclosure and synthetic time-series main path; portfolio evidence, source requalification and the wider documentation inventory remain open in section 10.

UNVERIFIED: Dataset source accuracy and representativeness for investment estimates are not established by schema validation or the current prediction tests; see U1 in section 10. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/public_dataset.py:L1643-L1651] [tests/unit/cost/test_cost_predictor.py:L103-L141]

## 2. Inputs and outputs

### Inputs

| Surface / field | Unit | Allowed range / default | Source and evidence |
| --- | --- | --- | --- |
| `CostDataPoint.water_depth_m` | m | At least 0; required | Caller or public dataset. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L100-L106] |
| `well_depth_m`, `well_depth_band` | m; category | Nonnegative depth or `None`; both default `None`; TVD versus MD is not separately encoded | Caller. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L108-L114] |
| `year_sanction`, `year_drilling` | calendar year | 1970–2035 required; 1970–2040 or `None`, respectively | Caller. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L118-L129] |
| `cost_usd_mm`, `cost_type` | USD million; category | Cost greater than 0; required type permits well cost, day rate and total CAPEX | Caller. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L64-L69] [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L141-L145] |
| `project_name`, `operator`, `region`, `source` | text | Nonempty required strings | Caller; source is free text, not a resolved citation sidecar. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L92-L98] [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L117-L117] [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L147-L153] |
| `rig_type`, `activity_type`, `hpht`, `subsea`, `water_depth_band`, `confidence` | categorical / boolean, unit 1 | Required declared categories and boolean | Caller. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L22-L77] [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L132-L153] |
| `CostPredictor.fit(records)` | records | Minimum 5 records; no cost-type partition at this boundary | `CostDataPoint` list. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L216-L236] |
| Predictor features | m; year; unit 1 | Missing well depth becomes 0; numeric depth/year/flag and categorical region/rig/subsea/depth band | `_extract_features`; activity and cost type are absent from this feature projection. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L104-L120] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L123-L143] |
| `DisclosureRecord` | USD million; calendar year; text | Caller supplies amount, year, scope and identity; provenance defaults empty; comparability and currency default `None` | Local dataclass, without numeric range validators. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L58-L75] |
| `DisclosureRow`, `DisclosureCitation` | Caller-declared `metric_unit` | Fiscal year 1970–2050; mandatory nonblank citation strings, HTTP(S) prefix and declared enums | Ingest contract; metric unit is a string, not an automatic conversion. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py:L104-L154] |
| `CostObservation` | Explicit `unit`, currency and price basis | Year 1970–2040; currency defaults USD; nominal default; `value=None` represents a gap; real requires a basis year | Time-series schema. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/schema.py:L156-L204] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/schema.py:L223-L271] |

There is no geometric coordinate-frame input on these main-path interfaces; depth is a scalar and missing depth is imputed as 0 in prediction, so an absent measurement must not be interpreted as a measured zero. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L100-L114] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L108-L117]

### Outputs

| Output | Unit / convention | Contract and evidence |
| --- | --- | --- |
| `PredictionResult` | USD million in requested sanction-year nominal terms; training count in records | Point, lower and upper bounds plus `source_record_count`; bounds use 5th/95th bootstrap percentiles. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L50-L69] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L358-L410] |
| `training_r2_score`, `cross_validate` | Unit 1 | R² is evaluated in transformed target space; cross-validation returns mean and standard deviation with default 5 folds. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L295-L345] |
| Disclosure view rows | USD million; fractional change, unit 1 | Delta is current minus preceding record; `yoy_delta_pct` is a fraction, not a number already multiplied by 100. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L122-L129] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L151-L169] |
| `DisclosureBenchmarkResult` | USD million; fractional delta, unit 1 | `absolute_delta_usd_mm` is signed predicted minus disclosed, not absolute magnitude; `pct_delta` divides by disclosed, with zero denominator mapped to 0. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L246-L266] |
| `IngestResult` | Records | Accepted, duplicate, conflict and invalid partitions retain input indices and order. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py:L306-L345] [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py:L361-L413] |
| `CostDataPointLinkResult` | Matches, count | Exact identity matching gives 0/unlinked, 1/linked or at least 2/ambiguous; an explicit empty corpus does not load defaults. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/linkage.py:L123-L161] |
| `annual_means` | Input observation unit | Sorted year-to-mean mapping after source, component, currency, figure-type and region filtering. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/series.py:L90-L104] |
| `to_real` / `FitResult` | Input money unit / slope per year or per oil-price unit | Normalized value or `None`; fit records coefficients, R², adjusted R², RMSE, count and window; `predict` returns value with extrapolation flag or `None`. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/normalization.py:L223-L243] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L81-L105] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L273-L306] |
| Component CSV | Per-row explicit unit; UTF-8 text | Uppercase headers; empty cells encode `None`, enum values remain strings and dates are ISO format; readback reconstructs validated observations. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/schema.py:L301-L324] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/dataset.py:L63-L141] |

## 3. Method and governing standards

| Method | Implementation and reference |
| --- | --- |
| Ordinary least squares on a transformed target | `_build_pipeline` uses `StandardScaler`, dense one-hot encoding with unknown categories ignored, and `LinearRegression`; `fit` uses the natural logarithm of the adjusted target. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L123-L143] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L225-L236] Reference: scikit-learn developers, *LinearRegression*, documentation edition 1.7.2, description and Notes: [ordinary least squares](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LinearRegression.html). |
| Escalation | `_inflate_to_base`: cost times `(1 + rate) ** (2020 - year)` with code rate 0.03; inverse transformation returns the requested year's money. These are code assumptions, not values reproduced from a licensed index. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L37-L42] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L77-L93] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L358-L367] |
| Bootstrap bounds | `_bootstrap_ci` resamples training rows with replacement, refits 200 times using seed 42, skips failed fits and takes 5th/95th percentiles; fewer than 10 successful resamples returns 0.5/1.5 times the point estimate. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L369-L410] |
| R² / cross-validation | `training_r2_score` scores log adjusted costs; `cross_validate` calls `cross_val_score` on that same target without project-group identifiers. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L295-L345] |
| Disclosure comparison | `_yoy` returns `current - prior` and divides by nonzero prior; benchmark computes `(predicted - disclosed) / disclosed`. These are signed arithmetic differences with no currency conversion. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L122-L129] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L236-L266] |
| Trend fit | `fit_component` requires at least 5 distinct retained years, fits linear/exponential and optional current/lagged oil-price candidates using `polyfit`, scores each on its available rows and selects the largest adjusted R². [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L69-L70] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L146-L237] |
| Normalization | `to_real` multiplies nominal value by the basis-year/source-year deflator ratio; missing coverage or a zero source index returns `None`. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/normalization.py:L223-L243] |
| Allocation | `allocate_project` adjusts assumed stage shares for well count, renormalizes their sum and multiplies by total CAPEX; `reconcile_drilling` compares the drilling share with well count × duration × daily rate × spread multiplier. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/back_allocation.py:L328-L402] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/back_allocation.py:L426-L479] |

UNVERIFIED: Independent calibration of the escalation assumption and empirical coverage of the bootstrap bounds are not established; the algorithm descriptions do not establish prediction-interval coverage (U2, section 10). [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L5-L16] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L369-L410]

UNVERIFIED: A published methodological reference for the bootstrap policy and trend-model selection has not been established by the inspected source; the OLS reference above qualifies the library method only (U3, section 10). [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L369-L410] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L108-L121] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L210-L237]

No licensed standard is adopted as a design criterion by this pack; no licensed clause text or tabulated value is reproduced. Citation-sidecar qualification for a future standards-derived calculation remains a separate requirement.

## 4. Validated worked examples

The following expected values are independently derived arithmetic identities for synthetic inputs; they qualify those operations only, not real-world cost calibration. [tests/unit/cost/test_timeseries_analysis.py:L92-L96] [tests/unit/cost/test_timeseries_analysis.py:L256-L265] [tests/unit/cost/test_disclosure_analytics.py:L280-L306]

| ID / kind | Input and independent expected value | Criterion and basis | Existing test node ID | Offline result at code revision |
| --- | --- | --- | --- | --- |
| V1 validated: linear fit | Synthetic 2000–2011 series `y = 100000 + 10000*t` USD/day; direct OLS gives intercept 100000 USD/day, slope 10000 USD/day/year and R² 1 | Test checks slope relative error at most `1e-6` (0.01 USD/day/year) and R² absolute error at most `1e-6`, unit 1; numerical roundoff criterion. [tests/unit/cost/test_timeseries_analysis.py:L256-L265] | `tests/unit/cost/test_timeseries_analysis.py::test_fit_recovers_a_clean_linear_trend` | PASS at BASE and AFTER |
| V2 validated: deflator ratio | Synthetic index grows by factor 1.02 per year over 20 years; ratio identity gives `100 * (1.02 ** 20)` basis-year USD | Relative error at most `1e-9`, unit 1, as explicitly asserted in the test. [tests/unit/cost/test_timeseries_analysis.py:L67-L78] [tests/unit/cost/test_timeseries_analysis.py:L92-L96] | `tests/unit/cost/test_timeseries_analysis.py::test_to_real_converts_to_the_basis_year` | PASS at BASE and AFTER |
| V3 validated: benchmark delta | Synthetic disclosed 950.0 and supplied predicted 1100.0 USD million; subtraction gives 150.0 USD million and ratio `150/950` (15.8 %) | Existing `pytest.approx` default comparison; relative tolerance `1e-6` and absolute floor `1e-12` in each output unit; the ratio is compared before display rounding. [tests/unit/cost/test_disclosure_analytics.py:L280-L306] | `tests/unit/cost/test_disclosure_analytics.py::TestCostDisclosureBenchmark::test_cost_consumer_can_compare_predictor_output_to_latest_disclosed_capex_when_rows_are_comparable` | PASS at BASE and AFTER |
| R1 regression: prediction shape and bounds | Public loader, fitted predictor and first returned record; expected type and bound ordering, without an independently sourced prediction value | Lower bound ≤ point ≤ upper bound; zero ordering violations, count. [tests/unit/cost/test_cost_predictor.py:L115-L141] | `tests/unit/cost/test_cost_predictor.py::TestCostPredictorPredict::test_prediction_includes_confidence_interval` | PASS at BASE and AFTER |
| R2 regression: ingest partitions | Synthetic four-row batch against existing row; one accepted, one duplicate, one conflict, one invalid | Exactly 1 record in each partition; 0 missing conflict annotations. [tests/unit/cost/test_disclosure_ingest_contract.py:L320-L350] | `tests/unit/cost/test_disclosure_ingest_contract.py::test_ingest_contract_returns_partitioned_result_sets` | PASS at BASE and AFTER |

For V1, hand algebra uses `n=12`, `sum(t)=66`, `sum(t²)=506`, `sum(y)=1860000` and `sum(t*y)=11660000`; `(n*sum(t*y)-sum(t)*sum(y))/(n*sum(t²)-sum(t)²)=10000`, with intercept `(sum(y)-10000*sum(t))/n=100000`, so every residual is zero. [tests/unit/cost/test_timeseries_analysis.py:L256-L265]

### Offline execution ledger

Results recorded at `e73bda871798429eeb6dda0d16ed5520548d6cad` on 2026-10-15; counts are run / passed / failed / skipped / NOT_RUN, with collection errors stated separately.

| Selection / form | BASE | AFTER |
| --- | --- | --- |
| `tests/unit/cost` in the ordinary `uv run python -m pytest` form | 356 / 356 / 0 / 0 / 0; exit 0 | Covered by expanded selection below |
| `tests/unit/cost`, `tests/unit/fdas/test_disclosure_api.py`, `tests/test_query_api.py::TestFDASDisclosureAnalyticsQuery`, `tests/contracts`; ordinary form with `--allow-existing-tree-changes` | 380 / 380 / 0 / 0 / 0; exit 0 | 380 / 380 / 0 / 0 / 0; exit 0 |
| `tests/unit/cost/test_proxy_comparison.py`; AGENTS form with `--noconftest --continue-on-collection-errors` | 0 / 0 / 0 / 0 / 0; 1 collection error; exit 1 | 0 / 0 / 0 / 0 / 0; 1 collection error; exit 1 |

Every pytest command uses `-q -rA -p no:cacheprovider` and a distinct scratch `--basetemp`; expanded and proxy coverage outputs are directed to scratch, with configured coverage checks retained. The ordinary conftest excludes the proxy file; the explicit AGENTS-form attempt exposes `ModuleNotFoundError: No module named 'worldenergydata.cost.calibration.proxy_comparison'`, leaving 14 source-defined tests uncollected rather than reporting them as skipped or solver-dependent NOT_RUN. [tests/conftest.py:L628-L644] [tests/unit/cost/test_proxy_comparison.py:L9-L14]

The documented existing-work mode fingerprints initially dirty files and rejects changes to those bytes or new undeclared paths; it preserves the uncommitted pack during after-checks. [docs/development/index.md:L56-L59]

Hand-probe results at BASE: V1 algebra gives intercept 100000.0 USD/day and slope 10000.0 USD/day/year; C12 returns 1 one-year delta instead of 0 for each of the two scopes across a two-year gap; the zero-denominator benchmark returns a 100.0 USD million signed delta with fractional delta 0.0, although that ratio is undefined. [tests/unit/cost/test_timeseries_analysis.py:L256-L265] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L122-L129] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L151-L169] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L246-L266]

## 5. QA gates

Gate assignment: AQG r0, section 10, *Python calculations*; G0 inputs/units/citations, G1 imports/tests, G2 independent arithmetic, G3 and G4 NOT_APPLICABLE, G5 evidence appendix (AQG r0, sections 3, 9 and 10).

The criteria below are pack acceptance proposals, not claims of clearance; checks with known failures retain their failure and issue reference.

| Check | Gate / applicability | Executable check and numeric pass criterion, including unit | Evidence / disposition |
| --- | --- | --- | --- |
| C01 | G0 applicable | `CostDataPoint` construction rejects cost 0 USD million, cost -10 USD million and water depth -5 m; exactly 3 rejected inputs | `test_calibration_schema.py::TestCostDataPointNumericConstraints::{test_zero_cost_raises,test_negative_cost_raises,test_negative_water_depth_raises}`; numeric schema tests. [tests/unit/cost/test_calibration_schema.py:L151-L173] |
| C02 | G0 applicable | `ingest_disclosure_rows` produces 1 accepted, 1 duplicate, 1 conflict and 1 invalid record from R2; 0 unclassified inputs | R2 and its partition assertions. [tests/unit/cost/test_disclosure_ingest_contract.py:L320-L350] |
| C03 | G0 applicable | `annual_means` retains 0 nonmatching-currency observations and `compare_against_inflation` retains 0 fitted observations as endpoints; count | Existing currency-filter and fitted-endpoint tests. [tests/unit/cost/test_timeseries_analysis.py:L219-L240] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/series.py:L90-L104] |
| C04 | G1 applicable | Import `worldenergydata.cost`; execute every collected offline node under `tests/unit/cost` and the contracts domain; 0 import errors and 0 failing nodes, count | Execution ledger; known baseline failures prevent gate clearance even if the documentation change is eligible for review. [tests/unit/cost/test_disclosure_analytics.py:L401-L430] |
| C05 | G2 applicable | `fit_component` on V1 returns slope 10000 USD/day/year within 0.01 USD/day/year and R² 1 within `1e-6`, unit 1 | V1 test and the independent algebra in section 4. [tests/unit/cost/test_timeseries_analysis.py:L256-L265] |
| C06 | G2 applicable | `to_real` on V2 agrees with `100*(1.02**20)` basis-year USD to relative `1e-9`, unit 1 | V2 identity and test. [tests/unit/cost/test_timeseries_analysis.py:L92-L96] |
| C07 | G2 applicable | `build_cost_disclosure_benchmark` on V3 returns signed delta 150.0 USD million within `1.5e-4` USD million and fraction `150/950` within `1e-6`, unit 1 | V3, with the pack's explicit numeric bounds. [tests/unit/cost/test_disclosure_analytics.py:L280-L306] |
| C08 | G3 NOT_APPLICABLE | Time-domain solver dynamics are outside these arithmetic interfaces; required solver calls: 0, count | Pipeline fitting, disclosure views and arithmetic normalization interfaces. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L198-L249] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L132-L205] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/normalization.py:L223-L243] |
| C09 | G4 NOT_APPLICABLE | Diffraction bodies/meshes are outside these arithmetic interfaces; required diffraction cases: 0, count | Same main-path input contracts. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L85-L153] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L58-L75] |
| C10 | G5 applicable | Resolve every citation at the code revision; invalid locators: 0, count; example rows without node/result: 0, count; reviewer signatures required before clearance: 1, count | Pack self-check and second-provider clearance record; signature pending |
| C11 | G0 applicable | Hand/source inspection of `load_public_dataset`: independent-source claims unsupported by row provenance: 0, count; derived rows shall be labeled separately | Source-qualification gap U1; derived sub-observations do not count as independent measurements. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/public_dataset.py:L1622-L1651] |
| C12 | G2 applicable | Two same-identity rows in 2020 and 2022 shall produce 0 one-year deltas in both disclosure views, count | New regression required; the current loops do not check year distance; issue pending (1). [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L151-L169] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L186-L205] |

Checks defined: G0 4; G1 1; G2 4; G3 1 NOT_APPLICABLE; G4 1 NOT_APPLICABLE; G5 1. Gate pass thresholds do not waive missing evidence.

## 6. Known failure modes and pitfalls

| Symptom | Cause and detection | Tracking / date |
| --- | --- | --- |
| Bounds can look complete despite resampling failures | Failed bootstrap fits are silently skipped; fewer than 10 successful fits substitutes a ±50.0 % band without a result-status flag; C11 source/basis review shall not interpret it as measured uncertainty. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L388-L410] | Issue 1043; 2026-10-15; no dedicated fallback-status detection test identified |
| Annual means can combine otherwise different bases | `annual_means` does not partition unit, band, segment or nominal/real basis; callers shall supply a homogeneous cohort in addition to its implemented filters; C11 requires that basis check. [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/series.py:L90-L104] | Issue 844; 2026-10-15; no automatic unit/band/basis rejection check exists in this function |
| Missing well depth becomes a physical-looking zero | `_extract_features` imputes 0.0 m; the schema permits absent depth; C01 verifies the input distinction but does not supply a measurement. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L108-L114] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L108-L111] | Issue 1043; 2026-10-15 |
| A row count can overstate independently observed evidence | Loader appends 29 derived records made by scaling earlier cost values and changing metadata; C11 requires their separate qualification. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/public_dataset.py:L1622-L1651] | Issue 1101 and issue 1043; 2026-10-15 |
| Costs of different scopes can share one prediction target | `cost_type` and `activity_type` exist in the schema but are absent from the model projection and fit-time eligibility checks; C11 requires basis-compatible training before engineering use. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/calibration_schema.py:L131-L145] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L104-L120] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L216-L236] | Issue 1043; 2026-10-15; no basis-rejection check exists in `fit` |
| A multi-year or duplicate-year interval is labeled year-over-year | Sorted records retain only preceding amount, without previous fiscal year or duplicate-year handling; C12 detects the missing-year case. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L151-L169] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L186-L205] | Issue pending (1); 2026-10-15 |
| Ingest and analytics scope vocabulary differs | The ingest contract uses `corporate`, whereas analytics filters the literal `operator`; a caller adapter is required to preserve corporate rows in the annual operator view. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/disclosure_ingest_contract.py:L45-L50] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L53-L56] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L185-L189] | Issue 334; 2026-10-15; no automatic adapter check identified |
| A caller-provided comparable flag is treated as enough | Benchmark accepts the flag without validating `comparability_basis` or currency against the prediction; C11 requires an upstream same-basis contract. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L58-L75] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L236-L266] | Issue 336 and issue 1043; 2026-10-15 |
| Zero disclosed amount produces a zero fractional benchmark delta | Zero denominator follows an explicit `else 0.0` branch; the signed money difference can still be nonzero; C07 covers positive-denominator arithmetic only. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L246-L256] | Issue pending (1); 2026-10-15; no zero-denominator rejection check identified |
| Proxy comparison cannot import | Existing test imports `worldenergydata.cost.calibration.proxy_comparison`; C04 detects the absent import boundary; aggregate collection can omit it through the existing conftest. [tests/unit/cost/test_proxy_comparison.py:L9-L14] [tests/conftest.py:L628-L644] | Issue 342; 2026-10-15 |
| Refresh instructions name an unavailable module entry point | Documented `python -m worldenergydata.cost.timeseries.refresh` needs a target beyond the inspected time-series exports; no detection check exists in the main-path tests. [docs/modules/cost/REFRESH_PROCEDURE.md:L63-L83] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/__init__.py:L1-L22] | Issue 844; 2026-10-15; entry-point coverage remains open |

The ordinary collected suite passes at BASE; C04 remains uncleared because the explicit proxy import attempt fails collection under issue 342, and C12 fails the two temporal-gap hand probes under issue pending (1). [tests/unit/cost/test_proxy_comparison.py:L9-L14] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L151-L169] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L186-L205]

## 7. Lessons log

Append-only fields: date, record ID, lesson, evidence, pack change and shared-log reference.

| Date | Record ID | Lesson / evidence | Pack change | Shared-log reference |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial revision | Independent-source counts must distinguish appended derived observations from stored inputs. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/public_dataset.py:L1622-L1651] | Sections 1, 5 and 6 distinguish qualification from record count | Pending maintainer filing under issue 1101 |
| 2026-10-15 | Initial revision | Positive-denominator arithmetic tests do not establish temporal-gap handling. [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L151-L169] [tests/unit/cost/test_disclosure_analytics.py:L179-L216] | C12 and section 6 expose temporal semantics | Issue pending (1) |

## 8. Ownership

Requested reviewing role: calculations quality manager; producing role: module documentation contributor; escalation route: the maintainer for scope, publication or unresolved evidence. This is an assignment request, not a clearance record.

UNVERIFIED: A named deputy and module maturity assignment are not established by a routing entry; assignment and clearance remain pending under issue pending (2), item U4.

## 9. Dependencies

The package declares `worldenergydata-core`, NumPy, Pydantic and scikit-learn dependencies; `cost_predictor` also imports pandas when converting feature rows. [packages/worldenergydata-cost/pyproject.toml:L30-L35] [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L146-L150]

`fdas.api` delegates its disclosure benchmark to `build_cost_disclosure_benchmark`; report builders consume the shared `annual_means` function instead of defining another filter policy. [packages/worldenergydata-fdas/src/worldenergydata/fdas/api.py:L328-L345] [scripts/cost/build_cost_basis_report.py:L131-L145] [scripts/cost/build_stakeholder_presentation.py:L245-L254]

Repository-wide search, including `scripts/`, also finds a separate BSEE cost-calibration implementation and independent trend fitting in the production forecasting module; neither is adopted here as an independent expected-cost source. [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/cost/cost_calibration.py:L120-L149] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L269-L284]

Inventory links for those adjoining domains are discovery leads; qualification of their full consumer contracts remains open under issue pending (2).

## 10. Coverage and open items

### Reading coverage

Main-path code read: package and calibration exports; `calibration/cost_predictor.py`; `data_collection/calibration_schema.py`, `disclosure_ingest_contract.py`, `linkage.py`, `operator_statement_registry.py` and `statement_source_fetch.py`; `disclosure_analytics.py`; time-series schema, CSV, normalization, annual aggregation, trend fitting and allocation implementations. The public dataset loader and supplemental-record construction were inspected; its individual source documents were not requalified.

Additional code inspected for boundaries: `timeseries/cost_map.py`, `cost_map_schema.py`, `project_trace.py`, `reconciliation.py`, `evidence_pack.py` and `evidence_pack_render.py`. The full curated-record body in `timeseries/records.py` remains outside main-path qualification, under issue pending (2).

Primary documentation read: `packages/worldenergydata-cost/README.md`, `docs/modules/cost/REFRESH_PROCEDURE.md`, and `docs/plans/2026-05-04-issue-342-proxy-comparison-fix.md`; the last is a proposal, not implementation evidence. [packages/worldenergydata-cost/README.md:L1-L8] [docs/modules/cost/REFRESH_PROCEDURE.md:L63-L83] [docs/plans/2026-05-04-issue-342-proxy-comparison-fix.md:L1-L50]

Document search finds 32 references under `docs/`; the following additional references remain discovery coverage under issue pending (2). The 1 identity-bearing pathname is retained in the local discovery record, with neutral locator completion assigned to the same draft.

- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L707-L707] — discovery reference; deeper qualification: issue pending (2).
- [docs/adr/0001-domain-package-split.md:L254-L254] — discovery reference; deeper qualification: issue pending (2).
- [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L81-L81] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-22-issue-335-disclosure-to-costdatapoint-linkage-model.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/modules/cost/validation/2026-07-14-sanctioned-cost-second-source-validation.md:L1-L1] — discovery reference; deeper qualification: issue pending (2).
- [docs/research/annual-statement-source-registry.md:L102-L102] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-05-04-issue-143-bsee-field-econ-calibrated.md:L20-L20] — discovery reference; deeper qualification: issue pending (2).
- [docs/ci/flake8-inventory-2026-04-23.md:L155-L155] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-16-issue-1040-required-assets-award-coverage.md:L16-L16] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/execution-packs/2026-04-22-approved-cost-wave/future-issues-and-exit-handoff.md:L38-L38] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-23-issue-344-restatement-version-lineage-for-annual-disclosure-records.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-19-issue-1040-required-assets-award-coverage-replan.html:L28-L28] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-16-issue-1042-component-cost-time-traces.md:L22-L22] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-23-issue-343-major-operator-annual-statement-source-registry-and-yearly-coverage-tracker.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-05-04-issue-362-operator-cost-benchmarking-report.md:L13-L13] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-22-issue-337-citation-quality-and-automated-ingestion-contracts-for-annual-disclosures.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-338.md:L8-L8] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-22-issue-336-currency-normalization-and-comparability-policy-for-annual-disclosures.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-16-issue-1041-bidirectional-cost-synthesis.md:L22-L22] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-22-issue-338-annual-disclosure-analytics-views-and-consumer-integration.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-337.md:L7-L7] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/execution-packs/2026-04-22-approved-cost-wave/master-plan.md:L23-L23] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-335.md:L8-L8] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-16-issue-1043-correlated-capex-estimator.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-16-issue-1038-cost-map-program.md:L13-L13] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-18-issue-1039-manifest-lineage-hotfix.md:L208-L208] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md:L14-L14] — discovery reference; deeper qualification: issue pending (2).
- [docs/plans/2026-07-16-issue-1044-fdas-workbook-reconciliation.md:L29-L29] — discovery reference; deeper qualification: issue pending (2).

Test scope: all `tests/unit/cost/test_*.py` files discovered; package-local test directory absent; adjacent BSEE/decommissioning/field-development cost domains are separate coverage, not included in the test-count claim. Node outcomes and collection gaps are recorded in section 4.

### Open-item register

| Item | Missing evidence / required next checkpoint | Responsible role / tracking |
| --- | --- | --- |
| U1 | Independent source accuracy and representative cost basis for stored and derived training rows; qualify sources individually and report independent sample counts | Maintainer; issue 1101 and issue 1043. [packages/worldenergydata-cost/src/worldenergydata/cost/data_collection/public_dataset.py:L1622-L1651] |
| U2 | An independent multivariate-prediction worked example, calibrated escalation and empirical interval coverage; separate bootstrap fallback status, grouped holdouts and target-scope compatibility before prediction acceptance | Maintainer; issue 1043. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L369-L410] |
| U3 | Published references for bootstrap and trend-selection policy beyond the opened scikit-learn OLS documentation; no licensed clause is claimed checked | Maintainer; issue 1101. [packages/worldenergydata-cost/src/worldenergydata/cost/calibration/cost_predictor.py:L369-L410] [packages/worldenergydata-cost/src/worldenergydata/cost/timeseries/trend_fit.py:L210-L237] |
| U4 | Deputy assignment, module maturity and second-provider clearance | Maintainer; issue pending (2) |
| O1 | Year-gap, duplicate-year and zero-denominator disclosure semantics; implement and run C12 plus denominator tests | Maintainer; issue pending (1). [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L122-L129] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L151-L169] [packages/worldenergydata-cost/src/worldenergydata/cost/disclosure_analytics.py:L246-L256] |
| O2 | Restore missing proxy comparison import and its offline regression boundary | Maintainer; issue 342. [tests/unit/cost/test_proxy_comparison.py:L9-L14] |
| O3 | Complete source-row, portfolio evidence, reporting and documentation qualification; extend examples to the remaining paths without naming underlying projects | Maintainer; issue pending (2), related issues 1040, 1041, 1042 and 1044 |
| O4 | Package-data pattern `**/*.md` includes nested Markdown; an excluded documentation-only pack is not established by the current packaging configuration | Maintainer; issue pending (3). [packages/worldenergydata-cost/pyproject.toml:L55-L56] |
| O5 | Reconcile the documented refresh target with the executable route and offline entry-point tests | Maintainer; issue 844. [docs/modules/cost/REFRESH_PROCEDURE.md:L63-L83] |

Pending issue references identify draft numbers for maintainer filing; this draft does not claim final issue linkage or quality clearance.
