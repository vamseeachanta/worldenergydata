# Julia Field — BSEE End-to-End Economics (by well / block / field)

**Date:** 2026-06-17 · **Field:** Julia (GoM, Walker Ridge 584, Lower Tertiary subsea tieback)
**Operator:** Equinor 50% / ExxonMobil 50% · **Lease:** G20351 · **First oil:** Mar 2016 · **Dev system:** tieback15

## What this is
The marketing demo no longer uses a toy cashflow. It now consumes the **full BSEE workflow**:
real OGOR-A monthly production (local `ogora*delimit` pickles, 1996–2025) → WTI historical price deck →
royalty / OPEX / D&C / facilities (FDAS V30 `tieback15` assumptions) → NPV / MIRR / payback, queryable
**by well, by block, and by field**, for two data vintages.

## Validation (both baselines)
Reproduced from local `.bin` data using the **sanctioned** `reproduce_v30_financials()` engine:

| Metric | Reproduced | Golden baseline (V30) | Δ |
|---|---|---|---|
| Oil | 70.94 MMbbl | 70.94 MMbbl | 0.00% |
| Revenue | $4,715.1M | $4,715.2M | −0.001% |
| D&C | $1,349.6M | $1,349.6M | exact |
| Facilities | $1,375.0M | $1,375.0M | exact |
| **NPV@10%** | **−$530.64M** | **−$530.64M** | **+0.001%** |
| MIRR | 6.31% | 6.31% | match |

Latest OGOR cross-check (through Nov 2025): **74.62 MMbbl / $4,946M** vs published latest baseline
**74.03 MMbbl / $4,917M** — consistent. Whole 11-field portfolio reproduced to ~0.001%.

## Field result (V30, validated)
- Oil 70.94 MMbbl · Gas ~ per OGOR · Revenue **$4,715M** · CAPEX **$2,724.6M** (D&C $1,349.6M + facilities $1,375M)
- **NPV@10% = −$531M** · **MIRR 6.31%** · lifetime net op cashflow −$13M
- **Honest result: Julia is full-cycle NPV-negative** — ~$2.72B CAPEX outweighs discounted net operating
  cashflow at historical prices. The demo's value is the *traceable, reproducible* public-data pipeline.

## By well (exact production/revenue; indicative full-cycle NPV)
| Well | Oil (MMbbl) | Revenue | Net Op CF | CAPEX (alloc) | NPV@10% (≈) | MIRR |
|---|---|---|---|---|---|---|
| JU104 | 28.08 | $1,913M | $1,163M | $877M | −$136M | 7.9% |
| JU106 | 17.04 | $1,200M | $776M | $592M | −$68M | 8.2% |
| DC101 | 14.08 | $863M | $482M | $664M | −$290M | 3.1% |
| JU102 | 11.74 | $740M | $417M | $590M | −$289M | 2.0% |

**Insight:** the two later high-rate wells (JU104, JU106) are individually value-accretive (~8% MIRR) and
carry the development; the early appraisal wells (DC101, JU102) do not.

## By block
Julia produces entirely from a single block (**WR 584**), so by-block == by-field here. The capability
matters for multi-block/multi-lease fields (e.g. Jack/St. Malo spans 6 leases).

## Vintages
- **V30** — OGOR+WTI through 2025-05 (golden-baseline window; field/block figures authoritative).
- **Latest** — through last available OGOR month (~Nov 2025); +3.7 MMbbl, +$231M revenue → NPV improves to ≈ −$486M.

## Artifacts (in /tmp/jwork)
- `julia_report.html` — interactive report with By Field/Block/Well + V30/Latest toggles
- `julia_granular.py` — granular economics engine (reads local OGOR `.bin`, emits JSON)
- `julia_repro.py` — validation harness (monkeypatches sanctioned engine to read local `.bin`)
- `julia_granular_out.json` — full per-unit results

## Notes / caveats
- Local OGOR `.bin` already current through 2025; `refresh_bsee_all.py` confirmed bins are real (refresh = no-op).
- The sanctioned reproducers read OGOR `.zip` (absent locally); bridged by reading the present `.bin` pickles
  (identical column order), validated to ~0.001%.
- Per-well NPV (≈) allocates shared CAPEX + fixed OPEX by production share — indicative, not a re-derivation of
  the field NPV (per-unit discounting is non-linear).
