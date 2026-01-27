"""
Python code refactoring validation scripts.

This package provides tools for measuring and comparing code quality metrics:

- measure_complexity: AST-based complexity analysis (cyclomatic, cognitive, nesting)
- analyze_with_flake8: Run flake8 with comprehensive plugins
- compare_flake8_reports: Compare before/after flake8 reports
- check_documentation: Check docstring and type hint coverage
- compare_metrics: Compare before/after complexity metrics
- benchmark_changes: Performance regression detection
"""

from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

__all__ = [
    "SCRIPTS_DIR",
]
