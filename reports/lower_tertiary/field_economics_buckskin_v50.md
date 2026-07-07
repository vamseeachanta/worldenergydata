# Buckskin Field Economics Report

**Development:** Buckskin (tieback20) &middot; **Lease:** 6 leases (G25806, G25813, G25814, G25815, G25823, G32650) &middot; **First oil:** 2018-08-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04 (latest V50-KC recompute)

## Summary

On public BSEE production + cost data, **Buckskin** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-989.7 M** (V50-KC recompute; no frozen V30 Buckskin row).

- **72.9 MMbbl** oil produced from **4 producing wells** (**25 total wellbores**), generating **$5,116 M** gross revenue.
- A **high-capex, deepwater** signature: **$4,062 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-1,661.8 M** in **2018** and has since recovered **$+672.1 M** as production paid back capital.

> **V50-KC run.** The NPV timeline is built from the V30 cashflow model using the opt-in Keathley Canyon V50 lease and D&C inputs (`leases_v21_kc.csv`, `drilling_and_completion_days_v21_kc.csv`) through the latest available BSEE OGOR-A month. The frozen V30 baseline has no Buckskin row and remains unchanged.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-989.7 M** (V50-KC recompute; no frozen V30 Buckskin reference).

Cumulative NPV path (by year): `█▇▇▇▇▆▆▆▆▆▁▁▁▂▂▃▃▄▄`  _start $-129M → trough $-1,662M (2018) → latest $-990M_

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2008 | -130.9 | -129.3 | Sidetrack: 001 (608084001600) |
| 2009 | -20.9 | -149.6 | Temporary abandonment: 001 (608084001601) |
| 2010 | 0.0 | -149.6 |  |
| 2011 | -132.0 | -250.4 | Temporary abandonment: 001 (608084002100) |
| 2012 | 0.0 | -250.4 |  |
| 2013 | -223.3 | -391.4 | Sidetrack: 001 (608084003100)<br>Sidetrack: 001 (608084003101)<br>Sidetrack: 001 (608084003102) |
| 2014 | -258.5 | -539.1 | Sidetrack: 001 (608084003103)<br>Sidetrack: 001 (608084003104)<br>Sidetrack: 001 (608084003105)<br>Plug & abandon: 001 (608084003106)<br>Sidetrack: 002 (608084004700)<br>Plug & abandon: 002 (608084004701) |
| 2015 | 0.0 | -539.1 |  |
| 2016 | 0.0 | -539.1 |  |
| 2017 | 0.0 | -539.1 | Plug & abandon: 001 (608084002100) |
| 2018 | -2,876.2 | -1,661.8 | Sidetrack: 002 (608084006000)<br>Sidetrack: 003 (608084006100)<br>Temporary abandonment: SS003 (608084006101)<br>Completion: SS002 (608084006001)<br>Well online (first production): API 608084006001<br>Completion: SS003 (608084006101)<br>Well online (first production): API 608084006101 |
| 2019 | 157.4 | -1,607.0 |  |
| 2020 | 140.0 | -1,561.5 |  |
| 2021 | 423.2 | -1,435.7 | Sidetrack: 001 (608084006700)<br>Sidetrack: 001 (608084006701) |
| 2022 | 548.7 | -1,287.0 | Temporary abandonment: SS001 (608084006702)<br>Completion: SS001 (608084006702)<br>Well online (first production): API 608084006702<br>Plug & abandon: 002 (608084007000) |
| 2023 | 492.3 | -1,166.5 | Sidetrack: 004 (608084007300)<br>Temporary abandonment: SS004 (608084007301) |
| 2024 | 335.3 | -1,092.0 | Completion: SS004 (608084007301)<br>Well online (first production): API 608084007301 |
| 2025 | 431.5 | -1,004.9 |  |
| 2026 | 79.4 | -989.7 |  |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2008-11-23 | Sidetrack | 001 (608084001600) | -96.0 |
| 2009-01-18 | Temporary abandonment | 001 (608084001601) | -149.6 |
| 2011-09-18 | Temporary abandonment | 001 (608084002100) | -250.4 |
| 2013-09-08 | Sidetrack | 001 (608084003100) | -371.9 |
| 2013-11-03 | Sidetrack | 001 (608084003101) | -390.8 |
| 2013-12-29 | Sidetrack | 001 (608084003102) | -391.4 |
| 2014-01-26 | Sidetrack | 001 (608084003103) | -396.1 |
| 2014-03-16 | Sidetrack | 001 (608084003104) | -407.8 |
| 2014-06-29 | Sidetrack | 001 (608084003105) | -436.2 |
| 2014-09-28 | Plug & abandon | 001 (608084003106) | -497.5 |
| 2014-10-26 | Sidetrack | 002 (608084004700) | -513.5 |
| 2014-12-14 | Plug & abandon | 002 (608084004701) | -539.1 |
| 2017-07-02 | Plug & abandon | 001 (608084002100) | -539.1 |
| 2018-03-18 | Sidetrack | 002 (608084006000) | -599.5 |
| 2018-05-27 | Sidetrack | 003 (608084006100) | -659.7 |
| 2018-06-17 | Temporary abandonment | SS003 (608084006101) | -687.5 |
| 2018-07-01 | Completion | SS002 (608084006001) | -754.3 |
| 2018-08-01 | Well online (first production) | API 608084006001 | -1,633.1 |
| 2018-09-02 | Completion | SS003 (608084006101) | -1,645.8 |
| 2018-10-01 | Well online (first production) | API 608084006101 | -1,661.8 |
| 2021-09-26 | Sidetrack | 001 (608084006700) | -1,459.1 |
| 2021-12-19 | Sidetrack | 001 (608084006701) | -1,435.7 |
| 2022-01-23 | Temporary abandonment | SS001 (608084006702) | -1,420.5 |
| 2022-06-03 | Completion | SS001 (608084006702) | -1,333.2 |
| 2022-08-01 | Well online (first production) | API 608084006702 | -1,321.3 |
| 2022-09-01 | Well online (first production) | API 608084006702 | -1,306.8 |
| 2022-11-20 | Plug & abandon | 002 (608084007000) | -1,299.5 |
| 2023-09-03 | Sidetrack | 004 (608084007300) | -1,200.5 |
| 2023-10-08 | Temporary abandonment | SS004 (608084007301) | -1,188.4 |
| 2024-02-02 | Completion | SS004 (608084007301) | -1,150.5 |
| 2024-08-01 | Well online (first production) | API 608084007301 | -1,124.6 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-989.7 M**; sum of per-well net NPV = **$-989.7 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608084006001 | SS002 | 34.85 | 394.1 | -823.8 | -429.6 | 43.4% |
| 2 | 608084006101 | SS003 | 26.48 | 280.7 | -626.0 | -345.3 | 34.9% |
| 3 | 608084006702 | SS001 | 8.78 | 70.9 | -207.6 | -136.7 | 13.8% |
| 4 | 608084007301 | SS004 | 2.77 | -12.7 | -65.4 | -78.1 | 7.9% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
SS002      -429.6 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SS003      -345.3 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SS001      -136.7 M  ▓▓▓▓▓▓▓▓
SS004       -78.1 M  ▓▓▓▓
```

**[Interactive NPV waterfalls →](./buckskin_npv_stackup.html)** — two views: an **over-time NPV bridge** (each year's change in cumulative NPV, with the biggest swings annotated by the events that drove them) and this **per-well stackup** (each well's net NPV stepping to the field total). Hover any bar for detail. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev Buckskin`.

