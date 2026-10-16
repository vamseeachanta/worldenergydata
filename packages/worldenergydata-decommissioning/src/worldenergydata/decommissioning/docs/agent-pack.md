# Decommissioning module knowledge pack

| Header | Value |
| --- | --- |
| Module | `decommissioning` |
| Repository | `worldenergydata` |
| Path | `packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning` |
| Pack revision | 1, 2026-10-15 |
| Code revision | `285d65c40896b17ccf44568e59f5b789d59c943e` |
| Analysis family | EC; data pipelines and Python calculations |
| Quality manager role | Calculations quality manager; interim data-pipeline coverage |
| Status | DRAFT |

The review basis is AQG r0, sections 10–11 (Python calculations and independent sign-off), and the Module agent lifecycle, revision 0, sections 2–3 (location and template).

## 1. Purpose and scope

The package exports parametric cost estimation, cost calibration, late-life screening, documentation completeness scoring and regulatory lookup. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/__init__.py:L30-L75]

Facility liability classifies facility rows, delegates asset pricing to `DecommissioningCostEstimator`, and aggregates the results by region and asset type. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L78-L144]

Cost estimation accepts seven asset types and five region keys; regulatory lookup covers four region keys, without a `west_africa` branch. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L17-L72] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L15-L24] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L186-L198] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L313-L325] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L416-L428]

These are screening calculations: the cost result identifies its source as `parametric_estimate`, the cessation function calls itself a rough extrapolation, and regulation queries return static records rather than checking compliance. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L161-L170] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L112-L128] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L45-L96]

The distribution metadata declares Alpha; no routing maturity is asserted in this pack. [packages/worldenergydata-decommissioning/pyproject.toml:L14-L21]

Section 6 records 16 failure-mode rows, including four silent failures tracked by #1281. The 14 checks in section 5 do not detect those four failures; the pack documents current behavior without correcting the implementation.

### Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-15 | Initial package inventory, regression evidence and limitations. |
| 1 | 2026-10-15 | Record four silent failures under #1281, facility pricing assumptions, uncomputed diagnostics and absent year escalation; correct detection and routing wording. |

## 2. Inputs and outputs

### Inputs

| Route / input | Unit | Accepted form / range / default | Source and evidence |
| --- | --- | --- | --- |
| `estimate`: `asset_type`, `region` | categorical | Lowercased; membership checked against constants; region defaults to `gom` | Function arguments and validation. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L109-L146] |
| `water_depth_m`, `weight_tonnes`, `year` | m, tonnes, calendar year | Depth required; weight defaults to 0.0 and `None` becomes 0.0; year defaults to 2025 and is returned without escalation; numeric bounds are not checked | Caller arguments. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L109-L126] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L148-L170] |
| `pipeline_km` overloaded depth argument | km by API documentation | The documentation interprets `water_depth_m` as length; the pipeline factors have zero slope, so length does not scale the result; see section 6 | Caller argument, not physical water depth for this type. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L42-L47] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L119-L124] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L153-L159] |
| `fit`: removal DataFrame | m, tonnes, MUSD, calendar year | Nonempty input requires `asset_type`, `water_depth_m`, `weight_tonnes`, `cost_musd`, `year`; empty input installs baseline factors; only five exact asset-type strings enter fits, while all rows count toward `total_records`; see section 6 | Supplied history or synthetic records. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L30-L36] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L119-L147] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L22-L28] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L149-L186] |
| `assess_field`: production DataFrame | year, month, bbl/month | Columns `year`, `month`, `oil_bbl`; field identifier required; region defaults to `unknown`; empty input returns zeros and an unflagged result; a final NaN interrupts the idle count; see section 6 | Caller time series. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L166-L200] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L100-L109] |
| `score`: availability dictionary | dimensionless fractions | Five categories; missing keys become false; `None` becomes zero; booleans become zero/one; finite floats clamp to [0, 1], but NaN becomes 1.0; `asset_type` defaults to `jacket` | Documentation availability, not measured structural condition. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L20-L35] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L63-L89] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L118-L153] |
| `price_portfolio`: facility DataFrame | depth m; other columns categorical or identifiers | Reads `HOST_TYPE`, `COUNTRY`, `US_GOM_FLAG`, `WATER_DEPTH_M`, `FACILITY_ID`, `FACILITY_NAME`; missing depth becomes 0.0; every priced row uses weight 0.0 | Caller-curated rows. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L93-L115] |
| Regulatory region / requirement | categorical | Lowercased; unknown region returns []; unknown pair returns 0 months | Static database, not an absence-of-obligation assertion. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L45-L74] |

### Outputs

