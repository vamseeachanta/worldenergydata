#!/usr/bin/env python3
"""
Module Compliance Checker for worldenergydata.

Checks each module in src/worldenergydata/modules/ for compliance with
the module template and generates a detailed compliance report.

Usage:
    uv run python scripts/tools/check_module_compliance.py
"""

import ast
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


@dataclass
class ComplianceIssue:
    """Represents a single compliance issue found in a module."""

    rule: str
    severity: str  # "error" or "warning"
    message: str
    suggestion: str


@dataclass
class ModuleMetrics:
    """Baseline metrics for a module."""

    file_count: int = 0
    python_file_count: int = 0
    test_file_count: int = 0
    max_directory_depth: int = 0
    has_init: bool = False
    has_data_dir: bool = False
    has_readme: bool = False
    total_lines_of_code: int = 0


@dataclass
class ModuleComplianceResult:
    """Result of compliance check for a single module."""

    module_name: str
    is_compliant: bool
    issues: list[ComplianceIssue] = field(default_factory=list)
    metrics: ModuleMetrics = field(default_factory=ModuleMetrics)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ComplianceReport:
    """Full compliance report for all modules."""

    timestamp: str
    total_modules: int
    compliant_count: int
    non_compliant_count: int
    module_results: list[ModuleComplianceResult] = field(default_factory=list)
    summary_metrics: dict = field(default_factory=dict)


