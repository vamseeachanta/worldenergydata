# Jack St Malo Field Economics Report

**Development:** Jack St Malo (subsea15) &middot; **Lease:** 6 leases (G17015, G17016, G18745, G18753, G20394, G21245) &middot; **First oil:** 2014-12-01 &middot; **Discount rate:** 10% annual

**Data window:** 2000-09 -> 2026-04 (latest); frozen V30 reference NPV = -$530.6M

## Summary

On public BSEE production + cost data, **Jack St Malo** is **NPV-negative at 10%** life-to-date: terminal cumulative NPV **$-804.5 M** (frozen V30 sanctioned reference $-945.0 M).

- **438.7 MMbbl** oil produced from **22 producing wells** (**73 total wellbores**), generating **$27,891 M** gross revenue.
- A **high-capex, deepwater** signature: **$12,850 M** of one-time D&C + facilities capital is the dominant driver of the NPV.
- The cumulative-NPV path bottomed at **$-3,154.7 M** in **2014** and has since recovered **$+2,350.2 M** as production paid back capital.

> **LATEST run.** The NPV timeline is built from the V30 cashflow model extended through the latest available BSEE OGOR-A month (`build_field_npv_timeline(dev, end_date=...)`). The terminal cumulative NPV reflects the extended window and therefore differs from the frozen V30 sanctioned value (shown for reference below). The frozen V30 baseline (`golden_baseline_v30.yml`) is unchanged.

---

## NPV Timeline

Cumulative discounted NPV evolution over field life, with critical well operations annotated. Terminal cumulative NPV = **$-804.5 M** (frozen V30 reference: $-945.0 M; delta +140.5 M).

Cumulative NPV path (by year): `█▇▇▇▇▇▇▇▆▆▆▆▆▅▁▁▁▁▂▃▃▄▄▅▅▆▆`  _start $-75M → trough $-3,155M (2014) → latest $-804M_

