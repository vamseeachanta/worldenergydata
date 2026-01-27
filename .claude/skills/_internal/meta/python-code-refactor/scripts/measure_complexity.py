#!/usr/bin/env python3
"""
Measure code complexity metrics using AST analysis.

Provides per-function and aggregate metrics including:
- Cyclomatic complexity (McCabe)
- Cognitive complexity
- Function length
- Nesting depth

Usage:
    python measure_complexity.py path/to/file.py
    python measure_complexity.py path/to/directory --recursive
    python measure_complexity.py path/to/file.py --output metrics.json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FunctionMetrics:
    """Metrics for a single function or method."""

    name: str
    file: str
    line_start: int
    line_end: int
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    length: int = 0
    max_nesting_depth: int = 0
    parameter_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class FileMetrics:
    """Aggregate metrics for a file."""

    file: str
    total_lines: int = 0
    code_lines: int = 0
    functions: list[FunctionMetrics] = field(default_factory=list)
    classes: int = 0
    avg_cyclomatic_complexity: float = 0.0
    avg_cognitive_complexity: float = 0.0
    max_cyclomatic_complexity: int = 0
    max_cognitive_complexity: int = 0
    max_function_length: int = 0
    max_nesting_depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["functions"] = [f.to_dict() for f in self.functions]
        return result


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """Calculate McCabe cyclomatic complexity for a function."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        self.complexity = 1  # Base complexity

    def visit_If(self, node: ast.If) -> None:
        """Count if statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Count for loops."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Count while loops."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Count except handlers."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """Count with statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        """Count assert statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        """Count comprehensions."""
        self.complexity += 1
        # Count ifs in comprehension
        self.complexity += len(node.ifs)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Count boolean operators (and/or)."""
        # Each and/or adds a decision point
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        """Count ternary expressions."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Count match statements (Python 3.10+)."""
        self.complexity += len(node.cases)
        self.generic_visit(node)


