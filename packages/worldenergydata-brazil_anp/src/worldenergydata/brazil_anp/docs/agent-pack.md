# Brazil ANP module knowledge pack

| Header | Value |
| --- | --- |
| Module | `brazil_anp` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp` |
| Pack revision | 1 |
| Code revision | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` |
| Analysis family | EC; data pipelines, using the Python calculations gates of AQG r0 section 10 |
| Quality manager role | Calculations quality manager, pending a dedicated data quality manager |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

The module downloads monthly production ZIPs, normalizes well records, aggregates field-month totals, fits decline curves, evaluates illustrative fiscal calculations and connects production to concept screening and pre-tax cashflow. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L53-L99] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L40-L76] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L14-L48] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L62-L98] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L109] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L69]

The reference chain labels its economics `chain_plumbing_pre_tax`; it supplies empty drilling costs and defaults an unknown development system to `subsea15`, so its result is not an investment decision basis. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L43-L69]

Concession royalty bands are explicitly illustrative and require a governing contract and case before fiscal-deck use. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L1-L6] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L92]

Empty production can return a 1970-01-01 first-oil default, zero months and zero economics without an error (#1289). Unknown fields, numeric coercion, missing names and unqualified fiscal inputs can also return plausible results (#1291); section 6 records the observed paths and missing detection checks. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L85] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L50-L59]

The distribution declares Alpha maturity; this is package metadata, not an independently established readiness result. [packages/worldenergydata-brazil_anp/pyproject.toml:L15-L23]

## 2. Inputs and outputs

### Inputs

| Input | Unit and allowed range | Default and source | Evidence |
| --- | --- | --- | --- |
| `ANPClient.download_month(year, month)` | Calendar year; month 1–12 on URL construction | `force_refresh=False`, `encoding="utf-8-sig"`; explicit cache directory advised | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L27-L36] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L53-L76] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L101-L104] |
| Current well table | `Período` year/month; oil, condensate, water bbl/day; gas header interpreted by code as thousand m³/day | Required current-schema columns; no physical range validation; decimal comma parsing | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L1-L6] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L78-L110] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L139-L162] |
| Legacy well table | `campo`, `poco`, `data`; liquid `*_sm3` monthly volumes and `gas_mm3` multiplied by 1000 | No schema default; calendar days determine oil daily rate | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L26-L34] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L47-L76] |
| Decline series | Positive non-null observations; minimum 3; time is retained-observation index, not elapsed calendar time | Exponential model; fitted decline bounded 0–2 per observation interval | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L62-L84] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L100-L114] |
| Metadata tables | Field/platform/well tables; depth m; well count dimensionless | Normalized text matching; missing depth returns `None`; missing wells yield 0 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L31-L53] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L69-L115] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L143-L146] |
| Fiscal arguments | Revenue, opex and capex share the caller basis, but special-participation thresholds are fixed BRL amounts with no period conversion; production bbl/day; share dimensionless | PSA share default 0.50; arbitrary currency/period is unsafe for concession participation (#1291) | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L81] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L133-L146] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L162-L176] |
| Reference-chain arguments | Adapter, metadata, field selector, optional start/end; oil price USD/bbl | Price default 75.0; region `brazil` | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L46] |

### Outputs

| Output | Units and conventions | Evidence |
| --- | --- | --- |
| Client DataFrame | CSV strings plus partition marker `location_source`; no CSV is returned as an empty DataFrame | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L110-L142] |
| Normalized well DataFrame | `oil_bbl`, `condensate_bbl`, `water_bbl` monthly bbl; `gas_mcf` monthly Mcf; `oil_bbl_per_day` bbl/day; current schema retains source metadata but does not return `gas_m3` | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L92-L110] |
| Field DataFrame and summary | Sums by field/date; unique well count; water fraction dimensionless; monthly oil peak and mean of field-month daily rates | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L31-L67] |
| `DeclineCurveResult` | Initial rate and RMSE inherit input units; decline per retained interval; R² and b dimensionless; integer prediction starts at t=0 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L28-L56] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L117-L124] |
| `FiscalResult` | Amounts retain the caller basis, but participation uses fixed BRL thresholds; tax rate dimensionless; no period/currency conversion (#1291) | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L61-L70] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L140-L156] |
| Reference-chain dictionary | Unified/project_economics tables, concept rankings, pre-tax label; cashflow metrics USD and month counts | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L85] |

Spatial coordinates, phase and load signs have no role in the production normalization equations; metadata carries scalar water depth rather than a coordinate frame. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L78-L110] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L43-L53]

## 3. Method and governing standards

