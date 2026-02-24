# ABOUTME: WRK-171 sanctioned project cost calibration module.
# ABOUTME: Provides models, dataset builder, regional loader, and multivariate calibration.

"""Sanctioned project cost calibration — WRK-171.

Exports:
    CostRecord, CostEstimate, CalibrationComparison — core data models
    SanctionedProjectDataset — dataset schema and synthetic data generator
    RegionalCostLoader — YAML-backed day-rate database
    MultivariateCalibration — linear regression cost predictor
    CostEngine — proxy + calibrated cost estimation
"""

from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    CalibrationComparison,
    ConfidenceLevel,
    CostEstimate,
    CostRecord,
    CostType,
    RigType,
    WaterDepthBand,
    WellDepthBand,
    classify_water_depth_band,
    classify_well_depth_band,
)
from worldenergydata.bsee.analysis.cost.sanctioned_dataset import SanctionedProjectDataset
from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader
from worldenergydata.bsee.analysis.cost.cost_calibration import (
    MultivariateCalibration,
    CalibrationReport,
)
from worldenergydata.bsee.analysis.cost.cost_engine import CostEngine

__all__ = [
    "ActivityType",
    "CalibrationComparison",
    "CalibrationReport",
    "ConfidenceLevel",
    "CostEngine",
    "CostEstimate",
    "CostRecord",
    "CostType",
    "MultivariateCalibration",
    "RegionalCostLoader",
    "RigType",
    "SanctionedProjectDataset",
    "WaterDepthBand",
    "WellDepthBand",
    "classify_water_depth_band",
    "classify_well_depth_band",
]
