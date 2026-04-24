"""
Verification and audit views for well detail dashboard.

Contains verification status badges, audit trail links,
and verification summary formatting.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class VerificationStatusBadge:
    """Creates verification status badges."""

    def create(
        self,
        status: str,
        quality_score: float,
        timestamp: datetime,
        details: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Create verification status badge."""
        # Define badge properties based on status
        badge_config = {
            "verified": {"color": "green", "icon": "check", "text": "Verified"},
            "pending": {"color": "yellow", "icon": "warning", "text": "Pending"},
            "failed": {"color": "red", "icon": "x", "text": "Failed"},
        }

        config = badge_config.get(status, badge_config["pending"])

        badge = {
            "status": status,
            "color": config["color"],
            "icon": config["icon"],
            "text": config["text"],
            "quality_score": quality_score,
            "timestamp": (
                timestamp.isoformat()
                if isinstance(timestamp, datetime)
                else str(timestamp)
            ),
            "tooltip": f"{config['text']} - Quality: {quality_score:.2%}",
        }

        if details:
            badge["details"] = details

        return badge


class AuditTrailLink:
    """Creates audit trail links."""

    def create(
        self, well_id: str, verification_id: str, timestamp: datetime
    ) -> Dict[str, str]:
        """Create audit trail link."""
        return {
            "url": f"/api/verification/{well_id}/{verification_id}",
            "text": f"View Audit Trail ({verification_id})",
            "icon": "clipboard",
            "timestamp": (
                timestamp.isoformat()
                if isinstance(timestamp, datetime)
                else str(timestamp)
            ),
        }

    def create_batch(
        self, well_id: str, verification_ids: List[str]
    ) -> List[Dict[str, str]]:
        """Create multiple audit trail links."""
        return [
            self.create(well_id, ver_id, datetime.now()) for ver_id in verification_ids
        ]

    def format_summary(
        self, total_verifications: int, passed: int, failed: int, pending: int
    ) -> Dict[str, Any]:
        """Format audit trail summary."""
        success_rate = passed / total_verifications if total_verifications > 0 else 0

        return {
            "total": total_verifications,
            "passed": passed,
            "failed": failed,
            "pending": pending,
            "success_rate": success_rate,
            "summary_text": (
                f"Verifications: {passed}/{total_verifications} "
                f"passed ({success_rate:.1%})"
            ),
        }


# Export all public names
__all__ = ["VerificationStatusBadge", "AuditTrailLink"]