| Method | Implementation and basis | Qualification |
| --- | --- | --- |
| ZIP/CSV ingestion | Sorted CSV members; semicolon separator, two header rows, third row skipped, all strings; column flattening | Implemented parser contract, not independently checked current regulator schema. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L110-L158] |
| Duplicate treatment | Key `(Campo, Nome Poço ANP, Período)`; only combined `mar`/`presal` duplicates are accepted; `presal` priority | No comparison of conflicting production values precedes retention. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L172-L204] |
| Current monthly conversion | Daily liquid rates × calendar days; gas rate × shared gas conversion × days | Code-defined interpretation; independent regulator unit confirmation remains open. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L78-L110] |
| Legacy conversion | Liquid Sm³ × shared oil factor; gas input × 1000 m³ then scf/1000 | Shared unit constants rather than a new standard-derived constant. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L14-L27] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L47-L61] |
| Aggregation | Group sums; unique wells; water/(oil+water), denominator substituted with 1 when total ≤0 | No duplicate-well check inside the aggregator. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L31-L48] |
| Decline fit | Exponential `qi*exp(-D*t)`, hyperbolic `qi/(1+b*D*t)^(1/b)`, harmonic `qi/(1+D*t)`; nonlinear least squares, R² selection | Code equations; no published method edition is established by these docstrings; fallback behaviour is section 6. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L1-L6] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L86-L98] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L100-L197] |
| Field concept | Mapping into shared normalizer; mean available platform depth; unique wells | Sparse metadata screening, not a design calculation. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L18-L28] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L56-L66] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L98-L124] |
| Fiscal calculations | Inclusive illustrative royalty bands; progressive special-participation bands; nonnegative corporate tax; PSA profit-oil allocation | Regulatory validity is not established by compatibility tests. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L26-L58] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L187] |

The concession source comments name Lei 9.478/1997 article 47 and Decreto 2.705/1998 articles 11–12, while explicitly rejecting the daily-rate bands as contract qualification; this pack makes no fresh legal interpretation. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L28-L39]

UNVERIFIED: current regulator schema, unit definitions, fiscal applicability and independent decline benchmark qualification have not been checked against source publications in this pack; issue pending (1).

## 4. Validated worked examples

Validated examples: **0**; the retained cases below are **6 regression examples**, based on synthetic inputs and implementation assertions rather than a versioned independent regulator benchmark. [tests/unit/brazil_anp/test_anp_client.py:L15-L42] [tests/unit/brazil_anp/test_decline_curves.py:L13-L41] [tests/unit/brazil_anp/test_field_economics.py:L254-L279]

The result column records offline execution on 2026-10-16 against code pin `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746`; PASS denotes the named test's assertions, with the qualification limits retained below. [tests/unit/brazil_anp/test_field_production.py:L42-L48]

| ID | Source and input | Expected result; tolerance and basis | Test node ID | Offline result |
| --- | --- | --- | --- | --- |
| R1 | In-memory monthly CSV ZIP fixture | 3 records; exact count; request and cache contract | `tests/unit/brazil_anp/test_anp_client.py::TestANPClientDownloadMonth::test_download_month_uses_official_gov_br_zip_url` | PASS; mocked HTTP, not a live endpoint check. [tests/unit/brazil_anp/test_anp_client.py:L112-L128] |
| R2 | In-memory current well-rate fixture | Oil 31015.5 bbl, condensate 310.0 bbl, water 627.75 bbl for 31 days; test-native `pytest.approx` | `tests/unit/brazil_anp/test_well_production.py::TestCurrentAnpWellProductionSchema::test_current_portuguese_schema_parses_decimal_comma_rates` | PASS; parser arithmetic only. [tests/unit/brazil_anp/test_well_production.py:L118-L154] |
| R3 | In-memory normalized well records | Oil 314490.0 + 283041.0 = 597531.0 bbl; absolute error <1.0 bbl, the test criterion | `tests/unit/brazil_anp/test_field_production.py::TestFieldProductionAggregator::test_aggregate_sums_oil_production` | PASS; conservation arithmetic, not independent measured production. [tests/unit/brazil_anp/test_field_production.py:L10-L23] [tests/unit/brazil_anp/test_field_production.py:L42-L48] |
| R4 | Seeded noisy exponential series; 36 observations | Positive fitted rate and decline; R² >0.9 (unit 1), the test criterion | `tests/unit/brazil_anp/test_decline_curves.py::TestDeclineCurveAnalyzerFit::test_fit_exponential` | PASS; synthetic fit, no physical forecast accuracy claim. [tests/unit/brazil_anp/test_decline_curves.py:L13-L18] [tests/unit/brazil_anp/test_decline_curves.py:L60-L66] |
| R5 | In-memory loader and metadata fixtures | 2 months; finite cashflow USD; pre-tax label and ranked concept assertion; exact predicates | `tests/unit/brazil_anp/test_reference_chain.py::test_reference_chain_runs_production_project_economics_cashflow_and_concept_screening` | PASS; wiring only. [tests/unit/brazil_anp/test_reference_chain.py:L58-L75] |
| R6 | Code-pinned illustrative band fixtures | Exact inclusive boundary outputs; zero revenue returns 0 currency units | `tests/unit/brazil_anp/test_field_economics.py::test_royalty_band_values_and_boundaries_regression_pin` | PASS; legal validity is excluded. [tests/unit/brazil_anp/test_field_economics.py:L254-L280] |

## 5. QA gates

AQG r0 section 10, Python calculations, supplies G0–G2; G3 and G4 are inapplicable; section 9 supplies G5. The following checks are acceptance definitions for this module, not a declaration that a production dataset has passed every gate (AQG r0 sections 9–11).