| Route / output | Unit / interpretation | Evidence |
| --- | --- | --- |
| `DecommissioningCostEstimate`; campaign list; total and regional dictionaries | MUSD; single results and totals rounded to four decimal places; confidence is a category stored in factors | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L79-L91] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L161-L218] |
| `CalibrationFit`, `CalibrationResult`, result DataFrame | Base and RMSE in MUSD; R-squared dimensionless; coverage percentage counts data-driven asset types, not records | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L53-L92] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L173-L186] |
| `LateLifeAssessment`; screening/filter lists | bbl/day, decline %, idle-month count, boolean flag, trigger string, cessation calendar year; zero cessation means not applicable | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L30-L42] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L223-L262] |
| `CompletenessScore`; portfolio DataFrame | Dimensionless weighted score, categorical risk, category gaps; `top_gap` is the first gap in category order | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L43-L55] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L155-L168] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L187-L208] |
| Facility roll-up dictionary | MUSD sums and means; counts of modeled, unmodeled-region and unmapped-asset rows; priced row list | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L118-L144] |
| Regulations list / `regulatory_summary` | Lead times in months; reference and threshold strings; one summary row per database record | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_model.py:L9-L19] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L77-L96] |

No spatial frame, origin, phase or vector sign convention is consumed by these routes; the relevant transformations are scalar cost, production and availability operations. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L153-L170] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L196-L206] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L144-L168]

Monthly production is divided by a fixed 30.0 to obtain bbl/day; positive decline means reduced production and increases are floored at zero decline. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L77-L84] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L196-L200]

File formats belong to consumers: regional liability writes its priced rows as CSV, while the package route returns in-memory dictionaries and DataFrames. [scripts/decommissioning/build_regional_liability.py:L105-L123] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L133-L144]

## 3. Method and governing standards

### Calculation routes

| Method | Implementation and interpretation | Provenance / limits |
| --- | --- | --- |
| Parametric cost | `estimate`: `C = (b + a*w + d*h)*r`, rounded to four decimal places; factor selection prefers an instance calibration | Factor tables are code constants, not verified regulatory tariffs. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L17-L69] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L148-L170] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L252-L257] |
| Cost calibration | `_fit_asset_type`: least squares with columns [1, weight, depth]; below 3 records retain baseline; clamp fitted intercept to [0.5, 2.0] times baseline, then blend 0.7 fitted / 0.3 baseline | `fit` installs only the blended intercept; slopes remain baseline; RMSE and R-squared describe the unconstrained three-coefficient fit. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L145-L165] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L278-L352] |
| Late-life decline | `_compute_decline_pct`: compare mean production across all years at or before `max_year - 5` against the latest year's mean, then floor percentage decline at zero | It does not select one historical endpoint or enforce five complete calendar years. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L19-L22] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L50-L84] |
| Idle and cessation | Count trailing sorted rows at or below 10.0 bbl/day; flag at 12 rows or decline >=80.0%; project with annual fractional decline `decline_pct / 100 / 5` for at most 50 iterations | Calendar continuity is not validated; the trigger labels use `>` even though the comparisons use `>=`. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L87-L109] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L130-L150] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L202-L219] |
| Completeness | Normalize category scores; redistribute mooring weight equally for `jacket`, `concrete_gravity`, `subsea`; weighted sum; risk boundaries 0.70 and 0.40; gaps below 0.5 | Gap detection still considers every category, including one with zero weight. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L20-L35] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L63-L103] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L144-L168] |
| Facility liability | `region_of` gives the GoM flag priority; `classify_asset_type` uses an exact stripped mapping; `price_portfolio` excludes unknown regions before unknown assets | No per-well plugging count is produced by this facility pricing route. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L25-L75] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L93-L144] |
| Regulatory lookup | Filter by region, select the first matching lead time, or serialize all static records | Reference strings are carried as data; no retrieval, edition resolution or clause evaluation occurs. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L45-L96] |

UNVERIFIED: The cost factors' claimed published-benchmark basis has no named edition, table or equation in the estimator docstring; empirical validity is not established by the range tests; issue pending (7). [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L99-L107] [tests/unit/decommissioning/test_cost_model.py:L117-L133]

### Regulatory references stored by the module

The following inventory identifies code references, without adopting the accompanying thresholds as checked legal requirements. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_model.py:L13-L19] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L85-L96]

| Stored source / clause identifier | Located uses | Edition / clause-text status |
| --- | --- | --- |
| 30 CFR 250.1725, 250.1750, 250.1703, 250.1703(b) | Structure removal, pipeline decommission, decommissioning plan, financial assurance records | Code gives section numbers without an edition. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L25-L75] |
| 30 CFR 250.1740, 250.1743, 250.1709 | Equipment clearance, site clearance, concurrent-obligation records | Code gives section numbers without an edition. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L76-L122] |
| 30 CFR 250.1726, 250.1721, 250.1780 | Conductor removal, third-party verification, report records | Code gives section numbers without an edition. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L135-L167] |
| Other BSEE source strings | NTL and policy/guidance references | Exact source labels are stored in records. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L15-L24] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L46-L54] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L99-L109] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L123-L134] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L168-L179] |
| UKCS references | Petroleum Act sections, OSPAR, well and environmental guidance, tax/security/safety references | Mixed dated and undated reference strings; no external validation inferred. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L186-L307] |
| NCS references | Petroleum Act, petroleum/well/management/facilities regulation sections | Structured lead time and threshold narrative disagree for the disposal-plan record; see section 6. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L313-L410] |
| Brazil references | ANP resolution/portaria and IBAMA references; `ABNT NBR 15544` appears in threshold text | Edition and clause title for the licensed reference are not recorded; clause text not checked against the licensed copy. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L416-L488] |

