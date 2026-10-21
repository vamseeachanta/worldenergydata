# Lower Tertiary module knowledge pack

| Header | Value |
| --- | --- |
| Module | bsee:lower_tertiary |
| Repository | worldenergydata |
| Path | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary |
| Pack revision | 1, 2026-10-15 |
| Code revision | 285d65c40896b17ccf44568e59f5b789d59c943e |
| Analysis family | EC; data pipelines and calculations |
| Quality manager role | Calculations quality manager |
| Status | DRAFT |

## 1. Purpose and scope

The production path normalizes yearly OGOR-A records, maps leases to developments, aggregates monthly oil and applies a first-oil window. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L116-L200] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L203-L232] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L303-L344]

The package also provides monthly oil/gas financial calculations, historical cashflow reproduction, well benchmarking, drilling-intensity comparisons and portfolio reporting. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L133-L226] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L566-L597] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:L345-L434] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py:L41-L107] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L1-L18]

Portfolio economics uses a plateau followed by a declared decline curve; it does not aggregate observed OGOR production for its cashflow basis. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L16-L19] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L124-L159]

Observed-production analysis verifies retained filing digests, coverage and identity before computing a pre-tax assumption scenario; its horizon ends at observed production rather than a reserves forecast. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L15-L78] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L81-L129]

The scope is this package, including its helper modules; physical design, equipment response and environmental loading are outside the observed-production calculation. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L187-L205]

### Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-15 | Initial module scope, methods, evidence and limitations |
| 1 | 2026-10-15 | Correct the discount-rate citation; identify absent-data groups, silent defaults, public-record checks and the parallel implementation so evidence and limits are explicit |

## 2. Inputs and outputs

### Inputs

| Interface / input | Unit and convention | Range / default | Source and citation |
| --- | --- | --- | --- |
| `load_lease_mapping` | Lease identifier; stripped and uppercased | Empty mappings become empty dictionaries | YAML mapping; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L16-L50] |
| `load_field_inputs` | `first_oil`, `data_through`: timestamps; `capex.total_mm_usd`: USD million | Status filter optional; missing first-oil resolves to 1970-01-01 | Field YAML directory and lease mapping; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L53-L130] |
| `calculate_monthly_financials` | `oil_bbl`: bbl/month; `gas_mcf`: Mcf/month; oil price USD/bbl; gas price USD/Mcf; opex USD/boe; rates dimensionless | Empty input returns unchanged; missing volume columns use zero | Monthly DataFrame and economic configuration; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L133-L170] |
| `summarize_field_financials` | `date`: month timestamp; cashflow USD/month; annual effective discount fraction | Empty input raises; missing cashflow is zero; missing capex is zero | Monthly financials, profile and economic configuration; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L173-L226] |
| `load_ogor_production` | `PRODUCTION_DATE`: YYYYMM; `MON_O_PROD_VOL`: bbl/month | Years 2000–2025 by default; malformed oil becomes zero; absent archives skipped | Yearly ZIP records; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L116-L200] |
| `classify_production` | Oil bbl/month; string `PRODUCT_CODE`, `WELL_STAT_CD`; timestamp `date` | Optional first-oil mapping; default grouping key `development` | Record-level DataFrame; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/production_classifier.py:L19-L81] |
| `compute_learning` | `drill_days`: days; `MAX_WELL_BORE_TVD`: ft; spud timestamps | At least 4 dated wells per group; threshold 10.0 percent | Cleaned drilling DataFrame; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py:L21-L67] |
| `analyze_field` | Capex USD million; plateau thousand bbl/day; annual decline fraction | Positive capex and plateau required; default horizon 20 years, plateau 3 years | Field YAML and keyword overrides; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L46-L54] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L220-L257] |
| `load_extended_wti_prices` | `Month`: month-start timestamp; `WTI_USD`: USD/bbl | Default through 2025-10-01; workbook values precede extension sources | Workbook, snapshot, remote sources, then flat-forward; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/wti_prices.py:L192-L270] |
| `load_verified` | Oil bbl, gas Mcf, water bbl; raw record identities and digest manifest | Complete declared years and consecutive observed months required | Dataset directory with basis and sources JSON; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L15-L78] |

No spatial coordinate frame or phase convention participates in the monthly financial equations; the discount origin is the configured first-oil month, and project capex is subtracted at that origin. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L133-L226]

### Outputs

