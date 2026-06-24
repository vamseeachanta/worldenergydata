"""
Validators for workflow steps and configuration.
"""

from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import jsonschema
    from jsonschema import Draft7Validator  # noqa: F401

    HAS_JSONSCHEMA = True
except ImportError:
    jsonschema = None
    HAS_JSONSCHEMA = False


def _fallback_validate(
    instance: Dict[str, Any], schema: Dict[str, Any]
) -> Optional[str]:
    """Minimal JSON-schema validation fallback for CI environments.

    The workflow validators only need object required-field and primitive type
    checks when the optional jsonschema dependency is unavailable.
    """

    required = schema.get("required", [])
    for field in required:
        if field not in instance:
            return f"'{field}' is a required property"

    type_map = {
        "integer": int,
        "number": (int, float),
        "string": str,
        "object": dict,
        "array": list,
        "boolean": bool,
    }
    for field, field_schema in schema.get("properties", {}).items():
        if field not in instance:
            continue
        expected_type = field_schema.get("type")
        expected_python_type = type_map.get(expected_type)
        if expected_python_type and not isinstance(
            instance[field], expected_python_type
        ):
            return f"{instance[field]!r} is not of type '{expected_type}'"
    return None


class StepValidator:
    """Validator for individual workflow steps."""

    def __init__(self):
        """Initialize step validator."""
        self.errors: List[str] = []

    def validate_input(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate input data against schema.

        Args:
            data: Input data to validate
            schema: JSON schema for validation

        Returns:
            True if valid, False otherwise
        """
        try:
            if HAS_JSONSCHEMA:
                jsonschema.validate(instance=data, schema=schema)
                return True

            message = _fallback_validate(data, schema)
            if message is None:
                return True
            self.errors.append(f"Input validation failed: {message}")
            logger.error(f"Input validation error: {message}")
            return False
        except jsonschema.ValidationError as e:
            self.errors.append(f"Input validation failed: {e.message}")
            logger.error(f"Input validation error: {e.message}")
            return False

    def validate_output(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate output data against schema.

        Args:
            data: Output data to validate
            schema: JSON schema for validation

        Returns:
            True if valid, False otherwise
        """
        try:
            if HAS_JSONSCHEMA:
                jsonschema.validate(instance=data, schema=schema)
                return True

            message = _fallback_validate(data, schema)
            if message is None:
                return True
            self.errors.append(f"Output validation failed: {message}")
            logger.error(f"Output validation error: {message}")
            return False
        except jsonschema.ValidationError as e:
            self.errors.append(f"Output validation failed: {e.message}")
            logger.error(f"Output validation error: {e.message}")
            return False

    def clear_errors(self) -> None:
        """Clear validation errors."""
        self.errors.clear()

    def get_errors(self) -> List[str]:
        """Get list of validation errors."""
        return self.errors.copy()


class WorkflowValidator:
    """Validator for workflow configuration and dependencies."""

    def __init__(self):
        """Initialize workflow validator."""
        self.errors: List[str] = []

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate workflow configuration.

        Args:
            config: Workflow configuration to validate

        Returns:
            True if valid, False otherwise
        """
        self.errors.clear()

        # Check for required fields
        if "workflow_steps" not in config:
            self.errors.append("Missing required field: workflow_steps")
            return False

        steps = config["workflow_steps"]

        # Check that steps is a non-empty list
        if not isinstance(steps, list):
            self.errors.append("workflow_steps must be a list")
            return False

        if len(steps) == 0:
            self.errors.append("workflow_steps cannot be empty")
            return False

        # Validate each step name
        for step in steps:
            if not isinstance(step, str):
                self.errors.append(f"Invalid step name: {step}")
                return False

        # Validate optional fields
        if "timeout_seconds" in config:
            if (
                not isinstance(config["timeout_seconds"], int)
                or config["timeout_seconds"] <= 0
            ):
                self.errors.append("timeout_seconds must be a positive integer")
                return False

        if "max_retries" in config:
            if not isinstance(config["max_retries"], int) or config["max_retries"] < 0:
                self.errors.append("max_retries must be a non-negative integer")
                return False

        return True

    def validate_dependencies(self, steps: List[Any]) -> bool:
        """
        Validate step dependencies for circular references.

        Args:
            steps: List of workflow steps with dependencies

        Returns:
            True if dependencies are valid, False if circular
        """
        # Build dependency graph
        graph = {}
        step_names = set()

        for step in steps:
            step_name = step.name
            step_names.add(step_name)
            graph[step_name] = getattr(step, "depends_on", [])

        # Check for unknown dependencies
        for step_name, deps in graph.items():
            for dep in deps:
                if dep not in step_names:
                    self.errors.append(
                        f"Unknown dependency: {dep} referenced by {step_name}"
                    )
                    return False

        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    self.errors.append(
                        f"Circular dependency detected: {node} -> {neighbor}"
                    )
                    return True

            rec_stack.remove(node)
            return False

        # Check each component
        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return False

        return True

    def validate_step_order(self, steps: List[Any]) -> bool:
        """
        Validate that step order respects dependencies.

        Args:
            steps: List of workflow steps with order

        Returns:
            True if order is valid
        """
        # Create order map
        order_map = {}
        for step in steps:
            order_map[step.name] = step.order

        # Check dependencies come before dependents
        for step in steps:
            deps = getattr(step, "depends_on", [])
            for dep in deps:
                if dep in order_map:
                    if order_map[dep] >= order_map[step.name]:
                        self.errors.append(
                            f"Step {step.name} (order {order_map[step.name]}) "
                            f"depends on {dep} (order {order_map[dep]}) which comes after"
                        )
                        return False

        return True

    def get_errors(self) -> List[str]:
        """Get list of validation errors."""
        return self.errors.copy()


class WorkflowDocumentationGenerator:
    """Generate documentation for workflow execution."""

    def __init__(self):
        """Initialize documentation generator."""
        pass

    def generate_workflow_summary(
        self, workflow_name: str, steps: List[Any], config: Dict[str, Any]
    ) -> str:
        """
        Generate workflow summary documentation.

        Args:
            workflow_name: Name of the workflow
            steps: List of workflow steps
            config: Workflow configuration

        Returns:
            Formatted documentation string
        """
        doc = f"# Workflow: {workflow_name}\n\n"
        doc += f"Total Steps: {len(steps)}\n\n"

        # Add configuration summary
        doc += "## Configuration\n\n"
        if "timeout_seconds" in config:
            doc += f"- Timeout: {config['timeout_seconds']} seconds\n"
        if "max_retries" in config:
            doc += f"- Max Retries: {config['max_retries']}\n"
        doc += "\n"

        # Add steps documentation
        doc += "## Workflow Steps\n\n"
        for i, step in enumerate(steps, 1):
            doc += f"### {i}. {step.name}\n"
            doc += f"- Description: {step.description}\n"
            doc += f"- Required: {'Yes' if step.required else 'No'}\n"
            doc += f"- Timeout: {step.timeout_seconds} seconds\n"

            if hasattr(step, "depends_on") and step.depends_on:
                doc += f"- Dependencies: {', '.join(step.depends_on)}\n"

            doc += "\n"

        return doc

    def generate_execution_report(
        self,
        session_id: str,
        progress: Dict[str, Any],
        start_time: str,
        end_time: Optional[str] = None,
    ) -> str:
        """
        Generate execution report for completed workflow.

        Args:
            session_id: Workflow session ID
            progress: Progress tracking data
            start_time: Workflow start time
            end_time: Workflow end time (if completed)

        Returns:
            Formatted report string
        """
        report = "# Workflow Execution Report\n\n"
        report += f"**Session ID:** {session_id}\n"
        report += f"**Start Time:** {start_time}\n"

        if end_time:
            report += f"**End Time:** {end_time}\n"

        report += "\n## Progress Summary\n\n"
        report += f"- Total Steps: {progress['total_steps']}\n"
        report += f"- Completed: {progress['completed_steps']}\n"
        report += f"- Failed: {progress['failed_steps']}\n"
        report += f"- Skipped: {progress['skipped_steps']}\n"
        report += f"- Progress: {progress['percentage']:.1f}%\n"
        report += f"- Status: {progress['status'].upper()}\n"

        # Add step details
        if "metrics" in progress and progress["metrics"]:
            report += "\n## Step Details\n\n"

            for step_name, metrics in progress["metrics"].items():
                report += f"### {step_name}\n"
                report += f"- Status: {metrics['status']}\n"
                report += f"- Duration: {metrics['duration_seconds']:.2f} seconds\n"
                report += f"- Attempts: {metrics['attempts']}\n"

                if metrics["error_count"] > 0:
                    report += f"- Errors: {metrics['error_count']}\n"
                    if metrics["last_error"]:
                        report += f"- Last Error: {metrics['last_error']}\n"

                report += "\n"

        # Add timing information
        if "elapsed_seconds" in progress:
            report += "\n## Timing\n\n"
            report += f"- Elapsed Time: {self._format_duration(progress['elapsed_seconds'])}\n"

            if "total_duration_seconds" in progress:
                report += f"- Total Duration: {self._format_duration(progress['total_duration_seconds'])}\n"  # noqa: E501

        return report

    def generate_checkpoint_summary(self, checkpoint: Dict[str, Any]) -> str:
        """
        Generate summary of checkpoint data.

        Args:
            checkpoint: Checkpoint data dictionary

        Returns:
            Formatted summary string
        """
        summary = "# Workflow Checkpoint\n\n"
        summary += f"**Session ID:** {checkpoint['session_id']}\n"
        summary += f"**State:** {checkpoint['state']}\n"
        summary += f"**Created At:** {checkpoint['created_at']}\n\n"

        summary += "## Completed Steps\n\n"
        for step in checkpoint["completed_steps"]:
            summary += f"- ✓ {step}\n"

        if checkpoint.get("current_step"):
            summary += f"\n**Current Step:** {checkpoint['current_step']}\n"

        if checkpoint.get("metadata"):
            summary += "\n## Metadata\n\n"
            for key, value in checkpoint["metadata"].items():
                summary += f"- {key}: {value}\n"

        return summary

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.0f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
