# ABOUTME: SQLAlchemy ORM models for BSEE HSE (Health, Safety, Environment) incident database
# ABOUTME: Implements base HSEIncident and specialized models for injury, spill, violation, and equipment failure incidents

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class HSEIncident(Base):
    """
    Base HSE incident model for offshore oil & gas safety incidents.

    Represents incidents reported to BSEE (Bureau of Safety and Environmental Enforcement)
    under 30 CFR 250.188 regulations for Gulf of Mexico operations.

    Incident Types:
        - injury: Personnel injuries requiring medical treatment
        - spill: Oil, gas, or chemical spills to environment
        - equipment_failure: Critical equipment failures (BOP, cranes, safety systems)
        - violation: Regulatory violations (Incidents of Non-Compliance)

    Severity Levels:
        - fatality: Incident resulted in death
        - lost_time: Injury requiring time away from work
        - recordable: OSHA recordable injury
        - near_miss: Incident with potential for serious consequences
        - minor: Minor incident with limited impact
    """
    __tablename__ = 'hse_incidents'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Required fields (NOT NULL)
    bsee_incident_id = Column(String(50), unique=True, nullable=False, index=True)
    incident_date = Column(DateTime, nullable=False, index=True)
    operator = Column(String(200), nullable=False, index=True)

    # Optional identification fields
    facility_name = Column(String(200), index=True)
    lease_number = Column(String(50), index=True)
    block_number = Column(String(50))
    field_name = Column(String(100), index=True)

    # Geographic coordinates (Gulf of Mexico boundaries)
    latitude = Column(Float)  # Valid range: 18.0 to 31.0
    longitude = Column(Float)  # Valid range: -98.0 to -80.0

    # Incident classification
    incident_type = Column(
        Enum('injury', 'spill', 'equipment_failure', 'violation', name='incident_type_enum'),
        nullable=False
    )
    severity = Column(
        Enum('fatality', 'lost_time', 'recordable', 'near_miss', 'minor', name='severity_enum'),
        nullable=False
    )

    # Incident details
    description = Column(Text)
    root_cause = Column(Text)
    corrective_actions = Column(Text)
    investigation_status = Column(String(50))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships to specialized models
    injury_incident = relationship("InjuryIncident", back_populates="hse_incident", uselist=False)
    spill_incident = relationship("SpillIncident", back_populates="hse_incident", uselist=False)
    violation_incident = relationship("ViolationIncident", back_populates="hse_incident", uselist=False)
    equipment_failure = relationship("EquipmentFailure", back_populates="hse_incident", uselist=False)

    @validates('latitude')
    def validate_latitude(self, key, value):
        """
        Validate latitude within Gulf of Mexico range (18-31°N).

        Args:
            key: Column name (latitude)
            value: Latitude value to validate

        Returns:
            Validated latitude value

        Raises:
            ValueError: If latitude is outside Gulf of Mexico boundaries
        """
        if value is not None:
            if value < 18.0 or value > 31.0:
                raise ValueError(f"Latitude {value} outside Gulf of Mexico range (18-31°N)")
        return value

    @validates('longitude')
    def validate_longitude(self, key, value):
        """
        Validate longitude within Gulf of Mexico range (-98 to -80°W).

        Args:
            key: Column name (longitude)
            value: Longitude value to validate

        Returns:
            Validated longitude value

        Raises:
            ValueError: If longitude is outside Gulf of Mexico boundaries
        """
        if value is not None:
            if value < -98.0 or value > -80.0:
                raise ValueError(f"Longitude {value} outside Gulf of Mexico range (-98 to -80°W)")
        return value

    def __repr__(self):
        return f"<HSEIncident(id={self.id}, bsee_id='{self.bsee_incident_id}', type='{self.incident_type}', date='{self.incident_date}')>"


class InjuryIncident(Base):
    """
    Injury incident details for personnel injuries.

    Linked to HSEIncident base model via foreign key relationship.
    Tracks injury-specific information including OSHA recordability metrics
    (days away from work, days restricted duty).
    """
    __tablename__ = 'injury_incidents'

    id = Column(Integer, primary_key=True)
    hse_incident_id = Column(Integer, ForeignKey('hse_incidents.id'), nullable=False)

    # Personnel information
    injured_person_name = Column(String(200))
    job_title = Column(String(100))

    # Injury details
    injury_type = Column(String(200))
    body_part_affected = Column(String(100))

    # OSHA recordability metrics
    days_away_from_work = Column(Integer)
    days_restricted_duty = Column(Integer)

    # Medical treatment
    medical_treatment = Column(Text)

    # Relationship to base HSEIncident
    hse_incident = relationship("HSEIncident", back_populates="injury_incident")

    def __repr__(self):
        return f"<InjuryIncident(id={self.id}, hse_incident_id={self.hse_incident_id}, type='{self.injury_type}')>"


