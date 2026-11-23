"""
Well Data Verification System

A comprehensive verification system that extends the existing validation framework
to provide systematic workflows for validating production data accuracy and
ensuring data quality standards.
"""

from .base import VerificationError, VerificationResult, VerificationWorkflow
from .config import VerificationConfig
from .processors import BSEEDataAdapter

__version__ = "1.0.0"
__all__ = [
    "VerificationResult",
    "VerificationWorkflow",
    "VerificationError",
    "VerificationConfig",
    "BSEEDataAdapter",
]
