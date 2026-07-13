# Big Foot Field Economics Report

**Development:** Big Foot (dry) &middot; **Lease:** G16942 &middot; **First oil:** 2018-11-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04

## Summary

On public BSEE production + cost data, **Big Foot** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-989.0 M**.

- **78.7 MMbbl** oil produced from **7 producing wells** (**38 total wellbores**), generating **$5,571 M** gross revenue.
- A **high-capex, deepwater** signature: **$4,517 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-1,484.3 M** in **2018** and has since recovered **$+495.3 M** as production paid back capital.

> Generated from public BSEE OGOR-A production and drilling/WAR records run through a monthly cashflow + trimmed-discount model (`build_field_npv_timeline`), covering field life through the latest available BSEE OGOR-A month. The NPV timeline below is an additive presentation layer over that model; it does not alter the computed final NPV.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-989.0 M**.

Cumulative NPV path (by year): `█▇▇▇▇▇▇▅▅▅▅▅▃▁▁▁▁▂▂▂▃▃`  _start $-92M → trough $-1,484M (2018) → latest $-989M_

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2005 | -93.6 | -91.7 | Drilling (spud): 001<br>Plug & abandon: 001 (608124001900)<br>Drilling (spud): 002<br>Plug & abandon: 002 (608124002000)<br>Temporary abandonment: 002 (608124002000) |
| 2006 | -93.6 | -176.6 | Drilling (spud): 002<br>Sidetrack: 002 (608124002000)<br>Sidetrack: 002 (608124002001)<br>Temporary abandonment: 002 (608124002002)<br>Sidetrack: 002 (608124002002)<br>Plug & abandon: 002 (608124002003)<br>Sidetrack: 002 (608124002003)<br>Temporary abandonment: 002 (608124002004)<br>Drilling (spud): 003 |
| 2007 | -76.0 | -239.1 | Plug & abandon: 003 (608124002300)<br>Sidetrack: 003 (608124002300)<br>Drilling (spud): 003<br>Sidetrack: 003 (608124002301) |
| 2008 | -40.0 | -268.7 | Temporary abandonment: 003 (608124002302)<br>Sidetrack: 002 (608124002004)<br>Drilling (spud): 002<br>Temporary abandonment: 002 (608124002005) |
| 2009 | -0.8 | -269.3 |  |
| 2010 | 0.0 | -269.3 |  |
| 2011 | -17.6 | -278.8 | Drilling (spud): A004 |
| 2012 | -415.2 | -494.6 | Temporary abandonment: A004 (608124006000)<br>Drilling (spud): A001<br>Drilling (spud): A006<br>Drilling (spud): A011<br>Drilling (spud): A007<br>Drilling (spud): A005<br>Temporary abandonment: A001 (608124006200) |
| 2013 | -94.4 | -540.0 | Drilling (spud): A008 |
| 2014 | 0.0 | -540.0 |  |
| 2015 | 0.0 | -540.0 |  |
| 2016 | -166.7 | -596.4 |  |
| 2017 | -1,000.0 | -916.4 |  |
| 2018 | -1,980.8 | -1,484.3 | Completion: A001 (608124006200)<br>Well online (first production): API 608124006200<br>Completion: A004 (608124006000) |
| 2019 | 91.8 | -1,461.1 | Drilling (spud): A004<br>Sidetrack: A004 (608124006000)<br>Completion: A004 (608124006001)<br>Well online (first production): API 608124006001<br>Sidetrack: A006 (608124006600) |
| 2020 | -6.2 | -1,463.1 | Drilling (spud): A006<br>Sidetrack: A006 (608124006601)<br>Sidetrack: A006 (608124006602)<br>Completion: A006 (608124006603)<br>Workover: A004 (608124006001)<br>Well online (first production): API 608124006603 |
| 2021 | 318.3 | -1,394.9 | Plug & abandon: A011 (608124007100)<br>Sidetrack: A011 (608124007100)<br>Drilling (spud): A011<br>Sidetrack: A011 (608124007101)<br>Plug & abandon: 003 (608124002302)<br>Plug & abandon: 002 (608124002005)<br>Completion: A011 (608124007102)<br>Well online (first production): API 608124007102<br>Workover: A001 (608124006200) |
| 2022 | 609.2 | -1,274.1 | Temporary abandonment: A008 (608124006800)<br>Workover: A006 (608124006603)<br>Completion: A008 (608124006800)<br>Well online (first production): API 608124006800<br>Completion: A007 (608124006700) |
| 2023 | 521.8 | -1,179.7 | Completion: A005 (608124006500)<br>Workover: A011 (608124007102)<br>Plug & abandon: A011 (608124007102)<br>Sidetrack: A011 (608124007102)<br>Drilling (spud): A011<br>Completion: A011 (608124007103)<br>Well online (first production): API 608124007103 |
| 2024 | 513.1 | -1,094.9 | Drilling (spud): A002<br>Completion: A002 (608124006302) |
| 2025 | 469.5 | -1,024.6 | Well online (first production): API 608124006302<br>Completion: A003 (608124006404)<br>Well online (first production): API 608124006404<br>Workover: A008 (608124006800) |
| 2026 | 255.2 | -989.0 |  |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2005-07-26 | Drilling (spud) | 001 | -1.6 |
| 2005-07-31 | Plug & abandon | 001 (608124001900) | -1.6 |
| 2005-08-09 | Drilling (spud) | 002 | -19.9 |
| 2005-12-11 | Plug & abandon | 002 (608124002000) | -91.7 |
| 2005-12-18 | Temporary abandonment | 002 (608124002000) | -91.7 |
| 2006-01-01 | Drilling (spud) | 002 | -103.9 |
| 2006-01-01 | Sidetrack | 002 (608124002000) | -103.9 |
| 2006-01-15 | Drilling (spud) | 002 | -103.9 |
| 2006-01-15 | Sidetrack | 002 (608124002001) | -103.9 |
| 2006-01-15 | Temporary abandonment | 002 (608124002002) | -103.9 |
| 2006-02-17 | Sidetrack | 002 (608124002002) | -103.9 |
| 2006-03-23 | Drilling (spud) | 002 | -110.7 |
| 2006-05-21 | Plug & abandon | 002 (608124002003) | -130.0 |
| 2006-05-29 | Sidetrack | 002 (608124002003) | -130.0 |
| 2006-06-03 | Drilling (spud) | 002 | -135.2 |
| 2006-06-04 | Temporary abandonment | 002 (608124002004) | -135.2 |
| 2006-11-03 | Drilling (spud) | 003 | -154.9 |
| 2007-10-07 | Plug & abandon | 003 (608124002300) | -210.4 |
| 2007-10-14 | Sidetrack | 003 (608124002300) | -210.4 |
| 2007-10-15 | Drilling (spud) | 003 | -210.4 |
| 2007-12-02 | Sidetrack | 003 (608124002301) | -239.1 |
| 2007-12-04 | Drilling (spud) | 003 | -239.1 |
| 2008-01-13 | Temporary abandonment | 003 (608124002302) | -247.3 |
| 2008-11-10 | Sidetrack | 002 (608124002004) | -250.8 |
| 2008-11-25 | Drilling (spud) | 002 | -250.8 |
| 2008-12-28 | Temporary abandonment | 002 (608124002005) | -268.7 |
| 2011-12-10 | Drilling (spud) | A004 | -278.8 |
| 2012-03-11 | Temporary abandonment | A004 (608124006000) | -302.0 |
| 2012-04-03 | Drilling (spud) | A001 | -329.3 |
| 2012-04-12 | Drilling (spud) | A006 | -329.3 |
| 2012-04-13 | Drilling (spud) | A011 | -329.3 |
| 2012-05-17 | Drilling (spud) | A007 | -378.1 |
| 2012-05-23 | Drilling (spud) | A005 | -378.1 |
| 2012-09-30 | Temporary abandonment | A001 (608124006200) | -494.6 |
| 2013-01-22 | Drilling (spud) | A008 | -498.6 |
| 2018-07-10 | Completion | A001 (608124006200) | -1,110.5 |
| 2018-11-01 | Well online (first production) | API 608124006200 | -1,484.7 |
| 2018-11-25 | Completion | A004 (608124006000) | -1,484.7 |
| 2019-03-10 | Drilling (spud) | A004 | -1,492.3 |
| 2019-03-10 | Sidetrack | A004 (608124006000) | -1,492.3 |
| 2019-04-07 | Completion | A004 (608124006001) | -1,494.1 |
| 2019-06-01 | Well online (first production) | API 608124006001 | -1,494.6 |
| 2019-12-29 | Sidetrack | A006 (608124006600) | -1,461.1 |
| 2020-01-04 | Drilling (spud) | A006 | -1,458.2 |
| 2020-01-19 | Drilling (spud) | A006 | -1,458.2 |
| 2020-01-19 | Sidetrack | A006 (608124006601) | -1,458.2 |
| 2020-02-09 | Sidetrack | A006 (608124006602) | -1,459.1 |
| 2020-02-12 | Drilling (spud) | A006 | -1,459.1 |
| 2020-06-07 | Completion | A006 (608124006603) | -1,469.5 |
| 2020-08-30 | Workover | A004 (608124006001) | -1,472.7 |
| 2020-09-01 | Well online (first production) | API 608124006603 | -1,474.8 |
| 2021-01-17 | Plug & abandon | A011 (608124007100) | -1,457.8 |
| 2021-01-31 | Sidetrack | A011 (608124007100) | -1,457.8 |
| 2021-02-05 | Drilling (spud) | A011 | -1,458.3 |
| 2021-02-21 | Drilling (spud) | A011 | -1,458.3 |
| 2021-02-21 | Sidetrack | A011 (608124007101) | -1,458.3 |
| 2021-03-30 | Plug & abandon | 003 (608124002302) | -1,456.5 |
| 2021-03-31 | Plug & abandon | 002 (608124002005) | -1,456.5 |
| 2021-05-23 | Completion | A011 (608124007102) | -1,456.1 |
| 2021-07-01 | Well online (first production) | API 608124007102 | -1,448.1 |
| 2021-07-15 | Workover | A001 (608124006200) | -1,448.1 |
| 2022-03-13 | Temporary abandonment | A008 (608124006800) | -1,366.5 |
| 2022-03-16 | Workover | A006 (608124006603) | -1,366.5 |
| 2022-05-15 | Completion | A008 (608124006800) | -1,351.7 |
| 2022-07-01 | Well online (first production) | API 608124006800 | -1,327.5 |
| 2022-12-18 | Completion | A007 (608124006700) | -1,274.1 |
| 2023-06-18 | Completion | A005 (608124006500) | -1,225.0 |
| 2023-07-11 | Workover | A011 (608124007102) | -1,216.8 |
| 2023-08-13 | Plug & abandon | A011 (608124007102) | -1,208.1 |
| 2023-09-17 | Sidetrack | A011 (608124007102) | -1,200.2 |
| 2023-09-18 | Drilling (spud) | A011 | -1,200.2 |
| 2023-10-15 | Completion | A011 (608124007103) | -1,191.3 |
| 2023-12-01 | Well online (first production) | API 608124007103 | -1,179.7 |
| 2024-07-11 | Drilling (spud) | A002 | -1,118.1 |
| 2024-12-01 | Completion | A002 (608124006302) | -1,094.9 |
| 2025-01-01 | Well online (first production) | API 608124006302 | -1,089.4 |
| 2025-09-07 | Completion | A003 (608124006404) | -1,038.7 |
| 2025-10-01 | Well online (first production) | API 608124006404 | -1,032.4 |
| 2025-10-03 | Workover | A008 (608124006800) | -1,032.4 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-989.0 M**; sum of per-well net NPV = **$-989.0 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124006001 | A004 | 32.24 | 307.1 | -628.5 | -321.4 | 32.5% |
| 2 | 608124006603 | A006 | 21.33 | 189.3 | -415.8 | -226.5 | 22.9% |
| 3 | 608124006200 | A001 | 14.94 | 65.0 | -291.3 | -226.3 | 22.9% |
| 4 | 608124006800 | A008 | 4.69 | -13.5 | -91.5 | -105.0 | 10.6% |
| 5 | 608124007102 | A011 | 0.93 | -17.7 | -18.0 | -35.7 | 3.6% |
| 6 | 608124006302 | A002 | 1.51 | -2.3 | -29.4 | -31.7 | 3.2% |
| 7 | 608124006404 | A003 | 1.99 | 15.3 | -38.8 | -23.4 | 2.4% |
| 8 | 608124007103 | A011 | 1.13 | 3.0 | -21.9 | -18.9 | 1.9% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
A004       -321.4 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
A006       -226.5 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
A001       -226.3 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
A008       -105.0 M  ▓▓▓▓▓▓▓▓
A011        -35.7 M  ▓▓▓
A002        -31.7 M  ▓▓
A003        -23.4 M  ▓▓
A011        -18.9 M  ▓
```

**[Interactive NPV waterfalls →](./big_foot_npv_stackup.html)** — two views: an **over-time NPV bridge** (each year's change in cumulative NPV, with the biggest swings annotated by the events that drove them) and this **per-well stackup** (each well's net NPV stepping to the field total). Hover any bar for detail. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev "Big Foot"`.

