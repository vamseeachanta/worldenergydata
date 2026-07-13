# Anchor Field Economics Report

**Development:** Anchor (subsea20) &middot; **Lease:** 2 leases (G31751, G31752) &middot; **First oil:** 2024-08-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04

## Summary

On public BSEE production + cost data, **Anchor** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-1,586.9 M**.

- **18.6 MMbbl** oil produced from **2 producing wells** (**15 total wellbores**), generating **$1,279 M** gross revenue.
- A **high-capex, deepwater** signature: **$4,161 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-1,797.0 M** in **2024** and has since recovered **$+210.1 M** as production paid back capital.

> Generated from public BSEE OGOR-A production and drilling/WAR records run through a monthly cashflow + trimmed-discount model (`build_field_npv_timeline`), covering field life through the latest available BSEE OGOR-A month. The NPV timeline below is an additive presentation layer over that model; it does not alter the computed final NPV.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-1,586.9 M**.

Cumulative NPV path (by year): `█▇▇▇▇▇▇▇▆▄▁▁▁`  _start $-145M → trough $-1,797M (2024) → latest $-1,587M_

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2014 | -149.6 | -144.5 | Drilling (spud): 001<br>Sidetrack: 001 (608114062100)<br>Plug & abandon: 001 (608114062101)<br>Drilling (spud): 002<br>Temporary abandonment: 002 (608114063500) |
| 2015 | -37.6 | -177.4 | Sidetrack: 002 (608114063500)<br>Drilling (spud): 002<br>Sidetrack: 002 (608114063501)<br>Plug & abandon: 002 (608114063502) |
| 2016 | -166.4 | -311.3 | Drilling (spud): 001<br>Drilling (spud): 003<br>Sidetrack: 003 (608114067300) |
| 2017 | -18.4 | -325.3 | Plug & abandon: 003 (608114067301) |
| 2018 | 0.0 | -325.3 |  |
| 2019 | -5.6 | -328.6 | Drilling (spud): SB001<br>Plug & abandon: SB001 (608114072800) |
| 2020 | 0.0 | -328.6 |  |
| 2021 | -19.2 | -337.7 | Drilling (spud): AP001 |
| 2022 | -406.9 | -518.8 | Temporary abandonment: AP001 (608114075000)<br>Drilling (spud): AP002 |
| 2023 | -860.4 | -872.9 | Temporary abandonment: AP002 (608114075100)<br>Drilling (spud): BP003 |
| 2024 | -2,459.7 | -1,797.0 | Completion: AP001 (608114075000)<br>Temporary abandonment: BP003 (608114077400)<br>Well online (first production): API 608114075000<br>Completion: AP002 (608114075100)<br>Well online (first production): API 608114075100 |
| 2025 | 435.5 | -1,648.4 |  |
| 2026 | 192.5 | -1,586.9 | Well online (first production): API 608114076101 |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2014-03-16 | Drilling (spud) | 001 | -12.8 |
| 2014-05-25 | Sidetrack | 001 (608114062100) | -52.4 |
| 2014-05-28 | Drilling (spud) | 001 | -52.4 |
| 2014-07-20 | Plug & abandon | 001 (608114062101) | -62.5 |
| 2014-08-12 | Drilling (spud) | 002 | -77.9 |
| 2014-12-14 | Temporary abandonment | 002 (608114063500) | -144.5 |
| 2015-07-05 | Sidetrack | 002 (608114063500) | -157.9 |
| 2015-07-09 | Drilling (spud) | 002 | -157.9 |
| 2015-08-09 | Sidetrack | 002 (608114063501) | -170.5 |
| 2015-08-14 | Drilling (spud) | 002 | -170.5 |
| 2015-09-20 | Plug & abandon | 002 (608114063502) | -177.4 |
| 2016-01-26 | Drilling (spud) | 001 | -181.4 |
| 2016-02-26 | Drilling (spud) | 001 | -190.8 |
| 2016-09-17 | Drilling (spud) | 003 | -270.9 |
| 2016-12-04 | Drilling (spud) | 003 | -311.3 |
| 2016-12-04 | Sidetrack | 003 (608114067300) | -311.3 |
| 2017-02-12 | Plug & abandon | 003 (608114067301) | -325.3 |
| 2019-11-19 | Drilling (spud) | SB001 | -328.6 |
| 2019-11-24 | Plug & abandon | SB001 (608114072800) | -328.6 |
| 2021-12-08 | Drilling (spud) | AP001 | -337.7 |
| 2022-04-10 | Temporary abandonment | AP001 (608114075000) | -364.9 |
| 2022-11-16 | Drilling (spud) | AP002 | -480.9 |
| 2023-03-19 | Temporary abandonment | AP002 (608114075100) | -611.4 |
| 2023-11-26 | Drilling (spud) | BP003 | -818.0 |
| 2024-03-10 | Completion | AP001 (608114075000) | -1,051.9 |
| 2024-06-02 | Temporary abandonment | BP003 (608114077400) | -1,213.7 |
| 2024-08-01 | Well online (first production) | API 608114075000 | -1,776.5 |
| 2024-08-18 | Completion | AP002 (608114075100) | -1,776.5 |
| 2024-11-01 | Well online (first production) | API 608114075100 | -1,803.6 |
| 2026-04-01 | Well online (first production) | API 608114076101 | -1,586.9 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-1,586.9 M**; sum of per-well net NPV = **$-1,586.9 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608114075100 | AP002 | 9.89 | 79.9 | -889.6 | -809.7 | 51.0% |
| 2 | 608114075000 | AP001 | 8.43 | -2.4 | -758.3 | -760.7 | 47.9% |
| 3 | 608114076101 |  | 0.25 | 6.0 | -22.5 | -16.6 | 1.0% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
AP002      -809.7 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
AP001      -760.7 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
608114076101    -16.6 M  ▓
```

**[Interactive NPV waterfalls →](./anchor_npv_stackup.html)** — two views: an **over-time NPV bridge** (each year's change in cumulative NPV, with the biggest swings annotated by the events that drove them) and this **per-well stackup** (each well's net NPV stepping to the field total). Hover any bar for detail. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev Anchor`.

