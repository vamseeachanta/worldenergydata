# Economics module knowledge pack

| Header | Value |
| --- | --- |
| Module | economics |
| Repository | worldenergydata |
| Path | `packages/worldenergydata-economics/src/worldenergydata/economics` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `e73bda871798429eeb6dda0d16ed5520548d6cad` |
| Analysis family | Data pipeline; AQG r0 Python calculations gate set |
| Quality role | Calculations quality manager |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

`calculate_npv` computes discounted net cash flow, `calculate_mirr` computes modified internal rate of return, and `build_cash_flow_schedule` constructs revenue, operating expenditure and carbon costs from production inputs. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L137-L245] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L253-L309]

`carbon_npv_curve` sweeps carbon prices, `breakeven_carbon_price` searches for zero NPV, and `tornado_sensitivity` varies price, operating cost, carbon price and discount rate independently. [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L98-L194] [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L197-L313]

The NPV path uses equally spaced array positions beginning at time zero; calendar labels do not determine discount exponents, and no tax or inflation adjustment appears in its cash-flow equation. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L163-L175]

Package metadata classifies development status as Alpha; this is a metadata classification rather than engineering qualification. [packages/worldenergydata-economics/pyproject.toml:L15-L23]

## 2. Inputs and outputs

### Inputs

| Input | Unit and basis | Range / default | Route and evidence |
| --- | --- | --- | --- |
| `years` | Period labels, dimensionless integers | Required; equal list lengths | `CashFlowSchedule`; labels only. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L33-L79] |
| `capex`, `revenue`, `opex`, `carbon_cost` | USD per period; positive expenditures are outflows, revenue inflows | Required; equal lengths; no value bounds enforced | `CashFlowSchedule`. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L39-L79] |
| `emission_tco2_per_period` | tCO2 per period | Default `None`; length checked when supplied | Optional schedule field. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L47-L79] |
| `production_boe_per_year` | boe per annual period | Required; no numeric bounds enforced | Constructor. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L253-L309] |
| `oil_price_usd_per_boe`, `opex_usd_per_boe` | USD/boe | Required; flat scalars | Constructor. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L276-L300] |
| `capex_by_year` | USD per period | Required | Constructor. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L280-L308] |
| `carbon_cost_usd_per_tonne` | USD/tCO2 | Required | Constructor. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L282-L300] |
| `scope1_tco2_per_boe`, `scope2_tco2_per_boe` | tCO2/boe | Required; summed | Constructor. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L284-L300] |
| `discount_rate` | Fraction per annual period | Required; greater than -1 | `calculate_npv`. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L147-L161] |
| `finance_rate`, `reinvestment_rate` | Fraction per period | Required; no explicit range check | `calculate_mirr`. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L185-L236] |
| `carbon_prices`, `search_upper` | USD/tCO2 | Sweep array; search upper default 2000 | Carbon API. [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L98-L194] |
| `swing_fraction` | Dimensionless fraction | Default 0.20; no explicit bound | Tornado API. [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L197-L237] |

UNVERIFIED: a currency reference year and a real-versus-nominal basis are not established for the USD inputs; callers must provide compatible bases (issue pending (1)).

The interfaces contain no spatial coordinate, origin or phase fields; cash-flow signs follow the positive-component convention above. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L29-L79]

### Outputs

| Output | Unit / contents | Evidence |
| --- | --- | --- |
| `NPVResult` | NPV USD; net and discounted cash-flow lists USD; rate fraction | [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L82-L101] |
| `MIRRResult` | MIRR and rates fractions; negative PV and positive FV USD; interval count dimensionless | [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L104-L129] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L215-L245] |
| `CarbonSensitivityResult` | Price array USD/tCO2; NPV array and zero-price base NPV USD; rate fraction | [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L39-L60] |
| Breakeven | Price USD/tCO2 or `None` when the bracket has no sign change or the root call raises `ValueError` | [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L152-L194] |
| `TornadoEntry` | Low/high/base NPV and absolute swing USD; scenario values in the varied input's unit | [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L64-L89] [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L298-L313] |

