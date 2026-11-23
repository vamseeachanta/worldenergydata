"""Tests for workflow validators and documentation generator."""

from types import SimpleNamespace

from worldenergydata.bsee.analysis.well_data_verification.engine.validators import (
    StepValidator,
    WorkflowDocumentationGenerator,
    WorkflowValidator,
)


class TestStepValidator:
    def test_init(self):
        sv = StepValidator()
        assert sv.errors == []

    def test_validate_input_valid(self):
        sv = StepValidator()
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        assert sv.validate_input({"name": "test"}, schema) is True

    def test_validate_input_invalid(self):
        sv = StepValidator()
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer"}},
            "required": ["age"],
        }
        result = sv.validate_input({}, schema)
        assert result is False
        assert len(sv.errors) >= 1
        assert "Input validation failed" in sv.errors[0]

    def test_validate_output_valid(self):
        sv = StepValidator()
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        assert sv.validate_output({"result": "ok"}, schema) is True

    def test_validate_output_invalid(self):
        sv = StepValidator()
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
        }
        result = sv.validate_output({"count": "not_int"}, schema)
        assert result is False
        assert len(sv.errors) >= 1
        assert "Output validation failed" in sv.errors[0]

    def test_clear_errors(self):
        sv = StepValidator()
        schema = {"type": "object", "required": ["x"]}
        sv.validate_input({}, schema)
        assert len(sv.errors) > 0
        sv.clear_errors()
        assert sv.errors == []

    def test_get_errors_returns_copy(self):
        sv = StepValidator()
        schema = {"type": "object", "required": ["x"]}
        sv.validate_input({}, schema)
        errors = sv.get_errors()
        errors.clear()
        assert len(sv.errors) > 0


class TestWorkflowValidator:
    def test_init(self):
        wv = WorkflowValidator()
        assert wv.errors == []

    def test_validate_config_valid(self):
        wv = WorkflowValidator()
        config = {"workflow_steps": ["step1", "step2"]}
        assert wv.validate_config(config) is True

    def test_validate_config_missing_steps(self):
        wv = WorkflowValidator()
        assert wv.validate_config({}) is False
        assert "Missing required field" in wv.errors[0]

    def test_validate_config_steps_not_list(self):
        wv = WorkflowValidator()
        assert wv.validate_config({"workflow_steps": "step1"}) is False
        assert "must be a list" in wv.errors[0]

    def test_validate_config_empty_steps(self):
        wv = WorkflowValidator()
        assert wv.validate_config({"workflow_steps": []}) is False
        assert "cannot be empty" in wv.errors[0]

    def test_validate_config_invalid_step_name(self):
        wv = WorkflowValidator()
        assert wv.validate_config({"workflow_steps": [123]}) is False
        assert "Invalid step name" in wv.errors[0]

    def test_validate_config_valid_timeout(self):
        wv = WorkflowValidator()
        config = {"workflow_steps": ["s1"], "timeout_seconds": 60}
        assert wv.validate_config(config) is True

    def test_validate_config_invalid_timeout(self):
        wv = WorkflowValidator()
        config = {"workflow_steps": ["s1"], "timeout_seconds": -1}
        assert wv.validate_config(config) is False
        assert "timeout_seconds" in wv.errors[0]

    def test_validate_config_invalid_timeout_type(self):
        wv = WorkflowValidator()
        config = {"workflow_steps": ["s1"], "timeout_seconds": "sixty"}
        assert wv.validate_config(config) is False

    def test_validate_config_valid_retries(self):
        wv = WorkflowValidator()
        config = {"workflow_steps": ["s1"], "max_retries": 3}
        assert wv.validate_config(config) is True

    def test_validate_config_invalid_retries(self):
        wv = WorkflowValidator()
        config = {"workflow_steps": ["s1"], "max_retries": -1}
        assert wv.validate_config(config) is False
        assert "max_retries" in wv.errors[0]

    def test_validate_config_zero_retries_ok(self):
        wv = WorkflowValidator()
        config = {"workflow_steps": ["s1"], "max_retries": 0}
        assert wv.validate_config(config) is True

    def test_validate_dependencies_no_cycle(self):
        wv = WorkflowValidator()
        steps = [
            SimpleNamespace(name="A", depends_on=[]),
            SimpleNamespace(name="B", depends_on=["A"]),
            SimpleNamespace(name="C", depends_on=["B"]),
        ]
        assert wv.validate_dependencies(steps) is True

    def test_validate_dependencies_cycle(self):
        wv = WorkflowValidator()
        steps = [
            SimpleNamespace(name="A", depends_on=["C"]),
            SimpleNamespace(name="B", depends_on=["A"]),
            SimpleNamespace(name="C", depends_on=["B"]),
        ]
        assert wv.validate_dependencies(steps) is False
        assert any("Circular" in e for e in wv.errors)

    def test_validate_dependencies_unknown_dep(self):
        wv = WorkflowValidator()
        steps = [
            SimpleNamespace(name="A", depends_on=["X"]),
        ]
        assert wv.validate_dependencies(steps) is False
        assert any("Unknown dependency" in e for e in wv.errors)

    def test_validate_step_order_valid(self):
        wv = WorkflowValidator()
        steps = [
            SimpleNamespace(name="A", order=1, depends_on=[]),
            SimpleNamespace(name="B", order=2, depends_on=["A"]),
        ]
        assert wv.validate_step_order(steps) is True

    def test_validate_step_order_invalid(self):
        wv = WorkflowValidator()
        steps = [
            SimpleNamespace(name="A", order=2, depends_on=[]),
            SimpleNamespace(name="B", order=1, depends_on=["A"]),
        ]
        assert wv.validate_step_order(steps) is False

    def test_get_errors_returns_copy(self):
        wv = WorkflowValidator()
        wv.validate_config({})
        errors = wv.get_errors()
        errors.clear()
        assert len(wv.errors) > 0