UNVERIFIED: Regulatory currency, clause accuracy and edition consistency remain unconfirmed; the attempted public eCFR source returned an access-request page rather than clause text; issue pending (3). [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L15-L180]

UNVERIFIED: Standards-derived output citation sidecars are not demonstrated by the returned regulation schema, which holds `reference_doc` as a string; issue pending (3). [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_model.py:L9-L19] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L85-L96]

## 4. Validated worked examples

Validated examples: **0**; the selected examples below exercise code-defined constants, constructed fixtures or self-consistency, rather than an externally sourced cost benchmark. [tests/unit/decommissioning/test_cost_model.py:L129-L133] [tests/unit/decommissioning/test_cost_calibration.py:L70-L73] [tests/unit/decommissioning/test_late_life.py:L42-L63]

### Regression examples

Verification record, 2026-10-15: every node below PASS at the header pin before editing; all seven nodes also PASS after editing; the execution record is in section 10.

| Case | Source / input | Expected value and tolerance basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 flat subsea cost | In-memory calls at depths 100 and 2000 m and weights 0 and 500 tonnes | Equal MUSD within relative 0.01, the test's code-stability criterion | `tests/unit/decommissioning/test_cost_model.py::test_subsea_tree_flat_cost` | PASS. [tests/unit/decommissioning/test_cost_model.py:L129-L133] |
| R2 campaign sum | Two asset dictionaries; no external input file | Total equals sum of returned MUSD costs within relative 1e-6, the test's arithmetic criterion | `tests/unit/decommissioning/test_cost_model.py::test_total_cost_musd_equals_sum` | PASS. [tests/unit/decommissioning/test_cost_model.py:L169-L181] |
| R3 seeded records | Two calls to `synthetic_removal_dataframe(30)` | 0 differing cells under `assert_frame_equal`; seeded-generator reproducibility | `tests/unit/decommissioning/test_cost_calibration.py::TestSyntheticDataFrame::test_seeded_rng_is_reproducible` | PASS. [tests/unit/decommissioning/test_cost_calibration.py:L70-L73] |
| R4 weighted documentation | Availability: as-built and inspection true; other categories zero; `fpso` | Score 0.55 ±0.01 dimensionless; test expectation from stored weights | `tests/unit/decommissioning/test_data_completeness.py::test_partial_scores_average_correctly` | PASS. [tests/unit/decommissioning/test_data_completeness.py:L103-L113] |
| R5 decline flag | `_declining_field` fixture; no input file | Flag true; 0 boolean mismatches; synthetic production profile, not a validated cessation forecast | `tests/unit/decommissioning/test_late_life.py::test_high_decline_field_is_flagged` | PASS. [tests/unit/decommissioning/test_late_life.py:L42-L63] [tests/unit/decommissioning/test_late_life.py:L126-L129] |
| R6 portfolio exclusions | Three synthetic facility rows | 1 modeled, 1 unmapped asset, 1 unmodeled region, 1 regional and 1 asset count; exact integer counts | `tests/unit/decommissioning/test_facility_liability.py::test_price_portfolio_counts_and_exclusions` | PASS. [tests/unit/decommissioning/test_facility_liability.py:L82-L114] |
| R7 summary serialization | Built-in static database | Summary row count equals database length; 0 missing rows; no legal-accuracy inference | `tests/unit/decommissioning/test_regulations.py::test_regulatory_summary_row_count_matches_database` | PASS. [tests/unit/decommissioning/test_regulations.py:L157-L159] |

## 5. QA gates

Gate applicability follows AQG r0, section 10, Python calculations, with G5 from section 9; checks below are review criteria, not a claim of signed clearance.

| Gate | Applicability / route | Module-specific checks |
| --- | --- | --- |
| G0 | Applicable: validate input keys, units and record schema | G0-01 to G0-03; D-01, D-03 to D-07 |
| G1 | Applicable: import Python package and execute offline tests; no target-program deck is written by the listed package routes | G1-01. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L161-L195] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L133-L144] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L77-L96] |
| G2 | Applicable: independent arithmetic evaluation of implemented cost and weighting formulas; empirical validation remains open | G2-01, G2-02, D-02 |
| G3 | NOT_APPLICABLE: time-series screening returns an assessment without integrating dynamics | No dynamics run. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L196-L233] |
| G4 | NOT_APPLICABLE: facility pricing classifies scalar input rows and delegates cost; no diffraction calculation | No body/mesh result. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L93-L144] |
| G5 | Applicable: retain code/input fingerprints, node results, failures and limitations with the review evidence; independent appendix sign-off remains open | G5-01; issue pending (7) |

