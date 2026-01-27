#!/usr/bin/env python3
"""
Check documentation and type hint coverage in Python code.

Checks:
- Docstring coverage (public functions, classes, modules)
- Type hint coverage (function signatures)
- Output percentages and missing items

Usage:
    python check_documentation.py path/to/file.py
    python check_documentation.py path/to/directory --recursive
    python check_documentation.py path/to/code --output coverage.json
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
class DocumentationItem:
    """Represents an item that should be documented."""

    name: str
    file: str
    line: int
    kind: str  # 'module', 'class', 'function', 'method'
    has_docstring: bool = False
    has_type_hints: bool = False
    missing_param_hints: list[str] = field(default_factory=list)
    missing_return_hint: bool = False
    is_public: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CoverageStats:
    """Documentation coverage statistics."""

    total_items: int = 0
    documented_items: int = 0
    type_hinted_items: int = 0
    docstring_coverage: float = 0.0
    type_hint_coverage: float = 0.0
    missing_docstrings: list[DocumentationItem] = field(default_factory=list)
    missing_type_hints: list[DocumentationItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["missing_docstrings"] = [i.to_dict() for i in self.missing_docstrings]
        result["missing_type_hints"] = [i.to_dict() for i in self.missing_type_hints]
        return result


@dataclass
class FileCoverage:
    """Coverage for a single file."""

    file: str
    has_module_docstring: bool = False
    classes: CoverageStats = field(default_factory=CoverageStats)
    functions: CoverageStats = field(default_factory=CoverageStats)
    methods: CoverageStats = field(default_factory=CoverageStats)
    overall: CoverageStats = field(default_factory=CoverageStats)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "has_module_docstring": self.has_module_docstring,
            "classes": self.classes.to_dict(),
            "functions": self.functions.to_dict(),
            "methods": self.methods.to_dict(),
            "overall": self.overall.to_dict(),
        }


def is_public(name: str) -> bool:
    """
    Check if a name is public (doesn't start with underscore).

    Args:
        name: Name to check

    Returns:
        True if public
    """
    return not name.startswith("_")


def has_docstring(node: ast.AST) -> bool:
    """
    Check if a node has a docstring.

    Args:
        node: AST node to check

    Returns:
        True if has docstring
    """
    return (
        isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, (ast.Constant, ast.Str))
    )


def get_function_type_hint_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[bool, list[str], bool]:
    """
    Analyze type hints for a function.

    Args:
        node: Function AST node

    Returns:
        Tuple of (has_complete_hints, missing_params, missing_return)
    """
    missing_params = []

    # Check regular arguments
    for arg in node.args.args:
        if arg.arg != "self" and arg.arg != "cls" and arg.annotation is None:
            missing_params.append(arg.arg)

    # Check positional-only arguments
    for arg in node.args.posonlyargs:
        if arg.annotation is None:
            missing_params.append(arg.arg)

    # Check keyword-only arguments
    for arg in node.args.kwonlyargs:
        if arg.annotation is None:
            missing_params.append(arg.arg)

    # Check *args
    if node.args.vararg and node.args.vararg.annotation is None:
        missing_params.append(f"*{node.args.vararg.arg}")

    # Check **kwargs
    if node.args.kwarg and node.args.kwarg.annotation is None:
        missing_params.append(f"**{node.args.kwarg.arg}")

    # Check return type (skip for __init__)
    missing_return = node.returns is None and node.name != "__init__"

    has_complete = len(missing_params) == 0 and not missing_return

    return has_complete, missing_params, missing_return


def analyze_file(file_path: Path, public_only: bool = True) -> FileCoverage:
    """
    Analyze documentation coverage for a Python file.

    Args:
        file_path: Path to the Python file
        public_only: Only check public items

    Returns:
        FileCoverage with detailed coverage info
    """
    content = file_path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}", file=sys.stderr)
        return FileCoverage(file=str(file_path))

    coverage = FileCoverage(file=str(file_path))
    coverage.has_module_docstring = has_docstring(tree)

    all_items: list[DocumentationItem] = []

    # Analyze top-level classes and functions
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not public_only or is_public(node.name):
                item = DocumentationItem(
                    name=node.name,
                    file=str(file_path),
                    line=node.lineno,
                    kind="class",
                    has_docstring=has_docstring(node),
                    has_type_hints=True,  # Classes don't need type hints themselves
                    is_public=is_public(node.name),
                )
                all_items.append(item)

                if not item.has_docstring:
                    coverage.classes.missing_docstrings.append(item)

                # Analyze methods
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not public_only or is_public(method.name):
                            has_hints, missing_p, missing_r = (
                                get_function_type_hint_info(method)
                            )
                            method_item = DocumentationItem(
                                name=f"{node.name}.{method.name}",
                                file=str(file_path),
                                line=method.lineno,
                                kind="method",
                                has_docstring=has_docstring(method),
                                has_type_hints=has_hints,
                                missing_param_hints=missing_p,
                                missing_return_hint=missing_r,
                                is_public=is_public(method.name),
                            )
                            all_items.append(method_item)

                            if not method_item.has_docstring:
                                coverage.methods.missing_docstrings.append(method_item)
                            if not method_item.has_type_hints:
                                coverage.methods.missing_type_hints.append(method_item)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not public_only or is_public(node.name):
                has_hints, missing_p, missing_r = get_function_type_hint_info(node)
                item = DocumentationItem(
                    name=node.name,
                    file=str(file_path),
                    line=node.lineno,
                    kind="function",
                    has_docstring=has_docstring(node),
                    has_type_hints=has_hints,
                    missing_param_hints=missing_p,
                    missing_return_hint=missing_r,
                    is_public=is_public(node.name),
                )
                all_items.append(item)

                if not item.has_docstring:
                    coverage.functions.missing_docstrings.append(item)
                if not item.has_type_hints:
                    coverage.functions.missing_type_hints.append(item)

    # Compute statistics
    for stats, kind in [
        (coverage.classes, "class"),
        (coverage.functions, "function"),
        (coverage.methods, "method"),
    ]:
        items = [i for i in all_items if i.kind == kind]
        stats.total_items = len(items)
        stats.documented_items = sum(1 for i in items if i.has_docstring)
        stats.type_hinted_items = sum(1 for i in items if i.has_type_hints)

        if stats.total_items > 0:
            stats.docstring_coverage = stats.documented_items / stats.total_items * 100
            stats.type_hint_coverage = stats.type_hinted_items / stats.total_items * 100

    # Overall statistics
    coverage.overall.total_items = len(all_items)
    coverage.overall.documented_items = sum(1 for i in all_items if i.has_docstring)
    coverage.overall.type_hinted_items = sum(1 for i in all_items if i.has_type_hints)
    coverage.overall.missing_docstrings = [i for i in all_items if not i.has_docstring]
    coverage.overall.missing_type_hints = [i for i in all_items if not i.has_type_hints]

    if coverage.overall.total_items > 0:
        coverage.overall.docstring_coverage = (
            coverage.overall.documented_items / coverage.overall.total_items * 100
        )
        coverage.overall.type_hint_coverage = (
            coverage.overall.type_hinted_items / coverage.overall.total_items * 100
        )

    return coverage


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


def aggregate_coverage(results: list[FileCoverage]) -> CoverageStats:
    """
    Aggregate coverage across multiple files.

    Args:
        results: List of per-file coverage

    Returns:
        Aggregated CoverageStats
    """
    stats = CoverageStats()

    for file_cov in results:
        stats.total_items += file_cov.overall.total_items
        stats.documented_items += file_cov.overall.documented_items
        stats.type_hinted_items += file_cov.overall.type_hinted_items
        stats.missing_docstrings.extend(file_cov.overall.missing_docstrings)
        stats.missing_type_hints.extend(file_cov.overall.missing_type_hints)

    if stats.total_items > 0:
        stats.docstring_coverage = stats.documented_items / stats.total_items * 100
        stats.type_hint_coverage = stats.type_hinted_items / stats.total_items * 100

    return stats


def format_text(results: list[FileCoverage], aggregate: CoverageStats) -> str:
    """
    Format results as plain text.

    Args:
        results: Per-file coverage results
        aggregate: Aggregate statistics

    Returns:
        Formatted text string
    """
    lines = [
        "=" * 80,
        "DOCUMENTATION COVERAGE REPORT",
        "=" * 80,
        "",
    ]

    # Per-file summary
    for file_cov in results:
        lines.append(f"\nFile: {file_cov.file}")
        lines.append(
            f"  Module docstring: {'Yes' if file_cov.has_module_docstring else 'No'}"
        )
        lines.append(
            f"  Docstring coverage: {file_cov.overall.docstring_coverage:.1f}% "
            f"({file_cov.overall.documented_items}/{file_cov.overall.total_items})"
        )
        lines.append(
            f"  Type hint coverage: {file_cov.overall.type_hint_coverage:.1f}% "
            f"({file_cov.overall.type_hinted_items}/{file_cov.overall.total_items})"
        )

    # Overall summary
    lines.extend(
        [
            "",
            "=" * 80,
            "AGGREGATE SUMMARY",
            "=" * 80,
            "",
            f"Total items: {aggregate.total_items}",
            f"Docstring coverage: {aggregate.docstring_coverage:.1f}% "
            f"({aggregate.documented_items}/{aggregate.total_items})",
            f"Type hint coverage: {aggregate.type_hint_coverage:.1f}% "
            f"({aggregate.type_hinted_items}/{aggregate.total_items})",
            "",
        ]
    )

    # Missing docstrings
    if aggregate.missing_docstrings:
        lines.append("-" * 40)
        lines.append(f"MISSING DOCSTRINGS ({len(aggregate.missing_docstrings)}):")
        lines.append("-" * 40)
        for item in sorted(
            aggregate.missing_docstrings, key=lambda x: (x.file, x.line)
        ):
            lines.append(f"  {item.file}:{item.line} {item.kind} {item.name}")
        lines.append("")

    # Missing type hints
    if aggregate.missing_type_hints:
        lines.append("-" * 40)
        lines.append(f"MISSING TYPE HINTS ({len(aggregate.missing_type_hints)}):")
        lines.append("-" * 40)
        for item in sorted(
            aggregate.missing_type_hints, key=lambda x: (x.file, x.line)
        ):
            details = []
            if item.missing_param_hints:
                details.append(f"params: {', '.join(item.missing_param_hints)}")
            if item.missing_return_hint:
                details.append("return")
            detail_str = f" ({', '.join(details)})" if details else ""
            lines.append(
                f"  {item.file}:{item.line} {item.kind} {item.name}{detail_str}"
            )

    return "\n".join(lines)


def format_markdown(results: list[FileCoverage], aggregate: CoverageStats) -> str:
    """
    Format results as Markdown.

    Args:
        results: Per-file coverage results
        aggregate: Aggregate statistics

    Returns:
        Markdown formatted string
    """
    lines = [
        "# Documentation Coverage Report",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Items | {aggregate.total_items} |",
        f"| Docstring Coverage | {aggregate.docstring_coverage:.1f}% |",
        f"| Type Hint Coverage | {aggregate.type_hint_coverage:.1f}% |",
        f"| Missing Docstrings | {len(aggregate.missing_docstrings)} |",
        f"| Missing Type Hints | {len(aggregate.missing_type_hints)} |",
        "",
    ]

    # Per-file breakdown
    lines.extend(["## Per-File Coverage", ""])
    lines.append("| File | Docstrings | Type Hints |")
    lines.append("|------|------------|------------|")
    for file_cov in results:
        name = Path(file_cov.file).name
        lines.append(
            f"| `{name}` | {file_cov.overall.docstring_coverage:.0f}% | "
            f"{file_cov.overall.type_hint_coverage:.0f}% |"
        )
    lines.append("")

    # Missing docstrings
    if aggregate.missing_docstrings:
        lines.extend(
            [f"## Missing Docstrings ({len(aggregate.missing_docstrings)})", ""]
        )
        lines.append("| File | Line | Kind | Name |")
        lines.append("|------|------|------|------|")
        for item in sorted(
            aggregate.missing_docstrings, key=lambda x: (x.file, x.line)
        )[:50]:
            lines.append(
                f"| `{Path(item.file).name}` | {item.line} | {item.kind} | `{item.name}` |"
            )
        if len(aggregate.missing_docstrings) > 50:
            lines.append(f"\n*... and {len(aggregate.missing_docstrings) - 50} more*")
        lines.append("")

    # Missing type hints
    if aggregate.missing_type_hints:
        lines.extend(
            [f"## Missing Type Hints ({len(aggregate.missing_type_hints)})", ""]
        )
        lines.append("| File | Line | Name | Missing |")
        lines.append("|------|------|------|---------|")
        for item in sorted(
            aggregate.missing_type_hints, key=lambda x: (x.file, x.line)
        )[:50]:
            missing = []
            if item.missing_param_hints:
                missing.extend(item.missing_param_hints[:3])
                if len(item.missing_param_hints) > 3:
                    missing.append("...")
            if item.missing_return_hint:
                missing.append("return")
            lines.append(
                f"| `{Path(item.file).name}` | {item.line} | `{item.name}` | "
                f"{', '.join(missing)} |"
            )
        if len(aggregate.missing_type_hints) > 50:
            lines.append(f"\n*... and {len(aggregate.missing_type_hints) - 50} more*")

    return "\n".join(lines)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 if coverage met, 1 otherwise)
    """
    parser = argparse.ArgumentParser(
        description="Check documentation and type hint coverage in Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s src/module.py
    %(prog)s src/ --recursive
    %(prog)s src/ -r --min-docstring 80 --min-typehint 90
    %(prog)s src/ -r --output coverage.json
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
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--min-docstring",
        type=float,
        default=0,
        help="Minimum docstring coverage percentage (default: 0)",
    )
    parser.add_argument(
        "--min-typehint",
        type=float,
        default=0,
        help="Minimum type hint coverage percentage (default: 0)",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private items (starting with _)",
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        return 1

    files = collect_python_files(args.path, args.recursive)
    if not files:
        print(f"No Python files found in {args.path}", file=sys.stderr)
        return 1

    # Analyze files
    results = [analyze_file(f, public_only=not args.include_private) for f in files]
    aggregate = aggregate_coverage(results)

    # Prepare output
    output_data = {
        "aggregate": aggregate.to_dict(),
        "files": [r.to_dict() for r in results],
    }

    # Write JSON output
    if args.output:
        args.output.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
        print(f"Coverage report written to {args.output}")

    # Display formatted output
    if args.format == "json":
        print(json.dumps(output_data, indent=2))
    elif args.format == "markdown":
        print(format_markdown(results, aggregate))
    else:
        print(format_text(results, aggregate))

    # Check thresholds
    exit_code = 0

    if aggregate.docstring_coverage < args.min_docstring:
        print(
            f"\nFailed: Docstring coverage {aggregate.docstring_coverage:.1f}% "
            f"< {args.min_docstring}%",
            file=sys.stderr,
        )
        exit_code = 1

    if aggregate.type_hint_coverage < args.min_typehint:
        print(
            f"\nFailed: Type hint coverage {aggregate.type_hint_coverage:.1f}% "
            f"< {args.min_typehint}%",
            file=sys.stderr,
        )
        exit_code = 1

    if exit_code == 0 and (args.min_docstring > 0 or args.min_typehint > 0):
        print("\nAll coverage thresholds met!")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