## 3. Method and governing standards

NPV uses `CF[t] = revenue[t] - opex[t] - capex[t] - carbon_cost[t]` and `sum(CF[t]/(1+r)**t)` for `t=0..len(CF)-1`; subsequent annual entries are discounted at integer period ends, with the initial entry undiscounted. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L163-L175]

The published definition used for comparison is NumPy Financial, *Financial functions*, version 1.0.0, `npv`, Parameters, Warnings and Notes; its fixed interval must match the rate interval and its series begins at time zero. [NumPy Financial 1.0.0, npv definition](https://github.com/numpy/numpy-financial/blob/v1.0.0/numpy_financial/_financial.py#L712-L781)

MIRR sets `n=len(CF)-1`, discounts negative cash flows at the finance rate, compounds nonnegative flows to `n` at the reinvestment rate, and returns `(FV/PV)**(1/n)-1`. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L215-L244]

The published comparison definition is NumPy Financial, *Financial functions*, version 1.0.0, `mirr`, Parameters and implementation; its documented requirement for both signs differs from this module's negative-only guard, so it is not a drop-in validation oracle for all-negative schedules. [NumPy Financial 1.0.0, mirr definition](https://github.com/numpy/numpy-financial/blob/v1.0.0/numpy_financial/_financial.py#L784-L820) [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L218-L236]

Carbon cost is production times the sum of the two supplied emission intensities times the supplied carbon price; revenue and operating cost are production times their respective unit prices. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L294-L308]

UNVERIFIED: no published carbon-accounting definition, reporting boundary, or standard edition is established by this arithmetic; the two supplied intensities are added without an accounting-method reference (issue pending (1)).

Breakeven uses `brentq` over zero to the upper price with `xtol=1e-6` USD/tCO2 and `rtol=1e-9`; tornado results sort the absolute NPV ranges in descending order. [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L178-L194] [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L298-L313]

