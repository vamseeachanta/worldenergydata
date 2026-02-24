"""EIA (Energy Information Administration) weekly feed ingestion.

Provides:
- EIAFeedClient: HTTP client for EIA API v2 weekly petroleum and gas endpoints
- EIAIngestionSync: Incremental JSONL ingestion with state tracking
- CLI command: worldenergydata eia-sync
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
