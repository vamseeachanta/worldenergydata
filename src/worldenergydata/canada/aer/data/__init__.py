# ABOUTME: AER data loaders and sources package initialization
# ABOUTME: Provides data access layer for Alberta Energy Regulator sources

"""
AER Data Sources Module.

This package provides data loaders and sources for AER data:
- Statistical report parsers (ST series)
- Petrinex API client
- Data file readers (CSV, Excel)

Example usage:
    from worldenergydata.canada.aer.data import AERDataLoader

    loader = AERDataLoader()
    wells = loader.load_wells()
"""

# Data loaders will be added as implementations progress
__all__ = []
