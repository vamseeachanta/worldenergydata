# FDAS module knowledge pack

| Header | Value |
| --- | --- |
| Module | `fdas` |
| Repository | `worldenergydata` |
| Path | `packages/worldenergydata-fdas/src/worldenergydata/fdas` |
| Pack revision | 0, 2026-10-15 |
| Code revision | `e73bda871798429eeb6dda0d16ed5520548d6cad` |
| Analysis family | Data pipeline; AQG r0 Python calculations gate set |
| Quality role | Calculations quality manager, pending data quality appointment |
| Status | DRAFT; independent clearance pending |

Use the code revision above for every source citation. Treat the execution records below as observations of the cited test nodes at that revision, rather than as facts established by test source alone. The proposed QA criteria supplement the existing assertions; a passing regression does not clear a known calculation defect.

## 1. Purpose and scope

FDAS implements periodic NPV, trimmed NPV, monthly MIRR, IRR and discrete payback; `EconomicsQuery.npv` converts sequences to arrays before delegation. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L25-L115] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L118-L200] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L203-L276] [packages/worldenergydata-fdas/src/worldenergydata/fdas/api.py:L90-L98]

`ProductionProcessor` aggregates production by identifier and month, detects first oil, computes cumulative volumes and water cut, and creates summaries and pivots; `ProductionForecaster` implements exponential and hyperbolic formulas. [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L58-L137] [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L139-L236] [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L300-L353]

`CashflowEngine` combines production, supplied drilling days, assumptions, oil prices, optional gas prices and a royalty deck into monthly rows; its fixed OPEX, facilities CAPEX and monetary scaling limitations are recorded in section 6. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L456-L589]

`FDAS.router` supports CSV cashflow metrics and an NPV sensitivity matrix, producing CSV and JSON files; `FDASReportBuilder` separately assembles Excel summary and detail sheets. [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L21-L82] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L84-L162] [packages/worldenergydata-fdas/src/worldenergydata/fdas/reports/excel_generator.py:L392-L442]

The country contract normalizes production and metadata; disclosure analytics delegates to the cost package rather than estimating costs within FDAS. [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/contract.py:L75-L127] [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/field_concept_normalizer.py:L145-L170] [packages/worldenergydata-fdas/src/worldenergydata/fdas/api.py:L301-L344]

The member metadata declares version `0.1.0` and Alpha status, while the import module exposes `1.0.0`; these are declarations, not an engineering qualification or a routing maturity rating. [packages/worldenergydata-fdas/pyproject.toml:L5-L22] [packages/worldenergydata-fdas/src/worldenergydata/fdas/__init__.py:L99-L101]

UNVERIFIED: U1 — README claims of complete validation, complete coverage and faster execution are not established as module-wide qualification by this pack; see section 10. [packages/worldenergydata-fdas/src/worldenergydata/fdas/README.md:L7-L17]

## 2. Inputs and outputs

### Inputs