_Block scope: Single OGOR block (WR 29) for this development; block-level NPV decomposition is not applicable (identical to the field total)._

_The stackup covers the 7 producing wells. The field's 38 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Well Geometry (3D)

Interactive 3D well-path views — minimum-curvature trajectories from BSEE directional surveys, rendered with Plotly and Three.js — are in development for this field. When verified they will live at:

- `reports/bsee/big_foot_well_path_plotly.html`
- `reports/bsee/big_foot_well_path_threejs.html`

_They are intentionally **not linked yet**: the geometry render must first be confirmed to cover the same lease-resolved producers shown in the NPV stackup above (same APIs, same field), so the economics and the well paths never describe different wells._

---

## Financial Summary

Life-to-date field economics on public BSEE data (2000-09 -> 2026-04). D&C and facilities are one-time capital already incurred; revenue, royalty and opex accrue with production.

| Metric | Value |
|--------|------:|
| Revenue | $5,570.8 M |
| Royalty | $1,044.5 M |
| Variable opex | $315.0 M |
| Fixed opex | $900.0 M |
| D&C cost | $1,787.3 M |
| Facilities cost | $2,730.0 M |
| Net cashflow (undiscounted) | $-1,206.0 M |
| **NPV @ 10%** | **$-989.0 M** |
| MIRR (annual) | 4.53% |
| Producers | 7 |
| Injectors | 1 |
| Wellbores | 38 |

