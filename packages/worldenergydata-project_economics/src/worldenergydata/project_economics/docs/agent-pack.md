# project_economics module knowledge pack

| Header | Value |
| --- | --- |
| Module | `project_economics` |
| Repository | `worldenergydata` |
| Path | `packages/worldenergydata-project_economics/src/worldenergydata/project_economics` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `e73bda871798429eeb6dda0d16ed5520548d6cad` |
| Analysis family | EC (engineering calculations); gates per AQG r0 §10 Python calculations row |
| Quality role | Calculations quality manager, pending data quality appointment |
| Status | DRAFT; independent clearance pending |

Use the code revision above for every source citation. Treat the execution records below as observations of the cited test nodes at that revision, rather than as facts established by test source alone. The proposed QA criteria supplement the existing assertions; a passing regression does not clear a known calculation defect.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 0 | 2026-10-15 | Initial draft with pinned source citations and offline execution evidence. |
| 0, correction | 2026-10-15 | Expand method inventory and output QA criteria; correct skip descriptions and record source inconsistencies. |

## 1. Purpose and scope

project_economics implements periodic NPV, trimmed NPV, monthly MIRR, IRR and discrete payback; `EconomicsQuery.npv` converts sequences to arrays before delegation. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L25-L115] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L118-L200] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L203-L276] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/api.py:L90-L98]

`ProductionProcessor` aggregates production by identifier and month, detects first oil, computes cumulative volumes and water cut, and creates summaries and pivots; `ProductionForecaster` implements exponential and hyperbolic formulas. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L58-L137] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L139-L236] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L300-L353]

`CashflowEngine` combines production, supplied drilling days, assumptions, oil prices, optional gas prices and a royalty deck into monthly rows; its fixed OPEX, facilities CAPEX and monetary scaling limitations are recorded in section 6. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L456-L589]

`project_economics.router` supports CSV cashflow metrics and an NPV sensitivity matrix, producing CSV and JSON files; `ProjectEconomicsReportBuilder` separately assembles Excel summary and detail sheets. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L21-L82] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L84-L162] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/reports/excel_generator.py:L392-L442]

The country contract normalizes production and metadata; disclosure analytics delegates to the cost package rather than estimating costs within project_economics. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/contract.py:L75-L127] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/field_concept_normalizer.py:L145-L170] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/api.py:L301-L344]

The member metadata declares version `0.1.0` and Alpha status, while the import module exposes `1.0.0`; these are declarations, not an engineering qualification or a routing maturity rating. [packages/worldenergydata-project_economics/pyproject.toml:L5-L22] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/__init__.py:L99-L101]

UNVERIFIED: U1 — README claims of complete validation, complete coverage and faster execution are not established as module-wide qualification by this pack; see section 10. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/README.md:L7-L17]

## 2. Inputs and outputs

### Inputs

| Input | Unit / convention | Allowed range and default | Source and implementation |
| --- | --- | --- | --- |
| `cashflows`, annual discount rate, `period` | Caller-selected common currency; positive inflow, negative outflow; first element at time zero | Nonempty; NPV rate accepted in [-1, 1]; monthly default or annual; endpoint -1 needs separate qualification | `EconomicsQuery.npv`; no implicit currency conversion. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/api.py:L64-L76] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L141-L166] |
| Raw production frame | `PROD_DATE`; oil/water bbl, gas Mcf; grouping identifier | Constructor requires date and oil only; default group `API_WELL_NUMBER`; downstream methods need additional columns | `ProductionProcessor`; no global numeric/range validation. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L30-L59] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L151-L164] |
| Unified country production | `year`, `month`, `oil_bbl`, `gas_mcf`, `water_bbl`, `region`, `field_name` | Month 1–12; numeric year/month; empty input produces typed empty; volume coercion can produce NaN | `to_project_economics_production`; no aggregation across entities. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/contract.py:L32-L55] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/contract.py:L96-L127] |
| Monthly production | `YEAR_MONTH` as YYYY-MM; `MONTHLY_OIL_BBL`; optional `MONTHLY_GAS_MCF` | Supply a single entity with one row per month; oil-only dict conversion otherwise overwrites duplicate months | `CashflowEngine.generate_monthly_cashflow`. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L516-L544] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/gas_revenue.py:L18-L34] |
| Drilling timeline and cost assumptions | `drilling_monthly` days; host/SURF million USD, rig rate million USD/day, variable OPEX USD/bbl | No inferred drilling duration; absent timeline warns and yields zero drilling CAPEX; parameter lookup can fall back to default row/value | `AssumptionsManager.get` and cashflow generator. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L29-L41] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L233-L265] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L489-L514] |
| Oil deck and differential | YYYY-MM → USD/bbl; differential added to price | Missing month silently defaults to 75.0 USD/bbl; differential defaults to zero | `calculate_revenue`. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L266-L297] |
| Optional gas deck | YYYY-MM → realized USD/Mcf | Finite, nonnegative price and volume every production month; zero permitted; no deck leaves gas unpriced | `monthly_gas_revenue`; caller supplies any heating-value conversion or escalation. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/gas_revenue.py:L9-L44] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L530-L544] |
| Fiscal YAML | Schema 1; royalty fraction dimensionless; sliding-scale rate bbl/day | Exact four development keys for flat model, fractions in [0, 1]; ordered finite thresholds and final unbounded band; provenance strings required | `validate_deck`, `_validate_royalty`, `_validate_bands`. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/schema.py:L72-L163] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/schema.py:L166-L233] |
| Water depth / metadata | Classifier ft; metadata transform accepts m | `<500` ft dry; `[500,6000)` ft subsea15; `>=6000` ft subsea20; missing → unknown; mapping transforms are explicit | `classify_dev_system_by_depth`, `dev_system_from_water_depth_m`, `FieldMetaMapping`. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L85-L116] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/field_concept_normalizer.py:L78-L87] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/field_concept_normalizer.py:L145-L170] |
| Excel assumptions / oil prices | Assumption column units above; `year_month`, `wti_price` USD/bbl | Default sheets `assumptions` and `WTI`; assumptions loader transposes when `DEV_SYSTEM` and more than two columns exist | `AssumptionsManager.from_excel`, `PriceDeckManager.from_excel/get_price`. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L146-L195] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L365-L405] |
| Durable workflow configuration | CSV `cashflow` column; explicit common currency and period required by consumer | Router defaults to annual and rate 0.10; CSV is the only supported cashflow source | `project_economics._run_field_npv`, `_read_cashflows`. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L38-L48] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L148-L162] |

