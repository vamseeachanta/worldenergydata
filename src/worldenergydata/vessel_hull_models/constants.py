# ABOUTME: Constants and enums for the vessel hull models module
# ABOUTME: Defines vessel types, model quality levels, and data sources

"""
Constants and Enumerations for Vessel Hull Models Module
"""

from enum import Enum


class VesselType(str, Enum):
    """Types of offshore installation vessels"""

    CRANE_VESSEL = "crane_vessel"
    PIPELAY_VESSEL = "pipelay_vessel"
    DERRICK_LAY_VESSEL = "derrick_lay_vessel"
    SINGLE_LIFT_VESSEL = "single_lift_vessel"
    PSV = "platform_supply_vessel"
    AHTS = "anchor_handling_tug_supply"
    CONSTRUCTION_VESSEL = "construction_vessel"
    DIVING_SUPPORT_VESSEL = "diving_support_vessel"
    FPSO = "floating_production_storage_offloading"
    SEMI_SUBMERSIBLE = "semi_submersible"
    JACK_UP = "jack_up"
    GENERIC = "generic"


class ModelSource(str, Enum):
    """Sources for 3D hull models"""

    CGTRADER = "cgtrader"
    SKETCHFAB = "sketchfab"
    TURBOSQUID = "turbosquid"
    GRABCAD = "grabcad"
    PARAMETRIC = "parametric"
    MANUAL = "manual"


class ModelQuality(str, Enum):
    """Quality levels for 3D models"""

    ENGINEERING = "engineering"  # CAD-grade accuracy
    PROFESSIONAL = "professional"  # High polygon, detailed
    ARTISTIC = "artistic"  # Visually appealing but not accurate
    SYNTHETIC = "synthetic"  # Parametrically generated


class HullFormType(str, Enum):
    """Standard hull form types for parametric generation"""

    SERIES_60 = "series_60"
    WIGLEY = "wigley"
    NPL = "npl"
    BARGE = "barge"
    SEMI_SUB = "semi_sub"
    PONTOON = "pontoon"


# Target vessel operators in GOM
GOM_OPERATORS = [
    "Heerema",
    "Saipem",
    "McDermott",
    "Allseas",
    "Subsea 7",
    "TechnipFMC",
    "Helix Energy Solutions",
]

# Priority vessel fleet for acquisition
PRIORITY_VESSELS = {
    "sleipnir": {
        "imo": "9781400",
        "operator": "Heerema",
        "type": VesselType.CRANE_VESSEL,
        "loa": 220.0,
        "beam": 102.0,
        "draft": 12.0,
    },
    "thialf": {
        "imo": "8757740",
        "operator": "Heerema",
        "type": VesselType.CRANE_VESSEL,
        "loa": 201.6,
        "beam": 88.4,
        "draft": 11.0,
    },
    "saipem_7000": {
        "imo": "8767350",
        "operator": "Saipem",
        "type": VesselType.CRANE_VESSEL,
        "loa": 198.0,
        "beam": 87.0,
        "draft": 9.2,
    },
    "pioneering_spirit": {
        "imo": "9593505",
        "operator": "Allseas",
        "type": VesselType.SINGLE_LIFT_VESSEL,
        "loa": 382.0,
        "beam": 124.0,
        "draft": 10.0,
    },
    "seven_borealis": {
        "imo": "9426941",
        "operator": "Subsea 7",
        "type": VesselType.PIPELAY_VESSEL,
        "loa": 182.0,
        "beam": 46.0,
        "draft": 8.0,
    },
}

# Default dimension tolerances
DEFAULT_TOLERANCE = 0.05  # 5% tolerance for dimension validation

# OBJ file constraints
MAX_VERTEX_COUNT = 10_000_000
MAX_FACE_COUNT = 10_000_000
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB

# Mesh decimation targets
DECIMATION_LOW = 10_000  # faces
DECIMATION_MEDIUM = 50_000
DECIMATION_HIGH = 200_000