| Gate | Applicability | Check ID and executable route | Numeric pass criterion and unit | Evidence and current disposition |
| --- | --- | --- | --- | --- |
| G0 | Applicable: input schema and units | C0a: `tests/unit/brazil_anp/test_well_production.py::TestUnitConversions::test_convert_mm3_to_m3` | `convert_mm3_to_m3(1.0)` =1000.0 m³; absolute error 0.0 m³ | PASS in offline tests. [tests/unit/brazil_anp/test_well_production.py:L38-L42] |
| G0 | Applicable: source selection | C0b: R1 plus cached-month test | 3 records; 0 HTTP calls when cache is present | PASS with mock source only. [tests/unit/brazil_anp/test_anp_client.py:L130-L142] |
| G0 | Applicable: provenance | C0c: compare input row counts before/after `WellProductionLoader.load`; inspect invalid periods and blank rates; compare duplicate-key values before retention | 0 unexplained dropped rows; 0 unqualified blank-to-zero substitutions; 0 conflicting retained duplicates (units: records); this loader-side comparison cannot count rows already dropped by the client (SF5) | Proposed detection; targeted tests absent, issue pending (2). [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L78-L90] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L139-L145] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L172-L204] |
| G1 | Applicable: Python import and tests; no external program load route | C1: run the complete test selection recorded in section 10, with normal test collection and tree-preservation checks | 238 tests passed; 0 failed; 0 skipped; 0 collection errors (unit: tests) | BASE and after PASS; both runs are recorded in section 10. [tests/unit/brazil_anp/test_reference_chain.py:L58-L75] [tests/contracts/test_assetutilities_engine_contract.py:L1-L29] |
| G2 | Applicable: independent arithmetic and reference qualification | C2a: R3; sum the two fixture oil inputs separately and compare `FieldProductionAggregator.aggregate` | Expected 597531.0 bbl; absolute error <1.0 bbl | PASS for arithmetic; independent production benchmark remains issue pending (1). [tests/unit/brazil_anp/test_field_production.py:L42-L48] |
| G2 | Applicable: fitting behaviour | C2b: R4; inspect elapsed intervals and optimizer failure status before using a forecast | R² >0.9 (unit 1) on the seeded case; 0 unmarked fallbacks and 0 compressed missing intervals (unit: events) | R² assertion PASS; failure/time criteria need targeted tests, issue pending (3). [tests/unit/brazil_anp/test_decline_curves.py:L60-L66] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L62-L75] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L125-L132] |
| G3 | NOT_APPLICABLE: no dynamics integration in the module method set | No dynamics check | Not applicable | The production fit computes rates and scalar fit metrics, not time-domain dynamics. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L28-L56] |
| G4 | NOT_APPLICABLE: no diffraction body or mesh calculation in this scope | No diffraction check | Not applicable | Metadata and monthly production are the inputs of this chain. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L41] |
| G5 | Applicable: reproducible QA evidence | C5: attach machine-readable case status, source revision/digest, units, input fingerprint and disposition to every reported result; recompute fingerprints before consumption | 0 missing evidence fields; 0 fingerprint mismatches; 0 unexplained report values (unit: records) | Not established for a production dataset; issue pending (1). The chain returns results without such a record. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L85] |

Checks defined: G0 **3**, G1 **1**, G2 **2**, G3 **0**, G4 **0**, G5 **1**; **7 total** (AQG r0 sections 9–10; check definitions above).

## 6. Known failure modes and pitfalls
sweep: not run (legacy pack)

