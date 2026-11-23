"""
Tests for the audit and logging system.

Tests audit trail functionality, user activity tracking, compliance reporting,
and data lineage tracking for well data verification.
"""

import json
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from worldenergydata.modules.analysis.verification.audit.compliance import (
    ComplianceReport,
    ComplianceReportGenerator,
)
from worldenergydata.modules.analysis.verification.audit.database import (
    AuditDatabase,
    AuditEvent,
    DataLineage,
    UserActivity,
    VerificationStatus,
)

# Import audit system components (to be implemented)
from worldenergydata.modules.analysis.verification.audit.logger import AuditLogger
from worldenergydata.modules.analysis.verification.audit.tracker import (
    ActivityTracker,
    DataLineageTracker,
    VerificationStatusManager,
)


class TestAuditLogger:
    """Test audit logger functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass  # Windows sometimes locks the file

    @pytest.fixture
    def audit_logger(self, temp_db):
        """Create audit logger instance."""
        logger = AuditLogger(db_path=temp_db)
        yield logger
        # Ensure connection is closed
        logger.close()

    def test_logger_initialization(self, audit_logger):
        """Test audit logger initialization."""
        assert audit_logger is not None
        assert audit_logger.db_path.exists()
        assert audit_logger.is_connected

    def test_log_event(self, audit_logger):
        """Test logging an audit event."""
        event = audit_logger.log_event(
            event_type="VERIFICATION_START",
            user_id="test_user",
            details={
                "well_id": "W123",
                "lease_num": "L456",
                "workflow": "manual_verification",
            },
        )

        assert event is not None
        assert event.event_type == "VERIFICATION_START"
        assert event.user_id == "test_user"
        assert event.details["well_id"] == "W123"
        assert event.timestamp is not None

    def test_log_error(self, audit_logger):
        """Test logging an error event."""
        error_event = audit_logger.log_error(
            error_message="Validation failed",
            error_type="ValidationError",
            context={"field": "production_volume", "value": -100},
        )

        assert error_event.event_type == "ERROR"
        assert error_event.severity == "error"
        assert "Validation failed" in error_event.details["message"]

    def test_query_events(self, audit_logger):
        """Test querying audit events."""
        # Log multiple events
        for i in range(5):
            audit_logger.log_event(
                event_type=f"TEST_EVENT_{i}", user_id="test_user", details={"index": i}
            )

        # Query all events
        events = audit_logger.query_events(user_id="test_user")
        assert len(events) == 5

        # Query by event type
        events = audit_logger.query_events(event_type="TEST_EVENT_2")
        assert len(events) == 1
        assert events[0].details["index"] == 2

    def test_event_retention(self, audit_logger):
        """Test audit event retention policy."""
        # Create an old event by directly inserting with old timestamp
        old_timestamp = datetime.now() - timedelta(days=365)
        old_event = AuditEvent(
            event_type="OLD_EVENT",
            user_id="test_user",
            timestamp=old_timestamp,
            details={},
        )

        # Insert the old event
        audit_logger.database.insert_audit_event(old_event)

        # Apply retention policy (keep last 90 days by default)
        audit_logger.apply_retention_policy(days=90)

        # Check old event is removed
        events = audit_logger.query_events(event_type="OLD_EVENT")
        assert len(events) == 0


class TestActivityTracker:
    """Test user activity tracking."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass  # Windows sometimes locks the file

    @pytest.fixture
    def activity_tracker(self, temp_db):
        """Create activity tracker instance."""
        tracker = ActivityTracker(db_path=temp_db)
        yield tracker
        # Close database connection
        tracker.database.close()

    def test_track_user_login(self, activity_tracker):
        """Test tracking user login."""
        activity = activity_tracker.track_login(
            user_id="test_user", session_id="session_123", ip_address="192.168.1.1"
        )

        assert activity.activity_type == "LOGIN"
        assert activity.user_id == "test_user"
        assert activity.session_id == "session_123"

    def test_track_data_access(self, activity_tracker):
        """Test tracking data access."""
        activity = activity_tracker.track_data_access(
            user_id="test_user",
            resource="well_data",
            action="READ",
            details={"well_id": "W123"},
        )

        assert activity.activity_type == "DATA_ACCESS"
        assert activity.action == "READ"
        assert activity.resource == "well_data"

    def test_track_modification(self, activity_tracker):
        """Test tracking data modifications."""
        activity = activity_tracker.track_modification(
            user_id="test_user",
            resource="validation_rule",
            before_value={"threshold": 100},
            after_value={"threshold": 150},
            reason="Adjusted threshold based on new requirements",
        )

        assert activity.activity_type == "MODIFICATION"
        assert activity.before_value["threshold"] == 100
        assert activity.after_value["threshold"] == 150

    def test_user_activity_report(self, activity_tracker):
        """Test generating user activity report."""
        # Track various activities
        activity_tracker.track_login("user1", "session1", "192.168.1.1")
        activity_tracker.track_data_access("user1", "well_data", "READ", {})
        activity_tracker.track_modification("user1", "config", {}, {}, "update")

        # Generate report
        report = activity_tracker.generate_activity_report(
            user_id="user1",
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
        )

        assert report["user_id"] == "user1"
        assert report["total_activities"] == 3
        assert "LOGIN" in report["activity_types"]


