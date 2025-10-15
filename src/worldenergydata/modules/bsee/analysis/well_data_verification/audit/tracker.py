"""
Activity and status tracking for verification system.

Provides user activity tracking, verification status management,
and data lineage tracking for complete audit trail.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import uuid

from loguru import logger

from .database import (
    AuditDatabase,
    UserActivity,
    VerificationStatus,
    DataLineage
)


class ActivityTracker:
    """
    Tracks user activities in the verification system.
    
    Monitors login/logout, data access, modifications, and
    generates activity reports for compliance.
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize activity tracker.
        
        Args:
            db_path: Path to audit database
        """
        self.db_path = Path(db_path)
        self.database = AuditDatabase(db_path)
        self._current_session = None
    
    def set_session(self, session_id: str):
        """Set current session ID for tracking."""
        self._current_session = session_id
    
    def track_login(self,
                    user_id: str,
                    session_id: str,
                    ip_address: Optional[str] = None) -> UserActivity:
        """
        Track user login event.
        
        Args:
            user_id: User logging in
            session_id: Session identifier
            ip_address: User's IP address
        
        Returns:
            Created activity record
        """
        activity = UserActivity(
            user_id=user_id,
            activity_type="LOGIN",
            session_id=session_id,
            ip_address=ip_address,
            details={"login_time": datetime.now().isoformat()}
        )
        
        self.database.insert_user_activity(activity)
        logger.info(f"User {user_id} logged in from {ip_address}")
        
        return activity
    
    def track_logout(self,
                     user_id: str,
                     session_id: str) -> UserActivity:
        """
        Track user logout event.
        
        Args:
            user_id: User logging out
            session_id: Session identifier
        
        Returns:
            Created activity record
        """
        activity = UserActivity(
            user_id=user_id,
            activity_type="LOGOUT",
            session_id=session_id,
            details={"logout_time": datetime.now().isoformat()}
        )
        
        self.database.insert_user_activity(activity)
        logger.info(f"User {user_id} logged out")
        
        return activity
    
    def track_data_access(self,
                          user_id: str,
                          resource: str,
                          action: str = "READ",
                          details: Optional[Dict[str, Any]] = None) -> UserActivity:
        """
        Track data access activity.
        
        Args:
            user_id: User accessing data
            resource: Resource being accessed
            action: Type of access (READ, WRITE, DELETE)
            details: Additional access details
        
        Returns:
            Created activity record
        """
        activity = UserActivity(
            user_id=user_id,
            activity_type="DATA_ACCESS",
            session_id=self._current_session,
            resource=resource,
            action=action,
            details=details or {}
        )
        
        self.database.insert_user_activity(activity)
        logger.debug(f"User {user_id} performed {action} on {resource}")
        
        return activity
    
    def track_modification(self,
                          user_id: str,
                          resource: str,
                          before_value: Dict[str, Any],
                          after_value: Dict[str, Any],
                          reason: Optional[str] = None) -> UserActivity:
        """
        Track data modification activity.
        
        Args:
            user_id: User making modification
            resource: Resource being modified
            before_value: Value before modification
            after_value: Value after modification
            reason: Reason for modification
        
        Returns:
            Created activity record
        """
        activity = UserActivity(
            user_id=user_id,
            activity_type="MODIFICATION",
            session_id=self._current_session,
            resource=resource,
            action="UPDATE",
            before_value=before_value,
            after_value=after_value,
            details={"reason": reason} if reason else {}
        )
        
        self.database.insert_user_activity(activity)
        logger.info(f"User {user_id} modified {resource}")
        
        return activity
    
    def track_export(self,
                    user_id: str,
                    export_type: str,
                    destination: str,
                    record_count: int) -> UserActivity:
        """
        Track data export activity.
        
        Args:
            user_id: User exporting data
            export_type: Type of export (PDF, Excel, CSV)
            destination: Export destination
            record_count: Number of records exported
        
        Returns:
            Created activity record
        """
        activity = UserActivity(
            user_id=user_id,
            activity_type="DATA_EXPORT",
            session_id=self._current_session,
            resource="verification_data",
            action="EXPORT",
            details={
                "export_type": export_type,
                "destination": destination,
                "record_count": record_count,
                "export_time": datetime.now().isoformat()
            }
        )
        
        self.database.insert_user_activity(activity)
        logger.info(f"User {user_id} exported {record_count} records to {export_type}")
        
        return activity
    
    def generate_activity_report(self,
                                 user_id: Optional[str] = None,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate user activity report.
        
        Args:
            user_id: Filter by user (None for all users)
            start_date: Report start date
            end_date: Report end date
        
        Returns:
            Activity report dictionary
        """
        # Build query
        query = "SELECT * FROM user_activities WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        # Get activities
        rows = self.database.query(query, tuple(params))
        
        # Process activities
        activities = []
        activity_types = set()
        resources_accessed = set()
        
        for row in rows:
            activity_types.add(row["activity_type"])
            if row["resource"]:
                resources_accessed.add(row["resource"])
            
            activities.append({
                "activity_id": row["activity_id"],
                "user_id": row["user_id"],
                "activity_type": row["activity_type"],
                "timestamp": row["timestamp"],
                "resource": row["resource"],
                "action": row["action"]
            })
        
        # Generate summary
        report = {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "total_activities": len(activities),
            "activity_types": list(activity_types),
            "resources_accessed": list(resources_accessed),
            "activities": activities[:100]  # Limit to recent 100
        }
        
        return report
    
    def get_user_sessions(self,
                         user_id: str,
                         limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's recent sessions.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions
        
        Returns:
            List of session information
        """
        # Get login activities
        query = """
            SELECT * FROM user_activities
            WHERE user_id = ? AND activity_type = 'LOGIN'
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        logins = self.database.query(query, (user_id, limit))
        
        sessions = []
        for login in logins:
            session_id = login["session_id"]
            
            # Get logout for this session
            logout_query = """
                SELECT * FROM user_activities
                WHERE session_id = ? AND activity_type = 'LOGOUT'
                LIMIT 1
            """
            logout = self.database.query(logout_query, (session_id,))
            
            # Get activity count for session
            activity_query = """
                SELECT COUNT(*) as count FROM user_activities
                WHERE session_id = ?
            """
            activity_count = self.database.query(activity_query, (session_id,))[0]["count"]
            
            sessions.append({
                "session_id": session_id,
                "login_time": login["timestamp"],
                "logout_time": logout[0]["timestamp"] if logout else None,
                "ip_address": login["ip_address"],
                "activity_count": activity_count
            })
        
        return sessions


class VerificationStatusManager:
    """
    Manages verification session status and checkpoints.
    
    Tracks verification progress, saves/restores checkpoints,
    and maintains session history.
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize status manager.
        
        Args:
            db_path: Path to audit database
        """
        self.db_path = Path(db_path)
        self.database = AuditDatabase(db_path)
    
    def create_session(self,
                      user_id: str,
                      workflow_type: str,
                      well_ids: List[str]) -> VerificationStatus:
        """
        Create new verification session.
        
        Args:
            user_id: User creating session
            workflow_type: Type of verification workflow
            well_ids: List of wells to verify
        
        Returns:
            Created verification session
        """
        session = VerificationStatus(
            user_id=user_id,
            workflow_type=workflow_type,
            well_ids=well_ids,
            status="in_progress",
            details={
                "total_wells": len(well_ids),
                "verified_wells": 0,
                "start_time": datetime.now().isoformat()
            }
        )
        
        self.database.insert_verification_status(session)
        logger.info(f"Created verification session {session.session_id} for {user_id}")
        
        return session
    
    def update_status(self,
                     session_id: str,
                     status: str,
                     details: Optional[Dict[str, Any]] = None) -> VerificationStatus:
        """
        Update verification session status.
        
        Args:
            session_id: Session to update
            status: New status
            details: Additional status details
        
        Returns:
            Updated verification status
        """
        # Get current status
        query = "SELECT * FROM verification_status WHERE session_id = ?"
        rows = self.database.query(query, (session_id,))
        
        if not rows:
            raise ValueError(f"Session {session_id} not found")
        
        row = rows[0]
        
        # Create updated status
        session = VerificationStatus(
            session_id=session_id,
            user_id=row["user_id"],
            workflow_type=row["workflow_type"],
            status=status,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.now(),
            well_ids=json.loads(row["well_ids"]),
            details={**json.loads(row["details"]), **(details or {})},
            checkpoint_data=json.loads(row["checkpoint_data"]) if row["checkpoint_data"] else None
        )
        
        self.database.insert_verification_status(session)
        logger.info(f"Updated session {session_id} status to {status}")
        
        return session
    
    def save_checkpoint(self,
                       session_id: str,
                       checkpoint_data: Dict[str, Any]) -> VerificationStatus:
        """
        Save checkpoint for session.
        
        Args:
            session_id: Session to checkpoint
            checkpoint_data: Data to save
        
        Returns:
            Updated session with checkpoint
        """
        # Get current session
        query = "SELECT * FROM verification_status WHERE session_id = ?"
        rows = self.database.query(query, (session_id,))
        
        if not rows:
            raise ValueError(f"Session {session_id} not found")
        
        row = rows[0]
        
        # Update with checkpoint
        session = VerificationStatus(
            session_id=session_id,
            user_id=row["user_id"],
            workflow_type=row["workflow_type"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.now(),
            well_ids=json.loads(row["well_ids"]),
            details=json.loads(row["details"]),
            checkpoint_data=checkpoint_data
        )
        
        self.database.insert_verification_status(session)
        logger.info(f"Saved checkpoint for session {session_id}")
        
        return session
    
    def restore_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore checkpoint for session.
        
        Args:
            session_id: Session to restore
        
        Returns:
            Checkpoint data if exists
        """
        query = "SELECT checkpoint_data FROM verification_status WHERE session_id = ?"
        rows = self.database.query(query, (session_id,))
        
        if not rows or not rows[0]["checkpoint_data"]:
            return None
        
        checkpoint = json.loads(rows[0]["checkpoint_data"])
        logger.info(f"Restored checkpoint for session {session_id}")
        
        return checkpoint
    
    def get_session_history(self,
                           user_id: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get verification session history.
        
        Args:
            user_id: Filter by user
            status: Filter by status
            limit: Maximum results
        
        Returns:
            List of session information
        """
        query = "SELECT * FROM verification_status WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        rows = self.database.query(query, tuple(params))
        
        sessions = []
        for row in rows:
            details = json.loads(row["details"])
            sessions.append({
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "workflow_type": row["workflow_type"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "well_count": len(json.loads(row["well_ids"])),
                "verified_wells": details.get("verified_wells", 0)
            })
        
        return sessions
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active verification sessions."""
        return self.get_session_history(status="in_progress")
    
    def complete_session(self,
                        session_id: str,
                        summary: Dict[str, Any]) -> VerificationStatus:
        """
        Complete verification session.
        
        Args:
            session_id: Session to complete
            summary: Session summary data
        
        Returns:
            Updated session
        """
        details = {
            **summary,
            "end_time": datetime.now().isoformat()
        }
        
        return self.update_status(session_id, "completed", details)


class DataLineageTracker:
    """
    Tracks data lineage and transformations.
    
    Maintains complete audit trail of data sources, transformations,
    and dependencies for compliance and impact analysis.
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize lineage tracker.
        
        Args:
            db_path: Path to audit database
        """
        self.db_path = Path(db_path)
        self.database = AuditDatabase(db_path)
    
    def track_source(self,
                    data_id: str,
                    source_type: str,
                    source_location: str,
                    fetch_timestamp: datetime,
                    metadata: Optional[Dict[str, Any]] = None) -> DataLineage:
        """
        Track data source.
        
        Args:
            data_id: Unique identifier for data
            source_type: Type of source (API, CSV, Database)
            source_location: Source location/URL
            fetch_timestamp: When data was fetched
            metadata: Additional source metadata
        
        Returns:
            Created lineage record
        """
        lineage = DataLineage(
            data_id=data_id,
            source_type=source_type,
            source_location=source_location,
            fetch_timestamp=fetch_timestamp,
            metadata=metadata or {}
        )
        
        self.database.insert_data_lineage(lineage)
        logger.info(f"Tracked data source: {data_id} from {source_type}")
        
        return lineage
    
    def track_transformation(self,
                           source_id: str,
                           target_id: str,
                           transformation_type: str,
                           operations: List[str]) -> DataLineage:
        """
        Track data transformation.
        
        Args:
            source_id: Source data identifier
            target_id: Target data identifier
            transformation_type: Type of transformation
            operations: List of operations performed
        
        Returns:
            Created lineage record
        """
        lineage = DataLineage(
            data_id=target_id,
            source_id=source_id,
            target_id=target_id,
            transformation_type=transformation_type,
            operations=operations
        )
        
        self.database.insert_data_lineage(lineage)
        logger.info(f"Tracked transformation: {source_id} -> {target_id}")
        
        return lineage
    
    def get_lineage_chain(self, data_id: str) -> List[Dict[str, Any]]:
        """
        Get complete lineage chain for data.
        
        Args:
            data_id: Data identifier
        
        Returns:
            List of lineage records in chain
        """
        chain = []
        current_id = data_id
        visited = set()
        
        while current_id and current_id not in visited:
            visited.add(current_id)
            
            # Get lineage record
            query = "SELECT * FROM data_lineage WHERE data_id = ? OR target_id = ?"
            rows = self.database.query(query, (current_id, current_id))
            
            if not rows:
                break
            
            row = rows[0]
            chain.append({
                "data_id": row["data_id"],
                "source_id": row["source_id"],
                "source_type": row["source_type"],
                "transformation_type": row["transformation_type"],
                "operations": json.loads(row["operations"]) if row["operations"] else [],
                "timestamp": row["timestamp"]
            })
            
            # Move to source
            current_id = row["source_id"]
        
        return list(reversed(chain))
    
    def analyze_impact(self, data_id: str) -> Dict[str, Any]:
        """
        Analyze impact of changes to data.
        
        Args:
            data_id: Data identifier
        
        Returns:
            Impact analysis results
        """
        # Find direct dependencies
        query = "SELECT * FROM data_lineage WHERE source_id = ?"
        direct_deps = self.database.query(query, (data_id,))
        
        direct_dependencies = []
        for dep in direct_deps:
            direct_dependencies.append(dep["target_id"] or dep["data_id"])
        
        # Find indirect dependencies (recursive)
        indirect_dependencies = []
        to_check = direct_dependencies.copy()
        checked = {data_id}
        
        while to_check:
            current = to_check.pop(0)
            if current in checked:
                continue
            
            checked.add(current)
            
            # Get dependencies of current
            deps = self.database.query(query, (current,))
            for dep in deps:
                dep_id = dep["target_id"] or dep["data_id"]
                if dep_id not in direct_dependencies:
                    indirect_dependencies.append(dep_id)
                    to_check.append(dep_id)
        
        return {
            "data_id": data_id,
            "direct_dependencies": direct_dependencies,
            "indirect_dependencies": indirect_dependencies,
            "total_impact": len(direct_dependencies) + len(indirect_dependencies)
        }
    
    def get_data_provenance(self, data_id: str) -> Dict[str, Any]:
        """
        Get complete data provenance information.
        
        Args:
            data_id: Data identifier
        
        Returns:
            Provenance information
        """
        chain = self.get_lineage_chain(data_id)
        
        if not chain:
            return {"data_id": data_id, "provenance": "unknown"}
        
        # Get original source
        origin = chain[0]
        
        # Get all transformations
        transformations = []
        for i in range(1, len(chain)):
            if chain[i]["transformation_type"]:
                transformations.append({
                    "type": chain[i]["transformation_type"],
                    "operations": chain[i]["operations"],
                    "timestamp": chain[i]["timestamp"]
                })
        
        return {
            "data_id": data_id,
            "origin": {
                "source_type": origin["source_type"],
                "timestamp": origin["timestamp"]
            },
            "transformations": transformations,
            "transformation_count": len(transformations)
        }