| Interface / output | Unit and convention | Behaviour and citation |
| --- | --- | --- |
| `calculate_monthly_financials` DataFrame | Revenue, royalty, opex, tax, operating income and cashflow in USD/month; `boe` in boe/month | Returns a copy; income tax is charged only on positive operating income; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L140-L170] |
| `summarize_field_financials` dictionary | Oil MMbbl; BOE MMboe; money USD million; `Months` rows; PI dimensionless | `NPV Project` = discounted operating cashflow less total capex; gas output has a known conversion defect in section 6; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L186-L226] |
| `reproduce_v30_production` dictionary | Oil bbl; producing-month count; first/last timestamps; monthly oil frame | Excludes zero-oil months and pre-first-oil records; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L328-L344] |
| `classify_production` / `summarize_classification` | Class strings, class counts and oil bbl | Copies records, removes working columns and groups totals; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/production_classifier.py:L43-L108] |
| `FieldEconomicsResult` | NPV/capex USD million; annual rates dimensionless; payback years; breakeven USD/bbl | Contains sensitivities, citations and explicit cashflow basis; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L62-L77] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L363-L386] |
| Portfolio renderers | CSV / UTF-8 HTML | Summary CSV flattens sensitivity prices; HTML includes input citations; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L443-L514] |
| Well benchmark table | Cumulative oil MMbbl; revenue USD million; uptime percent; durations days | Missing-data and partial-price flags retained; `drilling_days` aliases calendar cycle time; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:L254-L342] |

## 3. Method and governing standards

| Method | Implementing definition and computational basis | Reference status |
| --- | --- | --- |
| Monthly financials | Revenue = oil × oil price + gas × gas price; BOE = oil + gas / 6; royalty = revenue × rate; opex = BOE × unit cost; tax = max(operating income, 0) × tax rate; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L145-L168] | Code convention; independent physical energy equivalence is not established here |
| Monthly discounting | Monthly effective rate = `(1 + annual_rate) ** (1/12) - 1`; elapsed months measured from first oil; present cashflow summed and capex subtracted; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L179-L210] | Code algorithm, distinct from the historical reproduction origin |
| Historical NPV and MIRR | Cashflows trimmed to first/last entries above 1e-6 USD magnitude, NPV discounted from the first retained entry; MIRR uses monthly compounding and annualizes by twelfth power; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L273-L287] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L751-L768] | Workbook reproduction; equality to its golden outputs is regression evidence |
| Production classification | Test-product code has highest priority, then exploratory status / first-oil rules, with commercial/non-producing defaults from oil volume; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/production_classifier.py:L43-L81] | Repository rules; negative oil also follows the non-producing default |
| Drilling learning | Sort wells by spud, split at `n // 2`, compare median days per 1,000 ft TVD between halves; strict deltas below -10.0 or above +10.0 percent classify change; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py:L24-L67] | Repository heuristic; no external calibration claimed |
| Portfolio production and cashflow | Annual plateau = thousand bbl/day × 365 / 1,000 MMbbl; post-plateau production multiplied by `(1 - annual_decline) ** decline_years`; inception capital negative, subsequent net oil receipts positive before tax; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L124-L159] | Scenario calculation; leap years ignored |
| Breakeven | Bisection calls `EconomicsQuery.npv`, returning a bounded price or `None`; stopping residual 0.01 USD million and 64 iterations; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L162-L198] | Numerical root criterion is an NPV tolerance, not a price tolerance |
| Input integrity | SHA-256 equality, record counts, publisher URL prefix, declared units and year coverage are checked before aggregation; [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L50-L78] | Traceability check, not independent validation of economic assumptions |

The portfolio citations name a federal offshore regulation and a price outlook, but these are emitted attribution strings rather than verified applicability or regulatory advice; the comprehensive report labels generic defaults and unsourced inputs as assumptions. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L298-L359] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L138-L168]

No licensed-standard clause is used as a checked engineering reference in this pack; formula descriptions above are bounded to the cited implementations. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L133-L226] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py:L21-L107] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L124-L198]

## 4. Validated worked examples

### Analytical validation

| Case | Independent expected value / input | Tolerance and basis | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| V1: synthetic oil revenue | Closed-form multiplication outside the implementation: 10,000 bbl × 75.0 USD/bbl = 750,000.0 USD; inline synthetic DataFrame | `pytest.approx` relative 1e-6, absolute 1e-12 USD; floating-point arithmetic check | `tests/unit/lower_tertiary/test_npv.py::TestCalculateMonthlyFinancials::test_basic` | PASS at code pin; [tests/unit/lower_tertiary/test_npv.py:L222-L248] |

