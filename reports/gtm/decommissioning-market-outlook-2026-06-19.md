# GoM Decommissioning Market Outlook — 5-Year P&A Forecast

> **Issue**: [#424](https://github.com/vamseeachanta/worldenergydata/issues/424) (child of [#423](https://github.com/vamseeachanta/worldenergydata/issues/423))  
> **Branch**: `feat/autorun-2026-06-19`  
> **Data as of**: 2026-06-19 (BSEE borehole-status census; status dates through 2025)  
> **Framing**: market-intelligence (commercial), operator-aggregate only.

---

## What this document is

A forward 5-year (2026-2030) Gulf of Mexico **decommissioning / plug-&-abandonment (P&A)** volume, timing, and market-size forecast. It mirrors the rigor of the field-analysis and HSE reports in `reports/`: it is grounded in the **real local BSEE well-status census**, and it makes a **hard separation** between measured data and explicitly-cited public-knowledge assumptions. Every projected number traces to either the data pass or a labelled assumption — nothing is fabricated.

## Caveat block

> **Data source**: BSEE wells census — `data/modules/bsee/current/wells/well_data.csv` (57,281 boreholes nationally; 54,492 fall inside the GoM bounding box and are this report's universe). The **populated, reliable fields** in this extract are `BOREHOLE_STAT_CD` (100%), `BOREHOLE_STAT_DT` (99%), and bottom-hole coordinates (99%). **Known thinness**: `WATER_DEPTH` and `WELL_SPUD_DATE` are populated for only ~100 rows in this extract, so per-well **water-depth strata and spud-age cohorts cannot be grounded** — the deepwater mix and the attrition pace are therefore carried as **explicit assumptions**, not data, and are stress-tested in the sensitivity. This is engineering analysis of public regulatory data, **not** a regulatory finding. Operator names are not surfaced (Operator Aggregation Contract #420).

## Borehole-status inventory (DATA — measured)

BSEE `BOREHOLE_STAT_CD`, GoM-filtered:

| Status | Meaning | GoM wells |
|---|---|---:|
| `PA` | Permanently Abandoned (plugged & abandoned — already decommissioned) | 29,800 |
| `ST` | Sidetrack (borehole of a sidetracked well — not a standalone P&A unit) | 16,888 |
| `COM` | Completed (producing or capable — reaches end-of-life over horizon) | 4,215 |
| `TA` | Temporarily Abandoned (idle/suspended — prime P&A candidate) | 3,190 |
| `CNL` | Cancelled | 397 |
| `DRL` | Drilling | 1 |
| `APD` | Approved Permit to Drill | 1 |
| **Total** | | **54,492** |

**Already decommissioned (PA):** 29,800 GoM boreholes are permanently abandoned — the historical decommissioning record this forecast extends.

## Eligible-for-decommissioning inventory (DATA)

Wells **not yet permanently abandoned** but in a status that draws down into P&A over the horizon — the addressable pipeline:

| Eligible bucket | Count | Basis |
|---|---:|---|
| `TA` temporarily abandoned (idle) | 3,190 | idle iron — direct P&A candidates |
| `COM` completed (producing/capable) | 4,215 | reach end-of-life over horizon |
| `DSI` drilled & suspended | 0 | inactive |
| `AST` abandoned sidetrack | 0 | residual |
| **Total eligible inventory** | **7,405** | model drawdown base |

### Idle-iron aging (DATA) — regulatory P&A pressure

TA wells by how long they have sat idle (from `BOREHOLE_STAT_DT`):

- **2,217** TA wells have been idle **≥10 years** (status date ≤2015) — the BSEE 'idle iron' cohort under the strongest plug-or-restore regulatory pressure.

- **1,178** TA wells idle **≥15 years**.

## Observed historical P&A rate (DATA — calibration anchor)

GoM permanent abandonments completed per year (from `BOREHOLE_STAT_DT`):

| Year | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GoM P&A | 479 | 683 | 423 | 397 | 304 | 214 | 302 | 397 | 610 | 266 |

- **2015-2024 mean**: 407.5 P&A / yr.  **2020-2024 mean**: 357.8 / yr.
- Implied historical attrition pace vs. the eligible inventory: **5.5% / yr** — the empirical anchor for the assumed pace below.

## Forecast model

**Model**: eligible-inventory drawdown.  For each forecast year, `plugged = remaining_eligible × attrition_pace`, then `remaining -= plugged`. Market size = `Σ plugged × blended_unit_cost`, where the blended unit cost mixes shelf and deepwater per-well cost at the assumed deepwater share. The data fixes the starting inventory (7,405) and the empirical pace anchor (5.5%); the pace, deepwater mix, and unit costs are the assumptions stress-tested below.

### Assumptions (NOT data — explicit & cited)

| Parameter | Low | Base | High | Source |
|---|---:|---:|---:|---|
| Shelf/shallow P&A unit cost ($MM/well) | 0.8 | 1.5 | 3.0 | BOEM/BSEE decom cost reports; GAO-16-40 |
| Deepwater P&A unit cost ($MM/well) | 5.0 | 12.0 | 25.0 | Wood Mackenzie / Westwood GoM decom (public) |
| Deepwater share of eligible | 3% | 6% | 10% | BOEM GoM well census (shelf-dominated) |
| Annual attrition pace | 4.0% | 5.5% | 7.0% | calibrated to observed PA rate (data), flexed ± |

## 5-year forecast & sensitivity (2026-2030)

| Scenario | Pace | DW share | Blended $/well | 2026 | 2027 | 2028 | 2029 | 2030 | 5-yr wells | 5-yr market |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| low | 4.0% | 3% | $0.93MM | 296 | 284 | 273 | 262 | 252 | **1367** | **$1.27B** |
| base | 5.5% | 6% | $2.13MM | 407 | 385 | 364 | 344 | 325 | **1825** | **$3.89B** |
| high | 7.0% | 10% | $5.20MM | 518 | 482 | 448 | 417 | 388 | **2253** | **$11.72B** |

**Base case**: **1,825 GoM wells** plugged over 2026-2030 (~407/yr declining as the inventory draws down), a **$3.89B** addressable P&A market at the base blended unit cost of $2.13MM/well.

**Sensitivity span**: the market ranges from **$1.27B** (low pace × low cost) to **$11.72B** (high pace × high cost) — a 9.2× spread, driven jointly by pace and unit cost.

## Commercial read-through

- **Pipeline is large and aging**: 7,405 eligible wells, of which 3,190 are already idle and 2,217 have been idle ≥10 years — a standing backlog independent of new end-of-life additions.

- **Steady multi-year demand**: at the base pace the GoM sustains several hundred P&A wells/year, a durable services market for well-plugging, rig/vessel, casing-cut, and conductor-removal contractors.

- **Capacity gap signal**: the observed PA rate (358/yr, 2020-2024) sits below the base-case requirement, implying a backlog-clearing gap that favors decom-capable vendors.

## Reproduce

```
PYTHONPATH=src python3 reports/gtm/decommissioning_market_outlook.py
```
Deterministic: emits the `.json` sidecar (all figures), this `.md`, and the `.html`. Every number above is in the JSON.

*Generated 2026-06-20T04:05:11.302711Z · data as of 2026-06-19 · operator-aggregate only.*