| Symptom | Cause and detection | Incident or follow-up; recorded date | Evidence |
| --- | --- | --- | --- |
| Missing values become zero; malformed periods disappear | Coercion then row filtering; C0c must count rejected rows and missingness; **no detection check exists** | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L78-L90] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L139-L145] |
| Expected overlap can conceal conflicting production | Partition preference without value comparison; C0c; **no detection check exists** for conflicting values | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L172-L204] |
| Fit failure returns a default fit or another model | Broad exception fallback, including skipped candidate models in `best_fit`; C2b; **no detection check exists** for optimizer failure | issue pending (3); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L125-L132] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L160-L161] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L188-L189] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L86-L98] |
| Forecast uses compressed history or restarts at zero | Filtering before integer-index construction; integer `predict` uses `range(periods)`; C2b; **no detection check exists** for dated gaps | issue pending (3); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L38-L54] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L62-L75] |
| Missing environment raises; numeric depth changes magnitude | Empty non-null selection indexed at zero; numeric value string stripped of decimal points; **no detection check exists** for these metadata edges | issue pending (4); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L118-L133] |
| Synthetic adapter output mistaken for observed production | Adapter without an injected loader generates profiles; C5 requires source qualification; the emitted `anp_producao_poco` tag is excluded by the real-source allowlist, so loaded data cannot pass that status check; numeric coercion has no counter; no detection check exists for either defect (production pack D5/D8) | #1291; issue pending (1); 2026-10-16 | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L39-L70] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L138-L175] [packages/worldenergydata-production/src/worldenergydata/production/docs/agent-pack.md:L136-L139] |
| Configured download previously returned HTTP 404 | Historical incident; C0b verifies monthly URL/cache contract; scheduler failure test verifies failure status; live reachability is not established by mock tests | #459, closed; live availability #1096, open; 2026-10-16 | [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L24-L32] [tests/unit/brazil_anp/test_anp_client.py:L112-L128] [tests/unit/scheduler/test_brazil_anp_refresh.py:L110-L124] |
| Royalty bands mistaken for qualified fiscal terms | Explicit illustrative marker; R6 checks compatibility, not law; qualification-marker and shipped-deck tests detect loss of that boundary | #1182, closed; remaining fiscal seam #737, open; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L28-L39] [tests/unit/brazil_anp/test_field_economics.py:L189-L251] |
| Pre-tax chain mistaken for full project economics | Empty drilling costs, default development system, flat default oil price 75.0 USD/bbl and pre-tax output label; R5 detects the label; no independent investment check exists | #737; issue pending (1); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L69] |
| Refresh metadata still describes an obsolete blocker | Source-refresh contract still lists closed incident 459; C5 requires reconciliation; no detection check exists for stale blocker text | #917; 2026-10-16 | [data/source-refresh-acceptance-contract.json:L15-L15] |
| SF1. Empty production returns a 1970 first-oil date and zero economics | Empty project_economics frame substitutes 1970-01-01; zero months and USD sums retain the normal pre-tax label. Unknown adapter selectors or empty loads reach this path; no detection check exists. R5 exercises nonempty production only | #1289; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L85] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L96-L104] |
| SF2. Unknown field returns a zero summary | Exact case-sensitive selection has no match; zero oil, rate, water cut, peak and months resemble valid zero production. The existing unknown-field test preserves this contract; no detection check exists | #1291; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L50-L67] [tests/unit/brazil_anp/test_field_production.py:L97-L100] |
| SF3. Currency or period silently moves participation band edges | Fixed BRL thresholds apply to gross revenue minus opex and capex in the caller basis; no currency/period argument or conversion is enforced. The source comment describes quarterly tables; the separate chain uses USD. no detection check exists; compatibility is not fiscal qualification | #1291; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L37-L55] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L95-L109] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L133-L146] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L79-L85] |
| SF4. Dot-decimal production rates change magnitude | Every dot is removed before comma replacement: text or float 1000.5 becomes 10005.0 and 0.5 becomes 5.0. The public loader accepts frames beyond the string CSV route; no detection check exists. R2 covers decimal commas only | #1291; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L40-L45] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L86-L110] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L139-L145] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L127-L142] |
| SF5. Empty or partial ingestion is reported as success | Non-CSV members are skipped; no CSV yields an empty frame; blank rows and periods without a year-first match are removed before C0c. Empty loader/aggregator inputs remain empty. Scheduler writes snapshots and success metadata even for 0 raw records; no detection check exists for raw-to-client rejects or empty refreshes | #1291; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L110-L142] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L40-L42] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L14-L29] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py:L48-L77] |
| SF6. Well count is zero or counts rows instead of distinct wells | Missing field column or unmatched wells gives 0; absent well-name columns gives row count, including well-months. Null labels are dropped and blank labels can count as one well; no detection check exists | #1291; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L89-L115] |
| SF7. Missing or negative production rate gets 5 % royalty | NaN matches no band and retains 0.05; negative rates match the first band. no detection check exists; R6 checks valid boundaries only | #1291; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L92] |
| SF8. Blank field and well names become literal nan labels | String coercion converts missing names to "nan"; aggregation then creates a field with that label and counts it as a well. Whitespace labels also survive; no detection check exists | #1291; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L92-L110] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L40-L43] |
| SW1. Unvalidated or stale ZIP payload is cached | Download writes bytes before ZIP/CSV validation; cached files are reused by existence with no freshness or digest check, even when parsing later fails or yields empty data. Default cache is inside the package; no detection check exists; C0b checks reuse only | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L27-L51] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L61-L76] |
| SW2. Overlap checks disappear or partition identity is unknown | Missing key columns return the input without duplicate checks; unknown filenames get "unknown" and a low priority. no detection check exists for missing-key bypass or unknown-source acceptance; C0c is a proposal | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L161-L180] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L195-L204] |
| SW3. Ambiguous gas headers select a column without a unit check | First fuzzy gas-total match or fallback header is used; no ambiguity check or header-unit reconciliation occurs before the gas conversion. no detection check exists | issue pending (1); issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L86-L110] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L148-L162] |
| SW4. Unqualified unit basis and nonphysical volumes survive conversion | Current inputs are treated as daily rates; legacy Sm3 and gas input times 1000 are treated as monthly volumes. Negative/nonfinite values have no physical range validation; C0a/R2 check arithmetic only; no detection check exists for basis or physical validity | issue pending (1); issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L21-L27] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L47-L61] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L86-L110] |
| SW5. Aggregation drops keys or turns unknown totals into zero | Missing numeric columns are omitted, null field/date groups are dropped, default sums turn all-null streams into zero and null well labels are excluded from the count. no detection check exists; C2a checks complete fixture conservation only | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L31-L43] |
| SW6. Invalid liquid totals yield a plausible water fraction | Nonpositive oil-plus-water replaces the denominator with 1.0, so zero or negative liquid totals can hide an undefined fraction or produce an unphysical value. no detection check exists | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L45-L46] |
| SW7. Ambiguous metadata selection takes the first matching row | Normalized case/accent matching can conflate labels; duplicate field rows return the first without reconciliation. Missing labels are string-normalized rather than validated; no detection check exists | issue pending (4); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L69-L76] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L143-L146] |
| SW8. Missing metadata propagates without completeness status | Missing platform table/column or no valid depths returns None; available depths alone are averaged. Blank optional metadata becomes None, absent environment returns None and optional production columns get NA. no detection check exists for completeness; C5 does not yet attach a status | issue pending (4); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L79-L86] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L98-L106] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L118-L140] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L165-L168] |
| SW9. Invalid model or prediction silently falls back | Unknown fit model or unknown prediction model, including hyperbolic without b, uses exponential; predictions clamp negative or NaN values to zero. Nonpositive integer periods yield empty predictions. no detection check exists for these fallbacks | issue pending (3); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L38-L56] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L77-L84] |
| SW10. Constant observations report R squared zero | Zero total variance returns 0.0 instead of an undefined-fit status; dataclass metrics also default to zero if omitted. no detection check exists for distinguishing unset/undefined metrics from measured fit quality | issue pending (3); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L28-L36] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L191-L197] |
| SW11. Invalid fiscal arguments produce clamped or fixed results | Nonpositive royalty/net-revenue inputs return zero; profit oil and corporate tax clamp to zero, while negative costs and out-of-range government shares are unchecked. PSA uses fixed 15 %, 30 % and default 50 % shares with no contract validation; concession corporate tax is fixed 34 %. no detection check exists for input or contract validity; R6 is compatibility only | issue pending (1); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L26-L26] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L57-L58] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L124] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L140-L187] |
| S6. Semester refresh fetches one month | Scheduler resolves semester 1 to June and semester 2 to December, then downloads only that month, unlike the client six-month wrapper; no detection check exists | issue pending (2); 2026-10-16 | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py:L48-L53] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py:L91-L99] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L78-L99] |

