"""
Tests for verification workflow engine with state management.
Tests the complete workflow lifecycle including checkpoints and persistence.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

from worldenergydata.modules.analysis.verification.config import VerificationConfig
from worldenergydata.modules.analysis.verification.engine.progress import (
    ProgressTracker,
    StepStatus,
)
from worldenergydata.modules.analysis.verification.engine.validators import (
    StepValidator,
    WorkflowValidator,
)
from worldenergydata.modules.analysis.verification.engine.workflow import (
    WorkflowCheckpoint,
    WorkflowEngine,
    WorkflowSession,
    WorkflowState,
    WorkflowStep,
)


class TestWorkflowState:
    """Test workflow state management."""

    def test_workflow_state_enum(self):
        """Test WorkflowState enum values."""
        assert WorkflowState.NOT_STARTED.value == "not_started"
        assert WorkflowState.IN_PROGRESS.value == "in_progress"
        assert WorkflowState.PAUSED.value == "paused"
        assert WorkflowState.COMPLETED.value == "completed"
        assert WorkflowState.FAILED.value == "failed"
        assert WorkflowState.CANCELLED.value == "cancelled"

    def test_state_transitions(self):
        """Test valid state transitions."""
        # Valid transitions
        assert WorkflowState.can_transition(
            WorkflowState.NOT_STARTED, WorkflowState.IN_PROGRESS
        )
        assert WorkflowState.can_transition(
            WorkflowState.IN_PROGRESS, WorkflowState.PAUSED
        )
        assert WorkflowState.can_transition(
            WorkflowState.PAUSED, WorkflowState.IN_PROGRESS
        )
        assert WorkflowState.can_transition(
            WorkflowState.IN_PROGRESS, WorkflowState.COMPLETED
        )
        assert WorkflowState.can_transition(
            WorkflowState.IN_PROGRESS, WorkflowState.FAILED
        )

        # Invalid transitions
        assert not WorkflowState.can_transition(
            WorkflowState.COMPLETED, WorkflowState.IN_PROGRESS
        )
        assert not WorkflowState.can_transition(
            WorkflowState.FAILED, WorkflowState.COMPLETED
        )

    def test_is_terminal_state(self):
        """Test terminal state identification."""
        assert not WorkflowState.is_terminal(WorkflowState.NOT_STARTED)
        assert not WorkflowState.is_terminal(WorkflowState.IN_PROGRESS)
        assert not WorkflowState.is_terminal(WorkflowState.PAUSED)
        assert WorkflowState.is_terminal(WorkflowState.COMPLETED)
        assert WorkflowState.is_terminal(WorkflowState.FAILED)
        assert WorkflowState.is_terminal(WorkflowState.CANCELLED)


class TestWorkflowStep:
    """Test individual workflow steps."""

    def test_workflow_step_creation(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            name="validate_data",
            description="Validate input data",
            order=1,
            required=True,
            timeout_seconds=300,
        )

        assert step.name == "validate_data"
        assert step.description == "Validate input data"
        assert step.order == 1
        assert step.required is True
        assert step.timeout_seconds == 300
        assert step.status == StepStatus.PENDING

    def test_step_execution(self):
        """Test executing a workflow step."""
        step = WorkflowStep(name="test_step", description="Test step", order=1)

        # Execute step
        result = step.execute(data={"test": "data"})

        assert step.status == StepStatus.COMPLETED
        assert step.start_time is not None
        assert step.end_time is not None
        assert step.duration_seconds >= 0  # Duration can be 0 for very fast operations
        assert result["success"] is True

    def test_step_validation(self):
        """Test step input/output validation."""
        step = WorkflowStep(
            name="validated_step",
            description="Step with validation",
            order=1,
            input_schema={"type": "object", "required": ["data"]},
            output_schema={"type": "object", "required": ["result"]},
        )

        # Valid input
        assert step.validate_input({"data": "test"}) is True

        # Invalid input
        assert step.validate_input({"invalid": "data"}) is False

    def test_step_retry_logic(self):
        """Test step retry on failure."""
        step = WorkflowStep(
            name="retry_step", description="Step with retry", order=1, max_retries=3
        )

        # Simulate failures then success
        step.fail_count = 2
        result = step.execute(data={})

        assert step.retry_count == 0  # Reset after success
        assert step.status == StepStatus.COMPLETED


class TestWorkflowSession:
    """Test workflow session management."""

    def test_session_creation(self):
        """Test creating a workflow session."""
        session = WorkflowSession(
            session_id="TEST-001", user="test_user", workflow_type="well_verification"
        )

        assert session.session_id == "TEST-001"
        assert session.user == "test_user"
        assert session.workflow_type == "well_verification"
        assert session.state == WorkflowState.NOT_STARTED
        assert session.created_at is not None

    def test_session_metadata(self):
        """Test session metadata management."""
        session = WorkflowSession(session_id="TEST-002", user="test_user")

        # Add metadata
        session.add_metadata("data_source", "bsee_production")
        session.add_metadata("well_count", 100)

        assert session.metadata["data_source"] == "bsee_production"
        assert session.metadata["well_count"] == 100

    def test_session_context(self):
        """Test session context for data sharing."""
        session = WorkflowSession(session_id="TEST-003", user="test_user")

        # Set context data
        session.set_context("validated_data", {"wells": [1, 2, 3]})

        # Get context data
        data = session.get_context("validated_data")
        assert data["wells"] == [1, 2, 3]

        # Clear context
        session.clear_context()
        assert session.get_context("validated_data") is None


class TestWorkflowEngine:
    """Test the main workflow engine."""

    def test_engine_initialization(self):
        """Test workflow engine initialization."""
        config = VerificationConfig()
        engine = WorkflowEngine(config=config)

        assert engine.config == config
        assert len(engine.steps) > 0
        assert engine.current_session is None

    def test_start_workflow(self):
        """Test starting a new workflow."""
        engine = WorkflowEngine()

        session = engine.start_workflow(user="test_user", data_source="test_data.csv")

        assert session is not None
        assert engine.current_session == session
        assert session.state == WorkflowState.IN_PROGRESS
        assert engine.get_current_step() is not None

    def test_execute_next_step(self):
        """Test executing the next workflow step."""
        engine = WorkflowEngine()
        engine.start_workflow(user="test_user")

        # Execute first step
        result = engine.execute_next_step(data={"test": "data"})

        assert result["success"] is True
        assert engine.get_progress()["completed_steps"] == 1

    def test_skip_optional_step(self):
        """Test skipping optional steps."""
        engine = WorkflowEngine()
        engine.start_workflow(user="test_user")

        # Get current step
        current_step = engine.get_current_step()
        if not current_step.required:
            result = engine.skip_step(reason="Not needed for this dataset")
            assert result["skipped"] is True
            assert current_step.status == StepStatus.SKIPPED

    def test_pause_and_resume_workflow(self):
        """Test pausing and resuming workflow."""
        engine = WorkflowEngine()
        session = engine.start_workflow(user="test_user")

        # Pause workflow
        engine.pause_workflow()
        assert session.state == WorkflowState.PAUSED

        # Resume workflow
        engine.resume_workflow()
        assert session.state == WorkflowState.IN_PROGRESS

    def test_cancel_workflow(self):
        """Test cancelling a workflow."""
        engine = WorkflowEngine()
        session = engine.start_workflow(user="test_user")

        # Cancel workflow
        engine.cancel_workflow(reason="User requested cancellation")
        assert session.state == WorkflowState.CANCELLED
        assert engine.current_session is None

    def test_complete_workflow(self):
        """Test completing all workflow steps."""
        engine = WorkflowEngine()
        engine.start_workflow(user="test_user")

        # Execute all steps
        while not engine.is_complete():
            result = engine.execute_next_step(data={})
            assert result["success"] is True

        assert engine.current_session.state == WorkflowState.COMPLETED
        assert engine.get_progress()["percentage"] == 100


class TestWorkflowCheckpoint:
    """Test workflow checkpoint functionality."""

    def test_create_checkpoint(self):
        """Test creating a workflow checkpoint."""
        engine = WorkflowEngine()
        session = engine.start_workflow(user="test_user")

        # Execute some steps
        engine.execute_next_step(data={})

        # Create checkpoint
        checkpoint = engine.create_checkpoint()

        assert checkpoint is not None
        assert checkpoint.session_id == session.session_id
        assert checkpoint.state == session.state.value  # Compare with enum value
        assert len(checkpoint.completed_steps) > 0

    def test_save_checkpoint_to_file(self):
        """Test saving checkpoint to file."""
        engine = WorkflowEngine()
        engine.start_workflow(user="test_user")
        engine.execute_next_step(data={})

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save checkpoint
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            engine.save_checkpoint(checkpoint_path)

            assert checkpoint_path.exists()

            # Verify checkpoint content
            with open(checkpoint_path, "r") as f:
                checkpoint_data = json.load(f)

            assert "session_id" in checkpoint_data
            assert "state" in checkpoint_data
            assert "completed_steps" in checkpoint_data

    def test_restore_from_checkpoint(self):
        """Test restoring workflow from checkpoint."""
        # Create and save checkpoint
        engine1 = WorkflowEngine()
        session1 = engine1.start_workflow(user="test_user")
        engine1.execute_next_step(data={"step1": "data"})

        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = Path(tmpdir) / "checkpoint.json"
            engine1.save_checkpoint(checkpoint_path)

            # Restore in new engine
            engine2 = WorkflowEngine()
            engine2.restore_from_checkpoint(checkpoint_path)

            assert engine2.current_session is not None
            assert engine2.current_session.session_id == session1.session_id
            assert len(engine2.get_completed_steps()) == 1

    def test_auto_checkpoint(self):
        """Test automatic checkpoint creation."""
        engine = WorkflowEngine(auto_checkpoint=True, checkpoint_interval=2)
        engine.start_workflow(user="test_user")

        # Execute steps
        engine.execute_next_step(data={})
        assert engine.last_checkpoint is None  # Not yet at interval

        engine.execute_next_step(data={})
        assert engine.last_checkpoint is not None  # Auto checkpoint created


class TestProgressTracker:
    """Test workflow progress tracking."""

    def test_progress_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker(total_steps=10)

        assert tracker.total_steps == 10
        assert tracker.completed_steps == 0
        assert tracker.failed_steps == 0
        assert tracker.skipped_steps == 0
        assert tracker.get_percentage() == 0

    def test_update_progress(self):
        """Test updating progress."""
        tracker = ProgressTracker(total_steps=10)

        # Complete some steps
        tracker.mark_completed("step1")
        tracker.mark_completed("step2")
        assert tracker.completed_steps == 2
        assert tracker.get_percentage() == 20

        # Skip a step
        tracker.mark_skipped("step3")
        assert tracker.skipped_steps == 1
        assert tracker.get_percentage() == 30  # Skipped counts as progress

        # Fail a step
        tracker.mark_failed("step4")
        assert tracker.failed_steps == 1
        assert tracker.get_percentage() == 30  # Failed doesn't count

    def test_progress_report(self):
        """Test generating progress report."""
        tracker = ProgressTracker(total_steps=5)
        tracker.mark_completed("step1")
        tracker.mark_completed("step2")
        tracker.mark_skipped("step3")

        report = tracker.get_report()

        assert report["total_steps"] == 5
        assert report["completed_steps"] == 2
        assert report["skipped_steps"] == 1
        assert report["failed_steps"] == 0
        assert report["percentage"] == 60
        assert report["status"] == "in_progress"

    def test_estimated_time_remaining(self):
        """Test estimating time remaining."""
        tracker = ProgressTracker(total_steps=10)
        tracker.start_tracking()  # Start tracking to set start_time

        # Simulate step execution with timing
        import time

        tracker.mark_completed("step1")
        time.sleep(0.1)
        tracker.mark_completed("step2")

        estimate = tracker.estimate_time_remaining()
        assert estimate is not None
        assert estimate > 0


class TestWorkflowValidator:
    """Test workflow validation."""

    def test_validate_workflow_config(self):
        """Test validating workflow configuration."""
        validator = WorkflowValidator()

        valid_config = {
            "workflow_steps": ["step1", "step2", "step3"],
            "timeout_seconds": 3600,
            "max_retries": 3,
        }

        assert validator.validate_config(valid_config) is True

        invalid_config = {"workflow_steps": []}  # Empty steps

        assert validator.validate_config(invalid_config) is False

    def test_validate_step_dependencies(self):
        """Test validating step dependencies."""
        validator = WorkflowValidator()

        steps = [
            WorkflowStep("step1", "Step 1", order=1),
            WorkflowStep("step2", "Step 2", order=2, depends_on=["step1"]),
            WorkflowStep("step3", "Step 3", order=3, depends_on=["step2"]),
        ]

        assert validator.validate_dependencies(steps) is True

        # Circular dependency
        steps[0].depends_on = ["step3"]
        assert validator.validate_dependencies(steps) is False

    def test_validate_input_data(self):
        """Test validating workflow input data."""
        validator = StepValidator()

        schema = {
            "type": "object",
            "properties": {
                "well_data": {"type": "array"},
                "date_range": {"type": "object"},
            },
            "required": ["well_data"],
        }

        valid_data = {
            "well_data": [1, 2, 3],
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
        }

        assert validator.validate_input(valid_data, schema) is True

        invalid_data = {"date_range": {"start": "2024-01-01"}}  # Missing required field

        assert validator.validate_input(invalid_data, schema) is False


@pytest.fixture
def workflow_config():
    """Fixture providing test workflow configuration."""
    return {
        "workflow_steps": [
            "load_data",
            "validate_structure",
            "check_completeness",
            "validate_ranges",
            "detect_anomalies",
            "generate_report",
        ],
        "step_config": {
            "load_data": {"required": True, "timeout": 300},
            "validate_structure": {"required": True, "timeout": 60},
            "check_completeness": {"required": True, "timeout": 120},
            "validate_ranges": {"required": True, "timeout": 120},
            "detect_anomalies": {"required": False, "timeout": 180},
            "generate_report": {"required": True, "timeout": 300},
        },
    }


@pytest.fixture
def sample_workflow_data():
    """Fixture providing sample data for workflow testing."""
    return {
        "data_source": "test_data.csv",
        "well_data": pd.DataFrame(
            {
                "WELL_ID": ["W-001", "W-002", "W-003"],
                "PRODUCTION_DATE": pd.to_datetime(
                    ["2024-01-01", "2024-01-01", "2024-01-01"]
                ),
                "OIL_VOLUME": [1000, 1200, 1500],
                "GAS_VOLUME": [500, 600, 750],
            }
        ),
        "validation_rules": {
            "oil_min": 0,
            "oil_max": 10000,
            "gas_min": 0,
            "gas_max": 5000,
        },
    }
