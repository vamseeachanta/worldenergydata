# ABOUTME: Database manager for the metocean module.
# ABOUTME: Provides sync and async database connections with session management.

"""
Database Manager for Metocean Module

Handles database connections, sessions, and basic operations.
Supports both synchronous and asynchronous operations.
"""

from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Generator, Optional, TypeVar

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from worldenergydata.metocean.config import get_config
from worldenergydata.metocean.database.models import Base
from worldenergydata.metocean.exceptions import ConnectionError as DBConnectionError
from worldenergydata.metocean.exceptions import (
    DatabaseError,
    QueryError,
)

T = TypeVar("T", bound=Base)


class DatabaseManager:
    """
    Manages database connections and sessions.

    Supports both synchronous and asynchronous operations with
    connection pooling and automatic schema selection.
    """

    def __init__(self) -> None:
        """Initialize database manager with configuration."""
        self.config = get_config().database
        self._engine: Optional[Any] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[async_sessionmaker] = None

    def _create_engine(self) -> Any:
        """Create synchronous SQLAlchemy engine."""
        try:
            engine = create_engine(
                self.config.url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                echo=self.config.echo,
            )

            # Set search path to include metocean schema
            @event.listens_for(engine, "connect")
            def set_search_path(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute(f"SET search_path TO {self.config.schema}, public")
                cursor.close()

            return engine
        except Exception as e:
            raise DBConnectionError(
                message=f"Failed to create database engine: {str(e)}",
                error_code="ENGINE_CREATE_FAILED",
            )

    def _create_async_engine(self) -> AsyncEngine:
        """Create asynchronous SQLAlchemy engine."""
        try:
            engine = create_async_engine(
                self.config.async_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                echo=self.config.echo,
            )

            # Set search path for async connections
            @event.listens_for(engine.sync_engine, "connect")
            def set_search_path(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute(f"SET search_path TO {self.config.schema}, public")
                cursor.close()

            return engine
        except Exception as e:
            raise DBConnectionError(
                message=f"Failed to create async database engine: {str(e)}",
                error_code="ASYNC_ENGINE_CREATE_FAILED",
            )

    @property
    def engine(self) -> Any:
        """Get or create synchronous engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def async_engine(self) -> AsyncEngine:
        """Get or create asynchronous engine."""
        if self._async_engine is None:
            self._async_engine = self._create_async_engine()
        return self._async_engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create synchronous session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                class_=Session,
                expire_on_commit=False,
            )
        return self._session_factory

    @property
    def async_session_factory(self) -> async_sessionmaker:
        """Get or create asynchronous session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._async_session_factory

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for synchronous database sessions.

        Yields:
            Session: SQLAlchemy session

        Example:
            with db_manager.session() as session:
                stations = session.query(Station).all()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise QueryError(
                message=f"Database operation failed: {str(e)}",
                error_code="SESSION_ERROR",
            )
        finally:
            session.close()

    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager for database sessions.

        Yields:
            AsyncSession: SQLAlchemy async session

        Example:
            async with db_manager.async_session() as session:
                result = await session.execute(select(Station))
                stations = result.scalars().all()
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise QueryError(
                message=f"Async database operation failed: {str(e)}",
                error_code="ASYNC_SESSION_ERROR",
            )
        finally:
            await session.close()

    def create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.config.schema}"))
                conn.commit()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create schema: {str(e)}",
                error_code="SCHEMA_CREATE_FAILED",
            )

    def create_enum_types(self) -> None:
        """Create PostgreSQL ENUM types for metocean module."""
        try:
            with self.engine.connect() as conn:
                # Create DataSource enum
                conn.execute(
                    text(
                        f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_type t
                            JOIN pg_namespace n ON n.oid = t.typnamespace
                            WHERE t.typname = 'data_source_enum'
                            AND n.nspname = '{self.config.schema}'
                        ) THEN
                            CREATE TYPE {self.config.schema}.data_source_enum AS ENUM (
                                'ndbc', 'coops', 'open_meteo', 'cmems', 'hycom',
                                'nws', 'ecmwf', 'gfs', 'other'
                            );
                        END IF;
                    END
                    $$;
                """
                    )
                )

                # Create StationType enum
                conn.execute(
                    text(
                        f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_type t
                            JOIN pg_namespace n ON n.oid = t.typnamespace
                            WHERE t.typname = 'station_type_enum'
                            AND n.nspname = '{self.config.schema}'
                        ) THEN
                            CREATE TYPE {self.config.schema}.station_type_enum AS ENUM (
                                'buoy', 'cman', 'dart', 'ship', 'oil_platform',
                                'tide_gauge', 'current_meter', 'weather_station',
                                'drifter', 'argo', 'glider', 'hf_radar',
                                'satellite', 'model_grid', 'other'
                            );
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

    def create_tables(self) -> None:
        """Create all tables defined in models."""
        try:
            self.create_schema()
            self.create_enum_types()
            Base.metadata.create_all(
                bind=self.engine,
                checkfirst=True,
            )
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create tables: {str(e)}",
                error_code="TABLE_CREATE_FAILED",
            )

    def drop_tables(self) -> None:
        """Drop all tables (use with caution!)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to drop tables: {str(e)}",
                error_code="TABLE_DROP_FAILED",
            )

    def check_connection(self) -> bool:
        """
        Check if database connection is working.

        Returns:
            bool: True if connection is successful
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def async_check_connection(self) -> bool:
        """
        Async check if database connection is working.

        Returns:
            bool: True if connection is successful
        """
        try:
            async with self.async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close all database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._session_factory:
            self._session_factory = None

    async def async_close(self) -> None:
        """Close all async database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
        if self._async_session_factory:
            self._async_session_factory = None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get or create the global database manager instance.

    Returns:
        DatabaseManager: The global database manager
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def reset_db_manager() -> None:
    """Reset the global database manager instance."""
    global _db_manager
    if _db_manager is not None:
        _db_manager.close()
        _db_manager = None


# Convenience functions for common operations
@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session (convenience function)."""
    with get_db_manager().session() as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session (convenience function)."""
    async with get_db_manager().async_session() as session:
        yield session