### Outputs

| Output | Unit / convention and limitations | Implementation |
| --- | --- | --- |
| `MONTHLY_OIL_BBL`, `MONTHLY_WATER_BBL`, `MONTHLY_GAS_MCF` | Monthly summed bbl/bbl/Mcf; raw processor uses pandas monthly Period; country contract uses string | [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L75-L101] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/contract.py:L116-L127] |
| `FIRST_OIL_DATE`, `CUMULATIVE_OIL_BBL`, `WATER_CUT` | First date at or above threshold (default 10 bbl); first-oil cumulative sum excludes below-threshold rows; water cut is dimensionless water/liquid | [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L103-L137] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L151-L164] |
| Monthly cashflow rows | Revenue/cost labels USD; net = gross revenue minus royalty and five cost components; actual CAPEX scaling is defective | [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L60-L94] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L562-L587] |
| NPV / MIRR / IRR / payback | NPV retains currency unit; rates dimensionless; payback is a zero-based discrete index and years, infinite if never reached; aggregate errors become None plus error fields | [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L159-L166] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L223-L276] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L367-L406] |
| CSV / JSON workflow files | Summary, metrics and sensitivity matrix; JSON maps nonfinite floating values to null; no unit-conversion layer | [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L53-L82] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L126-L146] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L172-L181] |
| Excel workbook | Summary, monthly cashflow and optional production/CAPEX sheets; currency/discount labels are fixed presentation strings, not evidence of conversion | [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/reports/excel_generator.py:L122-L140] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/reports/excel_generator.py:L227-L250] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/reports/excel_generator.py:L424-L442] |

No spatial coordinate or phase convention is used by the financial operations above; the relevant origin is the first cashflow index, with a separate re-origin for trimmed calculations. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L159-L200]

## 3. Method and governing standards

| Method | Implemented rule | Reference / qualification |
| --- | --- | --- |
| NPV | Sum `C[t]/(1+r_period)^t`; monthly rate `(1+r_annual)^(1/12)-1`; annual rate unchanged | Code-defined formula, with time zero included; no standards clause cited by the function. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L149-L166] |
| Trimmed NPV / monthly MIRR | Endpoints use `abs(C)>1e-6`; preserve intermediate zeros; MIRR compounds positives forward, discounts negatives back, then annualizes monthly return | Compatibility implementation; do not treat the Excel label as independently checked vendor behaviour. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L72-L115] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L192-L200] |
| IRR / payback | `numpy_financial.irr`; monthly compounding to annual; payback is first nonnegative cumulative sum, without interpolation | Algorithm and discrete convention. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L223-L276] |
| Revenue and cost | Oil volume × realized oil price; optional gas volume × explicit gas price; day count × rig rate; well count × SURF unit cost; host cost evenly allocated backwards including first-oil month | Component methods do not establish completeness of generator cost lines. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L192-L297] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/gas_revenue.py:L24-L34] |
| Royalty | Sliding scale selects first inclusive threshold; oil rate is monthly oil volume/calendar days; flat/none paths use explicit argument, then deck, then assumptions | Current royalty behaviour, including leap-year day counts; no income-tax computation in this path. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/terms.py:L80-L109] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L305-L385] |
| Forecast | Exponential uses effective annual decline converted to monthly; hyperbolic uses years and nominal initial decline, with exponential branch at `b=0` | Distinct decline-rate conventions; no published calibration is asserted. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L300-L353] |
| Fiscal provenance | Loader checks required nonempty strings and schema; the metadata-mutation test establishes unchanged royalty output for changes to fiscal currency, discount and price marker | Provenance presence does not establish source authority or current law. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/schema.py:L187-L233] [tests/unit/project_economics/fiscal/test_cashflow_fiscal.py:L59-L73] |

Reference class: repository algorithms and compatibility tests; no governing engineering standard or standards-derived `Citation` sidecar is identified in these implementing functions. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L25-L115] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L167-L297]

UNVERIFIED: U2 — legal correctness, current applicability and effective dates of the shipped fiscal assumptions are not checked against their external sources; the YAML provenance is a reference lead, not acceptance evidence. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/decks/us_gom.yml:L26-L33] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/decks/norway.yml:L21-L28] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/decks/uk.yml:L25-L32]

## 4. Validated worked examples

Status fields are reserved for the recorded offline executions at the header pin. Use the synthetic monetary unit USD consistently within each case; these are algorithm checks, not field economics qualifications.

| Case / kind | Independent basis or regression source; input | Expected / tolerance and basis | Existing test node ID | BASE / AFTER |
| --- | --- | --- | --- | --- |
| V1 validated, closed form | At zero rate the discounted sum equals the arithmetic sum; inline array `[-1000,300,300,300,300]` | 200.0 USD; existing assertion explicitly supplies `abs=1e-6` USD; H1 separately requires absolute residual ≤1e-6 USD | `tests/unit/project_economics/test_financial.py::TestCalculateNpv::test_zero_discount_rate` [tests/unit/project_economics/test_financial.py:L107-L111] | PASS / PASS |
| V2 validated, closed form | One annual period: `-1000+1100/(1+r)=0`, hence `r=0.1`; inline array | Annual IRR 0.1 (1); existing `np.isclose` assertion explicitly sets atol 0.001 (1) | `tests/unit/project_economics/unit/test_financial.py::TestIRR::test_basic_irr_calculation` [tests/unit/project_economics/unit/test_financial.py:L154-L161] | PASS / PASS |
| V3 validated, closed form | Annual array `[-1000,500,500,500]`, annual rate 0.10; sum discounted at t = 0–3 | 243.426 USD; existing `np.isclose` sets atol 0.01 USD (default rtol also applies); separate hand probe requires absolute residual ≤0.01 USD | `tests/unit/project_economics/validation/test_against_original.py::TestNumericalAccuracy::test_npv_precision` [tests/unit/project_economics/validation/test_against_original.py:L270-L282] | Execution recorded in the correction record below |
| V4 validated, closed form | Monthly array: −1000 USD at t = 0, zeros at t = 1–11, +1100 USD at t = 12; annual rate 0.10 | NPV 0 USD; absolute residual ≤1e-9 USD; `(1+r_month)^12=1.10` | Separate arithmetic probe of `calculate_npv`, not a committed pytest node; [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L149-L166] | Execution recorded in the correction record below |
| R1 regression | Padded versus unpadded stream, same implementation | Monthly and annual MIRR agree under the existing `assert_allclose` assertions, explicitly set rtol 1e-6 (1) | `tests/unit/project_economics/unit/test_financial.py::TestExcelLikeMIRR::test_mirr_with_zero_padding` [tests/unit/project_economics/unit/test_financial.py:L39-L49] | PASS / PASS |
| R2 regression | Decked versus deckless engine, inline production/price/timeline fixture; no independent economic answer | Same row counts, dates and all nine component values across four development-system keys; exact equality in native component units | `tests/unit/project_economics/fiscal/test_deck_parity.py::test_deckless_vs_us_gom_identical_component_vectors` [tests/unit/project_economics/fiscal/test_deck_parity.py:L22-L69] | PASS / PASS |

