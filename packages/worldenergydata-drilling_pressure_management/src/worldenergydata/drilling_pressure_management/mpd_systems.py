"""
ABOUTME: Managed Pressure Drilling (MPD) system specifications catalog.
ABOUTME: MPDSystemEntry for 5+ commercial systems with technical specs.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class MPDSystemEntry:
    """Specification record for a commercial MPD system."""

    system_id: str
    manufacturer: str
    product_name: str
    mpd_type: str  # "CBHP" | "PMCD" | "dual_gradient" | "RFC" | "multi_mode"
    max_pressure_rating_psi: float
    max_flow_rate_gpm: float
    rcd_type: str  # "rotating_control_device" | "passive_rcd" | "active_rcd"
    integration_level: str  # "full_rig_integration" | "skid_mounted" | "portable"
    suitable_water_depths: list[str]
    compatible_rig_types: list[str]
    key_features: list[str]
    reference_wells: list[str]
    notes: str = ""


MPD_SYSTEMS: list[MPDSystemEntry] = [
    MPDSystemEntry(
        system_id="safekick_mpd",
        manufacturer="Safekick (Halliburton)",
        product_name="Safekick MPD System",
        mpd_type="multi_mode",
        max_pressure_rating_psi=15000.0,
        max_flow_rate_gpm=1200.0,
        rcd_type="active_rcd",
        integration_level="full_rig_integration",
        suitable_water_depths=["deepwater", "ultra_deepwater"],
        compatible_rig_types=["drillship", "semisubmersible"],
        key_features=[
            "Real-time downhole pressure monitoring via ECD control",
            "Dual-mode CBHP/PMCD operation",
            "Automated back-pressure regulation",
            "Full rig-integrated choke manifold",
            "Continuous flow drilling capability",
        ],
        reference_wells=["GOM Keathley Canyon KC-20", "GOM Walker Ridge WR-758"],
        notes="Primary system on Valaris DS-12; widely deployed in US Gulf of Mexico",
    ),
    MPDSystemEntry(
        system_id="ec_drill",
        manufacturer="Enhanced Drilling (NOV)",
        product_name="EC-Drill",
        mpd_type="PMCD",
        max_pressure_rating_psi=10000.0,
        max_flow_rate_gpm=800.0,
        rcd_type="passive_rcd",
        integration_level="skid_mounted",
        suitable_water_depths=["deepwater", "ultra_deepwater"],
        compatible_rig_types=["semisubmersible", "drillship"],
        key_features=[
            "Pump and dump PMCD with seawater returns",
            "Narrow pressure window drilling solution",
            "Reduces mud weight requirements",
            "Modular skid design for rig retrofit",
            "Proven in Norwegian Continental Shelf HPHT wells",
        ],
        reference_wells=["Statoil Aasta Hansteen", "Equinor Johan Sverdrup"],
        notes="Preferred for NCS and harsh-environment semisubs; acquired by NOV in 2019",
    ),
    MPDSystemEntry(
        system_id="microflux_weatherford",
        manufacturer="Weatherford International",
        product_name="Microflux Control System",
        mpd_type="CBHP",
        max_pressure_rating_psi=5000.0,
        max_flow_rate_gpm=600.0,
        rcd_type="rotating_control_device",
        integration_level="skid_mounted",
        suitable_water_depths=["shallow", "deepwater"],
        compatible_rig_types=["drillship", "semisubmersible", "jackup", "land"],
        key_features=[
            "Early kick and loss detection capability",
            "Real-time flow measurement at sub-barrel accuracy",
            "Continuous wellbore pressure monitoring",
            "Multi-rig type compatibility",
            "Industry-standard CBHP constant bottomhole pressure control",
        ],
        reference_wells=["BP GoM deepwater exploration", "Shell Perdido"],
        notes="Broad compatibility across rig types; well suited for exploration programs",
    ),
    MPDSystemEntry(
        system_id="onesubsea_mpd",
        manufacturer="SLB (Schlumberger) / OneSubsea",
        product_name="OneSubsea MPD System",
        mpd_type="dual_gradient",
        max_pressure_rating_psi=20000.0,
        max_flow_rate_gpm=1500.0,
        rcd_type="active_rcd",
        integration_level="full_rig_integration",
        suitable_water_depths=["deepwater", "ultra_deepwater"],
        compatible_rig_types=["drillship", "semisubmersible"],
        key_features=[
            "Subsea mud lift dual gradient capability",
            "20K rated for HPHT ultra-deepwater",
            "Integrated subsea rotating control device",
            "Closed-loop automated pressure management",
            "Compatible with SLB DrillPlan real-time optimization",
        ],
        reference_wells=["GOM Tiber well", "GOM Paleogene exploratory"],
        notes="Highest pressure rating in catalog; targets ultra-deepwater frontier wells",
    ),
    MPDSystemEntry(
        system_id="afglobal_dapc",
        manufacturer="AFGlobal Corporation",
        product_name="Dynamic Annular Pressure Control (DAPC)",
        mpd_type="CBHP",
        max_pressure_rating_psi=7500.0,
        max_flow_rate_gpm=1000.0,
        rcd_type="active_rcd",
        integration_level="full_rig_integration",
        suitable_water_depths=["deepwater", "ultra_deepwater"],
        compatible_rig_types=["drillship"],
        key_features=[
            "Dynamic annular pressure control for drillships",
            "Real-time ECD management and optimization",
            "Automated well control response",
            "Reduces NPT from pressure-related events",
            "Full BOP stack compatibility",
        ],
        reference_wells=["Transocean Deepwater Atlas GOM", "Shell Appomattox"],
        notes="Optimized for drillship geometry; deployed on several 7th-gen drillships",
    ),
    MPDSystemEntry(
        system_id="managed_pressure_ops_secure",
        manufacturer="Managed Pressure Operations (MPO)",
        product_name="SecureDrill MPD",
        mpd_type="RFC",
        max_pressure_rating_psi=5000.0,
        max_flow_rate_gpm=500.0,
        rcd_type="passive_rcd",
        integration_level="portable",
        suitable_water_depths=["shallow", "deepwater"],
        compatible_rig_types=["jackup", "land", "drillship"],
        key_features=[
            "Returns flow control (RFC) design",
            "Portable system for rig-agnostic deployment",
            "Low footprint for jackup and land rig integration",
            "Cost-effective for moderate-complexity wells",
            "Fast installation and rig-up time",
        ],
        reference_wells=["North Sea jack-up MPD campaign", "Oman land rig HPHT"],
        notes="RFC configuration primarily; suited for shallower HPHT applications",
    ),
]

_SYSTEMS_INDEX: dict[str, MPDSystemEntry] = {s.system_id: s for s in MPD_SYSTEMS}


def get_system(system_id: str) -> MPDSystemEntry:
    """Return the MPDSystemEntry for the given system_id.

    Raises KeyError if system_id is not found.
    """
    if system_id not in _SYSTEMS_INDEX:
        raise KeyError(f"Unknown MPD system_id: {system_id!r}")
    return _SYSTEMS_INDEX[system_id]


def get_systems_by_type(mpd_type: str) -> list[MPDSystemEntry]:
    """Return all systems matching the given mpd_type."""
    return [s for s in MPD_SYSTEMS if s.mpd_type == mpd_type]


def get_systems_by_rig_type(rig_type: str) -> list[MPDSystemEntry]:
    """Return all systems compatible with the given rig_type."""
    return [s for s in MPD_SYSTEMS if rig_type in s.compatible_rig_types]


def systems_summary() -> pd.DataFrame:
    """Return a summary DataFrame of all MPD systems."""
    rows = [
        {
            "system_id": s.system_id,
            "manufacturer": s.manufacturer,
            "product_name": s.product_name,
            "mpd_type": s.mpd_type,
            "max_pressure_rating_psi": s.max_pressure_rating_psi,
            "max_flow_rate_gpm": s.max_flow_rate_gpm,
            "rcd_type": s.rcd_type,
            "integration_level": s.integration_level,
        }
        for s in MPD_SYSTEMS
    ]
    return pd.DataFrame(rows)
