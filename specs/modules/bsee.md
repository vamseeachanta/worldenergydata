# Module: bsee

## Purpose
Provides comprehensive access to BSEE (Bureau of Safety and Environmental
Enforcement) data for US Gulf of Mexico offshore operations, covering well and
production data retrieval by API10/API12 number, OCS block, or lease; financial
analysis; production forecasting; and multi-format reporting.

## Key Classes / Functions
- `BSEEData` (`bsee.py`): Top-level data access facade; dispatches to API-,
  block-, and lease-based loaders and returns normalised DataFrames
- `BSEEAnalysis` (`analysis/`): Production decline, well performance scoring,
  and cross-field benchmarking
- `WellAPI10` (`analysis/well_api10.py`): Single-well production and status
  queries keyed by 10-digit API well number
- `WellAPI12` (`analysis/well_api12.py`): Completion-level queries keyed by
  12-digit API number (adds sidetrack/perforation suffix)
- `ProductionAPI10` / `ProductionAPI12` (`analysis/`): Monthly production
  time series retrieval and aggregation at well and completion level
- `FinancialAnalysis` (`analysis/financial/`): NPV, IRR, and cash-flow
  modelling for individual wells and field portfolios
- `Forecasting` (`analysis/forecasting/`): Hyperbolic and exponential decline
  curve fitting (Arps); probabilistic P10/P50/P90 production forecasts
- `WellDataVerification` (`analysis/well_data_verification/`): Cross-checks
  reported production against proration and allocation data; flags anomalies
- `WellRigDays` (`analysis/well_rig_days.py`): Rig utilisation and spud-to-TD
  duration metrics from BSEE well activity records
- `PipelineRunner` (`pipeline/pipeline_runner.py`): Orchestrates bulk data
  download, parsing, and storage update cycles
- `FieldQuery` / `FieldReport` (`pipeline/`): Generates structured field-level
  summaries and HTML/Excel/PDF reports
- `BSEEComponents` (`components/bseedata.py`): Low-level binary `.bin` file
  parser and ZIP archive extractor for raw BSEE downloads

## Data Sources
- BSEE Production Data: https://www.bsee.gov/data-statistics (ZIP/binary);
  monthly update; ~300 MB binary files (not in git, run `make data`)
- BSEE Well Data: same portal; API10/API12 well header CSV
- OCS Block map: BOEM GIS shapefiles; quarterly update
- Paleontological well data (`paleowells/`): BSEE paleo horizon picks; static

## Integration Points
- **Depends on**: `worldenergydata.common` (unit conversion, date helpers),
  `worldenergydata.economics` (fiscal regime models)
- **Used by**: `worldenergydata.analysis` (cross-jurisdiction comparisons),
  `worldenergydata.lower_tertiary` (deepwater play analysis),
  `worldenergydata.reporting` (portfolio dashboards)

## Status
Active — core data access and analysis implemented; financial sub-package
partially implemented; paleowells module planned