| Input | Unit / convention | Allowed range and default | Source and implementation |
| --- | --- | --- | --- |
| `cashflows`, annual discount rate, `period` | Caller-selected common currency; positive inflow, negative outflow; first element at time zero | Nonempty; NPV rate accepted in [-1, 1]; monthly default or annual; endpoint -1 needs separate qualification | `EconomicsQuery.npv`; no implicit currency conversion. [packages/worldenergydata-fdas/src/worldenergydata/fdas/api.py:L64-L76] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L141-L166] |
| Raw production frame | `PROD_DATE`; oil/water bbl, gas Mcf; grouping identifier | Constructor requires date and oil only; default group `API_WELL_NUMBER`; downstream methods need additional columns | `ProductionProcessor`; no global numeric/range validation. [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L30-L59] [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L151-L164] |
| Unified country production | `year`, `month`, `oil_bbl`, `gas_mcf`, `water_bbl`, `region`, `field_name` | Month 1–12; numeric year/month; empty input produces typed empty; volume coercion can produce NaN | `to_fdas_production`; no aggregation across entities. [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/contract.py:L32-L55] [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/contract.py:L96-L127] |
| Monthly production | `YEAR_MONTH` as YYYY-MM; `MONTHLY_OIL_BBL`; optional `MONTHLY_GAS_MCF` | Supply a single entity with one row per month; oil-only dict conversion otherwise overwrites duplicate months | `CashflowEngine.generate_monthly_cashflow`. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L516-L544] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/gas_revenue.py:L18-L34] |
| Drilling timeline and cost assumptions | `drilling_monthly` days; host/SURF million USD, rig rate million USD/day, variable OPEX USD/bbl | No inferred drilling duration; absent timeline warns and yields zero drilling CAPEX; parameter lookup can fall back to default row/value | `AssumptionsManager.get` and cashflow generator. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/config.py:L29-L41] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/config.py:L233-L265] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L489-L514] |
| Oil deck and differential | YYYY-MM → USD/bbl; differential added to price | Missing month silently defaults to 75.0 USD/bbl; differential defaults to zero | `calculate_revenue`. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L266-L297] |
| Optional gas deck | YYYY-MM → realized USD/Mcf | Finite, nonnegative price and volume every production month; zero permitted; no deck leaves gas unpriced | `monthly_gas_revenue`; caller supplies any heating-value conversion or escalation. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/gas_revenue.py:L9-L44] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L530-L544] |
| Fiscal YAML | Schema 1; royalty fraction dimensionless; sliding-scale rate bbl/day | Exact four development keys for flat model, fractions in [0, 1]; ordered finite thresholds and final unbounded band; provenance strings required | `validate_deck`, `_validate_royalty`, `_validate_bands`. [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/schema.py:L72-L163] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/schema.py:L166-L233] |
| Water depth / metadata | Classifier ft; metadata transform accepts m | `<500` ft dry; `[500,6000)` ft subsea15; `>=6000` ft subsea20; missing → unknown; mapping transforms are explicit | `classify_dev_system_by_depth`, `dev_system_from_water_depth_m`, `FieldMetaMapping`. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/config.py:L85-L116] [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/field_concept_normalizer.py:L78-L87] [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/field_concept_normalizer.py:L145-L170] |
| Excel assumptions / oil prices | Assumption column units above; `year_month`, `wti_price` USD/bbl | Default sheets `assumptions` and `WTI`; assumptions loader transposes when `DEV_SYSTEM` and more than two columns exist | `AssumptionsManager.from_excel`, `PriceDeckManager.from_excel/get_price`. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/config.py:L146-L195] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/config.py:L365-L405] |
| Durable workflow configuration | CSV `cashflow` column; explicit common currency and period required by consumer | Router defaults to annual and rate 0.10; CSV is the only supported cashflow source | `FDAS._run_field_npv`, `_read_cashflows`. [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L38-L48] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L148-L162] |

### Outputs

| Output | Unit / convention and limitations | Implementation |
| --- | --- | --- |
| `MONTHLY_OIL_BBL`, `MONTHLY_WATER_BBL`, `MONTHLY_GAS_MCF` | Monthly summed bbl/bbl/Mcf; raw processor uses pandas monthly Period; country contract uses string | [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L75-L101] [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/contract.py:L116-L127] |
| `FIRST_OIL_DATE`, `CUMULATIVE_OIL_BBL`, `WATER_CUT` | First date at or above threshold (default 10 bbl); first-oil cumulative sum excludes below-threshold rows; water cut is dimensionless water/liquid | [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L103-L137] [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L151-L164] |
| Monthly cashflow rows | Revenue/cost labels USD; net = gross revenue minus royalty and five cost components; actual CAPEX scaling is defective | [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L60-L94] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L562-L587] |
| NPV / MIRR / IRR / payback | NPV retains currency unit; rates dimensionless; payback is a zero-based discrete index and years, infinite if never reached; aggregate errors become None plus error fields | [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L159-L166] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L223-L276] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L367-L406] |
| CSV / JSON workflow files | Summary, metrics and sensitivity matrix; JSON maps nonfinite floating values to null; no unit-conversion layer | [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L53-L82] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L126-L146] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L172-L181] |
| Excel workbook | Summary, monthly cashflow and optional production/CAPEX sheets; currency/discount labels are fixed presentation strings, not evidence of conversion | [packages/worldenergydata-fdas/src/worldenergydata/fdas/reports/excel_generator.py:L122-L140] [packages/worldenergydata-fdas/src/worldenergydata/fdas/reports/excel_generator.py:L227-L250] [packages/worldenergydata-fdas/src/worldenergydata/fdas/reports/excel_generator.py:L424-L442] |

No spatial coordinate or phase convention is used by the financial operations above; the relevant origin is the first cashflow index, with a separate re-origin for trimmed calculations. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L159-L200]

## 3. Method and governing standards

