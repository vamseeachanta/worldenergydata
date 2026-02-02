# ABOUTME: SQLAlchemy ORM models for PHMSA pipeline safety incident database
# ABOUTME: Implements PipelineIncident model covering gas distribution, gas transmission,
# ABOUTME: hazardous liquid, and LNG facility incidents (1986-present)

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PipelineIncident(Base):
    """
    PHMSA pipeline safety incident model.

    Represents incidents reported to the Pipeline and Hazardous Materials
    Safety Administration under 49 CFR 191/195 for pipeline systems
    across the United States.

    Report Types:
        - gas_distribution: Local distribution pipelines (PHMSA Form 7100.1)
        - gas_transmission: Interstate/intrastate transmission and gathering (Form 7100.2)
        - hazardous_liquid: Crude oil, refined products, chemical pipelines (Form 7000-1)
        - lng: Liquefied natural gas facilities (Form 7100.3)

    Data Coverage:
        - Gas Distribution: 1986-present (~4,864 incidents)
        - Gas Transmission/Gathering: 1986-present (~4,260 incidents)
        - Hazardous Liquid: 1986-present (~11,831 incidents)
        - LNG Facilities: 2011-present (~48 incidents)
    """

    __tablename__ = "pipeline_incidents"

    # Primary key
    id = Column(Integer, primary_key=True)

    # PHMSA identification
    report_number = Column(String(50), unique=True, nullable=False, index=True)
    supplemental_number = Column(String(50))
    report_type = Column(String(50), nullable=False, index=True)

    # Operator information
    operator_name = Column(String(300), nullable=False, index=True)
    operator_id = Column(String(50), index=True)

    # Temporal fields
    incident_date = Column(DateTime, nullable=False, index=True)
    incident_time = Column(String(20))

    # Geographic location
    state = Column(String(50), index=True)
    county = Column(String(100))
    city = Column(String(100))
    location_description = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)

    # Pipeline characteristics
    pipeline_type = Column(String(50), index=True)
    pipeline_diameter = Column(Float)
    pipeline_material = Column(String(100))

    # Release information
    commodity_released = Column(String(200))
    estimated_quantity_released = Column(Float)
    unit_of_measure = Column(String(50))

    # Incident characteristics
    ignition = Column(Boolean)
    explosion = Column(Boolean)

    # Consequences
    fatalities = Column(Integer, default=0)
    injuries = Column(Integer, default=0)

    # Financial impact
    estimated_property_damage = Column(Float)
    estimated_cost_of_commodity_lost = Column(Float)

    # Cause analysis
    cause_category = Column(String(200))
    cause_subcategory = Column(String(200))

    # Description
    narrative = Column(Text)

    # Audit timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<PipelineIncident("
            f"id={self.id}, "
            f"report_number='{self.report_number}', "
            f"type='{self.pipeline_type}', "
            f"date='{self.incident_date}', "
            f"operator='{self.operator_name}'"
            f")>"
        )
