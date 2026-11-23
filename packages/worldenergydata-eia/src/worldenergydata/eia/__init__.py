"""EIA API v2 HTTP client for live feed ingestion (eia).

This module is the EIA API v2 HTTP client (api.eia.gov/v2/).
It handles weekly petroleum/gas feed ingestion with incremental JSONL
output and state tracking between runs.

Provides:
- EIAFeedClient: HTTP client for EIA API v2 weekly petroleum and gas endpoints
- EIAIngestionSync: Incremental JSONL ingestion with state tracking
- CLI command: worldenergydata eia-sync

Related:
    worldenergydata.eia_us — US state-level production analytics
        (EIA-914, DPR basins, Alaska breakdown, shale decline, fiscal models).
        Use that module for domestic production analysis rather than
        live API ingestion.
"""

from worldenergydata.eia.client import EIAFeedClient, EIAFeedError, EIAKeyError
from worldenergydata.eia.ingestion import EIAIngestionState, EIAIngestionSync

__all__ = [
    "EIAFeedClient",
    "EIAFeedError",
    "EIAKeyError",
    "EIAIngestionState",
    "EIAIngestionSync",
]