class ModuleComplianceChecker:
    """Checks module compliance with project templates and standards."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.modules_dir = project_root / "src" / "worldenergydata" / "modules"
        self.common_dir = project_root / "src" / "worldenergydata" / "common"
        self.tests_dir = project_root / "tests"

        # Common layer exports to check for proper imports
        self.common_exports = self._get_common_exports()

    def _get_common_exports(self) -> set[str]:
        """Get the list of exports from the common layer."""
        common_init = self.common_dir / "__init__.py"
        exports = set()

        if common_init.exists():
            try:
                content = common_init.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == "__all__":
                                if isinstance(node.value, ast.List):
                                    for elt in node.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            exports.add(elt.value)
            except Exception:
                pass

        return exports

    def _get_module_directories(self) -> list[Path]:
        """Get all module directories."""
        if not self.modules_dir.exists():
            return []

        return [
            d for d in self.modules_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")
        ]

    def _check_init_file(self, module_path: Path) -> tuple[bool, Optional[list[str]], list[ComplianceIssue]]:
        """Check if module has __init__.py with __all__ declaration."""
        issues = []
        init_file = module_path / "__init__.py"

        if not init_file.exists():
            issues.append(ComplianceIssue(
                rule="init_file",
                severity="error",
                message="Missing __init__.py file",
                suggestion=f"Create {init_file.relative_to(self.project_root)} with __all__ declaration"
            ))
            return False, None, issues

        content = init_file.read_text()

        # Check for __all__ declaration
        if "__all__" not in content:
            issues.append(ComplianceIssue(
                rule="all_declaration",
                severity="error",
                message="__init__.py missing __all__ declaration",
                suggestion="Add __all__ = [...] to declare public API"
            ))
            return True, None, issues

        # Parse __all__ content
        try:
            tree = ast.parse(content)
            all_exports = None

            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            if isinstance(node.value, ast.List):
                                all_exports = []
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        all_exports.append(elt.value)

            if all_exports is not None and len(all_exports) == 0:
                issues.append(ComplianceIssue(
                    rule="empty_all",
                    severity="warning",
                    message="__all__ declaration is empty",
                    suggestion="Add public API exports to __all__"
                ))

            return True, all_exports, issues

        except SyntaxError as e:
            issues.append(ComplianceIssue(
                rule="syntax_error",
                severity="error",
                message=f"Syntax error in __init__.py: {e}",
                suggestion="Fix syntax errors in the file"
            ))
            return True, None, issues

    def _check_data_directory(self, module_path: Path) -> tuple[bool, list[ComplianceIssue]]:
        """Check if module has a data/ directory."""
        issues = []
        data_dir = module_path / "data"

        if not data_dir.exists():
            # Check for alternative data locations
            alt_data_dirs = ["datasets", "resources", "assets"]
            found_alt = None
            for alt in alt_data_dirs:
                if (module_path / alt).exists():
                    found_alt = alt
                    break

            if found_alt:
                issues.append(ComplianceIssue(
                    rule="data_directory",
                    severity="warning",
                    message=f"Uses '{found_alt}/' instead of 'data/' directory",
                    suggestion="Consider renaming to 'data/' for consistency"
                ))
            else:
                issues.append(ComplianceIssue(
                    rule="data_directory",
                    severity="warning",
                    message="Missing data/ directory",
                    suggestion="Create data/ directory if module handles data"
                ))
            return False, issues

        return True, issues

    def _check_common_imports(self, module_path: Path) -> list[ComplianceIssue]:
        """Check if module uses common layer imports instead of local copies."""
        issues = []

        # Patterns that indicate local copies of common functionality
        local_copy_patterns = [
            (r"class\s+\w*Error\(Exception\)", "custom exception"),
            (r"def\s+get_logger\s*\(", "custom logger"),
            (r"def\s+configure_logging\s*\(", "custom logging configuration"),
            (r"logging\.getLogger\(__name__\)", "direct logging usage"),
        ]

        # Get all Python files in module (excluding __pycache__)
        for py_file in module_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                rel_path = py_file.relative_to(self.project_root)

                # Check for local copy patterns
                for pattern, description in local_copy_patterns:
                    if re.search(pattern, content):
                        # Check if it also imports from common
                        if "from worldenergydata.common" not in content:
                            issues.append(ComplianceIssue(
                                rule="common_layer",
                                severity="warning",
                                message=f"Local {description} in {rel_path}",
                                suggestion=f"Use worldenergydata.common instead of local {description}"
                            ))
                            break

            except Exception:
                pass

        return issues

    def _check_naming_conventions(self, module_path: Path) -> list[ComplianceIssue]:
        """Check if module follows naming conventions."""
        issues = []
        module_name = module_path.name

        # Module name should be snake_case
        if not re.match(r"^[a-z][a-z0-9_]*$", module_name):
            issues.append(ComplianceIssue(
                rule="naming",
                severity="error",
                message=f"Module name '{module_name}' should be snake_case",
                suggestion=f"Rename to '{module_name.lower().replace('-', '_')}'"
            ))

        # Check Python file names
        for py_file in module_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            file_name = py_file.stem

            # Skip __init__ and other dunder files
            if file_name.startswith("__") and file_name.endswith("__"):
                continue

            if not re.match(r"^[a-z][a-z0-9_]*$", file_name):
                rel_path = py_file.relative_to(self.project_root)
                issues.append(ComplianceIssue(
                    rule="naming",
                    severity="warning",
                    message=f"File '{rel_path}' should use snake_case naming",
                    suggestion=f"Rename to '{file_name.lower().replace('-', '_')}.py'"
                ))

        return issues

    def _calculate_metrics(self, module_path: Path) -> ModuleMetrics:
        """Calculate baseline metrics for a module."""
        metrics = ModuleMetrics()
        module_name = module_path.name

        # Count files
        all_files = list(module_path.rglob("*"))
        metrics.file_count = len([f for f in all_files if f.is_file()])

        # Count Python files
        py_files = [f for f in all_files if f.suffix == ".py" and "__pycache__" not in str(f)]
        metrics.python_file_count = len(py_files)

        # Count lines of code
        for py_file in py_files:
            try:
                content = py_file.read_text()
                metrics.total_lines_of_code += len(content.splitlines())
            except Exception:
                pass

        # Check for __init__.py and data/ dir
        metrics.has_init = (module_path / "__init__.py").exists()
        metrics.has_data_dir = (module_path / "data").exists()
        metrics.has_readme = (module_path / "README.md").exists()

        # Calculate max directory depth
        max_depth = 0
        for item in module_path.rglob("*"):
            if item.is_dir() and "__pycache__" not in str(item):
                depth = len(item.relative_to(module_path).parts)
                max_depth = max(max_depth, depth)
        metrics.max_directory_depth = max_depth

        # Count test files
        tests_module_dir = self.tests_dir / "modules" / module_name
        if tests_module_dir.exists():
            test_files = list(tests_module_dir.rglob("test_*.py"))
            metrics.test_file_count = len(test_files)

        return metrics

    def check_module(self, module_path: Path) -> ModuleComplianceResult:
        """Check a single module for compliance."""
        module_name = module_path.name
        issues = []
        suggestions = []

        # Check __init__.py
        has_init, all_exports, init_issues = self._check_init_file(module_path)
        issues.extend(init_issues)

        # Check data directory
        has_data, data_issues = self._check_data_directory(module_path)
        issues.extend(data_issues)

        # Check common layer usage
        common_issues = self._check_common_imports(module_path)
        issues.extend(common_issues)

        # Check naming conventions
        naming_issues = self._check_naming_conventions(module_path)
        issues.extend(naming_issues)

        # Calculate metrics
        metrics = self._calculate_metrics(module_path)

        # Generate suggestions based on issues
        if not metrics.has_readme:
            suggestions.append("Add README.md documenting the module's purpose and usage")

        if metrics.test_file_count == 0:
            suggestions.append("Add test files to tests/modules/{module_name}/")

        if metrics.max_directory_depth > 4:
            suggestions.append("Consider flattening directory structure (max depth: 4)")

        # Determine overall compliance
        error_count = sum(1 for issue in issues if issue.severity == "error")
        is_compliant = error_count == 0

        return ModuleComplianceResult(
            module_name=module_name,
            is_compliant=is_compliant,
            issues=issues,
            metrics=metrics,
            suggestions=suggestions
        )

    def run(self) -> ComplianceReport:
        """Run compliance checks on all modules."""
        module_dirs = self._get_module_directories()
        results = []

        for module_dir in sorted(module_dirs):
            result = self.check_module(module_dir)
            results.append(result)

        compliant_count = sum(1 for r in results if r.is_compliant)
        non_compliant_count = len(results) - compliant_count

        # Calculate summary metrics
        summary_metrics = {
            "total_python_files": sum(r.metrics.python_file_count for r in results),
            "total_test_files": sum(r.metrics.test_file_count for r in results),
            "total_lines_of_code": sum(r.metrics.total_lines_of_code for r in results),
            "modules_with_init": sum(1 for r in results if r.metrics.has_init),
            "modules_with_data_dir": sum(1 for r in results if r.metrics.has_data_dir),
            "modules_with_readme": sum(1 for r in results if r.metrics.has_readme),
            "average_directory_depth": (
                sum(r.metrics.max_directory_depth for r in results) / len(results)
                if results else 0
            ),
        }

        return ComplianceReport(
            timestamp=datetime.now().isoformat(),
            total_modules=len(results),
            compliant_count=compliant_count,
            non_compliant_count=non_compliant_count,
            module_results=results,
            summary_metrics=summary_metrics
        )


def print_report(report: ComplianceReport) -> None:
    """Print a formatted compliance report to the terminal."""
    c = Colors

    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"{c.BOLD}Module Compliance Report{c.RESET}")
    print(f"{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"\nTimestamp: {report.timestamp}")
    print(f"Total Modules: {report.total_modules}")
    print(f"Compliant: {c.GREEN}{report.compliant_count}{c.RESET}")
    print(f"Non-Compliant: {c.RED}{report.non_compliant_count}{c.RESET}")

    print(f"\n{c.BOLD}Summary Metrics:{c.RESET}")
    for key, value in report.summary_metrics.items():
        formatted_key = key.replace("_", " ").title()
        if isinstance(value, float):
            print(f"  {formatted_key}: {value:.2f}")
        else:
            print(f"  {formatted_key}: {value}")

    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")
    print(f"{c.BOLD}Module Details{c.RESET}")
    print(f"{c.BOLD}{'=' * 70}{c.RESET}")

    for result in report.module_results:
        status_color = c.GREEN if result.is_compliant else c.RED
        status_icon = "[PASS]" if result.is_compliant else "[FAIL]"

        print(f"\n{status_color}{status_icon}{c.RESET} {c.BOLD}{result.module_name}{c.RESET}")

        # Print metrics
        m = result.metrics
        print(f"  Files: {m.python_file_count} Python | {m.test_file_count} Tests | {m.total_lines_of_code} LOC")

        # Print issues
        if result.issues:
            print(f"  {c.YELLOW}Issues:{c.RESET}")
            for issue in result.issues:
                severity_color = c.RED if issue.severity == "error" else c.YELLOW
                print(f"    {severity_color}[{issue.severity.upper()}]{c.RESET} {issue.rule}: {issue.message}")
                print(f"         Suggestion: {issue.suggestion}")

        # Print suggestions
        if result.suggestions:
            print(f"  {c.BLUE}Suggestions:{c.RESET}")
            for suggestion in result.suggestions:
                print(f"    - {suggestion}")

    print(f"\n{c.BOLD}{'=' * 70}{c.RESET}")


def serialize_report(report: ComplianceReport) -> dict:
    """Convert report to JSON-serializable dictionary."""
    def serialize_issue(issue: ComplianceIssue) -> dict:
        return asdict(issue)

    def serialize_metrics(metrics: ModuleMetrics) -> dict:
        return asdict(metrics)

    def serialize_result(result: ModuleComplianceResult) -> dict:
        return {
            "module_name": result.module_name,
            "is_compliant": result.is_compliant,
            "issues": [serialize_issue(i) for i in result.issues],
            "metrics": serialize_metrics(result.metrics),
            "suggestions": result.suggestions
        }

    return {
        "timestamp": report.timestamp,
        "total_modules": report.total_modules,
        "compliant_count": report.compliant_count,
        "non_compliant_count": report.non_compliant_count,
        "module_results": [serialize_result(r) for r in report.module_results],
        "summary_metrics": report.summary_metrics
    }


def main() -> int:
    """Main entry point."""
    # Determine project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent  # scripts/tools/ -> project root

    # Verify we're in the right location
    if not (project_root / "src" / "worldenergydata").exists():
        print(f"{Colors.RED}Error: Could not find src/worldenergydata directory{Colors.RESET}")
        print(f"Expected project root: {project_root}")
        return 1

    print(f"Project root: {project_root}")
    print(f"Checking modules in: {project_root / 'src' / 'worldenergydata' / 'modules'}")

    # Run compliance checks
    checker = ModuleComplianceChecker(project_root)
    report = checker.run()

    # Print report to terminal
    print_report(report)

    # Save JSON report
    reports_dir = project_root / "reports" / "compliance"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "module_compliance_report.json"
    report_data = serialize_report(report)

    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n{Colors.GREEN}Report saved to: {report_path}{Colors.RESET}")

    # Return non-zero exit code if there are non-compliant modules
    return 0 if report.non_compliant_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
