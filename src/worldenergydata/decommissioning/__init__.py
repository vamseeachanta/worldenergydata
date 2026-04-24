# ABOUTME: Decommissioning analytics package for offshore assets.
# ABOUTME: Exports cost estimation, regulatory database, late-life
# identification, and data completeness scoring.

"""Decommissioning analytics for offshore oil and gas assets.

Sub-modules:
    cost_model         - Parametric cost estimation by asset type, region, depth
    regulations        - BSEE, NSTA, PSA, ANP regulatory database
    late_life          - Late-life field identification from production decline
    data_completeness  - Documentation completeness scoring

Quick import::

    from worldenergydata.decommissioning import (
        DecommissioningCostEstimator,
        DecommissioningCostEstimate,
        DecommissioningRegulation,
        get_regulations,
        get_lead_time,
        regulatory_summary,
        DECOMMISSIONING_REGULATIONS,
        LateLifeAssessment,
        LateLifeIdentifier,
        CompletenessScore,
        DataCompletenessScorer,
    )
"""

from worldenergydata.decommissioning.cost_calibration import (
    CalibrationFit,
    CalibrationResult,
    CostModelCalibration,
)
from worldenergydata.decommissioning.cost_model import (
    DecommissioningCostEstimate,
    DecommissioningCostEstimator,
)
from worldenergydata.decommissioning.data_completeness import (
    CompletenessScore,
    DataCompletenessScorer,
)
from worldenergydata.decommissioning.late_life import (
    LateLifeAssessment,
    LateLifeIdentifier,
)
from worldenergydata.decommissioning.regulations import (
    DECOMMISSIONING_REGULATIONS,
    DecommissioningRegulation,
    get_lead_time,
    get_regulations,
    regulatory_summary,
)

__all__ = [
    # Cost model
    "DecommissioningCostEstimate",
    "DecommissioningCostEstimator",
    # Regulations
    "DECOMMISSIONING_REGULATIONS",
    "DecommissioningRegulation",
    "get_lead_time",
    "get_regulations",
    "regulatory_summary",
    # Late life
    "LateLifeAssessment",
    "LateLifeIdentifier",
    # Data completeness
    "CompletenessScore",
    "DataCompletenessScorer",
    # Cost calibration
    "CalibrationFit",
    "CalibrationResult",
    "CostModelCalibration",
]
