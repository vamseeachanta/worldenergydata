# ABOUTME: BCER data loaders and sources package initialization
# ABOUTME: Provides data access layer for BC Energy Regulator ArcGIS services

"""
BCER Data Sources Module.

This package provides data loaders for BCER ArcGIS REST services:
- ArcGIS feature service clients
- Petrinex BC API client
- Geometry processors

Example usage:
    from worldenergydata.modules.canada.bcer.data import BCERDataLoader

    loader = BCERDataLoader()
    wells = loader.load_wells()
"""

# Data loaders will be added as implementations progress
__all__ = []
