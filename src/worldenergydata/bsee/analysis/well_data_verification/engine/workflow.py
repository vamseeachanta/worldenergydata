"""
Workflow engine for verification process orchestration.

Provides state machine-based workflow management with checkpoint support.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from ..config import VerificationConfig
from .progress import ProgressTracker, StepStatus


class WorkflowState(Enum):
    """Workflow state enumeration."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def can_transition(
        cls, from_state: "WorkflowState", to_state: "WorkflowState"
    ) -> bool:
        """
        Check if transition between states is valid.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is valid
        """
        valid_transitions = {
            cls.NOT_STARTED: [cls.IN_PROGRESS, cls.CANCELLED],
            cls.IN_PROGRESS: [cls.PAUSED, cls.COMPLETED, cls.FAILED, cls.CANCELLED],
            cls.PAUSED: [cls.IN_PROGRESS, cls.CANCELLED],
            cls.COMPLETED: [],
            cls.FAILED: [],
            cls.CANCELLED: [],
        }

        return to_state in valid_transitions.get(from_state, [])

    @classmethod
    def is_terminal(cls, state: "WorkflowState") -> bool:
        """
        Check if state is terminal (no further transitions possible).

        Args:
            state: State to check

        Returns:
            True if state is terminal
        """
        return state in [cls.COMPLETED, cls.FAILED, cls.CANCELLED]


@dataclass
class WorkflowStep:
    """Individual workflow step definition."""

    name: str
    description: str
    order: int
    required: bool = True
    timeout_seconds: int = 300
    max_retries: int = 3
    depends_on: List[str] = field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

    # Runtime attributes
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    retry_count: int = 0
    fail_count: int = 0
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the workflow step.

        Args:
            data: Input data for the step

        Returns:
            Execution result
        """
        self.start_time = datetime.now()
        self.status = StepStatus.IN_PROGRESS

        try:
            # Placeholder for actual step execution
            # In real implementation, would call specific validation logic
            logger.info(f"Executing step: {self.name}")

            # Simulate execution
            self.result = {
                "success": True,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }

            self.status = StepStatus.COMPLETED

        except Exception as e:
            self.status = StepStatus.FAILED
            self.error_message = str(e)
            self.fail_count += 1
            logger.error(f"Step {self.name} failed: {e}")
            self.result = {"success": False, "error": str(e)}

        finally:
            self.end_time = datetime.now()
            if self.start_time:
                self.duration_seconds = (
                    self.end_time - self.start_time
                ).total_seconds()

        return self.result

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Validate input data against schema.

        Args:
            data: Input data to validate

        Returns:
            True if valid
        """
        if not self.input_schema:
            return True

        # Simple validation - in real implementation would use jsonschema
        required_fields = self.input_schema.get("required", [])
        for field in required_fields:
            if field not in data:
                return False

        return True

    def validate_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate output data against schema.

        Args:
            data: Output data to validate

        Returns:
            True if valid
        """
        if not self.output_schema:
            return True

        required_fields = self.output_schema.get("required", [])
        for field in required_fields:
            if field not in data:
                return False

        return True


@dataclass
class WorkflowSession:
    """Workflow execution session."""

    session_id: str
    user: str
    workflow_type: str = "verification"
    state: WorkflowState = WorkflowState.NOT_STARTED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to session."""
        self.metadata[key] = value

    def set_context(self, key: str, value: Any) -> None:
        """Set context data for sharing between steps."""
        self.context[key] = value

    def get_context(self, key: str) -> Any:
        """Get context data."""
        return self.context.get(key)

    def clear_context(self) -> None:
        """Clear all context data."""
        self.context.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "user": self.user,
            "workflow_type": self.workflow_type,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "metadata": self.metadata,
            "context": self.context,
        }


