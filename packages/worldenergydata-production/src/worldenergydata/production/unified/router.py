"""RegionRouter — maps region string keys to their adapter instances.

The router is the single source-of-truth for which adapters handle which
region.  All adapter registration happens here; callers never instantiate
adapters directly.
"""

from __future__ import annotations

from typing import Dict, List

from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.adapters.brazil_anp_adapter import (
    BrazilAnpAdapter,
)
from worldenergydata.production.unified.adapters.bsee_adapter import BseeAdapter
from worldenergydata.production.unified.adapters.canada_adapter import CanadaAdapter
from worldenergydata.production.unified.adapters.eia_us_adapter import EiaUsAdapter
from worldenergydata.production.unified.adapters.mexico_cnh_adapter import (
    MexicoCnhAdapter,
)
from worldenergydata.production.unified.adapters.sodir_adapter import SodirAdapter
from worldenergydata.production.unified.adapters.spain_cores_adapter import (
    SpainCoresAdapter,
)
from worldenergydata.production.unified.adapters.texas_rrc_adapter import (
    TexasRrcAdapter,
)
from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter

# Canonical region keys accepted by RegionRouter.
REGION_ALIASES: Dict[str, str] = {
    # Norwegian Continental Shelf
    "ncs": "ncs",
    "norway": "ncs",
    "sodir": "ncs",
    # Gulf of Mexico (BSEE)
    "gom": "gom",
    "bsee": "gom",
    "gulf_of_mexico": "gom",
    # Brazil
    "brazil": "brazil",
    "anp": "brazil",
    "brazil_anp": "brazil",
    # UK Continental Shelf
    "ukcs": "ukcs",
    "uk": "ukcs",
    # Spain CORES
    "spain": "spain",
    "cores": "spain",
    # EIA US plays
    "eia_us": "eia_us",
    "eia": "eia_us",
    "us": "eia_us",
    # Mexico
    "mexico": "mexico",
    "cnh": "mexico",
    "mexico_cnh": "mexico",
    # Texas RRC
    "texas": "texas",
    "rrc": "texas",
    "texas_rrc": "texas",
    # Canada offshore NL
    "canada": "canada",
    "nl": "canada",
}


class RegionRouter:
    """Maps region strings to concrete adapter instances.

    Usage::

        router = RegionRouter()
        adapter = router.get_adapter("ncs")
        regions = router.list_regions()
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, AbstractProductionAdapter] = {
            "ncs": SodirAdapter(),
            "gom": BseeAdapter(),
            "brazil": BrazilAnpAdapter(),
            "ukcs": UkcsAdapter(),
            "spain": SpainCoresAdapter(),
            "eia_us": EiaUsAdapter(),
            "mexico": MexicoCnhAdapter(),
            "texas": TexasRrcAdapter(),
            "canada": CanadaAdapter(),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_regions(self) -> List[str]:
        """Return sorted canonical region keys."""
        return sorted(self._adapters)

    def get_adapter(self, region: str) -> AbstractProductionAdapter:
        """Return the adapter for *region* (aliases accepted).

        Args:
            region: Region key or alias (case-insensitive).

        Returns:
            Corresponding adapter instance.

        Raises:
            KeyError: If *region* is not recognised.
        """
        canonical = self._resolve(region)
        return self._adapters[canonical]

    def resolve_regions(self, regions: List[str]) -> List[str]:
        """Resolve a list of raw region strings to canonical keys.

        Duplicates are removed; order is preserved (first occurrence wins).

        Args:
            regions: Raw region strings from a ProductionQuery.

        Returns:
            Deduplicated list of canonical region keys.

        Raises:
            KeyError: If any region cannot be resolved.
        """
        seen: set[str] = set()
        canonical: List[str] = []
        for r in regions:
            c = self._resolve(r)
            if c not in seen:
                canonical.append(c)
                seen.add(c)
        return canonical

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, region: str) -> str:
        key = region.lower().strip()
        if key in REGION_ALIASES:
            return REGION_ALIASES[key]
        raise KeyError(
            f"Unknown region {region!r}. " f"Valid options: {sorted(REGION_ALIASES)}"
        )
