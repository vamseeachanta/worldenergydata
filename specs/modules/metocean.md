# Module: metocean

## Purpose
Provides retrieval, storage, and analysis of meteorological and oceanographic
data from public APIs including NOAA NDBC buoys, CO-OPS tides and currents,
Open-Meteo weather forecasts, ERDDAP servers, and the Norwegian Meteorological
Institute, with offline caching and CLI access.

## Key Classes / Functions
- `NDBCClient` (`clients/ndbc_client.py`): HTTP client for NOAA NDBC
  standard meteorological data; fetches historical and real-time observations
  with parquet caching; wraps `NDBCStation` and `NDBCObservation` models
- `NDBCStation` / `NDBCObservation`: Dataclasses for station metadata and
  individual observation records (Hs, Tp, wind speed/direction, air/water temp)
- `COOPSClient` (`clients/coops_client.py`): NOAA CO-OPS API client for tide
  predictions, water levels, and current observations
- `COOPSStation`, `COOPSTidePrediction`, `COOPSWaterLevel`, `COOPSCurrent`:
  Typed data models for CO-OPS response objects
- `OpenMeteoClient` (`clients/open_meteo_client.py`): Open-Meteo forecast API
  client; retrieves hourly weather grids; wraps `OpenMeteoForecast`
- `ERDDAPClient` (`clients/erddap_client.py`): Generic ERDDAP dataset client
  for gridded oceanographic and atmospheric products
- `MetNorwayClient` (`clients/met_norway_client.py`): Norwegian Meteorological
  Institute Frost API client for offshore met station data
- `build_scatter_matrix()` (`ndbc_analysis.py`): Constructs Hs/Tp joint
  probability scatter matrix from observation records; supports normalisation
- `filter_by_season()` (`ndbc_analysis.py`): Filters DataFrame by calendar
  month list for seasonal statistics
- `fit_weibull_hs()` (`ndbc_analysis.py`): Two- or three-parameter Weibull fit
  to significant wave height samples; returns shape, scale, location
- `wave_rose()` (`ndbc_analysis.py`): Directional Hs distribution by compass
  sector; returns sector-frequency and mean Hs per sector
- `parse_stdmet_line()` / `parse_stdmet_file()`: Text parsers for NDBC
  standard meteorological (STDMET) bulletin format
- `CacheManager` (`cache/`): TTL-based parquet/JSON cache for API responses;
  shared `OfflineStore` for air-gapped environments
- `DatabaseManager` (`database/db_manager.py`): SQLite-backed observation store
  with initialisation and query helpers

## Data Sources
- NOAA NDBC: https://www.ndbc.noaa.gov/; real-time + 45 yr historical; text
- NOAA CO-OPS: https://tidesandcurrents.noaa.gov/api/; real-time; JSON
- Open-Meteo: https://open-meteo.com/; 7-day forecast + ERA5 reanalysis; JSON
- ERDDAP (NOAA/Copernicus): variable URL; gridded NetCDF/CSV; no auth
- Norwegian Met Institute Frost: https://frost.met.no/; requires API key;
  JSON; covers offshore and coastal stations

## Integration Points
- **Depends on**: `worldenergydata.common` (unit conversion, date helpers)
- **Used by**: `worldenergydata.marine_safety` (sea state operability),
  `worldenergydata.vessel_fleet` (weather routing context),
  `worldenergydata.analysis` (metocean statistics for field studies);
  `digitalmodel.hydrodynamics` consumes metocean outputs as environmental
  condition inputs (cross-repo)

## Status
Active — NDBC, CO-OPS, Open-Meteo, and ERDDAP clients implemented; NDBC
analysis helpers (scatter, Weibull, wave rose) implemented (WRK-316);
Met Norway client implemented; ERA5 extrapolation module partial