### Checks and observed results

Verification record, 2026-10-15: scratch recipes and input digests retained as `module_checks.py`, `module-checks.json` and `module-evidence.json`; FAIL rows below detect unchanged source defects, with draft references in section 6.

| ID / gate | Executable check and numeric pass criterion | Evidence / observed result | Code or test basis |
| --- | --- | --- | --- |
| G0-01 / G0 | `estimate('bad',100)` and `estimate('jacket',100,region='bad')`: 2 `ValueError` exceptions | PASS: 2 exceptions | [tests/unit/decommissioning/test_cost_model.py:L230-L237] |
| G0-02 / G0 | `fit(DataFrame({'asset_type':['jacket']}))`: 1 `ValueError` for missing columns | PASS: 1 exception | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L145-L147] [tests/unit/decommissioning/test_cost_calibration.py:L103-L106] |
| G0-03 / G0 | `regulatory_summary()`: exactly 39 rows, 0 null cells | PASS: 39 rows, 0 null cells; structural evidence only | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L15-L180] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L186-L307] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L313-L410] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L416-L494] |
| G1-01 / G1 | `uv run --extra test python -m pytest tests/unit/decommissioning -q -rA -p no:cacheprovider` with scratch output options: 133 passed tests, 0 failed/error/skipped nodes | PASS: 133 passed at the pin | [tests/unit/decommissioning/test_cost_model.py:L24-L247] [tests/unit/decommissioning/test_cost_calibration.py:L47-L233] [tests/unit/decommissioning/test_data_completeness.py:L33-L231] [tests/unit/decommissioning/test_late_life.py:L97-L245] [tests/unit/decommissioning/test_facility_liability.py:L19-L114] [tests/unit/decommissioning/test_regulations.py:L33-L207] |
| G2-01 / G2 | `estimate('jacket',100,1000)`: compare with `2.0 + 0.00005*1000 + 0.005*100`; absolute error <=0.0001 MUSD | PASS: 0.0 MUSD error; checks implementation arithmetic, not cost-factor validity | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L18-L23] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L153-L166] |
| G2-02 / G2 | R4: compare `overall_score` with `0.30 + 0.25`; absolute error <=0.01 dimensionless | PASS: 0.0 score error | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L20-L26] [tests/unit/decommissioning/test_data_completeness.py:L103-L113] |
| G5-01 / G5 | Hash all 9 package Python files and 7 test Python files, pin every result to code revision, associate all 133 node results: 0 missing fingerprints/results | PASS: 0 missing records in scratch evidence; signature and report appendix are not supplied | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/__init__.py:L30-L75] [tests/unit/decommissioning/test_regulations.py:L157-L159] |
| D-01 / G0 | Compare pipeline lengths 1 and 10 km: cost ratio 10.0 within 0.0001 dimensionless | FAIL: both cost 0.5 MUSD; issue pending (1) | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L42-L47] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L153-L159] |
| D-02 / G2 | Fit 5 jacket rows, `w=i`, `h=i*i`, `cost=2+w+2*h`, `i=0..4`, year 2020; compare reported RMSE with applied-estimator RMSE, difference <=0.0001 MUSD | FAIL: reported 0.0 MUSD, applied 19.2 MUSD; issue pending (2) | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L157-L165] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L301-L349] |
| D-03 / G0 | For plan records explicitly stating 5 years before cessation, normalize to months and compare with `lead_time_months`: 0 inconsistent records | FAIL: 2 inconsistent records; issue pending (3) | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L313-L325] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L416-L428] |
| D-04 / G0 | Supply 12 duplicate rows for one year/month with zero oil: contribution <=1 calendar month | FAIL: `months_idle=12`; issue pending (4) | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L100-L109] |
| D-05 / G0 | Price 1 mapped facility with missing depth: 0 rows silently replacing unknown depth with 0 m | FAIL: 1 modeled row with assigned 0.0 m; issue pending (5) | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L102-L115] |
| D-06 / G0 | Complete all applicable `jacket` categories, omit mooring: 0 gaps from zero-weight categories | FAIL: 1 mooring gap; issue pending (5) | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L77-L94] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L144-L156] |
| D-07 / G0 | `estimate('jacket',-1000,-1000)`: 0 negative MUSD estimates accepted from invalid depth/weight | FAIL: negative cost accepted; issue pending (5) | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L137-L159] |

Check inventory: G0 has 9 checks, G1 has 1, G2 has 3, G3 and G4 have 0 applicable checks, G5 has 1; total 14. No check is added for the four silent failures tracked by #1281: NaN availability, unknown regulatory keys, unassigned calibration rows and missing production months. Their section-6 rows state "no detection check exists"; passing G1 tests do not establish their absence.