@dataclass
class WorkflowCheckpoint:
    """Workflow checkpoint for persistence."""

    session_id: str
    state: str
    completed_steps: List[str]
    current_step: Optional[str]
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "state": self.state,
            "completed_steps": self.completed_steps,
            "current_step": self.current_step,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowCheckpoint":
        """Create checkpoint from dictionary."""
        return cls(
            session_id=data["session_id"],
            state=data["state"],
            completed_steps=data["completed_steps"],
            current_step=data.get("current_step"),
            context=data["context"],
            metadata=data["metadata"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class WorkflowEngine:
    """
    Main workflow engine for verification process orchestration.
    """

    def __init__(
        self,
        config: Optional[VerificationConfig] = None,
        auto_checkpoint: bool = False,
        checkpoint_interval: int = 5,
    ):
        """
        Initialize workflow engine.

        Args:
            config: Verification configuration
            auto_checkpoint: Enable automatic checkpointing
            checkpoint_interval: Steps between auto checkpoints
        """
        self.config = config or VerificationConfig()
        self.auto_checkpoint = auto_checkpoint
        self.checkpoint_interval = checkpoint_interval

        self.current_session: Optional[WorkflowSession] = None
        self.steps: List[WorkflowStep] = []
        self.current_step_index: int = 0
        self.progress_tracker: Optional[ProgressTracker] = None
        self.last_checkpoint: Optional[WorkflowCheckpoint] = None
        self.checkpoint_counter: int = 0

        self._initialize_steps()

    def _initialize_steps(self) -> None:
        """Initialize workflow steps from configuration."""
        step_names = self.config.workflow_steps

        for i, step_name in enumerate(step_names):
            step = WorkflowStep(
                name=step_name,
                description=f"Execute {step_name.replace('_', ' ')}",
                order=i + 1,
                required=True,  # Can be configured per step
            )
            self.steps.append(step)

        logger.info(f"Initialized {len(self.steps)} workflow steps")

    def start_workflow(
        self,
        user: str,
        data_source: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> WorkflowSession:
        """
        Start a new workflow session.

        Args:
            user: User initiating the workflow
            data_source: Optional data source identifier
            session_id: Optional session ID (generated if not provided)

        Returns:
            Created workflow session
        """
        if self.current_session and not WorkflowState.is_terminal(
            self.current_session.state
        ):
            raise RuntimeError("Cannot start new workflow - current workflow is active")

        # Create new session
        self.current_session = WorkflowSession(
            session_id=session_id or self._generate_session_id(), user=user
        )

        # Set metadata
        if data_source:
            self.current_session.add_metadata("data_source", data_source)

        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(total_steps=len(self.steps))

        # Update state
        self.current_session.state = WorkflowState.IN_PROGRESS
        self.current_session.started_at = datetime.now()
        self.current_step_index = 0

        logger.info(f"Started workflow session: {self.current_session.session_id}")
        return self.current_session

    def execute_next_step(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the next workflow step.

        Args:
            data: Input data for the step

        Returns:
            Step execution result
        """
        if not self.current_session:
            raise RuntimeError("No active workflow session")

        if self.current_session.state != WorkflowState.IN_PROGRESS:
            raise RuntimeError(
                f"Workflow not in progress: {self.current_session.state}"
            )

        if self.current_step_index >= len(self.steps):
            # All steps completed
            self._complete_workflow()
            return {"success": True, "message": "Workflow completed"}

        # Get current step
        current_step = self.steps[self.current_step_index]

        # Execute step
        result = current_step.execute(data)

        # Update progress
        if result["success"]:
            self.progress_tracker.mark_completed(current_step.name)
            self.current_step_index += 1

            # Auto checkpoint if enabled
            if self.auto_checkpoint:
                self.checkpoint_counter += 1
                if self.checkpoint_counter >= self.checkpoint_interval:
                    self.last_checkpoint = self.create_checkpoint()
                    self.checkpoint_counter = 0
        else:
            self.progress_tracker.mark_failed(current_step.name)

        return result

    def skip_step(self, reason: str) -> Dict[str, Any]:
        """
        Skip the current step.

        Args:
            reason: Reason for skipping

        Returns:
            Skip result
        """
        if self.current_step_index >= len(self.steps):
            return {"skipped": False, "message": "No step to skip"}

        current_step = self.steps[self.current_step_index]

        if current_step.required:
            return {"skipped": False, "message": "Cannot skip required step"}

        current_step.status = StepStatus.SKIPPED
        self.progress_tracker.mark_skipped(current_step.name)
        self.current_step_index += 1

        logger.info(f"Skipped step {current_step.name}: {reason}")
        return {"skipped": True, "step": current_step.name, "reason": reason}

    def pause_workflow(self) -> None:
        """Pause the current workflow."""
        if not self.current_session:
            raise RuntimeError("No active workflow")

        if WorkflowState.can_transition(
            self.current_session.state, WorkflowState.PAUSED
        ):
            self.current_session.state = WorkflowState.PAUSED
            logger.info("Workflow paused")

    def resume_workflow(self) -> None:
        """Resume a paused workflow."""
        if not self.current_session:
            raise RuntimeError("No active workflow")

        if WorkflowState.can_transition(
            self.current_session.state, WorkflowState.IN_PROGRESS
        ):
            self.current_session.state = WorkflowState.IN_PROGRESS
            logger.info("Workflow resumed")

    def cancel_workflow(self, reason: str) -> None:
        """
        Cancel the current workflow.

        Args:
            reason: Reason for cancellation
        """
        if not self.current_session:
            return

        self.current_session.state = WorkflowState.CANCELLED
        self.current_session.add_metadata("cancellation_reason", reason)
        self.current_session.completed_at = datetime.now()

        logger.info(f"Workflow cancelled: {reason}")
        self.current_session = None

    def _complete_workflow(self) -> None:
        """Mark workflow as completed."""
        if self.current_session:
            self.current_session.state = WorkflowState.COMPLETED
            self.current_session.completed_at = datetime.now()
            logger.info("Workflow completed successfully")

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current workflow step."""
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def get_completed_steps(self) -> List[WorkflowStep]:
        """Get list of completed steps."""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    def get_progress(self) -> Dict[str, Any]:
        """Get workflow progress information."""
        if not self.progress_tracker:
            return {"percentage": 0, "completed_steps": 0, "total_steps": 0}

        return {
            "percentage": self.progress_tracker.get_percentage(),
            "completed_steps": self.progress_tracker.completed_steps,
            "total_steps": self.progress_tracker.total_steps,
            "failed_steps": self.progress_tracker.failed_steps,
            "skipped_steps": self.progress_tracker.skipped_steps,
        }

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return (
            self.current_session
            and self.current_session.state == WorkflowState.COMPLETED
        )

    def create_checkpoint(self) -> WorkflowCheckpoint:
        """
        Create a checkpoint of current workflow state.

        Returns:
            Workflow checkpoint
        """
        if not self.current_session:
            raise RuntimeError("No active workflow to checkpoint")

        checkpoint = WorkflowCheckpoint(
            session_id=self.current_session.session_id,
            state=self.current_session.state.value,
            completed_steps=[s.name for s in self.get_completed_steps()],
            current_step=(
                self.get_current_step().name if self.get_current_step() else None
            ),
            context=self.current_session.context,
            metadata=self.current_session.metadata,
        )

        logger.debug(
            f"Created checkpoint for session {self.current_session.session_id}"
        )
        return checkpoint

    def save_checkpoint(self, filepath: Path) -> None:
        """
        Save checkpoint to file.

        Args:
            filepath: Path to save checkpoint
        """
        checkpoint = self.create_checkpoint()

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        logger.info(f"Saved checkpoint to {filepath}")

    def restore_from_checkpoint(self, filepath: Path) -> None:
        """
        Restore workflow from checkpoint file.

        Args:
            filepath: Path to checkpoint file
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Checkpoint file not found: {filepath}")

        with open(filepath, "r") as f:
            data = json.load(f)

        checkpoint = WorkflowCheckpoint.from_dict(data)

        # Restore session
        self.current_session = WorkflowSession(
            session_id=checkpoint.session_id,
            user="restored_user",  # Would need to store in checkpoint
            state=WorkflowState(checkpoint.state),
        )
        self.current_session.context = checkpoint.context
        self.current_session.metadata = checkpoint.metadata

        # Restore step states
        completed_steps = set(checkpoint.completed_steps)
        for step in self.steps:
            if step.name in completed_steps:
                step.status = StepStatus.COMPLETED

        # Find current step index
        if checkpoint.current_step:
            for i, step in enumerate(self.steps):
                if step.name == checkpoint.current_step:
                    self.current_step_index = i
                    break

        # Restore progress tracker
        self.progress_tracker = ProgressTracker(total_steps=len(self.steps))
        for step_name in completed_steps:
            self.progress_tracker.mark_completed(step_name)

        logger.info(f"Restored workflow from checkpoint: {checkpoint.session_id}")

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"WF-{timestamp}-{unique_id}"
