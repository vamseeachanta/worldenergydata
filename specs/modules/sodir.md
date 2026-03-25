# Module: sodir

## Purpose
Provides integration with the Norwegian Offshore Directorate (SODIR, formerly
NPD) REST API to collect and analyse Norwegian Continental Shelf petroleum data
including wellbores, fields, discoveries, facilities, blocks, and seismic
surveys; supports cross-regional comparison with BSEE GOM data.

## Key Classes / Functions
- `Sodir` (`sodir.py`): Top-level router class following the BSEE module
  pattern; dispatches collection and analysis tasks from a configuration dict;
  entry point for all SODIR operations
- `ApiClient` (`api_client.py`): Rate-limited HTTP client for
  `factmaps.sodir.no` REST endpoints; handles pagination, caching, and
  exponential backoff retry
- `Datasets` (`datasets.py`): Catalogue of available SODIR dataset IDs and
  field name mappings; central registry for endpoint routing
- `Endpoints` (`endpoints.py`): Typed enum of all supported SODIR REST
  endpoint paths (wellbores, fields, discoveries, surveys, installations)
- `DataNormaliser` (`data.py`): Converts SODIR Norwegian units and
  naming conventions to WorldEnergyData standard schema
- `SodirProcessors` (`processors/`): Per-dataset post-processing pipelines
  (wellbore lithology parsing, field production aggregation)
- `SodirProduction` (`production/`): Monthly and annual field production
  aggregation; liquid/gas split; NCS total production tracking
- `CrossRegional` (`cross_regional.py`): Side-by-side comparison of NCS
  and GOM data sets (requires `worldenergydata.bsee`)
- `NpvNorway` (`npv_norway.py`): Norwegian fiscal regime NPV model
  incorporating petroleum tax (78% marginal rate), uplift deductions, and
  CO2 tax
- `CacheOptimiser` (`cache_optimizer.py`): Prioritises local cache vs API
  fetch based on dataset age and bandwidth budget
- `Forecasting` (`forecasting.py`): Field-level production decline and
  plateau extension forecasting for NCS assets
- `Validators` (`validators.py`): Schema validation for SODIR response objects
- `Visualization` (`visualization.py`): Plotly-based HTML charts for NCS
  production, discovery timelines, and field maps

## Data Sources
- SODIR FactMaps REST API: https://factmaps.sodir.no/factmaps/10_0/;
  public; JSON; updated daily for wellbores and weekly for production
- SODIR bulk downloads: https://sodir.no/en/facts/; Excel/CSV; static
- Norwegian Petroleum Directorate open data portal: background reference

## Integration Points
- **Depends on**: `worldenergydata.common` (unit conversion, date helpers),
  `worldenergydata.economics` (fiscal regime base classes)
- **Used by**: `worldenergydata.analysis` (global cross-jurisdiction
  comparisons), `worldenergydata.reporting` (NCS portfolio dashboards),
  `worldenergydata.cross_regional` (NCS vs GOM benchmarking via bsee)

## Status
Active — API client, data normalisation, production aggregation, and NPV
model implemented; forecasting and cross-regional modules partially implemented