| Year | Net Cashflow ($MM) | Cumulative NPV ($MM) | Critical Operations |
|------|-------------------:|---------------------:|---------------------|
| 2000 | -76.0 | -74.9 | Drilling (spud): 001<br>Sidetrack: 001 (608124000400) |
| 2001 | -4.0 | -78.8 |  |
| 2002 | 0.0 | -78.8 |  |
| 2003 | -79.2 | -138.7 | Drilling (spud): 002 |
| 2004 | -112.8 | -218.3 | Drilling (spud): 001<br>Sidetrack: 001 (608124001300) |
| 2005 | -160.0 | -318.9 | Drilling (spud): PS002 |
| 2006 | -149.6 | -405.7 | Completion: PS002 (608124001700)<br>Well online (first production): API 608124001700 |
| 2007 | -133.6 | -473.7 | Drilling (spud): 002<br>Drilling (spud): 001<br>Drilling (spud): 003 |
| 2008 | -364.8 | -648.7 | Drilling (spud): 002<br>Drilling (spud): 003 |
| 2009 | -1.6 | -649.4 | Drilling (spud): 001 |
| 2010 | 0.0 | -649.4 |  |
| 2011 | -231.2 | -728.7 | Drilling (spud): PS001<br>Drilling (spud): PS005<br>Drilling (spud): PN001<br>Drilling (spud): PN002<br>Drilling (spud): PN003<br>Drilling (spud): PS003<br>Drilling (spud): PS004 |
| 2012 | -584.4 | -921.3 | Drilling (spud): PS004<br>Sidetrack: PS004 (608124005102)<br>Well online (first production): API 608124005600<br>Drilling (spud): PS002 |
| 2013 | -624.8 | -1,106.4 | Well online (first production): API 608124001701 |
| 2014 | -7,927.3 | -3,154.7 | Completion: PS001 (608124005700)<br>Well online (first production): API 608124005000<br>Well online (first production): API 608124005300 |
| 2015 | 387.3 | -3,060.6 | Completion: PS005 (608124005000)<br>Well online (first production): API 608124005700<br>Workover: PS005 (608124005000)<br>Well online (first production): API 608124005103<br>Drilling (spud): PS001<br>Drilling (spud): PN007<br>Completion: PS001 (608124005201) |
| 2016 | 583.9 | -2,932.8 | Completion: PS004 (608124005800)<br>Well online (first production): API 608124005800<br>Completion: PN002 (608124005400)<br>Well online (first production): API 608124005400<br>Completion: PN007 (608124010701)<br>Well online (first production): API 608124010701<br>Drilling (spud): PS001<br>Drilling (spud): PS002 |
| 2017 | 856.5 | -2,760.3 | Well online (first production): API 608124005203<br>Drilling (spud): PS007<br>Drilling (spud): PS008<br>Well online (first production): API 608124011400<br>Drilling (spud): PS005<br>Completion: PS007 (608124011504)<br>Well online (first production): API 608124011504 |
| 2018 | 1,924.7 | -2,408.0 | Well online (first production): API 608124011801<br>Drilling (spud): PS007<br>Workover: PS007 (608124011504)<br>Drilling (spud): PS008<br>Well online (first production): API 608124012200<br>Well online (first production): API 608124011606<br>Drilling (spud): PS006 |
| 2019 | 1,689.5 | -2,126.0 | Completion: PS003 (608124005600)<br>Drilling (spud): PS003<br>Well online (first production): API 608124012601<br>Drilling (spud): 001<br>Sidetrack: 001 (608124012800)<br>Sidetrack: 001 (608124012801)<br>Sidetrack: 001 (608124012802)<br>Sidetrack: 001 (608124012803)<br>Drilling (spud): PS009 |
| 2020 | 651.7 | -2,026.5 | Well online (first production): API 608124012500<br>Drilling (spud): PN005<br>Drilling (spud): IS003<br>Completion: PS003 (608124012601)<br>Drilling (spud): IS001 |
| 2021 | 1,675.7 | -1,796.6 | Well online (first production): API 608124013202<br>Workover: PS003 (608124005600)<br>Drilling (spud): PS006<br>Well online (first production): API 608124013600<br>Completion: PS009 (608124012804) |
| 2022 | 2,797.6 | -1,445.6 | Well online (first production): API 608124012804<br>Workover: PS003 (608124012601)<br>Completion: IS003 (608124013300)<br>Completion: IS001 (608124013500) |
| 2023 | 1,992.5 | -1,218.5 | Completion: PS008 (608124011606)<br>Drilling (spud): PS011<br>Well online (first production): API 608124014600<br>Drilling (spud): PS008 |
| 2024 | 1,994.1 | -1,011.7 | Well online (first production): API 608124015100<br>Workover: PN001 (608124005300)<br>Workover: PS008 (608124011606) |
| 2025 | 1,580.4 | -862.5 | Completion: PS012 (608124015504)<br>Well online (first production): API 608124015504<br>Well online (first production): API 608124015400 |
| 2026 | 658.9 | -804.5 |  |

### Critical Operations Detail