## 6. Known failure modes and pitfalls

The incident leads are feature requests rather than confirmed incident reports; the confirmed code findings and their detection recipes follow, with silent substitutions first. [docs/plans/2026-05-18-issue-424-decommissioning-market-outlook.md:L49-L80]

| Symptom / cause | Detection and limitation | Reference / recorded date | Evidence |
| --- | --- | --- | --- |
| SF1: NaN availability scores 1.0; five NaN categories give overall 1.0, low risk and 0 gaps, unlike missing keys | no detection check exists; reject or identify non-finite availability before interpreting completeness | #1281; 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L63-L74] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L92-L103] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L144-L168] |
| SF2: absent regulatory keys silently return 0 months or []; `decommissioning_plan` misses UKCS `decommissioning_programme`, and cost region `west_africa` has no regulatory rows | no detection check exists; current-behavior pins: `tests/unit/decommissioning/test_regulations.py::test_get_lead_time_unknown_returns_zero` and `tests/unit/decommissioning/test_regulations.py::test_get_regulations_unknown_region_returns_empty` assert the defaults, not absence of obligations | #1281; 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L45-L74] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L186-L198] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L64-L69] [tests/unit/decommissioning/test_regulations.py:L96-L98] [tests/unit/decommissioning/test_regulations.py:L123-L125] |
| SF3: calibration silently ignores `spar`, `tlp`, `Jacket` and ` jacket` rows outside five exact strings, but includes them in `total_records`; `coverage_pct` measures types, not used rows | no detection check exists; compare summed fit `n_records` with `total_records` before treating the input count as calibrated coverage | #1281; 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L22-L28] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L149-L186] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L134-L145] |
| SF4: a final NaN `oil_bbl` interrupts trailing idle rows, gives `months_idle=0` and removes the idle trigger; current rate is NaN and cessation returns the latest data year when the decline guard permits projection; decline means skip NaN without a count | no detection check exists; distinguish missing months from production and verify finite inputs before interpreting an idle or cessation result | #1281; 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L74-L84] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L100-L109] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L130-L150] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L196-L219] |
| Missing facility depth is priced as zero; unknown regions/assets are excluded | D-05; R6 checks exclusion counts, not missing-depth quality | issue pending (5); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L93-L115] |
| Facility pricing always supplies weight 0.0 and maps US facilities outside the GoM to the GoM multiplier; priced rows expose neither assumption | no detection check exists; at 100 m a 10,000 t jacket costs 3.0 MUSD by the formula versus 2.5 MUSD with weight omitted, 16.7 % lower | issue pending (5); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L60-L66] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L102-L115] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L18-L23] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L153-L166] |
| Empty production returns an unflagged zero-valued assessment; insufficient old history gives zero decline | no detection check exists for a missing-data status; G0 preflight must distinguish absence from a stable series | issue pending (5); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L74-L81] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L183-L194] |
| Pipeline length is documented but contributes no cost | D-01; existing test only checks positive output | issue pending (1); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L42-L47] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L153-L159] [tests/unit/decommissioning/test_cost_model.py:L49-L51] |
| Calibration reports the unconstrained fit's error while applying only the blended intercept | D-02; do not use reported RMSE as an independent reference for calibrated estimates | issue pending (2); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L157-L165] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L327-L349] |
| Calibration fits with fewer than 3 records and the empty-input fallback report uncomputed RMSE and R-squared as 0.0 | no detection check exists; `data_driven=False` distinguishes fallback diagnostics from a computed perfect fit; D-02 checks a different diagnostic mismatch | issue pending (2); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L289-L299] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L354-L373] |
| Regulatory plan fields disagree internally; source strings lack an explicit CFR edition | D-03 detects internal contradiction only; no detection check exists for external legal accuracy | issue pending (3); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L25-L35] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L313-L325] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/_regulations_data.py:L416-L428] |
| Idle count counts rows, including duplicate or discontinuous months | D-04; the idle fixture itself repeats month numbers, and its count assertion only requires >=12 | issue pending (4); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L100-L109] [tests/unit/decommissioning/test_late_life.py:L75-L84] [tests/unit/decommissioning/test_late_life.py:L167-L170] |
| Cessation returns latest year plus at most 50 iterations even if the threshold is not reached | Check final projected rate is <=10.0 bbl/day before treating a year as cessation; no detection check exists for a capped projection | issue pending (4); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L135-L150] |
| Negative numeric inputs can yield negative costs; fixed-asset mooring can remain a gap despite zero weight | D-07 and D-06; categorical-key tests do not validate these numeric and applicability conditions | issue pending (5); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L137-L159] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L77-L94] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L144-L156] |
| Code comments use inconsistent currency conversion descriptions for per-tonne coefficients | Compare comment dollars/tonne with coefficient times one million dollars/MUSD: 0 unit inconsistencies required; no detection check exists | issue pending (7); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L18-L33] |
| `estimate` returns the supplied `year` without escalating cost; a future year retains the factor-year cost basis | no detection check exists; establish the factor-year basis and apply any escalation separately before using future-year estimates | issue pending (7); 2026-10-15 | [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L109-L126] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L148-L170] |

