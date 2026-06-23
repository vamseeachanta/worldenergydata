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

### `api_rp2met_gom_extremes_by_region.csv` — 116 rows
Deep-water Gulf of Mexico hurricane extremes (wind / wave / current / water
level) by **sub-region** and return period — the regional breakdown
(Central / Western / Eastern GoM, All Regions North of 28° N) plus the
early-season / late-season seasonal blocks, complementing the single-region
`api_rp2met_hurricane_gom_extremes.csv`. Long-form.

Columns: PARAMETER, UNIT, REGION, RP_10YR … RP_2000YR.

### `metocean_regional_extremes.csv` — 82 rows
Indicative extreme metocean parameters (wind / wave / current / storm surge) by
return period (1, 5, 10, 50, 100 yr) for non-GoM regions: West Africa
(Nigeria shallow & deep, northern Angola, southern Namibia), the North Sea /
NE Atlantic / Norwegian Sea (Celtic Sea, Southern/Central/Northern North Sea,
West of Shetland, Haltenbank, Barents Sea) and the NW Atlantic (off Newfoundland,
off Nova Scotia / Sable Island Bank). Long-form, one row per region × parameter.

Columns: REGION, NOMINAL_WATER_DEPTH, PARAMETER, UNIT, RP_1YR … RP_100YR.

### `metocean_hs_tp_occurrence.csv` — 226 rows
Joint percentage-occurrence scatter of significant wave height (Hs) versus
spectral peak period (Tp) for three deep-water locations (Gulf of Mexico,
offshore Nigeria, offshore Angola). Long-form; zero-occurrence cells dropped.

Columns: LOCATION, HS_BAND_M, TP_BAND_S, OCCURRENCE_PCT.

### `metocean_temperature_ranges.csv` — 7 rows
Air / sea-surface / sea-floor temperature ranges (°C) for North Sea,
eastern North Atlantic and Norwegian Sea areas.

Columns: AREA, AIR_TEMP_C, SEA_TEMP_C, SEAFLOOR_TEMP_C.

### `api_rp2met_us_zone_100yr_winds.csv` — 15 rows
100-year extreme 10 m / 60-min wind speeds (with-wave and maximum) by US offshore
zone — the wind companion to `api_rp2met_us_zone_100yr_waves.csv`.

Columns: ZONE, LOCATION, WIND_10M_60MIN_WITH_WAVE_MS, WIND_10M_60MIN_MAX_MS.

## Notes

- The source workbooks were multi-table "poster" layouts. Only the
  cleanly-structured, unambiguous tables were extracted; blocks that mixed
  several locations without a per-row location key were **not** carried over to
  avoid stripping context from facts.
- Relationship to the live `metocean-data-fetcher` / `metocean-statistics`
  skills: these are static **design-criteria reference** tables (standards-style
  indicative extremes), complementing real-time/observed metocean feeds.
