# Stones Field Economics Report

**Development:** Stones (subsea15) &middot; **Lease:** G17001 &middot; **First oil:** 2016-09-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2025-05 (V30 frozen window)

## Summary

On public BSEE production + cost data, **Stones** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-1,479.5 M** (sanctioned V30 model).

- **10 producing wells** (**22 total wellbores**), generating **$5,582 M** gross revenue.
- A **high-capex, deepwater** signature: **$6,232 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-1,907.4 M** in **2017** and has since recovered **$+427.9 M** as production paid back capital.

> Generated from the sanctioned V30 financial model (`build_field_npv_timeline` reuses the same monthly cashflow + trimmed-discount formula as `reproduce_v30_financials`). The NPV timeline below is an additive presentation layer; it does not alter the computed final NPV.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-1,479.5 M** (reconciles to sanctioned baseline $-1,479.5 M).

Cumulative NPV path (by year): `█▇▇▇▇▇▇▇▇▇▆▅▁▁▁▁▁▁▂▂▂▂`  _start $-1M → trough $-1,907M (2017) → latest $-1,479M_

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2004 | -0.8 | -0.8 | Drilling (spud): 001 |
| 2005 | -54.4 | -54.5 |  |
| 2006 | 0.0 | -54.5 | Drilling (spud): 002 |
| 2007 | 0.0 | -54.5 |  |
| 2008 | 0.0 | -54.5 |  |
| 2009 | 0.0 | -54.5 |  |
| 2010 | 0.0 | -54.5 |  |
| 2011 | 0.0 | -54.5 |  |
| 2012 | -98.4 | -101.8 | Drilling (spud): 001 |
| 2013 | -41.6 | -119.5 | Drilling (spud): 004 |
| 2014 | -435.2 | -292.0 | Drilling (spud): 005<br>Drilling (spud): SN105 |
| 2015 | -735.2 | -561.2 | Drilling (spud): SN109<br>Drilling (spud): 009<br>Drilling (spud): SN208<br>Drilling (spud): 008<br>Completion: SN109 (608124009900)<br>Completion: SN105 (608124009500) |
| 2016 | -4,008.5 | -1,874.9 | Drilling (spud): 011<br>Sidetrack: 011 (608124011000)<br>Drilling (spud): SN110<br>Well online (first production): API 608124009500<br>Well online (first production): API 608124009900<br>Completion: SN110 (608124011001)<br>Well online (first production): API 608124011001<br>Drilling (spud): SN206 |
| 2017 | -101.2 | -1,907.4 | Completion: SN208 (608124010400)<br>Drilling (spud): SN207<br>Well online (first production): API 608124010400<br>Completion: SN207 (608124011700)<br>Well online (first production): API 608124011700<br>Completion: SN206 (608124011200) |
| 2018 | 190.1 | -1,855.9 | Drilling (spud): SN213<br>Completion: SN213 (608124012300)<br>Well online (first production): API 608124012300 |
| 2019 | 254.3 | -1,791.8 | Drilling (spud): SN115 |
| 2020 | 10.2 | -1,790.2 | Completion: SN115 (608124012900)<br>Well online (first production): API 608124012900<br>Drilling (spud): SN216 |
| 2021 | 374.8 | -1,713.3 | Completion: SN216 (608124013400)<br>Well online (first production): API 608124013400<br>Drilling (spud): SN114 |
| 2022 | 627.7 | -1,595.3 | Sidetrack: SN114 (608124013700)<br>Drilling (spud): SN114<br>Completion: SN114 (608124013701)<br>Well online (first production): API 608124013701<br>Drilling (spud): SN219 |
| 2023 | 359.8 | -1,534.0 | Sidetrack: SN219 (608124014300)<br>Drilling (spud): SN219<br>Completion: SN219 (608124014301)<br>Well online (first production): API 608124014301 |
| 2024 | 296.5 | -1,487.7 | Workover: SN213 (608124012300) |
| 2025 | 56.4 | -1,479.5 |  |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2004-12-31 | Drilling (spud) | 001 | -0.8 |
| 2006-08-02 | Drilling (spud) | 002 | -54.5 |
| 2012-06-20 | Drilling (spud) | 001 | -58.8 |
| 2013-11-10 | Drilling (spud) | 004 | -109.0 |
| 2014-02-15 | Drilling (spud) | 005 | -130.6 |
| 2014-04-01 | Drilling (spud) | 005 | -148.7 |
| 2014-07-24 | Drilling (spud) | SN105 | -167.9 |
| 2015-03-18 | Drilling (spud) | SN109 | -353.1 |
| 2015-08-01 | Drilling (spud) | 009 | -472.2 |
| 2015-08-07 | Drilling (spud) | SN208 | -472.2 |
| 2015-08-12 | Drilling (spud) | 008 | -472.2 |
| 2015-08-23 | Completion | SN109 (608124009900) | -472.2 |
| 2015-10-18 | Completion | SN105 (608124009500) | -525.4 |
| 2016-05-12 | Drilling (spud) | 011 | -660.2 |
| 2016-08-14 | Sidetrack | 011 (608124011000) | -793.0 |
| 2016-08-16 | Drilling (spud) | SN110 | -793.0 |
| 2016-09-01 | Well online (first production) | API 608124009500 | -1,840.3 |
| 2016-09-01 | Well online (first production) | API 608124009900 | -1,840.3 |
| 2016-09-11 | Completion | SN110 (608124011001) | -1,840.3 |
| 2016-12-01 | Well online (first production) | API 608124011001 | -1,874.9 |
| 2016-12-08 | Drilling (spud) | SN206 | -1,874.9 |
| 2017-02-19 | Completion | SN208 (608124010400) | -1,900.7 |
| 2017-04-02 | Drilling (spud) | SN207 | -1,914.0 |
| 2017-05-01 | Well online (first production) | API 608124010400 | -1,928.2 |
| 2017-06-11 | Completion | SN207 (608124011700) | -1,923.6 |
| 2017-08-01 | Well online (first production) | API 608124011700 | -1,919.2 |
| 2017-08-27 | Completion | SN206 (608124011200) | -1,919.2 |
| 2018-04-06 | Drilling (spud) | SN213 | -1,899.6 |
| 2018-06-24 | Completion | SN213 (608124012300) | -1,897.1 |
| 2018-09-01 | Well online (first production) | API 608124012300 | -1,885.7 |
| 2019-10-22 | Drilling (spud) | SN115 | -1,790.8 |
| 2020-05-03 | Completion | SN115 (608124012900) | -1,806.2 |
| 2020-06-01 | Well online (first production) | API 608124012900 | -1,810.8 |
| 2020-12-09 | Drilling (spud) | SN216 | -1,790.2 |
| 2021-03-07 | Completion | SN216 (608124013400) | -1,780.8 |
| 2021-05-01 | Well online (first production) | API 608124013400 | -1,773.2 |
| 2021-08-17 | Drilling (spud) | SN114 | -1,740.5 |
| 2022-01-30 | Sidetrack | SN114 (608124013700) | -1,704.4 |
| 2022-02-04 | Drilling (spud) | SN114 | -1,694.4 |
| 2022-03-13 | Completion | SN114 (608124013701) | -1,681.7 |
| 2022-05-01 | Well online (first production) | API 608124013701 | -1,670.0 |
| 2022-12-19 | Drilling (spud) | SN219 | -1,595.3 |
| 2023-02-12 | Sidetrack | SN219 (608124014300) | -1,587.1 |
| 2023-02-14 | Drilling (spud) | SN219 | -1,587.1 |
| 2023-03-12 | Completion | SN219 (608124014301) | -1,582.2 |
| 2023-04-01 | Well online (first production) | API 608124014301 | -1,579.2 |
| 2024-01-28 | Workover | SN213 (608124012300) | -1,529.4 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-1,479.5 M**; sum of per-well net NPV = **$-1,479.5 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124009500 | SN105 | 17.87 | 100.2 | -425.8 | -325.7 | 22.0% |
| 2 | 608124009900 | SN109 | 15.98 | 121.1 | -380.9 | -259.8 | 17.6% |
| 3 | 608124012300 | SN213 | 16.44 | 139.4 | -391.8 | -252.4 | 17.1% |
| 4 | 608124012900 | SN115 | 11.93 | 74.9 | -284.4 | -209.5 | 14.2% |
| 5 | 608124013400 | SN216 | 11.97 | 109.5 | -285.4 | -175.9 | 11.9% |
| 6 | 608124010400 | SN208 | 2.87 | -18.8 | -68.4 | -87.2 | 5.9% |
| 7 | 608124011700 | SN207 | 2.02 | -5.0 | -48.2 | -53.2 | 3.6% |
| 8 | 608124013701 | SN114 | 2.52 | 15.6 | -60.0 | -44.5 | 3.0% |
| 9 | 608124011001 | SN110 | 0.25 | -31.6 | -5.9 | -37.5 | 2.5% |
| 10 | 608124014301 | SN219 | 1.81 | 9.4 | -43.2 | -33.8 | 2.3% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
SN105      -325.7 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN109      -259.8 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN213      -252.4 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN115      -209.5 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN216      -175.9 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓
SN208       -87.2 M  ▓▓▓▓▓▓
SN207       -53.2 M  ▓▓▓▓
SN114       -44.5 M  ▓▓▓
SN110       -37.5 M  ▓▓▓
SN219       -33.8 M  ▓▓
```

**[Interactive NPV waterfalls →](./stones_npv_stackup.html)** — two views: an **over-time NPV bridge** (each year's change in cumulative NPV, with the biggest swings annotated by the events that drove them) and this **per-well stackup** (each well's net NPV stepping to the field total). Hover any bar for detail. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev Stones`.