| Date | Operation | Well | Cumulative NPV at event ($MM) |
|------|-----------|------|------------------------------:|
| 2000-09-21 | Drilling (spud) | 001 | -8.0 |
| 2000-11-27 | Drilling (spud) | 001 | -50.7 |
| 2000-12-21 | Sidetrack | 001 (608124000400) | -74.9 |
| 2003-07-06 | Drilling (spud) | 002 | -94.7 |
| 2004-03-09 | Drilling (spud) | 001 | -151.8 |
| 2004-05-16 | Sidetrack | 001 (608124001300) | -192.6 |
| 2004-05-18 | Drilling (spud) | 001 | -192.6 |
| 2004-05-21 | Drilling (spud) | 001 | -192.6 |
| 2005-04-22 | Drilling (spud) | PS002 | -222.9 |
| 2006-02-12 | Completion | PS002 (608124001700) | -320.3 |
| 2006-08-01 | Well online (first production) | API 608124001700 | -405.7 |
| 2007-08-06 | Drilling (spud) | 002 | -419.8 |
| 2007-08-17 | Drilling (spud) | 001 | -419.8 |
| 2007-12-21 | Drilling (spud) | 003 | -473.7 |
| 2008-04-30 | Drilling (spud) | 002 | -535.5 |
| 2008-06-04 | Drilling (spud) | 002 | -577.4 |
| 2008-06-12 | Drilling (spud) | 002 | -577.4 |
| 2008-08-23 | Drilling (spud) | 003 | -616.7 |
| 2009-07-19 | Drilling (spud) | 001 | -649.4 |
| 2011-11-06 | Drilling (spud) | PS001 | -669.8 |
| 2011-11-13 | Drilling (spud) | PS005 | -669.8 |
| 2011-11-21 | Drilling (spud) | PN001 | -669.8 |
| 2011-11-22 | Drilling (spud) | PN002 | -669.8 |
| 2011-11-23 | Drilling (spud) | PN003 | -669.8 |
| 2011-11-26 | Drilling (spud) | PS003 | -669.8 |
| 2011-12-03 | Drilling (spud) | PS001 | -728.7 |
| 2011-12-05 | Drilling (spud) | PS004 | -728.7 |
| 2012-04-03 | Drilling (spud) | PS004 | -841.5 |
| 2012-05-17 | Drilling (spud) | PS004 | -853.6 |
| 2012-05-24 | Drilling (spud) | PS004 | -853.6 |
| 2012-05-27 | Sidetrack | PS004 (608124005102) | -853.6 |
| 2012-06-02 | Drilling (spud) | PS004 | -869.0 |
| 2012-08-01 | Well online (first production) | API 608124005600 | -885.7 |
| 2012-10-05 | Drilling (spud) | PS002 | -891.3 |
| 2013-01-01 | Well online (first production) | API 608124001701 | -944.4 |
| 2014-11-13 | Completion | PS001 (608124005700) | -1,402.8 |
| 2014-12-01 | Well online (first production) | API 608124005000 | -3,154.7 |
| 2014-12-01 | Well online (first production) | API 608124005300 | -3,154.7 |
| 2015-01-16 | Completion | PS005 (608124005000) | -3,157.4 |
| 2015-02-01 | Well online (first production) | API 608124005700 | -3,156.1 |
| 2015-02-22 | Workover | PS005 (608124005000) | -3,156.1 |
| 2015-07-01 | Well online (first production) | API 608124005103 | -3,104.6 |
| 2015-08-10 | Drilling (spud) | PS001 | -3,094.7 |
| 2015-10-29 | Drilling (spud) | PN007 | -3,072.1 |
| 2015-11-02 | Completion | PS001 (608124005201) | -3,066.6 |
| 2015-11-27 | Drilling (spud) | PN007 | -3,066.6 |
| 2016-02-14 | Completion | PS004 (608124005800) | -3,053.6 |
| 2016-04-01 | Well online (first production) | API 608124005800 | -3,045.6 |
| 2016-04-18 | Completion | PN002 (608124005400) | -3,045.6 |
| 2016-06-01 | Well online (first production) | API 608124005400 | -3,027.2 |
| 2016-06-08 | Completion | PN007 (608124010701) | -3,027.2 |
| 2016-08-01 | Well online (first production) | API 608124010701 | -3,002.3 |
| 2016-09-12 | Drilling (spud) | PS001 | -2,984.4 |
| 2016-10-30 | Drilling (spud) | PS001 | -2,962.2 |
| 2016-12-17 | Drilling (spud) | PS002 | -2,932.8 |
| 2017-01-01 | Well online (first production) | API 608124005203 | -2,922.0 |
| 2017-01-18 | Drilling (spud) | PS007 | -2,922.0 |
| 2017-01-26 | Drilling (spud) | PS008 | -2,922.0 |
| 2017-03-27 | Drilling (spud) | PS007 | -2,893.0 |
| 2017-04-05 | Drilling (spud) | PS007 | -2,876.1 |
| 2017-04-17 | Drilling (spud) | PS007 | -2,876.1 |
| 2017-04-23 | Drilling (spud) | PS007 | -2,876.1 |
| 2017-05-01 | Well online (first production) | API 608124011400 | -2,864.9 |
| 2017-05-16 | Drilling (spud) | PS005 | -2,864.9 |
| 2017-06-15 | Drilling (spud) | PS005 | -2,847.1 |
| 2017-09-06 | Completion | PS007 (608124011504) | -2,807.0 |
| 2017-11-01 | Well online (first production) | API 608124011504 | -2,781.7 |
| 2018-01-01 | Well online (first production) | API 608124011801 | -2,739.8 |
| 2018-01-05 | Drilling (spud) | PS007 | -2,739.8 |
| 2018-03-04 | Workover | PS007 (608124011504) | -2,688.2 |
| 2018-04-21 | Drilling (spud) | PS008 | -2,663.2 |
| 2018-04-27 | Drilling (spud) | PS008 | -2,663.2 |
| 2018-05-07 | Drilling (spud) | PS008 | -2,632.7 |
| 2018-05-20 | Drilling (spud) | PS008 | -2,632.7 |
| 2018-05-30 | Drilling (spud) | PS008 | -2,632.7 |
| 2018-06-01 | Well online (first production) | API 608124012200 | -2,606.1 |
| 2018-08-31 | Drilling (spud) | PS008 | -2,526.1 |
| 2018-12-01 | Well online (first production) | API 608124011606 | -2,408.0 |
| 2018-12-23 | Drilling (spud) | PS006 | -2,408.0 |
| 2019-02-15 | Completion | PS003 (608124005600) | -2,356.8 |
| 2019-03-26 | Drilling (spud) | PS003 | -2,328.6 |
| 2019-04-19 | Drilling (spud) | PS003 | -2,301.6 |
| 2019-08-01 | Well online (first production) | API 608124012601 | -2,220.5 |
| 2019-08-17 | Drilling (spud) | 001 | -2,220.5 |
| 2019-09-08 | Sidetrack | 001 (608124012800) | -2,194.4 |
| 2019-09-09 | Drilling (spud) | 001 | -2,194.4 |
| 2019-09-29 | Drilling (spud) | 001 | -2,194.4 |
| 2019-09-29 | Sidetrack | 001 (608124012801) | -2,194.4 |
| 2019-11-10 | Sidetrack | 001 (608124012802) | -2,149.6 |
| 2019-11-16 | Drilling (spud) | 001 | -2,149.6 |
| 2019-11-24 | Sidetrack | 001 (608124012803) | -2,149.6 |
| 2019-11-28 | Drilling (spud) | PS009 | -2,149.6 |
| 2020-05-01 | Well online (first production) | API 608124012500 | -2,080.4 |
| 2020-05-17 | Drilling (spud) | PN005 | -2,080.4 |
| 2020-06-19 | Drilling (spud) | PN005 | -2,069.2 |
| 2020-07-11 | Drilling (spud) | PN005 | -2,056.6 |
| 2020-08-14 | Drilling (spud) | IS003 | -2,052.0 |
| 2020-09-16 | Completion | PS003 (608124012601) | -2,047.1 |
| 2020-12-26 | Drilling (spud) | IS001 | -2,026.5 |
| 2021-02-01 | Well online (first production) | API 608124013202 | -2,002.9 |
| 2021-02-07 | Workover | PS003 (608124005600) | -2,002.9 |
| 2021-04-11 | Drilling (spud) | PS006 | -1,962.0 |
| 2021-08-01 | Well online (first production) | API 608124013600 | -1,886.0 |
| 2021-08-17 | Completion | PS009 (608124012804) | -1,886.0 |
| 2022-03-01 | Well online (first production) | API 608124012804 | -1,712.1 |
| 2022-03-07 | Workover | PS003 (608124012601) | -1,712.1 |
| 2022-09-07 | Completion | IS003 (608124013300) | -1,520.1 |
| 2022-12-30 | Completion | IS001 (608124013500) | -1,445.6 |
| 2023-03-15 | Completion | PS008 (608124011606) | -1,384.8 |
| 2023-04-21 | Drilling (spud) | PS011 | -1,364.9 |
| 2023-09-01 | Well online (first production) | API 608124014600 | -1,275.0 |
| 2023-10-14 | Drilling (spud) | PS008 | -1,254.0 |
| 2024-02-01 | Well online (first production) | API 608124015100 | -1,189.1 |
| 2024-07-09 | Workover | PN001 (608124005300) | -1,085.8 |
| 2024-10-10 | Workover | PS008 (608124011606) | -1,039.2 |
| 2025-04-13 | Completion | PS012 (608124015504) | -956.8 |
| 2025-06-01 | Well online (first production) | API 608124015504 | -932.6 |
| 2025-12-01 | Well online (first production) | API 608124015400 | -862.5 |

