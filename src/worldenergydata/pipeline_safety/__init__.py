# ABOUTME: Pipeline safety module initialization
# ABOUTME: Exports database models and PHMSA importer for pipeline incident management

"""
Pipeline Safety Module - PHMSA Pipeline Incident Management

This module provides pipeline safety incident data management for PHMSA
(Pipeline and Hazardous Materials Safety Administration) data covering:
- Gas Distribution (GD) incidents
- Gas Transmission/Gathering (GTGG) incidents
- Hazardous Liquid (HL) pipeline accidents
- Liquefied Natural Gas (LNG) facility incidents

Data spans 1986-present with ~21,000 total incident records.

Example usage:
    from worldenergydata.pipeline_safety import (
        PipelineIncident,
        PHMSAImporter,
    )

    # Import incidents from PHMSA Excel files
    importer = PHMSAImporter(db_session, data_dir="path/to/phmsa/extracted")
    stats = importer.import_data()
"""

from worldenergydata.common import get_logger
from worldenergydata.pipeline_safety.database import Base, PipelineIncident
from worldenergydata.pipeline_safety.importers.phmsa_importer import (
    PHMSAImporter,
)
from worldenergydata.pipeline_safety.workflow import (
    FFSResult,
    PipelineDefect,
    PipelineSafetyWorkflow,
)

__version__ = "1.1.0"
__all__ = [
    "Base",
    "PipelineIncident",
    "PHMSAImporter",
    "PipelineDefect",
    "FFSResult",
    "PipelineSafetyWorkflow",
]

_logger = get_logger(__name__)