class TestWorkflowDocumentationGenerator:
    def test_generate_workflow_summary(self):
        gen = WorkflowDocumentationGenerator()
        steps = [
            SimpleNamespace(
                name="Step1",
                description="First step",
                required=True,
                timeout_seconds=30,
                depends_on=[],
            ),
            SimpleNamespace(
                name="Step2",
                description="Second step",
                required=False,
                timeout_seconds=60,
                depends_on=["Step1"],
            ),
        ]
        config = {"timeout_seconds": 120, "max_retries": 3}
        doc = gen.generate_workflow_summary("TestWorkflow", steps, config)
        assert "# Workflow: TestWorkflow" in doc
        assert "Total Steps: 2" in doc
        assert "Timeout: 120 seconds" in doc
        assert "Max Retries: 3" in doc
        assert "Step1" in doc
        assert "Step2" in doc
        assert "Dependencies: Step1" in doc

    def test_generate_workflow_summary_no_optional_config(self):
        gen = WorkflowDocumentationGenerator()
        steps = [
            SimpleNamespace(
                name="S1", description="Test", required=True, timeout_seconds=10
            )
        ]
        doc = gen.generate_workflow_summary("W", steps, {})
        assert "# Workflow: W" in doc
        assert "Timeout" not in doc.split("## Workflow Steps")[0]

    def test_generate_execution_report(self):
        gen = WorkflowDocumentationGenerator()
        progress = {
            "total_steps": 3,
            "completed_steps": 2,
            "failed_steps": 1,
            "skipped_steps": 0,
            "percentage": 66.7,
            "status": "failed",
            "metrics": {
                "step1": {
                    "status": "completed",
                    "duration_seconds": 1.5,
                    "attempts": 1,
                    "error_count": 0,
                    "last_error": None,
                },
                "step2": {
                    "status": "failed",
                    "duration_seconds": 0.5,
                    "attempts": 2,
                    "error_count": 1,
                    "last_error": "timeout",
                },
            },
        }
        report = gen.generate_execution_report(
            "sess-001", progress, "2024-01-01T00:00:00"
        )
        assert "Session ID" in report
        assert "sess-001" in report
        assert "66.7%" in report
        assert "FAILED" in report
        assert "step2" in report
        assert "timeout" in report

    def test_generate_execution_report_with_end_time(self):
        gen = WorkflowDocumentationGenerator()
        progress = {
            "total_steps": 1,
            "completed_steps": 1,
            "failed_steps": 0,
            "skipped_steps": 0,
            "percentage": 100.0,
            "status": "completed",
            "metrics": {},
            "elapsed_seconds": 30.0,
            "total_duration_seconds": 30.0,
        }
        report = gen.generate_execution_report(
            "s1", progress, "2024-01-01T00:00:00", "2024-01-01T00:00:30"
        )
        assert "End Time" in report
        assert "Elapsed Time" in report

    def test_generate_checkpoint_summary(self):
        gen = WorkflowDocumentationGenerator()
        checkpoint = {
            "session_id": "sess-001",
            "state": "in_progress",
            "created_at": "2024-01-01T00:00:00",
            "completed_steps": ["step1", "step2"],
            "current_step": "step3",
            "metadata": {"version": "1.0"},
        }
        summary = gen.generate_checkpoint_summary(checkpoint)
        assert "sess-001" in summary
        assert "in_progress" in summary
        assert "step1" in summary
        assert "step3" in summary
        assert "version" in summary

    def test_generate_checkpoint_summary_no_metadata(self):
        gen = WorkflowDocumentationGenerator()
        checkpoint = {
            "session_id": "s1",
            "state": "completed",
            "created_at": "2024-01-01",
            "completed_steps": ["a"],
        }
        summary = gen.generate_checkpoint_summary(checkpoint)
        assert "Metadata" not in summary

    def test_format_duration_seconds(self):
        gen = WorkflowDocumentationGenerator()
        assert gen._format_duration(45) == "45 seconds"

    def test_format_duration_minutes(self):
        gen = WorkflowDocumentationGenerator()
        assert gen._format_duration(300) == "5.0 minutes"

    def test_format_duration_hours(self):
        gen = WorkflowDocumentationGenerator()
        assert gen._format_duration(3600) == "1.0 hours"
