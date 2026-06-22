# Metocean — API-RP-2MET Extremes & Marine Growth Reference

Public-safe metocean reference tables converted from legacy API-RP-2MET-derived
engineering workbooks (read with openpyxl). All values are indicative reference
data re-expressed in clean tables.

Corpus epic llm-wiki#767; worldenergydata issue #543 (Part B).

## Tables (`curated/`)

### `api_rp2met_hurricane_gom_extremes.csv` — 16 rows
Hurricane wind / wave / current / water-level extremes for the deep-water Gulf
of Mexico, by return period (10, 25, 50, 100, 200, 1000, 2000 years).

| Column | Notes |
|---|---|
| PARAMETER | metocean parameter incl. units (e.g. `Significant wave height (m)`) |
| RP_10YR … RP_2000YR | value at each return period |

### `api_rp2met_us_zone_100yr_waves.csv` — 15 rows
Nominal 100-year extreme wave heights and associated current / storm-tide by US
offshore zone (Washington/Oregon, Gulf of Alaska, Cook Inlet, Aleutian/Bering
shelf basins, Chukchi/Beaufort seas, US Atlantic embayments).

Columns: ZONE, LOCATION, HMAX_100YR_MEAN_M, HMAX_100YR_RANGE_M,
WAVE_STEEPNESS_RANGE, CURRENT_MEAN_MS, CURRENT_RANGE_MS, STORM_TIDE_MEAN_M,
STORM_TIDE_RANGE_M, BASIS.

### `marine_growth_terminal_thickness.csv` — 3 rows
Terminal thickness of marine growth (hard / soft / algae-kelp) by depth band
(0–15 m, 15–30 m, 30 m–sea floor). Thickness values carry their `m` unit
verbatim from the source.

## Notes

- The source workbooks were multi-table "poster" layouts. Only the
  cleanly-structured, unambiguous tables were extracted; blocks that mixed
  several locations without a per-row location key were **not** carried over to
  avoid stripping context from facts.
- Relationship to the live `metocean-data-fetcher` / `metocean-statistics`
  skills: these are static **design-criteria reference** tables (standards-style
  indicative extremes), complementing real-time/observed metocean feeds.
