# Lower Tertiary Comprehensive Field Report

**Revision: C**
**Issue date:** 2026-10-15
**Fields:** 10 GoM Lower Tertiary fields

---

## Executive Summary

- Economic basis: constant scenario oil price $70.0/bbl; discount rate 10.0%; before corporate tax. Costs are assumed (unsourced configuration value, #651), at the configuration dates.
- Portfolio totals: 10 fields, $55,500 M aggregate scenario capex
- Strongest economics: **Shenandoah** (NPV $8,569.8 M @ 10.0%, breakeven $26.3/bbl)
- Marginal at base case: Julia (NPV < 0 at $70.0/bbl with documented decline-curve cashflow)
- Operator concentration: Among fields with uncontested configuration working interests (publicly sourced for Julia only), BP has the largest working-interest-weighted scenario capex share, 39.9% across two fields.
- Dominant tech generation: **Subsea 20K** (5 fields, $31,400 M total scenario capex)
- Pre-FID configurations: 3 fields classified pre-FID; current sanction status is not established. Capital estimates are assumed.
- Caveats: cashflow basis is documented decline-curve (OGOR-grounded follow-up under #367); HSE coverage minimum-viable pending #366; live cost benchmarking pending #343 + #344

---

## Revision history

| revision | date | change |
|---|---|---|
| A | 2026-10-14 | First issue combines ten-field scenario economics, source references and explicit data gaps to support comparisons on a stated assumption basis. |
| B | 2026-10-14 | Public sources and retrieval dates are attached to their input keys; unsourced field inputs are labelled as assumptions. Contradicted or unverified working interests are excluded from concentration comparisons. |
| C | 2026-10-15 | Operator citation corrected to exclude evidence predating the configured role; share lines qualified by configuration working interests and scenario capex; reporting tests collected by CI so publication contracts run on pull requests. |

Revision history: each row identifies an issue and its reason.

## Economic basis

Oil-price deck: $70.0/bbl, constant nominal scenario; discount rate: 10.0%; reinvestment rate: 6.0%; horizon: 20 years; plateau duration: 3 years; annual decline: 8.0%. Unsourced field inputs are assumed (unsourced configuration value, #651). Generic discount, reinvestment and decline rates and horizon defaults are assumed, based on previous experience. Capital is charged at inception; oil-only cashflows deduct operating costs and the configured royalty, before corporate tax. NPV is discounted to model inception, without calendar-year alignment. Gas revenue, escalation and decommissioning are not modelled. Paired development entries retain combined capital and plateau rates; separate field splits are not established. Configuration dates govern the input basis; the issue date does not refresh those inputs. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

## Portfolio Economics — All Fields

| field_id | display_name | status | operator | capex_mm_usd | plateau_thousand_bbl_per_day | npv_mm_usd | irr_annual_pct | mirr_annual_pct | payback_years | breakeven_oil_usd_per_bbl | cashflow_basis | npv_mm_usd_at_$50 | npv_mm_usd_at_$60 | npv_mm_usd_at_$70 | npv_mm_usd_at_$80 | npv_mm_usd_at_$100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anchor | Anchor | producing | Chevron | 5,600.0 | 75.0 | 2,177.4 | 17.3 | Not established | 5.0 | 55.2 | documented_decline_curve_v1 | -765.4 | 706.0 | 2,177.4 | 3,648.8 | 6,591.5 |
| big_foot | Big Foot | producing | Chevron | 5,200.0 | 75.0 | 2,577.4 | 19.2 | Not established | 5.0 | 52.5 | documented_decline_curve_v1 | -365.4 | 1,106.0 | 2,577.4 | 4,048.8 | 6,991.5 |
| cascade_chinook | Cascade/Chinook | producing | Murphy | 2,900.0 | 75.0 | 4,372.9 | 36.9 | Not established | 3.0 | 40.3 | documented_decline_curve_v1 | 1,430.1 | 2,901.5 | 4,372.9 | 5,844.3 | 8,787.1 |
| jack_st_malo | Jack/St. Malo | producing | Chevron | 7,500.0 | 94.0 | 2,247.6 | 15.6 | Not established | 5.0 | 57.8 | documented_decline_curve_v1 | -1,440.7 | 403.5 | 2,247.6 | 4,091.8 | 7,780.1 |
| julia | Julia | producing | ExxonMobil | 4,700.0 | 34.0 | -1,403.0 | 4.0 | Not established | 12.0 | 91.0 | documented_decline_curve_v1 | -2,737.0 | -2,070.0 | -1,403.0 | -735.9 | 598.1 |
| kaskida | Kaskida | pre_fid | BP | 10,000.0 | 120.0 | 2,443.8 | 14.6 | Not established | 6.0 | 59.6 | documented_decline_curve_v1 | -2,264.7 | 89.6 | 2,443.8 | 4,798.0 | 9,506.5 |
| north_platte | North Platte | pre_fid | TotalEnergies | 6,000.0 | 75.0 | 1,777.4 | 15.6 | Not established | 5.0 | 57.9 | documented_decline_curve_v1 | -1,165.4 | 306.0 | 1,777.4 | 3,248.8 | 6,191.5 |
| shenandoah | Shenandoah | under_development | Beacon Offshore Energy | 1,800.0 | 100.0 | 8,569.8 | 91.7 | Not established | 2.0 | 26.3 | documented_decline_curve_v1 | 4,646.1 | 6,608.0 | 8,569.8 | 10,531.7 | 14,455.4 |
| stones | Stones | producing | Shell | 3,800.0 | 50.0 | 1,384.9 | 16.8 | Not established | 5.0 | 55.9 | documented_decline_curve_v1 | -576.9 | 404.0 | 1,384.9 | 2,365.8 | 4,327.7 |
| tiber | Tiber | pre_fid | BP | 8,000.0 | 80.0 | 295.9 | 10.7 | Not established | 7.0 | 68.1 | documented_decline_curve_v1 | -2,843.1 | -1,273.6 | 295.9 | 1,865.3 | 5,004.3 |

Portfolio economics, using the economic basis above.

## Cross-Field Analytics

### Technology Generation

| dev_system | field_count | fields | total_capex_mm_usd | mean_capex_usd_per_bbl_proxy | total_recoverable_mmbbl_proxy | total_npv_mm_usd | mean_breakeven_usd_per_bbl | caveats |
|---|---|---|---|---|---|---|---|---|
| Dry Tree | 1 | big_foot | 5,200.0 | 9.5 | 547.5 | 2,577.4 | 52.5 | recoverable_mmbbl_proxy uses plateau×20yr — OGOR-grounded follow-up under #367 |
| Subsea 15K | 3 | cascade_chinook, jack_st_malo, stones | 14,200.0 | 8.9 | 1,598.7 | 8,005.4 | 51.3 | recoverable_mmbbl_proxy uses plateau×20yr — OGOR-grounded follow-up under #367 |
| Subsea 20K | 5 | anchor, kaskida, north_platte, shenandoah, tiber | 31,400.0 | 9.8 | 3,285.0 | 15,264.2 | 53.4 | recoverable_mmbbl_proxy uses plateau×20yr — OGOR-grounded follow-up under #367 |
| Tieback 15K | 1 | julia | 4,700.0 | 18.9 | 248.2 | -1,403.0 | 91.0 | recoverable_mmbbl_proxy uses plateau×20yr — OGOR-grounded follow-up under #367 |

Technology comparisons, using a plateau-equivalent recovery proxy.

### Operator Concentration

| company | field_count | sum_wi_capex_mm_usd | sum_wi_plateau_thousand_bbl_per_day | share_capex_pct | hhi_contribution |
|---|---|---|---|---|---|
| BP | 2 | 18,000.0 | 200.0 | 39.9 | 1,592.9 |
| TotalEnergies | 2 | 6,700.0 | 84.4 | 14.9 | 220.7 |
| Chevron | 2 | 6,620.0 | 91.9 | 14.7 | 215.5 |
| Equinor | 3 | 5,180.0 | 56.4 | 11.5 | 131.9 |
| Shell | 1 | 3,800.0 | 50.0 | 8.4 | 71.0 |
| ExxonMobil | 1 | 2,350.0 | 17.0 | 5.2 | 27.2 |
| Beacon Offshore Energy | 1 | 1,800.0 | 100.0 | 4.0 | 15.9 |
| Marubeni Oil & Gas | 1 | 650.0 | 9.4 | 1.4 | 2.1 |

Cascade/Chinook and Jack/St. Malo excluded: working interests contradicted or unverified. Shares and concentration index use only the remaining fields. Among fields with uncontested configuration working interests (publicly sourced for Julia only), BP has the largest working-interest-weighted scenario capex share, 39.9% across two fields.

### HSE per Field (minimum-viable; full coverage pending #366)

| field_id | incident_count | incidents_per_mmbbl | data_completeness | source |
|---|---|---|---|---|
| anchor | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| big_foot | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| cascade_chinook | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| jack_st_malo | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| julia | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| kaskida | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| north_platte | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| shenandoah | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| stones | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |
| tiber | Not established | Not established | minimum_viable_pending_#366 | placeholder pending #366 (HSE bulk dedup + ingest) |

HSE availability; missing counts are not measured zeroes.

### Cost Benchmark vs Disclosures (no_data pending #343)

| field_id | operator | modelled_capex_mm_usd | disclosed_capex_mm_usd | delta_pct | benchmark_status | caveats |
|---|---|---|---|---|---|---|
| anchor | Chevron | 5,600.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| big_foot | Chevron | 5,200.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| cascade_chinook | Murphy | 2,900.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| jack_st_malo | Chevron | 7,500.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| julia | ExxonMobil | 4,700.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| kaskida | BP | 10,000.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| north_platte | TotalEnergies | 6,000.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| shenandoah | Beacon Offshore Energy | 1,800.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| stones | Shell | 3,800.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |
| tiber | BP | 8,000.0 | Not established | Not established | no_data_pending_#343 | Live benchmark requires #343 (operator registry) + #344 (restatement lineage) to seed the project_revision_view. |

Cost comparison availability, using scenario capital costs.

---

## Per-Field Detail

### Anchor (`anchor`)

- **Status:** producing
- **Operator:** Chevron
- **First oil:** 2024-08-01
- **Capex:** $5,600 M total
- **Plateau:** 75 thousand bbl/day
- **NPV @ 10.0%:** $2,177.4 M
- **Payback:** 5.0 years
- **Breakeven oil price:** $55.2/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -765.4 |
| 60.0 | 706.0 |
| 70.0 | 2,177.4 |
| 80.0 | 3,648.8 |
| 100.0 | 6,591.5 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $5,600.0 M | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.capex.total_mm_usd | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 75.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.production_profile.plateau_rate_mbopd | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.opex_per_boe | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.first_oil | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.data_through | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.operator | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.status | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | worldenergydata | config/analysis/lower_tertiary/fields/anchor.yml#field.partners | sha256:d20c5e685f139b2ac202a481c4b82d79e5eed8345afbae491f3ad5d712b6113a | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Big Foot (`big_foot`)

- **Status:** producing
- **Operator:** Chevron
- **First oil:** 2018-11-01
- **Capex:** $5,200 M total
- **Plateau:** 75 thousand bbl/day
- **NPV @ 10.0%:** $2,577.4 M
- **Payback:** 5.0 years
- **Breakeven oil price:** $52.5/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -365.4 |
| 60.0 | 1,106.0 |
| 70.0 | 2,577.4 |
| 80.0 | 4,048.8 |
| 100.0 | 6,991.5 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $5,200.0 M | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.capex.total_mm_usd | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 75.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.production_profile.plateau_rate_mbopd | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.opex_per_boe | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.first_oil | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.data_through | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.operator | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.status | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | worldenergydata | config/analysis/lower_tertiary/fields/big_foot.yml#field.partners | sha256:605e7701cab20fdd8a213664aed1ca38339e4a019b7b73f214aaf3320355c31e | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Cascade/Chinook (`cascade_chinook`)

- **Status:** producing
- **Operator:** Murphy
- **First oil:** 2012-02-01
- **Capex:** $2,900 M total
- **Plateau:** 75 thousand bbl/day
- **NPV @ 10.0%:** $4,372.9 M
- **Payback:** 3.0 years
- **Breakeven oil price:** $40.3/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | 1,430.1 |
| 60.0 | 2,901.5 |
| 70.0 | 4,372.9 |
| 80.0 | 5,844.3 |
| 100.0 | 8,787.1 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $2,900.0 M | worldenergydata | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.capex.total_mm_usd | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 75.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.production_profile.plateau_rate_mbopd | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $18.0/boe | worldenergydata | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.opex_per_boe | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | www.sec.gov | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.first_oil | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | public source recorded in configuration; not retrieved in this revision; exact first-flow day not established by this citation; configured month-start convention retained | P1 | Production Start-up of Cascade field in Gulf of Mexico ultra deep water (Petrobras), 2012-03-01 | https://www.sec.gov/Archives/edgar/data/0001119639/000129281412000476/pbra20120301_6k.htm | not retrieved in this revision | Not established | 403 |
| First-oil schedule | bwoffshore.com | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.first_oil | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | public source recorded in configuration; retrieved; exact first-flow day not established by this citation; configured month-start convention retained | P2 | First oil on BW Pioneer (BW Offshore), 2012-03-02 | https://bwoffshore.com/pressreleases/first-oil-on-bw-pioneer | 2026-10-14 | 04de52ed4035b3080dfa028341568dfba796c91951a14910866fa34590a9f8f6 | 200 |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.data_through | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | www.sec.gov | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.operator | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | public source recorded in configuration; not retrieved in this revision | P3 | Murphy Oil Closes Gulf of Mexico Joint Venture, Provides Updated Guidance and Announces New Unsecured Credit Facility, 2018-12-03 | https://www.sec.gov/Archives/edgar/data/0000717423/000071742318000050/mur-20181203xex99_1.htm | not retrieved in this revision | Not established | 403 |
| Operator | www.sec.gov | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.operator | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | public source recorded in configuration; not retrieved in this revision | P5 | Murphy Oil Corporation annual report, FY2025 (filed 2026) | https://www.sec.gov/Archives/edgar/data/717423/000162828026011709/mur-20251231.htm | not retrieved in this revision | Not established | 403 |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.status | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | www.sec.gov | config/analysis/lower_tertiary/fields/cascade_chinook.yml#field.partners | sha256:8320764f9b3e56a770ae244ebde60b3eac2ce6786e60b0863dc033db3e79cc63 | public source recorded in configuration; not retrieved in this revision; working interests contradicted or unverified; excluded from concentration | P4 | Murphy Oil Corporation annual report, FY2018 (filed 2019) | https://www.sec.gov/Archives/edgar/data/717423/000071742319000016/mur-20181231x10k.htm | not retrieved in this revision | Not established | 403 |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Jack/St. Malo (`jack_st_malo`)

- **Status:** producing
- **Operator:** Chevron
- **First oil:** 2014-12-01
- **Capex:** $7,500 M total
- **Plateau:** 94 thousand bbl/day
- **NPV @ 10.0%:** $2,247.6 M
- **Payback:** 5.0 years
- **Breakeven oil price:** $57.8/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -1,440.7 |
| 60.0 | 403.5 |
| 70.0 | 2,247.6 |
| 80.0 | 4,091.8 |
| 100.0 | 7,780.1 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $7,500.0 M | worldenergydata | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.capex.total_mm_usd | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 94.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.production_profile.plateau_rate_mbopd | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.opex_per_boe | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | www.sec.gov | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.first_oil | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | public source recorded in configuration; not retrieved in this revision; exact first-flow day not established by this citation; configured month-start convention retained | P7 | Chevron Corporation annual report, FY2014 (filed 2015) | https://www.sec.gov/Archives/edgar/data/93410/000009341015000010/cvx-123114x10kdoc.htm | not retrieved in this revision | Not established | 403 |
| First-oil schedule | worldoil.com | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.first_oil | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | public source recorded in configuration; retrieved; exact first-flow day not established by this citation; configured month-start convention retained | P8 | Jack, St. Malo partners announce first oil from deepwater Gulf of Mexico project (World Oil), 2014-12-02 | https://worldoil.com/news/2014/12/2/jack-st-malo-partners-announce-first-oil-from-deepwater-gulf-of-mexico-project | 2026-10-14 | 621f3bb94654776468d4a7e4ee8883ce1efa3513712eff3d80187dff6cb3af5b | 200 |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.data_through | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | www.sec.gov | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.operator | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | public source recorded in configuration; not retrieved in this revision | P7 | Chevron Corporation annual report, FY2014 (filed 2015) | https://www.sec.gov/Archives/edgar/data/93410/000009341015000010/cvx-123114x10kdoc.htm | not retrieved in this revision | Not established | 403 |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.status | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | www.sec.gov | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.partners | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | public source recorded in configuration; not retrieved in this revision; working interests contradicted or unverified; excluded from concentration | P7 | Chevron Corporation annual report, FY2014 (filed 2015) | https://www.sec.gov/Archives/edgar/data/93410/000009341015000010/cvx-123114x10kdoc.htm | not retrieved in this revision | Not established | 403 |
| Working-interest shares | worldoil.com | config/analysis/lower_tertiary/fields/jack_st_malo.yml#field.partners | sha256:a3f5a8503077beee51d783c85c83218d17d123f3aa76b7543aa7259311ab8079 | public source recorded in configuration; retrieved; working interests contradicted or unverified; excluded from concentration | P8 | Jack, St. Malo partners announce first oil from deepwater Gulf of Mexico project (World Oil), 2014-12-02 | https://worldoil.com/news/2014/12/2/jack-st-malo-partners-announce-first-oil-from-deepwater-gulf-of-mexico-project | 2026-10-14 | 621f3bb94654776468d4a7e4ee8883ce1efa3513712eff3d80187dff6cb3af5b | 200 |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Julia (`julia`)

- **Status:** producing
- **Operator:** ExxonMobil
- **First oil:** 2016-03-01
- **Capex:** $4,700 M total
- **Plateau:** 34 thousand bbl/day
- **NPV @ 10.0%:** $-1,403.0 M
- **Payback:** 12.0 years
- **Breakeven oil price:** $91.0/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -2,737.0 |
| 60.0 | -2,070.0 |
| 70.0 | -1,403.0 |
| 80.0 | -735.9 |
| 100.0 | 598.1 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $4,700.0 M | worldenergydata | config/analysis/lower_tertiary/fields/julia.yml#field.capex.total_mm_usd | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 34.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/julia.yml#field.production_profile.plateau_rate_mbopd | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $18.0/boe | worldenergydata | config/analysis/lower_tertiary/fields/julia.yml#field.opex_per_boe | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/julia.yml#field.first_oil | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/julia.yml#field.data_through | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | corporate.exxonmobil.com | config/analysis/lower_tertiary/fields/julia.yml#field.operator | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | public source recorded in configuration; retrieved | P6 | ExxonMobil starts production at Julia Oil Field in the Gulf of Mexico, 2016-04-19 | https://corporate.exxonmobil.com/news/news-releases/2016/0419_exxonmobil-starts-production-at-julia-oil-field-in-the-gulf-of-mexico | 2026-10-14 | 29052f7a5b0cc7865ec9c43e1a4708c8616bb811fb009f9434cf008061c7f54f | 200 |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/julia.yml#field.status | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | corporate.exxonmobil.com | config/analysis/lower_tertiary/fields/julia.yml#field.partners | sha256:db275d8b985265daf35c062815b669ae2502e392af6e9fc087a5ba51fd6af080 | public source recorded in configuration; retrieved | P6 | ExxonMobil starts production at Julia Oil Field in the Gulf of Mexico, 2016-04-19 | https://corporate.exxonmobil.com/news/news-releases/2016/0419_exxonmobil-starts-production-at-julia-oil-field-in-the-gulf-of-mexico | 2026-10-14 | 29052f7a5b0cc7865ec9c43e1a4708c8616bb811fb009f9434cf008061c7f54f | 200 |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Kaskida (`kaskida`)

- **Status:** pre_fid
- **Operator:** BP
- **First oil:** 2032-01-01
- **Capex:** $10,000 M total
- **Plateau:** 120 thousand bbl/day
- **NPV @ 10.0%:** $2,443.8 M
- **Payback:** 6.0 years
- **Breakeven oil price:** $59.6/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -2,264.7 |
| 60.0 | 89.6 |
| 70.0 | 2,443.8 |
| 80.0 | 4,798.0 |
| 100.0 | 9,506.5 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $10,000.0 M | worldenergydata | config/analysis/lower_tertiary/fields/kaskida.yml#field.capex.total_mm_usd | sha256:059587560dd87343b4372529aed8c1960977592d4a07489f76a3786542be8eff | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 120.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/kaskida.yml#field.production_profile.plateau_rate_mbopd | sha256:059587560dd87343b4372529aed8c1960977592d4a07489f76a3786542be8eff | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_OPEX_PER_BOE | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/kaskida.yml#field.first_oil | sha256:059587560dd87343b4372529aed8c1960977592d4a07489f76a3786542be8eff | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/kaskida.yml#field.data_through | sha256:059587560dd87343b4372529aed8c1960977592d4a07489f76a3786542be8eff | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | worldenergydata | config/analysis/lower_tertiary/fields/kaskida.yml#field.operator | sha256:059587560dd87343b4372529aed8c1960977592d4a07489f76a3786542be8eff | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/kaskida.yml#field.status | sha256:059587560dd87343b4372529aed8c1960977592d4a07489f76a3786542be8eff | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### North Platte (`north_platte`)

- **Status:** pre_fid
- **Operator:** TotalEnergies
- **First oil:** 2030-01-01
- **Capex:** $6,000 M total
- **Plateau:** 75 thousand bbl/day
- **NPV @ 10.0%:** $1,777.4 M
- **Payback:** 5.0 years
- **Breakeven oil price:** $57.9/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -1,165.4 |
| 60.0 | 306.0 |
| 70.0 | 1,777.4 |
| 80.0 | 3,248.8 |
| 100.0 | 6,191.5 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $6,000.0 M | worldenergydata | config/analysis/lower_tertiary/fields/north_platte.yml#field.capex.total_mm_usd | sha256:72dcc19d42bb81435efae7d69996f7eb25ab1cc90589716584882750351514ca | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 75.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/north_platte.yml#field.production_profile.plateau_rate_mbopd | sha256:72dcc19d42bb81435efae7d69996f7eb25ab1cc90589716584882750351514ca | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_OPEX_PER_BOE | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/north_platte.yml#field.first_oil | sha256:72dcc19d42bb81435efae7d69996f7eb25ab1cc90589716584882750351514ca | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/north_platte.yml#field.data_through | sha256:72dcc19d42bb81435efae7d69996f7eb25ab1cc90589716584882750351514ca | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | worldenergydata | config/analysis/lower_tertiary/fields/north_platte.yml#field.operator | sha256:72dcc19d42bb81435efae7d69996f7eb25ab1cc90589716584882750351514ca | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/north_platte.yml#field.status | sha256:72dcc19d42bb81435efae7d69996f7eb25ab1cc90589716584882750351514ca | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Shenandoah (`shenandoah`)

- **Status:** under_development
- **Operator:** Beacon Offshore Energy
- **First oil:** 2025-10-01
- **Capex:** $1,800 M total
- **Plateau:** 100 thousand bbl/day
- **NPV @ 10.0%:** $8,569.8 M
- **Payback:** 2.0 years
- **Breakeven oil price:** $26.3/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | 4,646.1 |
| 60.0 | 6,608.0 |
| 70.0 | 8,569.8 |
| 80.0 | 10,531.7 |
| 100.0 | 14,455.4 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $1,800.0 M | worldenergydata | config/analysis/lower_tertiary/fields/shenandoah.yml#field.capex.total_mm_usd | sha256:f5cd461122c618a36968737689f19af0a1712bc4fbe28b3b8ad97c5f61219a66 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 100.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/shenandoah.yml#field.production_profile.plateau_rate_mbopd | sha256:f5cd461122c618a36968737689f19af0a1712bc4fbe28b3b8ad97c5f61219a66 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_OPEX_PER_BOE | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/shenandoah.yml#field.first_oil | sha256:f5cd461122c618a36968737689f19af0a1712bc4fbe28b3b8ad97c5f61219a66 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/shenandoah.yml#field.data_through | sha256:f5cd461122c618a36968737689f19af0a1712bc4fbe28b3b8ad97c5f61219a66 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | worldenergydata | config/analysis/lower_tertiary/fields/shenandoah.yml#field.operator | sha256:f5cd461122c618a36968737689f19af0a1712bc4fbe28b3b8ad97c5f61219a66 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/shenandoah.yml#field.status | sha256:f5cd461122c618a36968737689f19af0a1712bc4fbe28b3b8ad97c5f61219a66 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Stones (`stones`)

- **Status:** producing
- **Operator:** Shell
- **First oil:** 2016-09-01
- **Capex:** $3,800 M total
- **Plateau:** 50 thousand bbl/day
- **NPV @ 10.0%:** $1,384.9 M
- **Payback:** 5.0 years
- **Breakeven oil price:** $55.9/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -576.9 |
| 60.0 | 404.0 |
| 70.0 | 1,384.9 |
| 80.0 | 2,365.8 |
| 100.0 | 4,327.7 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $3,800.0 M | worldenergydata | config/analysis/lower_tertiary/fields/stones.yml#field.capex.total_mm_usd | sha256:7829532d7685b55cc3e5a28725bfe58b451bd5137755ad6ea5abb5476ee97314 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 50.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/stones.yml#field.production_profile.plateau_rate_mbopd | sha256:7829532d7685b55cc3e5a28725bfe58b451bd5137755ad6ea5abb5476ee97314 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | config/analysis/lower_tertiary/fields/stones.yml#field.opex_per_boe | sha256:7829532d7685b55cc3e5a28725bfe58b451bd5137755ad6ea5abb5476ee97314 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/stones.yml#field.first_oil | sha256:7829532d7685b55cc3e5a28725bfe58b451bd5137755ad6ea5abb5476ee97314 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/stones.yml#field.data_through | sha256:7829532d7685b55cc3e5a28725bfe58b451bd5137755ad6ea5abb5476ee97314 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | worldenergydata | config/analysis/lower_tertiary/fields/stones.yml#field.operator | sha256:7829532d7685b55cc3e5a28725bfe58b451bd5137755ad6ea5abb5476ee97314 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/stones.yml#field.status | sha256:7829532d7685b55cc3e5a28725bfe58b451bd5137755ad6ea5abb5476ee97314 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

### Tiber (`tiber`)

- **Status:** pre_fid
- **Operator:** BP
- **First oil:** 2030-01-01
- **Capex:** $8,000 M total
- **Plateau:** 80 thousand bbl/day
- **NPV @ 10.0%:** $295.9 M
- **Payback:** 7.0 years
- **Breakeven oil price:** $68.1/bbl
- **Cashflow basis:** `documented_decline_curve_v1`
- Economic basis: oil-price deck $70.0/bbl; cost basis: configuration capex and opex, assumed (unsourced configuration value, #651); data_through: 2024-12-31; nominal cost base year: not established. Production history: not established in this assembly; the plateau is a scenario input, and the cashflow is a decline-curve projection, not observed BSEE production (#367). HSE: not established; the upstream placeholder is not an observed zero (#366). Comparable disclosed cost and escalation basis: not established (#343, #344). Field status and first-oil schedule are configuration values, not a current operating-status check. Annual MIRR: not established; the monthly-period rate routine is applied to annual cashflows (#373).

**Sensitivity:**

| oil_price_usd_per_bbl | npv_mm_usd |
|---|---|
| 50.0 | -2,843.1 |
| 60.0 | -1,273.6 |
| 70.0 | 295.9 |
| 80.0 | 1,865.3 |
| 100.0 | 5,004.3 |

Oil-price sensitivity, using the field economic basis.

**Citations:**

| input | publisher | code_id | revision | basis | source_id | title | url | retrieved | sha256 | http_status |
|---|---|---|---|---|---|---|---|---|---|---|
| Capex $8,000.0 M | worldenergydata | config/analysis/lower_tertiary/fields/tiber.yml#field.capex.total_mm_usd | sha256:19cb8fc299c730625a00ace219310d65d33214d63ca31c5f4f210698870787f5 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Plateau 80.0 thousand bbl/day | worldenergydata | config/analysis/lower_tertiary/fields/tiber.yml#field.production_profile.plateau_rate_mbopd | sha256:19cb8fc299c730625a00ace219310d65d33214d63ca31c5f4f210698870787f5 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Opex $15.0/boe | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_OPEX_PER_BOE | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Oil price $70.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.oil_price_usd_per_bbl | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Royalty 12.5% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#DEFAULT_FEDERAL_ROYALTY | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| discount_rate: 10.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.discount_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| reinvestment_rate: 6.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.reinvestment_rate | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| annual_decline: 8.0% | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.annual_decline | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| project_years: 20 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.project_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| plateau_years: 3 | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.plateau_years | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed, based on previous experience | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Sensitivity oil-price deck: $50.0/bbl, $60.0/bbl, $70.0/bbl, $80.0/bbl, $100.0/bbl | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#run_portfolio.sensitivity_prices | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| First-oil schedule | worldenergydata | config/analysis/lower_tertiary/fields/tiber.yml#field.first_oil | sha256:19cb8fc299c730625a00ace219310d65d33214d63ca31c5f4f210698870787f5 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Data cutoff | worldenergydata | config/analysis/lower_tertiary/fields/tiber.yml#field.data_through | sha256:19cb8fc299c730625a00ace219310d65d33214d63ca31c5f4f210698870787f5 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Operator | worldenergydata | config/analysis/lower_tertiary/fields/tiber.yml#field.operator | sha256:19cb8fc299c730625a00ace219310d65d33214d63ca31c5f4f210698870787f5 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Status | worldenergydata | config/analysis/lower_tertiary/fields/tiber.yml#field.status | sha256:19cb8fc299c730625a00ace219310d65d33214d63ca31c5f4f210698870787f5 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Working-interest shares | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| Technology classification | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#_resolved_dev_system | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | assumed (unsourced configuration value, #651) | Not established | Not established | Not established | Not established | Not established | Not applicable |
| NPV, rates, payback, breakeven and sensitivities | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_economics.py#analyze_field | sha256:1611e9fcd6fd3a60580e0bcdf24f2352127299fdafef606dd7d68bd234075d32 | computed from the scenario inputs above | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Portfolio totals and technology comparisons | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#run_portfolio_analytics | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed; plateau-equivalent recovery proxy, not reserves | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Operator concentration | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_operator_concentration | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | computed from eligible configuration working interests; contradicted or unverified interests excluded | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| HSE and disclosed-cost completeness | worldenergydata | packages/worldenergydata-bsee/src/worldenergydata/lower_tertiary/portfolio_analytics.py#analyze_hse_per_field | sha256:504c1161557ae4147dd24d0b235515017a86754e3e9928879f51ff984062f165 | not established; placeholder values are not measurements | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |
| Report revision and issue date | worldenergydata | config/analysis/lower_tertiary/comprehensive_revision.yml | sha256:39d98264b26ddc5de9f21137b74d92bae67ec03155099d940ec617d59457f75a | issued revision record | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable |

Numeric-input and calculation references; source digests are in the companion manifest.

---

## Caveats

- **Cashflow basis:** documented decline-curve (plateau×K years → exponential decline). OGOR-grounded forward path is #367 (ProductionAPI12 → FDAS migration).
- **HSE coverage:** placeholder rows pending #366 (HSE bulk dedup + ingest).
- **Cost benchmarking:** every field flagged `no_data_pending_#343` until the operator registry seeds disclosures.
- **Pre-FID economics:** configured capital estimates are assumptions; treat NPV / breakeven as scenario-grade, not commitment-grade.
- **Citation schema:** flat dict per field. Migration to the workspace-hub `Citation` schema is #361.