Original-code and captured-output comparisons are regression candidates only; the nominal published MIRR example asserts positivity rather than matching its cited value, and the golden comparison only checks nonempty output. [tests/unit/project_economics/validation/test_against_original.py:L58-L72] [tests/unit/project_economics/validation/test_against_original.py:L252-L264] [tests/unit/project_economics/validation/test_against_original.py:L284-L297]

## 5. QA gates

Gate applicability: AQG r0 §10, Python calculations row; G5 applies to every family. Proposed checks below require retained inputs, node outcomes and source revision before a calculation is qualified.

| Gate | Applicability / route |
| --- | --- |
| G0 | Applicable: production schemas, month keys, gas units and fiscal provenance; checks I1–I6 and E1 |
| G1 | Applicable: Python import and offline pytest routes; no external program deck is generated; checks L1–L2 |
| G2 | Applicable: independently evaluated arithmetic and dimensional reconciliation; checks H1–H6 |
| G3 | NOT_APPLICABLE: no time-domain dynamics model in the cited monthly economic generator. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L456-L589] |
| G4 | NOT_APPLICABLE: no body/mesh/diffraction computation in the cited generator. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L456-L589] |
| G5 | Applicable: module-output QA appendix and result accounting; checks E2–E3 |

| Check | Executable route / quantity | Proposed numeric pass criterion and unit | Evidence / current disposition | Gate |
| --- | --- | --- | --- | --- |
| I1 | `to_project_economics_production`; `test_maps_to_exact_project_economics_columns`, `test_bad_month_rejected` | Exactly 5 columns; 0 accepted month-13 rows; 2 valid fixture rows | Existing assertions. [tests/unit/project_economics/adapters/test_contract.py:L40-L43] [tests/unit/project_economics/adapters/test_contract.py:L100-L111] | G0 |
| I2 | `monthly_gas_revenue` via `test_invalid_gas_price_is_rejected`, `test_invalid_gas_volume_is_rejected`, `test_gas_deck_requires_volume_column_and_unique_periods` | 0 accepted negative/nonfinite USD/Mcf prices or Mcf volumes; 0 accepted duplicate month keys | Existing rejection assertions; oil-only path needs the same completeness check separately. [tests/unit/project_economics/analysis/test_gas_cashflow.py:L85-L117] | G0 |
| I3 | `validate_deck`; `test_unknown_top_level_field_rejected`, `test_provenance_fields_required_nonempty` | 0 accepted unknown keys; 0 blank required provenance strings across 4 fields | Existing schema assertions, not a legal-source check. [tests/unit/project_economics/fiscal/test_terms.py:L98-L109] [tests/unit/project_economics/fiscal/test_terms.py:L155-L169] | G0 |
| I4 | `classify_dev_system_by_depth`, `dev_system_from_water_depth_m`; boundary tests | 0 classification mismatches at 500 ft and 6000 ft; 0 mismatches across the 5 tested metre-input cases, including missing and comma-formatted values | Existing boundary assertions. [tests/unit/project_economics/core/test_config.py:L85-L95] [tests/unit/project_economics/adapters/test_field_concept_normalizer.py:L50-L55] | G0 |
| I5 | Join every production month to the oil-price deck before `calculate_revenue` | Production months without a price key: 0 (count); months using the 75.0 USD/bbl fallback: 0 (count) | Proposed input audit; no rejecting check exists in the generator; the fallback regression is not qualification. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L291-L295] [tests/unit/project_economics/analysis/test_cashflow.py:L209-L215] | G0 |
| I6 | Compare each development-system royalty with the percentage stated in the same deck provenance | Absolute rate residual ≤1e-6 (fraction) for every key; 0 keys lacking an explicit provenance mapping (count) | FAIL by internal consistency inspection: dry agrees; subsea15, subsea20 and default differ by 0.0005 (fraction), 0.3% relative. No legal-source claim; #736. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/decks/us_gom.yml:L16-L27] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L31-L36] | G0 |
| L1 | `test_project_economics_public_api_surface`, `test_fiscal_decks_ship_as_package_data` | 0 missing public symbols among 6; 3 readable deck files | Imports/resource checks. [tests/unit/project_economics/test_packaging.py:L40-L61] | G1 |
| L2 | Full module tests and contracts using the execution record in section 10 | 447 collected; errors 0; failures 0 except the named 50.0 ms timing node, issue pending (5); skipped 2 with reasons (count); all 4 original section-4 nodes executed | Distinguish unchanged baseline failures and missing fixtures; they do not clear engineering results | G1 |
| H1 | `calculate_npv`, V1 hand sum | Absolute difference ≤1e-6 USD from 200.0 USD | Closed-form node V1; the separate strict arithmetic probe returned exactly 200.0 USD at the code pin, PASS. [tests/unit/project_economics/test_financial.py:L107-L111] | G2 |
| H2 | `calculate_irr`, V2 hand root | Proposed absolute difference ≤0.001 (1) from 0.1, in addition to the existing assertion | Closed-form node V2; an additional absolute bound, without relaxing the existing test; the separate arithmetic probe passed at the code pin. [tests/unit/project_economics/unit/test_financial.py:L154-L161] | G2 |
| H3 | Inspect `generate_monthly_cashflow` dimensional route: sum host/drilling USD fields versus million-USD component totals converted by 1e6 | Absolute residual ≤0.01 USD for each nonzero capital total; fixed/SURF cost coverage: 0 omitted required categories | FAIL by source inspection: direct assignments, fixed/facilities zero; no detection test exists; issue pending (1). Reference route: section-9 row (a), which converts million USD and includes facilities/fixed OPEX. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L489-L514] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L562-L571] | G2 |
| H4 | Inspect annual `calculate_all_metrics` MIRR route against one-period root with array `[-1000,1100]` | Absolute annual-rate residual ≤0.001 (1) from 0.1 | FAIL: arithmetic probe returned annual MIRR 213.8% against the 10.0% closed-form target; source inspection confirms monthly annualization by power 12; no annual MIRR detection test exists; issue pending (2). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L85-L113] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L378-L386] | G2 |
| H5 | `calculate_npv`, V3 annual closed form at 10.0% | Absolute residual ≤0.01 USD from 243.426 USD | Existing precision node plus strict hand probe; correction execution below. [tests/unit/project_economics/validation/test_against_original.py:L270-L282] | G2 |
| H6 | `calculate_npv`, V4 monthly hand value at 10.0% annual | Absolute NPV ≤1e-9 USD | Separate hand probe; correction execution below. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L149-L166] | G2 |
| E1 | Resolve pack source references using `git show` at the pin; inspect 10 selected supporting ranges | 0 absent files, 0 out-of-range citations; 10/10 semantic matches | Citation resolver and manual sample record, retained with the review evidence | G0 |
| E2 | Reconcile pytest node outcomes and input digests with the pin, pack and issue drafts | 6/6 example outcomes including the two hand probes; 0 unaccounted test outcomes; 0 input digest mismatches | BASE/AFTER records and SHA-256 inventory, retained with the review evidence | G5 |
| E3 | Audit every `{label}_summary.json`, `{label}_metrics.csv` from `project_economics._run_field_npv` and every `ProjectEconomicsReportBuilder` workbook against an appendix generated from I, L and H records | Metric fields without a PASS record: 0 (count); unflagged `mirr_annual` values for `period: annual` while H4 is open: 0 (count); fingerprint mismatches: 0 (count) | Proposed output qualification, not implemented: retain input `cashflows.csv` SHA-256, period, annual discount rate, cashflow count, per-metric check IDs/statuses, and code revision; embed the appendix in JSON/workbooks and link the identical appendix from CSV. In-memory workbook inputs need retained canonical cashflow CSV bytes. Current writers emit no such appendix, so G5 remains OPEN, issue pending (3). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L53-L77] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/reports/excel_generator.py:L376-L442] | G5 |