No citation sidecar is present in the NPV or MIRR result fields; the provenance gap is tracked by [the calculation-citation issue](https://github.com/vamseeachanta/worldenergydata/issues/361). [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L82-L129]

## 4. Validated worked examples

These independent checks use short-series arithmetic rather than stored module output; the expected arithmetic is also present in the cited existing tests. [tests/unit/economics/test_dcf.py:L68-L76] [tests/unit/economics/test_dcf.py:L222-L237] [tests/unit/economics/test_dcf.py:L281-L295]

| ID / classification | Independent expectation and input basis | Tolerance / test node ID | Offline result |
| --- | --- | --- | --- |
| V1 validated | USD cash flows `[-500,150,150,150]`, zero rate: `-500+3*150=-50` USD | Absolute 1e-6 USD; `tests/unit/economics/test_dcf.py::TestNPVCalculation::test_npv_zero_discount_rate_equals_sum` | PASS; BASE and documentation-tree runs both passed. [tests/unit/economics/test_dcf.py:L68-L76] |
| V2 validated | USD cash flows `[-1000,0,0,1500]`: PV 1000 USD, FV 1500 USD, MIRR `1.5**(1/3)-1`; rounded display 14.5 percent | Test relative 1e-3 against 0.14471 fraction; rounded expected-value basis; `tests/unit/economics/test_dcf.py::TestMIRRCalculation::test_mirr_simple_case` | PASS; BASE and documentation-tree runs both passed. [tests/unit/economics/test_dcf.py:L222-L237] |
| V3 validated | `10000*(0.02+0.03)=500` tCO2; `500*50=25000` USD carbon cost | Existing test uses `pytest.approx`; additional hand criterion 1e-6 USD absolute; `tests/unit/economics/test_dcf.py::TestBuildCashFlowSchedule::test_build_schedule_carbon_cost_calculation` | PASS; BASE and documentation-tree runs both passed. [tests/unit/economics/test_dcf.py:L281-L295] |
| R1 regression | Zero-price curve compared with `calculate_npv` from the same module; no independent expected value | Relative 1e-6; `tests/unit/economics/test_carbon.py::TestCarbonNpvCurve::test_npv_at_zero_carbon_matches_no_carbon_case` | PASS; BASE and documentation-tree runs both passed. [tests/unit/economics/test_carbon.py:L90-L104] |

## 5. QA gates

Proposed checks under AQG r0, section 10, Python calculations, and section 9, G5 (independent clearance pending):

| Gate / check | Module-specific executable check | Numeric pass criterion and unit | Evidence |
| --- | --- | --- | --- |
| G0 / C0 | Construct mismatched `CashFlowSchedule` lists using the existing length test | Exactly 1 `ValueError` per mismatched schedule; count | [tests/unit/economics/test_dcf.py:L90-L99] |
| G0 / C1 | Check NPV rate -1.5 using the existing invalid-rate test | Exactly 1 `ValueError`; count | [tests/unit/economics/test_dcf.py:L101-L105] |
| G1 / C2 | Import public economics APIs through both offline test files and run the domain tests | 35 passed tests, 0 failed tests; count | [tests/unit/economics/test_dcf.py:L13-L20] [tests/unit/economics/test_carbon.py:L13-L23] |
| G2 / C3 | `calculate_npv`, V1 | Absolute NPV difference at most 1e-6 USD | [tests/unit/economics/test_dcf.py:L68-L76] |
| G2 / C4 | `calculate_mirr`, V2; use the unrounded closed form for an additional hand comparison | Absolute MIRR difference at most 1e-10 fraction for the hand comparison | [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L228-L236] [tests/unit/economics/test_dcf.py:L222-L237] |
| G2 / C5 | `build_cash_flow_schedule`, V3 | Absolute carbon-cost difference at most 1e-6 USD | [tests/unit/economics/test_dcf.py:L281-L295] |
| G2 / C6 | `breakeven_carbon_price`, reconstruct the schedule at its returned price | Absolute NPV at most 1 USD | [tests/unit/economics/test_carbon.py:L153-L175] |
| G3 | NOT_APPLICABLE: these functions contain no dynamic model or time integration | No dynamic check required | [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L137-L245] [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L98-L194] |
| G4 | NOT_APPLICABLE: the interfaces accept cash-flow arrays, not diffraction geometry | No diffraction check required | [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L29-L79] |
| G5 / C7 | Compare section-4 node IDs and results with the offline test records at the pinned revision | 4 of 4 case records matched; 0 missing results; count | [tests/unit/economics/test_dcf.py:L68-L76] [tests/unit/economics/test_dcf.py:L222-L237] [tests/unit/economics/test_dcf.py:L281-L295] [tests/unit/economics/test_carbon.py:L90-L104] |

Additional diagnostic criteria for known gaps, without claiming an existing passing test:

| Gate / check | Detection route | Proposed pass criterion | Evidence |
| --- | --- | --- | --- |
| G0 / D1 | Inspect a schedule with nonzero stored carbon cost and missing emissions before calling `carbon_npv_curve` | 0 missing-emission records admitted for sensitivity; count | [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L321-L345] |
| G0 / D2 | Inspect `calculate_mirr` input length and both rates before evaluation | At least 2 samples; 0 nonfinite rates; both rates greater than -1 fraction | [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L185-L236] |
| G5 / D3 | Inspect package-data patterns before asserting that this pack is excluded from a wheel | 0 `docs/agent-pack.md` members in a built wheel; count; build not performed | [packages/worldenergydata-economics/pyproject.toml:L54-L55] |

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection | Tracking |
| --- | --- | --- |
| Missing emissions become zero; the replacement schedule discards existing carbon costs when sensitivity is recalculated | D1; no existing missing-emission detection test exists in the two domain test files | Issue pending (2). [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L321-L345] |
| One negative sample gives zero MIRR periods, then division by zero; finance and reinvestment rate domains are unchecked | D2; no existing one-sample detection test exists | Issue pending (3). [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L215-L236] |
| A local MIRR path and an independent FDAS financial path remain present; matching method names do not establish identical timing or error semantics | Compare time bases and guards before reusing reference values; no cross-surface parity test is established here | [Consolidation](https://github.com/vamseeachanta/worldenergydata/issues/735) redirects to [economics reconciliation](https://github.com/vamseeachanta/worldenergydata/issues/832). [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L215-L244] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L62-L113] |
| Result structures carry no formula provenance sidecar | Inspect result fields; no sidecar detection check exists in these tests | [Citation tracking](https://github.com/vamseeachanta/worldenergydata/issues/361). [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L82-L129] |
| Package-data glob includes nested Markdown, so exclusion of the pack from distributions is not established | D3 | Issue pending (4). [packages/worldenergydata-economics/pyproject.toml:L54-L55] |

## 7. Lessons log

| Date | Record | Lesson | Evidence / pack change | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-15 | Initial pack | Sensitivity requires explicit emissions even when a schedule already stores carbon cost | Missing-emission warning added to section 6. [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L321-L345] | Issue pending (2) |

## 8. Ownership

Proposed roles: calculations quality manager; deputy calculations quality manager; producing function: module documentation. Escalation route: the quality manager for unresolved criteria, and the maintainer for scope or publication decisions. Independent clearance remains required; these role assignments are proposals, not recorded appointments.

## 9. Dependencies and parallel implementations

The package declares core, NumPy and SciPy dependencies; the carbon module calls SciPy `brentq`, and DCF evaluates NumPy arrays. [packages/worldenergydata-economics/pyproject.toml:L30-L35] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L163-L175] [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L178-L194]

No runtime dependency on a licensed solver appears in the public exports or these calculation paths. [packages/worldenergydata-economics/src/worldenergydata/economics/__init__.py:L6-L34] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L17-L22] [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L19-L31]

Repository-wide search inventory of financial arithmetic and calls (including scripts, templates, tests and archives):

| Source location | Arithmetic sites / calls |
| --- | --- |
| .claude/agent-library/worldenergydata/financial-analysis/templates/financial_calculations.py | `bond_price` [.claude/agent-library/worldenergydata/financial-analysis/templates/financial_calculations.py:L493-L497]; `bond_duration` [.claude/agent-library/worldenergydata/financial-analysis/templates/financial_calculations.py:L530-L541]; `project_finance_model` [.claude/agent-library/worldenergydata/financial-analysis/templates/financial_calculations.py:L676-L727] |
| .claude/agent-library/worldenergydata/oil-and-gas-expert/templates/calculations.py | `calculate_npv` [.claude/agent-library/worldenergydata/oil-and-gas-expert/templates/calculations.py:L321-L321]; `calculate_irr` [.claude/agent-library/worldenergydata/oil-and-gas-expert/templates/calculations.py:L346-L346] |
| _archive/bsee/analysis/legacy/api12_economics.py | `perform_npv_calculation` [_archive/bsee/analysis/legacy/api12_economics.py:L228-L243]; `perform_excel_aligned_npv_calculation` [_archive/bsee/analysis/legacy/api12_economics.py:L410-L515] |
| docs/modules/bsee/analysis/production/FDAS_V30/generate_financial_summary_V30.py | `excel_like_mirr` [docs/modules/bsee/analysis/production/FDAS_V30/generate_financial_summary_V30.py:L191-L193] |
| packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py | `get_monthly_discount_rate` [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L70-L70]; `get_monthly_finance_rate` [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L74-L74]; `get_monthly_reinvest_rate` [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L78-L78]; `calculate_financial_metrics` [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L419-L419]; `calculate_npv` [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L442-L442]; `calculate_mirr` [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L475-L481] |
| packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/models.py | `calculate_npv` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/models.py:L529-L531] |
| packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_models.py | `npv` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_models.py:L244-L244]; `present_value_inflows` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_models.py:L252-L252]; `present_value_outflows` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_models.py:L260-L260]; `calculate_irr` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_models.py:L267-L267]; `sensitivity_analysis` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_models.py:L276-L276] |
| packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_tables.py | `generate_sensitivity_analysis_tables` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_tables.py:L53-L234] |
| packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_template.py | `add_economic_forecast` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_template.py:L309-L309] |
| packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_well_analysis.py | `analyze_individual_well_economics` [packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/economic_well_analysis.py:L46-L86] |
| packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py | `summarize_field_financials` [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L179-L186] |
| packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py | `_solve_breakeven_oil_price` [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L181-L181]; `npv_at` [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L181-L181]; `analyze_field` [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L270-L282] |
| packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py | `_excel_like_mirr` [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L282-L284] |
| packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/field_aggregation.py | `calculate_field_npv` [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/field_aggregation.py:L783-L783]; `calculate_irr` [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/field_aggregation.py:L805-L807] |
| packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/views_financial.py | `calculate_npv` [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/views_financial.py:L40-L40]; `calculate_irr` [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/views_financial.py:L47-L47] |
| packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/well_production.py | `calculate_npv` [packages/worldenergydata-bsee/src/worldenergydata/well_production_dashboard/well_production.py:L102-L102] |
| packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py | `excel_like_mirr` [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L88-L113]; `calculate_npv` [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L151-L161]; `calculate_irr` [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L225-L232] |
| packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py | `fiscal_sensitivity` [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L224-L224] |
| packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py | `calculate_npv` [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L222-L222]; `_calculate_npv_from_cashflows` [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L556-L556] |
| packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py | `_compute` [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/cross_basin_example.py:L173-L173] |
| scripts/all_fields_economics.py | `npv_trim` [scripts/all_fields_economics.py:L77-L77]; `excel_mirr` [scripts/all_fields_economics.py:L84-L85] |
| scripts/gtm/generate_fdas_gtm_report.py | `run_scenario` [scripts/gtm/generate_fdas_gtm_report.py:L111-L123] |
| scripts/julia_field_granular_economics.py | `excel_mirr` [scripts/julia_field_granular_economics.py:L105-L106]; `npv_trimmed` [scripts/julia_field_granular_economics.py:L118-L118] |
| scripts/lower_tertiary/run_parametric_economics.py | `_npv_at_rates` [scripts/lower_tertiary/run_parametric_economics.py:L103-L103] |
| src/worldenergydata/field_development/integrations.py | `_rough_npv` [src/worldenergydata/field_development/integrations.py:L168-L168] |
| src/worldenergydata/modules/well_production_dashboard/well_detail_views.py | `calculate_npv` [src/worldenergydata/modules/well_production_dashboard/well_detail_views.py:L471-L471]; `calculate_irr` [src/worldenergydata/modules/well_production_dashboard/well_detail_views.py:L478-L478] |
| tests/_archive/integration/test_bsee_pipeline.py | `test_economic_analysis_with_production` [tests/_archive/integration/test_bsee_pipeline.py:L319-L324] |
| tests/_archive/modules/bsee/analysis/legacy/run_npv_test.py | `run_npv_test_basic` [tests/_archive/modules/bsee/analysis/legacy/run_npv_test.py:L61-L61] |
| tests/_archive/modules/bsee/analysis/test_excel_aligned_npv.py | `calculate_excel_aligned_npv` [tests/_archive/modules/bsee/analysis/test_excel_aligned_npv.py:L160-L205]; `test_excel_formula_equivalence_verification` [tests/_archive/modules/bsee/analysis/test_excel_aligned_npv.py:L471-L479] |
| tests/_archive/modules/bsee/analysis/test_monthly_field_economics.py | `npv` [tests/_archive/modules/bsee/analysis/test_monthly_field_economics.py:L43-L43]; `generate_monthly_economics_dataframe` [tests/_archive/modules/bsee/analysis/test_monthly_field_economics.py:L262-L262] |
| tests/_archive/modules/bsee/analysis/test_npv_accuracy_validation.py | `calculate_benchmark_npv` [tests/_archive/modules/bsee/analysis/test_npv_accuracy_validation.py:L108-L108] |
| tests/_archive/performance/test_regression_detection.py | `_simulate_npv_calculation` [tests/_archive/performance/test_regression_detection.py:L387-L387] |
| tests/integration/test_production_api12_full.py | `test_economic_calculations` [tests/integration/test_production_api12_full.py:L154-L154] |
| tests/modules/bsee/analysis/api12_drilling_completion_analysis/production_data_investigation.py | `test_production_data_rows` [tests/modules/bsee/analysis/api12_drilling_completion_analysis/production_data_investigation.py:L89-L147] |
| tests/modules/bsee/analysis/custom_scripts/Copilot/comprehensive_npv_analyzer.py | `calculate_scenario_npvs` [tests/modules/bsee/analysis/custom_scripts/Copilot/comprehensive_npv_analyzer.py:L144-L145]; `perform_sensitivity_analysis` [tests/modules/bsee/analysis/custom_scripts/Copilot/comprehensive_npv_analyzer.py:L168-L195] |
| tests/modules/bsee/analysis/custom_scripts/Copilot/excel_npv_analysis.py | `extract_npv_from_sheets` [tests/modules/bsee/analysis/custom_scripts/Copilot/excel_npv_analysis.py:L222-L222] |
| tests/modules/bsee/analysis/custom_scripts/Copilot/npv_analysis.py | `calculate_custom_npv_scenarios` [tests/modules/bsee/analysis/custom_scripts/Copilot/npv_analysis.py:L88-L88]; `analyze_npv_sensitivity` [tests/modules/bsee/analysis/custom_scripts/Copilot/npv_analysis.py:L149-L165] |
| tests/modules/bsee/analysis/financial-analysis-sme-code/scripts/Build_Development_Financials_V20_worldenergydata.py | `npv_from_monthly` [tests/modules/bsee/analysis/financial-analysis-sme-code/scripts/Build_Development_Financials_V20_worldenergydata.py:L495-L495]; `mirr_from_monthly` [tests/modules/bsee/analysis/financial-analysis-sme-code/scripts/Build_Development_Financials_V20_worldenergydata.py:L512-L516] |
| tests/modules/bsee/analysis/financial-analysis-sme-code/task-0-artifacts/consolidated_analysis.py | `_calculate_npv` [tests/modules/bsee/analysis/financial-analysis-sme-code/task-0-artifacts/consolidated_analysis.py:L339-L339] |
| tests/modules/bsee/analysis/legacy/test_npv_analysis_debug.py | `calculate_npv` [tests/modules/bsee/analysis/legacy/test_npv_analysis_debug.py:L151-L151]; `test_npv_calculation_direct` [tests/modules/bsee/analysis/legacy/test_npv_analysis_debug.py:L151-L151] |
| tests/modules/bsee/analysis/npv-data-source-comparison/test_current_npv_implementation.py | `test_discount_rate_application` [tests/modules/bsee/analysis/npv-data-source-comparison/test_current_npv_implementation.py:L172-L180]; `test_period_timing_assumptions` [tests/modules/bsee/analysis/npv-data-source-comparison/test_current_npv_implementation.py:L223-L223] |
| tests/performance/test_critical_operations.py | `calculate_npv` [tests/performance/test_critical_operations.py:L92-L102]; `test_financial_calculation_performance` [tests/performance/test_critical_operations.py:L92-L102] |
| tests/test_query_api.py | `test_npv_calculation` [tests/test_query_api.py:L316-L316]; `test_npv_negative_result` [tests/test_query_api.py:L326-L326]; `test_npv_accepts_list` [tests/test_query_api.py:L333-L333]; `test_npv_accepts_numpy_array` [tests/test_query_api.py:L341-L341]; `test_irr_calculation` [tests/test_query_api.py:L349-L349]; `test_mirr_calculation` [tests/test_query_api.py:L363-L363] |
| tests/unit/financial/test_npv_analysis.py | `setup` [tests/unit/financial/test_npv_analysis.py:L32-L32]; `test_npv_calculation_basic` [tests/unit/financial/test_npv_analysis.py:L37-L37]; `test_npv_with_different_rates` [tests/unit/financial/test_npv_analysis.py:L51-L51]; `test_npv_with_zero_rate` [tests/unit/financial/test_npv_analysis.py:L61-L61]; `test_npv_with_empty_cash_flows` [tests/unit/financial/test_npv_analysis.py:L70-L70]; `test_npv_with_single_cash_flow` [tests/unit/financial/test_npv_analysis.py:L78-L78]; `test_npv_edge_case_cash_flows` [tests/unit/financial/test_npv_analysis.py:L212-L212]; `test_npv_edge_case_rates` [tests/unit/financial/test_npv_analysis.py:L234-L236]; `test_irr_calculation` [tests/unit/financial/test_npv_analysis.py:L248-L248]; `test_profitability_index` [tests/unit/financial/test_npv_analysis.py:L273-L273]; `calculate_all_npvs` [tests/unit/financial/test_npv_analysis.py:L314-L314]; `test_multiple_npv_calculations_performance` [tests/unit/financial/test_npv_analysis.py:L314-L314]; `test_basic_npv_function` [tests/unit/financial/test_npv_analysis.py:L335-L335] |
| tests/unit/lower_tertiary/test_field_inputs.py | `test_summarize_field_financials_computes_discounted_cash_flow` [tests/unit/lower_tertiary/test_field_inputs.py:L136-L141] |
| tests/unit/test_property_based.py | `calculate_npv` [tests/unit/test_property_based.py:L39-L39] |

