# Module: eia_us

## Purpose
Provides US domestic energy production analytics using EIA data sources,
covering state-level crude and NGL production, DPR basin drilling productivity,
Alaska field-level breakdowns, shale decline curve modelling, and US federal
and state fiscal regime calculations.

## Key Classes / Functions
- `StateProduction` (`production/`): Retrieves and aggregates monthly crude
  and NGL production by US state from EIA-914 and state-level series; outputs
  normalised DataFrames with BOE conversion
- `DPRBasinAnalysis` (`analysis/`): Drilling Productivity Report basin models
  for Permian, Bakken, Eagle Ford, Niobrara, Haynesville, Marcellus, and
  Utica; computes new-well IP and legacy decline per basin per month
- `AlaskaBreakdown` (`production/`): Field-level Alaska production for Prudhoe
  Bay, Kuparuk, Point Thomson, and satellite fields with state proration data
- `HyperbolicDecline` (`analysis/`): Arps hyperbolic decline (b > 1) with
  terminal exponential switch; fits EUR, IP, and b-factor from production history
- `FiscalRegimeModel` (`analysis/`): Federal BLM onshore royalty (12.5%/16.67%),
  Texas RRC severance tax, and North Dakota Bakken incentive programme models
  for net revenue and breakeven price calculation
- `InternationalReference` (`international/`): EIA INTL series country-level
  production data for non-US benchmarking and cross-regional comparisons
- `EIAClient` (`client/`): Thin HTTP wrapper around the EIA API v2
  (`api.eia.gov/v2/`) for on-demand series retrieval with incremental JSONL
  output and state-file tracking; distinct from the live `worldenergydata.eia`
  feed module

## Data Sources
- EIA API v2: https://api.eia.gov/v2/; real-time; requires EIA_API_KEY env var
- EIA-914 Monthly Production Report: CSV downloads; monthly release
- EIA Drilling Productivity Report (DPR): Excel workbooks; monthly release
- EIA INTL series: API series; updated quarterly
- Alaska Oil and Gas Conservation Commission (AOGCC): field-level CSV; monthly

## Integration Points
- **Depends on**: `worldenergydata.common` (unit conversion, date helpers),
  `worldenergydata.economics` (breakeven modelling)
- **Related**: `worldenergydata.eia` (live API feed module for weekly petroleum
  and gas data — use that module for ingestion; eia_us is for analytics)
- **Used by**: `worldenergydata.analysis` (cross-jurisdiction production
  comparisons), `worldenergydata.reporting` (US market dashboards),
  `worldenergydata.dashboard` (interactive production visualisations)

## Status
Active — analysis, client, production, and international sub-packages
implemented and tested