G2 is not cleared for complete economic use: H3 and H4 remain failed checks with scoped issue drafts. V1 and V2 test isolated primitives and must not be used to qualify the defective generator or aggregate annual-MIRR path. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L562-L586] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L378-L386]

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom / cause | Detection or absence | Record / disposition |
| --- | --- | --- |
| Missing oil prices become an assumed constant; missing assumptions can select the default row or scalar without provenance | I5: 0 missing month keys and 0 fallback-priced months (count); existing `test_missing_price_uses_default` preserves the fallback, rather than rejecting incomplete pricing | Issue pending (1), source observations at the header pin. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L291-L295] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/config.py:L237-L265] [tests/unit/project_economics/analysis/test_cashflow.py:L209-L215] |
| Skipped baseline comparisons and historical examples can overstate assurance | SKIPPED: unconditional golden-baseline placeholder (`pass`); run-time skip: sheet-name mismatch against an existing workbook; inspect exact node outcomes | #349; #1044; issue pending (3). [tests/unit/project_economics/unit/test_financial.py:L335-L340] [tests/unit/project_economics/validation/test_against_original.py:L252-L264] [tests/unit/project_economics/validation/test_v30_determinism.py:L36-L43] |
| Fixed OPEX and facilities CAPEX remain zero; million-USD capital totals enter USD-labelled rows without conversion | H3 FAIL; no end-to-end dimensional/completeness detection check exists | Issue pending (1). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L489-L514] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L562-L571] |
| Duplicate oil-only month keys overwrite earlier rows through `to_dict`; country normalizer does not aggregate entities | Review single-entity, unique-month input invariant; gas-enabled duplicate detection exists in I2; oil-only loss detection absent | Issue pending (1). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/contract.py:L116-L127] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L516-L522] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/gas_revenue.py:L20-L22] |
| No drilling timeline yields zero capital; a warning is emitted, not an inferred duration | `test_honesty_guard_warns_on_empty_drilling_timeline`: warning count ≥1, drilling capital 0 USD | #783 is the open source-gap tracking issue; #1075 is closed historical context for the removed calendar-duration estimator. [tests/unit/project_economics/adapters/test_conformance.py:L106-L124] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/__init__.py:L6-L20] |
| Public BSEE adapter emits `MONTHLY_*_VOLUME`, but generator reads `MONTHLY_OIL_BBL` | No direct adapter→generator detection check exists; separate schema tests preserve incompatible outputs | Issue 784 (#784). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/bsee_adapter.py:L301-L310] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L517-L520] [tests/unit/project_economics/test_bsee_adapter.py:L179-L185] |
| Aggregate annual metrics invoke monthly MIRR regardless of `period` | H4 FAIL; `test_annual_period` only checks period metadata and nonempty NPV | Issue pending (2). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L378-L386] [tests/unit/project_economics/test_financial.py:L258-L262] |
| Single-sign MIRR becomes NaN; aggregate metrics retain errors/None; workflow JSON converts nonfinite floats to null | `test_all_positive_returns_nan`, `test_with_bad_cashflows`; consumers must check per-metric state | Issue 832 (#832), economic-function consolidation/parity context. [tests/unit/project_economics/test_financial.py:L46-L56] [tests/unit/project_economics/test_financial.py:L264-L268] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/project_economics.py:L172-L181] |
| Fiscal currency, price marker and discount metadata mutation leaves the tested royalty output unchanged | `test_declarative_fields_are_not_consumed`: 0 royalty differences after metadata mutation | Issue 736 (#736); no after-tax qualification. [tests/unit/project_economics/fiscal/test_cashflow_fiscal.py:L59-L73] |
| Optional production columns are accepted at construction but cumulative/summary paths later require water or gas columns | No missing-optional-column end-to-end detection check exists | Issue pending (1). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L52-L56] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L151-L158] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/production.py:L185-L195] |
| Excel summary labels NPV as a fixed discount and million-USD value without rescaling input | No rate/currency label-consistency detection check exists; current report tests exercise formatting and initialization only | Issue pending (1). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/reports/excel_generator.py:L122-L140] [tests/unit/project_economics/reports/test_excel_generator.py:L27-L72] |
| Runtime qualification can fail the existing 50.0 ms assertion without a calculation change | Existing `tests/unit/project_economics/unit/test_financial.py::TestPerformance::test_all_metrics_performance`; BASE FAIL, AFTER PASS; no cause established | Issue pending (5). [tests/unit/project_economics/unit/test_financial.py:L363-L375] |
| Deck royalty differs from its own provenance and the parallel cross-basin table | I6 FAIL: 3 of 4 development-system keys differ by 0.0005 (fraction), 0.3% relative; exact parity alone preserves the discrepancy | #736; section-9 row (h). [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/decks/us_gom.yml:L16-L27] [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L19-L28] |
| Acronym expansion differs between the root docstring and member metadata | No documentation consistency detection check exists | Issue pending (6); compare the two descriptions without adopting either expansion. [src/worldenergydata/__init__.py:L16] [packages/worldenergydata-project_economics/pyproject.toml:L8] |

