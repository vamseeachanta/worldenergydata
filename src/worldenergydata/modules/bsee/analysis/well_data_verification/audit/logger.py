"""
Audit logger for verification system.

Provides comprehensive logging of all verification activities,
errors, and system events for compliance and debugging.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import json

from loguru import logger

from .database import AuditDatabase, AuditEvent


class AuditLogger:
    """
    Manages audit logging for the verification system.
    
    Provides methods to log events, errors, and queries with
    automatic persistence to the audit database.
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize audit logger.
        
        Args:
            db_path: Path to audit database
        """
        self.db_path = Path(db_path)
        self.database = AuditDatabase(db_path)
        self._session_id = None
        
        # Log initialization
        self.log_event(
            event_type="AUDIT_LOGGER_INIT",
            user_id="system",
            details={"db_path": str(self.db_path)}
        )
    
    def set_session(self, session_id: str):
        """Set current session ID for all subsequent logs."""
        self._session_id = session_id
    
    def log_event(self,
                  event_type: str,
                  user_id: str,
                  details: Optional[Dict[str, Any]] = None,
                  severity: str = "info") -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "VERIFICATION_START")
            user_id: User performing the action
            details: Additional event details
            severity: Event severity (debug, info, warning, error, critical)
        
        Returns:
            Created audit event
        """
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            details=details or {},
            severity=severity,
            session_id=self._session_id,
            timestamp=datetime.now()
        )
        
        # Store in database
        self.database.insert_audit_event(event)
        
        # Also log to system logger
        log_method = getattr(logger, severity, logger.info)
        log_method(f"Audit Event: {event_type} by {user_id} - {details}")
        
        return event
    
    def log_error(self,
                  error_message: str,
                  error_type: str = "ERROR",
                  context: Optional[Dict[str, Any]] = None,
                  user_id: str = "system") -> AuditEvent:
        """
        Log an error event.
        
        Args:
            error_message: Error message
            error_type: Type of error
            context: Error context information
            user_id: User associated with error
        
        Returns:
            Created error event
        """
        details = {
            "message": error_message,
            "error_type": error_type,
            "context": context or {}
        }
        
        return self.log_event(
            event_type="ERROR",
            user_id=user_id,
            details=details,
            severity="error"
        )
    
    def log_warning(self,
                    warning_message: str,
                    context: Optional[Dict[str, Any]] = None,
                    user_id: str = "system") -> AuditEvent:
        """
        Log a warning event.
        
        Args:
            warning_message: Warning message
            context: Warning context information
            user_id: User associated with warning
        
        Returns:
            Created warning event
        """
        details = {
            "message": warning_message,
            "context": context or {}
        }
        
        return self.log_event(
            event_type="WARNING",
            user_id=user_id,
            details=details,
            severity="warning"
        )
    
    def log_verification_start(self,
                               user_id: str,
                               workflow_type: str,
                               well_ids: List[str],
                               config: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """
        Log verification workflow start.
        
        Args:
            user_id: User starting verification
            workflow_type: Type of verification workflow
            well_ids: List of well IDs being verified
            config: Workflow configuration
        
        Returns:
            Created event
        """
        return self.log_event(
            event_type="VERIFICATION_START",
            user_id=user_id,
            details={
                "workflow_type": workflow_type,
                "well_count": len(well_ids),
                "well_ids": well_ids[:10],  # Log first 10 for brevity
                "config": config or {}
            }
        )
    
    def log_verification_complete(self,
                                  user_id: str,
                                  session_id: str,
                                  results: Dict[str, Any]) -> AuditEvent:
        """
        Log verification workflow completion.
        
        Args:
            user_id: User who completed verification
            session_id: Verification session ID
            results: Verification results summary
        
        Returns:
            Created event
        """
        return self.log_event(
            event_type="VERIFICATION_COMPLETE",
            user_id=user_id,
            details={
                "session_id": session_id,
                "results": results,
                "completion_time": datetime.now().isoformat()
            }
        )
    
    def log_validation_failure(self,
                               user_id: str,
                               field: str,
                               reason: str,
                               well_id: Optional[str] = None,
                               value: Any = None) -> AuditEvent:
        """
        Log validation failure.
        
        Args:
            user_id: User performing validation
            field: Field that failed validation
            reason: Reason for failure
            well_id: Associated well ID
            value: The invalid value
        
        Returns:
            Created event
        """
        return self.log_event(
            event_type="VALIDATION_FAILURE",
            user_id=user_id,
            details={
                "field": field,
                "reason": reason,
                "well_id": well_id,
                "value": str(value) if value is not None else None
            },
            severity="warning"
        )
    
    def log_data_access(self,
                        user_id: str,
                        resource: str,
                        action: str = "READ",
                        details: Optional[Dict[str, Any]] = None) -> AuditEvent:
        """
        Log data access event.
        
        Args:
            user_id: User accessing data
            resource: Resource being accessed
            action: Type of access (READ, WRITE, DELETE)
            details: Additional access details
        
        Returns:
            Created event
        """
        return self.log_event(
            event_type="DATA_ACCESS",
            user_id=user_id,
            details={
                "resource": resource,
                "action": action,
                **(details or {})
            }
        )
    
    def log_configuration_change(self,
                                 user_id: str,
                                 config_type: str,
                                 before: Dict[str, Any],
                                 after: Dict[str, Any],
                                 reason: Optional[str] = None) -> AuditEvent:
        """
        Log configuration change.
        
        Args:
            user_id: User making change
            config_type: Type of configuration
            before: Configuration before change
            after: Configuration after change
            reason: Reason for change
        
        Returns:
            Created event
        """
        return self.log_event(
            event_type="CONFIG_CHANGE",
            user_id=user_id,
            details={
                "config_type": config_type,
                "before": before,
                "after": after,
                "reason": reason,
                "changed_fields": list(set(before.keys()) | set(after.keys()))
            }
        )
    
    def query_events(self,
                     event_type: Optional[str] = None,
                     user_id: Optional[str] = None,
                     session_id: Optional[str] = None,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     severity: Optional[str] = None,
                     limit: int = 100) -> List[AuditEvent]:
        """
        Query audit events.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            session_id: Filter by session ID
            start_date: Filter events after this date
            end_date: Filter events before this date
            severity: Filter by severity level
            limit: Maximum number of results
        
        Returns:
            List of matching audit events
        """
        # Build query
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        # Execute query
        rows = self.database.query(query, tuple(params))
        
        # Convert to AuditEvent objects
        events = []
        for row in rows:
            event = AuditEvent(
                event_id=row["event_id"],
                event_type=row["event_type"],
                user_id=row["user_id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                details=json.loads(row["details"]) if row["details"] else {},
                severity=row["severity"],
                session_id=row["session_id"]
            )
            events.append(event)
        
        return events
    
    def get_event_statistics(self,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get audit event statistics.
        
        Args:
            start_date: Start of period
            end_date: End of period
        
        Returns:
            Dictionary with event statistics
        """
        # Build date filter
        date_filter = "WHERE 1=1"
        params = []
        
        if start_date:
            date_filter += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            date_filter += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        # Get event counts by type
        query = f"""
            SELECT event_type, COUNT(*) as count
            FROM audit_events
            {date_filter}
            GROUP BY event_type
        """
        type_counts = self.database.query(query, tuple(params))
        
        # Get event counts by severity
        query = f"""
            SELECT severity, COUNT(*) as count
            FROM audit_events
            {date_filter}
            GROUP BY severity
        """
        severity_counts = self.database.query(query, tuple(params))
        
        # Get user activity
        query = f"""
            SELECT user_id, COUNT(*) as count
            FROM audit_events
            {date_filter}
            GROUP BY user_id
            ORDER BY count DESC
            LIMIT 10
        """
        user_counts = self.database.query(query, tuple(params))
        
        return {
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "event_types": {row["event_type"]: row["count"] for row in type_counts},
            "severities": {row["severity"]: row["count"] for row in severity_counts},
            "top_users": [(row["user_id"], row["count"]) for row in user_counts]
        }
    
    def apply_retention_policy(self, days: int = 90):
        """
        Apply retention policy to remove old events.
        
        Args:
            days: Number of days to retain events
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = "DELETE FROM audit_events WHERE timestamp < ?"
        deleted = self.database.execute(query, (cutoff_date.isoformat(),))
        
        self.log_event(
            event_type="RETENTION_POLICY_APPLIED",
            user_id="system",
            details={
                "days_retained": days,
                "cutoff_date": cutoff_date.isoformat(),
                "events_deleted": deleted.rowcount
            }
        )
        
        logger.info(f"Retention policy applied: removed {deleted.rowcount} events older than {days} days")
    
    def export_audit_log(self,
                        output_path: Path,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None):
        """
        Export audit log to file.
        
        Args:
            output_path: Path to output file
            start_date: Start of export period
            end_date: End of export period
        """
        events = self.query_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        # Convert to JSON
        export_data = {
            "export_date": datetime.now().isoformat(),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "event_count": len(events),
            "events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "user_id": e.user_id,
                    "timestamp": e.timestamp.isoformat(),
                    "details": e.details,
                    "severity": e.severity,
                    "session_id": e.session_id
                }
                for e in events
            ]
        }
        
        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.log_event(
            event_type="AUDIT_LOG_EXPORTED",
            user_id="system",
            details={
                "output_path": str(output_path),
                "event_count": len(events)
            }
        )
        
        logger.info(f"Exported {len(events)} audit events to {output_path}")
    
    def close(self):
        """Close audit logger and database connection."""
        self.log_event(
            event_type="AUDIT_LOGGER_CLOSE",
            user_id="system",
            details={}
        )
        self.database.close()
    
    @property
    def is_connected(self) -> bool:
        """Check if logger is connected to database."""
        return self.database.is_connected