"""Enumerations and constants for the vessel fleet module."""

from __future__ import annotations

from enum import Enum, unique


@unique
class VesselCategory(str, Enum):
    """Top-level vessel category."""

    DRILLING_RIG = "drilling_rig"
    CONSTRUCTION_VESSEL = "construction_vessel"
    SERVICE_VESSEL = "service_vessel"
    INTERVENTION_VESSEL = "intervention_vessel"


@unique
class RigType(str, Enum):
    """Drilling rig sub-types."""

    DRILLSHIP = "drillship"
    SEMI_SUBMERSIBLE = "semi_submersible"
    JACK_UP = "jack_up"
    PLATFORM_RIG = "platform_rig"
    TENDER_ASSISTED = "tender_assisted"
    INLAND_BARGE = "inland_barge"
    SUBMERSIBLE = "submersible"
    LAND_RIG = "land_rig"


@unique
class VesselType(str, Enum):
    """Construction/service vessel sub-types."""

    CRANE_VESSEL = "crane_vessel"
    PIPELAY_VESSEL = "pipelay_vessel"
    HEAVY_LIFT = "heavy_lift"
    HEAVY_TRANSPORT = "heavy_transport"
    WIND_INSTALLATION = "wind_installation"
    CABLE_LAY = "cable_lay"
    SURF_VESSEL = "surf_vessel"
    AHTS = "ahts"
    PSV = "psv"
    DIVE_SUPPORT = "dive_support"
    FPSO = "fpso"
    RLWI_MONOHULL = "rlwi_monohull"
    HEAVY_INTERVENTION_SEMI = "heavy_intervention_semi"
    MPSV = "mpsv"


@unique
class VesselStatus(str, Enum):
    """Operational status."""

    ACTIVE = "active"
    UNDER_CONTRACT = "under_contract"
    WARM_STACKED = "warm_stacked"
    COLD_STACKED = "cold_stacked"
    UNDER_CONSTRUCTION = "under_construction"
    IN_TRANSIT = "in_transit"
    IN_YARD = "in_yard"
    SCRAPPED = "scrapped"
    RETIRED = "retired"


@unique
class DataSource(str, Enum):
    """Provenance for each collected record."""

    XLS_HISTORICAL = "xls_historical"
    BSEE_WAR = "bsee_war"
    CONTRACTOR_FLEET_PAGE = "contractor_fleet_page"
    CONTRACTOR_SPEC_PDF = "contractor_spec_pdf"
    CONTRACTOR_FSR = "contractor_fsr"
    EQUASIS = "equasis"
    ABS_REGISTER = "abs_register"
    DNV_REGISTER = "dnv_register"
    LLOYD_REGISTER = "lloyd_register"
    BOEM = "boem"
    BAKER_HUGHES = "baker_hughes"
    MANUAL = "manual"


@unique
class PipelayMethod(str, Enum):
    """Pipelay installation method."""

    S_LAY = "s_lay"
    J_LAY = "j_lay"
    REEL_LAY = "reel_lay"
    FLEX_LAY = "flex_lay"


@unique
class PowerType(str, Enum):
    """Rig power system type."""

    AC = "ac"
    SCR = "scr"
    MECHANICAL = "mechanical"
    AC_VFD = "ac_vfd"


# --- Static constants ---

INACTIVE_STATUSES: frozenset[str] = frozenset(
    {
        VesselStatus.WARM_STACKED.value,
        VesselStatus.COLD_STACKED.value,
        VesselStatus.SCRAPPED.value,
        VesselStatus.RETIRED.value,
    }
)

DEEPWATER_THRESHOLD_FT: float = 4000.0
ULTRA_DEEPWATER_THRESHOLD_FT: float = 7500.0

FT_TO_M: float = 0.3048
M_TO_FT: float = 1.0 / FT_TO_M
