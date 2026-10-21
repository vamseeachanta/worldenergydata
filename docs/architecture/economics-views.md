# Economics calculation engine and comparison views

## Summary

FDAS is the canonical NPV, MIRR and IRR calculator for the economics schedules
and unified-production benchmark. The benchmark and country reference chains
remain deliberately distinct views. Their numbers answer different questions;
their calculation bases accompany the outputs. This decision implements the
explicit-label alternative in issue #832.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-21 | Consolidate valuation on FDAS and declare both views to prevent comparisons across incompatible bases. |

## Decision record

| Difference | Reference-chain view | Benchmark view | Resolution |
| --- | --- | --- | --- |
| Purpose | Exercise production, concept and cash-flow wiring | Compare supplied historical oil revenue under illustrative fiscal assumptions | Preserve both purposes; do not describe either as full-cycle investment NPV. |
| Data | Adapter supplied by the caller | RegionRouter adapters, individually badged real or seed | Report source tags and retain fail-closed benchmark provenance. Real data in one view does not qualify another view. |
| Revenue | Flat caller oil-price input; optional gas deck in the Spain chain | Flat caller oil-price input; gas not priced | Declare the price marker and units rather than imply a market time series. |
| Royalty | Default FDAS assumptions except the UK royalty deck | Simplified cross-basin royalty assumptions | Declare the actual basis. Country fiscal validation is NOT_EVALUATED; no coefficients are ratified by this change. |
| Income tax | Excluded | Simplified tax on revenue after royalties | Label pre-income-tax versus simplified post-tax explicitly. |
| Operating costs | Variable FDAS assumptions; fixed costs excluded by the runners | Excluded | Declare cost scope in each basis. |
| Capital costs | Model host cost; no drilling or facilities schedule supplied | Excluded | Declare scope; reference-chain host cost is not a complete development estimate. |
| Discounting | Undiscounted sum | Fixed effective annual rate converted to monthly | Use FDAS for valuation; remove the benchmark's separate nominal-rate calculation. |
| Reference date | Not applicable to the undiscounted sum | First supplied calendar month at t=0 for each field | Preserve calendar gaps and aggregate duplicate field-month observations. Values across fields need not share a valuation date. |
| Empty production | Existing placeholder metrics; Australia remains screening-only | No fabricated economics row | Basis status NOT_EVALUATED on empty chains; retain the benchmark skipped-region notice. |

Every chain adds `economics_basis` without changing its existing country-specific
keys or metrics. The benchmark adds a basis to every row and a view identifier
to its metadata. `fiscal_sensitivity` retains `operator_npv_usd` for existing
consumers; its meaning remains the historical cash-flow proxy, published as
`disc_posttax_cf_usd`. No public investment-NPV headline is enabled.

Choosing distinct views does not require normalizing all country return dicts
or substituting real-chain outputs into the benchmark. Those would change the
benchmark's purpose and require qualified full-cycle inputs.

## Canonical calculator and migration

`worldenergydata.fdas.core.financial` supplies the valuation functions.
`economics/dcf.py` and its result DTOs are removed, without a compatibility
wrapper. Import `CashFlowSchedule` and `build_cash_flow_schedule` from
`worldenergydata.economics.cash_flow` (also exported from `economics`). Pass
`schedule.net_cashflows()` to FDAS with `period="annual"`. NPV now returns a
scalar; the schedule supplies net cash flows directly. Callers needing discounted
components must declare their timing rather than rely on the removed NPV DTO.

For MIRR, use `excel_like_mirr(..., period="annual")` for annual schedules.
The default remains monthly, preserving the existing FDAS/BSEE path. MIRR
trims boundary zeros using the existing FDAS threshold and returns NaN when
both cash-flow signs are not present. This deliberately replaces the former
schedule calculator's untrimmed horizon and exception for all-positive flows.
`EconomicsQuery.mirr` accepts the same period choice. `calculate_all_metrics`
now passes the selected period to MIRR as well as NPV and IRR. Its legacy
`mirr_monthly` dictionary key holds the selected period return; use
`mirr_annual` for the annualized value.

