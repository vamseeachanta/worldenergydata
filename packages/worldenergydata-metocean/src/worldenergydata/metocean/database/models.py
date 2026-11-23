# ABOUTME: SQLAlchemy database models for the metocean module.
# ABOUTME: Defines Station, Observation, GridPoint, Forecast, and FetchLog tables.

"""
SQLAlchemy Database Models for Metocean Module

Defines all database models following SQLAlchemy 2.0+ declarative style
with proper relationships, indexes, and constraints.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from worldenergydata.metocean import constants


class Base(DeclarativeBase):
    """Base class for all metocean models."""

    pass


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )


class Station(Base, TimestampMixin):
    """
    Measurement station/buoy metadata.

    Stores information about NDBC buoys, CO-OPS tide gauges,
    and other observation platforms.
    """

    __tablename__ = "stations"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_station_id",
            name="uq_station_source_id",
        ),
        Index("idx_station_coords", "latitude", "longitude"),
        Index("idx_station_type", "station_type"),
        Index("idx_station_active", "is_active"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="check_station_latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="check_station_longitude_range",
        ),
        {"schema": "metocean"},
    )

    station_id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(
        PgEnum(
            constants.DataSource,
            name="data_source_enum",
            schema="metocean",
            create_type=False,
        ),
        nullable=False,
    )
    source_station_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Station ID from source (e.g., NDBC '41001')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Station name/description",
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    water_depth_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Water depth at station in meters",
    )
    station_type: Mapped[str] = mapped_column(
        PgEnum(
            constants.StationType,
            name="station_type_enum",
            schema="metocean",
            create_type=False,
        ),
        nullable=False,
        default=constants.StationType.BUOY,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether station is currently active",
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional station metadata",
    )

    # Relationships
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="station",
        cascade="all, delete-orphan",
    )
    forecasts: Mapped[List["Forecast"]] = relationship(
        "Forecast",
        back_populates="station",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Station(station_id={self.station_id}, "
            f"source={self.source}, "
            f"source_station_id='{self.source_station_id}', "
            f"name='{self.name}')"
        )


class Observation(Base):
    """
    Time-series observation data from stations.

    Single table approach storing all metocean parameters with nullable columns.
    This allows efficient storage and retrieval of sparse observation data.
    """

    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint(
            "station_id",
            "observation_time",
            name="uq_observation_station_time",
        ),
        Index("idx_observation_time", "observation_time"),
        Index("idx_observation_source", "source"),
        Index(
            "idx_observation_composite",
            "station_id",
            "observation_time",
            "source",
        ),
        CheckConstraint(
            "wave_height_m IS NULL OR (wave_height_m >= 0 AND wave_height_m <= 30)",
            name="check_wave_height_range",
        ),
        CheckConstraint(
            "wave_period_s IS NULL OR (wave_period_s >= 1 AND wave_period_s <= 30)",
            name="check_wave_period_range",
        ),
        CheckConstraint(
            "wave_direction_deg IS NULL OR "
            "(wave_direction_deg >= 0 AND wave_direction_deg <= 360)",
            name="check_wave_direction_range",
        ),
        CheckConstraint(
            "wind_speed_ms IS NULL OR (wind_speed_ms >= 0 AND wind_speed_ms <= 100)",
            name="check_wind_speed_range",
        ),
        CheckConstraint(
            "wind_direction_deg IS NULL OR "
            "(wind_direction_deg >= 0 AND wind_direction_deg <= 360)",
            name="check_wind_direction_range",
        ),
        CheckConstraint(
            "current_speed_ms IS NULL OR "
            "(current_speed_ms >= 0 AND current_speed_ms <= 5)",
            name="check_current_speed_range",
        ),
        CheckConstraint(
            "current_direction_deg IS NULL OR "
            "(current_direction_deg >= 0 AND current_direction_deg <= 360)",
            name="check_current_direction_range",
        ),
        CheckConstraint(
            "sea_surface_temp_c IS NULL OR "
            "(sea_surface_temp_c >= -2 AND sea_surface_temp_c <= 40)",
            name="check_sst_range",
        ),
        CheckConstraint(
            "pressure_hpa IS NULL OR " "(pressure_hpa >= 870 AND pressure_hpa <= 1084)",
            name="check_pressure_range",
        ),
        {"schema": "metocean"},
    )

    observation_id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(
        ForeignKey("metocean.stations.station_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observation_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        PgEnum(
            constants.DataSource,
            name="data_source_enum",
            schema="metocean",
            create_type=False,
        ),
        nullable=False,
    )

    # Wave parameters
    wave_height_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Significant wave height in meters",
    )
    wave_period_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Dominant wave period in seconds",
    )
    wave_direction_deg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Mean wave direction in degrees (0-360)",
    )

    # Wind parameters
    wind_speed_ms: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Wind speed in meters per second",
    )
    wind_direction_deg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Wind direction in degrees (0-360)",
    )
    wind_gust_ms: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Wind gust speed in meters per second",
    )

    # Current parameters
    current_speed_ms: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3),
        nullable=True,
        comment="Current speed in meters per second",
    )
    current_direction_deg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Current direction in degrees (0-360)",
    )

    # Temperature and atmospheric
    sea_surface_temp_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Sea surface temperature in Celsius",
    )
    water_level_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3),
        nullable=True,
        comment="Water level relative to datum in meters",
    )
    pressure_hpa: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(7, 2),
        nullable=True,
        comment="Atmospheric pressure in hectopascals",
    )
    air_temp_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Air temperature in Celsius",
    )

    # Quality control
    quality_flag: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=constants.QualityFlag.NOT_CHECKED,
        comment="Quality control flag (-1=not checked, 0=good, 1=suspect, 2=bad, 9=missing)",
    )
    raw_data_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Raw data from source for reference",
    )

    # Relationship
    station: Mapped["Station"] = relationship(
        "Station",
        back_populates="observations",
    )

    def __repr__(self) -> str:
        return (
            f"Observation(observation_id={self.observation_id}, "
            f"station_id={self.station_id}, "
            f"observation_time={self.observation_time})"
        )


class GridPoint(Base):
    """
    Grid points for model data (CMEMS, HYCOM, etc.).

    Stores the grid coordinates used by ocean models for forecast data.
    """

    __tablename__ = "grid_points"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "latitude",
            "longitude",
            name="uq_gridpoint_source_coords",
        ),
        Index("idx_gridpoint_coords", "latitude", "longitude"),
        Index("idx_gridpoint_source", "source"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="check_gridpoint_latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="check_gridpoint_longitude_range",
        ),
        {"schema": "metocean"},
    )

    grid_point_id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(
        PgEnum(
            constants.DataSource,
            name="data_source_enum",
            schema="metocean",
            create_type=False,
        ),
        nullable=False,
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    depth_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Depth level in meters (for 3D models)",
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional grid point metadata",
    )

    def __repr__(self) -> str:
        return (
            f"GridPoint(grid_point_id={self.grid_point_id}, "
            f"source={self.source}, "
            f"lat={self.latitude}, lon={self.longitude})"
        )


class Forecast(Base):
    """
    Forecast data from model sources.

    Stores forecast predictions with initialization time and valid time
    for tracking forecast skill and data freshness.
    """

    __tablename__ = "forecasts"
    __table_args__ = (
        Index(
            "idx_forecast_composite",
            "source",
            "latitude",
            "longitude",
            "init_time",
            "valid_time",
        ),
        Index("idx_forecast_init_time", "init_time"),
        Index("idx_forecast_valid_time", "valid_time"),
        Index("idx_forecast_station", "station_id"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="check_forecast_latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="check_forecast_longitude_range",
        ),
        CheckConstraint(
            "lead_hours >= 0",
            name="check_forecast_lead_hours_positive",
        ),
        {"schema": "metocean"},
    )

    forecast_id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(
        PgEnum(
            constants.DataSource,
            name="data_source_enum",
            schema="metocean",
            create_type=False,
        ),
        nullable=False,
    )
    station_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("metocean.stations.station_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated station if applicable",
    )
    latitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    longitude: Mapped[Decimal] = mapped_column(
        Numeric(10, 7),
        nullable=False,
    )
    init_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Time when forecast was initialized/issued",
    )
    valid_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Time for which forecast is valid",
    )
    lead_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Forecast lead time in hours",
    )

    # Wave parameters (same as Observation)
    wave_height_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    wave_period_s: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    wave_direction_deg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Wind parameters
    wind_speed_ms: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )
    wind_direction_deg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    wind_gust_ms: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )

    # Current parameters
    current_speed_ms: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    current_direction_deg: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Temperature and atmospheric
    sea_surface_temp_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    water_level_m: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 3),
        nullable=True,
    )
    pressure_hpa: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(7, 2),
        nullable=True,
    )
    air_temp_c: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # Relationship
    station: Mapped[Optional["Station"]] = relationship(
        "Station",
        back_populates="forecasts",
    )

    def __repr__(self) -> str:
        return (
            f"Forecast(forecast_id={self.forecast_id}, "
            f"source={self.source}, "
            f"init_time={self.init_time}, "
            f"valid_time={self.valid_time}, "
            f"lead_hours={self.lead_hours})"
        )


class FetchLog(Base):
    """
    Logging table for data fetch operations.

    Tracks fetch operations for monitoring, debugging, and
    ensuring data freshness.
    """

    __tablename__ = "fetch_logs"
    __table_args__ = (
        Index("idx_fetchlog_source", "source"),
        Index("idx_fetchlog_timestamp", "fetch_timestamp"),
        Index("idx_fetchlog_status", "status"),
        {"schema": "metocean"},
    )

    fetch_id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(
        PgEnum(
            constants.DataSource,
            name="data_source_enum",
            schema="metocean",
            create_type=False,
        ),
        nullable=False,
    )
    fetch_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Fetch status (success, failed, partial, timeout, rate_limited)",
    )
    records_fetched: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of records retrieved from source",
    )
    records_stored: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of records successfully stored",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if fetch failed",
    )
    execution_time_seconds: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Total execution time in seconds",
    )
    parameters_json: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Parameters used for the fetch request",
    )

    def __repr__(self) -> str:
        return (
            f"FetchLog(fetch_id={self.fetch_id}, "
            f"source={self.source}, "
            f"status='{self.status}', "
            f"records_stored={self.records_stored})"
        )