Read-only issue references: #424 concerns forecasting assumptions, #770 and #777 concern consumers, and #960 concerns per-field well attribution; none is adopted as evidence that the cost coefficients or regulatory clauses are validated. Public issue bodies, read 2026-10-15, #424, #770, #777 and #960; forecasting scope is also recorded in [docs/plans/2026-05-18-issue-424-decommissioning-market-outlook.md:L49-L80]

For #424, do not equate the module's field cessation heuristic with the separate report's drawdown forecast; for #770/#777, trace delegated pricing before using a page; for #960, facility removal is not well plugging; the consumer states the distinction explicitly. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L112-L150] [reports/gtm/decommissioning_market_outlook.py:L154-L232] [scripts/decommissioning/build_pa_liability_wave.py:L86-L96] [src/worldenergydata/field_development/decommission_risk.py:L22-L32]

## 7. Lessons log

Append-only record; subsequent changes should retain earlier rows, use public change references and link independent review evidence (Module agent lifecycle, revision 0, sections 3 and 4).

| Date | Change reference | Lesson / evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial draft | Preserve the distinction between model self-consistency and empirical validation; range and positivity assertions alone do not establish a benchmark. [tests/unit/decommissioning/test_cost_model.py:L117-L133] | Regression classification and coefficient-provenance limitation | Not assigned; issue pending (7) |

## 8. Ownership

Review contract: calculations quality manager, with a calculations deputy role requiring assignment; producing role: module maintainer; escalation: unresolved method, tolerance, edition or data questions go to the quality manager, with cross-family questions routed to the maintainers (AQG r0, sections 10–11; Module agent lifecycle, revision 0, section 4, escalation).

No clearance or deputy appointment is recorded here; keep DRAFT until independent review and the open-item issue references are resolved (Module agent lifecycle, revision 0, sections 3–4; issue pending (7)).

## 9. Dependencies and implementation inventory

### Dependencies and consumers

The package metadata declares `worldenergydata-core`, NumPy and pandas; calibration uses NumPy least squares, and the screening, scoring and serialization routes operate on pandas DataFrames. [packages/worldenergydata-decommissioning/pyproject.toml:L24-L33] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L301-L332] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L196-L203] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L170-L208] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L77-L96]

The regional report delegates to `price_portfolio`; the P&A page uses the estimator for reference costs and multiplies its output by borehole counts; the risk badge serializes an existing priced facility row. [scripts/decommissioning/build_regional_liability.py:L92-L118] [scripts/decommissioning/build_pa_liability_wave.py:L86-L96] [scripts/decommissioning/build_pa_liability_wave.py:L115-L143] [src/worldenergydata/field_development/decommission_risk.py:L25-L50]

No external solver version is required by the listed scalar calculations; data-refresh, report publishing and solver-based removal engineering are outside this package review. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L148-L170] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L301-L352] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L196-L233] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L144-L168]

### Map inventory and counted search

