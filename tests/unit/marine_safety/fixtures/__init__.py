"""Test fixtures package for marine_safety module.

This package provides sample data generators and fixtures for testing
marine safety incident database operations and parsers.
"""

from tests.modules.marine_safety.fixtures.sample_data import (
    SAMPLE_INCIDENT_DATA,
    SAMPLE_USCG_PDF_TEXT,
    SAMPLE_USCG_REPORT,
    generate_batch,
    generate_incident,
    generate_vessel,
)

__all__ = [
    "generate_incident",
    "generate_vessel",
    "generate_batch",
    "SAMPLE_USCG_REPORT",
    "SAMPLE_USCG_PDF_TEXT",
    "SAMPLE_INCIDENT_DATA",
]