_Operations are derived deterministically from BSEE Well Activity Reports (`bin/war/`) and OGOR-A first-production dates (BSEE OGOR-A pickled .bin DataFrames (zip archives absent in checkout)). Activity codes: DRL=drilling, COM=completion, WO=workover, REC=recompletion, ST=sidetrack; re-entries detected via API completion-suffix changes on a shared wellbore. Markers are annotations only and do not feed the cashflow model._

---

## Well-Level NPV Stackup

Field terminal NPV decomposed into per-well contributions that sum exactly to the field total. Field NPV = **$-804.5 M**; sum of per-well net NPV = **$-804.5 M** (residual $-0.0000).

| Rank | Well (API) | Name | Oil (MMbbl) | Gross well NPV ($MM) | Allocated shared cost ($MM) | Net well NPV ($MM) | % of field NPV |
|-----:|-----------|------|------------:|---------------------:|----------------------------:|-------------------:|-----------:|
| 1 | 608124005600 | PS003 | 23.33 | 80.4 | -169.5 | -89.1 | 11.1% |
| 2 | 608124005000 | PS005 | 24.72 | 99.3 | -179.6 | -80.3 | 10.0% |
| 3 | 608124005700 | PS001 | 34.02 | 196.8 | -247.2 | -50.4 | 6.3% |
| 4 | 608124011504 | PS007 | 25.90 | 144.4 | -188.2 | -43.8 | 5.4% |
| 5 | 608124005103 | PS004 | 39.51 | 243.5 | -287.0 | -43.5 | 5.4% |
| 6 | 608124005300 | PN001 | 19.33 | 97.3 | -140.5 | -43.1 | 5.4% |
| 7 | 608124005800 | PS004 | 39.67 | 246.3 | -288.2 | -41.9 | 5.2% |
| 8 | 608124005400 | PN002 | 31.75 | 192.8 | -230.7 | -37.9 | 4.7% |
| 9 | 608124012500 | PS006 | 10.34 | 38.2 | -75.2 | -37.0 | 4.6% |
| 10 | 608124011801 | PS005 | 17.20 | 88.2 | -125.0 | -36.9 | 4.6% |
| 11 | 608124011400 | PS002 | 37.28 | 234.9 | -270.8 | -36.0 | 4.5% |
| 12 | 608124012200 | PS007 | 19.22 | 105.3 | -139.7 | -34.4 | 4.3% |
| 13 | 608124012601 | PS003 | 1.98 | -15.8 | -14.4 | -30.2 | 3.8% |
| 14 | 608124010701 | PN007 | 30.87 | 196.3 | -224.3 | -28.1 | 3.5% |
| 15 | 608124013202 | PN005 | 8.94 | 38.0 | -64.9 | -26.9 | 3.3% |
| 16 | 608124011606 | PS008 | 14.22 | 76.8 | -103.3 | -26.6 | 3.3% |
| 17 | 608124001701 | PS002 | 25.28 | 161.7 | -183.7 | -22.0 | 2.7% |
| 18 | 608124015100 | PS008 | 6.53 | 27.7 | -47.4 | -19.7 | 2.5% |
| 19 | 608124012804 | PS009 | 10.83 | 59.0 | -78.7 | -19.7 | 2.4% |
| 20 | 608124014600 | PS011 | 4.54 | 14.2 | -33.0 | -18.8 | 2.3% |
| 21 | 608124013600 | PS006 | 9.90 | 55.1 | -71.9 | -16.8 | 2.1% |
| 22 | 608124005203 | PS001 | 1.14 | -8.1 | -8.3 | -16.4 | 2.0% |
| 23 | 608124015504 | PS012 | 1.63 | 7.7 | -11.8 | -4.1 | 0.5% |
| 24 | 608124015400 | PS014 | 0.56 | 3.1 | -4.1 | -0.9 | 0.1% |