This example validates one arithmetic output, without qualifying prices, tax applicability, production forecasts or investment value. [tests/unit/lower_tertiary/test_npv.py:L222-L248]

### Regression examples

| Case | Input / expected result | Criterion | Existing test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1: classification priority | Inline 100 bbl record with test-product code → `well_test` | Exact class equality; 0 misclassified records | `tests/unit/lower_tertiary/test_production_classifier.py::TestClassifyProductionRule1::test_product_code_t_is_well_test` | PASS at code pin; [tests/unit/lower_tertiary/test_production_classifier.py:L45-L49] |
| R2: learning heuristic | Inline 12-well synthetic frame, 4 wells per group → 1 group in each verdict | Exact dictionary equality; 0 differing counts | `tests/unit/lower_tertiary/test_drilling_learning.py::test_learn_stepout_flat_verdicts` | PASS at code pin; [tests/unit/lower_tertiary/test_drilling_learning.py:L40-L53] |
| R3: reproducible observed-production build | Fixture dataset selected by the test; two builds of HTML, results JSON and manifest → identical bytes and matching output digests | 0 differing bytes and 0 digest mismatches | `tests/unit/lower_tertiary/test_life_to_date.py::test_build_twice_identical_with_valid_output_digests` | PASS at code pin; identifying fixture path withheld, issue pending (3); [tests/unit/lower_tertiary/test_life_to_date.py:L173-L188] |
| R4: snapshot provenance replay | Committed snapshot and its recorded metadata → exact reproduced sidecar | 0 differing characters | `tests/unit/lower_tertiary/test_wti_prices.py::TestProvenance::test_emitter_reproduces_committed_sidecar` | PASS at code pin; [tests/unit/lower_tertiary/test_wti_prices.py:L376-L382] |

The golden-baseline comparisons are regression checks; their expected outputs come from the retained baseline, and data-dependent cases explicitly skip when production files are absent. [tests/unit/lower_tertiary/test_repeatability_v30.py:L39-L84] [tests/unit/lower_tertiary/test_v30_benchmarks.py:L65-L90]

## 5. QA gates

Gate selection: AQG r0, section 10, Python calculations; G5 also applies under section 9 of that standard.

| Gate | Applicability | Module-specific check | Numeric pass criterion and unit | Evidence |
| --- | --- | --- | --- | --- |
| G0 | Applicable: inputs, units and provenance | C0a: corrupt one byte in a copied retained input, then call `load_verified` | 1 `ValueError` matching digest; 0 accepted corrupt inputs | `tests/unit/lower_tertiary/test_life_to_date.py::test_corrupt_raw_bytes_fail_closed`; [tests/unit/lower_tertiary/test_life_to_date.py:L44-L48] |
| G0 | Applicable | C0b: remove one declared source year before `load_verified` | 1 coverage exception; 0 accepted incomplete datasets | `tests/unit/lower_tertiary/test_life_to_date.py::test_missing_year_fails_closed`; [tests/unit/lower_tertiary/test_life_to_date.py:L51-L59] |
| G0 | Applicable: configuration provenance | C0c: compare three configured records through YAML and `load_field_inputs`; reject a reverted first-oil date through both readers | 0 value or source-marker mismatches in 3 records; 1 rejected reversion per reader (2 readers); not an audit of every field | `tests/unit/lower_tertiary/test_field_public_record_747.py::test_public_record_corrections` and `tests/unit/lower_tertiary/test_field_public_record_747.py::test_reverted_first_oil_is_rejected`; [tests/unit/lower_tertiary/test_field_public_record_747.py:L11-L64] |
| G1 | Applicable: Python imports and offline tests | C1: import the module through the full discovered module test suite | 0 failed tests and 0 collection errors, counts in tests; absent-data cases disclosed separately | Test receipt below; package exports [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/__init__.py:L6-L18] |
| G2 | Applicable: independent arithmetic | C2: `calculate_monthly_financials`, V1 closed-form revenue comparison | Relative error ≤ 1e-6, unit 1; expected 750,000.0 USD | V1 node; [tests/unit/lower_tertiary/test_npv.py:L222-L248] |
| G3 | NOT_APPLICABLE: no time-domain mechanical simulation in the monthly calculation | None | Not applicable | Calculation surface [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L131-L226]; AQG r0, section 10 |
| G4 | NOT_APPLICABLE: no diffraction body or mesh in the monthly calculation | None | Not applicable | Calculation surface [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L131-L226]; AQG r0, section 10 |
| G5 | Applicable: retained evidence and reproducibility | C5a: `build` twice and check every emitted output digest | 0 differing bytes; 0 SHA-256 mismatches | R3 node; [tests/unit/lower_tertiary/test_life_to_date.py:L173-L188] |
| G5 | Applicable | C5b: render comprehensive text outputs and validate manifest inputs and outputs | 0 digest mismatches, count in files | `tests/integration/reporting/test_comprehensive_delivery.py::test_manifest_matches_files_and_inputs`; [tests/integration/reporting/test_comprehensive_delivery.py:L113-L132] |