Sweep: **30 section-6 rows**, comprising the 10 retained rows, SF1–SF8, SW1–SW11 and the external scheduler S6 row; these are 29 package/shared risk rows and 1 external scheduler row. The whole package was read at the code revision; the following candidate search returned **94 matching lines**, classified into the rows above rather than counted as independent defects. Visible errors (missing requests, invalid month/semester, unexpected overlaps, insufficient fit data and missing required columns) are not silent fallbacks. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L12-L14] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L64-L65] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L70-L71]

```sh
rg -n 'except|continue|return None|return \[\]|return \{\}|\b0(\.0)?\b|1970|\b(int|float)\(|write_bytes|to_csv|to_parquet|dropna|errors=|fillna|where\(' packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp --glob '*.py'
```

Issue references use repository issue numbers; historical incidents are distinguished from current code observations, and no new live download has been performed. [tests/unit/brazil_anp/test_anp_client.py:L112-L128]

## 7. Lessons log

| Date | Change reference | Lesson and pack change | Evidence | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-16 | Pack revision 0 | Separate code regression from source qualification; sections 3–6 retain illustrative, synthetic and pre-tax limits | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L1-L6] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L69] | Pending maintainer registration; issue pending (6) |
| 2026-10-16 | Pack revision 1 | Record silent defaults before interpreting test success; sections 1, 5, 6, 9 and 10 distinguish known defects from detection coverage | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L72-L85] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L139-L145] | #1289; #1291 |

## 8. Ownership

- Family quality manager role: calculations quality manager, covering data pipelines pending a dedicated data quality manager (module lifecycle revision 0, section 6).
- Deputy role: independent calculations reviewer; designation pending, issue pending (6) (module lifecycle revision 0, section 3 item 8).
- Production responsibility: module maintainers; technical classification and gate disagreements go to the quality manager; priority and cross-family conflicts go to the maintainer (module lifecycle revision 0, section 4 step E).
- Independent clearance shall precede merge; the producer shall not issue clearance (AQG r0 section 11).

## 9. Dependencies

| Direction | Dependency and boundary | Evidence |
| --- | --- | --- |
| Upstream | pandas CSV/dataframe operations; optional requests for downloads; ZIP payload supplied by cache or HTTP | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L9-L14] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L61-L76] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L110-L142] |
| Upstream | Shared oil/gas units; NumPy, SciPy optimization and scikit-learn metrics | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L14-L27] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L52-L55] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L100-L124] |
| Upstream/downstream | Shared metadata normalizer, unified query/adapter, project_economics cashflow and assumptions, concept recommendation | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L18-L28] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L56-L61] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L31-L59] |
| Downstream | Scheduler writes raw and normalized month snapshots and refresh metadata; semester mode resolves only June or December (S6), not all six months; issue pending (2) | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py:L47-L77] [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py:L91-L99] |
| Downstream | Loader-backed adapter supplies canonical monthly columns; no-loader route remains synthetic; merged production pack D5/D8 records uncounted numeric coercion and the emitted tag absent from the real-source allowlist | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L39-L70] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L113-L136] [packages/worldenergydata-production/src/worldenergydata/production/docs/agent-pack.md:L136-L139] |

The package declares core, NumPy, pandas, SciPy and scikit-learn dependencies; metadata/concept/cashflow use additional sibling packages in the workspace, so standalone dependency completeness is not asserted. [packages/worldenergydata-brazil_anp/pyproject.toml:L26-L36] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L31-L59]

### Implementation-map inventory and A8

