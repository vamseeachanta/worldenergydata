"""
Tests for well data verification core infrastructure.
Tests the extension of existing validation framework with verification-specific components.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

# These imports will be implemented in the next steps
from worldenergydata.modules.analysis.verification.base import (
    VerificationError,
    VerificationResult,
    VerificationWorkflow,
)
from worldenergydata.modules.analysis.verification.config import VerificationConfig
from worldenergydata.modules.analysis.verification.processors import BSEEDataAdapter


class TestVerificationResult:
    """Test VerificationResult class that extends ValidationResult."""

    def test_verification_result_extends_validation_result(self):
        """Verify that VerificationResult properly extends ValidationResult."""
        result = VerificationResult()

        # Should have base ValidationResult properties
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "is_valid")

        # Should have verification-specific properties
        assert hasattr(result, "verification_id")
        assert hasattr(result, "workflow_state")
        assert hasattr(result, "audit_trail")
        assert hasattr(result, "verified_by")
        assert hasattr(result, "verification_timestamp")

    def test_verification_result_initialization(self):
        """Test proper initialization of VerificationResult."""
        result = VerificationResult(verification_id="VER-001", verified_by="test_user")

        assert result.verification_id == "VER-001"
        assert result.verified_by == "test_user"
        assert result.workflow_state == "initialized"
        assert isinstance(result.audit_trail, list)
        assert result.is_valid is True  # No errors initially

    def test_add_verification_error(self):
        """Test adding verification-specific errors."""
        result = VerificationResult()

        result.add_verification_error(
            field="production_volume",
            message="Volume exceeds threshold",
            severity="error",
            well_id="W-12345",
        )

        assert len(result.errors) == 1
        assert result.is_valid is False
        error = result.errors[0]
        assert error.field == "production_volume"
        assert "W-12345" in str(error)

    def test_audit_trail_tracking(self):
        """Test audit trail functionality."""
        result = VerificationResult()

        result.add_audit_entry(
            action="validation_started",
            user="test_user",
            details={"step": "production_check"},
        )

        assert len(result.audit_trail) == 1
        entry = result.audit_trail[0]
        assert entry["action"] == "validation_started"
        assert entry["user"] == "test_user"
        assert "timestamp" in entry


class TestVerificationWorkflow:
    """Test VerificationWorkflow class that extends DataValidator."""

    def test_workflow_extends_data_validator(self):
        """Verify that VerificationWorkflow properly extends DataValidator."""
        workflow = VerificationWorkflow()

        # Should have base DataValidator methods
        assert hasattr(workflow, "validate")
        assert hasattr(workflow, "schema")
        assert hasattr(workflow, "strict")

        # Should have workflow-specific methods
        assert hasattr(workflow, "start_verification")
        assert hasattr(workflow, "execute_step")
        assert hasattr(workflow, "get_current_state")
        assert hasattr(workflow, "save_checkpoint")
        assert hasattr(workflow, "resume_from_checkpoint")

    def test_workflow_initialization(self):
        """Test proper initialization of workflow."""
        config = VerificationConfig(config_path="test_config.yaml")
        workflow = VerificationWorkflow(config=config)

        assert workflow.config == config
        assert workflow.current_state == "not_started"
        assert workflow.steps_completed == []
        assert workflow.total_steps is not None

    def test_start_verification_workflow(self):
        """Test starting a verification workflow."""
        workflow = VerificationWorkflow()

        result = workflow.start_verification(
            data_source="bsee_production", user="test_user"
        )

        assert isinstance(result, VerificationResult)
        assert workflow.current_state == "in_progress"
        assert result.verified_by == "test_user"
        assert result.workflow_state == "in_progress"

    def test_execute_workflow_step(self):
        """Test executing a workflow step."""
        workflow = VerificationWorkflow()
        workflow.start_verification(data_source="test", user="test_user")

        # Execute first step
        step_result = workflow.execute_step("load_data")

        assert step_result["status"] in ["success", "failed", "skipped"]
        assert "load_data" in workflow.steps_completed
        assert workflow.current_state != "not_started"

    def test_workflow_checkpoint_persistence(self):
        """Test saving and resuming from checkpoints."""
        workflow = VerificationWorkflow()
        workflow.start_verification(data_source="test", user="test_user")
        workflow.execute_step("load_data")

        # Save checkpoint
        checkpoint_path = workflow.save_checkpoint()
        assert checkpoint_path.exists()

        # Create new workflow and resume
        new_workflow = VerificationWorkflow()
        new_workflow.resume_from_checkpoint(checkpoint_path)

        assert new_workflow.steps_completed == workflow.steps_completed
        assert new_workflow.current_state == workflow.current_state


class TestVerificationConfig:
    """Test configuration management for verification system."""

    def test_load_yaml_config(self):
        """Test loading configuration from YAML."""
        config = VerificationConfig()

        # Should have default configuration
        assert hasattr(config, "validation_rules")
        assert hasattr(config, "audit_settings")
        assert hasattr(config, "report_templates")
        assert hasattr(config, "workflow_steps")

    def test_config_adapts_bsee_patterns(self):
        """Test that config follows BSEE module patterns."""
        config = VerificationConfig()

        # Should follow same structure as BSEE financial config
        assert "rules" in config.validation_rules
        assert "quality" in config.validation_rules
        assert "thresholds" in config.validation_rules

    def test_config_validation(self):
        """Test configuration validation."""
        config = VerificationConfig()

        # Valid configuration should pass
        assert config.validate()

        # Invalid configuration should raise error
        with pytest.raises(ValueError):
            config.validation_rules["invalid_key"] = "invalid_value"
            config.validate()


class TestBSEEDataAdapter:
    """Test BSEE data processor integration."""

    def test_adapter_imports_bsee_processors(self):
        """Test that adapter properly imports BSEE processors."""
        adapter = BSEEDataAdapter()

        # Should have methods from BSEE processors
        assert hasattr(adapter, "load_production_data")
        assert hasattr(adapter, "process_well_data")
        assert hasattr(adapter, "validate_lease_numbers")

    def test_load_production_data(self):
        """Test loading production data through adapter."""
        adapter = BSEEDataAdapter()

        # Create sample data
        sample_data = pd.DataFrame(
            {
                "WELL_ID": ["W-001", "W-002"],
                "PRODUCTION_DATE": ["2024-01-01", "2024-01-01"],
                "OIL_VOLUME": [1000, 1500],
                "GAS_VOLUME": [500, 750],
            }
        )

        # Process through adapter
        processed = adapter.process_well_data(sample_data)

        assert isinstance(processed, pd.DataFrame)
        assert len(processed) == 2
        assert "WELL_ID" in processed.columns

    def test_validate_with_financial_validators(self):
        """Test using financial validators through adapter."""
        adapter = BSEEDataAdapter()

        sample_data = pd.DataFrame(
            {
                "LEASE_NUM": ["OCS-G 12345", "OCS-G 67890"],
                "PRODUCTION_DATE": ["2024-01-01", "2024-01-01"],
                "OIL_VOLUME": [1000, 1500],
            }
        )

        # Validate using imported validators
        validated = adapter.validate_lease_numbers(sample_data)

        assert "LEASE_NUM" in validated.columns
        # Lease numbers should be normalized
        assert all(lease.startswith("OCS-G") for lease in validated["LEASE_NUM"])


class TestModuleIntegration:
    """Test integration with existing WorldEnergyData modules."""

    def test_imports_validation_base_classes(self):
        """Test that we can import and use base validation classes."""
        from worldenergydata.validation.base import ValidationError, ValidationResult

        # Should be able to create instances
        error = ValidationError(field="test", message="test error")
        assert error.field == "test"

        result = ValidationResult()
        assert result.is_valid is True

    def test_imports_bsee_validators(self):
        """Test importing BSEE financial validators."""
        from worldenergydata.modules.bsee.analysis.financial.validators import (
            validate_numeric_columns,
            validate_required_columns,
        )

        # Should be callable functions
        assert callable(validate_required_columns)
        assert callable(validate_numeric_columns)

    def test_imports_report_exporters(self):
        """Test importing report exporters."""
        # These will be available after comprehensive reports module is complete
        # For now, we'll test the import path exists
        import importlib.util

        spec = importlib.util.find_spec("worldenergydata.modules.bsee.reports")
        assert spec is not None


@pytest.fixture
def sample_well_data():
    """Fixture providing sample well data for testing."""
    return pd.DataFrame(
        {
            "WELL_ID": ["W-001", "W-002", "W-003"],
            "LEASE_NUM": ["OCS-G 12345", "OCS-G 12345", "OCS-G 67890"],
            "PRODUCTION_DATE": pd.to_datetime(
                ["2024-01-01", "2024-02-01", "2024-01-01"]
            ),
            "OIL_VOLUME": [1000, 1200, 1500],
            "GAS_VOLUME": [500, 600, 750],
            "WATER_VOLUME": [100, 120, 150],
        }
    )


@pytest.fixture
def verification_config():
    """Fixture providing test verification configuration."""
    return {
        "validation_rules": {
            "production_volume": {"min": 0, "max": 100000},
            "completeness": {
                "required_fields": ["WELL_ID", "PRODUCTION_DATE", "OIL_VOLUME"]
            },
        },
        "audit_settings": {"enabled": True, "retention_days": 365},
    }