class TestVerificationStatusManager:
    """Test verification status management."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass  # Windows sometimes locks the file

    @pytest.fixture
    def status_manager(self, temp_db):
        """Create verification status manager."""
        manager = VerificationStatusManager(db_path=temp_db)
        yield manager
        # Close database connection
        manager.database.close()

    def test_create_verification_session(self, status_manager):
        """Test creating verification session."""
        session = status_manager.create_session(
            user_id="test_user",
            workflow_type="manual_verification",
            well_ids=["W1", "W2", "W3"],
        )

        assert session.session_id is not None
        assert session.status == "in_progress"
        assert len(session.well_ids) == 3

    def test_update_verification_status(self, status_manager):
        """Test updating verification status."""
        session = status_manager.create_session(
            user_id="test_user", workflow_type="manual_verification", well_ids=["W1"]
        )

        # Update status
        updated = status_manager.update_status(
            session_id=session.session_id,
            status="completed",
            details={"verified_count": 1},
        )

        assert updated.status == "completed"
        assert updated.details["verified_count"] == 1

    def test_checkpoint_management(self, status_manager):
        """Test checkpoint save and restore."""
        session = status_manager.create_session(
            user_id="test_user",
            workflow_type="manual_verification",
            well_ids=["W1", "W2"],
        )

        # Save checkpoint
        checkpoint = status_manager.save_checkpoint(
            session_id=session.session_id,
            checkpoint_data={
                "current_well": "W1",
                "progress": 50,
                "validated_fields": ["production", "revenue"],
            },
        )

        assert checkpoint is not None
        assert checkpoint.checkpoint_data["progress"] == 50

        # Restore checkpoint
        restored = status_manager.restore_checkpoint(session.session_id)
        assert restored["current_well"] == "W1"
        assert restored["progress"] == 50

    def test_session_history(self, status_manager):
        """Test retrieving session history."""
        # Create multiple sessions
        for i in range(3):
            status_manager.create_session(
                user_id="test_user", workflow_type=f"workflow_{i}", well_ids=[f"W{i}"]
            )

        # Get history
        history = status_manager.get_session_history(user_id="test_user")
        assert len(history) == 3

        # Get active sessions
        active = status_manager.get_active_sessions()
        assert len(active) == 3


class TestComplianceReportGenerator:
    """Test compliance report generation."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass  # Windows sometimes locks the file

    @pytest.fixture
    def report_generator(self, temp_db):
        """Create compliance report generator."""
        audit_logger = AuditLogger(db_path=temp_db)
        activity_tracker = ActivityTracker(db_path=temp_db)
        status_manager = VerificationStatusManager(db_path=temp_db)

        generator = ComplianceReportGenerator(
            audit_logger=audit_logger,
            activity_tracker=activity_tracker,
            status_manager=status_manager,
        )
        yield generator
        # Close all connections
        audit_logger.close()
        activity_tracker.database.close()
        status_manager.database.close()

    def test_generate_compliance_report(self, report_generator):
        """Test generating compliance report."""
        # Add some audit data
        report_generator.audit_logger.log_event(
            event_type="VERIFICATION_COMPLETE",
            user_id="auditor1",
            details={"well_count": 10},
        )

        # Generate report
        report = report_generator.generate_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            report_type="monthly_compliance",
        )

        assert report is not None
        assert report.report_type == "monthly_compliance"
        assert report.period_start is not None
        assert report.period_end is not None

    def test_export_compliance_report(self, report_generator, tmp_path):
        """Test exporting compliance report."""
        # Generate report
        report = report_generator.generate_report(
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            report_type="weekly_summary",
        )

        # Export to PDF
        pdf_path = tmp_path / "compliance_report.pdf"
        report_generator.export_pdf(report, pdf_path)
        assert pdf_path.exists()

        # Export to Excel
        excel_path = tmp_path / "compliance_report.xlsx"
        report_generator.export_excel(report, excel_path)
        assert excel_path.exists()

    def test_regulatory_requirements(self, report_generator):
        """Test regulatory requirement checks."""
        # Check if system meets regulatory requirements
        requirements = report_generator.check_regulatory_requirements()

        assert "data_retention" in requirements
        assert "audit_trail" in requirements
        assert "user_authentication" in requirements
        assert "data_lineage" in requirements


