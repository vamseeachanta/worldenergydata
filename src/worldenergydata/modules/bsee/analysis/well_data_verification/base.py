"""
Base classes for well data verification system.

Extends the existing validation framework with verification-specific functionality.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
import json
from dataclasses import dataclass, field

from worldenergydata.validation.base import ValidationError, ValidationResult
from worldenergydata.validation.validators import DataValidator
from worldenergydata.validation.schema import ValidationSchema
from worldenergydata.common import get_logger

logger = get_logger(__name__)


class VerificationError(ValidationError):
    """
    Verification-specific error that extends ValidationError.
    Adds well-specific context and verification metadata.
    """
    
    def __init__(self, 
                 field: str,
                 message: str,
                 value: Any = None,
                 rule: str = None,
                 severity: str = 'error',
                 row_index: Optional[int] = None,
                 well_id: Optional[str] = None,
                 lease_num: Optional[str] = None):
        """
        Initialize verification error with additional well context.
        
        Args:
            field: Field that failed verification
            message: Error message
            value: The invalid value
            rule: Rule that was violated
            severity: Error severity level
            row_index: Row index in dataset
            well_id: Well identifier
            lease_num: Lease number
        """
        super().__init__(field, message, value, rule, severity, row_index)
        self.well_id = well_id
        self.lease_num = lease_num
    
    def __str__(self) -> str:
        """String representation with well context."""
        base_str = super().__str__()
        context = []
        if self.well_id:
            context.append(f"Well: {self.well_id}")
        if self.lease_num:
            context.append(f"Lease: {self.lease_num}")
        
        if context:
            return f"{base_str} ({', '.join(context)})"
        return base_str


@dataclass
class VerificationResult(ValidationResult):
    """
    Container for verification results extending ValidationResult.
    Adds verification-specific metadata and audit trail capabilities.
    """
    
    # Verification-specific fields
    verification_id: Optional[str] = None
    verified_by: Optional[str] = None
    verification_timestamp: Optional[datetime] = None
    workflow_state: str = "initialized"
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    checkpoint_path: Optional[Path] = None
    
    def __post_init__(self):
        """Initialize verification timestamp if not provided."""
        if self.verification_timestamp is None:
            self.verification_timestamp = datetime.now()
    
    def add_verification_error(self,
                               field: str,
                               message: str,
                               severity: str = 'error',
                               well_id: Optional[str] = None,
                               **kwargs) -> None:
        """
        Add a verification-specific error.
        
        Args:
            field: Field that failed verification
            message: Error message  
            severity: Error severity
            well_id: Well identifier
            **kwargs: Additional error context
        """
        error = VerificationError(
            field=field,
            message=message,
            severity=severity,
            well_id=well_id,
            **kwargs
        )
        
        if severity == 'error':
            self.errors.append(error)
        elif severity == 'warning':
            self.warnings.append(error)
        else:
            self.info.append(error)
        
        # Add to audit trail
        self.add_audit_entry(
            action=f"verification_{severity}",
            details={
                'field': field,
                'message': message,
                'well_id': well_id
            }
        )
    
    def add_audit_entry(self,
                       action: str,
                       user: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an entry to the audit trail.
        
        Args:
            action: Action performed
            user: User who performed the action
            details: Additional details about the action
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'user': user or self.verified_by,
            'details': details or {}
        }
        self.audit_trail.append(entry)
        logger.debug(f"Audit entry added: {action}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        base_dict = {
            'verification_id': self.verification_id,
            'verified_by': self.verified_by,
            'verification_timestamp': self.verification_timestamp.isoformat() if self.verification_timestamp else None,
            'workflow_state': self.workflow_state,
            'is_valid': self.is_valid,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'audit_trail': self.audit_trail
        }
        return base_dict


class VerificationWorkflow(DataValidator):
    """
    Workflow engine for systematic data verification.
    Extends DataValidator with state management and checkpoint capabilities.
    """
    
    def __init__(self,
                 schema: Optional[ValidationSchema] = None,
                 config: Optional['VerificationConfig'] = None,
                 strict: bool = True):
        """
        Initialize verification workflow.
        
        Args:
            schema: Validation schema to use
            config: Verification configuration
            strict: If True, raise exceptions on errors
        """
        # Initialize parent with empty schema if none provided
        super().__init__(schema or ValidationSchema(name="verification", fields={}), strict)
        
        self.config = config
        self.current_state = "not_started"
        self.steps_completed = []
        self.current_result: Optional[VerificationResult] = None
        self.checkpoint_dir = Path("checkpoints")
        
        # Define workflow steps
        self.workflow_steps = [
            "load_data",
            "validate_structure",
            "check_completeness",
            "validate_ranges",
            "detect_anomalies",
            "cross_reference",
            "generate_report"
        ]
        self.total_steps = len(self.workflow_steps)
    
    def start_verification(self,
                          data_source: str,
                          user: str,
                          verification_id: Optional[str] = None) -> VerificationResult:
        """
        Start a new verification workflow.
        
        Args:
            data_source: Source of data to verify
            user: User initiating verification
            verification_id: Optional ID for this verification
            
        Returns:
            VerificationResult instance
        """
        # Create new result
        self.current_result = VerificationResult(
            verification_id=verification_id or self._generate_verification_id(),
            verified_by=user,
            workflow_state="in_progress"
        )
        
        # Update state
        self.current_state = "in_progress"
        self.steps_completed = []
        
        # Add audit entry
        self.current_result.add_audit_entry(
            action="verification_started",
            user=user,
            details={'data_source': data_source}
        )
        
        logger.info(f"Started verification workflow: {self.current_result.verification_id}")
        return self.current_result
    
    def execute_step(self, step_name: str) -> Dict[str, Any]:
        """
        Execute a specific workflow step.
        
        Args:
            step_name: Name of step to execute
            
        Returns:
            Dictionary with step execution results
        """
        if self.current_state == "not_started":
            raise RuntimeError("Workflow not started. Call start_verification first.")
        
        if step_name not in self.workflow_steps:
            raise ValueError(f"Unknown step: {step_name}")
        
        # Execute step (placeholder for actual implementation)
        result = {
            'step': step_name,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        }
        
        # Update tracking
        if step_name not in self.steps_completed:
            self.steps_completed.append(step_name)
        
        # Add audit entry
        if self.current_result:
            self.current_result.add_audit_entry(
                action=f"step_executed",
                details={'step': step_name, 'status': result['status']}
            )
        
        # Check if all steps completed
        if len(self.steps_completed) == self.total_steps:
            self.current_state = "completed"
            if self.current_result:
                self.current_result.workflow_state = "completed"
        
        logger.debug(f"Executed step {step_name}: {result['status']}")
        return result
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current workflow state.
        
        Returns:
            Dictionary with current state information
        """
        return {
            'state': self.current_state,
            'steps_completed': self.steps_completed,
            'total_steps': self.total_steps,
            'progress_percentage': (len(self.steps_completed) / self.total_steps * 100) if self.total_steps > 0 else 0
        }
    
    def save_checkpoint(self) -> Path:
        """
        Save current workflow state to checkpoint.
        
        Returns:
            Path to checkpoint file
        """
        if not self.current_result:
            raise RuntimeError("No active verification to checkpoint")
        
        # Create checkpoint directory
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Generate checkpoint filename
        checkpoint_file = self.checkpoint_dir / f"{self.current_result.verification_id}_checkpoint.json"
        
        # Prepare checkpoint data
        checkpoint_data = {
            'verification_id': self.current_result.verification_id,
            'verified_by': self.current_result.verified_by,
            'workflow_state': self.current_state,
            'steps_completed': self.steps_completed,
            'timestamp': datetime.now().isoformat(),
            'result': self.current_result.to_dict()
        }
        
        # Save checkpoint
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        self.current_result.checkpoint_path = checkpoint_file
        logger.info(f"Saved checkpoint to {checkpoint_file}")
        return checkpoint_file
    
    def resume_from_checkpoint(self, checkpoint_path: Path) -> None:
        """
        Resume workflow from checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint file
        """
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        # Load checkpoint
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        
        # Restore state
        self.current_state = checkpoint_data['workflow_state']
        self.steps_completed = checkpoint_data['steps_completed']
        
        # Restore result
        self.current_result = VerificationResult(
            verification_id=checkpoint_data['verification_id'],
            verified_by=checkpoint_data['verified_by'],
            workflow_state=checkpoint_data['workflow_state']
        )
        self.current_result.audit_trail = checkpoint_data['result']['audit_trail']
        
        # Add audit entry for resume
        self.current_result.add_audit_entry(
            action="verification_resumed",
            details={'checkpoint': str(checkpoint_path)}
        )
        
        logger.info(f"Resumed workflow from checkpoint: {checkpoint_path}")
    
    def _generate_verification_id(self) -> str:
        """Generate unique verification ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"VER-{timestamp}"