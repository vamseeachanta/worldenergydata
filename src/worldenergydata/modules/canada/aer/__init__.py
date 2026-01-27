# ABOUTME: Alberta Energy Regulator (AER) submodule package initialization
# ABOUTME: Provides access to Alberta well, production, and facility data

"""
Alberta Energy Regulator (AER) Data Module.

This submodule provides integration with AER data sources for Alberta
oil and gas information including wells, production, facilities, and licenses.

Data Sources:
- AER Statistical Reports (ST series)
- Petrinex Alberta production data
- AER Public Data Portal

Example usage:
    from worldenergydata.modules.canada.aer import AER

    aer = AER()
    cfg = {"data_types": ["wells", "production"]}
    data = aer.router(cfg)
"""

from worldenergydata.modules.canada.aer.aer import AER
from worldenergydata.modules.canada.aer.api_client import AERClient

__all__ = ["AER", "AERClient"]