These are executable evidence checks, not a signed release clearance; the comprehensive report validates citation presence and roster consistency before rendering. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L110-L129]

### Offline execution receipt

Code pin: `285d65c40896b17ccf44568e59f5b789d59c943e`; BASE: `1d59b3f6ee29e40f08ea4be17a0fa0f1a878a167`. Local checks use workspace sources through `PYTHONPATH`, declared test dependencies and calculation / I/O dependencies installed as wheels, with configured addopts retained. Coverage, performance and temporary outputs are directed to scratch. AFTER results are recorded on the uncommitted documentation tree with the existing `--allow-existing-tree-changes` option, retaining the tree-preservation guard.

| Command, generic form | BASE passed / failed / skipped | AFTER passed / failed / skipped | Total nodes | Not exercised / other skips |
| --- | --- | --- | --- | --- |
| `uv run --no-project --with pytest <test dependencies> python -m pytest tests/unit/lower_tertiary -q -rA -p no:cacheprovider --basetemp=<scratch> <coverage destinations>` | 470 / 0 / 138 | 470 / 0 / 138 | 608 | 137 SKIPPED; not exercised: BSEE OGOR-A production data absent; 1 stale-output case |
| `uv run --no-project --with pytest <test dependencies> python -m pytest <reporting-integration files> <determinism file> tests/contracts -q -rA -p no:cacheprovider --basetemp=<scratch> <coverage destinations>` | 107 / 0 / 0 | 107 / 0 / 0 | 107 | 0 |

BASE and AFTER JUnit receipts retain every node ID and skip reason: 470 passed, 0 failed, 138 skipped in each module run and 107 passed in each additional run; skip classifications are unchanged. Identifying node IDs are retained with the evidence rather than copied into this public pack.

The additional paths are `tests/integration/reporting/test_lt_comprehensive.py`, `tests/integration/reporting/test_comprehensive_delivery.py` and `tests/unit/fdas/validation/test_v30_determinism.py`; no routing-registry contract exists to exercise, so the existing `tests/contracts` domain was run.

The 137 absent-data cases are SKIPPED; not exercised, not successful production reproduction. The groups below are disjoint and counted from both BASE and AFTER JUnit receipts.

| Cases | Classification and named data | Evidence |
| --- | --- | --- |
| 117: 22 extended-production, 10 repeatability, 85 financial-benchmark cases | SKIPPED; not exercised: BSEE OGOR-A yearly archives `ogora<year>delimit.zip` absent under the BSEE data root `zip/historical_production_yearly` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L144-L154] [tests/unit/lower_tertiary/test_extended_production.py:L72-L84] [tests/unit/lower_tertiary/test_repeatability_v30.py:L44-L54] [tests/unit/lower_tertiary/test_v30_benchmarks.py:L75-L85] |
| 8: later-baseline cases | SKIPPED; not exercised: BSEE OGOR-A `.bin` production files absent under `bin/historical_production_yearly` | [tests/unit/lower_tertiary/test_v50_baseline.py:L98-L133] |
| 12: 6 well-benchmark and 6 well-NPV cases | SKIPPED; not exercised: BSEE OGOR-A yearly ZIP archives and `.bin` fallback absent; `WED_DATA_ROOT` selects the BSEE data root | [tests/unit/lower_tertiary/test_well_benchmark.py:L32-L43] [tests/unit/lower_tertiary/test_well_npv_stackup.py:L20-L37] |
| 0: V30 workbook cases | No absent-workbook skips: `leases.xlsx`, `lease_assumptions.xlsx`, `wti_monthly.xlsx` and `drilling_and_completion_days.xlsx` are present in `docs/modules/bsee/analysis/production/FDAS_V30/` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L23-L24] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L32-L49] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L81-L112] |
| 0: report-generator import failures | Counted separately from absent data: the broad exception guard could hide a broken import, but no skip with this reason occurred | [tests/unit/lower_tertiary/test_well_npv_stackup.py:L25-L29] |

