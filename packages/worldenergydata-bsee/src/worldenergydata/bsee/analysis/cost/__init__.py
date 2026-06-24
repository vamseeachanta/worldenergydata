# ABOUTME: WRK-171/WRK-019 cost estimation and benchmarking module.
# ABOUTME: Provides models, dataset builder, regional loader, multivariate calibration,
# ABOUTME: cost summary aggregation, cross-regional benchmarking, and report generation.

"""Drilling, completion, and intervention cost module — WRK-171 + WRK-019.

Exports:
    CostRecord, CostEstimate, CalibrationComparison — core data models
    SanctionedProjectDataset — dataset schema and synthetic data generator
    RegionalCostLoader — YAML-backed day-rate database
    MultivariateCalibration — linear regression cost predictor
    CostEngine — proxy + calibrated cost estimation
    FieldCostSummary — per-field cost roll-up dataclass (WRK-019)
    summarize_field_costs — build FieldCostSummary from estimate lists
    summarize_lease_costs — per-lease aggregation dict
    summarize_region_costs — cross-field DataFrame
    BenchmarkResult — per-field benchmarking result (WRK-019)
    compare_fields_to_regional_average — deviation from regional mean
    detect_outliers — flag fields beyond std threshold
    build_comparison_dataframe — tidy DataFrame for reporting
"""

from worldenergydata.bsee.analysis.cost.benchmarking import (
    BenchmarkResult,
    build_comparison_dataframe,
    compare_fields_to_regional_average,
    detect_outliers,
)
from worldenergydata.bsee.analysis.cost.cost_calibration import (
    CalibrationReport,
    MultivariateCalibration,
)
from worldenergydata.bsee.analysis.cost.cost_engine import CostEngine
from worldenergydata.bsee.analysis.cost.cost_summary import (
    FieldCostSummary,
    summarize_field_costs,
    summarize_lease_costs,
    summarize_region_costs,
)
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
from worldenergydata.bsee.analysis.cost.regional_loader import RegionalCostLoader
from worldenergydata.bsee.analysis.cost.sanctioned_dataset import (
    SanctionedProjectDataset,
)

__all__ = [
    "ActivityType",
    "BenchmarkResult",
    "CalibrationComparison",
    "CalibrationReport",
    "ConfidenceLevel",
    "CostEngine",
    "CostEstimate",
    "CostRecord",
    "CostType",
    "FieldCostSummary",
    "MultivariateCalibration",
    "RegionalCostLoader",
    "RigType",
    "SanctionedProjectDataset",
    "WaterDepthBand",
    "WellDepthBand",
    "build_comparison_dataframe",
    "classify_water_depth_band",
    "classify_well_depth_band",
    "compare_fields_to_regional_average",
    "detect_outliers",
    "summarize_field_costs",
    "summarize_lease_costs",
    "summarize_region_costs",
]
