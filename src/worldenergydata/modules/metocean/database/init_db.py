# ABOUTME: Database initialization utilities for the metocean module.
# ABOUTME: Provides functions to create schema, tables, and initialize the database.

"""
Database Initialization for Metocean Module

Provides functions for creating and managing the metocean database schema,
tables, and enum types.
"""

from typing import Optional

from sqlalchemy import text

from worldenergydata.modules.metocean.config import get_config
from worldenergydata.modules.metocean.database.db_manager import (
    DatabaseManager,
    get_db_manager,
)
from worldenergydata.modules.metocean.database.models import Base
from worldenergydata.modules.metocean.exceptions import DatabaseError


def create_schema(db_manager: Optional[DatabaseManager] = None) -> None:
    """
    Create the metocean database schema if it doesn't exist.

    Args:
        db_manager: Optional database manager instance. Uses global if not provided.

    Raises:
        DatabaseError: If schema creation fails
    """
    manager = db_manager or get_db_manager()
    config = get_config().database

    try:
        with manager.engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.schema}"))
            conn.commit()
    except Exception as e:
        raise DatabaseError(
            message=f"Failed to create schema '{config.schema}': {str(e)}",
            error_code="SCHEMA_CREATE_FAILED",
        )


def create_enum_types(db_manager: Optional[DatabaseManager] = None) -> None:
    """
    Create PostgreSQL ENUM types for the metocean module.

    Creates the following enum types:
    - data_source_enum: Data source identifiers
    - station_type_enum: Station/platform types

    Args:
        db_manager: Optional database manager instance. Uses global if not provided.

    Raises:
        DatabaseError: If enum creation fails
    """
    manager = db_manager or get_db_manager()
    config = get_config().database
    schema = config.schema

    enum_definitions = {
        "data_source_enum": [
            "ndbc",
            "coops",
            "open_meteo",
            "cmems",
            "hycom",
            "nws",
            "ecmwf",
            "gfs",
            "other",
        ],
        "station_type_enum": [
            "buoy",
            "cman",
            "dart",
            "ship",
            "oil_platform",
            "tide_gauge",
            "current_meter",
            "weather_station",
            "drifter",
            "argo",
            "glider",
            "hf_radar",
            "satellite",
            "model_grid",
            "other",
        ],
    }

    try:
        with manager.engine.connect() as conn:
            for enum_name, values in enum_definitions.items():
                values_str = ", ".join(f"'{v}'" for v in values)
                conn.execute(
                    text(
                        f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_type t
                            JOIN pg_namespace n ON n.oid = t.typnamespace
                            WHERE t.typname = '{enum_name}'
                            AND n.nspname = '{schema}'
                        ) THEN
                            CREATE TYPE {schema}.{enum_name} AS ENUM ({values_str});
                        END IF;
                    END
                    $$;
                """
                    )
                )
            conn.commit()
    except Exception as e:
        raise DatabaseError(
            message=f"Failed to create enum types: {str(e)}",
            error_code="ENUM_CREATE_FAILED",
        )


def create_tables(db_manager: Optional[DatabaseManager] = None) -> None:
    """
    Create all database tables defined in models.

    This function is idempotent - it will only create tables
    that don't already exist.

    Args:
        db_manager: Optional database manager instance. Uses global if not provided.

    Raises:
        DatabaseError: If table creation fails
    """
    manager = db_manager or get_db_manager()

    try:
        # Ensure schema and enums exist first
        create_schema(manager)
        create_enum_types(manager)

        # Create all tables
        Base.metadata.create_all(
            bind=manager.engine,
            checkfirst=True,
        )
    except DatabaseError:
        # Re-raise DatabaseError as-is
        raise
    except Exception as e:
        raise DatabaseError(
            message=f"Failed to create tables: {str(e)}",
            error_code="TABLE_CREATE_FAILED",
        )


def drop_tables(db_manager: Optional[DatabaseManager] = None) -> None:
    """
    Drop all metocean database tables.

    WARNING: This will permanently delete all data in the metocean tables.
    Use with caution!

    Args:
        db_manager: Optional database manager instance. Uses global if not provided.

    Raises:
        DatabaseError: If table drop fails
    """
    manager = db_manager or get_db_manager()

    try:
        Base.metadata.drop_all(bind=manager.engine)
    except Exception as e:
        raise DatabaseError(
            message=f"Failed to drop tables: {str(e)}",
            error_code="TABLE_DROP_FAILED",
        )


def drop_schema(
    db_manager: Optional[DatabaseManager] = None, cascade: bool = False
) -> None:
    """
    Drop the metocean database schema.

    WARNING: If cascade=True, this will permanently delete all data
    and objects in the schema. Use with extreme caution!

    Args:
        db_manager: Optional database manager instance. Uses global if not provided.
        cascade: If True, drop all objects in the schema. Default False.

    Raises:
        DatabaseError: If schema drop fails
    """
    manager = db_manager or get_db_manager()
    config = get_config().database

    try:
        cascade_clause = "CASCADE" if cascade else ""
        with manager.engine.connect() as conn:
            conn.execute(
                text(f"DROP SCHEMA IF EXISTS {config.schema} {cascade_clause}")
            )
            conn.commit()
    except Exception as e:
        raise DatabaseError(
            message=f"Failed to drop schema '{config.schema}': {str(e)}",
            error_code="SCHEMA_DROP_FAILED",
        )


def init_database(db_manager: Optional[DatabaseManager] = None) -> bool:
    """
    Initialize the complete metocean database.

    Creates schema, enum types, and all tables. This is the main
    function to call when setting up a new database.

    Args:
        db_manager: Optional database manager instance. Uses global if not provided.

    Returns:
        bool: True if initialization was successful

    Raises:
        DatabaseError: If initialization fails
    """
    manager = db_manager or get_db_manager()

    # Verify database connection first
    if not manager.check_connection():
        raise DatabaseError(
            message="Cannot connect to database",
            error_code="CONNECTION_FAILED",
        )

    # Create schema, enums, and tables
    create_tables(manager)

    return True


def verify_database(db_manager: Optional[DatabaseManager] = None) -> dict:
    """
    Verify the metocean database structure.

    Checks that all expected tables exist and are accessible.

    Args:
        db_manager: Optional database manager instance. Uses global if not provided.

    Returns:
        dict: Verification results with status for each component

    Example:
        >>> result = verify_database()
        >>> print(result)
        {
            "connection": True,
            "schema": True,
            "tables": {
                "stations": True,
                "observations": True,
                "grid_points": True,
                "forecasts": True,
                "fetch_logs": True
            }
        }
    """
    manager = db_manager or get_db_manager()
    config = get_config().database

    result = {
        "connection": False,
        "schema": False,
        "tables": {},
    }

    # Check connection
    result["connection"] = manager.check_connection()
    if not result["connection"]:
        return result

    # Check schema exists
    try:
        with manager.engine.connect() as conn:
            schema_check = conn.execute(
                text(
                    f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.schemata
                    WHERE schema_name = '{config.schema}'
                )
            """
                )
            )
            result["schema"] = schema_check.scalar()
    except Exception:
        result["schema"] = False

    if not result["schema"]:
        return result

    # Check tables exist
    expected_tables = [
        "stations",
        "observations",
        "grid_points",
        "forecasts",
        "fetch_logs",
    ]
    try:
        with manager.engine.connect() as conn:
            for table_name in expected_tables:
                table_check = conn.execute(
                    text(
                        f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = '{config.schema}'
                        AND table_name = '{table_name}'
                    )
                """
                    )
                )
                result["tables"][table_name] = table_check.scalar()
    except Exception:
        for table_name in expected_tables:
            result["tables"][table_name] = False

    return result