**By block (OGOR `AREA_CODE_BLOCK_NUM`):**

| Block | Oil (MMbbl) | % of field oil |
|-------|------------:|---------------:|
| KC  829 | 64.54 | 88.6% |
| KC  830 | 8.34 | 11.4% |

_Block scope: 2 OGOR blocks present; per-block oil shares shown. Per-block NPV would require a block-level cost split (gap: shared facilities/D&C are field-level in V30, not block-tagged)._

_The stackup covers the 4 producing wells. The field's 25 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Well Geometry (3D)

Interactive 3D well-path views — minimum-curvature trajectories from BSEE directional surveys, rendered with Plotly and Three.js — are in development for this field. When verified they will live at:

- `reports/bsee/buckskin_well_path_plotly.html`
- `reports/bsee/buckskin_well_path_threejs.html`

_They are intentionally **not linked yet**: the geometry render must first be confirmed to cover the same lease-resolved producers shown in the NPV stackup above (same APIs, same field), so the economics and the well paths never describe different wells._

---

## Financial Summary

**V50-KC latest window (2000-09 -> 2026-04).** Buckskin uses the opt-in KC lease/D&C input set; frozen V30 has no Buckskin row.

| Metric | Latest V50-KC | Frozen V30 |
|--------|------:|------:|
| **NPV @ 10%** | **$-989.7 M** | n/a |
| Revenue | $5,115.6 M | n/a |
| Oil produced (MMbbl) | 72.9 | n/a |

_Latest NPV, revenue and oil are recomputed from the V50-KC input set; window through 2026-04._

### V50-KC component breakdown

| Metric | Value |
|--------|------:|
| Revenue | $5,115.6 M |
| Royalty | $959.2 M |
| Variable opex | $437.3 M |
| Fixed opex | $691.7 M |
| D&C cost | $2,261.6 M |
| Facilities cost | $1,800.0 M |
| Net cashflow (undiscounted) | $-1,034.1 M |
| **NPV @ 10%** | **$-989.7 M** |
| MIRR (annual) | 4.47% |
| Producers | 4 |
| Injectors | 0 |
| Wellbores | 25 |

_Return metric: **MIRR** is the sanctioned return measure for these developments, not IRR. Deepwater Lower-Tertiary cashflows are heavily front-loaded (large D&C + facilities outflows, then a long production tail), so the net-cashflow sign changes more than once and the IRR polynomial can have multiple — or no — real roots; MIRR (single reinvestment/finance rate at the 10% discount rate) is well-defined and unambiguous. NPV @ 10% remains the primary value metric._

_Source-of-record for this recompute: `leases_v21_kc.csv` + `drilling_and_completion_days_v21_kc.csv` + BSEE OGOR-A `.bin`; the frozen V30 baseline has no Buckskin row._

---

## Price Sensitivity

NPV is linear in the oil price deck: each **+$1/bbl** on the realized oil price moves field NPV by **$+15.3 M**. Life-to-date NPV reaches **zero at a flat-equivalent realized WTI of $135/bbl**, versus the actual volume-weighted realized **$70/bbl** over the window.

| Flat-equivalent realized WTI ($/bbl) | NPV @ 10% ($MM) |
|-------------------------------------:|------------------:|
| 50 | -1,295.8 |
| 60 | -1,142.8 |
| 70  ← actual | -989.7 |
| 80 | -836.6 |
| 90 | -683.6 |

_Exact, not sampled: NPV is affine in a uniform price multiplier (revenue and royalty scale with price; variable/fixed opex, D&C, facilities and discounting do not), so one base run plus one scaled run define the entire line. 'Flat-equivalent realized WTI' is the volume-weighted average price; the underlying deck is the historical monthly WTI path._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Buckskin is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev Buckskin
  # frozen V30 reference report: add --frozen
  ```
