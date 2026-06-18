# Stones Field Economics Report

**Development:** Stones (subsea15) &middot; **Lease:** G17001 &middot; **First oil:** 2016-09-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04 (latest); frozen V30 reference NPV = -$530.6M

> **LATEST run.** The NPV timeline is built from the V30 cashflow model extended through the latest available BSEE OGOR-A month (`build_field_npv_timeline(dev, end_date=...)`). The terminal cumulative NPV reflects the extended window and therefore differs from the frozen V30 sanctioned value (shown for reference below). The frozen V30 baseline (`golden_baseline_v30.yml`) is unchanged.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-1,460.8 M** (frozen V30 reference: $-1,479.5 M; delta +18.7 M).

Cumulative NPV path (by year): `█▇▇▇▇▇▇▇▇▇▆▅▁▁▁▁▁▁▂▂▂▂▂`

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
| 2025 | 143.8 | -1,467.3 | Workover: SN115 (608124012900)<br>Workover: SN114 (608124013701) |
| 2026 | 49.5 | -1,460.8 |  |

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
| 2025-12-13 | Workover | SN115 (608124012900) | -1,467.3 |
| 2025-12-16 | Workover | SN114 (608124013701) | -1,467.3 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-1,460.8 M**; sum of per-well net NPV = **$-1,460.8 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124009500 | SN105 | 18.69 | 105.9 | -422.4 | -316.5 | 21.7% |
| 2 | 608124009900 | SN109 | 16.60 | 125.4 | -375.2 | -249.8 | 17.1% |
| 3 | 608124012300 | SN213 | 16.44 | 139.4 | -371.6 | -232.2 | 15.9% |
| 4 | 608124012900 | SN115 | 12.93 | 81.8 | -292.4 | -210.6 | 14.4% |
| 5 | 608124013400 | SN216 | 13.77 | 122.0 | -311.2 | -189.2 | 13.0% |
| 6 | 608124010400 | SN208 | 2.87 | -18.8 | -64.9 | -83.7 | 5.7% |
| 7 | 608124011700 | SN207 | 2.26 | -3.4 | -51.2 | -54.5 | 3.7% |
| 8 | 608124013701 | SN114 | 2.68 | 16.7 | -60.6 | -44.0 | 3.0% |
| 9 | 608124014301 | SN219 | 2.55 | 14.6 | -57.7 | -43.1 | 3.0% |
| 10 | 608124011001 | SN110 | 0.25 | -31.6 | -5.6 | -37.2 | 2.5% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative).

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
SN105      -316.5 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN109      -249.8 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN213      -232.2 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN115      -210.6 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN216      -189.2 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
SN208       -83.7 M  ▓▓▓▓▓▓
SN207       -54.5 M  ▓▓▓▓
SN114       -44.0 M  ▓▓▓
SN219       -43.1 M  ▓▓▓
SN110       -37.2 M  ▓▓▓
```

_Block scope: Single OGOR block (WR 508) for this development; block-level NPV decomposition is not applicable (identical to the field total)._

_The stackup covers the 10 producing wells. The field's 22 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Financial Summary

**Latest window (2000-09 -> 2026-04) vs frozen V30 reference.** D&C and facilities are one-time capital already incurred, so they are unchanged from V30; revenue, royalty and opex scale with the additional production.

| Metric | Latest | Frozen V30 (reference) |
|--------|------:|------:|
| **NPV @ 10%** | **$-1,460.8 M** | $-1,479.5 M |
| Revenue | $5,946.6 M | $5,582.4 M |
| Oil produced (MMbbl) | 89.0 | 83.7 |

_Latest NPV from `build_field_npv_timeline(dev, end_date)`; latest revenue/oil from `latest_baseline.yml` (regenerated through 2026-04). A full latest component breakdown (royalty/opex split) is not recomputed here — the frozen V30 breakdown below is the audited source-of-record._

### Frozen V30 reference (audited source-of-record)

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

_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. NPV reproduced within golden-baseline tolerance by `worldenergydata.lower_tertiary.v30_financial_reproducer`._

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