Map authority: **digitalmodel**, `docs/registry/implementation-map.yaml`, branch `codex/implmap-work`, branch commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, map data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954` (Implementation map, schema version 1, `revision`, `families` and `implementations` records).

The parsed map contains **13 families**, **0 implementation rows inside this package**, **0 module map families** and therefore **0 counted families**; section-9 inventory is empty, and the counted-family grep is **NOT_APPLICABLE: no map family has an implementation row in the package** (Implementation map, pinned branch commit above, all `families[].implementations[].path` records).

Map follow-up, issue pending (6): ZIP/CSV ingestion and overlap resolution; current/legacy production normalization; field-month aggregation; exponential/hyperbolic/harmonic decline fitting and prediction; fiscal royalty, participation and profit-oil calculations; metadata normalization and reference-chain orchestration. These methods are in section 3, but none is enrolled by this map revision. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L110-L204] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L40-L110] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L14-L48] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L38-L197] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L187] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L31-L66] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L69]

### Further repository search

A repository-wide Python text search, including `scripts/`, used `decline`, the three fiscal function names and the client/loader/aggregator class names; further-search findings do not alter the counted-family result. Comparable decline formulas compute directly in the following definitions, rather than delegating to this module. [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L48-L70] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L206-L258]

| Candidate | Classification and disposition | Evidence |
| --- | --- | --- |
| `sodir.forecasting.DeclineCurve.predict`, `ProductionForecaster._fit_exponential_decline`, `_fit_hyperbolic_decline`, `_fit_harmonic_decline` | Independent decline calculations outside package; map follow-up, issue pending (6) | [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L48-L70] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L150-L271] |
| `production.forecast.decline.ArpsDeclineCurve._fit_params`, `_rate_fn` | Independent decline calculations outside package; map follow-up, issue pending (6) | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L206-L277] |
| `BrazilAnpAdapter._generate_field_rows` | Synthetic profile generator outside package; separate from measured production ingestion; follow-up, issue pending (6) | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L138-L175] |
| `sodir.reference_chain` | Parallel orchestration template using shared project_economics/concept services; empty production defaults to 1970; shared empty-chain follow-up #1289; map follow-up, issue pending (6) | [packages/worldenergydata-sodir/src/worldenergydata/sodir/reference_chain.py:L27-L103] |
| `spain.reference_chain` | Parallel orchestration template using shared project_economics/concept services; empty production defaults to 1970; shared empty-chain follow-up #1289; map follow-up, issue pending (6) | [packages/worldenergydata-spain/src/worldenergydata/spain/reference_chain.py:L21-L108] |
| `canada.reference_chain` | Parallel orchestration template using shared project_economics/concept services; empty production defaults to 1970; shared empty-chain follow-up #1289; map follow-up, issue pending (6) | [packages/worldenergydata-canada/src/worldenergydata/canada/reference_chain.py:L32-L97] |
| `ukcs.reference_chain` | Parallel orchestration template using shared project_economics/concept services; empty production defaults to 1970; shared empty-chain follow-up #1289; map follow-up, issue pending (6) | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/reference_chain.py:L28-L99] |
| `australia.reference_chain` | Parallel orchestration template using shared project_economics/concept services; fixed 1970 placeholder and no production source; shared empty-chain follow-up #1289; map follow-up, issue pending (6) | [packages/worldenergydata-australia/src/worldenergydata/australia/reference_chain.py:L30-L88] |
| `ukcs.analysis.field_economics` | Independent fiscal calculator outside package; map follow-up, issue pending (6) | [packages/worldenergydata-ukcs/src/worldenergydata/ukcs/analysis/field_economics.py:L34-L130] |
| `west_africa.analysis.field_economics` | Independent fiscal calculator outside package; map follow-up, issue pending (6) | [packages/worldenergydata-west_africa/src/worldenergydata/west_africa/analysis/field_economics.py:L126-L260] |
| `project_economics.fiscal.terms.RoyaltyTerms.rate_for` and fiscal decks | Separate deck-driven royalty calculation; other fiscal terms remain declarative, not a full copy of the local regime; map follow-up, issue pending (6) | [packages/worldenergydata-project_economics/src/worldenergydata/project_economics/fiscal/terms.py:L64-L115] |

## 10. Coverage and open items

### Files and tests

All 10 Python files under the package were read; the implementation-bearing files and line ranges appear throughout sections 1–9, and the three initializer files describe package scope. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/__init__.py:L1-L10] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/__init__.py:L1-L1] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/__init__.py:L1-L1]

The package README was read for its illustrative-scale limits; its legal comparisons are documentation claims, not freshly checked law. [packages/worldenergydata-brazil_anp/README.md:L10-L26]

| Test file or selection | Passed at baseline confirmation | Result kind |
| --- | --- | --- |
| `tests/unit/brazil_anp/test_anp_client.py` | 12 | Offline PASS. [tests/unit/brazil_anp/test_anp_client.py:L1-L174] |
| `tests/unit/brazil_anp/test_brazil_field_concept.py` | 3 | Offline PASS. [tests/unit/brazil_anp/test_brazil_field_concept.py:L1-L99] |
| `tests/unit/brazil_anp/test_decline_curves.py` | 15 | Offline PASS. [tests/unit/brazil_anp/test_decline_curves.py:L1-L155] |
| `tests/unit/brazil_anp/test_field_economics.py` | 24 | Offline PASS. [tests/unit/brazil_anp/test_field_economics.py:L1-L280] |
| `tests/unit/brazil_anp/test_field_production.py` | 11 | Offline PASS. [tests/unit/brazil_anp/test_field_production.py:L1-L117] |
| `tests/unit/brazil_anp/test_reference_chain.py` | 1 | Offline PASS. [tests/unit/brazil_anp/test_reference_chain.py:L1-L75] |
| `tests/unit/brazil_anp/test_well_production.py` | 18 | Offline PASS. [tests/unit/brazil_anp/test_well_production.py:L1-L171] |
| `tests/unit/production/unified/test_brazil_anp_adapter_loader.py` | 4 | Offline PASS. [tests/unit/production/unified/test_brazil_anp_adapter_loader.py:L1-L126] |
| `tests/unit/scheduler/test_brazil_anp_refresh.py` | 5 | Offline PASS. [tests/unit/scheduler/test_brazil_anp_refresh.py:L1-L132] |
| `tests/unit/production/unified/test_adapters.py` | 94 | Offline PASS. [tests/unit/production/unified/test_adapters.py:L1-L205] |
| `tests/unit/project_economics/fiscal/test_deck_parity.py` | 5 | Offline PASS. [tests/unit/project_economics/fiscal/test_deck_parity.py:L1-L160] |
| `tests/contracts/test_assetutilities_data_contract.py` | 5 | Offline PASS. [tests/contracts/test_assetutilities_data_contract.py:L1-L51] |
| `tests/contracts/test_assetutilities_engine_contract.py` | 3 | Offline PASS. [tests/contracts/test_assetutilities_engine_contract.py:L1-L31] |
| `tests/contracts/test_flaky_register_schema.py` | 38 | Offline PASS. [tests/contracts/test_flaky_register_schema.py:L1-L237] |

Offline command form: `uv run python -m pytest` followed by the 6 selections in the table (the module directory, direct adapter/scheduler files, general adapter file, fiscal parity file and contracts directory), `-q -rA -p no:cacheprovider --allow-existing-tree-changes --basetemp=<scratch directory>`. The documented tree mode hashes initially dirty paths and fails on changed bytes or additional dirty paths; it does not exempt the pack from preservation. [docs/development/index.md:L45-L64]

| Run | Code revision | Run / passed / failed / skipped / NOT_RUN | Command exit |
| --- | --- | --- | --- |
| Initial baseline, module and direct callers | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` | 93 / 93 / 0 / 0 / 0 | 1: the new pack appeared during the run; tree-preservation guard rejected the change. [tests/conftest.py:L431-L456] |
| Baseline confirmation, expanded selection | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` | 238 / 238 / 0 / 0 / 0 | 0; existing-edit fingerprints preserved. [tests/conftest.py:L413-L451] |
| After, identical expanded selection | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746`; documentation-only tree | 238 / 238 / 0 / 0 / 0 | 0; identical passed node IDs and unchanged tree status |