Dates for the source observations above: 2026-10-15; issue event dates remain those of the linked records. These are current code observations, not an assertion that every backlog item is a past incident.

## 7. Lessons log

Append new entries; do not overwrite earlier entries. Use public evidence IDs rather than execution identifiers.

| Date | Evidence ID | Lesson / pack change | Shared-log entry |
| --- | --- | --- | --- |
| 2026-10-15 | V1, V2, R1, R2 | Separate isolated arithmetic qualification from implementation parity; section 4 records both kinds. [tests/unit/project_economics/test_financial.py:L107-L111] [tests/unit/project_economics/unit/test_financial.py:L154-L161] [tests/unit/project_economics/fiscal/test_deck_parity.py:L48-L69] | Pending, issue pending (3) |
| 2026-10-15 | H3, H4 | Passing isolated metrics does not establish monetary scaling or annual aggregate MIRR; sections 5–6 retain failures. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/analysis/cashflow.py:L562-L571] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L378-L386] | Pending, issue pending (3) |

## 8. Ownership

Review assignment for this draft: calculations quality manager for the data pipeline; deputy role: to be assigned by the maintainer. Producing roles: module documentation and data analysis. Escalate missing evidence, failed checks, altered tolerance or fiscal-basis changes to the quality manager; cross-family changes require the maintainer's disposition. These are review assignments and requirements, not completed approvals.

UNVERIFIED: U3 — a named deputy and a durable data-family appointment are not established; maintain DRAFT status until an independent provider records clearance; issue pending (3).

## 9. Dependencies

The member declares core, cost, NumPy, numpy-financial, pandas, openpyxl and PyYAML dependencies; the metadata normalizer additionally imports `field_development` from the root distribution at runtime. [packages/worldenergydata-project_economics/pyproject.toml:L38-L46] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/adapters/field_concept_normalizer.py:L31-L36]

Rig-day calculation is deliberately outside project_economics to avoid a dependency cycle; callers pass drilling timelines into the engine, rather than importing the BSEE implementation from project_economics. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/data/__init__.py:L6-L20]

Repository-wide method search includes `scripts/`, not only package source; the following parallel implementations require explicit parity before substituting one for another. [scripts/all_fields_economics.py:L73-L87] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L137-L181] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L427-L484]

| Other implementation / consumer | Distinction and evidence |
| --- | --- |
| `economics.dcf` | Separate NPV over net component cashflow and separate finance/reinvestment MIRR. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L137-L244] |
| BSEE financial calculator | NPV accepts a monthly rate directly; separate MIRR function. [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L427-L484] |
| Lower-tertiary reproducer | Separate trimmed monthly MIRR implementation; regression context, not an independent standard. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L273-L287] |
| `scripts/all_fields_economics.py` | Separate trimmed NPV and annualized MIRR. [scripts/all_fields_economics.py:L73-L87] |
| Report-generation script | Builds annual arrays and uses separate annual NPV/IRR/payback calls, but default MIRR call; interfaces touched by H4. [scripts/gtm/generate_project_economics_gtm_report.py:L88-L130] |
| Disclosure analytics | Cost-side loaders and comparability-gated benchmark invoked lazily through project_economics. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/api.py:L301-L344] |

Additional repository inventory (a–t); every source range below was read at the code pin. Restricted locators use opaque private-sidecar entries.