> **Reading the ranking.** Under production-pro-rata allocation, the largest producer absorbs the most shared capital — so the highest-output well can show the *most negative* net NPV. The **Gross well NPV** column reflects standalone operating performance; the **Net well NPV** column reflects each well's share of the fully-loaded field (which is NPV-negative overall, so every well's net is negative). **Bottom line:** a negative *net* NPV here is an allocation outcome on an NPV-negative field, not a verdict on the well's own performance — read the **Gross well NPV** column for standalone results.

Per-well net NPV (signed bars; █ = value-additive, ▓ = drag):

```
PS003       -89.1 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
PS005       -80.3 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
PS001       -50.4 M  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
PS007       -43.8 M  ▓▓▓▓▓▓▓▓▓▓▓▓
PS004       -43.5 M  ▓▓▓▓▓▓▓▓▓▓▓▓
PN001       -43.1 M  ▓▓▓▓▓▓▓▓▓▓▓▓
PS004       -41.9 M  ▓▓▓▓▓▓▓▓▓▓▓
PN002       -37.9 M  ▓▓▓▓▓▓▓▓▓▓
PS006       -37.0 M  ▓▓▓▓▓▓▓▓▓▓
PS005       -36.9 M  ▓▓▓▓▓▓▓▓▓▓
PS002       -36.0 M  ▓▓▓▓▓▓▓▓▓▓
PS007       -34.4 M  ▓▓▓▓▓▓▓▓▓
PS003       -30.2 M  ▓▓▓▓▓▓▓▓
PN007       -28.1 M  ▓▓▓▓▓▓▓▓
PN005       -26.9 M  ▓▓▓▓▓▓▓
PS008       -26.6 M  ▓▓▓▓▓▓▓
PS002       -22.0 M  ▓▓▓▓▓▓
PS008       -19.7 M  ▓▓▓▓▓
PS009       -19.7 M  ▓▓▓▓▓
PS011       -18.8 M  ▓▓▓▓▓
PS006       -16.8 M  ▓▓▓▓▓
PS001       -16.4 M  ▓▓▓▓
PS012        -4.1 M  ▓
PS014        -0.9 M  ▓
```

