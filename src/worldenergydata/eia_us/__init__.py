"""US state-level and domain-specific EIA data analysis (eia_us).

This module handles US domestic production analytics using EIA data sources:
- US state-level crude + NGL production (EIA-914 / state series)
- DPR basin-level drilling productivity (Permian, Bakken, Eagle Ford, etc.)
- Alaska field-level breakdown (Prudhoe Bay, Kuparuk, Point Thomson)
- Hyperbolic shale decline curve analysis (Arps b>1, terminal switch)
- US federal and state fiscal regime models (BLM onshore, Texas RRC, ND Bakken)
- International country production reference data (EIA INTL series)

Status: Active implementation — analysis, client, production, and
        international sub-packages are implemented and tested.

Related:
    worldenergydata.eia — EIA API v2 HTTP client (api.eia.gov/v2/):
        weekly petroleum/gas feed ingestion with incremental JSONL output
        and state tracking. Use that module for live API access.
"""

__version__ = "1.0.0"
