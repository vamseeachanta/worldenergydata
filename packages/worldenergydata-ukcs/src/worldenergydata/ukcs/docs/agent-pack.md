# UKCS module knowledge pack

| Header | Value |
| --- | --- |
| Module | `ukcs` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-ukcs/src/worldenergydata/ukcs` |
| Pack revision | 2, 2026-10-22 |
| Code pin | Historical pin `92b13dce6b3121cbe827f17327c6dde7fcd6dc5c`; the containing commit binds revision 2 behavior and test nodes. |
| Analysis family | EC; data pipeline, Python calculations gate set |
| Quality role | Calculations quality manager; deputy appointment pending |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

`NSTAClient` downloads production rows or reads a local CSV cache; `UKCSFieldProductionLoader` normalizes monthly oil, gas and water and sums annual totals. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L60-L96] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L47-L100] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L110-L125]

`UKCSWellLoader` normalizes supplied well records and returns counts and test-rate summaries; `DeclineCurveAnalyzer` fits exponential, hyperbolic and harmonic curves. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L28-L65] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L75-L103] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L66-L104]

`UKFiscalRegime` performs standalone fiscal arithmetic, while `CrossBasinComparator` discounts synthetic monthly cashflows under three code-defined fiscal branches. These are implementation descriptions, with current-law validity left open in section 10. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L96-L137] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L156-L228]

`run_ukcs_reference_chain` connects an injected adapter to FDAS production conversion, sparse concept screening and cashflow aggregation; its economics label is `chain_plumbing_pre_tax`. Sparse screening is a wiring proof rather than a published development recommendation. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L28-L78] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/field_concept.py:L1-L7]

Scope includes every Python file in this package, including `production`, `wells` and `analysis`; downstream adapter, scheduler, FDAS and recommendation internals are dependency boundaries, not additional package implementations. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L38-L78] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/ukcs_refresh.py:L48-L78]

Package metadata classifies the distribution as Alpha; that declaration is not independent engineering validation. [packages/worldenergydata-ukcs/pyproject.toml:L15-L24]

Section 6 records corrected input and cashflow failures under #1284. The revision-2 regression nodes below detect these cases; they do not qualify fiscal assumptions or investment results.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-15 | Initial implementation inventory and regression evidence |
| 1 | 2026-10-16 | Record silent failures and detection gaps; distinguish a pagination regression that encodes row loss from completeness evidence |

| 2 | 2026-10-22 | Reject unknown economics inputs, preserve loss cashflows and correct short-page offsets; retain fiscal and unit qualification limits. |

## 2. Inputs and outputs

### Inputs

| Route | Input names and units | Range, defaults and handling | Evidence |
| --- | --- | --- | --- |
| Download/cache | `year` integer; `dataset` string; `cache_dir`; `base_url`; `encoding`; `max_records` rows | `monthly`, UTF-8, no row cap, refresh false; default cache inside package; cache identity uses year and dataset only | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L34-L71] |
| Legacy production frame | `FieldName`, `Year`, `Month`; oil and water in thousand tonnes; gas in MMscf | Empty frame supported; missing measured values filled with zero; integer casts do not enforce calendar ranges | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L28-L33] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L61-L98] |
| PPRS production frame | `FIELDNAME`, `PERIODYR`, `PERIODMNTH`; `OILPRODMAS` tonnes; `AGASPROKSM` plus `DGASPROKSM` thousand standard cubic metres; `WATPRODVOL` cubic metres | Name/year/month aliases selected in order; absent gas columns have the defect in section 6 | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L35-L41] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L67-L98] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L128-L132] |
| Well frame | `WellName`, `FieldName`, `CompletionDate`, `Status`, `WaterDepth_m` metres, `TestRate_bopd` barrels/day | Dates remain strings; invalid depth becomes NaN; invalid rate becomes zero; no positivity check | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L17-L22] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L55-L65] |
| Decline fit | Positive monthly production series, any consistent rate/volume unit; `DeclineModel` | Default exponential; at least 3 positive non-null points; time is retained-row position, not calendar index | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L66-L104] |
| Fiscal arithmetic | `gross_revenue`, `opex`, `capex` in one currency, USD or GBP | All capex treated as qualifying; no currency conversion; non-positive taxable profit gives zero taxes | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L34-L72] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L104-L126] |
| Basin comparison | Monthly production bbl; oil price USD/bbl; capex million USD; opex USD/bbl; fiscal selector | Discount defaults to 0.10/year; monthly rate is annual rate divided by 12; unrecognized fiscal selector returns zero tax | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L35-L49] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L124-L126] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L156-L175] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L221-L228] |
| Reference chain | Adapter; `field_meta`; `field_name`; optional start/end; price USD/bbl | Price default 75.0; concept region forced to `uk`, production query region `ukcs`; unknown depth route falls back to `subsea15` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/field_concept.py:L35-L42] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L28-L57] |

### Outputs

| Route | Names and units | Conventions and evidence |
| --- | --- | --- |
| Production | `field`, `year`, `month`, `oil_bbl`, `gas_mcf`, `water_bbl`; monthly amounts | Names stripped and uppercased; annual sums grouped by field/year; row index reset. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L61-L100] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L110-L125] |
| Cache | Year/dataset CSV; UTF-8 read default | Generic CSV response saved before parsing; ArcGIS attributes serialized as CSV; no geometry requested. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L45-L58] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L90-L96] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L116-L143] |
| Wells | `well_name`, `field`, `completion_date`, `status`, `water_depth_m`, `test_rate_bopd` | Positive-down geometry is not defined by these routines; depth is passed through numerically, and no coordinates or phase arrays are read. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L55-L65] |
| Well summary | `well_count` records; average and maximum test rate bbl/day | Empty selection returns zero for all three. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L90-L103] |
| Decline | Model, initial rate in input units, decline per retained monthly step, dimensionless `b_factor` and R-squared, RMSE in input units | Integer forecast argument expands to periods starting at zero; predictions clipped to nonnegative values. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L31-L60] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L93-L104] |
| Fiscal result | Revenue, profit, tax components, allowance, government take and net income in input currency | Profit subtracts opex and capex; net income subtracts total tax from profit. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L78-L87] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L118-L137] |
| Comparison | NPV USD; government take dimensionless; price sensitivity NPV USD | Summary divides NPV into million USD; effective take clipped to [0, 1]; sensitivities recompute price cases. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L52-L68] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L180-L189] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L230-L262] |
| Reference chain | Unified and FDAS frames; concept and ranking; `months`, gross revenue, royalty, net cashflow USD | Monthly values are summed without discounting in `_pre_tax_metrics`; this output is not standalone `UKFiscalRegime` output. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L59-L78] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L93-L99] |

The production and well loaders expose no coordinate-frame, origin or wave-phase interface; their implemented transformations concern tabular names, dates, rates and amounts. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L61-L100] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L55-L65]

## 3. Method and governing standards

| Method | Definition implemented and applicability | Function evidence |
| --- | --- | --- |
| Production normalization | Legacy mass amounts scale to tonnes then oil barrels; PPRS oil uses tonnes directly; associated and dry gas are summed; PPRS water uses a water-volume factor; annual totals are pandas grouped sums | `UKCSFieldProductionLoader.load`, `annual_aggregate`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L73-L98] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L123-L125] |
| Decline equations | Exponential `qi*exp(-D*t)`; hyperbolic `qi/(1+b*D*t)**(1/b)`; harmonic `qi/(1+D*t)`; output clipped at zero | `DeclineCurveResult.predict`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L41-L60] |
| Fitting and selection | Bounded SciPy `curve_fit`; nonnegative qi and D; hyperbolic b bounded away from zero; best result maximizes R-squared, with zero returned for constant data | `_fit_exponential`, `_fit_hyperbolic`, `_fit_harmonic`, `_r_squared`, `best_fit`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L106-L143] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L163-L218] |
| Fiscal arithmetic | Profit = revenue - opex - capex; taxes multiply positive tax bases by code constants; EPL base subtracts investment allowance and floors at zero | `calculate_rfct`, `calculate_supplementary_charge`, `calculate_investment_allowance`, `calculate_epl`, `UKFiscalRegime.calculate`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L25-L72] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L118-L137] |
| Discounting | Initial cashflow = negative capex; operating months start at 1; discount factor `(1+annual_rate/12)**(-t)`; operating net cashflow floored at zero, including loss months | `CrossBasinComparator._compute`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L156-L189] |
| Fiscal comparison branches | UK delegates to standalone regime with capex spread over 36 months; NCS branch computes corporate/special tax and uplift; GoM branch computes royalty and federal tax; unknown selector produces zero | `CrossBasinComparator._apply_fiscal`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L191-L228] |
| Well summaries | Count, arithmetic mean and maximum of selected rows | `UKCSWellLoader.field_summary`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L90-L103] |
| Sparse metadata and reference chain | Mapping delegates to FDAS normalizer, then injected production routes through conversion, recommendation and cashflow engine | `ukcs_field_to_concept`, `run_ukcs_reference_chain`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/field_concept.py:L25-L42] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L38-L78] |

The fiscal source comment names HMRC guidance without an edition or effective-date selector; the implementation has fixed constants and no date argument. This pack records code arithmetic only. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L14-L28] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L96-L111]

The shared unit table names API MPMS Ch. 11, Measurement of Petroleum and Petroleum Products, without an edition or clause title; clause text not checked against the licensed copy. No standard-derived tabulated value is reproduced here. [packages/worldenergydata-core/src/worldenergydata/common/units.py:L16-L25]

The shared gas-unit documentation also names ISO 13443, Natural gas — Standard reference conditions, and GPA 2145, Physical Constants for Natural Gas and Gas Processing; editions and clause titles are absent, and clause text not checked against the licensed copy. [packages/worldenergydata-core/src/worldenergydata/common/units.py:L28-L36]

UNVERIFIED: current-law validity of the fiscal constants, cross-basin fiscal simplifications and authoritative applicability of conversion assumptions; see section 10, #736 and #361.

Returned fiscal, decline and reference-chain payloads do not include a `Citation` sidecar; provenance adoption remains tracked by #361. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L128-L137] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L31-L39] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L70-L78]

## 4. Validated worked examples

Validated examples: **0**; independent engineering reference coverage remains open under #361 and #736. The following **7 regression examples** use synthetic fixtures or code-defined arithmetic; none establishes a live-data or current-tax-law benchmark. [tests/unit/ukcs/test_nsta_client.py:L11-L45] [tests/unit/ukcs/test_field_economics.py:L19-L36] [tests/unit/ukcs/test_reference_chain.py:L25-L48]

All listed results are PASS at the code pin on 2026-10-15, before and after this documentation change; result records are retained with the test evidence. [tests/unit/ukcs/test_field_production.py:L79-L120] [tests/unit/ukcs/test_well_loader.py:L118-L123] [tests/unit/ukcs/test_decline_curves.py:L49-L60] [tests/unit/ukcs/test_field_economics.py:L33-L36] [tests/unit/ukcs/test_nsta_client.py:L150-L181] [tests/unit/ukcs/test_reference_chain.py:L92-L109]

| Case / fixture | Expected output and tolerance basis | Existing test node ID; offline result |
| --- | --- | --- |
| Empty production frame / inline fixture | 0 rows; exact empty predicate, not a physical validation | `tests/unit/ukcs/test_field_production.py::TestUKCSFieldProductionLoaderLoad::test_load_empty_dataframe_returns_empty`; PASS/PASS. [tests/unit/ukcs/test_field_production.py:L79-L91] |
| PPRS schema / inline fixture | Exact year/month; oil bbl, gas Mcf and water bbl from fixture × code conversion factors; `pytest.approx` default tolerance | `tests/unit/ukcs/test_field_production.py::TestUKCSFieldProductionLoaderLoad::test_load_accepts_current_pprs_schema_columns`; PASS/PASS. [tests/unit/ukcs/test_field_production.py:L98-L120] |
| Well average / inline fixture | 10750.0 bbl/day, relative tolerance 0.001 from test assertion | `tests/unit/ukcs/test_well_loader.py::TestUKCSWellLoaderSummary::test_field_summary_avg_test_rate`; PASS/PASS. [tests/unit/ukcs/test_well_loader.py:L118-L123] |
| Exponential forecast / inline result object | NumPy array of exactly 12 monthly predictions; no value-accuracy assertion | `tests/unit/ukcs/test_decline_curves.py::TestDeclineCurveResult::test_predict_returns_array`; PASS/PASS. [tests/unit/ukcs/test_decline_curves.py:L49-L60] |
| Positive-profit RFCT / inline fixture | 3000000.0 currency units; `pytest.approx` default tolerance; code-regime arithmetic only | `tests/unit/ukcs/test_field_economics.py::TestRFCT::test_rfct_on_positive_profit`; PASS/PASS. [tests/unit/ukcs/test_field_economics.py:L33-L36] |
| ArcGIS pagination / mocked responses | Corrected: two one-row pages require offsets 0 and 1; requested capacities remain unchanged. The old test expected offset 2000 and skipped unreturned rows. | `tests/unit/ukcs/test_nsta_client.py::TestNSTAClientDownload::test_download_paginates_official_arcgis_endpoint`; revision-2 regression |
| Reference-chain plumbing / inline fixture | At least 2 months; finite positive gross revenue USD; finite net cashflow USD; royalty approximately 0.0 USD; explicit pre-tax label | `tests/unit/ukcs/test_reference_chain.py::test_reference_chain_returns_labeled_finite_pre_tax_metrics_and_zero_royalty`; PASS/PASS. [tests/unit/ukcs/test_reference_chain.py:L92-L109] |

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations, with G5 from section 9. These checks are requirements for this package, not clearance signatures. (AQG r0, sections 9–11.)

| Gate | Applicability | Module-specific check, numeric pass criterion and unit | Evidence / replay route |
| --- | --- | --- | --- |
| G0 | Applicable: tabular inputs, units and citations | C0.1: `UKCSFieldProductionLoader.load(empty)` returns 0 rows and 6 columns, exact; C0.2: `DeclineCurveAnalyzer.fit` rejects a 2-point series with exactly 1 ValueError; C0.3: `UKCSWellLoader.load` maps an invalid depth to 1 NaN and an invalid rate to 0 bbl/day | PASS; empty/schema and insufficient-data tests plus synthetic invalid numeric probe. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L61-L64] [tests/unit/ukcs/test_decline_curves.py:L134-L137] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L60-L63] |
| G1 | Applicable: Python imports and offline tests; no target solver | C1.1: 119/119 UKCS test cases PASS, 0 failures, 0 skipped cases; C1.2: 9/9 dedicated adapter tests plus 46/46 contract cases PASS, 0 failures | Python import route: normal project environment, `python -m pytest --noconftest`; suite inventory in section 10. [tests/unit/ukcs/test_reference_chain.py:L92-L109] [tests/unit/scheduler/test_ukcs_adapter.py:L38-L69] [tests/unit/production/unified/test_ukcs_adapter_loader.py:L63-L90] |
| G2 | Applicable: hand arithmetic; independent engineering benchmark remains open | C2.1: `DeclineCurveResult.predict([1])` with qi 100 input-rate units and D = ln(2)/month returns 50 input-rate units within 0.0000000001 input-rate units; C2.2: well summary for rates 12000 and 9500 bbl/day returns count 2 and mean 10750 bbl/day within 0.0000000001 bbl/day; C2.3: standalone fiscal arithmetic for revenue 100, opex 20, capex 0 currency units returns take 60 and net 20 within 0.0000000001 currency units | PASS, synthetic hand calculations using halving, arithmetic mean and the pinned code constants; C2.3 checks implementation arithmetic only, not tax authority. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L41-L60] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L99-L103] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L25-L28] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L118-L137] |
| G3 | NOT_APPLICABLE: no dynamics model/time integrator in these tabular calculations | No dynamics criterion | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L47-L100] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L96-L137] |
| G4 | NOT_APPLICABLE: no diffraction body or mesh output | No diffraction criterion | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L70-L78] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L43-L65] |
| G5 | Applicable: reproducible evidence for module use | C5.1: 0 unresolved citation ranges at code pin, 0 section-4 cases without node/result mapping, and 0 mismatches between recomputed SHA-256 fingerprints and retained evidence manifest; units: ranges, cases, digests | PASS, citation resolver, JUnit mapping and evidence manifest; retain code pin, command, Python version and test counts with any use of these outputs. [tests/unit/ukcs/test_reference_chain.py:L92-L109] [tests/unit/ukcs/test_field_production.py:L98-L120] |

Replay C0.3 with one synthetic row containing the required well columns and nonnumeric depth/rate strings; replay C2.1 with `DeclineCurveResult("exponential", 100.0, log(2.0))`; replay C2.2 with two normalized rows in one anonymous dataset; replay C2.3 with `UKFiscalRegime().calculate(100.0, 20.0, 0.0)`. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L55-L65] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L31-L60] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L96-L137]

Additional detection procedures for section 6: D1 force SciPy fitting to raise and inspect fallback quality; D2 omit both PPRS gas columns; D3 download from a prewritten 3-row cache with `max_records=1`; D4 mock an HTTP-success JSON error envelope; D5 compare legacy water factor selection with `WaterUnits.TONNE_TO_BBL`. These characterize existing pitfalls rather than accepting the affected paths as hand-check references. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L154-L161] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L80-L98] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L69-L71] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L128-L143] [packages/worldenergydata-core/src/worldenergydata/common/units.py:L49-L54]

Revision-2 tests below detect SF1–SF3 in section 6. The corrected pagination test requires the next offset to equal returned rows; timeline forwarding establishes input wiring, not cost completeness. C0.3 concerns well values only; no detection check exists for zero-filled production measurements. G1 regression counts therefore do not clear these data or economics paths.

### Revision-2 detection checks

| Finding | Detection test node | Independent expectation |
| --- | --- | --- |
| Unknown selector | `tests/unit/ukcs/test_cross_basin.py::test_unknown_fiscal_selector_is_refused` | Issue #1284: raise, including empty histories |
| Negative net month | `tests/unit/ukcs/test_cross_basin.py::test_negative_month_is_retained` | Synthetic [5, -4, 7] accumulates to [5, 1, 8] USD |
| Pre-tax loss | `tests/unit/ukcs/test_cross_basin.py::test_pre_tax_loss_is_retained` | Hand sum -3 - 6 = -9 USD |
| Clipped diagnostic | `tests/unit/ukcs/test_cross_basin.py::test_government_take_diagnostic_is_not_clipped` | Synthetic tax 12 / profit 8 = 1.5; signed net -4 USD |
| Missing drilling basis | `tests/unit/ukcs/test_reference_chain.py::test_missing_drilling_timeline_is_refused`; `tests/unit/ukcs/test_reference_chain.py::test_invalid_drilling_timeline_is_refused` | Unknown or invalid effort is refused before acquisition |
| Timeline forwarding | `tests/unit/ukcs/test_reference_chain.py::test_drilling_timeline_reaches_cashflow_engine` | Caller-supplied mapping reaches FDAS unchanged |
| Empty production | `tests/unit/ukcs/test_reference_chain.py::test_empty_production_is_refused` | No inferred calendar origin or evaluated output |
| Short pages | `tests/unit/ukcs/test_nsta_client.py::test_short_pages_preserve_every_row_and_cache` | Five indexed rows, offsets [0,2,4]; cap three stops after offsets [0,2] |

Paging semantics follow [ArcGIS REST Query, resultOffset and resultRecordCount](https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/), opened 2026-10-22. All new monetary tests use synthetic inputs and independent arithmetic, not assumed fiscal coefficients. The comparator retains its nominal annual rate divided by twelve convention. Current-law fiscal validity remains UNVERIFIED.

The FDAS drilling helper currently returns days multiplied by a rate named in MM USD/day, then assigns it to a USD cashflow field without conversion (`fdas/analysis/cashflow.py::calculate_drilling_capex`, `generate_monthly_cashflow`). This dimensional concern remains NOT_EVALUATED for investment use; no coefficient or published report is silently changed here. The reference chain remains pre-tax plumbing, with fixed OPEX and facilities capital still omitted.

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

The entries below record observations against the code pin, checked on 2026-10-15; issue references identify existing work or numbered issue drafts, not completed corrections. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L154-L161] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L69-L71]

| Symptom, silent cases first | Cause / detection | Tracking and date |
| --- | --- | --- |
| SF1: unknown selectors, loss floors and clipped take diagnostics | Corrected: unknown selectors raise before iteration; signed net cashflows and unbounded take ratios are retained. | #1284; revision-2 nodes below |
| SF2: missing drilling capital or production | Corrected: a nonempty dated drilling timeline with finite positive effort is required and forwarded unchanged; empty production raises before screening. Inherited cost units and other omitted costs remain unqualified. | #1284; revision-2 nodes below |
| SF3: short ArcGIS pages can silently skip rows and produce an apparently complete cache | Offset advances by requested `record_count`, not received rows. No detection check exists. `tests/unit/ukcs/test_nsta_client.py::TestNSTAClientDownload::test_download_paginates_official_arcgis_endpoint` is historical defective assertion, corrected in revision 2: after 1 row with the limit flag true it expects offset 2000; it is not completeness evidence. | #1284; issue pending (2), 2026-10-16. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L128-L143] [tests/unit/ukcs/test_nsta_client.py:L150-L181] |
| A decline fit can return plausible parameters after optimization fails | Broad exception fallback sets quality to zero and RMSE to infinity; hyperbolic/harmonic failures delegate to exponential. D1 reproduced with forced optimization failure; do not use fallback as a reference. | issue pending (1), 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L154-L161] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L189-L190] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L217-L218] |
| Missing/nonpositive decline observations compress elapsed time | `dropna`, positive filtering and `arange(len(clean))` discard calendar gaps; no detection check exists in the shipped tests for elapsed-calendar fidelity | issue pending (1), 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L85-L94] |
| Download row cap ignored on cached data; a limited cache can masquerade as a full dataset | Cache keys omit cap, source and completeness; cache hit returns before cap handling. D3 reproduced: request cap 1 returns 3 cached rows. | issue pending (2), 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L45-L58] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L60-L88] |
| ArcGIS error payload can be cached as empty success | HTTP success is checked, JSON `error` is not; missing `features` becomes empty list. D4 reproduced with a synthetic error envelope and an empty returned frame. The scheduler reports `success` with 0 records for an empty payload; no detection check exists for false refresh success. | issue pending (2), 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L128-L143] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/ukcs_refresh.py:L53-L86] |
| Legacy water mass uses the crude-oil mass factor; missing measurements become zero | Legacy water path reuses `TONNES_TO_BBL`, while shared water constants have a separate mass conversion. D5 detects factor selection; C0.3 exposes well-rate coercion only; no detection check exists for zero-filled oil, gas or water production measurements. Independent density basis is not established here. | issue pending (3), 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L22-L26] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L75-L98] [packages/worldenergydata-core/src/worldenergydata/common/units.py:L49-L54] |
| PPRS input missing either gas column raises AttributeError | Scalar default `0.0` has no `.fillna`; D2 reproduced the missing-both-columns case: `'float' object has no attribute 'fillna'` | issue pending (3), 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L84-L87] |
| Condensate is unknown, rather than a measured zero | Loader emits only oil, gas and water; adapter adds NaN condensate; `tests/unit/production/unified/test_ukcs_adapter_loader.py::test_fetch_transforms_nsta_loader_output_to_standard_columns` detects loss of unknownness | #796, 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L61-L64] [tests/unit/production/unified/test_ukcs_adapter_loader.py:L81-L90] |
| Sparse metadata or absent depth still yields rankings/cashflows | Only name, region, optional depth and source are mapped; unknown development-system route defaults to `subsea15`. Detection: `tests/unit/ukcs/test_reference_chain.py::test_uk_field_meta_mapping_builds_sparse_concept` and `tests/unit/ukcs/test_reference_chain.py::test_sparse_uk_concept_screen_is_deterministic`; no completeness gate exists for a published recommendation. | #795 and #717, 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/field_concept.py:L25-L42] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L47-L57] [tests/unit/ukcs/test_reference_chain.py:L60-L89] |
| Pre-tax chain metrics may be mistaken for after-tax investment results | Runner labels plumbing and sums engine cashflows; standalone fiscal model is a separate path. Detection: `tests/unit/ukcs/test_reference_chain.py::test_reference_chain_returns_labeled_finite_pre_tax_metrics_and_zero_royalty`; no current-law parity check exists. | #736 and #717, 2026-10-15. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L59-L78] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L93-L99] [tests/unit/ukcs/test_reference_chain.py:L92-L109] |
| Synthetic default adapter data may be treated as live-source data | Loader injection selects source-backed rows; no-loader path generates benchmark rows. Detection: `tests/unit/production/unified/test_ukcs_adapter_loader.py::test_default_synthetic_surface_still_lists_benchmark_fields` requires the synthetic source label. | #797 and #717, 2026-10-15. [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py:L33-L71] [tests/unit/production/unified/test_ukcs_adapter_loader.py:L116-L128] |
| Low severity: empty well summaries present rates as measured zeros | `field_summary` returns count 0, mean 0.0 and maximum 0.0 for no rows. Count exposes emptiness; no detection check exists for distinguishing unmeasured rates from true zeros. | issue pending (3), 2026-10-16. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L90-L103] |
| Low severity: duplicate profile names overwrite comparison results | `compare` uses profile name as the result dictionary key; no detection check exists for name collisions. | issue pending (7), 2026-10-16. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L144-L148] |

Read-only issue inventory: historical intake records #192 and #194, completed chain #717, and follow-ons #736, #795, #796 and #797; no additional incident is inferred from an intake title. (worldenergydata, issue records #192, #194 and #717, read 2026-10-15.) The reference-chain scope and missing-stream constraints are recorded in the repository plan. [docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md:L22-L29] [docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md:L50-L61]

## 7. Lessons log

| Date | Entry | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | Keep synthetic adapters, sparse concept ranking and pre-tax chain metrics explicitly labelled | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/field_concept.py:L1-L7] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L70-L78] [tests/unit/production/unified/test_ukcs_adapter_loader.py:L116-L128] | Sections 1, 4 and 6 | Pending; issue pending (4) |
| 2026-10-15 | Initial pack | A fit result object is not proof of optimization success; inspect quality and finite residuals | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L154-L161] | Sections 5 and 6 | Pending; issue pending (1) |

## 8. Ownership

Review contract: calculations quality manager for this data pipeline; deputy role to be appointed; producing role is module documentation maintainer; ambiguous numerical criteria and method classification go to the family quality manager; cross-module priorities go to the maintainer. Clearance requires a provider different from the producer. Deputy appointment, shared-log indexing and independent clearance remain open under issue pending (4). (AQG r0, section 11, Sign-off and independence.)

## 9. Dependencies and implementation inventory

| Direction | Dependency and boundary | Evidence |
| --- | --- | --- |
| Upstream | NSTA CSV or ArcGIS attributes; requests is optional at import, required for downloads; HTTP failures are raised | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L15-L20] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L60-L96] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L116-L143] |
| Upstream | Shared oil, gas and water unit constants; NumPy, pandas, SciPy and scikit-learn numerical routines | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L18-L26] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L84-L98] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L132-L151] [packages/worldenergydata-ukcs/pyproject.toml:L29-L35] |
| Boundary | Production adapter accepts a duck-typed loader and bridges its frame; the reference runner accepts that adapter and delegates to FDAS/recommendation | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/ukcs_adapter.py:L97-L110] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L38-L78] |
| Downstream | Scheduler composes downloader/normalizer and writes raw plus normalized Parquet, with explicit output directory required | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/ukcs_refresh.py:L29-L78] |

Implementation-map provenance: `digitalmodel`, `docs/registry/implementation-map.yaml`, branch `codex/implmap-work`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `families` inventory. The map snapshot contains 13 families and 0 implementation rows whose path is inside the header package; the module's map-family inventory is therefore empty, with 0 counted families. A8(c): `NOT_APPLICABLE`, because no map family has an in-package implementation row. Signal exclusion and enclosing-definition assignment have no counted family to process. (digitalmodel, Implementation map, cited map commit and data revision, families/implementations.)

Map follow-up, issue pending (4): add the section-3 method families with in-package rows before counting them: NSTA pagination/cache handling; production unit/schema normalization and annual aggregation; exponential/hyperbolic/harmonic prediction and nonlinear fitting with R-squared selection; fiscal arithmetic; monthly discounting and fiscal comparison; well summaries; sparse metadata normalization and reference-chain orchestration. The synthetic-profile generator also computes the exponential formula independently of the prediction method. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L101-L143] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L47-L125] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L41-L218] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L34-L137] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L74-L78] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L156-L228] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L75-L103] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L38-L78]

Supplementary repository search included tracked Python under `packages`, `src` and `scripts`, using `decline`, `ring_fenced_profit`, `nsta_production_`, `annual_aggregate`, `UKFiscalRegime` and NPV definitions. Confirmed additional candidates include a separate country decline implementation, generic discounting, parallel production forecasting in `packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py` and fiscal comparison in `packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py`, and scheduler composition of the UKCS downloader. Decline and discounting consolidation is tracked by #1104. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L60-L94] [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L167-L223] These are map follow-up candidates; this search does not alter the empty counted-family inventory. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L38-L56] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L100-L132] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L160-L181] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/ukcs_refresh.py:L48-L78]

## 10. Coverage and open items

### Read coverage

Read scope: every package Python file, without excluded subpackages; pinned extents are recorded below.

| Package file | Evidence |
| --- | --- |
| `__init__.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/__init__.py:L1-L8] |
| `analysis/__init__.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/__init__.py:L1-L1] |
| `analysis/cross_basin_example.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L1-L262] |
| `analysis/field_economics.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L1-L137] |
| `field_concept.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/field_concept.py:L1-L52] |
| `production/__init__.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/__init__.py:L1-L1] |
| `production/decline_curves.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L1-L218] |
| `production/field_production.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/field_production.py:L1-L132] |
| `production/nsta_client.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/nsta_client.py:L1-L147] |
| `reference_chain.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L1-L99] |
| `wells/__init__.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/__init__.py:L1-L1] |
| `wells/well_loader.py` | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/wells/well_loader.py:L1-L103] |