_Block scope: Single OGOR block (WR 508) for this development; block-level NPV decomposition is not applicable (identical to the field total)._

_The stackup covers the 10 producing wells. The field's 22 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Well Geometry (3D)

Interactive 3D well-path views — minimum-curvature trajectories from BSEE directional surveys, rendered with Plotly and Three.js — are in development for this field. When verified they will live at:

- `reports/bsee/stones_well_path_plotly.html`
- `reports/bsee/stones_well_path_threejs.html`

_They are intentionally **not linked yet**: the geometry render must first be confirmed to cover the same lease-resolved producers shown in the NPV stackup above (same APIs, same field), so the economics and the well paths never describe different wells._

---

## Financial Summary (V30 sanctioned model)

| Metric | Value |
|--------|------:|
| Revenue | $5,582.4 M |
| Royalty | $1,046.7 M |
| Variable opex | $334.6 M |
| Fixed opex | $1,275.0 M |
| D&C cost | $2,081.6 M |
| Facilities cost | $4,150.0 M |
| Net cashflow (undiscounted) | $-3,305.5 M |
| **NPV @ 10%** | **$-1,479.5 M** |
| MIRR (annual) | 2.70% |
| Producers | 10 |
| Injectors | 2 |
| Wellbores | 22 |

_Return metric: **MIRR** is the sanctioned return measure for these developments, not IRR. Deepwater Lower-Tertiary cashflows are heavily front-loaded (large D&C + facilities outflows, then a long production tail), so the net-cashflow sign changes more than once and the IRR polynomial can have multiple — or no — real roots; MIRR (single reinvestment/finance rate at the 10% discount rate) is well-defined and unambiguous. NPV @ 10% remains the primary value metric._

_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. NPV reproduced within golden-baseline tolerance by `worldenergydata.lower_tertiary.v30_financial_reproducer`._

---

## Price Sensitivity

NPV is linear in the oil price deck: each **+$1/bbl** on the realized oil price moves field NPV by **$+14.3 M**. Life-to-date NPV reaches **zero at a flat-equivalent realized WTI of $170/bbl**, versus the actual volume-weighted realized **$67/bbl** over the window.

| Flat-equivalent realized WTI ($/bbl) | NPV @ 10% ($MM) |
|-------------------------------------:|------------------:|
| 47 | -1,765.7 |
| 57 | -1,622.6 |
| 67  ← actual | -1,479.5 |
| 77 | -1,336.3 |
| 87 | -1,193.2 |

_Exact, not sampled: NPV is affine in a uniform price multiplier (revenue and royalty scale with price; variable/fixed opex, D&C, facilities and discounting do not), so one base run plus one scaled run define the entire line. 'Flat-equivalent realized WTI' is the volume-weighted average price; the underlying deck is the historical monthly WTI path._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Stones is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev Stones
  # frozen V30 reference report: add --frozen
  ```
