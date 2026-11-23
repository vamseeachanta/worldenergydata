# ABOUTME: Tests for BSEE HSE database import bridge script
# ABOUTME: Tests validation, import, duplicate detection, and ViolationIncident creation

"""
Tests for scripts/import_bsee_hse_to_db.py

Covers:
- Record validation (required fields, enum values, date types)
- Incident investigation import (INCINV-* records)
- INC violation import with ViolationIncident child records
- Duplicate detection (idempotent imports)
- Composite ID format verification
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project src to path
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))

# Import functions from the bridge script
from import_bsee_hse_to_db import (
    import_incinv_records,
    import_incs_records,
    load_existing_ids,
    validate_record,
)

from worldenergydata.hse.database.models import (
    Base,
    HSEIncident,
    ViolationIncident,
)


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_incinv_record():
    """Sample incident investigation record matching BSEEIncInvImporter output."""
    return {
        "bsee_incident_id": "INCINV-20091219-G15610-0",
        "incident_date": datetime(2009, 12, 19, 8, 5),
        "operator": "BSEE Reported",
        "lease_number": "G15610",
        "block_number": "GC 782",
        "incident_type": "spill",
        "severity": "minor",
        "description": "Accident type: pollution; District: DISTRICT; Area/Block: GC 782",
        "investigation_status": "Complete",
    }


@pytest.fixture
def sample_inc_record():
    """Sample INC violation record matching BSEEINCSImporter output."""
    return {
        "bsee_incident_id": "INC-20200821-03295-COMP_SHUTIN-0",
        "incident_date": datetime(2020, 8, 21, 14, 12, 53),
        "operator": "Fieldwood Energy LLC",
        "incident_type": "violation",
        "severity": "minor",
        "description": (
            "Component Shut-in INC: 1 incident(s); "
            "Region: Gulf of Mexico; Operator code: 03295"
        ),
        "inc_number": None,
        "violation_type": "comp_shutin",
        "region": "Gulf of Mexico",
        "inc_count": 1,
    }


# --- Validation Tests ---


class TestValidateRecord:
    """Tests for validate_record function."""

    def test_valid_incinv_record_passes(self, sample_incinv_record):
        """Valid incident investigation record should pass validation."""
        assert validate_record(sample_incinv_record) is None

    def test_valid_inc_record_passes(self, sample_inc_record):
        """Valid INC violation record should pass validation."""
        assert validate_record(sample_inc_record) is None

    def test_missing_bsee_incident_id_fails(self, sample_incinv_record):
        """Record missing bsee_incident_id should fail validation."""
        del sample_incinv_record["bsee_incident_id"]
        error = validate_record(sample_incinv_record)
        assert error is not None
        assert "bsee_incident_id" in error

    def test_missing_incident_date_fails(self, sample_incinv_record):
        """Record missing incident_date should fail validation."""
        sample_incinv_record["incident_date"] = None
        error = validate_record(sample_incinv_record)
        assert error is not None
        assert "incident_date" in error

    def test_missing_operator_fails(self, sample_incinv_record):
        """Record missing operator should fail validation."""
        del sample_incinv_record["operator"]
        error = validate_record(sample_incinv_record)
        assert error is not None
        assert "operator" in error

    def test_invalid_incident_type_fails(self, sample_incinv_record):
        """Record with invalid incident_type should fail validation."""
        sample_incinv_record["incident_type"] = "unknown_type"
        error = validate_record(sample_incinv_record)
        assert error is not None
        assert "incident_type" in error

    def test_invalid_severity_fails(self, sample_incinv_record):
        """Record with invalid severity should fail validation."""
        sample_incinv_record["severity"] = "catastrophic"
        error = validate_record(sample_incinv_record)
        assert error is not None
        assert "severity" in error

    def test_non_datetime_incident_date_fails(self, sample_incinv_record):
        """Record with string incident_date should fail validation."""
        sample_incinv_record["incident_date"] = "2009-12-19"
        error = validate_record(sample_incinv_record)
        assert error is not None
        assert "datetime" in error

    def test_empty_dict_fails(self):
        """Empty dictionary should fail validation."""
        error = validate_record({})
        assert error is not None

    def test_none_fails(self):
        """None should fail validation."""
        error = validate_record(None)
        assert error is not None

    def test_all_valid_incident_types(self, sample_incinv_record):
        """All valid incident_type values should pass validation."""
        for itype in ["injury", "spill", "equipment_failure", "violation"]:
            sample_incinv_record["incident_type"] = itype
            assert validate_record(sample_incinv_record) is None

    def test_all_valid_severity_levels(self, sample_incinv_record):
        """All valid severity values should pass validation."""
        for severity in ["fatality", "lost_time", "recordable", "near_miss", "minor"]:
            sample_incinv_record["severity"] = severity
            assert validate_record(sample_incinv_record) is None


# --- Import Tests ---


class TestImportIncinvRecords:
    """Tests for incident investigation import."""

    def test_import_single_record(self, db_session, sample_incinv_record):
        """Single valid record should be imported successfully."""
        existing_ids = set()
        stats = import_incinv_records(db_session, [sample_incinv_record], existing_ids)
        assert stats["imported"] == 1
        assert stats["validation_errors"] == 0
        assert stats["skipped_duplicate"] == 0

        # Verify in DB
        count = db_session.query(HSEIncident).count()
        assert count == 1

        incident = db_session.query(HSEIncident).first()
        assert incident.bsee_incident_id == "INCINV-20091219-G15610-0"
        assert incident.incident_type == "spill"
        assert incident.severity == "minor"
        assert incident.operator == "BSEE Reported"
        assert incident.lease_number == "G15610"

    def test_import_multiple_records(self, db_session):
        """Multiple records should all be imported."""
        records = [
            {
                "bsee_incident_id": f"INCINV-20091219-G15610-{i}",
                "incident_date": datetime(2009, 12, 19, 8, 5),
                "operator": "BSEE Reported",
                "incident_type": "spill",
                "severity": "minor",
                "description": f"Test record {i}",
            }
            for i in range(5)
        ]
        existing_ids = set()
        stats = import_incinv_records(db_session, records, existing_ids)
        assert stats["imported"] == 5
        assert db_session.query(HSEIncident).count() == 5

    def test_duplicate_detection(self, db_session, sample_incinv_record):
        """Duplicate records should be skipped."""
        existing_ids = set()
        # First import
        import_incinv_records(db_session, [sample_incinv_record], existing_ids)
        # Second import with same record
        stats = import_incinv_records(db_session, [sample_incinv_record], existing_ids)
        assert stats["imported"] == 0
        assert stats["skipped_duplicate"] == 1
        assert db_session.query(HSEIncident).count() == 1

    def test_validation_error_skips_record(self, db_session):
        """Invalid records should be counted as validation errors."""
        bad_record = {
            "bsee_incident_id": "INCINV-BAD",
            "incident_date": "not-a-date",
            "operator": "Test",
            "incident_type": "spill",
            "severity": "minor",
        }
        existing_ids = set()
        stats = import_incinv_records(db_session, [bad_record], existing_ids)
        assert stats["validation_errors"] == 1
        assert stats["imported"] == 0
        assert db_session.query(HSEIncident).count() == 0

    def test_dry_run_does_not_persist(self, db_session, sample_incinv_record):
        """Dry run should validate but not write to DB."""
        existing_ids = set()
        stats = import_incinv_records(
            db_session, [sample_incinv_record], existing_ids, dry_run=True
        )
        assert stats["imported"] == 1
        assert db_session.query(HSEIncident).count() == 0

    def test_composite_id_format(self, sample_incinv_record):
        """Verify INCINV composite ID format."""
        bid = sample_incinv_record["bsee_incident_id"]
        assert bid.startswith("INCINV-")
        parts = bid.split("-")
        assert len(parts) == 4
        assert parts[0] == "INCINV"
        # Date portion should be 8 digits
        assert len(parts[1]) == 8
        assert parts[1].isdigit()


class TestImportIncsRecords:
    """Tests for INC violation import."""

    def test_import_single_inc_record(self, db_session, sample_inc_record):
        """Single INC record should create HSEIncident + ViolationIncident."""
        existing_ids = set()
        stats = import_incs_records(db_session, [sample_inc_record], existing_ids)
        assert stats["imported"] == 1
        assert stats["violation_records"] == 1
        assert stats["validation_errors"] == 0

        # Verify HSEIncident
        incident = db_session.query(HSEIncident).first()
        assert incident is not None
        assert incident.incident_type == "violation"
        assert incident.bsee_incident_id.startswith("INC-")

        # Verify ViolationIncident child
        violation = db_session.query(ViolationIncident).first()
        assert violation is not None
        assert violation.hse_incident_id == incident.id
        assert violation.violation_type == "comp_shutin"

    def test_import_multiple_inc_types(self, db_session):
        """Different violation types should all be imported correctly."""
        records = [
            {
                "bsee_incident_id": "INC-20200821-03295-WARNING-0",
                "incident_date": datetime(2020, 8, 21),
                "operator": "Test Operator",
                "incident_type": "violation",
                "severity": "minor",
                "description": "Warning INC",
                "inc_number": None,
                "violation_type": "warning",
            },
            {
                "bsee_incident_id": "INC-20200821-03295-COMP_SHUTIN-0",
                "incident_date": datetime(2020, 8, 21),
                "operator": "Test Operator",
                "incident_type": "violation",
                "severity": "minor",
                "description": "Component Shut-in INC",
                "inc_number": None,
                "violation_type": "comp_shutin",
            },
            {
                "bsee_incident_id": "INC-20200821-03295-FAC_SHUTIN-0",
                "incident_date": datetime(2020, 8, 21),
                "operator": "Test Operator",
                "incident_type": "violation",
                "severity": "minor",
                "description": "Facility Shut-in INC",
                "inc_number": None,
                "violation_type": "fac_shutin",
            },
        ]
        existing_ids = set()
        stats = import_incs_records(db_session, records, existing_ids)
        assert stats["imported"] == 3
        assert stats["violation_records"] == 3
        assert db_session.query(HSEIncident).count() == 3
        assert db_session.query(ViolationIncident).count() == 3

    def test_inc_duplicate_detection(self, db_session, sample_inc_record):
        """Duplicate INC records should be skipped."""
        existing_ids = set()
        import_incs_records(db_session, [sample_inc_record], existing_ids)
        stats = import_incs_records(db_session, [sample_inc_record], existing_ids)
        assert stats["imported"] == 0
        assert stats["skipped_duplicate"] == 1
        assert db_session.query(HSEIncident).count() == 1
        assert db_session.query(ViolationIncident).count() == 1

    def test_inc_composite_id_format(self, sample_inc_record):
        """Verify INC composite ID format."""
        bid = sample_inc_record["bsee_incident_id"]
        assert bid.startswith("INC-")
        parts = bid.split("-")
        assert len(parts) == 5
        assert parts[0] == "INC"
        assert len(parts[1]) == 8
        assert parts[1].isdigit()

    def test_inc_dry_run(self, db_session, sample_inc_record):
        """Dry run should validate but not write INC records to DB."""
        existing_ids = set()
        stats = import_incs_records(
            db_session, [sample_inc_record], existing_ids, dry_run=True
        )
        assert stats["imported"] == 1
        assert stats["violation_records"] == 1
        assert db_session.query(HSEIncident).count() == 0
        assert db_session.query(ViolationIncident).count() == 0


class TestLoadExistingIds:
    """Tests for existing ID pre-loading."""

    def test_empty_db_returns_empty_set(self, db_session):
        """Empty database should return empty set of IDs."""
        ids = load_existing_ids(db_session)
        assert ids == set()

    def test_returns_existing_ids(self, db_session):
        """Should return all bsee_incident_id values from DB."""
        incident = HSEIncident(
            bsee_incident_id="TEST-001",
            incident_date=datetime(2020, 1, 1),
            operator="Test",
            incident_type="spill",
            severity="minor",
        )
        db_session.add(incident)
        db_session.commit()

        ids = load_existing_ids(db_session)
        assert "TEST-001" in ids
        assert len(ids) == 1


class TestMixedImport:
    """Integration tests combining both import types."""

    def test_incinv_and_inc_import_coexist(self, db_session):
        """Both INCINV and INC records should coexist in the same DB."""
        incinv_record = {
            "bsee_incident_id": "INCINV-20091219-G15610-0",
            "incident_date": datetime(2009, 12, 19),
            "operator": "BSEE Reported",
            "incident_type": "spill",
            "severity": "minor",
            "description": "Test incident investigation",
        }
        inc_record = {
            "bsee_incident_id": "INC-20200821-03295-WARNING-0",
            "incident_date": datetime(2020, 8, 21),
            "operator": "Test Operator",
            "incident_type": "violation",
            "severity": "minor",
            "violation_type": "warning",
        }

        existing_ids = set()
        import_incinv_records(db_session, [incinv_record], existing_ids)
        import_incs_records(db_session, [inc_record], existing_ids)

        assert db_session.query(HSEIncident).count() == 2
        assert db_session.query(ViolationIncident).count() == 1

        # Check by type
        incinv = (
            db_session.query(HSEIncident)
            .filter(HSEIncident.bsee_incident_id.like("INCINV-%"))
            .count()
        )
        inc = (
            db_session.query(HSEIncident)
            .filter(HSEIncident.bsee_incident_id.like("INC-%"))
            .count()
        )
        assert incinv == 1
        assert inc == 1
