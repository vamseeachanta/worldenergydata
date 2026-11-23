# ABOUTME: Unified metocean query interface — combines all data sources.
# ABOUTME: Provides MetoceanQuery, MetoceanResult, UnifiedMetoceanClient,
# harmonizer, coverage, dashboard.

"""
Unified Metocean Query Interface

Provides a single entry point to query multiple metocean data sources
simultaneously, with automatic source selection based on geographic
coverage, parallel data fetching, and harmonised output.
"""

from worldenergydata.metocean.unified.coverage import MetoceanCoverage
from worldenergydata.metocean.unified.dashboard import MetoceanDashboard
from worldenergydata.metocean.unified.harmonizer import MetoceanHarmonizer
from worldenergydata.metocean.unified.unified_query import (
    MetoceanQuery,
    MetoceanResult,
    UnifiedMetoceanClient,
)

__all__ = [
    "MetoceanQuery",
    "MetoceanResult",
    "UnifiedMetoceanClient",
    "MetoceanHarmonizer",
    "MetoceanCoverage",
    "MetoceanDashboard",
]