class TestDataLineageTracker:
    """Test data lineage tracking."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass  # Windows sometimes locks the file

    @pytest.fixture
    def lineage_tracker(self, temp_db):
        """Create data lineage tracker."""
        tracker = DataLineageTracker(db_path=temp_db)
        yield tracker
        # Close database connection
        tracker.database.close()

    def test_track_data_source(self, lineage_tracker):
        """Test tracking data source."""
        lineage = lineage_tracker.track_source(
            data_id="dataset_001",
            source_type="BSEE_API",
            source_location="https://api.bsee.gov/wells",
            fetch_timestamp=datetime.now(),
            metadata={"record_count": 1000},
        )

        assert lineage.data_id == "dataset_001"
        assert lineage.source_type == "BSEE_API"
        assert lineage.metadata["record_count"] == 1000

    def test_track_transformation(self, lineage_tracker):
        """Test tracking data transformations."""
        # Track initial data
        source = lineage_tracker.track_source(
            data_id="raw_data_001",
            source_type="CSV",
            source_location="/data/wells.csv",
            fetch_timestamp=datetime.now(),
        )

        # Track transformation
        transformed = lineage_tracker.track_transformation(
            source_id="raw_data_001",
            target_id="cleaned_data_001",
            transformation_type="CLEANING",
            operations=[
                "Remove null values",
                "Normalize production units",
                "Validate date ranges",
            ],
        )

        assert transformed.source_id == "raw_data_001"
        assert transformed.target_id == "cleaned_data_001"
        assert len(transformed.operations) == 3

    def test_get_lineage_chain(self, lineage_tracker):
        """Test retrieving complete lineage chain."""
        # Create lineage chain
        lineage_tracker.track_source("data_v1", "API", "source1", datetime.now())
        lineage_tracker.track_transformation("data_v1", "data_v2", "CLEAN", ["op1"])
        lineage_tracker.track_transformation("data_v2", "data_v3", "VALIDATE", ["op2"])

        # Get complete chain
        chain = lineage_tracker.get_lineage_chain("data_v3")
        assert len(chain) == 3
        assert chain[0]["data_id"] == "data_v1"
        assert chain[-1]["data_id"] == "data_v3"

    def test_impact_analysis(self, lineage_tracker):
        """Test impact analysis for data changes."""
        # Create lineage
        lineage_tracker.track_source("base_data", "DB", "source", datetime.now())
        lineage_tracker.track_transformation("base_data", "derived1", "CALC", [])
        lineage_tracker.track_transformation("base_data", "derived2", "AGG", [])
        lineage_tracker.track_transformation("derived1", "report1", "REPORT", [])

        # Analyze impact
        impact = lineage_tracker.analyze_impact("base_data")
        assert len(impact["direct_dependencies"]) == 2
        assert "derived1" in impact["direct_dependencies"]
        assert "derived2" in impact["direct_dependencies"]
        assert "report1" in impact["indirect_dependencies"]


class TestAuditDatabase:
    """Test audit database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass  # Windows sometimes locks the file

    @pytest.fixture
    def audit_db(self, temp_db):
        """Create audit database instance."""
        db = AuditDatabase(db_path=temp_db)
        yield db
        # Close database connection
        db.close()

    def test_database_initialization(self, audit_db):
        """Test database initialization and schema creation."""
        assert audit_db.is_initialized

        # Check tables exist
        tables = audit_db.get_tables()
        assert "audit_events" in tables
        assert "user_activities" in tables
        assert "verification_status" in tables
        assert "data_lineage" in tables

    def test_transaction_management(self, audit_db):
        """Test database transaction management."""
        with audit_db.transaction() as tx:
            # Insert test data
            tx.execute(
                "INSERT INTO audit_events (event_id, event_type, user_id, timestamp, details) VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    "TEST_EVENT",
                    "user1",
                    datetime.now().isoformat(),
                    json.dumps({"test": True}),
                ),
            )

        # Verify data was committed
        result = audit_db.query(
            "SELECT * FROM audit_events WHERE event_type = ?", ("TEST_EVENT",)
        )
        assert len(result) == 1

    def test_database_backup(self, audit_db, tmp_path):
        """Test database backup functionality."""
        # Add some data
        audit_db.execute(
            "INSERT INTO audit_events (event_id, event_type, user_id, timestamp, details) VALUES (?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                "BACKUP_TEST",
                "user1",
                datetime.now().isoformat(),
                json.dumps({}),
            ),
        )

        # Create backup
        backup_path = tmp_path / "audit_backup.db"
        audit_db.backup(backup_path)

        assert backup_path.exists()

        # Verify backup contains data
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.execute(
            "SELECT * FROM audit_events WHERE event_type = 'BACKUP_TEST'"
        )
        assert len(cursor.fetchall()) == 1
        conn.close()


