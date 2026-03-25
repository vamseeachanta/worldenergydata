"""
SQLAlchemy Database Models for Marine Safety Module

Defines all database models following the optimized schema with proper
relationships, indexes, and constraints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
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

from worldenergydata.marine_safety import constants


class Base(DeclarativeBase):
    """Base class for all models"""

    pass


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )


class Company(Base, TimestampMixin):
    """Company/Operator entity"""

    __tablename__ = "companies"
    __table_args__ = (
        Index("idx_company_name_trgm", "company_name", postgresql_using="gin"),
    )

    company_id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    company_type: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    vessels: Mapped[List["Vessel"]] = relationship(
        "Vessel", back_populates="company", cascade="all, delete-orphan"
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="company", cascade="all, delete-orphan"
    )


class Vessel(Base, TimestampMixin):
    """Vessel/Platform entity"""

    __tablename__ = "vessels"
    __table_args__ = (
        Index("idx_vessel_name_trgm", "vessel_name", postgresql_using="gin"),
        Index("idx_vessel_imo", "imo_number"),
        Index("idx_vessel_type", "vessel_type"),
    )

    vessel_id: Mapped[int] = mapped_column(primary_key=True)
    vessel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vessel_type: Mapped[str] = mapped_column(
        PgEnum(constants.VesselType, name="vessel_type_enum", schema="marine_safety"),
        nullable=False,
    )
    imo_number: Mapped[Optional[str]] = mapped_column(String(10), unique=True)
    flag_state: Mapped[Optional[str]] = mapped_column(String(5))
    year_built: Mapped[Optional[int]] = mapped_column(Integer)
    gross_tonnage: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.company_id", ondelete="SET NULL"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    company: Mapped[Optional["Company"]] = relationship(
        "Company", back_populates="vessels"
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="vessel", cascade="all, delete-orphan"
    )


class Location(Base):
    """Geographic location entity"""

    __tablename__ = "locations"
    __table_args__ = (
        Index("idx_location_coords", "latitude", "longitude"),
        Index("idx_location_region", "region_code"),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name="check_latitude_range"
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name="check_longitude_range"
        ),
    )

    location_id: Mapped[int] = mapped_column(primary_key=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(500))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 7))
    water_depth_meters: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    region_code: Mapped[Optional[str]] = mapped_column(String(10))
    country_code: Mapped[Optional[str]] = mapped_column(String(5))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="location", cascade="all, delete-orphan"
    )


class Incident(Base, TimestampMixin):
    """Main incident entity"""

    __tablename__ = "incidents"
    __table_args__ = (
        Index("idx_incident_date", "incident_date"),
        Index("idx_incident_type", "incident_type"),
        Index("idx_incident_severity", "severity_level"),
        Index("idx_incident_source", "source_agency"),
        Index("idx_incident_status", "status"),
        Index("idx_incident_vessel", "vessel_id"),
        Index("idx_incident_company", "company_id"),
        Index("idx_incident_location", "location_id"),
        Index(
            "idx_incident_composite", "incident_date", "source_agency", "incident_type"
        ),
        UniqueConstraint(
            "source_agency", "source_incident_id", name="uq_source_incident"
        ),
    )

    incident_id: Mapped[int] = mapped_column(primary_key=True)
    source_agency: Mapped[str] = mapped_column(
        PgEnum(constants.DataSource, name="data_source_enum", schema="marine_safety"),
        nullable=False,
    )
    source_incident_id: Mapped[str] = mapped_column(String(100), nullable=False)
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    incident_type: Mapped[str] = mapped_column(
        PgEnum(
            constants.IncidentType, name="incident_type_enum", schema="marine_safety"
        ),
        nullable=False,
    )
    severity_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=constants.DEFAULT_SEVERITY
    )
    status: Mapped[str] = mapped_column(
        PgEnum(
            constants.IncidentStatus,
            name="incident_status_enum",
            schema="marine_safety",
        ),
        nullable=False,
        default=constants.DEFAULT_STATUS,
    )
    title: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Foreign keys
    vessel_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vessels.vessel_id", ondelete="SET NULL"), index=True
    )
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.company_id", ondelete="SET NULL"), index=True
    )
    location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.location_id", ondelete="SET NULL"), index=True
    )

    # Impact data
    fatalities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    injuries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_persons: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    environmental_impact: Mapped[Optional[str]] = mapped_column(Text)
    estimated_damage_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    # Weather data
    weather_condition: Mapped[Optional[str]] = mapped_column(
        PgEnum(
            constants.WeatherCondition,
            name="weather_condition_enum",
            schema="marine_safety",
        )
    )
    wind_speed_knots: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    wave_height_meters: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    sea_state: Mapped[Optional[int]] = mapped_column(Integer)
    visibility_meters: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))

    # Investigation data
    investigation_status: Mapped[Optional[str]] = mapped_column(String(100))
    investigation_priority: Mapped[Optional[str]] = mapped_column(
        PgEnum(
            constants.InvestigationPriority,
            name="investigation_priority_enum",
            schema="marine_safety",
        )
    )

    # Data quality
    data_quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    data_quality_flags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    last_verified_date: Mapped[Optional[date]] = mapped_column(Date)

    # Metadata
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    vessel: Mapped[Optional["Vessel"]] = relationship(
        "Vessel", back_populates="incidents"
    )
    company: Mapped[Optional["Company"]] = relationship(
        "Company", back_populates="incidents"
    )
    location: Mapped[Optional["Location"]] = relationship(
        "Location", back_populates="incidents"
    )
    causes: Mapped[List["IncidentCause"]] = relationship(
        "IncidentCause", back_populates="incident", cascade="all, delete-orphan"
    )
    documents: Mapped[List["IncidentDocument"]] = relationship(
        "IncidentDocument", back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentCause(Base):
    """Incident causes (many-to-many relationship)"""

    __tablename__ = "incident_causes"
    __table_args__ = (
        Index("idx_cause_incident", "incident_id"),
        Index("idx_cause_category", "cause_category"),
    )

    cause_id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False
    )
    cause_category: Mapped[str] = mapped_column(
        PgEnum(
            constants.CauseCategory, name="cause_category_enum", schema="marine_safety"
        ),
        nullable=False,
    )
    cause_description: Mapped[Optional[str]] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contributing_factor: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="causes")


class IncidentDocument(Base, TimestampMixin):
    """Documents related to incidents"""

    __tablename__ = "incident_documents"
    __table_args__ = (
        Index("idx_document_incident", "incident_id"),
        Index("idx_document_type", "document_type"),
        UniqueConstraint("incident_id", "document_url", name="uq_incident_document"),
    )

    document_id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_title: Mapped[Optional[str]] = mapped_column(String(500))
    document_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    local_file_path: Mapped[Optional[str]] = mapped_column(String(1024))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    publication_date: Mapped[Optional[date]] = mapped_column(Date)
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    download_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="documents")


class ScrapeLog(Base):
    """Logging table for scraping operations"""

    __tablename__ = "scrape_logs"
    __table_args__ = (
        Index("idx_scrape_source", "source_agency"),
        Index("idx_scrape_timestamp", "scrape_timestamp"),
        Index("idx_scrape_status", "status"),
    )

    scrape_id: Mapped[int] = mapped_column(primary_key=True)
    source_agency: Mapped[str] = mapped_column(
        PgEnum(constants.DataSource, name="data_source_enum", schema="marine_safety"),
        nullable=False,
    )
    scrape_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    records_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    execution_time_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)


class IncidentLink(Base, TimestampMixin):
    """
    Links between potentially related incidents across data sources.

    Used by the cross-source correlation engine to track duplicate or
    related incident records from different agencies.
    """

    __tablename__ = "incident_links"
    __table_args__ = (
        Index("idx_link_incident_1", "incident_id_1"),
        Index("idx_link_incident_2", "incident_id_2"),
        Index("idx_link_confidence", "confidence_score"),
        Index("idx_link_type", "match_type"),
        Index("idx_link_verified", "verified"),
        UniqueConstraint(
            "incident_id_1", "incident_id_2", name="uq_incident_link_pair"
        ),
        CheckConstraint(
            "confidence_score >= 0.00 AND confidence_score <= 1.00",
            name="check_confidence_range",
        ),
        CheckConstraint("incident_id_1 < incident_id_2", name="check_link_ordering"),
    )

    link_id: Mapped[int] = mapped_column(primary_key=True)
    incident_id_1: Mapped[int] = mapped_column(
        ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False
    )
    incident_id_2: Mapped[int] = mapped_column(
        ForeignKey("incidents.incident_id", ondelete="CASCADE"), nullable=False
    )
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    match_type: Mapped[str] = mapped_column(String(50), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationships
    incident_1: Mapped["Incident"] = relationship(
        "Incident", foreign_keys=[incident_id_1], backref="links_as_first"
    )
    incident_2: Mapped["Incident"] = relationship(
        "Incident", foreign_keys=[incident_id_2], backref="links_as_second"
    )
