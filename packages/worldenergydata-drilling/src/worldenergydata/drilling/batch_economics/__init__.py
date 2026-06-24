# ABOUTME: Batch drilling economics subpackage (WRK-219).
# ABOUTME: Exposes models, economics calculator, and BSEE batch detector.

"""Batch drilling economics: models, NPV analysis, and BSEE campaign detection."""

from worldenergydata.drilling.batch_economics.bsee_batch_detector import (
    BSEEBatchDetector,
)
from worldenergydata.drilling.batch_economics.economics import BatchDrillingEconomics
from worldenergydata.drilling.batch_economics.models import DrillCampaign, DrillingSite

__all__ = [
    "BatchDrillingEconomics",
    "BSEEBatchDetector",
    "DrillCampaign",
    "DrillingSite",
]
