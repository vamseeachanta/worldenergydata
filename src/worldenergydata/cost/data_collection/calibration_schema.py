"""
ABOUTME: Pydantic schema for sanctioned project cost data points.
ABOUTME: Used for calibration dataset construction and multivariate model training.

Schema fields align with WRK-171 Phase 2 specification.  All numeric fields carry
SI units (meters for depth, USD millions for cost).  Categorical fields use
string enums to ensure downstream consistency.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Categorical enums
# ---------------------------------------------------------------------------


class WaterDepthBand(str, Enum):
    """Water depth classification bands (metres)."""

    SHALLOW = "shallow"       # 0–300 m  (jack-up range)
    MID = "mid"               # 300–1,000 m
    DEEP = "deep"             # 1,000–2,000 m
    ULTRA_DEEP = "ultra_deep" # > 2,000 m


class WellDepthBand(str, Enum):
    """Total well depth classification bands (metres TVD/MD)."""

    SHALLOW = "shallow"       # 0–2,000 m
    MEDIUM = "medium"         # 2,000–4,000 m
    DEEP = "deep"             # 4,000–7,000 m
    ULTRA_DEEP = "ultra_deep" # > 7,000 m


class RigType(str, Enum):
    """Drilling rig / facility type."""

    DRILLSHIP = "drillship"
    SEMI_SUB = "semi_sub"
    JACK_UP = "jack_up"
    PLATFORM = "platform"


class ActivityType(str, Enum):
    """Well activity category."""

    DRILLING = "drilling"
    COMPLETION = "completion"
    INTERVENTION = "intervention"


class SubseaType(str, Enum):
    """Completion architecture — subsea vs. dry tree."""

    SUBSEA = "subsea"
    DRY_TREE = "dry_tree"


class CostType(str, Enum):
    """What the reported cost covers."""

    WELL_COST = "well_cost"
    DAY_RATE = "day_rate"
    TOTAL_CAPEX = "total_capex"


class Confidence(str, Enum):
    """Data quality / confidence level for the cost entry."""

    HIGH = "high"       # Direct operator/regulatory disclosure
    MEDIUM = "medium"   # Inferred from aggregate or partial disclosure
    LOW = "low"         # Estimated / analyst estimate


# ---------------------------------------------------------------------------
# Primary schema
# ---------------------------------------------------------------------------


class CostDataPoint(BaseModel):
    """A single sanctioned-project cost data point for calibration.

    All monetary values are in USD millions (USD MM).
    Depth values are in metres.
    """

    # Project identification
    project_name: str = Field(
        ..., min_length=1, description="Sanctioned project name (public)"
    )
    region: str = Field(
        ..., min_length=1, description="Geographic region (e.g. GOM, NCS, Brazil)"
    )

    # Water depth
    water_depth_m: float = Field(
        ..., ge=0.0, description="Water depth at project location (metres)"
    )
    water_depth_band: WaterDepthBand = Field(
        ..., description="Categorical water depth band"
    )

    # Well depth (optional — not always disclosed)
    well_depth_m: Optional[float] = Field(
        default=None, ge=0.0, description="Total well depth TVD or MD (metres)"
    )
    well_depth_band: Optional[WellDepthBand] = Field(
        default=None, description="Categorical well depth band"
    )

    # Project metadata
    operator: str = Field(..., min_length=1, description="Operating company name")
    year_sanction: int = Field(
        ...,
        ge=1970,
        le=2035,
        description="Year of FID / project sanction",
    )
    year_drilling: Optional[int] = Field(
        default=None,
        ge=1970,
        le=2040,
        description="Year(s) of primary drilling activity",
    )

    # Rig and activity
    rig_type: RigType = Field(..., description="Rig or facility type")
    activity_type: ActivityType = Field(..., description="Well activity category")

    # Technical flags
    hpht: bool = Field(
        ..., description="High pressure / high temperature well flag"
    )
    subsea: SubseaType = Field(
        ..., description="Completion architecture — subsea or dry tree"
    )

    # Cost
    cost_usd_mm: float = Field(
        ..., gt=0.0, description="Cost in USD millions (must be > 0)"
    )
    cost_type: CostType = Field(..., description="What the reported cost covers")

    # Provenance
    source: str = Field(
        ..., min_length=1, description="Data source (operator report, press release, etc.)"
    )
    confidence: Confidence = Field(
        ..., description="Data quality / confidence level"
    )
