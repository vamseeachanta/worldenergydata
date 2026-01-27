# ABOUTME: Database package for the metocean module.
# ABOUTME: Exports models, database manager, and initialization functions.

"""
Database Module for Metocean Data

Provides SQLAlchemy models for stations, observations, forecasts,
and grid points along with database management utilities.
"""

from worldenergydata.modules.metocean.database.db_manager import (
    DatabaseManager,
    get_async_session,
    get_db_manager,
    get_session,
)
from worldenergydata.modules.metocean.database.init_db import (
    create_schema,
    create_tables,
    drop_tables,
    init_database,
)
from worldenergydata.modules.metocean.database.models import (
    Base,
    FetchLog,
    Forecast,
    GridPoint,
    Observation,
    Station,
)

__all__ = [
    # Models
    "Base",
    "Station",
    "Observation",
    "GridPoint",
    "Forecast",
    "FetchLog",
    # Database manager
    "DatabaseManager",
    "get_db_manager",
    "get_session",
    "get_async_session",
    # Initialization
    "create_schema",
    "create_tables",
    "drop_tables",
    "init_database",
]
