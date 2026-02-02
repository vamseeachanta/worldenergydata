# ABOUTME: Package init for marine safety data acquirers.
# ABOUTME: Provides reusable acquirer classes for periodic data refresh.

from worldenergydata.modules.marine_safety.acquirers.ntsb_carol_acquirer import (
    NTSBCAROLAcquirer,
)
from worldenergydata.modules.marine_safety.acquirers.uscg_misle_acquirer import (
    USCGMISLEAcquirer,
)

__all__ = [
    "NTSBCAROLAcquirer",
    "USCGMISLEAcquirer",
]