| Method | Implemented rule | Reference / qualification |
| --- | --- | --- |
| NPV | Sum `C[t]/(1+r_period)^t`; monthly rate `(1+r_annual)^(1/12)-1`; annual rate unchanged | Code-defined formula, with time zero included; no standards clause cited by the function. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L149-L166] |
| Trimmed NPV / monthly MIRR | Endpoints use `abs(C)>1e-6`; preserve intermediate zeros; MIRR compounds positives forward, discounts negatives back, then annualizes monthly return | Compatibility implementation; do not treat the Excel label as independently checked vendor behaviour. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L72-L115] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L192-L200] |
| IRR / payback | `numpy_financial.irr`; monthly compounding to annual; payback is first nonnegative cumulative sum, without interpolation | Algorithm and discrete convention. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L223-L276] |
| Revenue and cost | Oil volume × realized oil price; optional gas volume × explicit gas price; day count × rig rate; well count × SURF unit cost; host cost evenly allocated backwards including first-oil month | Component methods do not establish completeness of generator cost lines. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L192-L297] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/gas_revenue.py:L24-L34] |
| Royalty | Sliding scale selects first inclusive threshold; oil rate is monthly oil volume/calendar days; flat/none paths use explicit argument, then deck, then assumptions | Current royalty behaviour, including leap-year day counts; no income-tax computation in this path. [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/terms.py:L80-L109] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L305-L385] |
| Forecast | Exponential uses effective annual decline converted to monthly; hyperbolic uses years and nominal initial decline, with exponential branch at `b=0` | Distinct decline-rate conventions; no published calibration is asserted. [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L300-L353] |
| Fiscal provenance | Loader checks required nonempty strings and schema; the metadata-mutation test establishes unchanged royalty output for changes to fiscal currency, discount and price marker | Provenance presence does not establish source authority or current law. [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/schema.py:L187-L233] [tests/unit/fdas/fiscal/test_cashflow_fiscal.py:L59-L73] |

Reference class: repository algorithms and compatibility tests; no governing engineering standard or standards-derived `Citation` sidecar is identified in these implementing functions. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L25-L115] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L167-L297]

UNVERIFIED: U2 — legal correctness, current applicability and effective dates of the shipped fiscal assumptions are not checked against their external sources; the YAML provenance is a reference lead, not acceptance evidence. [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/decks/us_gom.yml:L26-L33] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/decks/norway.yml:L21-L28] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/decks/uk.yml:L25-L32]

## 4. Validated worked examples

Status fields are reserved for the recorded offline executions at the header pin. Use the synthetic monetary unit USD consistently within each case; these are algorithm checks, not field economics qualifications.

| Case / kind | Independent basis or regression source; input | Expected / tolerance and basis | Existing test node ID | BASE / AFTER |
| --- | --- | --- | --- | --- |
| V1 validated, closed form | At zero rate the discounted sum equals the arithmetic sum; inline array `[-1000,300,300,300,300]` | 200.0 USD; existing assertion explicitly supplies `abs=1e-6` USD; H1 separately requires absolute residual ≤1e-6 USD | `tests/unit/fdas/test_financial.py::TestCalculateNpv::test_zero_discount_rate` [tests/unit/fdas/test_financial.py:L107-L111] | PASS / PASS |
| V2 validated, closed form | One annual period: `-1000+1100/(1+r)=0`, hence `r=0.1`; inline array | Annual IRR 0.1 (1); existing `np.isclose` assertion explicitly sets atol 0.001 (1) | `tests/unit/fdas/unit/test_financial.py::TestIRR::test_basic_irr_calculation` [tests/unit/fdas/unit/test_financial.py:L154-L161] | PASS / PASS |
| R1 regression | Padded versus unpadded stream, same implementation | Monthly and annual MIRR agree under the existing `assert_allclose` assertions, explicitly set rtol 1e-6 (1) | `tests/unit/fdas/unit/test_financial.py::TestExcelLikeMIRR::test_mirr_with_zero_padding` [tests/unit/fdas/unit/test_financial.py:L39-L49] | PASS / PASS |
| R2 regression | Decked versus deckless engine, inline production/price/timeline fixture; no independent economic answer | Same row counts, dates and all nine component values across four development-system keys; exact equality in native component units | `tests/unit/fdas/fiscal/test_deck_parity.py::test_deckless_vs_us_gom_identical_component_vectors` [tests/unit/fdas/fiscal/test_deck_parity.py:L22-L69] | PASS / PASS |

Original-code and captured-output comparisons are regression candidates only; the nominal published MIRR example asserts positivity rather than matching its cited value, and the golden comparison only checks nonempty output. [tests/unit/fdas/validation/test_against_original.py:L56-L70] [tests/unit/fdas/validation/test_against_original.py:L248-L260] [tests/unit/fdas/validation/test_against_original.py:L280-L293]