| Item / relationship | Distinction and evidence |
| --- | --- |
| (a) Legacy original | Own monthly MIRR; reference route for H3: million-USD conversion, facilities and fixed OPEX. [docs/modules/bsee/analysis/production/project_economics_V30/generate_financial_summary_V30.py:L185-L195] [docs/modules/bsee/analysis/production/project_economics_V30/generate_financial_summary_V30.py:L328-L329] [docs/modules/bsee/analysis/production/project_economics_V30/generate_financial_summary_V30.py:L359-L379] |
| (b) Legacy archived NPV | Separate archived calculator class. [_archive/bsee/analysis/legacy/api12_economics.py:L127-L140] |
| (c) Parallel lower-tertiary NPV | Own monthly discounting; outputs million USD. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/npv.py:L165-L206] |
| (d) Parallel Norway NPV | Own annual discount sum and tax path. [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L129-L140] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L335-L345] [packages/worldenergydata-sodir/src/worldenergydata/sodir/npv_norway.py:L550-L557] |
| (e) Parallel drilling economics | Cost-only batch versus standalone totals, labelled NPV; the body sums costs at time zero and does not use the supplied discount rate. [packages/worldenergydata-drilling/src/worldenergydata/drilling/batch_economics/economics.py:L142-L194] |
| (f) Parallel parametric NPV | Recovers discount exponents and re-discounts a timeline. [scripts/lower_tertiary/run_parametric_economics.py:L85-L104] |
| (g) Parallel restricted script | 1 discovery file with an identifying name; own `excel_mirr` and `npv_trimmed`, private sidecar R7-02:L96-L118 at the code pin; public codenaming pending, issue pending (3). |
| (h) Parallel cross-basin fiscal table | Separate royalty/tax stack (#832); GoM royalty 0.1875 differs from the deck/config 0.188 by 0.0005 (fraction), 0.3% relative; I6 records internal inconsistency. [packages/worldenergydata-production/src/worldenergydata/production/unified/cross_basin.py:L16-L46] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/decks/us_gom.yml:L16-L27] |
| (i) Parallel country fiscal methods | Separate UK, Brazil, West Africa and US formulae; no equivalence or legal qualification asserted. [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L34-L96] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L162] [packages/worldenergydata-west_africa/src/worldenergydata/west_africa/analysis/field_economics.py:L126-L218] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/us_fiscal.py:L56-L217] |
| (j) Parallel decline methods and helper | Production, UK, Brazil, Norway and US have separate decline fitting/formulae; BSEE `DeclineAnalysis.fit_all_models` delegates to the listed Norway forecaster, so it is a helper. [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L60-L79] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/forecasting/decline_analysis.py:L72-L140] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/production/decline_curves.py:L129-L195] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L100-L166] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L112-L235] [packages/worldenergydata-eia_us/src/worldenergydata/eia_us/analysis/basin_decline.py:L43-L60] |
| (k) Parallel production aggregation | Own cumulative sums and percent water cut; module water cut is a fraction. [scripts/project_economics/run_project_economics_production_retrieval.py:L163-L201] |
| (l) Consumer: CLI | Calls NPV, MIRR, IRR, aggregate metrics and cashflow engine. [src/worldenergydata/cli/commands/project_economics.py:L103-L109] [src/worldenergydata/cli/commands/project_economics.py:L190-L196] [src/worldenergydata/cli/commands/project_economics.py:L273-L277] [src/worldenergydata/cli/commands/project_economics.py:L348-L354] [src/worldenergydata/cli/commands/project_economics.py:L491-L503] |
| (m) Consumer: engine router | Instantiates the project_economics router. [src/worldenergydata/engine.py:L149-L153] |
| (n) Consumers: six country reference chains | Australia, Brazil, Canada, Norway, Spain and UK adapters feed the common engine; first stack in #832. [packages/worldenergydata-australia/src/worldenergydata/australia/reference_chain.py:L10-L29] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L10-L29] [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L10-L29] [packages/worldenergydata-sodir/src/worldenergydata/sodir/reference_chain.py:L16-L27] [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L10-L29] [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L16-L27] |
| (o) Consumer: BSEE production economics | Imports shared assumptions and NPV. [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/production_api12.py:L18-L22] |
| (p) Consumers: lower-tertiary portfolio | Uses economics and disclosure APIs. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py:L31-L38] [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py:L40-L48] |
| (q) Consumers: field-development integration/costs | Depth classification, assumptions and coarse economics. [src/worldenergydata/field_development/integrations.py:L111-L160] [src/worldenergydata/field_development/cost_estimator.py:L209-L218] |
| (r) Consumer: unified benchmark | Uses project_economics depth classification. [packages/worldenergydata-production/src/worldenergydata/production/unified/benchmark_report.py:L150-L160] |
| (s) Consumers: notebooks and workflows | Shared API examples, legacy import example and annual CSV workflow configuration; reading inventory below. [notebooks/quickstart_project_economics.py:L12-L33] [notebooks/lease_npv_walkthrough.py:L37-L45] [examples/project_economics_complete_workflow.py:L29-L45] [examples/workflows/project_economics-field-npv/input.yml:L14-L22] |
| (t) Consumer guidance: economics skill | Documents financial metrics, cashflows, forecasting and reporting; guidance rather than an implementation. [.claude/skills/project_economics-economics/SKILL.md:L3-L20] |

Map inventory: `digitalmodel` implementation map `docs/registry/implementation-map.yaml` at `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954`, contains 13 families and 0 implementation rows in the header package. The in-package inventory is empty; counted-family grep is NOT_APPLICABLE because there is no mapped family with a row in this package. No path signal or case-sensitive Python `re` search is applied without a counted family. The broader repository inventory above remains useful even though it does not alter that result.

Map follow-up: add the section-3 families NPV/trimmed NPV, MIRR, IRR/payback, cashflow/royalty, production forecasting and fiscal-provenance validation with in-package rows before counting them. Inventory outside the package is a map gap; #832 and #1088 track economic-surface consolidation.

Consolidation/parity follow-up: #832 and #1088 (single NPV surface). No solver binary or solver-program interface is required by the cited economic primitives. [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L84-L115] [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/core/financial.py:L149-L166]

UNVERIFIED: U4 — inventory rows and version compatibility for every upstream/downstream consumer are not exhaustively qualified; issue pending (3).

## 10. Coverage and open items

### Reading inventory

Source coverage: all 20 Python files under the module, its two READMEs, package metadata and all three fiscal YAML decks. Test source coverage: 21 test files under `tests/unit/project_economics`, the integration copy under `tests/modules/project_economics`, and CLI tests; 393 unit nodes were collected, plus 9 integration-copy nodes, 37 CLI nodes and 8 contract nodes; exact outcomes are recorded below.

READ module documentation: `docs/modules/project_economics/USER-GUIDE.md`, `VALIDATION-REPORT.md`, `DEPLOYMENT-CHECKLIST.md`, `country-adapter-checklist.md`; also `docs/domains/field-development/gas-revenue.md`. [docs/modules/project_economics/USER-GUIDE.md:L1-L12] [docs/modules/project_economics/VALIDATION-REPORT.md:L1-L20] [docs/modules/project_economics/DEPLOYMENT-CHECKLIST.md:L1-L14] [docs/modules/project_economics/country-adapter-checklist.md:L1-L18] [docs/domains/field-development/gas-revenue.md:L1-L20]

READ additional usage guidance and examples (source ranges, not executed workflows): [notebooks/quickstart_project_economics.py:L12-L33] [notebooks/lease_npv_walkthrough.py:L37-L45] [examples/project_economics_complete_workflow.py:L29-L45] [examples/workflows/project_economics-field-npv/input.yml:L14-L22] [.claude/skills/project_economics-economics/SKILL.md:L3-L20] The skill describes a historical configuration surface; the complete-workflow example retains legacy import paths, so neither establishes current API compatibility.

Markdown documentation mentioning project_economics was indexed across `docs/`; broader historical/planning/cross-module review is deferred under the bounded main-path scope, with no claim of exhaustive historical-document reading. The public inventory below uses source references and neutral folder groups; restricted names are not reproduced. Issue pending (3).

