# ABOUTME: HSE (Health, Safety, Environment) module initialization
# ABOUTME: Exports database models, importers, and data quality validation for BSEE HSE incidents

"""
HSE Module - Health, Safety, and Environment Incident Management

This module provides comprehensive HSE incident data management for BSEE
Gulf of Mexico offshore operations including:
- SQLAlchemy ORM models for incident tracking
- Data importers for BSEE incident, penalty, and statistics databases
- Post-import data quality validation
- Geographic validation for Gulf of Mexico boundaries

Example usage:
    from worldenergydata.modules.hse import (
        HSEIncident,
        BaseImporter,
        BSEEIncidentsImporter,
        DataQualityValidator,
    )

    # Import incidents from CSV
    importer = BSEEIncidentsImporter(db_session, csv_file_path="incidents.csv")
    stats = importer.import_data()

    # Validate data quality
    validator = DataQualityValidator(db_session)
    results = validator.run_all_validations()
"""

from worldenergydata.common import get_logger

# Database models
from worldenergydata.modules.hse.database import (
    Base,
    HSEIncident,
    InjuryIncident,
    SpillIncident,
    ViolationIncident,
    EquipmentFailure,
)

# Importers
from worldenergydata.modules.hse.importers.base_importer import BaseImporter
from worldenergydata.modules.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
from worldenergydata.modules.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
from worldenergydata.modules.hse.importers.bsee_statistics_importer import BSEEStatisticsImporter
from worldenergydata.modules.hse.importers.data_quality_validator import DataQualityValidator

__version__ = "1.0.0"
__all__ = [
    # Database models
    "Base",
    "HSEIncident",
    "InjuryIncident",
    "SpillIncident",
    "ViolationIncident",
    "EquipmentFailure",
    # Importers
    "BaseImporter",
    "BSEEIncidentsImporter",
    "BSEEPenaltiesImporter",
    "BSEEStatisticsImporter",
    # Validation
    "DataQualityValidator",
]

_logger = get_logger(__name__)