## 10. Coverage and open items

### Coverage record

All three module Python files, the package README and metadata, and both economics test files are covered by this pack's citations. [packages/worldenergydata-economics/src/worldenergydata/economics/__init__.py:L1-L34] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L1-L309] [packages/worldenergydata-economics/src/worldenergydata/economics/carbon.py:L1-L346] [packages/worldenergydata-economics/README.md:L1-L8] [packages/worldenergydata-economics/pyproject.toml:L1-L55] [tests/unit/economics/test_dcf.py:L1-L310] [tests/unit/economics/test_carbon.py:L1-L292]

The readiness matrix records “2 tests”; this is a README-style claim, unverified as a test-node count, and must not be read as the domain's executed count. [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L78-L86]

The documentation search also found a consolidation follow-on and a reference page linking the earlier source location; neither is independent numerical validation. [docs/plans/2026-07-03-issue-714-fdas-source-agnostic.md:L87-L91] [docs/reference/petroleum-domain/reserves-classification.md:L103-L109]

### Open items

| Item | Limitation / next checkpoint | Tracking |
| --- | --- | --- |
| O1 | UNVERIFIED currency reference year and real/nominal convention; UNVERIFIED published carbon-accounting definition. Document explicit compatible bases before engineering use | Issue pending (1) |
| O2 | Missing-emission sensitivity admission check and regression test | Issue pending (2) |
| O3 | MIRR input-domain and short-series detection tests | Issue pending (3) |
| O4 | Wheel exclusion of this pack is not established; check distribution contents and correct packaging separately | Issue pending (4) |
| O5 | Formula provenance sidecar and governing-reference coverage | [Calculation citations](https://github.com/vamseeachanta/worldenergydata/issues/361) |
| O6 | Independent disposition of overlapping financial surfaces and parity criteria | [Economics reconciliation](https://github.com/vamseeachanta/worldenergydata/issues/832) |
| O7 | Independent second-provider review, role appointment and replacement of pending issue references | Issue pending (5) |

No client-derived input values are introduced; examples use the cited test fixtures and closed-form arithmetic. [tests/unit/economics/test_dcf.py:L68-L76] [tests/unit/economics/test_dcf.py:L222-L237] [tests/unit/economics/test_dcf.py:L281-L295]
