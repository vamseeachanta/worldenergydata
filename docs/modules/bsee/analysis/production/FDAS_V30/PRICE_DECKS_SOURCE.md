# Price decks — provenance

Monthly price decks used by the BSEE field-economics atlas. Both are official
U.S. EIA series, retrieved as machine-readable CSV from FRED (Federal Reserve
Bank of St. Louis), which republishes the EIA series verbatim.

| File | Series | EIA name | FRED id | Coverage |
|------|--------|----------|---------|----------|
| `wti_monthly.xlsx` | WTI crude spot | Cushing, OK WTI Spot Price FOB ($/bbl) | `MCOILWTICO` | 1986-01 → 2026-05 |
| `henry_hub_monthly.xlsx` | Henry Hub gas spot | Henry Hub Natural Gas Spot Price ($/MMBtu) | `MHHNGSP` | 1997-01 → 2026-05 |

Verification: the WTI series matches the prior committed deck on all 475
overlapping months (1986-01 → 2025-07) with zero mismatches; this refresh only
extends it (2025-08 → 2026-05). Retrieved 2026-06-22.

Source: https://fred.stlouisfed.org/series/MCOILWTICO ,
        https://fred.stlouisfed.org/series/MHHNGSP (underlying: EIA).
