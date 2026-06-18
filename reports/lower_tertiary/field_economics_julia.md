# Julia Field Economics Report

**Development:** Julia (tieback15) &middot; **Lease:** G20351 &middot; **First oil:** 2016-03-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04 (latest); frozen V30 reference NPV = -$530.6M

## Summary

On public BSEE production + cost data, **Julia** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-482.8 M** (frozen V30 sanctioned reference $-530.6 M).

- **77.5 MMbbl** oil produced from **4 producing wells** (**9 total wellbores**), generating **$5,168 M** gross revenue.
- A **high-capex, deepwater** signature: **$2,725 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-1,154.1 M** in **2017** and has since recovered **$+671.3 M** as production paid back capital.

> **LATEST run.** The NPV timeline is built from the V30 cashflow model extended through the latest available BSEE OGOR-A month (`build_field_npv_timeline(dev, end_date=...)`). The terminal cumulative NPV reflects the extended window and therefore differs from the frozen V30 sanctioned value (shown for reference below). The frozen V30 baseline (`golden_baseline_v30.yml`) is unchanged.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-482.8 M** (frozen V30 reference: $-530.6 M; delta +47.8 M).

Cumulative NPV path (by year): `██████▇▇▁▁▁▁▁▂▃▄▄▅▅`  _start $-76M → trough $-1,154M (2017) → latest $-483M_

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
| 2019 | 59.3 | -1,043.3 | Drilling (spud): JU106<br>Drilling (spud): JU106 |
| 2020 | 113.6 | -1,009.0 | Well online (first production): API 608124012701 |
| 2021 | 425.1 | -890.5 |  |
| 2022 | 623.6 | -731.7 |  |
| 2023 | 433.9 | -631.5 |  |
| 2024 | 360.9 | -555.4 |  |
| 2025 | 278.4 | -502.1 |  |
| 2026 | 108.0 | -482.8 |  |

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

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-482.8 M**; sum of per-well net NPV = **$-482.8 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124010800 | JU104 | 30.87 | 314.6 | -476.2 | -161.6 | 33.5% |
| 2 | 608124009400 | DC101 | 14.67 | 98.9 | -226.3 | -127.4 | 26.4% |
| 3 | 608124003301 | JU102 | 12.57 | 89.2 | -194.0 | -104.8 | 21.7% |
| 4 | 608124012701 | JU106 | 19.37 | 209.8 | -298.8 | -89.0 | 18.4% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
JU104      -161.6 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
DC101      -127.4 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
JU102      -104.8 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
JU106       -89.0 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓
```

**[Interactive NPV stackup waterfall →](./julia_npv_stackup.html)** — each well's net NPV steps down to the field total; hover a bar for its gross / allocated-cost / net breakdown. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev Julia`.

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

## Financial Summary

**Latest window (2000-09 -> 2026-04) vs frozen V30 reference.** D&C and facilities are one-time capital already incurred, so they are unchanged from V30; revenue, royalty and opex scale with the additional production.

| Metric | Latest | Frozen V30 (reference) |
|--------|------:|------:|
| **NPV @ 10%** | **$-482.8 M** | $-530.6 M |
| Revenue | $5,168.4 M | $4,715.2 M |
| Oil produced (MMbbl) | 77.5 | 70.9 |

_Latest NPV from `build_field_npv_timeline(dev, end_date)`; latest revenue/oil from `latest_baseline.yml` (regenerated through 2026-04). A full latest component breakdown (royalty/opex split) is not recomputed here — the frozen V30 breakdown below is the audited source-of-record._

### Frozen V30 reference (audited source-of-record)

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

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Julia is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev Julia --lease G20351
  # frozen V30 reference report: add --frozen
  ```
