# Metocean reference data and external licensed tables

The module documents structures for external licensed tables.
The repository attributes these tables to API RP 2MET-derived workbooks.
Their tabulated values are not distributed with the repository.

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

Citation for each external table: API RP 2MET, Derivation of Metocean Design and Operating Conditions; edition and table titles: to be completed from the licensed copy

The following descriptions are repository section titles, not verified titles
of tables in the publication.

- `api_rp2met_hurricane_gom_extremes.csv` — not distributed; Hurricane extremes by return period.
- `api_rp2met_us_zone_100yr_waves.csv` — not distributed; Extreme waves, currents and storm tide by offshore zone.
- `api_rp2met_gom_extremes_by_region.csv` — not distributed; GoM hurricane extremes by sub-region and return period (long-form).
- `api_rp2met_us_zone_100yr_winds.csv` — not distributed; 100-year extreme 10m/60-min wind speeds by US offshore zone (wind companion to the US-zone waves table).

- `marine_growth_terminal_thickness.csv` — not distributed; Terminal marine-growth thickness by depth band.
- `metocean_regional_extremes.csv` — not distributed; Regional metocean extremes by parameter and return period.
- `metocean_hs_tp_occurrence.csv` — not distributed; Joint wave-height and peak-period occurrence.
- `metocean_temperature_ranges.csv` — not distributed; Air and sea temperature ranges by area.