class SpillIncident(Base):
    """
    Spill incident details for oil, gas, or chemical spills.

    Linked to HSEIncident base model via foreign key relationship.
    Tracks spill volume (barrels and gallons), substance, environmental impact,
    and cleanup costs.
    """
    __tablename__ = 'spill_incidents'

    id = Column(Integer, primary_key=True)
    hse_incident_id = Column(Integer, ForeignKey('hse_incidents.id'), nullable=False)

    # Substance information
    substance_spilled = Column(String(100))

    # Volume measurements
    volume_barrels = Column(Float)
    volume_gallons = Column(Float)

    # Location and impact
    spill_location = Column(String(200))
    environmental_impact = Column(Text)

    # Cleanup information
    cleanup_cost = Column(Float)
    cleanup_status = Column(String(50))

    # Relationship to base HSEIncident
    hse_incident = relationship("HSEIncident", back_populates="spill_incident")

    def convert_barrels_to_gallons(self):
        """
        Convert barrel volume to gallons (1 barrel = 42 gallons).

        Standard petroleum industry conversion for oil spill volumes.

        Returns:
            float: Volume in gallons, or None if volume_barrels is not set
        """
        if self.volume_barrels is not None:
            return self.volume_barrels * 42
        return None

    def convert_gallons_to_barrels(self):
        """
        Convert gallon volume to barrels (1 barrel = 42 gallons).

        Returns:
            float: Volume in barrels, or None if volume_gallons is not set
        """
        if self.volume_gallons is not None:
            return self.volume_gallons / 42
        return None

    def __repr__(self):
        return f"<SpillIncident(id={self.id}, hse_incident_id={self.hse_incident_id}, substance='{self.substance_spilled}', volume_barrels={self.volume_barrels})>"


class ViolationIncident(Base):
    """
    Violation incident details for regulatory violations (INC - Incidents of Non-Compliance).

    Linked to HSEIncident base model via foreign key relationship.
    Tracks BSEE civil penalties, violation types, regulatory citations,
    and compliance status.

    Penalty Status Values:
        - proposed: Civil penalty proposed by BSEE
        - assessed: Civil penalty formally assessed
        - paid: Civil penalty paid by operator
        - appealed: Civil penalty under appeal
    """
    __tablename__ = 'violation_incidents'

    id = Column(Integer, primary_key=True)
    hse_incident_id = Column(Integer, ForeignKey('hse_incidents.id'), nullable=False)

    # Violation identification
    inc_number = Column(String(50))  # INC (Incident of Non-Compliance) number
    violation_type = Column(String(200))
    regulation_cited = Column(String(100))  # e.g., "30 CFR 250.188"

    # Civil penalty information
    penalty_amount = Column(Float)
    penalty_status = Column(
        Enum('proposed', 'assessed', 'paid', 'appealed', name='penalty_status_enum')
    )

    # Compliance tracking
    compliance_deadline = Column(DateTime)
    compliance_achieved = Column(Boolean)

    # Relationship to base HSEIncident
    hse_incident = relationship("HSEIncident", back_populates="violation_incident")

    def __repr__(self):
        return f"<ViolationIncident(id={self.id}, hse_incident_id={self.hse_incident_id}, inc_number='{self.inc_number}', penalty=${self.penalty_amount})>"


class EquipmentFailure(Base):
    """
    Equipment failure incident details for critical equipment failures.

    Linked to HSEIncident base model via foreign key relationship.
    Tracks equipment type (BOP, cranes, safety systems), failure mode,
    root cause, downtime, and repair costs.

    Common Equipment Types:
        - BOP: Blowout Preventer
        - Crane: Lifting and material handling equipment
        - Fire Detection: Fire and gas detection systems
        - HIPPS: High Integrity Pressure Protection System
        - Safety Valve: Pressure relief and safety valves
    """
    __tablename__ = 'equipment_failures'

    id = Column(Integer, primary_key=True)
    hse_incident_id = Column(Integer, ForeignKey('hse_incidents.id'), nullable=False)

    # Equipment identification
    equipment_type = Column(String(100))
    equipment_description = Column(String(200))

    # Failure analysis
    failure_mode = Column(String(100))
    failure_cause = Column(Text)

    # Impact metrics
    downtime_hours = Column(Float)
    repair_cost = Column(Float)

    # Corrective measures
    preventive_actions = Column(Text)

    # Relationship to base HSEIncident
    hse_incident = relationship("HSEIncident", back_populates="equipment_failure")

    def __repr__(self):
        return f"<EquipmentFailure(id={self.id}, hse_incident_id={self.hse_incident_id}, equipment_type='{self.equipment_type}', failure_mode='{self.failure_mode}')>"
