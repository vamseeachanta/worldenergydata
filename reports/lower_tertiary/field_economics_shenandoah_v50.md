# Shenandoah Field Economics Report

**Development:** Shenandoah (subsea20) &middot; **Lease:** 2 leases (G25232, G31938) &middot; **First oil:** 2025-02-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04 (latest); frozen V30 reference NPV = -$530.6M

## Summary

On public BSEE production + cost data, **Shenandoah** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-991.3 M** (frozen V30 sanctioned reference $-1,166.4 M).

- **21.2 MMbbl** oil produced from **1 producing wells** (**23 total wellbores**), generating **$1,460 M** gross revenue.
- A **high-capex, deepwater** signature: **$3,866 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-1,086.3 M** in **2025** and has since recovered **$+95.0 M** as production paid back capital.

> **LATEST run.** The NPV timeline is built from the V30 cashflow model extended through the latest available BSEE OGOR-A month (`build_field_npv_timeline(dev, end_date=...)`). The terminal cumulative NPV reflects the extended window and therefore differs from the frozen V30 sanctioned value (shown for reference below). The frozen V30 baseline (`golden_baseline_v30.yml`) is unchanged.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-991.3 M** (frozen V30 reference: $-1,166.4 M; delta +175.1 M).

Cumulative NPV path (by year): `█▇▇▇▇▇▆▅▅▅▅▅▅▅▅▃▂▁▁`  _start $-140M → trough $-1,086M (2025) → latest $-991M_

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2008 | -143.2 | -139.8 | Drilling (spud): 001 |
| 2009 | -16.8 | -155.7 |  |
| 2010 | 0.0 | -155.7 |  |
| 2011 | 0.0 | -155.7 |  |
| 2012 | -140.0 | -248.7 | Drilling (spud): 001<br>Drilling (spud): 002 |
| 2013 | -22.4 | -263.2 |  |
| 2014 | -140.0 | -340.8 | Drilling (spud): 002<br>Sidetrack: 002 (608124009300) |
| 2015 | -153.6 | -417.9 | Drilling (spud): 003<br>Sidetrack: 003 (608124010101) |
| 2016 | -104.0 | -466.6 | Drilling (spud): SA005<br>Drilling (spud): 003 |
| 2017 | -44.8 | -486.2 | Drilling (spud): 003<br>Sidetrack: 003 (608124011300)<br>Sidetrack: 003 (608124011301)<br>Drilling (spud): SA006 |
| 2018 | 0.0 | -486.2 |  |
| 2019 | 0.0 | -486.2 |  |
| 2020 | 0.0 | -486.2 |  |
| 2021 | 0.0 | -486.2 |  |
| 2022 | -59.2 | -501.1 | Drilling (spud): SA008<br>Drilling (spud): SA009 |
| 2023 | -853.9 | -705.5 | Sidetrack: SA007 (608124014001) |
| 2024 | -1,033.8 | -927.6 | Completion: SA008 (608124014100)<br>Completion: SA009 (608124014400) |
| 2025 | -747.8 | -1,086.3 | Well online (first production): API 608124014400<br>Well online (first production): API 608124014100<br>Well online (first production): API 608124013900<br>Well online (first production): API 608124014003<br>Workover: SA010 (608124013900) |
| 2026 | 514.4 | -991.3 |  |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2008-06-04 | Drilling (spud) | 001 | -15.2 |
| 2008-07-03 | Drilling (spud) | 001 | -38.2 |
| 2008-11-11 | Drilling (spud) | 001 | -116.2 |
| 2012-06-29 | Drilling (spud) | 001 | -156.8 |
| 2012-09-17 | Drilling (spud) | 002 | -200.4 |
| 2014-05-29 | Drilling (spud) | 002 | -264.6 |
| 2014-12-07 | Drilling (spud) | 002 | -340.8 |
| 2014-12-07 | Sidetrack | 002 (608124009300) | -340.8 |
| 2015-05-26 | Drilling (spud) | 003 | -343.2 |
| 2015-09-08 | Drilling (spud) | 003 | -388.3 |
| 2015-10-25 | Sidetrack | 003 (608124010101) | -396.7 |
| 2015-10-26 | Drilling (spud) | 003 | -396.7 |
| 2015-12-21 | Drilling (spud) | 003 | -417.9 |
| 2016-03-14 | Drilling (spud) | SA005 | -425.2 |
| 2016-12-16 | Drilling (spud) | 003 | -466.6 |
| 2017-02-19 | Drilling (spud) | 003 | -482.1 |
| 2017-02-19 | Sidetrack | 003 (608124011300) | -482.1 |
| 2017-03-05 | Sidetrack | 003 (608124011301) | -486.2 |
| 2017-03-08 | Drilling (spud) | SA006 | -486.2 |
| 2022-11-22 | Drilling (spud) | SA008 | -488.7 |
| 2022-11-28 | Drilling (spud) | SA009 | -488.7 |
| 2023-12-17 | Sidetrack | SA007 (608124014001) | -705.5 |
| 2024-07-07 | Completion | SA008 (608124014100) | -802.2 |
| 2024-11-02 | Completion | SA009 (608124014400) | -897.1 |
| 2025-02-01 | Well online (first production) | API 608124014400 | -1,166.4 |
| 2025-07-01 | Well online (first production) | API 608124014100 | -1,167.8 |
| 2025-08-01 | Well online (first production) | API 608124013900 | -1,160.5 |
| 2025-08-01 | Well online (first production) | API 608124014003 | -1,160.5 |
| 2025-09-24 | Workover | SA010 (608124013900) | -1,147.0 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-991.3 M**; sum of per-well net NPV = **$-991.3 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124014400 | SA009 | 6.41 | -14.0 | -318.1 | -332.1 | 33.5% |
| 2 | 608124014100 | SA008 | 5.53 | -12.7 | -274.8 | -287.5 | 29.0% |
| 3 | 608124014003 | SA007 | 5.73 | 54.5 | -284.4 | -229.9 | 23.2% |
| 4 | 608124013900 | SA010 | 3.51 | 32.4 | -174.2 | -141.8 | 14.3% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
SA009      -332.1 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SA008      -287.5 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SA007      -229.9 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SA010      -141.8 M  ▓▓▓▓▓▓▓▓▓▓
```

**[Interactive NPV waterfalls →](./shenandoah_npv_stackup.html)** — two views: an **over-time NPV bridge** (each year's change in cumulative NPV, with the biggest swings annotated by the events that drove them) and this **per-well stackup** (each well's net NPV stepping to the field total). Hover any bar for detail. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev Shenandoah`.