Revision-1 verification uses the same six selections, source package roots on `PYTHONPATH`, and a tool environment created with `uv run --no-project --no-build --with pytest` plus the required scientific, coverage, data and contract-test dependencies. No source distribution was built. Coverage and temporary outputs are directed to scratch; `--cov-report=` clears the configured report destinations and a JSON report is directed to scratch. The after run uses the documented existing-edit fingerprint mode because the pack remains uncommitted.

| Revision-1 run | Tree | Run / passed / failed / skipped / NOT_RUN | Command exit |
| --- | --- | --- | --- |
| BASE | `ae7d2268bbf2e8a07de8278ac45a2eb3b118b44d`; clean tree | 238 / 238 / 0 / 0 / 0 | 0 |
| After | Same implementation and tests; pack revision 1 uncommitted | 238 / 238 / 0 / 0 / 0 | 0; identical passed node IDs; initial dirty bytes preserved |

Citation self-check: **242 occurrences**, **196 unique ranges**, **64 pinned files**, **0 range-resolution failures**. Ten manually read changed citations (SF1–SF8, production pack D5/D8 and the scheduler semester resolver) match their claims. All **7 explicit test node IDs** resolve through collection and pass; the bare C0a form at BASE fails the path-form check and its corrected form passes.

Two environment setup attempts stopped before collection: an unsupported wheel-only option, then missing `pydantic_settings`. The supported `--no-build` option and required wheel dependencies resolved both before the BASE run; neither is counted as a test failure.

The module-local count is **84** tests, rather than the inventory lead of 89; direct adapter and scheduler callers add **9**, and the expanded selection adds **145** compatibility, parity and contract tests (offline execution records above; test-file inventory table).

### Documentation discovery

The following 20 Markdown files were found under `docs/` by searching `brazil_anp` or `Brazil ANP`; matching passages were inspected, while complete archival-document revalidation is deferred to #349. Current source-refresh metadata reconciliation is #917. [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L17-L44] [data/source-refresh-acceptance-contract.json:L15-L15]

