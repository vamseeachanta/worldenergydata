# Cascade Chinook Field Economics Report

**Development:** Cascade Chinook (subsea15) &middot; **Lease:** 2 leases (G16965, G16997) &middot; **First oil:** 2014-01-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04 (latest); frozen V30 reference NPV = -$530.6M

> **LATEST run.** The NPV timeline is built from the V30 cashflow model extended through the latest available BSEE OGOR-A month (`build_field_npv_timeline(dev, end_date=...)`). The terminal cumulative NPV reflects the extended window and therefore differs from the frozen V30 sanctioned value (shown for reference below). The frozen V30 baseline (`golden_baseline_v30.yml`) is unchanged.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-1,480.5 M** (frozen V30 reference: $-1,477.2 M; delta -3.3 M).

Cumulative NPV path (by year): `█▇▇▇▇▇▇▆▆▆▄▂▁▁▁▁▁▁▁▁▁▁▁▁▁`

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2002 | -76.8 | -75.5 | Drilling (spud): 001<br>Sidetrack: 001 (608124000800) |
| 2003 | -125.6 | -187.4 | Drilling (spud): 001 |
| 2004 | 0.0 | -187.4 |  |
| 2005 | -93.6 | -254.6 | Drilling (spud): 002<br>Sidetrack: 002 (608124001600) |
| 2006 | 0.0 | -254.6 |  |
| 2007 | 0.0 | -254.6 |  |
| 2008 | -44.8 | -277.9 | Drilling (spud): CA003 |
| 2009 | -172.0 | -363.0 | Drilling (spud): 004<br>Drilling (spud): 002<br>Completion: CA003 (608124003800) |
| 2010 | -144.0 | -429.4 | Drilling (spud): 002<br>Drilling (spud): CH002 |
| 2011 | 0.0 | -429.4 |  |
| 2012 | -726.4 | -697.5 | Sidetrack: 004 (608124004700)<br>Drilling (spud): CA004<br>Well online (first production): API 608124004602<br>Completion: CA004 (608124004701)<br>Drilling (spud): 005 |
| 2013 | -1,252.0 | -1,114.3 | Drilling (spud): CA006<br>Completion: CA006 (608124008300) |
| 2014 | -772.5 | -1,361.6 | Well online (first production): API 608124008300<br>Drilling (spud): CH004 |
| 2015 | -159.6 | -1,406.4 | Completion: CH004 (608124009700) |
| 2016 | -114.0 | -1,435.2 |  |
| 2017 | -198.9 | -1,480.1 |  |
| 2018 | -141.6 | -1,511.1 | Well online (first production): API 608124009700 |
| 2019 | 110.8 | -1,490.0 |  |
| 2020 | -35.9 | -1,496.1 | Workover: CA003 (608124003800) |
| 2021 | 37.5 | -1,490.3 |  |
| 2022 | 84.6 | -1,478.2 |  |
| 2023 | 31.4 | -1,474.2 |  |
| 2024 | -14.2 | -1,475.8 |  |
| 2025 | -33.5 | -1,479.4 |  |
| 2026 | -11.1 | -1,480.5 |  |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2002-01-31 | Drilling (spud) | 001 | -0.8 |
| 2002-04-16 | Sidetrack | 001 (608124000800) | -63.8 |
| 2002-04-23 | Drilling (spud) | 001 | -63.8 |
| 2003-01-13 | Drilling (spud) | 001 | -89.3 |
| 2005-03-19 | Drilling (spud) | 002 | -195.1 |
| 2005-10-09 | Drilling (spud) | 002 | -241.9 |
| 2005-10-09 | Sidetrack | 002 (608124001600) | -241.9 |
| 2008-11-06 | Drilling (spud) | CA003 | -265.1 |
| 2009-11-25 | Drilling (spud) | 004 | -343.5 |
| 2009-11-27 | Drilling (spud) | 002 | -343.5 |
| 2009-12-28 | Completion | CA003 (608124003800) | -363.0 |
| 2010-01-08 | Drilling (spud) | 002 | -383.6 |
| 2010-02-11 | Drilling (spud) | CH002 | -400.2 |
| 2012-04-08 | Sidetrack | 004 (608124004700) | -511.0 |
| 2012-04-13 | Drilling (spud) | CA004 | -511.0 |
| 2012-09-01 | Well online (first production) | API 608124004602 | -643.2 |
| 2012-10-28 | Completion | CA004 (608124004701) | -661.2 |
| 2012-12-18 | Drilling (spud) | 005 | -697.5 |
| 2013-01-01 | Drilling (spud) | CA006 | -723.7 |
| 2013-12-15 | Completion | CA006 (608124008300) | -1,114.3 |
| 2014-01-01 | Well online (first production) | API 608124008300 | -1,403.2 |
| 2014-12-07 | Drilling (spud) | CH004 | -1,361.6 |
| 2015-04-05 | Completion | CH004 (608124009700) | -1,386.9 |
| 2018-07-01 | Well online (first production) | API 608124009700 | -1,529.5 |
| 2020-01-11 | Workover | CA003 (608124003800) | -1,489.0 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-1,480.5 M**; sum of per-well net NPV = **$-1,480.5 M** (residual $0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124009700 | CH004 | 24.27 | 109.4 | -1,084.2 | -974.8 | 65.8% |
| 2 | 608124008300 | CA006 | 10.43 | 28.1 | -465.9 | -437.8 | 29.6% |
| 3 | 608124004602 | CH002 | 1.69 | 7.8 | -75.6 | -67.8 | 4.6% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative).

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
CH004      -974.8 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
CA006      -437.8 M  ▓▓▓▓▓▓▓▓▓▓▓
CH002       -67.8 M  ▓▓
```

**By block (OGOR `AREA_CODE_BLOCK_NUM`):**

| Block | Oil (MMbbl) | % of field oil |
|-------|------------:|---------------:|
| WR  469 | 25.96 | 71.3% |
| WR  206 | 10.43 | 28.7% |

_Block scope: 2 OGOR blocks present; per-block oil shares shown. Per-block NPV would require a block-level cost split (gap: shared facilities/D&C are field-level in V30, not block-tagged)._

_The stackup covers the 3 producing wells. The field's 14 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Financial Summary

**Latest window (2000-09 -> 2026-04) vs frozen V30 reference.** D&C and facilities are one-time capital already incurred, so they are unchanged from V30; revenue, royalty and opex scale with the additional production.

| Metric | Latest | Frozen V30 (reference) |
|--------|------:|------:|
| **NPV @ 10%** | **$-1,480.5 M** | $-1,477.2 M |
| Revenue | $2,778.0 M | $2,326.9 M |
| Oil produced (MMbbl) | 39.7 | 34.3 |

_Latest NPV from `build_field_npv_timeline(dev, end_date)`; latest revenue/oil from `latest_baseline.yml` (regenerated through 2026-04). A full latest component breakdown (royalty/opex split) is not recomputed here — the frozen V30 breakdown below is the audited source-of-record._

### Frozen V30 reference (audited source-of-record)

| Metric | Value |
|--------|------:|
| Revenue | $2,326.9 M |
| Royalty | $436.3 M |
| Variable opex | $137.3 M |
| Fixed opex | $1,700.0 M |
| D&C cost | $1,973.6 M |
| Facilities cost | $1,900.0 M |
| Net cashflow (undiscounted) | $-3,820.3 M |
| **NPV @ 10%** | **$-1,477.2 M** |
| MIRR (annual) | -1.77% |
| Producers | 3 |
| Injectors | 0 |
| Wellbores | 14 |

_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. NPV reproduced within golden-baseline tolerance by `worldenergydata.lower_tertiary.v30_financial_reproducer`._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Cascade Chinook is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev "Cascade Chinook"
  # frozen V30 reference report: add --frozen
  ```
