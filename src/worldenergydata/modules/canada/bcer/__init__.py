# ABOUTME: BC Energy Regulator (BCER) submodule package initialization
# ABOUTME: Provides access to British Columbia well, production, and facility data

"""
BC Energy Regulator (BCER) Data Module.

This submodule provides integration with BCER data sources for British Columbia
oil and gas information through ArcGIS REST services.

Data Sources:
- BCER ArcGIS REST API (maps.bcer.gov.bc.ca)
- Petrinex BC production data

Example usage:
    from worldenergydata.modules.canada.bcer import BCER

    bcer = BCER()
    cfg = {"data_types": ["wells", "production"]}
    data = bcer.router(cfg)
"""

from worldenergydata.modules.canada.bcer.api_client import BCERClient
from worldenergydata.modules.canada.bcer.bcer import BCER

__all__ = ["BCER", "BCERClient"]