class CognitiveComplexityVisitor(ast.NodeVisitor):
    """
    Calculate cognitive complexity for a function.

    Cognitive complexity weights nested structures more heavily
    and penalizes certain constructs that break linear flow.
    """

    def __init__(self) -> None:
        """Initialize the visitor."""
        self.complexity = 0
        self.nesting_level = 0

    def _increment(self, amount: int = 1) -> None:
        """Increment complexity with nesting bonus."""
        self.complexity += amount + self.nesting_level

    def visit_If(self, node: ast.If) -> None:
        """Count if statements with nesting."""
        self._increment()
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1
        # elif adds complexity but no nesting
        for child in node.orelse:
            if isinstance(child, ast.If):
                self.complexity += 1

    def visit_For(self, node: ast.For) -> None:
        """Count for loops with nesting."""
        self._increment()
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_While(self, node: ast.While) -> None:
        """Count while loops with nesting."""
        self._increment()
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Count except handlers with nesting."""
        self._increment()
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Count sequences of boolean operators."""
        # Each sequence of boolean operators adds 1
        self.complexity += 1
        self.generic_visit(node)

    def visit_Break(self, node: ast.Break) -> None:
        """Count break statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Continue(self, node: ast.Continue) -> None:
        """Count continue statements."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Count lambda expressions."""
        self._increment()
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Count match statements (Python 3.10+)."""
        self._increment()
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1


class NestingDepthVisitor(ast.NodeVisitor):
    """Calculate maximum nesting depth."""

    def __init__(self) -> None:
        """Initialize the visitor."""
        self.max_depth = 0
        self.current_depth = 0

    def _enter_block(self) -> None:
        """Enter a nested block."""
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)

    def _exit_block(self) -> None:
        """Exit a nested block."""
        self.current_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        """Track if nesting."""
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_For(self, node: ast.For) -> None:
        """Track for loop nesting."""
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_While(self, node: ast.While) -> None:
        """Track while loop nesting."""
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_With(self, node: ast.With) -> None:
        """Track with statement nesting."""
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_Try(self, node: ast.Try) -> None:
        """Track try block nesting."""
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_Match(self, node: ast.Match) -> None:
        """Track match statement nesting (Python 3.10+)."""
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()


def analyze_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    file_path: str,
    class_name: str | None = None,
) -> FunctionMetrics:
    """
    Analyze a function or method and return its metrics.

    Args:
        node: AST node representing the function
        file_path: Path to the source file
        class_name: Name of containing class, if any

    Returns:
        FunctionMetrics with all computed metrics
    """
    name = f"{class_name}.{node.name}" if class_name else node.name

    # Calculate cyclomatic complexity
    cc_visitor = CyclomaticComplexityVisitor()
    cc_visitor.visit(node)

    # Calculate cognitive complexity
    cog_visitor = CognitiveComplexityVisitor()
    cog_visitor.visit(node)

    # Calculate nesting depth
    nest_visitor = NestingDepthVisitor()
    nest_visitor.visit(node)

    # Calculate function length
    line_start = node.lineno
    line_end = node.end_lineno or node.lineno
    length = line_end - line_start + 1

    # Count parameters
    args = node.args
    param_count = (
        len(args.args)
        + len(args.posonlyargs)
        + len(args.kwonlyargs)
        + (1 if args.vararg else 0)
        + (1 if args.kwarg else 0)
    )

    return FunctionMetrics(
        name=name,
        file=file_path,
        line_start=line_start,
        line_end=line_end,
        cyclomatic_complexity=cc_visitor.complexity,
        cognitive_complexity=cog_visitor.complexity,
        length=length,
        max_nesting_depth=nest_visitor.max_depth,
        parameter_count=param_count,
    )


def analyze_file(file_path: Path) -> FileMetrics:
    """
    Analyze a Python file and return its metrics.

    Args:
        file_path: Path to the Python file

    Returns:
        FileMetrics with per-function and aggregate metrics
    """
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    total_lines = len(lines)
    code_lines = sum(
        1 for line in lines if line.strip() and not line.strip().startswith("#")
    )

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return FileMetrics(
            file=str(file_path), total_lines=total_lines, code_lines=code_lines
        )

    file_metrics = FileMetrics(
        file=str(file_path),
        total_lines=total_lines,
        code_lines=code_lines,
    )

    # Collect all functions and methods
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            file_metrics.classes += 1
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    metrics = analyze_function(item, str(file_path), node.name)
                    file_metrics.functions.append(metrics)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Top-level function (not in a class)
            # Check if this is a direct child of the module
            if any(
                node in getattr(parent, "body", [])
                for parent in ast.walk(tree)
                if isinstance(parent, ast.Module)
            ):
                metrics = analyze_function(node, str(file_path))
                file_metrics.functions.append(metrics)

    # Calculate aggregates
    if file_metrics.functions:
        complexities = [f.cyclomatic_complexity for f in file_metrics.functions]
        cognitive = [f.cognitive_complexity for f in file_metrics.functions]
        lengths = [f.length for f in file_metrics.functions]
        nesting = [f.max_nesting_depth for f in file_metrics.functions]

        file_metrics.avg_cyclomatic_complexity = sum(complexities) / len(complexities)
        file_metrics.avg_cognitive_complexity = sum(cognitive) / len(cognitive)
        file_metrics.max_cyclomatic_complexity = max(complexities)
        file_metrics.max_cognitive_complexity = max(cognitive)
        file_metrics.max_function_length = max(lengths)
        file_metrics.max_nesting_depth = max(nesting)

    return file_metrics


def collect_python_files(path: Path, recursive: bool = False) -> list[Path]:
    """
    Collect Python files from a path.

    Args:
        path: File or directory path
        recursive: If True, search directories recursively

    Returns:
        List of Python file paths
    """
    if path.is_file():
        if path.suffix == ".py":
            return [path]
        return []

    if recursive:
        return list(path.rglob("*.py"))
    return list(path.glob("*.py"))


def format_human_readable(results: list[FileMetrics]) -> str:
    """
    Format results as human-readable text.

    Args:
        results: List of file metrics

    Returns:
        Formatted string report
    """
    lines = ["=" * 80, "CODE COMPLEXITY REPORT", "=" * 80, ""]

    total_functions = 0
    total_cc = 0
    total_cog = 0
    high_complexity_functions = []

    for file_metrics in results:
        lines.append(f"\nFile: {file_metrics.file}")
        lines.append(
            f"  Lines: {file_metrics.total_lines} total, {file_metrics.code_lines} code"
        )
        lines.append(f"  Classes: {file_metrics.classes}")
        lines.append(f"  Functions: {len(file_metrics.functions)}")

        if file_metrics.functions:
            lines.append(
                f"  Avg Cyclomatic Complexity: {file_metrics.avg_cyclomatic_complexity:.2f}"
            )
            lines.append(
                f"  Avg Cognitive Complexity: {file_metrics.avg_cognitive_complexity:.2f}"
            )
            lines.append(f"  Max Function Length: {file_metrics.max_function_length}")
            lines.append(f"  Max Nesting Depth: {file_metrics.max_nesting_depth}")

            lines.append("\n  Functions:")
            for func in file_metrics.functions:
                lines.append(
                    f"    {func.name} (lines {func.line_start}-{func.line_end}): "
                    f"CC={func.cyclomatic_complexity}, "
                    f"Cog={func.cognitive_complexity}, "
                    f"Len={func.length}, "
                    f"Nest={func.max_nesting_depth}"
                )
                total_functions += 1
                total_cc += func.cyclomatic_complexity
                total_cog += func.cognitive_complexity

                # Track high complexity functions
                if func.cyclomatic_complexity > 10 or func.cognitive_complexity > 15:
                    high_complexity_functions.append(func)

    # Summary
    lines.extend(["", "=" * 80, "SUMMARY", "=" * 80])
    lines.append(f"Files analyzed: {len(results)}")
    lines.append(f"Total functions: {total_functions}")
    if total_functions > 0:
        lines.append(f"Average cyclomatic complexity: {total_cc / total_functions:.2f}")
        lines.append(f"Average cognitive complexity: {total_cog / total_functions:.2f}")

    if high_complexity_functions:
        lines.extend(["", "HIGH COMPLEXITY FUNCTIONS (CC>10 or Cog>15):"])
        for func in high_complexity_functions:
            lines.append(
                f"  {func.file}:{func.line_start} {func.name} "
                f"(CC={func.cyclomatic_complexity}, Cog={func.cognitive_complexity})"
            )

    return "\n".join(lines)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="Measure code complexity metrics using AST analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s src/module.py
    %(prog)s src/ --recursive
    %(prog)s src/ -r --output metrics.json
    %(prog)s src/ -r --format json
        """,
    )
    parser.add_argument("path", type=Path, help="File or directory to analyze")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursively search directories"
    )
    parser.add_argument("-o", "--output", type=Path, help="Output file path (JSON)")
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "text", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--max-cc",
        type=int,
        default=10,
        help="Max cyclomatic complexity threshold (default: 10)",
    )
    parser.add_argument(
        "--max-cog",
        type=int,
        default=15,
        help="Max cognitive complexity threshold (default: 15)",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        return 1

    files = collect_python_files(args.path, args.recursive)
    if not files:
        print(f"No Python files found in {args.path}", file=sys.stderr)
        return 1

    results = [analyze_file(f) for f in files]

    # Output JSON
    json_output = {"files": [r.to_dict() for r in results]}

    if args.output:
        args.output.write_text(json.dumps(json_output, indent=2), encoding="utf-8")
        print(f"JSON output written to {args.output}")

    if args.format in ("json", "both"):
        if not args.output:
            print(json.dumps(json_output, indent=2))

    if args.format in ("text", "both"):
        print(format_human_readable(results))

    # Check thresholds and return appropriate exit code
    violations = 0
    for file_metrics in results:
        for func in file_metrics.functions:
            if func.cyclomatic_complexity > args.max_cc:
                violations += 1
            if func.cognitive_complexity > args.max_cog:
                violations += 1

    if violations > 0:
        print(
            f"\n{violations} complexity threshold violation(s) found", file=sys.stderr
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