Read record: `digitalmodel` implementation map, `docs/registry/implementation-map.yaml`, ref `origin/codex/implmap-work`, map commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, declared data/code revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`; schema 1, 13 families.

Inventory result: **0** implementation rows inside the header package; **0** map families and **0** counted families, so the required inventory is empty and the counted search is **NOT_APPLICABLE** for lack of in-package map rows. No case-insensitive package-path signal exclusion is needed because the counted set is empty.

Map follow-up: add the section-3 families before counting them at a later map revision: parametric decommissioning cost, removal-cost calibration, production-decline and idle screening, documentation completeness, facility-liability aggregation, and regulatory-record query/serialization; issue pending (9). The implementations to index are those listed in section 3. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L109-L218] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L119-L208] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L50-L150] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L63-L168] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L53-L144] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L45-L96]

### Additional whole-repository search

Read record at the code pin: `git grep -n -E` over every tracked `*.py` path, including scripts, using `DecommissioningCostEstimator|CostModelCalibration|LateLifeIdentifier|DataCompletenessScorer|price_portfolio|estimated_cost_musd|pa_unit_cost|build_field_decom_liability|_compute_consecutive_idle_months`; 127 hits in 17 files, assigned with Python AST to their smallest enclosing function/class, or module scope. This supplementary search does not alter the empty-map acceptance result.

| Outside-package definition | Classification / map follow-up | Evidence |
| --- | --- | --- |
| `build_regional_liability.main` | Delegates pricing and exports results; helper | [scripts/decommissioning/build_regional_liability.py:L92-L123] |
| `build_pa_liability_wave.main` | Delegates unit pricing; also computes its own count-times-unit-cost liability aggregation, an outside-package map gap for that result | [scripts/decommissioning/build_pa_liability_wave.py:L86-L96] [scripts/decommissioning/build_pa_liability_wave.py:L115-L143] |
| `decommissioning_market_outlook.build_forecast` | Independent drawdown and blended-cost forecast, outside-package map gap; not the field-screening method | [reports/gtm/decommissioning_market_outlook.py:L154-L232] |
| `field_decom.build_field_decom_liability` | Independent aggregation of upstream cost-band data, outside-package map gap; not parametric cost estimation | [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/field_decom.py:L255-L306] |
| `decommission_risk.classify_decommissioning` | Existing result lookup and badge serialization, helper | [src/worldenergydata/field_development/decommission_risk.py:L25-L50] |

In-package delegation paths include `estimate_campaign`, aggregate cost helpers, `screen_portfolio`, `late_life_fields`, `portfolio_scores`, and regulatory summary serialization; the independently computing routes are explicitly inventoried in section 3. [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_model.py:L173-L218] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/late_life.py:L235-L262] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/data_completeness.py:L170-L208] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/regulations.py:L77-L96]

## 10. Coverage and open items

### Read and discovery record

Code read: all 9 package Python files, including the complete regulatory dataset and both private regulatory modules; the package README and metadata; all 6 module test files and their test-package initializer. The main-path methods and tests are cited in sections 1–6; no package-local tests directory was found in the pinned tree.

Documentation discovery searched `docs/` for case-insensitive `decommission`; 20 Markdown files and 1 YAML file matched. The reference-bearing portions were read; this pack covers the package main path rather than certifying unrelated topics in those documents. Complete assessment of those wider topics remains under issue pending (7).

| Discovery document | Reference-bearing lines read |
| --- | --- |
| Package README | [packages/worldenergydata-decommissioning/README.md:L1-L8] |
| Forecast plan | [docs/plans/2026-05-18-issue-424-decommissioning-market-outlook.md:L1-L132] |
| Repository architecture | [docs/modules/repository-architecture.md:L230-L240] |
| Infrastructure bundle contract | [docs/data-sources/bsee/data/field_infrastructure_bundle_contract.md:L1-L8] |
| Capability-index reconciliation plan | [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L12-L21] |
| Local development-source guide | [docs/data-sources/bsee/data/local_field_development_sources.md:L71-L83] |
| Plan index | [docs/plans/README.md:L65-L75] |
| Package split design | [docs/adr/0001-domain-package-split.md:L43-L49] [docs/adr/0001-domain-package-split.md:L83-L89] |
| Capability inventory plan | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L15-L26] |
| Raw-data guide | [docs/knowledge-base/bsee/data-sources/raw-data-downloads.md:L96-L102] [docs/knowledge-base/bsee/data-sources/raw-data-downloads.md:L126-L134] |
| Readiness audit, Markdown and YAML | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L76-L95]; [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.yaml:L730-L739] |
| Data-source index | [docs/knowledge-base/bsee/data-sources/index.md:L127-L135] |
| Completeness audit | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L71-L79] |
| Update schedule | [docs/knowledge-base/bsee/data-sources/update-schedule.md:L98-L105] |
| Cross-region tutorial | [docs/modules/data_sodir/cross_regional_tutorial.md:L237-L246] |
| Data-dictionary index | [docs/knowledge-base/bsee/data-dictionaries/index.md:L76-L82] |
| Maritime source catalog | [docs/data-sources/INDUSTRIAL_MARITIME_DATA_SOURCES.md:L699-L706] |
| Regional source guide | [docs/knowledge-base/bsee/regions/pacific.md:L10-L28] |
| Production retrieval guide | [docs/modules/bsee/PRODUCTION_DATA_RETRIEVAL_GUIDE.md:L344-L356] |
| Platform query guide | [docs/knowledge-base/bsee/query-interfaces/platform-query.md:L303-L320] |
| 1 discovery file with identifying names | Path and identities withheld; codenaming follow-up: issue pending (6) |

The historical readiness audit's test-file count is a historical claim, not the current count; the six test files identified in the execution record supersede it for this pack. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L83-L83]

### Execution record

| Run | Code revision | Run / passed / failed / skipped / NOT_RUN |
| --- | --- | --- |
| BASE, before editing | `285d65c40896b17ccf44568e59f5b789d59c943e` | 133 / 133 / 0 / 0 / 0 |
| AFTER, documentation changes only | Same code pin; uncommitted documentation tree | 133 / 133 / 0 / 0 / 0 |

Command form: `uv run --extra test python -m pytest tests/unit/decommissioning -q -rA -p no:cacheprovider --basetemp=<scratch> --allow-existing-tree-changes --cov-report= --cov-report=term --cov-report=json:<scratch> --junitxml=<scratch>`; `COVERAGE_FILE` points to scratch, and the configured pytest options remain active. The ordinary source-resolution form was used; no `--no-sources`, `--noconftest`, deselection or addopts override was used.

Test-file run counts: cost model 25; calibration 26; completeness 23; facility liability 14; late life 19; regulations 26. These are execution counts, not an independent numerical validation claim.

The scratch review evidence retains the input SHA-256 values, full pytest node outcomes, citation resolution and defect recipes. No licensed solver was imported or invoked.

### Documentation correction checks

The correction is documentation only. BASE `05d32a46cdd92931f11fd4008f939570b7e9b87f` and the uncommitted AFTER tree each ran all 133 module tests: 133 passed, 0 failed, 0 skipped and 0 NOT_RUN. Per-file counts remain 25, 26, 23, 14, 19 and 26 in the order above. The seven section-4 nodes are included. No test assertion or runtime code changed.

Command form for both runs: `uv run --no-project --with pytest --with 'numpy>=2.2.6,<3' --with 'pandas>=2.3.3,<3' --with pytest-cov --with pytest-asyncio --with psutil --with plotly --with pydantic-settings python -m pytest tests/unit/decommissioning -q -rA -p no:cacheprovider --basetemp=<scratch> --cov-report= --cov-report=term --junitxml=<scratch>`; AFTER also uses `--allow-existing-tree-changes` to check preservation of the documentation edit. `PYTHONPATH` supplies the root, core and decommissioning source directories; `COVERAGE_FILE` points to scratch. Coverage, JUnit, performance records and logs remain outside the repository. The configured test hooks and coverage measurement remain active.

The failure inventory increases from 9 to 16 rows: SF1–SF4 under #1281, plus facility pricing assumptions, uncomputed calibration diagnostics and absent year escalation. The check inventory remains 14 and the open-item register remains 10 groups; groups 2–5 now also reference #1281. These are documented limitations, not corrected runtime defects.

Citation self-check: 36 citation occurrences on edited lines were checked against the header pin for matching source content and line spans. All 233 citation occurrences resolve in 42 files (172 distinct citations); BASE had 207 occurrences, 159 distinct citations and the same 42 files. The four UNVERIFIED claims, seven regression cases and empty implementation-map inventory are unchanged. All 16 package/test Python files match the code pin byte for byte.

### Open-item register

Each row is assigned to the module maintainer for triage; method, tolerance and edition dispositions require calculations quality-manager review (Module agent lifecycle, revision 0, section 4, escalation).

| Item | Known limit / required action | Issue reference |
| --- | --- | --- |
| 1 | Resolve pipeline length scaling and overloaded input units; D-01 | issue pending (1) |
| 2 | Align calibration diagnostics and the deployed factor set, distinguish uncomputed diagnostics, and report unassigned input rows; D-02, SF3 | issue pending (2); #1281 |
| 3 | Resolve contradictory regulatory fields, confirm sources/editions/clauses, and assess citation-sidecar coverage; D-03, SF2; UNVERIFIED claims in section 3; distinguish unknown lookup keys from absent obligations | issue pending (3); #1281 |
| 4 | Validate calendar continuity, duplicate rows, lookback basis and cessation-cap handling, and missing production months; D-04, SF4 | issue pending (4); #1281 |
| 5 | Add explicit quality states for missing histories/depth and numeric validation; decide zero-weight category gap behavior; flag weight-free pricing and US-to-GoM mapping; handle NaN availability; D-05 to D-07, SF1 | issue pending (5); #1281 |
| 6 | Codename 1 discovery file with identifying names and replace identifying synthetic labels before public reuse | issue pending (6). [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/cost_calibration.py:L229-L233] [packages/worldenergydata-decommissioning/src/worldenergydata/decommissioning/facility_liability.py:L105-L115] |
| 7 | Independent cost/cessation/score benchmarks, unit-comment correction, factor-year basis and absent escalation, signed QA appendix, deputy/shared-log assignment and wider-document assessment; UNVERIFIED benchmark basis in section 3 | issue pending (7) |
| 8 | Confirm documentation exclusion from build artifacts without expanding this documentation change into packaging changes | issue pending (8) |
| 9 | Add section-3 method families and outside-package computations to the implementation map before they become counted families | issue pending (9) |
| 10 | Preserve distinction between per-field facility removal and unattributed well plugging; downstream attribution remains outside this package | Existing #960; consumer distinction. [src/worldenergydata/field_development/decommission_risk.py:L22-L32] |

UNVERIFIED: Exclusion of the pack from built wheels has not been established; the existing package-data pattern includes `**/*.md`, and no package-data rule is changed here; issue pending (8). [packages/worldenergydata-decommissioning/pyproject.toml:L49-L55]

Review handoff: replace draft references with opened issue numbers and obtain independent clearance before changing the header status; `docs/registry/workflows.yaml` exists at the pin, but no module routing entry exists (Module agent lifecycle, revision 0, section 2).