One additional existing skip checks the committed benchmark column only after its regeneration; it is a stale-output limitation under #1077, not a missing dependency. Thus 470 executed and passed + 137 not exercised for absent data + 1 stale-output skip = 608 module nodes; all 107 additional nodes executed and passed. [tests/unit/lower_tertiary/test_well_benchmark.py:L210-L224]

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom / cause | Detection check or gap | Tracking / date | Evidence |
| --- | --- | --- | --- |
| Missing OGOR years are skipped by the ZIP loader; malformed oil is coerced to zero | C0b protects the separate retained-input route; no detection check exists for completeness of the general ZIP route | Issue pending (3), 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L144-L184] |
| Configured first-oil dates affect the discount origin; #747 reports historical public-record discrepancies, including a date about 9 years late, and operator discrepancies. The pin already contains a limited correction and regression check | C0c checks 3 records and rejects a reverted date; no detection check exists auditing every configuration date against the public record | #747 (open), 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L100-L103] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L175-L186] [tests/unit/lower_tertiary/test_field_public_record_747.py:L11-L64] |
| Missing first oil silently resolves to 1970-01-01, so later cashflows are discounted from January 1970 without warning; missing `capex.total_mm_usd` silently becomes 0.0, making project NPV equal operating NPV and PI 0.0 | No detection check exists rejecting either silent default; C2 verifies revenue arithmetic only | #1269 (open), 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L54-L59] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L175-L192] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L203-L207] |
| Missing WTI observations fall through to a fixed historical constant; early workbook return does not cap the requested month | Inspect output maximum month and fallback source counts; no detection check exists enforcing the intended capped-date / latest-observation contract | #1191, 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/wti_prices.py:L199-L206] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/wti_prices.py:L240-L266] |
| HSE placeholder carries a zero incident count; absence of observations must remain visible | Reporting test requires all placeholder counts to become unknown; 0 retained numeric placeholders in `report_hse` | #366, 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py:L334-L354] [tests/integration/reporting/test_comprehensive_delivery.py:L99-L102] |
| Cost comparison calls the disclosure query with an empty revision view and catches failures | Inspect `benchmark_status` and caveats; no detection check exists establishing live disclosure coverage | #343, #344, 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py:L388-L425] |
| `Gas (BCF)` in `summarize_field_financials` divides `gas_mcf` by 1e9 instead of 1e6; the observed-production path converts separately | No detection check exists for the summary gas key; `test_monthly_mass_balance_and_gas_units` covers the separate observed-production result only | Issue pending (1), 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L194-L217] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L104-L107] [tests/unit/lower_tertiary/test_life_to_date.py:L76-L83] |
| Annual portfolio cashflows are passed to an MIRR API documented as monthly; comprehensive output suppresses annual MIRR | No detection check exists validating the portfolio annual MIRR against an annual-period closed form; do not use that output as a hand reference | Issue pending (4), 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L266-L274] [packages/worldenergydata-fdas/src/worldenergydata/fdas/api.py:L137-L169] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L286-L295] |
| Calendar cycle time is exposed through deprecated `drilling_days` | Existing benchmark alias test / regenerated CSV check; 0 label ambiguities is the desired criterion, but regenerated CSV check skips | #1077; basis reconciliation #1062; WAR quantization, April 2004 coverage floor and MD versus TVD limits #1078, 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:L265-L294] [tests/unit/lower_tertiary/test_well_benchmark.py:L170-L224] |
| WAR labels are legacy display strings; some codes lack a defensible published definition | No detection check exists establishing meanings of undocumented codes; never treat display vocabulary as regulatory definitions | #1062, 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L59-L84] |
| Decline-derived EUR may be unavailable, low quality or unqualified as reserves | Inspect `decline_flag`, minimum 6 positive monthly points and fit quality; no detection check exists qualifying booked reserves | #973, 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:L205-L243] |
| Assumption decks, fiscal extension and formal citation adoption remain separate work | C2 verifies arithmetic only; no detection check exists establishing external validity of all default assumptions | #651, #361, 2026-10-15 | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L138-L168] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L630-L635] |
| A broad package-data glob includes nested Markdown, including this pack | Static glob check: 1 matching package-data pattern; no wheel exclusion check exists for the pack | Issue pending (2), 2026-10-15 | [packages/worldenergydata-bsee/pyproject.toml:L112-L116] |

