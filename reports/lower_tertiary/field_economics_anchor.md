# Anchor Field Economics Report

**Development:** Anchor (subsea20) &middot; **Lease:** 2 leases (G31751, G31752) &middot; **First oil:** 2024-08-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04 (latest); frozen V30 reference NPV = -$530.6M

> **LATEST run.** The NPV timeline is built from the V30 cashflow model extended through the latest available BSEE OGOR-A month (`build_field_npv_timeline(dev, end_date=...)`). The terminal cumulative NPV reflects the extended window and therefore differs from the frozen V30 sanctioned value (shown for reference below). The frozen V30 baseline (`golden_baseline_v30.yml`) is unchanged.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-1,586.9 M** (frozen V30 reference: $-1,732.8 M; delta +145.9 M).

Cumulative NPV path (by year): `█▇▇▇▇▇▇▇▆▄▁▁▁`

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2014 | -149.6 | -144.5 | Drilling (spud): 001<br>Sidetrack: 001 (608114062100)<br>Drilling (spud): 002 |
| 2015 | -37.6 | -177.4 | Sidetrack: 002 (608114063500)<br>Drilling (spud): 002<br>Sidetrack: 002 (608114063501) |
| 2016 | -166.4 | -311.3 | Drilling (spud): 001<br>Drilling (spud): 003<br>Sidetrack: 003 (608114067300) |
| 2017 | -18.4 | -325.3 |  |
| 2018 | 0.0 | -325.3 |  |
| 2019 | -5.6 | -328.6 | Drilling (spud): SB001 |
| 2020 | 0.0 | -328.6 |  |
| 2021 | -19.2 | -337.7 | Drilling (spud): AP001 |
| 2022 | -406.9 | -518.8 | Drilling (spud): AP002 |
| 2023 | -860.4 | -872.9 | Drilling (spud): BP003 |
| 2024 | -2,459.7 | -1,797.0 | Completion: AP001 (608114075000)<br>Well online (first production): API 608114075000<br>Completion: AP002 (608114075100)<br>Well online (first production): API 608114075100 |
| 2025 | 435.5 | -1,648.4 |  |
| 2026 | 192.5 | -1,586.9 | Well online (first production): API 608114076101 |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2014-03-16 | Drilling (spud) | 001 | -12.8 |
| 2014-05-25 | Sidetrack | 001 (608114062100) | -52.4 |
| 2014-05-28 | Drilling (spud) | 001 | -52.4 |
| 2014-08-12 | Drilling (spud) | 002 | -77.9 |
| 2015-07-05 | Sidetrack | 002 (608114063500) | -157.9 |
| 2015-07-09 | Drilling (spud) | 002 | -157.9 |
| 2015-08-09 | Sidetrack | 002 (608114063501) | -170.5 |
| 2015-08-14 | Drilling (spud) | 002 | -170.5 |
| 2016-01-26 | Drilling (spud) | 001 | -181.4 |
| 2016-02-26 | Drilling (spud) | 001 | -190.8 |
| 2016-09-17 | Drilling (spud) | 003 | -270.9 |
| 2016-12-04 | Drilling (spud) | 003 | -311.3 |
| 2016-12-04 | Sidetrack | 003 (608114067300) | -311.3 |
| 2019-11-19 | Drilling (spud) | SB001 | -328.6 |
| 2021-12-08 | Drilling (spud) | AP001 | -337.7 |
| 2022-11-16 | Drilling (spud) | AP002 | -480.9 |
| 2023-11-26 | Drilling (spud) | BP003 | -818.0 |
| 2024-03-10 | Completion | AP001 (608114075000) | -1,051.9 |
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

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative).

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
AP002      -809.7 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
AP001      -760.7 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
608114076101    -16.6 M  ▓
```

_Block scope: Single OGOR block (GC 807) for this development; block-level NPV decomposition is not applicable (identical to the field total)._

_The stackup covers the 2 producing wells. The field's 15 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Financial Summary

**Latest window (2000-09 -> 2026-04) vs frozen V30 reference.** D&C and facilities are one-time capital already incurred, so they are unchanged from V30; revenue, royalty and opex scale with the additional production.

| Metric | Latest | Frozen V30 (reference) |
|--------|------:|------:|
| **NPV @ 10%** | **$-1,586.9 M** | $-1,732.8 M |
| Revenue | $1,279.2 M | $476.3 M |
| Oil produced (MMbbl) | 18.6 | 6.9 |

_Latest NPV from `build_field_npv_timeline(dev, end_date)`; latest revenue/oil from `latest_baseline.yml` (regenerated through 2026-04). A full latest component breakdown (royalty/opex split) is not recomputed here — the frozen V30 breakdown below is the audited source-of-record._

### Frozen V30 reference (audited source-of-record)

| Metric | Value |
|--------|------:|
| Revenue | $476.3 M |
| Royalty | $89.3 M |
| Variable opex | $41.5 M |
| Fixed opex | $125.0 M |
| D&C cost | $1,761.2 M |
| Facilities cost | $2,400.0 M |
| Net cashflow (undiscounted) | $-3,940.7 M |
| **NPV @ 10%** | **$-1,732.8 M** |
| MIRR (annual) | -17.68% |
| Producers | 2 |
| Injectors | 0 |
| Wellbores | 15 |

_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. NPV reproduced within golden-baseline tolerance by `worldenergydata.lower_tertiary.v30_financial_reproducer`._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Anchor is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev Anchor
  # frozen V30 reference report: add --frozen
  ```
