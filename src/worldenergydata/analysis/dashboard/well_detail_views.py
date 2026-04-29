"""Compatibility wrapper for legacy well detail view imports."""

from worldenergydata.bsee.analysis.well_data_verification import VerificationWorkflow
from worldenergydata.well_production_dashboard.well_detail_views import *

__all__ = [name for name in globals() if not name.startswith("_")]
