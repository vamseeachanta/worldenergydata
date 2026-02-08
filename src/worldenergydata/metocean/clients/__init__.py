# ABOUTME: Client module for metocean data sources
# ABOUTME: Provides base client and source-specific implementations for NDBC, CO-OPS, Open-Meteo, MET Norway, ERDDAP

"""
Clients for Metocean Data Sources

Provides HTTP clients for fetching data from various metocean data providers:
- NDBC: National Data Buoy Center buoy and station data
- CO-OPS: Tides and currents from NOAA
- Open-Meteo Marine: Marine weather forecasts
- MET Norway: Norwegian Meteorological Institute ocean and weather forecasts
- ERDDAP: IOOS/GCOOS oceanographic data servers
"""

from worldenergydata.metocean.clients.base_client import BaseClient, FetchResult
from worldenergydata.metocean.clients.coops_client import (
    COOPSClient,
    COOPSCurrent,
    COOPSStation,
    COOPSTidePrediction,
    COOPSWaterLevel,
)
from worldenergydata.metocean.clients.erddap_client import (
    ERDDAPClient,
    ERDDAPDataset,
    ERDDAPObservation,
)
from worldenergydata.metocean.clients.met_norway_client import (
    MetNorwayClient,
    MetNorwayForecast,
)
from worldenergydata.metocean.clients.ndbc_client import (
    NDBCClient,
    NDBCObservation,
    NDBCStation,
)
from worldenergydata.metocean.clients.open_meteo_client import (
    OpenMeteoClient,
    OpenMeteoForecast,
)

__all__ = [
    "BaseClient",
    "FetchResult",
    "NDBCClient",
    "NDBCStation",
    "NDBCObservation",
    "OpenMeteoClient",
    "OpenMeteoForecast",
    "COOPSClient",
    "COOPSStation",
    "COOPSWaterLevel",
    "COOPSCurrent",
    "COOPSTidePrediction",
    "MetNorwayClient",
    "MetNorwayForecast",
    "ERDDAPClient",
    "ERDDAPDataset",
    "ERDDAPObservation",
]