| Indexed documentation | Coverage |
| --- | --- |
| [docs/CLI.md:L295-L297] | INDEXED; broader review deferred, issue pending (3) |
| [docs/COMMANDS.md:L5-L7] | INDEXED; broader review deferred, issue pending (3) |
| [docs/MIGRATION_GUIDE.md:L58-L60] | INDEXED; broader review deferred, issue pending (3) |
| [docs/adr/0001-domain-package-split.md:L40-L42] | INDEXED; broader review deferred, issue pending (3) |
| [docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.md:L19-L21] | INDEXED; broader review deferred, issue pending (3) |
| [docs/data-sources/bsee/analysis/well-identifier-grain.md:L31-L33] | INDEXED; broader review deferred, issue pending (3) |
| [docs/data-sources/bsee/data/WELL_ACTIVITY_CD/publication_status.md:L12-L14] | INDEXED; broader review deferred, issue pending (3) |
| [docs/domains/field-development/gas-revenue.md:L3-L5] | READ |
| [docs/guides/QUICK_START.md:L30-L32] | INDEXED; broader review deferred, issue pending (3) |
| [docs/guides/user_prompt.md:L28-L30] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/bsee/analysis/production/project_economics_V30/QUICKSTART.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/bsee/analysis/production/project_economics_V30/README_PRODUCTION_RETRIEVAL.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/bsee/analysis/production/lt_v30_v50_code_reconciliation.md:L110-L112] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/bsee/communications/email-review/reviewed/2026-07-08-project_economics-canonicalization.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/cost/REFRESH_PROCEDURE.md:L8-L10] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/project_economics/DEPLOYMENT-CHECKLIST.md:L1-L3] | READ |
| [docs/modules/project_economics/USER-GUIDE.md:L1-L3] | READ |
| [docs/modules/project_economics/VALIDATION-REPORT.md:L1-L3] | READ |
| [docs/modules/project_economics/country-adapter-checklist.md:L1-L3] | READ |
| [docs/plans/2026-04-21-issue-334-annual-operator-disclosures-dataset.md:L19-L21] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-04-22-issue-335-disclosure-to-costdatapoint-linkage-model.md:L69-L71] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-04-22-issue-338-annual-disclosure-analytics-views-and-consumer-integration.md:L16-L18] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L14-L16] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-04-27-issue-355-align-cli-docs-examples.md:L14-L16] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-03-issue-375-per-field-economics-10-lt-fields.md:L15-L17] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-03-issue-376-cross-field-analytics-lt.md:L17-L19] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-04-issue-143-bsee-field-econ-calibrated.md:L5-L7] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-04-issue-316-mypy-incremental.md:L27-L29] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-04-issue-339-legacy-npv-test-resolution.md:L15-L17] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L17-L19] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-04-issue-352-cli-smoke-verification.md:L21-L23] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-04-issue-361-calc-citation-contract.md:L14-L16] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-04-issue-367-api12-npv-migration.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L83-L85] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-03-issue-714-project_economics-source-agnostic.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-03-issue-732-texas-rrc-underpressured-screen.md:L43-L45] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-03-issue-740-oklahoma-occ-pressure-observations.md:L38-L40] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-03-issue-745-colorado-ecmc-wellhead-pressure-observations.md:L41-L43] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-04-issue-715-adapter-contract.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-04-issue-716-norway-sodir-reference-chain.md:L14-L16] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-04-issue-717-ukcs-nsta-reference-chain.md:L53-L55] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L47-L49] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-04-issue-749-colorado-ecmc-pressure-source-discovery.md:L45-L47] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-04-issue-751-colorado-ecmc-form5a-ingest.md:L46-L48] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-05-issue-810-spain-cores-field-development-report.md:L144-L146] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-06-issue-807-spain-cores-crude-density-api-table.md:L149-L151] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-16-issue-1038-cost-map-program.md:L16-L18] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-16-issue-1044-project_economics-workbook-reconciliation.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/2026-07-18-issue-1039-manifest-lineage-hotfix.md:L46-L48] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/README.md:L107-L109] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/execution-packs/2026-04-22-approved-cost-wave/future-issues-and-exit-handoff.md:L15-L17] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/execution-packs/2026-04-22-approved-cost-wave/master-plan.md:L9-L11] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-335.md:L23-L25] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-337.md:L27-L29] | INDEXED; broader review deferred, issue pending (3) |
| [docs/plans/execution-packs/2026-04-22-approved-cost-wave/stream-338.md:L5-L7] | INDEXED; broader review deferred, issue pending (3) |
| [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L13-L15] | INDEXED; broader review deferred, issue pending (3) |
| [docs/reports/2026-04-26-worldenergydata-cli-example-smoke-matrix.md:L12-L14] | INDEXED; broader review deferred, issue pending (3) |
| [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L19-L21] | INDEXED; broader review deferred, issue pending (3) |
| [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L66-L68] | INDEXED; broader review deferred, issue pending (3) |
| [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L67-L69] | INDEXED; broader review deferred, issue pending (3) |
| [docs/reports/cli-smoke-report-2026-05-11.md:L18-L20] | INDEXED; broader review deferred, issue pending (3) |
| [docs/reports/data-freshness-scorecard-2026-06-08.md:L10-L12] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/bsee-project_economics-integration-summary.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/docs/research/project_economics-INTEGRATION-STATUS.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/docs/research/project_economics-documentation-review-summary.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/docs/research/project_economics-integration-index.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/project_economics-code-comparison.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/project_economics-executive-summary.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/project_economics-implementation-plan.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/project_economics-quick-reference.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| 1 discovery file with an identifying name; locator in private sidecar R7-01 at the code pin; public codenaming pending | INDEXED; public naming boundary, issue pending (3) |

### Original offline execution record

Environment observation: CPython 3.11.15; code revision as pinned in the header. BASE and AFTER use the ordinary source-resolving `uv run python -m pytest` form, `-q -rA -p no:cacheprovider`, isolated `--basetemp`, scratch JUnit and coverage-database destinations, and `--allow-existing-tree-changes` to preserve the new documentation; default pytest addopts remain active; generated coverage reports and package metadata are removed by explicit file paths after each run.

Selection: `tests/unit/project_economics`, `tests/modules/project_economics/integration/test_end_to_end.py`, `tests/integration/cli/test_project_economics_cli.py`, `tests/contracts`. Existing repository ignore rules remain unchanged; report discovered but unexecuted nodes explicitly.

| Execution | Collected (nodes) | Passed (nodes) | Failed (nodes) | Errors (nodes) | Skipped (nodes) | Qualification status | Revision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BASE | 447 | 444 | 1 | 0 | 2 | SKIPPED: 2 baseline-comparison nodes; reasons below | `e73bda871798429eeb6dda0d16ed5520548d6cad` |
| AFTER | 447 | 445 | 0 | 0 | 2 | SKIPPED: same 2 baseline-comparison nodes | Same code pin, documentation only |

