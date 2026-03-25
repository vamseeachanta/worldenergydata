"""
ABOUTME: MPD capability flags for drillship and semisubmersible fleets.
ABOUTME: Covers Valaris, Transocean, Noble contractor fleets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class RigMPDCapability:
    """MPD capability record for a single drilling rig."""

    rig_name: str
    rig_type: str  # "drillship" | "semisubmersible" | "jackup"
    contractor: str  # "Valaris" | "Transocean" | "Noble" | "Diamond" | etc.
    mpd_capable: bool
    mpd_system: Optional[str]  # system_id from MPD_SYSTEMS or None
    mpd_manufacturer: Optional[str]
    mpd_certification_year: Optional[int]
    deepwater_capable: bool
    notes: str = ""


FLEET_MPD_DATA: list[RigMPDCapability] = [
    # --- Valaris fleet ---
    RigMPDCapability(
        rig_name="VALARIS DS-12",
        rig_type="drillship",
        contractor="Valaris",
        mpd_capable=True,
        mpd_system="safekick_mpd",
        mpd_manufacturer="Safekick (Halliburton)",
        mpd_certification_year=2019,
        deepwater_capable=True,
        notes="12,000 ft rated; Safekick MPD system; deployed in GOM deepwater",
    ),
    RigMPDCapability(
        rig_name="VALARIS DS-8",
        rig_type="drillship",
        contractor="Valaris",
        mpd_capable=True,
        mpd_system="microflux_weatherford",
        mpd_manufacturer="Weatherford International",
        mpd_certification_year=2021,
        deepwater_capable=True,
        notes="12,000 ft rated; Weatherford Microflux MPD system installed",
    ),
    RigMPDCapability(
        rig_name="VALARIS DS-4",
        rig_type="drillship",
        contractor="Valaris",
        mpd_capable=False,
        mpd_system=None,
        mpd_manufacturer=None,
        mpd_certification_year=None,
        deepwater_capable=True,
        notes="12,000 ft rated; MPD not fitted as of 2025",
    ),
    RigMPDCapability(
        rig_name="VALARIS DPS-5",
        rig_type="semisubmersible",
        contractor="Valaris",
        mpd_capable=False,
        mpd_system=None,
        mpd_manufacturer=None,
        mpd_certification_year=None,
        deepwater_capable=True,
        notes="8,000 ft semisubmersible; no MPD fitted",
    ),
    # --- Transocean fleet ---
    RigMPDCapability(
        rig_name="Deepwater Atlas",
        rig_type="drillship",
        contractor="Transocean",
        mpd_capable=True,
        mpd_system="afglobal_dapc",
        mpd_manufacturer="AFGlobal Corporation",
        mpd_certification_year=2022,
        deepwater_capable=True,
        notes="Jurong Espadon design; 12,000 ft; DAPC MPD; 20K BOP rated",
    ),
    RigMPDCapability(
        rig_name="Deepwater Titan",
        rig_type="drillship",
        contractor="Transocean",
        mpd_capable=True,
        mpd_system="afglobal_dapc",
        mpd_manufacturer="AFGlobal Corporation",
        mpd_certification_year=2022,
        deepwater_capable=True,
        notes="Samsung 12000 design; 12,000 ft; 20K BOP; DAPC MPD system",
    ),
    RigMPDCapability(
        rig_name="Development Driller III",
        rig_type="semisubmersible",
        contractor="Transocean",
        mpd_capable=True,
        mpd_system="microflux_weatherford",
        mpd_manufacturer="Weatherford International",
        mpd_certification_year=2018,
        deepwater_capable=True,
        notes="8,000 ft semisubmersible; Weatherford MPD fitted for narrow-window work",
    ),
    RigMPDCapability(
        rig_name="Deepwater Asgard",
        rig_type="semisubmersible",
        contractor="Transocean",
        mpd_capable=False,
        mpd_system=None,
        mpd_manufacturer=None,
        mpd_certification_year=None,
        deepwater_capable=True,
        notes="10,000 ft semisubmersible; no MPD fitted",
    ),
    # --- Noble Corporation fleet ---
    RigMPDCapability(
        rig_name="Noble Gerry de Souza",
        rig_type="drillship",
        contractor="Noble",
        mpd_capable=True,
        mpd_system="safekick_mpd",
        mpd_manufacturer="Safekick (Halliburton)",
        mpd_certification_year=2020,
        deepwater_capable=True,
        notes="Samsung 12000 DH design; 12,000 ft; Safekick MPD installed",
    ),
    RigMPDCapability(
        rig_name="Noble Globetrotter I",
        rig_type="semisubmersible",
        contractor="Noble",
        mpd_capable=True,
        mpd_system="ec_drill",
        mpd_manufacturer="Enhanced Drilling (NOV)",
        mpd_certification_year=2017,
        deepwater_capable=True,
        notes="Globetrotter Class; 10,000 ft; EC-Drill PMCD fitted",
    ),
    RigMPDCapability(
        rig_name="Noble Voyager",
        rig_type="drillship",
        contractor="Noble",
        mpd_capable=False,
        mpd_system=None,
        mpd_manufacturer=None,
        mpd_certification_year=None,
        deepwater_capable=True,
        notes="Samsung 96K design; 12,000 ft; no MPD fitted",
    ),
    RigMPDCapability(
        rig_name="Noble Globetrotter II",
        rig_type="semisubmersible",
        contractor="Noble",
        mpd_capable=False,
        mpd_system=None,
        mpd_manufacturer=None,
        mpd_certification_year=None,
        deepwater_capable=True,
        notes="Globetrotter Class; 10,000 ft; no MPD fitted",
    ),
]


def get_mpd_capable_rigs() -> list[RigMPDCapability]:
    """Return only rigs with mpd_capable=True."""
    return [r for r in FLEET_MPD_DATA if r.mpd_capable]


def get_contractor_fleet(contractor: str) -> list[RigMPDCapability]:
    """Return all rigs belonging to the named contractor."""
    return [r for r in FLEET_MPD_DATA if r.contractor == contractor]


def fleet_mpd_summary() -> pd.DataFrame:
    """Return a contractor-level summary DataFrame.

    Columns: contractor, total_rigs, mpd_capable_count.
    """
    from collections import defaultdict

    totals: dict[str, int] = defaultdict(int)
    capable: dict[str, int] = defaultdict(int)

    for rig in FLEET_MPD_DATA:
        totals[rig.contractor] += 1
        if rig.mpd_capable:
            capable[rig.contractor] += 1

    rows = [
        {
            "contractor": contractor,
            "total_rigs": totals[contractor],
            "mpd_capable_count": capable[contractor],
        }
        for contractor in sorted(totals)
    ]
    return pd.DataFrame(rows)
