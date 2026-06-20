# Seasonal Intervention Risk Windows — Hurricane Season × WAR × Operations

*Issue #427 · child of #423 · sibling of #403 / #416 · data as of 2026-06-19 · aggregate-only · **descriptive only (small N, no significance test)***

## TL;DR

- **177 WAR-derived operation records** carry a parseable activity start date across the local BSEE sample CSVs.

- **71 (40%)** fall inside the Atlantic hurricane season (Jun 1 - Nov 30); **25 (14%)** fall in the climatological peak (Aug - Oct).

- **106 (60%)** fall in the lower-storm-risk off-season (Dec–May) — the window where weather-driven deferral and evacuation risk is lowest.

- **Lowest-storm-risk months with observed activity (data):** Mar (26), Dec (23), Jan (21).

## Data vs assumptions — hard separation

| Element | Type | Source |
|---|---|---|
| Monthly/seasonal activity counts | **DATA** | local BSEE WAR CSVs (below) |
| Activity-type split | **DATA** | `WELL_ACTIVITY_CD` in the same CSVs |
| Hurricane-season window (Jun–Nov) & peak (Aug–Oct) | **ASSUMPTION (public)** | NOAA/NHC climatology |

> **No HSE-incident-by-season cut** is included: the assembled `data/modules/hse/hse_incidents.db` is a **0-byte stub** and no raw BSEE INCINV file (`mv_acc_investigations.txt`) is present locally. The acceptance criterion asking for a statistically-sane (#416 Bonferroni p<0.0125) HSE-rate recommendation **cannot be met from local data**; this memo therefore reports the WAR operations-timing cut only, descriptively. (See #426 scope-down note.)

## Local data sources (DATA)

| Source | Path | Rows | Parseable dates |
|---|---|---:|---:|
| `well_activity_summary` | `data/modules/bsee/current/operations/well_activity_summary.csv` | 100 | 100 |
| `war_detail_608124003301` | `docs/modules/bsee/analysis/rig_days/war_data_608124003301.csv` | 32 | 32 |
| `war_detail_608124009500` | `docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv` | 45 | 45 |

## Monthly distribution overlaid on hurricane season (DATA + overlay)

| Month | Records | Share | Hurricane season | Peak |
|---|---:|---:|:--:|:--:|
| Jan | 21 | 12% | — |  |
| Feb | 13 | 7% | — |  |
| Mar | 26 | 15% | — |  |
| Apr | 10 | 6% | — |  |
| May | 13 | 7% | — |  |
| Jun | 23 | 13% | 🌀 yes |  |
| Jul | 10 | 6% | 🌀 yes |  |
| Aug | 6 | 3% | 🌀 yes | ● peak |
| Sep | 10 | 6% | 🌀 yes | ● peak |
| Oct | 9 | 5% | 🌀 yes | ● peak |
| Nov | 13 | 7% | 🌀 yes |  |
| Dec | 23 | 13% | — |  |
| **Total** | **177** | | | |

## Seasonal roll-up (DATA)

| Meteorological season | Records | Share |
|---|---:|---:|
| Winter | 57 | 32% |
| Spring | 49 | 28% |
| Summer | 39 | 22% |
| Fall | 32 | 18% |

## Activity-type mix inside vs outside hurricane season (DATA)

| Activity | Meaning | In season | Off season | Total |
|---|---|---:|---:|---:|
| `COM` | Completion | 21 | 33 | 54 |
| `DRL` | Drilling | 28 | 22 | 50 |
| `PA` | Plug & abandon (P&A) | 11 | 10 | 21 |
| `TA` | Temporary abandonment | 2 | 16 | 18 |
| `PND` | Pending / sidetrack-bypass | 0 | 12 | 12 |
| `CHZ` |  | 8 | 3 | 11 |
| `WO` | Workover | 0 | 6 | 6 |
| `REC` |  | 1 | 2 | 3 |
| `(blank)` |  | 0 | 1 | 1 |
| `ST` | Sidetrack | 0 | 1 | 1 |

## Lower-risk operating windows (read-through)

- The Atlantic hurricane season (Jun 1 - Nov 30; source: NOAA National Hurricane Center — official Atlantic hurricane season (Jun 1-Nov 30) and climatological peak (mid-Aug to mid-Oct). Public knowledge.) concentrates storm-evacuation, weather-deferral, and crew-fatigue overlap risk in Jun–Nov, peaking Aug - Oct.

- **Off-season (Dec–May)** carried **106 of 177 (60%)** observed operation starts in this sample — the descriptively lower-storm-risk scheduling window.

- **Operational decision support:** where intervention scope is schedulable, front-loading discretionary work into the Dec–May off-season (and avoiding the Aug–Oct peak) reduces exposure to storm-driven deferral. This is a **directional, descriptive** recommendation — the local sample is too small (N≈177) to attach a quantified HSE-rate delta or a significance test.

## Caveats

- **Small N / sample extracts.** The local BSEE operations CSVs are truncated samples, not the full census; counts are illustrative of method, not a population estimate.

- **WAR_START_DT = reporting-period start**, a close proxy for when the operation was active that week; it is not a precise incident timestamp.

- **No HSE incident data** locally (0-byte db stub; no raw INCINV) — the incident-rate-by-season half of #427's scope is deferred to when INCINV lands.

- **No metocean current/wave overlay** included; that requires the #403 metocean datasets, out of scope for this local-only pass.

## Cross-links

- #403 — hurricane-mooring infrastructure (metocean/storm window source).

- #416 — Phase-1A WAR loaders + INCINV classification (loader reuse target).

- #423 — marketing-pipeline umbrella (parent).

## Reproduce

```
PYTHONPATH=src python3 reports/gtm/seasonal_intervention_risk_windows.py
```
Deterministic: emits the `.json` sidecar (all figures), this `.md`, and the `.html`. Every number above is in the JSON.

*Generated 2026-06-20T04:19:08Z · data as of 2026-06-19 · aggregate-only.*