| Discovery file | Relevant passage |
| --- | --- |
| `docs/ci/flake8-inventory-2026-04-23.md` | [docs/ci/flake8-inventory-2026-04-23.md:L147-L147] |
| `docs/modules/repository-architecture.md` | [docs/modules/repository-architecture.md:L104-L104] |
| `docs/adr/0001-domain-package-split.md` | [docs/adr/0001-domain-package-split.md:L48-L48] |
| `docs/plans/2026-05-04-issue-349-capability-inventory-audit.md` | [docs/plans/2026-05-04-issue-349-capability-inventory-audit.md:L21-L21] |
| `docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md` | [docs/plans/2026-07-05-issue-809-spain-cores-refresh-job.md:L49-L49] |
| `docs/plans/2026-05-08-issue-394-repo-structure-normalization.md` | [docs/plans/2026-05-08-issue-394-repo-structure-normalization.md:L73-L73] |
| `docs/plans/2026-05-04-issue-360-scheduler-health.md` | [docs/plans/2026-05-04-issue-360-scheduler-health.md:L38-L38] |
| `docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md` | [docs/plans/2026-06-09-issue-462-source-refresh-acceptance-contract.md:L27-L27] |
| `docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md` | [docs/plans/2026-04-27-issue-354-reconcile-capability-indexes.md:L126-L126] |
| `docs/plans/2026-05-04-issue-269-sodir-brazil-ukcs-adapters.md` | [docs/plans/2026-05-04-issue-269-sodir-brazil-ukcs-adapters.md:L1-L1] |
| `docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md` | [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L1-L1] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.issue-comment.md:L15-L15] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-overnight-commands.md:L41-L41] |
| `docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md` | [docs/reports/2026-04-26-worldenergydata-data-completeness-scorecard.md:L16-L16] |
| `docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md` | [docs/reports/2026-04-26-worldenergydata-capability-readiness-matrix.md:L16-L16] |
| `docs/reports/scheduler-health-2026-W24.md` | [docs/reports/scheduler-health-2026-W24.md:L15-L15] |
| `docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md` | [docs/reports/2026-04-26-worldenergydata-overnight-capability-batch.md:L69-L69] |
| `docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md` | [docs/reports/2026-04-26-issue-353-timeout-isolation-probe.md:L202-L202] |
| `docs/reports/data-freshness-scorecard-2026-06-08.md` | [docs/reports/data-freshness-scorecard-2026-06-08.md:L5-L5] |
| `docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md` | [docs/reports/2026-04-26-worldenergydata-scheduler-runtime-readiness.md:L12-L12] |

Broader shared tests were also discovered by string search in audit, router, project_economics integration/registration, scheduler configuration/health and skeleton-adapter suites; these were not executed as module-focused tests, and no results for those broader suites are asserted; coverage follow-up is #349. [tests/unit/production/unified/test_router.py:L1-L30] [tests/unit/scheduler/test_config.py:L1-L30]

### Open-item register

Every item below is assigned to module maintainers for disposition; an issue-pending marker identifies its numbered draft, to be replaced with an opened issue before independent clearance (module lifecycle revision 0, section 3 item 10).

| Item | Evidence or limitation | Issue |
| --- | --- | --- |
| Source and independent benchmark qualification | The UNVERIFIED statement in section 3; no live source data or reference publication was opened; section 4 contains no independently validated case; live data-service availability is tracked separately | issue pending (1); #1096; fiscal integration #737 |
| Input rejection and overlap accounting | C0c and section-6 ingestion findings, SW1–SW6 and scheduler semester route S6 | #1291; issue pending (2) |
| Decline time basis and fallback disposition | C2b and section-6 fitting findings | issue pending (3) |
| Metadata edge handling | Null environment, numeric decimal parsing, well-count fallback, missing labels, ambiguous selection and incomplete metadata (SF6/SF8, SW7/SW8) | #1291; issue pending (4) |
| Shared empty-production default | SF1; include all five sibling chains in the existing shared follow-up; the placeholder chain has a distinct output label | #1289 |
| Silent summaries and fiscal inputs | SF2/SF3/SF7 and SW11; detection checks remain absent | #1291; issue pending (1) |
| Documentation packaging | Recursive Markdown package-data pattern includes this path; exclusion from wheel resources is not established by this change. [packages/worldenergydata-brazil_anp/pyproject.toml:L56-L57] | issue pending (5) |
| Map, dependency ownership and shared-log coverage | No module map families; standalone dependency completeness, deputy designation and shared-log registration remain open | issue pending (6) |
| Identifying fixture labels | Discovery fixtures contain identifying text; only anonymous case IDs and numeric inputs are reproduced in this pack. [tests/unit/brazil_anp/test_well_production.py:L14-L24] [tests/unit/brazil_anp/test_brazil_field_concept.py:L13-L46] | issue pending (7) |
| Archive and broader shared-test coverage | Discovery inventory above; historical claims and unrelated shared-suite behaviour are not revalidated | #349 |
| Source-refresh metadata drift | Closed historical incident still used as blocker in the contract | #917 |

Not exercised: live monthly ZIP download and live field, platform and well metadata tables.

UNVERIFIED: live data freshness, current-source rights and intended-use readiness, complete standalone installation behaviour and exclusion of this document from built wheels are not established; issue pending (1), issue pending (5), issue pending (6), and #917.

No routing registry is present at the pinned repository revision; no registry entry is added. The pack is placed within the existing package scope only. [packages/worldenergydata-brazil_anp/pyproject.toml:L51-L57]