Package README and package metadata were read; metadata has a recursive Markdown package-data glob, so adding this pack would include it in the distribution unless packaging is corrected separately; issue pending (6). [packages/worldenergydata-ukcs/README.md:L1-L8] [packages/worldenergydata-ukcs/pyproject.toml:L56-L57]

Module-specific documentation read in full: the package README and the reference-chain plan. Other documentation discovery below records matching UKCS passages; complete cross-document reconciliation remains under #349 and issue pending (4). [packages/worldenergydata-ukcs/README.md:L1-L8] [docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md:L14-L29]

| Documentation discovered | Matching passage at pin |
| --- | --- |
| `docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md` | [docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md:L16-L16] |
| `docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md` | [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L17-L17] |
| `docs/plans/2026-05-04-issue-269-sodir-brazil-ukcs-adapters.md` | [docs/plans/2026-05-04-issue-269-sodir-brazil-ukcs-adapters.md:L1-L1] |
| `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` | [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L49-L49] |
| `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21] |
| `docs/modules/repository-architecture.md` | [docs/modules/repository-architecture.md:L105-L105] |
| `docs/plans/2026-05-08-issue-394-repo-structure-normalization.md` | [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L74-L74] |
| `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md` | [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L126-L126] |
| `docs/plans/README.md` | [docs/plans/README.md:L18-L18] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L12-L12] |
| `docs/adr/0001-domain-package-split.md` | [docs/adr/0001-domain-package-split.md:L48-L48] |
| `docs/plans/2026-05-04-issue-360-scheduler-health.md` | [docs/plans/2026-05-04-issue-360-scheduler-health.md:L38-L38] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L16-L16] |
| `docs/modules/fdas/country-adapter-checklist.md` | [docs/modules/fdas/country-adapter-checklist.md:L48-L48] |
| `docs/reports/data-freshness-scorecard-2026-06-08.md` | [docs/reports/data-freshness-scorecard-2026-06-08.md:L30-L30] |
| `docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md` | [docs/plans/2026-04-23-issue-342-restore-broken-proxy-comparison-regression-boundary.md:L64-L64] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L41-L41] |
| `docs/reports/scheduler-health-2026-W24.md` | [docs/reports/scheduler-health-2026-W24.md:L16-L16] |
| `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` | [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L27-L27] |
| `docs/reports/scheduler-health-2026-W16.md` | [docs/reports/scheduler-health-2026-W16.md:L15-L15] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L15-L15] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L16-L16] |
| `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` | [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L204-L204] |
| `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` | [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L35-L35] |
| `docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md` | [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L239-L239] |

### Tests and evidence

The package has 7 dedicated test files containing 119 collected test cases; dedicated external adapter tests add 9 cases and `tests/contracts` adds 46 cases. BASE and AFTER each report **174 run, 174 passed, 0 failed, 0 skipped, 0 NOT_RUN**, with unchanged code at BASE and on the uncommitted documentation tree. The replay command is `uv run --no-project --with pytest <dependency options> python -m pytest --noconftest <paths> -q -rA -p no:cacheprovider --basetemp=<scratch> --cov-report= --cov-report=term`, with coverage data directed to scratch and all package source roots on `PYTHONPATH`. Required numerical, configuration, Parquet and adapter-contract dependencies were supplied explicitly; no tests were skipped and no extra workers were started. Counts were repeated on 2026-10-16 before and after this revision. [tests/unit/ukcs/test_reference_chain.py:L92-L109] [tests/unit/scheduler/test_ukcs_adapter.py:L38-L69] [tests/unit/production/unified/test_ukcs_adapter_loader.py:L63-L90]

| Test scope | BASE pass / fail / skip | AFTER pass / fail / skip |
| --- | --- | --- |
| `tests/unit/ukcs` | 119 / 0 / 0 | 119 / 0 / 0 |
| `tests/unit/scheduler/test_ukcs_adapter.py`, `tests/unit/production/unified/test_ukcs_adapter_loader.py`, `tests/contracts` | 55 / 0 / 0 | 55 / 0 / 0 |

| Dedicated test file read | Evidence |
| --- | --- |
| `tests/unit/ukcs/test_cross_basin.py` | [tests/unit/ukcs/test_cross_basin.py:L1-L121] |
| `tests/unit/ukcs/test_decline_curves.py` | [tests/unit/ukcs/test_decline_curves.py:L1-L208] |
| `tests/unit/ukcs/test_field_economics.py` | [tests/unit/ukcs/test_field_economics.py:L1-L195] |
| `tests/unit/ukcs/test_field_production.py` | [tests/unit/ukcs/test_field_production.py:L1-L173] |
| `tests/unit/ukcs/test_nsta_client.py` | [tests/unit/ukcs/test_nsta_client.py:L1-L232] |
| `tests/unit/ukcs/test_reference_chain.py` | [tests/unit/ukcs/test_reference_chain.py:L1-L109] |
| `tests/unit/ukcs/test_well_loader.py` | [tests/unit/ukcs/test_well_loader.py:L1-L123] |

### Open items

| Item | Scope and required closure evidence | Responsible role | Tracking |
| --- | --- | --- | --- |
| Fiscal and conversion authority; UNVERIFIED claim from section 3 | Reconcile effective dates and fiscal sources with authoritative public material; add independent expected values, after-tax parity and provenance sidecars; 0 independently validated section-4 cases at present | Module maintainer | #736, #361 |
| Economics qualification | Input guards and signed cashflows are corrected in revision 2. Qualify inherited drilling-cost units, facilities capital, fixed OPEX and fiscal assumptions before investment use. | Module maintainer | #1284; #736 |
| Live source validity | UNVERIFIED: present endpoint availability, licence terms, production coverage and completeness; no live source download or independent production benchmark was run | Module maintainer | #797 |
| Decline quality and elapsed time | Surface fallback status and preserve or explicitly constrain calendar spacing; add focused failure/gap tests | Module maintainer | issue pending (1) |
| Cache and payload completeness | Separate partial/full caches and cap/source identities, enforce cached limits, reject ArcGIS error payloads and detect empty refresh success; short-page offsets corrected in revision 2 | Module maintainer | #1284; issue pending (2) |
| Production normalization | Correct missing-column behavior and establish legacy water density/conversion basis; audit zero-filled missing measurements | Module maintainer | issue pending (3) |
| Summary and profile identity | Distinguish empty well rates from measured zero; reject duplicate comparison profile names before dictionary insertion | Module maintainer | issue pending (3), issue pending (7) |
| Rich metadata and condensate | Keep sparse ranking and unknown streams explicit until source-backed enrichment and component mapping are tested | Module maintainer | #795, #796 |
| Knowledge coverage and indexing | Complete historical-doc reconciliation; add absent map families; appoint deputy; index/shared-log entry and independent clearance; no routing registry exists at this code pin | Documentation maintainer | #349; issue pending (4) |
| Identifying discovery text | 8 discovery files with identifying names in package Python and dedicated tests; replace examples with neutral dataset IDs before quoting them in guidance; names are not reproduced in this pack | Module maintainer | issue pending (5) |
| Pack distribution boundary | Recursive Markdown glob currently includes this documentation; exclude knowledge packs from package data without suppressing ordinary docs | Packaging maintainer | #529 |

The identifying-text count comprises 2 package Python files and 6 dedicated test files; the cited regions provide the evidence without repeating their identifiers. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L8-L9] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L3-L9] [tests/unit/ukcs/test_decline_curves.py:L14-L35] [tests/unit/ukcs/test_nsta_client.py:L11-L45] [tests/unit/ukcs/test_field_production.py:L12-L19] [tests/unit/ukcs/test_well_loader.py:L8-L15] [tests/unit/ukcs/test_cross_basin.py:L15-L23] [tests/unit/ukcs/test_reference_chain.py:L25-L57]

The table's issue-pending markers refer to numbered maintainer issue drafts; issue numbers and independent clearance must be recorded before this DRAFT pack is cleared. (AQG r0, section 11, Sign-off and independence.)