## 7. Lessons log

| Date | Entry ID | Lesson | Evidence | Pack change | Shared-log entry |
| --- | --- | --- | --- | --- | --- |
| 2026-10-15 | LT-knowledge-0 | State the cashflow basis before comparing NPV: annual projected oil receipts and observed monthly production have different origins and cost treatments | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L124-L159] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L175-L207] | Sections 1–3 distinguish the paths | Issue pending (5) |
| 2026-10-15 | LT-units-0 | A correctly converted reporting result does not qualify the summary helper's gas output | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L194-L217] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L104-L107] | Sections 2 and 6 disclose the difference | Issue pending (1) |

## 8. Ownership

Review assignment: calculations quality manager; deputy: an independent calculations reviewer; implementation and maintenance: module maintainers; escalation: quality manager for classification, evidence and tolerance questions, then maintainers for cross-module scope (AQG r0, section 11, Sign-off and independence).

A dedicated data-pipeline quality-manager appointment remains open under issue pending (3); the present family classification is EC (AQG r0, section 10, Python calculations).

## 9. Dependencies and implementation inventory

### Runtime and data routes

| Dependency / consumer | Role and boundary | Evidence |
| --- | --- | --- |
| pandas / YAML | Tabular processing and configuration loading | Actual loader and aggregation operations [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L16-L50] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L144-L200] |
| Shared data resolver | Resolves BSEE raw-data roots for ZIP and binary inputs | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L15-L28] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L92-L100] |
| FDAS API | NPV / IRR / MIRR / payback evaluation and disclosure comparison | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L266-L294] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py:L374-L401] |
| BSEE production / WAR | Historic production, monthly windows and operation markers; binary loader selection patches both reproducer modules | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L231-L243] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L455-L487] |
| BSEE decline and uptime analysis | Per-well fit, quality flags and uptime; EUR remains a provisional extrapolation | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:L196-L243] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:L377-L427] |
| Portfolio analytics → comprehensive report | Economics, roster, field payloads and analytics assembled before rendering | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L451-L479] |
| Optional browser | PDF renderer locates a browser executable, checks PDF bytes and normalizes date metadata; missing executable leaves text outputs available | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L783-L835] |

Version requirements are package constraints rather than a solver-version contract; the distribution declares Python >=3.10 and pandas, NumPy, FDAS and other dependencies. [packages/worldenergydata-bsee/pyproject.toml:L6-L12] [packages/worldenergydata-bsee/pyproject.toml:L59-L88]

### Map inventory and counted families

Map source record: digitalmodel, *Implementation map*, ref `origin/codex/implmap-work` at `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`; map data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, `families` collection.

| Inventory measure | Recorded result |
| --- | --- |
| Families in map | 13 |
| Families with an implementation `path` inside the header package | 0 |
| Inventory of implementations for those families | Empty |
| Ranked / counted families | Empty; no ties to resolve |
| Required package grep | NOT_APPLICABLE: no map family has any implementation row inside this package |
| Further implementations contributing to the counted total | 0; no counted family |
| A8 | PASS for empty inventory; mandatory grep NOT_APPLICABLE |

These values are the recorded result of parsing that map and selecting `implementations[].path` by the complete header-package prefix, before ranking by descending in-package row count and preserving file order for ties (digitalmodel, *Implementation map*, the map revision and `families` collection named above).

