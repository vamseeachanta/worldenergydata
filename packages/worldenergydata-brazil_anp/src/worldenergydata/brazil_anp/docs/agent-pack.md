# Brazil ANP module knowledge pack

| Header | Value |
| --- | --- |
| Module | `brazil_anp` |
| Repository | `worldenergydata` |
| Package path | `packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp` |
| Pack revision | 0 |
| Code revision | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` |
| Analysis family | EC; data pipelines, using the Python calculations gates of AQG r0 section 10 |
| Quality manager role | Calculations quality manager, pending a dedicated data quality manager |
| Status | DRAFT; independent clearance pending |

## 1. Purpose and scope

The module downloads monthly production ZIPs, normalizes well records, aggregates field-month totals, fits decline curves, evaluates illustrative fiscal calculations and connects production to concept screening and pre-tax cashflow. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L53-L99] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L40-L76] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L14-L48] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L62-L98] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L109] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L69]

The reference chain labels its economics `chain_plumbing_pre_tax`; it supplies empty drilling costs and defaults an unknown development system to `subsea15`, so its result is not an investment decision basis. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L43-L69]

Concession royalty bands are explicitly illustrative and require a governing contract and case before fiscal-deck use. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L1-L6] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L92]

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
| Fiscal arguments | Revenue, opex and capex in a caller-consistent currency and period; production bbl/day; share dimensionless | PSA share default 0.50; concession basis not qualified by the interface | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L81] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L133-L146] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L162-L176] |
| Reference-chain arguments | Adapter, metadata, field selector, optional start/end; oil price USD/bbl | Price default 75.0; region `brazil` | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L46] |

### Outputs

| Output | Units and conventions | Evidence |
| --- | --- | --- |
| Client DataFrame | CSV strings plus partition marker `location_source`; no CSV is returned as an empty DataFrame | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L110-L142] |
| Normalized well DataFrame | `oil_bbl`, `condensate_bbl`, `water_bbl` monthly bbl; `gas_mcf` monthly Mcf; `oil_bbl_per_day` bbl/day; current schema retains source metadata but does not return `gas_m3` | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L92-L110] |
| Field DataFrame and summary | Sums by field/date; unique well count; water fraction dimensionless; monthly oil peak and mean of field-month daily rates | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L31-L67] |
| `DeclineCurveResult` | Initial rate and RMSE inherit input units; decline per retained interval; R² and b dimensionless; integer prediction starts at t=0 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L28-L56] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L117-L124] |
| `FiscalResult` | Caller currency for amounts; tax rate dimensionless; no period/currency conversion | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L61-L70] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L140-L156] |
| Reference-chain dictionary | Unified/FDAS tables, concept rankings, pre-tax label; cashflow metrics USD and month counts | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L85] |

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
| R5 | In-memory loader and metadata fixtures | 2 months; finite cashflow USD; pre-tax label and ranked concept assertion; exact predicates | `tests/unit/brazil_anp/test_reference_chain.py::test_reference_chain_runs_production_fdas_cashflow_and_concept_screening` | PASS; wiring only. [tests/unit/brazil_anp/test_reference_chain.py:L58-L72] |
| R6 | Code-pinned illustrative band fixtures | Exact inclusive boundary outputs; zero revenue returns 0 currency units | `tests/unit/brazil_anp/test_field_economics.py::test_royalty_band_values_and_boundaries_regression_pin` | PASS; legal validity is excluded. [tests/unit/brazil_anp/test_field_economics.py:L254-L280] |

## 5. QA gates

AQG r0 section 10, Python calculations, supplies G0–G2; G3 and G4 are inapplicable; section 9 supplies G5. The following checks are acceptance definitions for this module, not a declaration that a production dataset has passed every gate (AQG r0 sections 9–11).

| Gate | Applicability | Check ID and executable route | Numeric pass criterion and unit | Evidence and current disposition |
| --- | --- | --- | --- | --- |
| G0 | Applicable: input schema and units | C0a: `TestUnitConversions::test_convert_mm3_to_m3` in the well test file | `convert_mm3_to_m3(1.0)` =1000.0 m³; absolute error 0.0 m³ | PASS in offline tests. [tests/unit/brazil_anp/test_well_production.py:L38-L42] |
| G0 | Applicable: source selection | C0b: R1 plus cached-month test | 3 records; 0 HTTP calls when cache is present | PASS with mock source only. [tests/unit/brazil_anp/test_anp_client.py:L130-L142] |
| G0 | Applicable: provenance | C0c: compare input row counts before/after `WellProductionLoader.load`; inspect invalid periods and blank rates; compare duplicate-key values before retention | 0 unexplained dropped rows; 0 unqualified blank-to-zero substitutions; 0 conflicting retained duplicates (units: records) | Proposed detection; targeted tests absent, issue pending (2). [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L78-L90] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L139-L145] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L172-L204] |
| G1 | Applicable: Python import and tests; no external program load route | C1: run the complete test selection recorded in section 10, with normal test collection and tree-preservation checks | 238 tests passed; 0 failed; 0 skipped; 0 collection errors (unit: tests) | Baseline confirmed PASS; final run is recorded in section 10. [tests/unit/brazil_anp/test_reference_chain.py:L58-L72] [tests/contracts/test_assetutilities_engine_contract.py:L1-L29] |
| G2 | Applicable: independent arithmetic and reference qualification | C2a: R3; sum the two fixture oil inputs separately and compare `FieldProductionAggregator.aggregate` | Expected 597531.0 bbl; absolute error <1.0 bbl | PASS for arithmetic; independent production benchmark remains issue pending (1). [tests/unit/brazil_anp/test_field_production.py:L42-L48] |
| G2 | Applicable: fitting behaviour | C2b: R4; inspect elapsed intervals and optimizer failure status before using a forecast | R² >0.9 (unit 1) on the seeded case; 0 unmarked fallbacks and 0 compressed missing intervals (unit: events) | R² assertion PASS; failure/time criteria need targeted tests, issue pending (3). [tests/unit/brazil_anp/test_decline_curves.py:L60-L66] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L62-L75] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L125-L132] |
| G3 | NOT_APPLICABLE: no dynamics integration in the module method set | No dynamics check | Not applicable | The production fit computes rates and scalar fit metrics, not time-domain dynamics. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L28-L56] |
| G4 | NOT_APPLICABLE: no diffraction body or mesh calculation in this scope | No diffraction check | Not applicable | Metadata and monthly production are the inputs of this chain. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L41] |
| G5 | Applicable: reproducible QA evidence | C5: attach machine-readable case status, source revision/digest, units, input fingerprint and disposition to every reported result; recompute fingerprints before consumption | 0 missing evidence fields; 0 fingerprint mismatches; 0 unexplained report values (unit: records) | Not established for a production dataset; issue pending (1). The chain returns results without such a record. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L85] |

Checks defined: G0 **3**, G1 **1**, G2 **2**, G3 **0**, G4 **0**, G5 **1**; **7 total** (AQG r0 sections 9–10; check definitions above).

## 6. Known failure modes and pitfalls

| Symptom | Cause and detection | Incident or follow-up; recorded date | Evidence |
| --- | --- | --- | --- |
| Missing values become zero; malformed periods disappear | Coercion then row filtering; C0c must count rejected rows and missingness; **no targeted detection check exists** | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L78-L90] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L139-L145] |
| Expected overlap can conceal conflicting production | Partition preference without value comparison; C0c; **no targeted detection check exists** for conflicting values | issue pending (2); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L172-L204] |
| Fit failure returns a default fit or another model | Broad exception fallback; C2b; **no targeted detection check exists** for optimizer failure | issue pending (3); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L125-L132] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L160-L161] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L188-L189] |
| Forecast uses compressed history or restarts at zero | Filtering before integer-index construction; integer `predict` uses `range(periods)`; C2b; **no targeted detection check exists** for dated gaps | issue pending (3); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L38-L54] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L62-L75] |
| Missing environment raises; numeric depth changes magnitude | Empty non-null selection indexed at zero; numeric value string stripped of decimal points; **no detection check exists** for these metadata edges | issue pending (4); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L118-L133] |
| Synthetic adapter output mistaken for observed production | Adapter without an injected loader generates profiles; require real-source status and C5; synthetic compatibility tests do not establish freshness | issue pending (1); 2026-10-16 | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L39-L70] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L138-L175] |
| Configured download previously returned HTTP 404 | Historical incident; C0b verifies monthly URL/cache contract; scheduler failure test verifies failure status; live reachability is not established by mock tests | Existing issue 459, closed; 2026-10-16 | [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L24-L32] [tests/unit/brazil_anp/test_anp_client.py:L112-L128] [tests/unit/scheduler/test_brazil_anp_refresh.py:L110-L124] |
| Royalty bands mistaken for qualified fiscal terms | Explicit illustrative marker; R6 checks compatibility, not law; qualification-marker and shipped-deck tests detect loss of that boundary | Existing issue 1182, closed; remaining fiscal seam issue 737, open; 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L28-L39] [tests/unit/brazil_anp/test_field_economics.py:L189-L251] |
| Pre-tax chain mistaken for full project economics | Empty drilling costs, default development system, pre-tax output label; R5 detects the label; no independent investment check exists | Existing issue 737; issue pending (1); 2026-10-16 | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L43-L69] |
| Refresh metadata still describes an obsolete blocker | Source-refresh contract still lists closed incident 459; reconcile live qualification separately, C5 | Existing issue 917; 2026-10-16 | [data/source-refresh-acceptance-contract.json:L15-L15] |

Issue references use repository issue numbers; historical incidents are distinguished from current code observations, and no new live download has been performed. [tests/unit/brazil_anp/test_anp_client.py:L112-L128]

## 7. Lessons log

| Date | Change reference | Lesson and pack change | Evidence | Shared-log entry |
| --- | --- | --- | --- | --- |
| 2026-10-16 | Pack revision 0 | Separate code regression from source qualification; sections 3–6 retain illustrative, synthetic and pre-tax limits | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L1-L6] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L61-L69] | Pending maintainer registration; issue pending (6) |

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
| Upstream/downstream | Shared metadata normalizer, unified query/adapter, FDAS cashflow and assumptions, concept recommendation | [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L18-L28] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L56-L61] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L31-L59] |
| Downstream | Scheduler writes raw and normalized month snapshots and refresh metadata | [packages/worldenergydata-scheduler/src/worldenergydata/scheduler/jobs/brazil_anp_refresh.py:L47-L77] |
| Downstream | Loader-backed adapter supplies canonical monthly columns; no-loader route remains synthetic | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L39-L70] [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L113-L136] |

The package declares core, NumPy, pandas, SciPy and scikit-learn dependencies; metadata/concept/cashflow use additional sibling packages in the workspace, so standalone dependency completeness is not asserted. [packages/worldenergydata-brazil_anp/pyproject.toml:L26-L36] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L31-L59]

### Implementation-map inventory and A8

Map authority: **digitalmodel**, `docs/registry/implementation-map.yaml`, branch `codex/implmap-work`, branch commit `b5acbe5f61ed4c755c1f7ea4fafa4611bd14e407`, map data revision `947fa50ff9a9e210de7e8f90e01b37add85c5954` (Implementation map, schema version 1, `revision`, `families` and `implementations` records).

The parsed map contains **13 families**, **0 implementation rows inside this package**, **0 module map families** and therefore **0 counted families**; section-9 inventory is empty, and the counted-family grep is **NOT_APPLICABLE: no map family has an implementation row in the package** (Implementation map, pinned branch commit above, all `families[].implementations[].path` records).

Map follow-up, issue pending (6): ZIP/CSV ingestion and overlap resolution; current/legacy production normalization; field-month aggregation; exponential/hyperbolic/harmonic decline fitting and prediction; fiscal royalty, participation and profit-oil calculations; metadata normalization and reference-chain orchestration. These methods are in section 3, but none is enrolled by this map revision. [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/anp_client.py:L110-L204] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/well_production.py:L40-L110] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/field_production.py:L14-L48] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/production/decline_curves.py:L38-L197] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/analysis/field_economics.py:L73-L187] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/field_concept.py:L31-L66] [packages/worldenergydata-brazil_anp/src/worldenergydata/brazil_anp/reference_chain.py:L21-L69]

### Further repository search

A repository-wide Python text search, including `scripts/`, used `decline`, the three fiscal function names and the client/loader/aggregator class names; further-search findings do not alter the counted-family result. Comparable decline formulas compute directly in the following definitions, rather than delegating to this module. [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L48-L70] [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L206-L258]

| Candidate | Classification and disposition | Evidence |
| --- | --- | --- |
| `sodir.forecasting.DeclineCurve.predict`, `ProductionForecaster._fit_exponential_decline`, `_fit_hyperbolic_decline` | Independent decline calculations outside package; map follow-up, issue pending (6) | [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L48-L70] [packages/worldenergydata-sodir/src/worldenergydata/sodir/forecasting.py:L150-L233] |
| `production.forecast.decline.ArpsDeclineCurve._fit_params`, `_rate_fn` | Independent decline calculations outside package; map follow-up, issue pending (6) | [packages/worldenergydata-production/src/worldenergydata/production/forecast/decline.py:L206-L277] |
| `BrazilAnpAdapter._generate_field_rows` | Synthetic profile generator outside package; separate from measured production ingestion; follow-up, issue pending (6) | [packages/worldenergydata-production/src/worldenergydata/production/unified/adapters/brazil_anp_adapter.py:L138-L175] |

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
| `tests/unit/brazil_anp/test_reference_chain.py` | 1 | Offline PASS. [tests/unit/brazil_anp/test_reference_chain.py:L1-L72] |
| `tests/unit/brazil_anp/test_well_production.py` | 18 | Offline PASS. [tests/unit/brazil_anp/test_well_production.py:L1-L171] |
| `tests/unit/production/unified/test_brazil_anp_adapter_loader.py` | 4 | Offline PASS. [tests/unit/production/unified/test_brazil_anp_adapter_loader.py:L1-L124] |
| `tests/unit/scheduler/test_brazil_anp_refresh.py` | 5 | Offline PASS. [tests/unit/scheduler/test_brazil_anp_refresh.py:L1-L132] |
| `tests/unit/production/unified/test_adapters.py` | 94 | Offline PASS. [tests/unit/production/unified/test_adapters.py:L1-L205] |
| `tests/unit/fdas/fiscal/test_deck_parity.py` | 5 | Offline PASS. [tests/unit/fdas/fiscal/test_deck_parity.py:L1-L160] |
| `tests/contracts/test_assetutilities_data_contract.py` | 5 | Offline PASS. [tests/contracts/test_assetutilities_data_contract.py:L1-L51] |
| `tests/contracts/test_assetutilities_engine_contract.py` | 3 | Offline PASS. [tests/contracts/test_assetutilities_engine_contract.py:L1-L31] |
| `tests/contracts/test_flaky_register_schema.py` | 38 | Offline PASS. [tests/contracts/test_flaky_register_schema.py:L1-L237] |

Offline command form: `uv run python -m pytest` followed by the 6 selections in the table (the module directory, direct adapter/scheduler files, general adapter file, fiscal parity file and contracts directory), `-q -rA -p no:cacheprovider --allow-existing-tree-changes --basetemp=<scratch directory>`. The documented tree mode hashes initially dirty paths and fails on changed bytes or additional dirty paths; it does not exempt the pack from preservation. [docs/development/index.md:L45-L64]

| Run | Code revision | Run / passed / failed / skipped / NOT_RUN | Command exit |
| --- | --- | --- | --- |
| Initial baseline, module and direct callers | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` | 93 / 93 / 0 / 0 / 0 | 1: the new pack appeared during the run; tree-preservation guard rejected the change. [tests/conftest.py:L431-L456] |
| Baseline confirmation, expanded selection | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746` | 238 / 238 / 0 / 0 / 0 | 0; existing-edit fingerprints preserved. [tests/conftest.py:L413-L451] |
| After, identical expanded selection | `3cad44fa0b5d4a5a4a8798cb6cb2dc15739ee746`; documentation-only tree | 238 / 238 / 0 / 0 / 0 | 0; identical passed node IDs and unchanged tree status |

The module-local count is **84** tests, rather than the inventory lead of 89; direct adapter and scheduler callers add **9**, and the expanded selection adds **145** compatibility, parity and contract tests (offline execution records above; test-file inventory table).

### Documentation discovery

The following 20 Markdown files were found under `docs/` by searching `brazil_anp` or `Brazil ANP`; matching passages were inspected, while complete archival-document revalidation is deferred to existing issue 349. Current source-refresh metadata reconciliation is existing issue 917. [docs/plans/2026-07-04-issue-718-brazil-anp-reference-chain.md:L17-L44] [data/source-refresh-acceptance-contract.json:L15-L15]

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

Broader shared tests were also discovered by string search in audit, router, FDAS integration/registration, scheduler configuration/health and skeleton-adapter suites; these were not executed as module-focused tests, and no results for those broader suites are asserted; coverage follow-up is existing issue 349. [tests/unit/production/unified/test_router.py:L1-L30] [tests/unit/scheduler/test_config.py:L1-L30]

### Open-item register

Every item below is assigned to module maintainers for disposition; an issue-pending marker identifies its numbered draft, to be replaced with an opened issue before independent clearance (module lifecycle revision 0, section 3 item 10).

| Item | Evidence or limitation | Issue |
| --- | --- | --- |
| Source and independent benchmark qualification | The UNVERIFIED statement in section 3; no live source data or reference publication was opened; section 4 contains no independently validated case | issue pending (1); fiscal integration remains existing issue 737 |
| Input rejection and overlap accounting | C0c and section-6 ingestion findings | issue pending (2) |
| Decline time basis and fallback disposition | C2b and section-6 fitting findings | issue pending (3) |
| Metadata edge handling | Null environment and numeric decimal parsing | issue pending (4) |
| Documentation packaging | Recursive Markdown package-data pattern includes this path; exclusion from wheel resources is not established by this change. [packages/worldenergydata-brazil_anp/pyproject.toml:L56-L57] | issue pending (5) |
| Map, dependency ownership and shared-log coverage | No module map families; standalone dependency completeness, deputy designation and shared-log registration remain open | issue pending (6) |
| Identifying fixture labels | Discovery fixtures contain identifying text; only anonymous case IDs and numeric inputs are reproduced in this pack. [tests/unit/brazil_anp/test_well_production.py:L14-L24] [tests/unit/brazil_anp/test_brazil_field_concept.py:L13-L46] | issue pending (7) |
| Archive and broader shared-test coverage | Discovery inventory above; historical claims and unrelated shared-suite behaviour are not revalidated | Existing issue 349 |
| Source-refresh metadata drift | Closed historical incident still used as blocker in the contract | Existing issue 917 |

UNVERIFIED: live data freshness, current-source rights and intended-use readiness, complete standalone installation behaviour and exclusion of this document from built wheels are not established; issue pending (1), issue pending (5), issue pending (6), and existing issue 917.

No routing registry is present at the pinned repository revision; no registry entry is added. The pack is placed within the existing package scope only. [packages/worldenergydata-brazil_anp/pyproject.toml:L51-L57]