class TestIntegration:
    """Integration tests for audit system."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            if db_path.exists():
                db_path.unlink()
        except PermissionError:
            pass  # Windows sometimes locks the file

    @pytest.fixture
    def audit_system(self, temp_db):
        """Create complete audit system."""
        logger = AuditLogger(db_path=temp_db)
        tracker = ActivityTracker(db_path=temp_db)
        status = VerificationStatusManager(db_path=temp_db)
        lineage = DataLineageTracker(db_path=temp_db)
        compliance = ComplianceReportGenerator(
            audit_logger=logger, activity_tracker=tracker, status_manager=status
        )

        system = {
            "logger": logger,
            "tracker": tracker,
            "status": status,
            "lineage": lineage,
            "compliance": compliance,
        }

        yield system

        # Close all connections
        logger.close()
        tracker.database.close()
        status.database.close()
        lineage.database.close()

    def test_complete_verification_workflow_audit(self, audit_system):
        """Test complete verification workflow with audit trail."""
        logger = audit_system["logger"]
        tracker = audit_system["tracker"]
        status = audit_system["status"]
        lineage = audit_system["lineage"]

        # Start verification session
        session = status.create_session(
            user_id="verifier1",
            workflow_type="comprehensive_verification",
            well_ids=["W001", "W002"],
        )

        # Log session start
        logger.log_event(
            event_type="SESSION_START",
            user_id="verifier1",
            details={"session_id": session.session_id},
        )

        # Track data access
        tracker.track_data_access(
            user_id="verifier1",
            resource="well_production_data",
            action="READ",
            details={"wells": ["W001", "W002"]},
        )

        # Track data lineage
        lineage.track_source(
            data_id="wells_batch_001",
            source_type="BSEE_DATABASE",
            source_location="production_table",
            fetch_timestamp=datetime.now(),
        )

        # Simulate validation
        lineage.track_transformation(
            source_id="wells_batch_001",
            target_id="validated_batch_001",
            transformation_type="VALIDATION",
            operations=["Check completeness", "Verify ranges", "Cross-reference"],
        )

        # Update session status with verified_wells count
        status.update_status(
            session_id=session.session_id,
            status="completed",
            details={"wells_verified": 2, "verified_wells": 2, "issues_found": 0},
        )

        # Log completion
        logger.log_event(
            event_type="SESSION_COMPLETE",
            user_id="verifier1",
            details={"session_id": session.session_id, "duration_minutes": 15},
        )

        # Generate compliance report
        report = audit_system["compliance"].generate_report(
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now(),
            report_type="session_summary",
        )

        assert report is not None
        # Check that the report was generated successfully
        assert report.report_type == "session_summary"
        # Since we completed one session with 2 wells, check for those
        assert report.summary.get("sessions_completed", 0) >= 1
        assert report.summary.get("total_wells_verified", 0) >= 2