FDAS input validation remains authoritative, including its existing discount-rate
bounds. This migration does not broaden those bounds or qualify its historical
spreadsheet-compatibility claims. The changed benchmark numbers follow effective
annual compounding and calendar timing, rather than the former rate divided by
months and compressed observation order.

## Equations and sources

- NPV = sum(CF[t] / (1+r_period)**t), starting at t=0. IRR solves that sum = 0.
  Source: [numpy-financial v1.0.0, NPV and IRR docstrings](https://github.com/numpy/numpy-financial/blob/v1.0.0/numpy_financial/_financial.py)
  (2019), citing Gitman, *Principles of Managerial Finance, Brief*, third
  edition (2003), pages 346 and 348.
- MIRR = (FV_positive / abs(PV_negative))**(1/n) - 1, with caller-supplied
  finance and reinvestment rates. Source: the same version's MIRR implementation
  (2019). Boundary trimming follows the existing
  `packages/worldenergydata-fdas/src/worldenergydata/fdas/core/financial.py`
  implementation (2025); it is a preserved FDAS convention, not a claim that
  arbitrary spreadsheet applications trim zeros.
- r_month = (1+r_annual)**(1/12)-1; annual return = (1+r_month)**12-1.
  Source: the existing FDAS financial module and
  [FDAS user guide](../modules/fdas/USER-GUIDE.md), financial methodology (2025).
  Twelve is the number of monthly periods in a year, not a fitted coefficient.
- Revenue = volume times price; pre-tax CF = revenue less royalty and supplied
  costs; simplified benchmark post-tax CF = revenue times (1-royalty) times
  (1-tax). Sources: the shipped FDAS `analysis/cashflow.py` and unified-production
  `cross_basin.py` accounting definitions (2026). Fiscal coefficients are
  inherited assumptions, not sourced legal determinations. Their qualification
  is NOT_EVALUATED; no new fiscal coefficient is introduced.

The fixed benchmark discount assumption is inherited from `cross_basin.py`,
not recommended as an investment hurdle rate. Prices, rates, costs and emissions
in the example below are synthetic user inputs chosen for hand arithmetic.
No empirical coefficient or acceptance threshold is inferred from memory.

## Worked example

Run `python examples/economics_views.py`. This offline example prints inputs,
method and answer and checks against the independent arithmetic shown here.

Annual schedule: initial capital outflow 100.0 USD; next-period revenue
141.0 USD, operating cost 10.0 USD and carbon cost 10.0 USD. Net cash flows are
[-100.0, 121.0] USD. At the supplied annual discount rate of 10.0 %:

- NPV = -100.0 + 121.0 / 1.1 = **10.0 USD**.
- One-period MIRR = 121.0 / 100.0 - 1 = **21.0 %**.
- IRR solves -100.0 + 121.0 / (1+r) = 0, hence **21.0 %**.

Timing comparison: synthetic receipts of 110.0 USD in January of consecutive
years have an undiscounted sum of **220.0 USD**. At the same effective annual
rate, FDAS monthly discounting gives 110.0 + 110.0 / 1.1 = **210.0 USD**.
The absent intervening observations do not move the second receipt earlier.
This arithmetic isolates timing; it does not represent a qualified fiscal case.

Tests in `tests/unit/economics/test_dcf.py` cover the former schedule and array
consumers, independent two-rate MIRR arithmetic, annual/monthly conversion,
boundary-zero trimming and undefined returns. The calendar case is exercised
through `fiscal_sensitivity` with synthetic royalty and tax inputs in
`tests/unit/production/unified/test_cross_basin.py`.

## Known limits and later work

Full-cycle forecasts, common valuation dates, qualified fiscal coefficients,
price histories and complete cost schedules remain outside these views.
No missing fiscal validation is presented as a pass. Existing country-specific
return structures and placeholder metrics remain available for compatibility.
The existing missing-golden-baseline test remains skipped by the repository;
passing unit arithmetic does not replace that validation evidence.