_Block scope: Single OGOR block (WR 51) for this development; block-level NPV decomposition is not applicable (identical to the field total)._

_The stackup covers the 1 producing wells. The field's 23 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Well Geometry (3D)

Interactive 3D well-path views — minimum-curvature trajectories from BSEE directional surveys, rendered with Plotly and Three.js — are in development for this field. When verified they will live at:

- `reports/bsee/shenandoah_well_path_plotly.html`
- `reports/bsee/shenandoah_well_path_threejs.html`

_They are intentionally **not linked yet**: the geometry render must first be confirmed to cover the same lease-resolved producers shown in the NPV stackup above (same APIs, same field), so the economics and the well paths never describe different wells._

---

## Financial Summary

**Latest window (2000-09 -> 2026-04) vs frozen V30 reference.** D&C and facilities are one-time capital already incurred, so they are unchanged from V30; revenue, royalty and opex scale with the additional production.

| Metric | Latest | Frozen V30 (reference) |
|--------|------:|------:|
| **NPV @ 10%** | **$-991.3 M** | $-1,166.4 M |
| Revenue | $1,459.7 M | $0.3 M |
| Oil produced (MMbbl) | 21.2 | 0.0 |

_Latest NPV from `build_field_npv_timeline(dev, end_date)`; latest revenue/oil from `latest_baseline.yml` (regenerated through 2026-04). A full latest component breakdown (royalty/opex split) is not recomputed here — the frozen V30 breakdown below is the audited source-of-record._

### Frozen V30 reference (audited source-of-record)

| Metric | Value |
|--------|------:|
| Revenue | $0.3 M |
| Royalty | $0.1 M |
| Variable opex | $0.0 M |
| Fixed opex | $12.5 M |
| D&C cost | $1,816.5 M |
| Facilities cost | $2,050.0 M |
| Net cashflow (undiscounted) | $-3,878.8 M |
| **NPV @ 10%** | **$-1,166.4 M** |
| Producers | 1 |
| Injectors | 0 |
| Wellbores | 23 |

_Return metric: **MIRR** is the sanctioned return measure for these developments, not IRR. Deepwater Lower-Tertiary cashflows are heavily front-loaded (large D&C + facilities outflows, then a long production tail), so the net-cashflow sign changes more than once and the IRR polynomial can have multiple — or no — real roots; MIRR (single reinvestment/finance rate at the 10% discount rate) is well-defined and unambiguous. NPV @ 10% remains the primary value metric._

_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. NPV reproduced within golden-baseline tolerance by `worldenergydata.lower_tertiary.v30_financial_reproducer`._

---

## Price Sensitivity

NPV is linear in the oil price deck: each **+$1/bbl** on the realized oil price moves field NPV by **$+3.2 M**. Life-to-date NPV reaches **zero at a flat-equivalent realized WTI of $376/bbl**, versus the actual volume-weighted realized **$69/bbl** over the window.

| Flat-equivalent realized WTI ($/bbl) | NPV @ 10% ($MM) |
|-------------------------------------:|------------------:|
| 49 | -1,055.9 |
| 59 | -1,023.6 |
| 69  ← actual | -991.3 |
| 79 | -959.0 |
| 89 | -926.7 |

_Exact, not sampled: NPV is affine in a uniform price multiplier (revenue and royalty scale with price; variable/fixed opex, D&C, facilities and discounting do not), so one base run plus one scaled run define the entire line. 'Flat-equivalent realized WTI' is the volume-weighted average price; the underlying deck is the historical monthly WTI path._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Shenandoah is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev Shenandoah
  # frozen V30 reference report: add --frozen
  ```
