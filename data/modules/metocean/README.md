# Metocean reference data and external licensed tables

The module documents table structures and retained legacy reference datasets.
API-RP-2MET tabulated values are not distributed with the repository.
The source-table origin of the retained legacy datasets is not established;
their presence does not establish source rights or engineering suitability.

## External licensed tables

These tables are **not distributed**. Their schema entries retain column names,
types and units, with no bundled path or values. Supply an authorized CSV copy
outside the repository using
`worldenergydata.metocean.licensed_tables.load_licensed_table(name, copy_path=...)`.
Alternatively, set `METOCEAN_LICENSED_DATA_DIR` to an external directory holding
the expected filename. An explicit `copy_path` takes precedence. The loader
requires the metocean source checkout to establish the repository boundary;
installed copies without that boundary fail plainly. Paths inside the
repository, including symlinks into it, are refused. Columns must match the
schema exactly, including order; returned cells remain strings.

Citation for each external table: API-RP-2MET; document title: not stated in the repository; edition: not stated in the repository; clause or publication table title: not stated in the repository.

The following descriptions are repository section titles, not verified titles
of tables in the publication.

- `api_rp2met_hurricane_gom_extremes.csv` — not distributed; Hurricane extremes by return period.
- `api_rp2met_us_zone_100yr_waves.csv` — not distributed; Extreme waves, currents and storm tide by offshore zone.
- `api_rp2met_gom_extremes_by_region.csv` — not distributed; GoM hurricane extremes by sub-region and return period (long-form).
- `api_rp2met_us_zone_100yr_winds.csv` — not distributed; 100-year extreme 10m/60-min wind speeds by US offshore zone (wind companion to the US-zone waves table).

## Retained legacy tables (`curated/`)

### `marine_growth_terminal_thickness.csv` — 3 rows
Terminal thickness of marine growth (hard / soft / algae-kelp) by depth band
(0–15 m, 15–30 m, 30 m–sea floor). Thickness values carry their `m` unit
verbatim from the source.

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
