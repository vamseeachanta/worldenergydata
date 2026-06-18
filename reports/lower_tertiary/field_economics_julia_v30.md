# Julia Field Economics Report

**Development:** Julia (tieback15) &middot; **Lease:** G20351 &middot; **First oil:** 2016-03-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2025-05 (V30 frozen window)

## Summary

On public BSEE production + cost data, **Julia** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-530.6 M** (sanctioned V30 model).

- **4 producing wells** (**9 total wellbores**), generating **$4,715 M** gross revenue.
- A **high-capex, deepwater** signature: **$2,725 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-1,154.1 M** in **2017** and has since recovered **$+623.4 M** as production paid back capital.

> Generated from the sanctioned V30 financial model (`build_field_npv_timeline` reuses the same monthly cashflow + trimmed-discount formula as `reproduce_v30_financials`). The NPV timeline below is an additive presentation layer; it does not alter the computed final NPV.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-530.6 M** (reconciles to sanctioned baseline $-530.6 M).

Cumulative NPV path (by year): `██████▇▇▁▁▁▁▁▂▃▄▄▅`  _start $-76M → trough $-1,154M (2017) → latest $-531M_

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2008 | -76.8 | -75.8 | Drilling (spud): JU102 |
| 2009 | 0.0 | -75.8 |  |
| 2010 | 0.0 | -75.8 |  |
| 2011 | 0.0 | -75.8 |  |
| 2012 | 0.0 | -75.8 |  |
| 2013 | 0.0 | -75.8 |  |
| 2014 | -92.8 | -125.5 | Drilling (spud): DC101 |
| 2015 | -164.0 | -204.8 | Drilling (spud): JU102<br>Completion: JU102 (608124003301)<br>Drilling (spud): JU103 |
| 2016 | -1,931.3 | -1,099.6 | Drilling (spud): JU104<br>Well online (first production): API 608124003301<br>Completion: DC101 (608124009400)<br>Well online (first production): API 608124009400<br>Drilling (spud): JU105 |
| 2017 | -132.9 | -1,154.1 | Drilling (spud): JU105<br>Completion: JU104 (608124010800)<br>Well online (first production): API 608124010800 |
| 2018 | 242.4 | -1,064.1 |  |
| 2019 | 59.3 | -1,043.3 | Drilling (spud): JU106 |
| 2020 | 113.6 | -1,009.0 | Well online (first production): API 608124012701 |
| 2021 | 425.1 | -890.5 |  |
| 2022 | 623.6 | -731.7 |  |
| 2023 | 433.9 | -631.5 |  |
| 2024 | 360.9 | -555.4 |  |
| 2025 | 126.1 | -530.6 |  |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2008-02-17 | Drilling (spud) | JU102 | -10.4 |
| 2014-07-10 | Drilling (spud) | DC101 | -85.4 |
| 2015-01-20 | Drilling (spud) | JU102 | -130.5 |
| 2015-04-05 | Completion | JU102 (608124003301) | -140.7 |
| 2015-10-21 | Drilling (spud) | JU103 | -153.1 |
| 2016-02-13 | Drilling (spud) | JU104 | -322.8 |
| 2016-03-01 | Well online (first production) | API 608124003301 | -1,053.0 |
| 2016-04-04 | Completion | DC101 (608124009400) | -1,076.1 |
| 2016-05-01 | Well online (first production) | API 608124009400 | -1,097.1 |
| 2016-09-03 | Drilling (spud) | JU105 | -1,103.3 |
| 2017-01-24 | Drilling (spud) | JU105 | -1,098.1 |
| 2017-09-21 | Completion | JU104 (608124010800) | -1,143.8 |
| 2017-11-01 | Well online (first production) | API 608124010800 | -1,160.0 |
| 2019-05-10 | Drilling (spud) | JU106 | -1,038.9 |
| 2019-10-29 | Drilling (spud) | JU106 | -1,042.1 |
| 2020-02-01 | Well online (first production) | API 608124012701 | -1,047.7 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-530.6 M**; sum of per-well net NPV = **$-530.6 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124010800 | JU104 | 28.08 | 289.0 | -468.1 | -179.2 | 33.8% |
| 2 | 608124009400 | DC101 | 14.08 | 93.4 | -234.8 | -141.4 | 26.6% |
| 3 | 608124003301 | JU102 | 11.74 | 81.4 | -195.6 | -114.2 | 21.5% |
| 4 | 608124012701 | JU106 | 17.04 | 188.2 | -284.0 | -95.9 | 18.1% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
JU104      -179.2 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
DC101      -141.4 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
JU102      -114.2 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
JU106       -95.9 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓
```

**[Interactive NPV waterfalls →](./julia_npv_stackup.html)** — two views: an **over-time NPV bridge** (each year's change in cumulative NPV, with the biggest swings annotated by the events that drove them) and this **per-well stackup** (each well's net NPV stepping to the field total). Hover any bar for detail. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev Julia`.

_Block scope: Single OGOR block (WR 584) for this development; block-level NPV decomposition is not applicable (identical to the field total)._

_The stackup covers the 4 producing wells. The field's 9 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Well Geometry (3D)

Interactive 3D well-path views — minimum-curvature trajectories from BSEE directional surveys, rendered with Plotly and Three.js — are in development for this field. When verified they will live at:

- `reports/bsee/julia_well_path_plotly.html`
- `reports/bsee/julia_well_path_threejs.html`

_They are intentionally **not linked yet**: the geometry render must first be confirmed to cover the same lease-resolved producers shown in the NPV stackup above (same APIs, same field), so the economics and the well paths never describe different wells._

_Julia status: the current demo render (`scripts/bsee/demo_well_path_julia.py`) selects wells by `WELL_NAME` prefix and picks up unrelated shelf wells, with an API collision on `608124009400` (DC101 here vs. JU101 in the well catalog). Tracked in worldenergydata#493 — re-select by lease G20351, then embed._

---

## Financial Summary (V30 sanctioned model)

| Metric | Value |
|--------|------:|
| Revenue | $4,715.1 M |
| Royalty | $884.1 M |
| Variable opex | $425.6 M |
| Fixed opex | $693.8 M |
| D&C cost | $1,349.6 M |
| Facilities cost | $1,375.0 M |
| Net cashflow (undiscounted) | $-12.9 M |
| **NPV @ 10%** | **$-530.6 M** |
| MIRR (annual) | 6.31% |
| Producers | 4 |
| Injectors | 0 |
| Wellbores | 9 |

_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. NPV reproduced within golden-baseline tolerance by `worldenergydata.lower_tertiary.v30_financial_reproducer`._

---

## Price Sensitivity

NPV is linear in the oil price deck: each **+$1/bbl** on the realized oil price moves field NPV by **$+16.3 M**. Life-to-date NPV reaches **zero at a flat-equivalent realized WTI of $99/bbl**, versus the actual volume-weighted realized **$66/bbl** over the window.

| Flat-equivalent realized WTI ($/bbl) | NPV @ 10% ($MM) |
|-------------------------------------:|------------------:|
| 46 | -856.1 |
| 56 | -693.4 |
| 66  ← actual | -530.6 |
| 76 | -367.9 |
| 86 | -205.2 |

_Exact, not sampled: NPV is affine in a uniform price multiplier (revenue and royalty scale with price; variable/fixed opex, D&C, facilities and discounting do not), so one base run plus one scaled run define the entire line. 'Flat-equivalent realized WTI' is the volume-weighted average price; the underlying deck is the historical monthly WTI path._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Julia is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev Julia
  # frozen V30 reference report: add --frozen
  ```