_Return metric: **MIRR** is the return measure used for these developments, not IRR. Deepwater Lower-Tertiary cashflows are heavily front-loaded (large D&C + facilities outflows, then a long production tail), so the net-cashflow sign changes more than once and the IRR polynomial can have multiple — or no — real roots; MIRR (single reinvestment/finance rate at the 10% discount rate) is well-defined and unambiguous. NPV @ 10% remains the primary value metric._

_Source-of-record: public BSEE OGOR-A production, drilling and WAR records, run through the field cashflow model._

---

## Price Sensitivity

NPV is linear in the oil price deck: each **+$1/bbl** on the realized oil price moves field NPV by **$+12.1 M**. Life-to-date NPV reaches **zero at a flat-equivalent realized WTI of $153/bbl**, versus the actual volume-weighted realized **$71/bbl** over the window.

| Flat-equivalent realized WTI ($/bbl) | NPV @ 10% ($MM) |
|-------------------------------------:|------------------:|
| 51 | -1,230.4 |
| 61 | -1,109.7 |
| 71  ← actual | -989.0 |
| 81 | -868.2 |
| 91 | -747.5 |

_Exact, not sampled: NPV is affine in a uniform price multiplier (revenue and royalty scale with price; variable/fixed opex, D&C, facilities and discounting do not), so one base run plus one scaled run define the entire line. 'Flat-equivalent realized WTI' is the volume-weighted average price; the underlying deck is the historical monthly WTI path._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Big Foot is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through a transparent cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → NPV) is reproducible end-to-end.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev "Big Foot"
  ```