## 5. QA gates

Gate applicability: AQG r0 §10, Python calculations row; G5 applies to every family. Proposed checks below require retained inputs, node outcomes and source revision before a calculation is qualified.

| Gate | Applicability / route |
| --- | --- |
| G0 | Applicable: production schemas, month keys, gas units and fiscal provenance; checks I1–I4 |
| G1 | Applicable: Python import and offline pytest routes; no external program deck is generated; checks L1–L2 |
| G2 | Applicable: independently evaluated arithmetic and dimensional reconciliation; checks H1–H4 |
| G3 | NOT_APPLICABLE: no time-domain dynamics model in the cited monthly economic generator. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L456-L589] |
| G4 | NOT_APPLICABLE: no body/mesh/diffraction computation in the cited generator. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L456-L589] |
| G5 | Applicable: retained QA evidence, citation and result accounting; checks E1–E2 |

| Check | Executable route / quantity | Proposed numeric pass criterion and unit | Evidence / current disposition | Gate |
| --- | --- | --- | --- | --- |
| I1 | `to_fdas_production`; `test_maps_to_exact_fdas_columns`, `test_bad_month_rejected` | Exactly 5 columns; 0 accepted month-13 rows; 2 valid fixture rows | Existing assertions. [tests/unit/fdas/adapters/test_contract.py:L40-L43] [tests/unit/fdas/adapters/test_contract.py:L98-L105] | G0 |
| I2 | `monthly_gas_revenue` via `test_invalid_gas_price_is_rejected`, `test_invalid_gas_volume_is_rejected`, `test_gas_deck_requires_volume_column_and_unique_periods` | 0 accepted negative/nonfinite USD/Mcf prices or Mcf volumes; 0 accepted duplicate month keys | Existing rejection assertions; oil-only path needs the same completeness check separately. [tests/unit/fdas/analysis/test_gas_cashflow.py:L85-L117] | G0 |
| I3 | `validate_deck`; `test_unknown_top_level_field_rejected`, `test_provenance_fields_required_nonempty` | 0 accepted unknown keys; 0 blank required provenance strings across 4 fields | Existing schema assertions, not a legal-source check. [tests/unit/fdas/fiscal/test_terms.py:L98-L109] [tests/unit/fdas/fiscal/test_terms.py:L155-L169] | G0 |
| I4 | `classify_dev_system_by_depth`, `dev_system_from_water_depth_m`; boundary tests | 0 classification mismatches at 500 ft and 6000 ft; 0 mismatches across the 5 tested metre-input cases, including missing and comma-formatted values | Existing boundary assertions. [tests/unit/fdas/core/test_config.py:L85-L95] [tests/unit/fdas/adapters/test_field_concept_normalizer.py:L50-L55] | G0 |
| L1 | `test_fdas_public_api_surface`, `test_fiscal_decks_ship_as_package_data` | 0 missing public symbols among 6; 3 readable deck files | Imports/resource checks. [tests/unit/fdas/test_packaging.py:L37-L58] | G1 |
| L2 | Full module tests and contracts using the execution record in section 10 | 0 new failed/error nodes versus BASE; all 4 section-4 nodes executed | Distinguish unchanged baseline failures and missing fixtures; they do not clear engineering results | G1 |
| H1 | `calculate_npv`, V1 hand sum | Absolute difference ≤1e-6 USD from 200.0 USD | Closed-form node V1; the separate strict arithmetic probe returned exactly 200.0 USD at the code pin, PASS. [tests/unit/fdas/test_financial.py:L107-L111] | G2 |
| H2 | `calculate_irr`, V2 hand root | Proposed absolute difference ≤0.001 (1) from 0.1, in addition to the existing assertion | Closed-form node V2; an additional absolute bound, without relaxing the existing test; the separate arithmetic probe passed at the code pin. [tests/unit/fdas/unit/test_financial.py:L154-L161] | G2 |
| H3 | Inspect `generate_monthly_cashflow` dimensional route: sum host/drilling USD fields versus million-USD component totals converted by 1e6 | Absolute residual ≤0.01 USD for each nonzero capital total; fixed/SURF cost coverage: 0 omitted required categories | FAIL by source inspection: direct assignments, fixed/facilities zero; no detection test exists; issue pending (1). [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L489-L514] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L562-L571] | G2 |
| H4 | Inspect annual `calculate_all_metrics` MIRR route against one-period root with array `[-1000,1100]` | Absolute annual-rate residual ≤0.001 (1) from 0.1 | FAIL: arithmetic probe returned annual MIRR 213.8% against the 10.0% closed-form target; source inspection confirms monthly annualization by power 12; no annual MIRR detection test exists; issue pending (2). [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L85-L113] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L378-L386] | G2 |
| E1 | Resolve pack source references using `git show` at the pin; inspect 10 selected supporting ranges | 0 absent files, 0 out-of-range citations; 10/10 semantic matches | Citation resolver and manual sample record, retained with the review evidence | G5 |
| E2 | Reconcile pytest node outcomes and input digests with the pin, pack and issue drafts | 4/4 example outcomes; 0 unaccounted test outcomes; 0 input digest mismatches | BASE/AFTER records and SHA-256 inventory, retained with the review evidence | G5 |