Map follow-up: add the section-3 method families for lease/month production aggregation, monthly cashflow and discounting, historical NPV/MIRR, production classification, depth-normalized drilling comparison, portfolio projection/breakeven and input-integrity checks, including the parallel production aggregation and WAR activity route inventoried below; a family becomes counted only when the map contains an in-package implementation row (#349). [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L203-L232] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L131-L226] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L273-L287] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/production_classifier.py:L19-L81] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py:L41-L107] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L124-L198] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L50-L78]

### Further repository search

An additional definition-name search covered repository Python, including `scripts/`, for monthly financials, production aggregation, classification, learning, NPV and MIRR; it is advisory rather than part of the counted-family result.

| Other definition | Classification / limitation | Evidence |
| --- | --- | --- |
| Sibling `bsee/analysis/lower_tertiary/` | Parallel route inside the bsee pack scope: `LegacyProductionLoader.field_total_rate` sums monthly well rates; WAR methods count records by year and rig and group subsea / dry-tree activity; map follow-up #349 should register both production routes and WAR methods | [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/lower_tertiary/legacy_loader.py:L109-L128] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/lower_tertiary/war_extractor.py:L83-L158] |
| FDAS `calculate_npv` and `excel_like_mirr` | Independent financial implementations outside the package; map follow-up #349 | [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L25-L115] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L118-L166] |
| Economics schedule valuation | Uses the canonical FDAS financial module; the duplicate schedule DCF was removed | [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py] |
| `scripts/all_fields_economics.py::npv_trim`, `excel_mirr` | Independently compute trimmed NPV and MIRR; map follow-up #349 | [scripts/all_fields_economics.py:L73-L87] |
| `build_field_npv_timeline` / `build_well_npv_stackup` | Reconstruct monthly cashflows and discount them inside the package; explicitly inventoried here and section 3; no claim that they merely delegate all arithmetic | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L948-L1074] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L1401-L1584] |

## 10. Coverage and open items

### Reading and test inventory

Source reading covers all 16 Python files of the header package, without excluding a subpackage; the source manifest below identifies the read revision's files and line ranges.

