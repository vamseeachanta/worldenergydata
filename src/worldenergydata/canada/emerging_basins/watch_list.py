# ABOUTME: Emerging basin watch list — data stubs for pre-production frontier basins.
# ABOUTME: Guyana Stabroek, Suriname GranMorgu, Namibia Orange Basin, Falklands Sea Lion.

"""
Emerging Basin Watch List.

Provides structured stubs for four major frontier basins that are in exploration,
appraisal, or early development phases.  Each stub captures operator information,
reserve estimates, timeline projections, and monitoring triggers that would
indicate material progress toward first oil.

Sources: operator press releases, Wood Mackenzie basin summaries, IEA upstream
investment reports (2023-2025), and Rystad Energy frontier basin tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class EmergingBasinStub:
    """Data stub for a pre-production or early-production frontier basin.

    Attributes:
        basin_name: Human-readable name of the basin or block.
        country: Host country (ISO-3166 full name).
        operator: Lead operator name.
        status: Current development status.
        estimated_reserves_bboe: Best-estimate recoverable reserves in
            billion barrels of oil equivalent (Bboe).
        first_oil_estimate: Projected first-oil year as "YYYY" or "TBD".
        monitor_triggers: List of observable events that would indicate
            material progress warranting data refresh.
        source: Attribution for the stub data.
    """

    basin_name: str
    country: str
    operator: str
    status: str  # "exploration" | "appraisal" | "development" | "production"
    estimated_reserves_bboe: float
    first_oil_estimate: str  # "YYYY" or "TBD"
    monitor_triggers: List[str]
    source: str


# ---------------------------------------------------------------------------
# Watch list
# ---------------------------------------------------------------------------

EMERGING_BASINS: List[EmergingBasinStub] = [
    EmergingBasinStub(
        basin_name="Guyana Stabroek",
        country="Guyana",
        operator="ExxonMobil",
        status="production",
        estimated_reserves_bboe=11.0,
        first_oil_estimate="2019",
        monitor_triggers=[
            "Yellowtail FPSO first oil (Phase 4)",
            "Hammerhead FID announced",
            "Fangtooth appraisal results released",
            "New discovery announced on Stabroek block",
            "PPGML block licensing update",
        ],
        source="ExxonMobil Guyana press releases; Rystad Upstream Analytics 2024",
    ),
    EmergingBasinStub(
        basin_name="Suriname GranMorgu",
        country="Suriname",
        operator="TotalEnergies",
        status="development",
        estimated_reserves_bboe=2.5,
        first_oil_estimate="2028",
        monitor_triggers=[
            "Block 58 FID announced",
            "GranMorgu FPSO contract awarded",
            "Appraisal well results released for Bonboni/Krabdagu",
            "Apache exit or stake sale in Block 58",
            "Suriname government PSA terms finalised",
        ],
        source="TotalEnergies Block 58 press releases; Wood Mackenzie Suriname Basin 2024",
    ),
    EmergingBasinStub(
        basin_name="Namibia Orange Basin",
        country="Namibia",
        operator="Shell",
        status="appraisal",
        estimated_reserves_bboe=3.0,
        first_oil_estimate="2030",
        monitor_triggers=[
            "Graff/Venus FID announced",
            "Shell or TotalEnergies FPSO contract awarded",
            "Appraisal drilling campaign results (Block 2913B)",
            "Namibia Petroleum (NAMCOR) stake structure confirmed",
            "Environmental impact assessment approved",
        ],
        source="Shell Namibia exploration updates; Namibia MEM upstream reports 2024",
    ),
    EmergingBasinStub(
        basin_name="Falkland Islands Sea Lion",
        country="Falkland Islands",
        operator="Navitas Petroleum",
        status="development",
        estimated_reserves_bboe=0.5,
        first_oil_estimate="2027",
        monitor_triggers=[
            "Sea Lion Phase 1 FID confirmed",
            "FPSO/FSO contract awarded",
            "Harbour Energy farm-in or stake transfer",
            "Falkland Islands government development licence renewed",
            "Financing package for FPSO secured",
        ],
        source=(
            "Navitas Petroleum Falkland Islands updates; "
            "Harbour Energy Sea Lion asset update 2024"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


def get_emerging_basins() -> List[EmergingBasinStub]:
    """Return the full emerging basin watch list.

    Returns:
        List of all :class:`EmergingBasinStub` entries.
    """
    return list(EMERGING_BASINS)


def get_basin(name: str) -> EmergingBasinStub:
    """Retrieve a single basin stub by name.

    Args:
        name: Basin name string (case-sensitive, e.g. ``"Guyana Stabroek"``).

    Returns:
        Matching :class:`EmergingBasinStub`.

    Raises:
        KeyError: If no basin with the given name exists in the watch list.
    """
    for stub in EMERGING_BASINS:
        if stub.basin_name == name:
            return stub
    available = ", ".join(s.basin_name for s in EMERGING_BASINS)
    raise KeyError(
        f"Basin {name!r} not found in watch list. Available: {available}"
    )
