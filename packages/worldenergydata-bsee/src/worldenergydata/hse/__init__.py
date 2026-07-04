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
    from worldenergydata.hse import (
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
from worldenergydata.hse.database import (
    Base,
    EquipmentFailure,
    HSEIncident,
    InjuryIncident,
    SpillIncident,
    ToxicRelease,
    ViolationIncident,
)

# Incident-grounding query (#487): failure-mode -> real precedent incidents
from worldenergydata.hse.grounding import Grounding, ground

# Demand-logging entry point (#491): the canonical call for bots/agents — logs
# which failure modes get requested so coverage gaps surface as the next build.
from worldenergydata.hse.grounding_demand import ground_and_log

# Importers
from worldenergydata.hse.importers.base_importer import BaseImporter
from worldenergydata.hse.importers.bsee_incidents_importer import (
    BSEEIncidentsImporter,
)
from worldenergydata.hse.importers.bsee_penalties_importer import (
    BSEEPenaltiesImporter,
)
from worldenergydata.hse.importers.bsee_statistics_importer import (
    BSEEStatisticsImporter,
)
from worldenergydata.hse.importers.data_quality_validator import (
    DataQualityValidator,
)
from worldenergydata.hse.importers.epa_tri_importer import EPATRIImporter

# Query API (wed#363 / workspace-hub#3286): typed-query surfaces on the shared
# TypedQuery base. Surfaced at the top level as ``wed.hse_api``.
from worldenergydata.hse import api

__version__ = "1.0.0"
__all__ = [
    # Database models
    "Base",
    "HSEIncident",
    "InjuryIncident",
    "SpillIncident",
    "ViolationIncident",
    "EquipmentFailure",
    "ToxicRelease",
    # Importers
    "BaseImporter",
    "BSEEIncidentsImporter",
    "BSEEPenaltiesImporter",
    "BSEEStatisticsImporter",
    "EPATRIImporter",
    # Validation
    "DataQualityValidator",
    # Incident grounding (#487) + demand logging (#491)
    "ground",
    "Grounding",
    "ground_and_log",
    # Query API (wed#363)
    "api",
]

_logger = get_logger(__name__)