Baseline failure: `tests/unit/project_economics/unit/test_financial.py::TestPerformance::test_all_metrics_performance`, 65.3 ms against `<50.0 ms`; the unchanged assertion is at the pin, issue pending (5). This is an observed failure, not evidence of its cause. [tests/unit/project_economics/unit/test_financial.py:L363-L375]

SKIPPED regression qualification: `tests/unit/project_economics/unit/test_financial.py::TestRegressionAgainstProjectEconomics::test_against_golden_baseline` has the unconditional reason `Requires golden baseline file`, but its body is a placeholder (`pass`) and `config/analysis/lower_tertiary/golden_baseline_v30.yml` exists at the pin; `tests/unit/project_economics/validation/test_against_original.py::TestFinancialOutputComparison::test_compare_with_golden_baseline` skipped because worksheet `Project Summary` was not found in the existing workbook. The implementation reads `Project Summary`, while the captured-output test reads `Project_Summary`; the skip therefore does not establish missing data. [tests/unit/project_economics/unit/test_financial.py:L335-L340] [tests/unit/project_economics/validation/test_against_original.py:L252-L264] [tests/unit/project_economics/validation/test_v30_determinism.py:L36-L43]

Both native outcomes are SKIPPED; NOT_RUN count is 0 because neither requires a licence or solver binary. All four original section-4 nodes passed at BASE and AFTER. The node sets match; the only outcome change is the baseline runtime failure passing AFTER, with no new failure or error. No performance cause is established by this difference. No licence-dependent node was identified in this selection.

### Correction execution record

Only this Markdown file differs from the starting commit `7b591cf2d4278ef304abb31b55fd523da6231730`; calculation code and test assertions still match the header code pin. The starting main reference was `285d65c40896b17ccf44568e59f5b789d59c943e`, with merge base `e73bda871798429eeb6dda0d16ed5520548d6cad`. No main integration was performed.

The local command used `uv run --no-project --with pytest` with declared dependency packages supplied by `--with`, followed by `python -m pytest tests/unit/project_economics tests/modules/project_economics/integration/test_end_to_end.py tests/integration/cli/test_project_economics_cli.py tests/contracts -q -rA -p no:cacheprovider`, isolated `--basetemp`, scratch JUnit, performance and coverage destinations, and `--allow-existing-tree-changes`. Default pytest assertions, ignores and coverage remain active. Environment: CPython 3.12.3; one test process, numerical-library threads limited to one. Initial collection attempts exposed missing dependencies before execution; none is reported as a pass.

| Execution | Collected | Passed | Failed | Errors | SKIPPED | NOT_RUN |
| --- | --- | --- | --- | --- | --- | --- |
| Starting tree, before documentation edits | 447 | 442 | 3 | 0 | 2 | 0 |
| Corrected documentation, completed dependency environment | 447 | 445 | 0 | 0 | 2 | 0 |

The three starting failures were `test_engine_importable`, `test_FileManagement_importable` and `test_WorkingWithYAML_importable` in `tests/contracts/test_assetutilities_engine_contract.py`, each blocked by the missing `webcolors` import in the dependency. Supplying that declared dependency and its import dependencies made all three pass; no contract or dependency source was changed. The two native skips retain the reasons in the original record above. The 50.0 ms timing node passed in both local executions; no performance explanation is inferred.

V1, V2, V3, R1 and R2 passed in both full executions. Separate strict hand probes passed: V3 absolute residual ≤0.01 USD against 243.426 USD; V4 absolute residual ≤1e-9 USD against 0 USD. Synthetic cashflow CSV bytes, SHA-256 digests, periods, rates, counts and unrounded probe results were retained with the execution evidence. I6 inspection confirmed one matching key and three keys differing by 0.0005 (fraction), 0.3% relative; this records a known calculation-input inconsistency, not a failed documentation check. E3 remains a proposed qualification requirement; no output appendix or calculation fix is claimed.

Private sidecar entries R7-01 (one indexed document) and R7-02 (one parallel script) retain restricted locators at the code pin. Public text contains opaque entry IDs only; durable private retention and public codenaming remain under issue pending (3).

### Open register

| Item | Required evidence / disposition | Responsible role | Tracking |
| --- | --- | --- | --- |
| U1 — README claim, unverified | Re-derive historical assurance, coverage and speed claims; no broad maturity assertion from this run | Maintainer | Issue 349 (#349) |
| U2 — fiscal source correctness, unverified | Open authoritative current sources and qualify effective dates before economic application; no legal rates asserted here | Maintainer | Issue 736 (#736) |
| U3 — reviewer/deputy appointment | Assign deputy and record independent clearance, pack index and shared-log entries | Maintainer | issue pending (3) |
| U4 — broader dependency inventory | Complete cross-module inventory/compatibility and historical documentation review beyond the cited main path | Maintainer | issue pending (3); issue 832 (#832) |
| Generator data integrity, completeness, unit labels and fallbacks | H3 and section-6 detection gaps; no module code changed | Maintainer | issue pending (1) |
| Annual aggregate MIRR | H4 and annual callers require a period-correct independent expectation | Maintainer | issue pending (2) |
| Legacy BSEE schema | Add adapter→generator interoperability detection before treating legacy adapter output as ready | Maintainer | Issue 784 (#784) |
| Drilling source availability | Missing source remains explicit; no duration is fabricated | Maintainer | #783 open; #1075 closed (historical context) |
| Historical fixtures and regression qualification | Resolve missing inputs and placeholder/nonempty-only checks; golden outputs remain regressions | Maintainer | Issue 1044 (#1044); issue pending (3) |
| Baseline runtime assertion | Record the existing 50.0 ms criterion and failed node without changing its threshold | Maintainer | issue pending (5). [tests/unit/project_economics/unit/test_financial.py:L363-L375] |
| Acronym documentation consistency | Reconcile root docstring and member metadata; no issue filed in this change | Maintainer | issue pending (6) |
| Wheel exclusion | Existing member `**/*.md` glob matches nested Markdown; exclusion cannot be asserted without an archive check or packaging change, neither included here | Maintainer | issue pending (4). [packages/worldenergydata-project_economics/pyproject.toml:L67-L72] |

Additional acceptance: section 9 records the map revision, empty in-package inventory and the reason the counted-family search is NOT_APPLICABLE. Registry update: not applicable to the inspected tree; no `docs/registry/module-routing.yaml` exists, so no replacement registry is introduced. Quality clearance and final issue-number substitution remain pending.
