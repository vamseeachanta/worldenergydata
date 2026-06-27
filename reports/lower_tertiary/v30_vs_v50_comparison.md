# Lower Tertiary Gold Standard: V30 → V50 Comparison

- **V30 window:** 2000-09 through 2025-05 (frozen gold standard — `golden_baseline_v30.yml`)
- **V50 window:** 2000-09 through 2026-04 (new gold standard — `golden_baseline_v50.yml`)
- **Methodology:** reproduce_v30_financials (identical to V30; data window extended)
- **Generated:** 2026-06-26
- **Source:** new BSEE OGOR-A `.bin` (latest) re-run of Roy Shilling's rerun-with-latest-ogora request; same lease mapping, cost assumptions, royalty/opex rates, and 10%/yr discounting as V30.

> **Reproduction gate (before update):** V30 reproduces from raw OGOR within
> ±0.1% on production and ±1% on NPV for all matched projects; Jack St Malo
> NPV sits in its known ~7.3% band (monthly D&C allocation timing). Because
> V50 changes *only* the data window, V30→V50 deltas isolate the new data.

## Producing fields

| Field | Oil V30 (MMbbl) | Oil V50 (MMbbl) | ΔOil % | Rev V30 ($MM) | Rev V50 ($MM) | ΔRev % | NPV V30 ($MM) | NPV V50 ($MM) | ΔNPV ($MM) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Jack St Malo ⚠️ | 406.6 | 438.7 | +7.9 | 25,648.5 | 27,890.7 | +8.7 | -881.1 | -804.5 | +76.6 |
| Stones | 83.7 | 89.0 | +6.4 | 5,582.4 | 5,946.6 | +6.5 | -1,479.5 | -1,460.8 | +18.7 |
| Julia | 70.9 | 77.5 | +9.2 | 4,715.2 | 5,168.4 | +9.6 | -530.6 | -482.8 | +47.8 |
| Big Foot | 66.9 | 78.7 | +17.8 | 4,737.8 | 5,570.8 | +17.6 | -1,063.4 | -989.0 | +74.4 |
| Cascade Chinook † | 34.3 | 39.7 | +15.5 | 2,326.9 | 2,778.0 | +19.4 | -1,474.1 | -1,580.0 | -106.0 |
| Anchor | 6.9 | 18.6 | +168.5 | 476.3 | 1,279.2 | +168.6 | -1,732.8 | -1,586.9 | +145.9 |
| Shenandoah | 0.0 | 21.2 | +559,532.9 | 0.3 | 1,459.7 | +539,179.4 | -1,166.4 | -991.3 | +175.1 |
| **Total** | **669.3** | **763.3** | **+14.1** | **43,487.3** | **50,093.5** | **+15.2** | **-8,327.8** | **-7,895.3** | **+432.5** |

⚠️ = Jack St Malo NPV carries the known ~7.3% reproducer-vs-frozen offset (monthly D&C allocation timing); its oil/revenue deltas are data-clean.

† = Cascade Chinook V50 adopts the verified first-oil correction (2014-01-01 → 2012-09-01, confirmed against raw OGOR); V30 stays frozen at 2014-01-01. Its delta therefore includes this one fix plus new data.

## Exploration-only (D&C, no production)

| Field | NPV V30 ($MM) | NPV V50 ($MM) | ΔNPV ($MM) |
|---|--:|--:|--:|
| North Platte | -783.5 | -783.5 | +0.0 |
| Kaskida | -625.0 | -625.0 | +0.0 |
| Tiber | -228.0 | -228.0 | +0.0 |

## Notes

- V50 extends every producer's window by 11 months (2025-05 → 2026-04), so
  oil and revenue rise across the board. The largest jumps are the late
  starters — Shenandoah and Anchor — which had almost no production captured
  in V30.
- NPV improvements reflect the added producing months net of continued opex;
  no field crosses into positive NPV.
- Frozen V30 (`golden_baseline_v30.yml`) is unchanged. V50 lives alongside it.

