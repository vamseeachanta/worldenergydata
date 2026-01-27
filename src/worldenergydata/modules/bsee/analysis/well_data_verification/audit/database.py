"""
Database management for audit trail system.

Provides SQLite-based storage for audit events, user activities,
verification status, and data lineage tracking.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger


@dataclass
class AuditEvent:
    """Represents an audit event."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    user_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": json.dumps(self.details),
            "severity": self.severity,
            "session_id": self.session_id,
        }


@dataclass
class UserActivity:
    """Represents a user activity record."""

    activity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    activity_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    before_value: Optional[Dict[str, Any]] = None
    after_value: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "activity_id": self.activity_id,
            "user_id": self.user_id,
            "activity_type": self.activity_type,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "resource": self.resource,
            "action": self.action,
            "details": json.dumps(self.details),
            "ip_address": self.ip_address,
            "before_value": (
                json.dumps(self.before_value) if self.before_value else None
            ),
            "after_value": json.dumps(self.after_value) if self.after_value else None,
        }


@dataclass
class VerificationStatus:
    """Represents verification session status."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    workflow_type: str = ""
    status: str = "in_progress"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    well_ids: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    checkpoint_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "well_ids": json.dumps(self.well_ids),
            "details": json.dumps(self.details),
            "checkpoint_data": (
                json.dumps(self.checkpoint_data) if self.checkpoint_data else None
            ),
        }


@dataclass
class DataLineage:
    """Represents data lineage record."""

    lineage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data_id: str = ""
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    source_type: Optional[str] = None
    source_location: Optional[str] = None
    transformation_type: Optional[str] = None
    operations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    fetch_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "lineage_id": self.lineage_id,
            "data_id": self.data_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_type": self.source_type,
            "source_location": self.source_location,
            "transformation_type": self.transformation_type,
            "operations": json.dumps(self.operations),
            "timestamp": self.timestamp.isoformat(),
            "fetch_timestamp": (
                self.fetch_timestamp.isoformat() if self.fetch_timestamp else None
            ),
            "metadata": json.dumps(self.metadata),
        }


class AuditDatabase:
    """
    Manages SQLite database for audit trail storage.

    Provides schema creation, data persistence, and query capabilities
    for audit events, user activities, and data lineage.
    """

    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize audit database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            # Create audit_events table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    severity TEXT DEFAULT 'info',
                    session_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create user_activities table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_activities (
                    activity_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    resource TEXT,
                    action TEXT,
                    details TEXT,
                    ip_address TEXT,
                    before_value TEXT,
                    after_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create verification_status table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS verification_status (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workflow_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    well_ids TEXT,
                    details TEXT,
                    checkpoint_data TEXT
                )
            """
            )

            # Create data_lineage table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS data_lineage (
                    lineage_id TEXT PRIMARY KEY,
                    data_id TEXT NOT NULL,
                    source_id TEXT,
                    target_id TEXT,
                    source_type TEXT,
                    source_location TEXT,
                    transformation_type TEXT,
                    operations TEXT,
                    timestamp TEXT NOT NULL,
                    fetch_timestamp TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indices for better query performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activities_user ON user_activities(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activities_type ON user_activities(activity_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_status_user ON verification_status(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_status_status ON verification_status(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_data ON data_lineage(data_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_source ON data_lineage(source_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lineage_target ON data_lineage(target_id)"
            )

            conn.commit()
            logger.info(f"Initialized audit database at {self.db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
        return self._connection

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def execute(self, query: str, params: tuple = ()):
        """Execute a database query."""
        with self.transaction() as conn:
            return conn.execute(query, params)

    def query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a query and return results."""
        conn = self.get_connection()
        cursor = conn.execute(query, params)
        return cursor.fetchall()

    def insert_audit_event(self, event: AuditEvent) -> str:
        """Insert audit event into database."""
        data = event.to_dict()
        query = """
            INSERT INTO audit_events
            (event_id, event_type, user_id, timestamp, details, severity, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data["event_id"],
            data["event_type"],
            data["user_id"],
            data["timestamp"],
            data["details"],
            data["severity"],
            data["session_id"],
        )
        self.execute(query, params)
        return data["event_id"]

    def insert_user_activity(self, activity: UserActivity) -> str:
        """Insert user activity into database."""
        data = activity.to_dict()
        query = """
            INSERT INTO user_activities
            (activity_id, user_id, activity_type, timestamp, session_id, resource,
             action, details, ip_address, before_value, after_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data["activity_id"],
            data["user_id"],
            data["activity_type"],
            data["timestamp"],
            data["session_id"],
            data["resource"],
            data["action"],
            data["details"],
            data["ip_address"],
            data["before_value"],
            data["after_value"],
        )
        self.execute(query, params)
        return data["activity_id"]

    def insert_verification_status(self, status: VerificationStatus) -> str:
        """Insert or update verification status."""
        data = status.to_dict()
        query = """
            INSERT OR REPLACE INTO verification_status
            (session_id, user_id, workflow_type, status, created_at,
             updated_at, well_ids, details, checkpoint_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data["session_id"],
            data["user_id"],
            data["workflow_type"],
            data["status"],
            data["created_at"],
            data["updated_at"],
            data["well_ids"],
            data["details"],
            data["checkpoint_data"],
        )
        self.execute(query, params)
        return data["session_id"]

    def insert_data_lineage(self, lineage: DataLineage) -> str:
        """Insert data lineage record."""
        data = lineage.to_dict()
        query = """
            INSERT INTO data_lineage
            (lineage_id, data_id, source_id, target_id, source_type, source_location,
             transformation_type, operations, timestamp, fetch_timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data["lineage_id"],
            data["data_id"],
            data["source_id"],
            data["target_id"],
            data["source_type"],
            data["source_location"],
            data["transformation_type"],
            data["operations"],
            data["timestamp"],
            data["fetch_timestamp"],
            data["metadata"],
        )
        self.execute(query, params)
        return data["lineage_id"]

    def get_tables(self) -> List[str]:
        """Get list of tables in database."""
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        results = self.query(query)
        return [row["name"] for row in results]

    def backup(self, backup_path: Path):
        """Create database backup."""
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(backup_path)) as backup_conn:
            self.get_connection().backup(backup_conn)

        logger.info(f"Database backed up to {backup_path}")

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        tables = self.get_tables()
        required_tables = [
            "audit_events",
            "user_activities",
            "verification_status",
            "data_lineage",
        ]
        return all(table in tables for table in required_tables)

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        try:
            self.get_connection().execute("SELECT 1")
            return True
        except:
            return False