G2 is not cleared for complete economic use: H3 and H4 remain failed checks with scoped issue drafts. V1 and V2 test isolated primitives and must not be used to qualify the defective generator or aggregate annual-MIRR path. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L562-L586] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L378-L386]

## 6. Known failure modes and pitfalls

| Symptom / cause | Detection or absence | Record / disposition |
| --- | --- | --- |
| Missing oil prices become an assumed constant; missing assumptions can select the default row or scalar without provenance | Inspect month-key completeness; existing `test_missing_price_uses_default` preserves the fallback, rather than rejecting incomplete pricing | Issue pending (1), source observations at the header pin. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L291-L295] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/config.py:L237-L265] [tests/unit/fdas/analysis/test_cashflow.py:L209-L215] |
| Fixed OPEX and facilities CAPEX remain zero; million-USD capital totals enter USD-labelled rows without conversion | H3 FAIL; no end-to-end dimensional/completeness detection check exists | Issue pending (1). [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L489-L514] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L562-L571] |
| Duplicate oil-only month keys overwrite earlier rows through `to_dict`; country normalizer does not aggregate entities | Review single-entity, unique-month input invariant; gas-enabled duplicate detection exists in I2; oil-only loss detection absent | Issue pending (1). [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/contract.py:L116-L127] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L516-L522] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/gas_revenue.py:L20-L22] |
| No drilling timeline yields zero capital; a warning is emitted, not an inferred duration | `test_honesty_guard_warns_on_empty_drilling_timeline`: warning count ≥1, drilling capital 0 USD | [Issue 783](https://github.com/vamseeachanta/worldenergydata/issues/783), upstream source gap; [issue 1075](https://github.com/vamseeachanta/worldenergydata/issues/1075), removed calendar-duration estimator. [tests/unit/fdas/adapters/test_conformance.py:L102-L120] [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/__init__.py:L6-L20] |
| Public BSEE adapter emits `MONTHLY_*_VOLUME`, but generator reads `MONTHLY_OIL_BBL` | No direct adapter→generator detection check exists; separate schema tests preserve incompatible outputs | [Issue 784](https://github.com/vamseeachanta/worldenergydata/issues/784). [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/bsee_adapter.py:L301-L310] [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L517-L520] [tests/unit/fdas/test_bsee_adapter.py:L179-L185] |
| Aggregate annual metrics invoke monthly MIRR regardless of `period` | H4 FAIL; `test_annual_period` only checks period metadata and nonempty NPV | Issue pending (2). [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L378-L386] [tests/unit/fdas/test_financial.py:L258-L262] |
| Single-sign MIRR becomes NaN; aggregate metrics retain errors/None; workflow JSON converts nonfinite floats to null | `test_all_positive_returns_nan`, `test_with_bad_cashflows`; consumers must check per-metric state | [Issue 832](https://github.com/vamseeachanta/worldenergydata/issues/832), economic-function consolidation/parity context. [tests/unit/fdas/test_financial.py:L46-L56] [tests/unit/fdas/test_financial.py:L264-L268] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fdas.py:L172-L181] |
| Fiscal currency, price marker and discount metadata mutation leaves the tested royalty output unchanged | `test_declarative_fields_are_not_consumed`: 0 royalty differences after metadata mutation | [Issue 736](https://github.com/vamseeachanta/worldenergydata/issues/736); no after-tax qualification. [tests/unit/fdas/fiscal/test_cashflow_fiscal.py:L59-L73] |
| Optional production columns are accepted at construction but cumulative/summary paths later require water or gas columns | No missing-optional-column end-to-end detection check exists | Issue pending (1). [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L52-L56] [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L151-L158] [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/production.py:L185-L195] |
| Excel summary labels NPV as a fixed discount and million-USD value without rescaling input | No rate/currency label-consistency detection check exists; current report tests exercise formatting and initialization only | Issue pending (1). [packages/worldenergydata-fdas/src/worldenergydata/fdas/reports/excel_generator.py:L122-L140] [tests/unit/fdas/reports/test_excel_generator.py:L27-L72] |
| Runtime qualification can fail the existing 50.0 ms assertion without a calculation change | Existing `TestPerformance::test_all_metrics_performance`; BASE FAIL, AFTER PASS; no cause established | Issue pending (5). [tests/unit/fdas/unit/test_financial.py:L363-L375] |
| Historical assurance and example APIs lag current source; some baseline comparisons skip missing files or check only nonempty workbooks | Use exact node outcomes, not historical validation percentages; no complete documentation-to-API detection check exists | [Issue 349](https://github.com/vamseeachanta/worldenergydata/issues/349); [issue 1044](https://github.com/vamseeachanta/worldenergydata/issues/1044); issue pending (3). [tests/unit/fdas/validation/test_against_original.py:L248-L260] [packages/worldenergydata-fdas/README.md:L29-L33] [packages/worldenergydata-fdas/src/worldenergydata/fdas/fiscal/schema.py:L124-L130] |

Dates for the source observations above: 2026-10-15; issue event dates remain those of the linked records. These are current code observations, not an assertion that every backlog item is a past incident.

## 7. Lessons log

Append new entries; do not overwrite earlier entries. Use public evidence IDs rather than execution identifiers.

| Date | Evidence ID | Lesson / pack change | Shared-log entry |
| --- | --- | --- | --- |
| 2026-10-15 | V1, V2, R1, R2 | Separate isolated arithmetic qualification from implementation parity; section 4 records both kinds. [tests/unit/fdas/test_financial.py:L107-L111] [tests/unit/fdas/unit/test_financial.py:L154-L161] [tests/unit/fdas/fiscal/test_deck_parity.py:L48-L69] | Pending, issue pending (3) |
| 2026-10-15 | H3, H4 | Passing isolated metrics does not establish monetary scaling or annual aggregate MIRR; sections 5–6 retain failures. [packages/worldenergydata-fdas/src/worldenergydata/fdas/analysis/cashflow.py:L562-L571] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L378-L386] | Pending, issue pending (3) |

## 8. Ownership

Review assignment for this draft: calculations quality manager for the data pipeline; deputy role: to be assigned by the maintainer. Producing roles: module documentation and data analysis. Escalate missing evidence, failed checks, altered tolerance or fiscal-basis changes to the quality manager; cross-family changes require the maintainer's disposition. These are review assignments and requirements, not completed approvals.

UNVERIFIED: U3 — a named deputy and a durable data-family appointment are not established; maintain DRAFT status until an independent provider records clearance; issue pending (3).

## 9. Dependencies

The member declares core, cost, NumPy, numpy-financial, pandas, openpyxl and PyYAML dependencies; the metadata normalizer additionally imports `field_development` from the root distribution at runtime. [packages/worldenergydata-fdas/pyproject.toml:L38-L46] [packages/worldenergydata-fdas/src/worldenergydata/fdas/adapters/field_concept_normalizer.py:L31-L36]

Rig-day calculation is deliberately outside FDAS to avoid a dependency cycle; callers pass drilling timelines into the engine, rather than importing the BSEE implementation from FDAS. [packages/worldenergydata-fdas/src/worldenergydata/fdas/data/__init__.py:L6-L20]

Repository-wide method search includes `scripts/`, not only package source; the following parallel implementations require explicit parity before substituting one for another. [scripts/all_fields_economics.py:L73-L87] [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L137-L181] [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L427-L484]

| Other implementation / consumer | Distinction and evidence |
| --- | --- |
| `economics.dcf` | Separate NPV over net component cashflow and separate finance/reinvestment MIRR. [packages/worldenergydata-economics/src/worldenergydata/economics/dcf.py:L137-L244] |
| BSEE financial calculator | NPV accepts a monthly rate directly; separate MIRR function. [packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/financial/cash_flow_calculator.py:L427-L484] |
| Lower-tertiary reproducer | Separate trimmed monthly MIRR implementation; regression context, not an independent standard. [packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/v30_financial_reproducer.py:L273-L287] |
| `scripts/all_fields_economics.py` | Separate trimmed NPV and annualized MIRR. [scripts/all_fields_economics.py:L73-L87] |
| Report-generation script | Builds annual arrays and uses separate annual NPV/IRR/payback calls, but default MIRR call; interfaces touched by H4. [scripts/gtm/generate_fdas_gtm_report.py:L88-L130] |
| Disclosure analytics | Cost-side loaders and comparability-gated benchmark invoked lazily through FDAS. [packages/worldenergydata-fdas/src/worldenergydata/fdas/api.py:L301-L344] |

Consolidation/parity follow-up: [issue 832](https://github.com/vamseeachanta/worldenergydata/issues/832). No solver binary or solver-program interface is required by the cited economic primitives. [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L84-L115] [packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py:L149-L166]

UNVERIFIED: U4 — inventory rows and version compatibility for every upstream/downstream consumer are not exhaustively qualified; issue pending (3).

## 10. Coverage and open items

### Reading inventory

Source coverage: all 20 Python files under the module, its two READMEs, package metadata and all three fiscal YAML decks. Test source coverage: 21 test files under `tests/unit/fdas`, the integration copy under `tests/modules/fdas`, and CLI tests; 393 unit nodes were collected, plus 9 integration-copy nodes, 37 CLI nodes and 8 contract nodes; exact outcomes are recorded below.

READ module documentation: `docs/modules/fdas/USER-GUIDE.md`, `VALIDATION-REPORT.md`, `DEPLOYMENT-CHECKLIST.md`, `country-adapter-checklist.md`; also `docs/domains/field-development/gas-revenue.md`. [docs/modules/fdas/USER-GUIDE.md:L1-L12] [docs/modules/fdas/VALIDATION-REPORT.md:L1-L20] [docs/modules/fdas/DEPLOYMENT-CHECKLIST.md:L1-L14] [docs/modules/fdas/country-adapter-checklist.md:L1-L18] [docs/domains/field-development/gas-revenue.md:L1-L20]

Markdown documentation mentioning FDAS was indexed across `docs/`; broader historical/planning/cross-module review is deferred under the bounded main-path scope, with no claim of exhaustive historical-document reading. The public inventory below uses source references and neutral folder groups; restricted names are not reproduced. Issue pending (3).

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
| [docs/modules/bsee/analysis/production/FDAS_V30/QUICKSTART.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/bsee/analysis/production/FDAS_V30/README_PRODUCTION_RETRIEVAL.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/bsee/analysis/production/lt_v30_v50_code_reconciliation.md:L110-L112] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/bsee/communications/email-review/reviewed/2026-07-08-fdas-canonicalization.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/cost/REFRESH_PROCEDURE.md:L8-L10] | INDEXED; broader review deferred, issue pending (3) |
| [docs/modules/fdas/DEPLOYMENT-CHECKLIST.md:L1-L3] | READ |
| [docs/modules/fdas/USER-GUIDE.md:L1-L3] | READ |
| [docs/modules/fdas/VALIDATION-REPORT.md:L1-L3] | READ |
| [docs/modules/fdas/country-adapter-checklist.md:L1-L3] | READ |
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
| [docs/plans/2026-07-03-issue-714-fdas-source-agnostic.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
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
| [docs/plans/2026-07-16-issue-1044-fdas-workbook-reconciliation.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
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
| [docs/research/bsee-fdas-integration-summary.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/docs/research/FDAS-INTEGRATION-STATUS.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/docs/research/fdas-documentation-review-summary.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/docs/research/fdas-integration-index.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/fdas-code-comparison.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/fdas-executive-summary.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/fdas-implementation-plan.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| [docs/research/fdas-quick-reference.md:L1-L3] | INDEXED; broader review deferred, issue pending (3) |
| 1 additional path with a restricted name; locator retained in the inspection record | INDEXED; public naming boundary, issue pending (3) |

### Offline execution record

Environment observation: CPython 3.11.15; code revision as pinned in the header. BASE and AFTER use the ordinary source-resolving `uv run python -m pytest` form, `-q -rA -p no:cacheprovider`, isolated `--basetemp`, scratch JUnit and coverage-database destinations, and `--allow-existing-tree-changes` to preserve the new documentation; default pytest addopts remain active; generated coverage reports and package metadata are removed by explicit file paths after each run.

Selection: `tests/unit/fdas`, `tests/modules/fdas/integration/test_end_to_end.py`, `tests/integration/cli/test_fdas_cli.py`, `tests/contracts`. Existing repository ignore rules remain unchanged; report discovered but unexecuted nodes explicitly.

| Execution | Collected (nodes) | Passed (nodes) | Failed (nodes) | Errors (nodes) | Skipped (nodes) | NOT_RUN qualification | Revision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BASE | 447 | 444 | 1 | 0 | 2 | 2 skipped baseline-comparison nodes; reasons below | `e73bda871798429eeb6dda0d16ed5520548d6cad` |
| AFTER | 447 | 445 | 0 | 0 | 2 | Same 2 skipped baseline-comparison nodes | Same code pin, documentation only |

Baseline failure: `tests/unit/fdas/unit/test_financial.py::TestPerformance::test_all_metrics_performance`, 65.3 ms against `<50.0 ms`; the unchanged assertion is at the pin, issue pending (5). This is an observed failure, not evidence of its cause. [tests/unit/fdas/unit/test_financial.py:L363-L375]

Skipped / NOT_RUN regression qualification: `tests/unit/fdas/unit/test_financial.py::TestRegressionAgainstFDAS::test_against_golden_baseline` has the unconditional reason `Requires golden baseline file`; `tests/unit/fdas/validation/test_against_original.py::TestFinancialOutputComparison::test_compare_with_golden_baseline` skipped because worksheet `Project Summary` was not found. The implementation reads `Project Summary`, while the captured-output test reads `Project_Summary`; the skip therefore does not establish missing data. [tests/unit/fdas/unit/test_financial.py:L335-L340] [tests/unit/fdas/validation/test_against_original.py:L248-L260] [tests/unit/fdas/validation/test_v30_determinism.py:L34-L41]

Native pytest skip count and NOT_RUN qualification describe the same two nodes and are not added together. All four section-4 nodes passed at BASE and AFTER. The node sets match; the only outcome change is the baseline runtime failure passing AFTER, with no new failure or error. No performance cause is established by this difference. No licence-dependent node was identified in this selection.

### Open register

| Item | Required evidence / disposition | Responsible role | Tracking |
| --- | --- | --- | --- |
| U1 — README claim, unverified | Re-derive historical assurance, coverage and speed claims; no broad maturity assertion from this run | Maintainer | [Issue 349](https://github.com/vamseeachanta/worldenergydata/issues/349) |
| U2 — fiscal source correctness, unverified | Open authoritative current sources and qualify effective dates before economic application; no legal rates asserted here | Maintainer | [Issue 736](https://github.com/vamseeachanta/worldenergydata/issues/736) |
| U3 — reviewer/deputy appointment | Assign deputy and record independent clearance, pack index and shared-log entries | Maintainer | issue pending (3) |
| U4 — broader dependency inventory | Complete cross-module inventory/compatibility and historical documentation review beyond the cited main path | Maintainer | issue pending (3); [issue 832](https://github.com/vamseeachanta/worldenergydata/issues/832) |
| Generator data integrity, completeness, unit labels and fallbacks | H3 and section-6 detection gaps; no module code changed | Maintainer | issue pending (1) |
| Annual aggregate MIRR | H4 and annual callers require a period-correct independent expectation | Maintainer | issue pending (2) |
| Legacy BSEE schema | Add adapter→generator interoperability detection before treating legacy adapter output as ready | Maintainer | [Issue 784](https://github.com/vamseeachanta/worldenergydata/issues/784) |
| Drilling source availability | Missing source remains explicit; no duration is fabricated | Maintainer | [Issue 783](https://github.com/vamseeachanta/worldenergydata/issues/783); [issue 1075](https://github.com/vamseeachanta/worldenergydata/issues/1075) |
| Historical fixtures and regression qualification | Resolve missing inputs and placeholder/nonempty-only checks; golden outputs remain regressions | Maintainer | [Issue 1044](https://github.com/vamseeachanta/worldenergydata/issues/1044); issue pending (3) |
| Baseline runtime assertion | Record the existing 50.0 ms criterion and failed node without changing its threshold | Maintainer | issue pending (5). [tests/unit/fdas/unit/test_financial.py:L363-L375] |
| Wheel exclusion | Existing member `**/*.md` glob matches nested Markdown; exclusion cannot be asserted without an archive check or packaging change, neither included here | Maintainer | issue pending (4). [packages/worldenergydata-fdas/pyproject.toml:L67-L72] |

Extra acceptance: no module-specific A8 criterion beyond the common acceptance set. Registry update: not applicable to the inspected tree; no `docs/registry/module-routing.yaml` exists, so no replacement registry is introduced. Quality clearance and final issue-number substitution remain pending.