_Block scope: Single OGOR block (GC 807) for this development; block-level NPV decomposition is not applicable (identical to the field total)._

_The stackup covers the 2 producing wells. The field's 15 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Well Geometry (3D)

Interactive 3D well-path views — minimum-curvature trajectories from BSEE directional surveys, rendered with Plotly and Three.js — are in development for this field. When verified they will live at:

- `reports/bsee/anchor_well_path_plotly.html`
- `reports/bsee/anchor_well_path_threejs.html`

_They are intentionally **not linked yet**: the geometry render must first be confirmed to cover the same lease-resolved producers shown in the NPV stackup above (same APIs, same field), so the economics and the well paths never describe different wells._

---

## Financial Summary

Life-to-date field economics on public BSEE data (2000-09 -> 2026-04). D&C and facilities are one-time capital already incurred; revenue, royalty and opex accrue with production.

| Metric | Value |
|--------|------:|
| Revenue | $1,279.2 M |
| Royalty | $239.8 M |
| Variable opex | $111.4 M |
| Fixed opex | $262.5 M |
| D&C cost | $1,761.2 M |
| Facilities cost | $2,400.0 M |
| Net cashflow (undiscounted) | $-3,495.7 M |
| **NPV @ 10%** | **$-1,586.9 M** |
| MIRR (annual) | -7.69% |
| Producers | 2 |
| Injectors | 0 |
| Wellbores | 15 |

_Return metric: **MIRR** is the return measure used for these developments, not IRR. Deepwater Lower-Tertiary cashflows are heavily front-loaded (large D&C + facilities outflows, then a long production tail), so the net-cashflow sign changes more than once and the IRR polynomial can have multiple — or no — real roots; MIRR (single reinvestment/finance rate at the 10% discount rate) is well-defined and unambiguous. NPV @ 10% remains the primary value metric._

_Source-of-record: public BSEE OGOR-A production, drilling and WAR records, run through the field cashflow model._

---

## Price Sensitivity

NPV is linear in the oil price deck: each **+$1/bbl** on the realized oil price moves field NPV by **$+5.1 M**. Life-to-date NPV reaches **zero at a flat-equivalent realized WTI of $380/bbl**, versus the actual volume-weighted realized **$69/bbl** over the window.

| Flat-equivalent realized WTI ($/bbl) | NPV @ 10% ($MM) |
|-------------------------------------:|------------------:|
| 49 | -1,688.8 |
| 59 | -1,637.9 |
| 69  ← actual | -1,586.9 |
| 79 | -1,535.9 |
| 89 | -1,485.0 |

_Exact, not sampled: NPV is affine in a uniform price multiplier (revenue and royalty scale with price; variable/fixed opex, D&C, facilities and discounting do not), so one base run plus one scaled run define the entire line. 'Flat-equivalent realized WTI' is the volume-weighted average price; the underlying deck is the historical monthly WTI path._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Anchor is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through a transparent cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → NPV) is reproducible end-to-end.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev Anchor
  ```
