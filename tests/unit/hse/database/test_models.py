# ABOUTME: Comprehensive pytest test suite for HSE database models
# ABOUTME: Tests HSEIncident base model and specialized models with TDD methodology

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import FlushError


class TestHSEIncidentBaseModel:
    """Test suite for HSEIncident base model"""

    def test_hse_incident_creation_with_valid_data(self, db_session):
        """Test HSEIncident model creation with all valid required fields"""
        from worldenergydata.hse.database.models import HSEIncident

        incident = HSEIncident(
            bsee_incident_id="INC-2024-001",
            incident_date=datetime(2024, 1, 15, 10, 30),
            operator="Shell Offshore Inc.",
            facility_name="Mars Platform",
            lease_number="G-12345",
            block_number="MC-807",
            field_name="Mars",
            latitude=28.5,
            longitude=-89.2,
            incident_type="injury",
            severity="recordable",
            description="Worker injured during crane operation",
            root_cause="Equipment failure - crane brake malfunction",
            corrective_actions="Replace crane brake system, additional operator training",
            investigation_status="Completed",
        )

        db_session.add(incident)
        db_session.commit()

        assert incident.id is not None
        assert incident.bsee_incident_id == "INC-2024-001"
        assert incident.operator == "Shell Offshore Inc."
        assert incident.facility_name == "Mars Platform"
        assert incident.incident_type == "injury"
        assert incident.severity == "recordable"
        assert incident.latitude == 28.5
        assert incident.longitude == -89.2
        assert incident.created_at is not None

    def test_hse_incident_required_bsee_id(self, db_session):
        """Test that bsee_incident_id is required (NOT NULL constraint)"""
        from worldenergydata.hse.database.models import HSEIncident

        incident = HSEIncident(
            # Missing bsee_incident_id (required)
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )

        db_session.add(incident)
        with pytest.raises((IntegrityError, FlushError)):
            db_session.commit()

    def test_hse_incident_required_incident_date(self, db_session):
        """Test that incident_date is required (NOT NULL constraint)"""
        from worldenergydata.hse.database.models import HSEIncident

        incident = HSEIncident(
            bsee_incident_id="INC-2024-002",
            # Missing incident_date (required)
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )

        db_session.add(incident)
        with pytest.raises((IntegrityError, FlushError)):
            db_session.commit()

    def test_hse_incident_required_operator(self, db_session):
        """Test that operator is required (NOT NULL constraint)"""
        from worldenergydata.hse.database.models import HSEIncident

        incident = HSEIncident(
            bsee_incident_id="INC-2024-003",
            incident_date=datetime(2024, 1, 15),
            # Missing operator (required)
            incident_type="injury",
            severity="recordable",
        )

        db_session.add(incident)
        with pytest.raises((IntegrityError, FlushError)):
            db_session.commit()

    def test_hse_incident_unique_bsee_id(self, db_session):
        """Test that bsee_incident_id must be unique"""
        from worldenergydata.hse.database.models import HSEIncident

        # Create first incident
        incident1 = HSEIncident(
            bsee_incident_id="INC-2024-004",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )
        db_session.add(incident1)
        db_session.commit()

        # Try to create second incident with same bsee_incident_id
        incident2 = HSEIncident(
            bsee_incident_id="INC-2024-004",  # Duplicate
            incident_date=datetime(2024, 1, 16),
            operator="BP Exploration",
            incident_type="spill",
            severity="minor",
        )
        db_session.add(incident2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_hse_incident_type_enum_valid_values(self, db_session):
        """Test all valid incident_type enum values"""
        from worldenergydata.hse.database.models import HSEIncident

        valid_types = ["injury", "spill", "equipment_failure", "violation"]

        for idx, incident_type in enumerate(valid_types):
            incident = HSEIncident(
                bsee_incident_id=f"INC-TYPE-{idx}",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type=incident_type,
                severity="recordable",
            )
            db_session.add(incident)
            db_session.commit()

            assert incident.incident_type == incident_type
            db_session.rollback()

    @pytest.mark.skip(
        reason="SQLite does not enforce Enum constraints; requires PostgreSQL or MySQL"
    )
    def test_hse_incident_type_enum_invalid_value(self, db_session):
        """Test that invalid incident_type raises error"""
        from worldenergydata.hse.database.models import HSEIncident

        with pytest.raises((ValueError, IntegrityError)):
            incident = HSEIncident(
                bsee_incident_id="INC-TYPE-INVALID",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="invalid_type",  # Not in enum
                severity="recordable",
            )
            db_session.add(incident)
            db_session.commit()

    def test_hse_incident_severity_enum_valid_values(self, db_session):
        """Test all valid severity enum values"""
        from worldenergydata.hse.database.models import HSEIncident

        valid_severities = ["fatality", "lost_time", "recordable", "near_miss", "minor"]

        for idx, severity in enumerate(valid_severities):
            incident = HSEIncident(
                bsee_incident_id=f"INC-SEV-{idx}",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity=severity,
            )
            db_session.add(incident)
            db_session.commit()

            assert incident.severity == severity
            db_session.rollback()

    @pytest.mark.skip(
        reason="SQLite does not enforce Enum constraints; requires PostgreSQL or MySQL"
    )
    def test_hse_incident_severity_enum_invalid_value(self, db_session):
        """Test that invalid severity raises error"""
        from worldenergydata.hse.database.models import HSEIncident

        with pytest.raises((ValueError, IntegrityError)):
            incident = HSEIncident(
                bsee_incident_id="INC-SEV-INVALID",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="invalid_severity",  # Not in enum
            )
            db_session.add(incident)
            db_session.commit()

    def test_hse_incident_latitude_valid_gom_range(self, db_session):
        """Test valid latitude within Gulf of Mexico range (18-31°N)"""
        from worldenergydata.hse.database.models import HSEIncident

        valid_latitudes = [18.0, 25.5, 28.0, 30.5, 31.0]

        for idx, lat in enumerate(valid_latitudes):
            incident = HSEIncident(
                bsee_incident_id=f"INC-LAT-{idx}",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="recordable",
                latitude=lat,
                longitude=-89.0,
            )
            db_session.add(incident)
            db_session.commit()

            assert incident.latitude == lat
            db_session.rollback()

    def test_hse_incident_latitude_invalid_below_range(self, db_session):
        """Test that latitude below GOM range (< 18°N) raises validation error"""
        from worldenergydata.hse.database.models import HSEIncident

        with pytest.raises((ValueError, IntegrityError)):
            incident = HSEIncident(
                bsee_incident_id="INC-LAT-LOW",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="recordable",
                latitude=15.0,  # Below GOM range
                longitude=-89.0,
            )
            db_session.add(incident)
            db_session.commit()

    def test_hse_incident_latitude_invalid_above_range(self, db_session):
        """Test that latitude above GOM range (> 31°N) raises validation error"""
        from worldenergydata.hse.database.models import HSEIncident

        with pytest.raises((ValueError, IntegrityError)):
            incident = HSEIncident(
                bsee_incident_id="INC-LAT-HIGH",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="recordable",
                latitude=35.0,  # Above GOM range
                longitude=-89.0,
            )
            db_session.add(incident)
            db_session.commit()

    def test_hse_incident_longitude_valid_gom_range(self, db_session):
        """Test valid longitude within Gulf of Mexico range (-98 to -80°W)"""
        from worldenergydata.hse.database.models import HSEIncident

        valid_longitudes = [-98.0, -94.5, -89.0, -85.0, -80.0]

        for idx, lon in enumerate(valid_longitudes):
            incident = HSEIncident(
                bsee_incident_id=f"INC-LON-{idx}",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="recordable",
                latitude=28.0,
                longitude=lon,
            )
            db_session.add(incident)
            db_session.commit()

            assert incident.longitude == lon
            db_session.rollback()

    def test_hse_incident_longitude_invalid_west_of_range(self, db_session):
        """Test that longitude west of GOM range (< -98°W) raises validation error"""
        from worldenergydata.hse.database.models import HSEIncident

        with pytest.raises((ValueError, IntegrityError)):
            incident = HSEIncident(
                bsee_incident_id="INC-LON-WEST",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="recordable",
                latitude=28.0,
                longitude=-105.0,  # West of GOM range
            )
            db_session.add(incident)
            db_session.commit()

    def test_hse_incident_longitude_invalid_east_of_range(self, db_session):
        """Test that longitude east of GOM range (> -80°W) raises validation error"""
        from worldenergydata.hse.database.models import HSEIncident

        with pytest.raises((ValueError, IntegrityError)):
            incident = HSEIncident(
                bsee_incident_id="INC-LON-EAST",
                incident_date=datetime(2024, 1, 15),
                operator="Shell Offshore Inc.",
                incident_type="injury",
                severity="recordable",
                latitude=28.0,
                longitude=-75.0,  # East of GOM range
            )
            db_session.add(incident)
            db_session.commit()

    def test_hse_incident_optional_fields_can_be_null(self, db_session):
        """Test that optional fields can be NULL"""
        from worldenergydata.hse.database.models import HSEIncident

        incident = HSEIncident(
            bsee_incident_id="INC-OPTIONAL",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
            # All other fields omitted (should default to NULL)
        )

        db_session.add(incident)
        db_session.commit()

        assert incident.facility_name is None
        assert incident.lease_number is None
        assert incident.block_number is None
        assert incident.field_name is None
        assert incident.latitude is None
        assert incident.longitude is None
        assert incident.description is None
        assert incident.root_cause is None
        assert incident.corrective_actions is None
        assert incident.investigation_status is None

    def test_hse_incident_timestamps_auto_populated(self, db_session):
        """Test that created_at and updated_at timestamps are automatically populated"""
        from worldenergydata.hse.database.models import HSEIncident

        incident = HSEIncident(
            bsee_incident_id="INC-TIMESTAMP",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )

        db_session.add(incident)
        db_session.commit()

        assert incident.created_at is not None
        assert isinstance(incident.created_at, datetime)

        # updated_at should be None initially (only set on update)
        assert incident.updated_at is None

    def test_hse_incident_updated_at_on_modification(self, db_session):
        """Test that updated_at timestamp is set when incident is modified"""
        import time

        from worldenergydata.hse.database.models import HSEIncident

        incident = HSEIncident(
            bsee_incident_id="INC-UPDATE",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )

        db_session.add(incident)
        db_session.commit()

        original_created_at = incident.created_at
        assert incident.updated_at is None

        # Wait briefly to ensure timestamp difference
        time.sleep(0.1)

        # Modify incident
        incident.description = "Updated description after investigation"
        db_session.commit()

        assert incident.updated_at is not None
        assert isinstance(incident.updated_at, datetime)
        assert incident.updated_at > original_created_at
        assert (
            incident.created_at == original_created_at
        )  # created_at should not change


class TestInjuryIncidentModel:
    """Test suite for InjuryIncident specialized model"""

    def test_injury_incident_creation_with_valid_data(self, db_session):
        """Test InjuryIncident creation with all required fields"""
        from worldenergydata.hse.database.models import (
            HSEIncident,
            InjuryIncident,
        )

        # Create base HSEIncident first
        base_incident = HSEIncident(
            bsee_incident_id="INJ-2024-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="lost_time",
        )
        db_session.add(base_incident)
        db_session.commit()

        # Create specialized InjuryIncident
        injury = InjuryIncident(
            hse_incident_id=base_incident.id,
            injured_person_name="John Doe",
            job_title="Crane Operator",
            injury_type="Crush injury to hand",
            body_part_affected="Right hand",
            days_away_from_work=15,
            days_restricted_duty=10,
            medical_treatment="Surgery, physical therapy",
        )

        db_session.add(injury)
        db_session.commit()

        assert injury.id is not None
        assert injury.hse_incident_id == base_incident.id
        assert injury.injured_person_name == "John Doe"
        assert injury.days_away_from_work == 15
        assert injury.days_restricted_duty == 10

    def test_injury_incident_relationship_to_hse_incident(self, db_session):
        """Test foreign key relationship between InjuryIncident and HSEIncident"""
        from worldenergydata.hse.database.models import (
            HSEIncident,
            InjuryIncident,
        )

        base_incident = HSEIncident(
            bsee_incident_id="INJ-REL-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="injury",
            severity="recordable",
        )
        db_session.add(base_incident)
        db_session.commit()

        injury = InjuryIncident(
            hse_incident_id=base_incident.id,
            injury_type="Minor burn",
            body_part_affected="Left arm",
        )
        db_session.add(injury)
        db_session.commit()

        # Test relationship access
        assert injury.hse_incident == base_incident
        assert base_incident.injury_incident == injury


class TestSpillIncidentModel:
    """Test suite for SpillIncident specialized model"""

    def test_spill_incident_creation_with_valid_data(self, db_session):
        """Test SpillIncident creation with all required fields"""
        from worldenergydata.hse.database.models import (
            HSEIncident,
            SpillIncident,
        )

        base_incident = HSEIncident(
            bsee_incident_id="SPILL-2024-001",
            incident_date=datetime(2024, 1, 15),
            operator="BP Exploration",
            incident_type="spill",
            severity="minor",
        )
        db_session.add(base_incident)
        db_session.commit()

        spill = SpillIncident(
            hse_incident_id=base_incident.id,
            substance_spilled="Crude Oil",
            volume_barrels=50.0,
            volume_gallons=2100.0,
            spill_location="Platform deck",
            environmental_impact="Contained on platform, no water contact",
            cleanup_cost=125000.0,
            cleanup_status="Completed",
        )

        db_session.add(spill)
        db_session.commit()

        assert spill.id is not None
        assert spill.volume_barrels == 50.0
        assert spill.volume_gallons == 2100.0
        assert spill.cleanup_cost == 125000.0

    def test_spill_incident_volume_conversion(self, db_session):
        """Test barrel to gallon conversion (1 barrel = 42 gallons)"""
        from worldenergydata.hse.database.models import (
            HSEIncident,
            SpillIncident,
        )

        base_incident = HSEIncident(
            bsee_incident_id="SPILL-CONV-001",
            incident_date=datetime(2024, 1, 15),
            operator="BP Exploration",
            incident_type="spill",
            severity="minor",
        )
        db_session.add(base_incident)
        db_session.commit()

        spill = SpillIncident(
            hse_incident_id=base_incident.id,
            substance_spilled="Crude Oil",
            volume_barrels=10.0,
        )

        # Should have convert_barrels_to_gallons() method
        expected_gallons = 10.0 * 42
        calculated_gallons = spill.convert_barrels_to_gallons()

        assert calculated_gallons == expected_gallons


class TestViolationIncidentModel:
    """Test suite for ViolationIncident specialized model"""

    def test_violation_incident_creation_with_valid_data(self, db_session):
        """Test ViolationIncident creation with all required fields"""
        from worldenergydata.hse.database.models import (
            HSEIncident,
            ViolationIncident,
        )

        base_incident = HSEIncident(
            bsee_incident_id="VIOL-2024-001",
            incident_date=datetime(2024, 1, 15),
            operator="Chevron USA Inc.",
            incident_type="violation",
            severity="recordable",
        )
        db_session.add(base_incident)
        db_session.commit()

        violation = ViolationIncident(
            hse_incident_id=base_incident.id,
            inc_number="INC-2024-5678",
            violation_type="Safety System Failure",
            regulation_cited="30 CFR 250.107",
            penalty_amount=45000.0,
            penalty_status="assessed",
            compliance_deadline=datetime(2024, 6, 15),
            compliance_achieved=False,
        )

        db_session.add(violation)
        db_session.commit()

        assert violation.id is not None
        assert violation.inc_number == "INC-2024-5678"
        assert violation.penalty_amount == 45000.0
        assert violation.penalty_status == "assessed"

    def test_violation_penalty_status_enum(self, db_session):
        """Test penalty_status enum constraint"""
        from worldenergydata.hse.database.models import (
            HSEIncident,
            ViolationIncident,
        )

        valid_statuses = ["proposed", "assessed", "paid", "appealed"]

        for idx, status in enumerate(valid_statuses):
            base_incident = HSEIncident(
                bsee_incident_id=f"VIOL-STAT-{idx}",
                incident_date=datetime(2024, 1, 15),
                operator="Chevron USA Inc.",
                incident_type="violation",
                severity="recordable",
            )
            db_session.add(base_incident)
            db_session.commit()

            violation = ViolationIncident(
                hse_incident_id=base_incident.id,
                violation_type="Safety System Failure",
                penalty_amount=10000.0,
                penalty_status=status,
            )
            db_session.add(violation)
            db_session.commit()

            assert violation.penalty_status == status
            db_session.rollback()


class TestEquipmentFailureModel:
    """Test suite for EquipmentFailure specialized model"""

    def test_equipment_failure_creation_with_valid_data(self, db_session):
        """Test EquipmentFailure creation with all required fields"""
        from worldenergydata.hse.database.models import (
            EquipmentFailure,
            HSEIncident,
        )

        base_incident = HSEIncident(
            bsee_incident_id="EQUIP-2024-001",
            incident_date=datetime(2024, 1, 15),
            operator="Shell Offshore Inc.",
            incident_type="equipment_failure",
            severity="near_miss",
        )
        db_session.add(base_incident)
        db_session.commit()

        failure = EquipmentFailure(
            hse_incident_id=base_incident.id,
            equipment_type="BOP",
            equipment_description="Annular Blowout Preventer",
            failure_mode="External Leak",
            failure_cause="Seal degradation",
            downtime_hours=48.0,
            repair_cost=250000.0,
            preventive_actions="Implement more frequent seal inspections",
        )

        db_session.add(failure)
        db_session.commit()

        assert failure.id is not None
        assert failure.equipment_type == "BOP"
        assert failure.failure_mode == "External Leak"
        assert failure.downtime_hours == 48.0
        assert failure.repair_cost == 250000.0


# Pytest fixtures for database session
@pytest.fixture
def db_session():
    """Create test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from worldenergydata.hse.database.models import Base

    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
