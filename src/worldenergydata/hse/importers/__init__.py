# ABOUTME: HSE importers module initialization
# ABOUTME: Exports base importer class and concrete BSEE data importers

"""
HSE Importers Module

Provides data import capabilities for BSEE HSE incident databases:
- BaseImporter: Abstract base class with validation and persistence framework
- BSEEIncidentsImporter: Import incident investigation records from CSV
- BSEEPenaltiesImporter: Import civil penalty records from CSV
- BSEEStatisticsImporter: Import aggregated safety statistics from CSV
- DataQualityValidator: Post-import data quality validation

All importers support:
- CSV file parsing with field normalization
- Data validation against schema constraints
- Duplicate detection and handling
- Database persistence via SQLAlchemy
"""

from worldenergydata.hse.importers.base_importer import BaseImporter
from worldenergydata.hse.importers.bsee_incidents_importer import BSEEIncidentsImporter
from worldenergydata.hse.importers.bsee_penalties_importer import BSEEPenaltiesImporter
from worldenergydata.hse.importers.bsee_statistics_importer import BSEEStatisticsImporter
from worldenergydata.hse.importers.data_quality_validator import DataQualityValidator

__all__ = [
    "BaseImporter",
    "BSEEIncidentsImporter",
    "BSEEPenaltiesImporter",
    "BSEEStatisticsImporter",
    "DataQualityValidator",
]