| Source file | Pinned range |
| --- | --- |
| `__init__.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/__init__.py:L1-L18] |
| `comprehensive_report.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L1-L835] |
| `drilling_learning.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/drilling_learning.py:L1-L107] |
| `latest_runner.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/latest_runner.py:L1-L321] |
| `life_to_date.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L1-L447] |
| `npv.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L1-L226] |
| `ops_timeline.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/ops_timeline.py:L1-L487] |
| `partner_reference.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/partner_reference.py:L1-L53] |
| `portfolio.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio.py:L1-L49] |
| `portfolio_analytics.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py:L1-L544] |
| `portfolio_economics.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L1-L514] |
| `production_classifier.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/production_classifier.py:L1-L108] |
| `v30_financial_reproducer.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L1-L1642] |
| `v30_reproducer.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_reproducer.py:L1-L388] |
| `well_benchmark.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/well_benchmark.py:L1-L434] |
| `wti_prices.py` | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/wti_prices.py:L1-L409] |

The main-path test reading covers the monthly-financial, classification, learning, snapshot, observed-production and portfolio/report checks cited in sections 4–6; the full module suite was executed, and detailed review of every ancillary builder test is deferred under issue pending (3).

Test discovery: 34 test files under `tests/unit/lower_tertiary`; 608 collected nodes rather than the inventory lead of 417; 107 additional reporting / determinism / contract nodes; run results in section 5 are observations from the code pin.

Documentation discovery used literal `lower_tertiary` and the spaced/hyphenated module name in Markdown under `docs/`: 38 files found, 33 safe-to-list paths below and 5 discovery files with identifying names withheld for codenaming under issue pending (3).

The first six read documents in the list below were read as main-path context; the remaining discovered documents require detailed audit under issue pending (3), rather than being accepted as evidence of current code behaviour.

- `docs/plans/2026-05-03-issue-375-per-field-economics-10-lt-fields.md`
- `docs/plans/2026-05-03-issue-376-cross-field-analytics-lt.md`
- `docs/plans/2026-05-03-issue-377-lt-comprehensive-report-assembly.md`
- `docs/plans/2026-05-04-issue-172-lt-rev30-reproducibility.md`
- `docs/modules/bsee/analysis/production/lt_v30_v50_code_reconciliation.md`
- `docs/data-sources/bsee/analysis/well-identifier-grain.md`
- `docs/AI_USAGE_GUIDELINES.md`
- `docs/CLI.md`
- `docs/PHASE_2_TIER_1_COVERAGE_EXPANSION.md`
- `docs/adr/0001-domain-package-split.md`
- `docs/ci/flake8-inventory-2026-04-23.md`
- `docs/data-outputs-site.md`
- `docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.md`
- `docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md`
- `docs/domains/bsee/paleowells-readme.md`
- `docs/guides/QUICK_START.md`
- `docs/guides/user_prompt.md`
- `docs/modules/cost/research/2026-07-15-e1-project-expansion-research-record.md`
- `docs/modules/repository-architecture.md`
- `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md`
- `docs/plans/2026-05-04-issue-361-calc-citation-contract.md`
- `docs/plans/2026-05-04-issue-367-api12-npv-migration.md`
- `docs/plans/2026-05-08-issue-394-repo-structure-normalization.md`
- `docs/plans/2026-07-03-issue-714-fdas-source-agnostic.md`
- `docs/plans/2026-07-06-issue-847-boem-reserves-discovery-ingest.md`
- `docs/plans/2026-07-16-issue-1044-fdas-workbook-reconciliation.md`
- `docs/plans/execution-packs/2026-04-22-approved-cost-wave/master-plan.md`
- `docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-335.md`
- `docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-337.md`
- `docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-338.md`
- `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md`
- `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md`
- `docs/reports/data-freshness-scorecard-2026-06-08.md`

The package README was read for distribution context; there is no pre-existing README or documentation subfolder inside the header package at the code pin. [packages/worldenergydata-bsee/README.md:L1-L20]

### Open-item register

| Item | Scope / required action | Maintainer follow-up | Evidence |
| --- | --- | --- | --- |
| O1 | Correct the summary helper's gas conversion and add a direct BCF assertion | Issue pending (1); module maintainers | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L194-L217] |
| O2 | Exclude knowledge-pack Markdown from wheel data without changing runtime data selection | Issue pending (2); packaging maintainers | [packages/worldenergydata-bsee/pyproject.toml:L112-L116] |
| O3 | Restore the absent bulk-production fixtures and rerun the 137 data-dependent cases; regenerate the stale calendar-alias CSV check separately | Issue pending (3), #1077; data maintainers | [tests/unit/lower_tertiary/test_repeatability_v30.py:L44-L54] [tests/unit/lower_tertiary/test_well_benchmark.py:L206-L224] |
| O4 | Complete detailed ancillary-test and discovered-document audit; codename identifying discovery paths and fixture identifiers; assign data-family deputy | Issue pending (3); module maintainers | Reading/discovery record above; test source inventory [tests/unit/lower_tertiary/test_life_to_date.py:L19-L27] |
| O5 | Qualify annual MIRR before exposing portfolio rates as a checked reference | Issue pending (4); calculations maintainers | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L266-L274] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L87-L115] |
| O6 | Resolve price fallback basis, requested-date ceiling and overlap-validation reachability | #1191; module maintainers | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/wti_prices.py:L199-L270] |
| O7 | Qualify assumptions, fiscal scope and full-cycle reserves; retain explicit scenario limits meanwhile | #651, #973; calculations maintainers | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L252-L271] |
| O8 | Replace placeholder HSE / empty disclosure comparison with observed coverage | #366, #343, #344; data maintainers | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py:L334-L425] |
| O9 | Formal calculation-citation sidecars remain outside this documentation change | #361; module maintainers | [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L630-L635] |
| O10 | Extend the implementation map to every method family in section 3 and the advisory duplicate findings in section 9 | #349; registry maintainers | Section-9 map source and cited definition inventory |
| O11 | Assign the shared-log entry for the cashflow-basis lesson | Issue pending (5); module maintainers | Section-7 lesson LT-knowledge-0 |
| O12 | Replace the broad report-generator import skip with a failing import check; keep import-failure counts separate meanwhile | Issue pending (6); test maintainers | [tests/unit/lower_tertiary/test_well_npv_stackup.py:L25-L29] |

### Unverified claims

UNVERIFIED: External validity and current applicability of the portfolio's emitted regulation and outlook attribution strings were not established from their original sources; defaults are documented as assumptions, not regulatory requirements (#651, #361). [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L298-L359] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/comprehensive_report.py:L138-L168]

UNVERIFIED: Production-wide reproduction and independent full-cycle economic accuracy remain unestablished without the missing production fixtures, qualified reserves and a reconciled fiscal/expenditure basis (issue pending (3), #651, #973). [tests/unit/lower_tertiary/test_repeatability_v30.py:L44-L54] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/life_to_date.py:L252-L271]

Final quality clearance and replacement of draft references by issue numbers remain maintainer actions; this pack retains DRAFT status.
