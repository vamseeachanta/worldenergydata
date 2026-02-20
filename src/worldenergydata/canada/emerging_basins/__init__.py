# ABOUTME: Emerging basin watch list sub-package initialization.
# ABOUTME: Exports stubs for pre-production frontier basins worldwide.

"""Emerging basin watch list — frontier basins approaching first oil."""

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
]
