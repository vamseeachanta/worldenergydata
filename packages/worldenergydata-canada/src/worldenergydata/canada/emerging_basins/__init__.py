# ABOUTME: Emerging basin watch list sub-package initialization.
# ABOUTME: Exports stubs for pre-production frontier basins worldwide.

"""Emerging basin watch list — frontier basins approaching first oil.

Two complementary views are provided:

* :mod:`watch_list` — one basin-level stub per frontier play (reserve estimate,
  first-oil projection, monitoring triggers).
* :mod:`discoveries` — a discovery-level catalog (one row per well/discovery)
  for the Guyana / Suriname / Namibia deepwater frontier (issue #603), backed
  by the curated CSV at ``data/modules/frontier_basins/curated/``.
"""

from worldenergydata.canada.emerging_basins.discoveries import (
    FrontierDiscoveryLoader,
)
from worldenergydata.canada.emerging_basins.discovery_schema import DiscoverySchema
from worldenergydata.canada.emerging_basins.watch_list import (
    EMERGING_BASINS,
    EmergingBasinStub,
    get_basin,
    get_emerging_basins,
)

__all__ = [
    "EmergingBasinStub",
    "EMERGING_BASINS",
    "get_emerging_basins",
    "get_basin",
    "DiscoverySchema",
    "FrontierDiscoveryLoader",
]