**[Interactive NPV waterfalls →](./jack_st_malo_npv_stackup.html)** — two views: an **over-time NPV bridge** (each year's change in cumulative NPV, with the biggest swings annotated by the events that drove them) and this **per-well stackup** (each well's net NPV stepping to the field total). Hover any bar for detail. Rebuild with `uv run --with plotly python scripts/lower_tertiary/build_npv_stackup_chart.py --dev "Jack St Malo"`.

**By block (OGOR `AREA_CODE_BLOCK_NUM`):**

| Block | Oil (MMbbl) | % of field oil |
|-------|------------:|---------------:|
| WR  678 | 221.31 | 50.4% |
| WR  758 | 138.92 | 31.7% |
| WR  634 | 30.87 | 7.0% |
| WR  677 | 25.86 | 5.9% |
| WR  759 | 10.90 | 2.5% |
| WR  802 | 10.83 | 2.5% |

_Block scope: 6 OGOR blocks present; per-block oil shares shown. Per-block NPV would require a block-level cost split (gap: shared facilities/D&C are field-level in V30, not block-tagged)._

_The stackup covers the 22 producing wells. The field's 73 total wellbores also include appraisal and sidetrack/re-drill bores; their drilling & completion capital is part of the shared cost allocated pro-rata (it is not attributed to a single producer)._

_**Allocation assumption.** Shared field costs (facilities, fixed opex, host) and the drilling/completion cost of non-producing bores (appraisal/sidetrack wells with no production to stand against) are pooled and allocated to the producing wells pro-rata by each well's share of total field oil production. Each producing well's own revenue, royalty, variable opex, and directly-resolvable D&C are attributed to it. Per-well NPVs sum to the field NPV._

---

## Well Geometry (3D)

Interactive 3D well-path views — minimum-curvature trajectories from BSEE directional surveys, rendered with Plotly and Three.js — are in development for this field. When verified they will live at:

- `reports/bsee/jack_st_malo_well_path_plotly.html`
- `reports/bsee/jack_st_malo_well_path_threejs.html`

_They are intentionally **not linked yet**: the geometry render must first be confirmed to cover the same lease-resolved producers shown in the NPV stackup above (same APIs, same field), so the economics and the well paths never describe different wells._

---

## Financial Summary

**Latest window (2000-09 -> 2026-04) vs frozen V30 reference.** D&C and facilities are one-time capital already incurred, so they are unchanged from V30; revenue, royalty and opex scale with the additional production.

