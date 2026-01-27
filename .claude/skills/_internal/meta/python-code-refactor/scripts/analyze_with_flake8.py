#!/usr/bin/env python3
"""
Run flake8 with comprehensive plugins and output structured reports.

Plugins included:
- Essential: bugbear, simplify, cognitive-complexity, pep8-naming, docstrings
- Recommended: comprehensions, expression-complexity, functions, variables-names, tryceratops

Usage:
    python analyze_with_flake8.py path/to/code
    python analyze_with_flake8.py path/to/code --output report.json
    python analyze_with_flake8.py path/to/code --format markdown
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Flake8 plugins to install/use
FLAKE8_PLUGINS = [
    "flake8-bugbear",  # B: Opinionated warnings
    "flake8-simplify",  # SIM: Simplification suggestions
    "flake8-cognitive-complexity",  # CCN: Cognitive complexity
    "pep8-naming",  # N: PEP8 naming conventions
    "flake8-docstrings",  # D: Docstring checks
    "flake8-comprehensions",  # C4: Comprehension improvements
    "flake8-expression-complexity",  # ECE: Expression complexity
    "flake8-functions",  # CFQ: Function complexity
    "flake8-variables-names",  # VNE: Variable naming
    "flake8-pie",  # PIE: Misc lints
    "flake8-quotes",  # Q: Quote consistency
    "flake8-return",  # R: Return statement checks
    "flake8-annotations",  # ANN: Type annotation checks
    "flake8-bandit",  # S: Security checks
    "flake8-blind-except",  # B: Blind except checks
    "flake8-debugger",  # T: Debugger checks
]

# Error code categories
ERROR_CATEGORIES = {
    "E": "PEP8 Error",
    "W": "PEP8 Warning",
    "F": "PyFlakes",
    "C": "Complexity/Comprehensions",
    "B": "Bugbear",
    "SIM": "Simplify",
    "N": "Naming",
    "D": "Docstrings",
    "CCN": "Cognitive Complexity",
    "ECE": "Expression Complexity",
    "CFQ": "Functions",
    "VNE": "Variable Names",
    "PIE": "Misc Lints",
    "Q": "Quotes",
    "R": "Return",
    "ANN": "Annotations",
    "S": "Security",
    "T": "Debugger",
}


@dataclass
class FlakeIssue:
    """A single flake8 issue."""

    file: str
    line: int
    column: int
    code: str
    message: str
    category: str = ""

    def __post_init__(self) -> None:
        """Set category based on error code."""
        self.category = self._get_category()

    def _get_category(self) -> str:
        """Determine category from error code."""
        for prefix, category in sorted(
            ERROR_CATEGORIES.items(), key=lambda x: -len(x[0])
        ):
            if self.code.startswith(prefix):
                return category
        return "Other"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "message": self.message,
            "category": self.category,
        }


@dataclass
class FlakeReport:
    """Complete flake8 analysis report."""

    path: str
    issues: list[FlakeIssue] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    by_file: dict[str, list[FlakeIssue]] = field(default_factory=dict)
    by_category: dict[str, list[FlakeIssue]] = field(default_factory=dict)
    by_code: dict[str, int] = field(default_factory=dict)

    def compute_summaries(self) -> None:
        """Compute summary statistics."""
        self.by_file = defaultdict(list)
        self.by_category = defaultdict(list)
        self.by_code = defaultdict(int)

        for issue in self.issues:
            self.by_file[issue.file].append(issue)
            self.by_category[issue.category].append(issue)
            self.by_code[issue.code] += 1

        self.summary = {
            "total_issues": len(self.issues),
            "files_with_issues": len(self.by_file),
            "categories": {k: len(v) for k, v in self.by_category.items()},
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "by_file": {k: [i.to_dict() for i in v] for k, v in self.by_file.items()},
            "by_category": {
                k: [i.to_dict() for i in v] for k, v in self.by_category.items()
            },
            "by_code": dict(self.by_code),
        }


def check_flake8_installed() -> bool:
    """
    Check if flake8 is installed.

    Returns:
        True if flake8 is available
    """
    try:
        subprocess.run(
            ["flake8", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_flake8(
    path: Path,
    max_line_length: int = 100,
    max_complexity: int = 10,
    exclude: list[str] | None = None,
    select: list[str] | None = None,
    ignore: list[str] | None = None,
) -> tuple[str, int]:
    """
    Run flake8 on the specified path.

    Args:
        path: Path to analyze
        max_line_length: Maximum line length
        max_complexity: Maximum cyclomatic complexity
        exclude: Patterns to exclude
        select: Error codes to select
        ignore: Error codes to ignore

    Returns:
        Tuple of (output, return_code)
    """
    cmd = [
        "flake8",
        str(path),
        f"--max-line-length={max_line_length}",
        f"--max-complexity={max_complexity}",
        "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
        "--show-source",
    ]

    if exclude:
        cmd.append(f"--exclude={','.join(exclude)}")
    if select:
        cmd.append(f"--select={','.join(select)}")
    if ignore:
        cmd.append(f"--ignore={','.join(ignore)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    return result.stdout + result.stderr, result.returncode


def parse_flake8_output(output: str, path: str) -> FlakeReport:
    """
    Parse flake8 output into structured report.

    Args:
        output: Raw flake8 output
        path: Path that was analyzed

    Returns:
        FlakeReport with parsed issues
    """
    report = FlakeReport(path=path)

    for line in output.strip().split("\n"):
        if not line or ":" not in line:
            continue

        # Skip source code lines (they don't have the expected format)
        parts = line.split(":", 4)
        if len(parts) < 5:
            continue

        try:
            file_path, line_num, col_num, code, message = parts
            issue = FlakeIssue(
                file=file_path,
                line=int(line_num),
                column=int(col_num),
                code=code.strip(),
                message=message.strip(),
            )
            report.issues.append(issue)
        except (ValueError, IndexError):
            # Skip malformed lines
            continue

    report.compute_summaries()
    return report


def format_markdown(report: FlakeReport) -> str:
    """
    Format report as Markdown.

    Args:
        report: FlakeReport to format

    Returns:
        Markdown formatted string
    """
    lines = [
        "# Flake8 Analysis Report",
        "",
        f"**Path**: `{report.path}`",
        f"**Total Issues**: {report.summary.get('total_issues', 0)}",
        f"**Files with Issues**: {report.summary.get('files_with_issues', 0)}",
        "",
    ]

    # Summary by category
    if report.summary.get("categories"):
        lines.extend(["## Issues by Category", ""])
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for category, count in sorted(
            report.summary["categories"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"| {category} | {count} |")
        lines.append("")

    # Top error codes
    if report.by_code:
        lines.extend(["## Top Error Codes", ""])
        lines.append("| Code | Count | Description |")
        lines.append("|------|-------|-------------|")
        for code, count in sorted(report.by_code.items(), key=lambda x: -x[1])[:20]:
            # Get first message for this code as description
            desc = ""
            for issue in report.issues:
                if issue.code == code:
                    desc = (
                        issue.message[:50] + "..."
                        if len(issue.message) > 50
                        else issue.message
                    )
                    break
            lines.append(f"| `{code}` | {count} | {desc} |")
        lines.append("")

    # Issues by file
    if report.by_file:
        lines.extend(["## Issues by File", ""])
        for file_path, issues in sorted(report.by_file.items()):
            lines.append(f"### `{file_path}` ({len(issues)} issues)")
            lines.append("")
            lines.append("| Line | Col | Code | Message |")
            lines.append("|------|-----|------|---------|")
            for issue in sorted(issues, key=lambda x: (x.line, x.column)):
                msg = (
                    issue.message[:60] + "..."
                    if len(issue.message) > 60
                    else issue.message
                )
                lines.append(
                    f"| {issue.line} | {issue.column} | `{issue.code}` | {msg} |"
                )
            lines.append("")

    return "\n".join(lines)


def format_text(report: FlakeReport) -> str:
    """
    Format report as plain text.

    Args:
        report: FlakeReport to format

    Returns:
        Plain text formatted string
    """
    lines = [
        "=" * 80,
        "FLAKE8 ANALYSIS REPORT",
        "=" * 80,
        "",
        f"Path: {report.path}",
        f"Total Issues: {report.summary.get('total_issues', 0)}",
        f"Files with Issues: {report.summary.get('files_with_issues', 0)}",
        "",
    ]

    if report.summary.get("categories"):
        lines.append("Issues by Category:")
        for category, count in sorted(
            report.summary["categories"].items(), key=lambda x: -x[1]
        ):
            lines.append(f"  {category}: {count}")
        lines.append("")

    if report.by_code:
        lines.append("Top Error Codes:")
        for code, count in sorted(report.by_code.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {code}: {count}")
        lines.append("")

    if report.issues:
        lines.append("-" * 80)
        lines.append("ALL ISSUES:")
        lines.append("-" * 80)
        for issue in sorted(report.issues, key=lambda x: (x.file, x.line)):
            lines.append(
                f"{issue.file}:{issue.line}:{issue.column} {issue.code} {issue.message}"
            )

    return "\n".join(lines)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for issues found)
    """
    parser = argparse.ArgumentParser(
        description="Run flake8 with comprehensive plugins and output structured reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Plugins used:
{chr(10).join('  - ' + p for p in FLAKE8_PLUGINS)}

Examples:
    %(prog)s src/
    %(prog)s src/ --output report.json
    %(prog)s src/ --format markdown > report.md
    %(prog)s src/ --ignore E501,W503
        """,
    )
    parser.add_argument("path", type=Path, help="Path to analyze")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output file path for JSON report"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "text", "markdown", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=100,
        help="Maximum line length (default: 100)",
    )
    parser.add_argument(
        "--max-complexity",
        type=int,
        default=10,
        help="Maximum cyclomatic complexity (default: 10)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        help="Comma-separated patterns to exclude",
    )
    parser.add_argument(
        "--select",
        type=str,
        help="Comma-separated error codes to select",
    )
    parser.add_argument(
        "--ignore",
        type=str,
        help="Comma-separated error codes to ignore",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit with non-zero code if any issues found",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        return 1

    if not check_flake8_installed():
        print(
            "Error: flake8 is not installed. Install with: pip install flake8",
            file=sys.stderr,
        )
        return 1

    # Parse optional arguments
    exclude = args.exclude.split(",") if args.exclude else None
    select = args.select.split(",") if args.select else None
    ignore = args.ignore.split(",") if args.ignore else None

    # Run flake8
    output, return_code = run_flake8(
        args.path,
        max_line_length=args.max_line_length,
        max_complexity=args.max_complexity,
        exclude=exclude,
        select=select,
        ignore=ignore,
    )

    # Parse output
    report = parse_flake8_output(output, str(args.path))

    # Write JSON output
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"JSON report written to {args.output}")

    # Display formatted output
    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif args.format == "markdown":
        print(format_markdown(report))
    elif args.format == "text":
        print(format_text(report))
    else:  # all
        print(format_text(report))
        if not args.output:
            print("\n" + "=" * 80)
            print("JSON OUTPUT:")
            print("=" * 80)
            print(json.dumps(report.to_dict(), indent=2))

    # Return appropriate exit code
    if args.fail_on_issues and report.issues:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