| Metric | Latest | Frozen V30 (reference) |
|--------|------:|------:|
| **NPV @ 10%** | **$-804.5 M** | $-945.0 M |
| Revenue | $27,890.7 M | $25,648.5 M |
| Oil produced (MMbbl) | 438.7 | 406.6 |

_Latest NPV from `build_field_npv_timeline(dev, end_date)`; latest revenue/oil from `latest_baseline.yml` (regenerated through 2026-04). A full latest component breakdown (royalty/opex split) is not recomputed here — the frozen V30 breakdown below is the audited source-of-record._

### Frozen V30 reference (audited source-of-record)

| Metric | Value |
|--------|------:|
| Revenue | $25,655.0 M |
| Royalty | $4,810.3 M |
| Variable opex | $1,626.7 M |
| Fixed opex | $1,575.0 M |
| D&C cost | $5,450.4 M |
| Facilities cost | $7,400.0 M |
| Net cashflow (undiscounted) | $4,792.6 M |
| **NPV @ 10%** | **$-945.0 M** |
| MIRR (annual) | 8.43% |
| Producers | 22 |
| Injectors | 4 |
| Wellbores | 73 |

_Return metric: **MIRR** is the sanctioned return measure for these developments, not IRR. Deepwater Lower-Tertiary cashflows are heavily front-loaded (large D&C + facilities outflows, then a long production tail), so the net-cashflow sign changes more than once and the IRR polynomial can have multiple — or no — real roots; MIRR (single reinvestment/finance rate at the 10% discount rate) is well-defined and unambiguous. NPV @ 10% remains the primary value metric._

_Source-of-record: `config/analysis/lower_tertiary/golden_baseline_v30.yml`. NPV reproduced within golden-baseline tolerance by `worldenergydata.lower_tertiary.v30_financial_reproducer`._

---

## Price Sensitivity

NPV is linear in the oil price deck: each **+$1/bbl** on the realized oil price moves field NPV by **$+52.3 M**. Life-to-date NPV reaches **zero at a flat-equivalent realized WTI of $79/bbl**, versus the actual volume-weighted realized **$64/bbl** over the window.

| Flat-equivalent realized WTI ($/bbl) | NPV @ 10% ($MM) |
|-------------------------------------:|------------------:|
| 44 | -1,849.8 |
| 54 | -1,327.1 |
| 64  ← actual | -804.5 |
| 74 | -281.8 |
| 84 | 240.8 |

_Exact, not sampled: NPV is affine in a uniform price multiplier (revenue and royalty scale with price; variable/fixed opex, D&C, facilities and discounting do not), so one base run plus one scaled run define the entire line. 'Flat-equivalent realized WTI' is the volume-weighted average price; the underlying deck is the historical monthly WTI path._

---

## Next Steps

- **Get a tailored analysis.** Want this for your own assets — a different field, a custom price deck, sensitivities, or a partner-level working-interest view? **AceEngineer** builds traceable field economics from public data. Contact **vamsee.achanta@aceengineer.com** to scope an engagement.
- **Explore the full play.** Jack St Malo is one of **10 Lower Tertiary (Wilcox) fields** covered by this model. Regenerate any field with `--dev <Field>`, or ask for the **portfolio economics report** for the whole-play NPV view (Jack/St. Malo, Stones, Big Foot, Anchor, Cascade/Chinook, and more).
- **See the methodology.** Every number here traces to **public BSEE OGOR-A production + drilling/WAR records** run through the sanctioned V30 cashflow model — no black box. The pipeline (BSEE public data → parsed `.bin` → V30 NPV) is reproducible end-to-end and reconciles to the frozen golden baseline.
- **Run it yourself.** Refresh the data and regenerate this report:

  ```bash
  # 1. refresh the latest BSEE OGOR-A production (2025 + current year)
  uv run python scripts/refresh_bsee_ogor_recent.py
  # 2. regenerate this report (latest window is the default;
  #    leases are auto-derived for the field)
  uv run python scripts/lower_tertiary/generate_field_economics_report.py --dev "Jack St Malo"
  # frozen V30 reference report: add --frozen
  ```
