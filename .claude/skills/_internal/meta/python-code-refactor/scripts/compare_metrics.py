#!/usr/bin/env python3
"""
Compare before/after complexity metric files.

Compares two JSON metric files (from measure_complexity.py) and reports:
- Complexity changes per function
- Function length changes
- Improvements vs regressions
- Summary table output

Usage:
    python compare_metrics.py before.json after.json
    python compare_metrics.py before.json after.json --output comparison.json
    python compare_metrics.py before.json after.json --format markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FunctionKey:
    """Unique identifier for a function."""

    file: str
    name: str

    def __hash__(self) -> int:
        """Make hashable for dict operations."""
        return hash((self.file, self.name))

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, FunctionKey):
            return False
        return self.file == other.file and self.name == other.name


@dataclass
class FunctionChange:
    """Change in metrics for a single function."""

    name: str
    file: str
    line: int
    cc_before: int
    cc_after: int
    cc_delta: int
    cog_before: int
    cog_after: int
    cog_delta: int
    len_before: int
    len_after: int
    len_delta: int
    nest_before: int
    nest_after: int
    nest_delta: int
    is_new: bool = False
    is_removed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "file": self.file,
            "line": self.line,
            "cyclomatic_complexity": {
                "before": self.cc_before,
                "after": self.cc_after,
                "delta": self.cc_delta,
            },
            "cognitive_complexity": {
                "before": self.cog_before,
                "after": self.cog_after,
                "delta": self.cog_delta,
            },
            "length": {
                "before": self.len_before,
                "after": self.len_after,
                "delta": self.len_delta,
            },
            "nesting_depth": {
                "before": self.nest_before,
                "after": self.nest_after,
                "delta": self.nest_delta,
            },
            "is_new": self.is_new,
            "is_removed": self.is_removed,
        }

    @property
    def is_improved(self) -> bool:
        """Check if function metrics improved overall."""
        return (self.cc_delta < 0 or self.cog_delta < 0) and not (
            self.cc_delta > 0 or self.cog_delta > 0
        )

    @property
    def is_regressed(self) -> bool:
        """Check if function metrics regressed overall."""
        return self.cc_delta > 0 or self.cog_delta > 0


@dataclass
class MetricsComparison:
    """Complete comparison of two metric reports."""

    before_file: str
    after_file: str
    changes: list[FunctionChange] = field(default_factory=list)
    new_functions: list[FunctionChange] = field(default_factory=list)
    removed_functions: list[FunctionChange] = field(default_factory=list)
    improved: list[FunctionChange] = field(default_factory=list)
    regressed: list[FunctionChange] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "before_file": self.before_file,
            "after_file": self.after_file,
            "summary": self.summary,
            "changes": [c.to_dict() for c in self.changes],
            "new_functions": [c.to_dict() for c in self.new_functions],
            "removed_functions": [c.to_dict() for c in self.removed_functions],
            "improved": [c.to_dict() for c in self.improved],
            "regressed": [c.to_dict() for c in self.regressed],
        }


def load_metrics(path: Path) -> dict[str, Any]:
    """
    Load a metrics JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Parsed metrics dictionary
    """
    content = path.read_text(encoding="utf-8")
    return json.loads(content)


def extract_functions(
    metrics: dict[str, Any],
) -> dict[FunctionKey, dict[str, Any]]:
    """
    Extract functions from metrics into a keyed dictionary.

    Args:
        metrics: Parsed metrics report

    Returns:
        Dictionary mapping FunctionKey to function metrics
    """
    functions = {}

    for file_data in metrics.get("files", []):
        file_path = file_data.get("file", "")
        for func in file_data.get("functions", []):
            key = FunctionKey(file=file_path, name=func.get("name", ""))
            functions[key] = func

    return functions


def compare_metrics(before: dict[str, Any], after: dict[str, Any]) -> MetricsComparison:
    """
    Compare two metrics reports.

    Args:
        before: Baseline metrics
        after: New metrics to compare

    Returns:
        MetricsComparison with detailed changes
    """
    before_funcs = extract_functions(before)
    after_funcs = extract_functions(after)

    before_keys = set(before_funcs.keys())
    after_keys = set(after_funcs.keys())

    comparison = MetricsComparison(
        before_file="before",
        after_file="after",
    )

    # Find changed functions
    common_keys = before_keys & after_keys
    for key in common_keys:
        b = before_funcs[key]
        a = after_funcs[key]

        change = FunctionChange(
            name=key.name,
            file=key.file,
            line=a.get("line_start", 0),
            cc_before=b.get("cyclomatic_complexity", 0),
            cc_after=a.get("cyclomatic_complexity", 0),
            cc_delta=a.get("cyclomatic_complexity", 0)
            - b.get("cyclomatic_complexity", 0),
            cog_before=b.get("cognitive_complexity", 0),
            cog_after=a.get("cognitive_complexity", 0),
            cog_delta=a.get("cognitive_complexity", 0)
            - b.get("cognitive_complexity", 0),
            len_before=b.get("length", 0),
            len_after=a.get("length", 0),
            len_delta=a.get("length", 0) - b.get("length", 0),
            nest_before=b.get("max_nesting_depth", 0),
            nest_after=a.get("max_nesting_depth", 0),
            nest_delta=a.get("max_nesting_depth", 0) - b.get("max_nesting_depth", 0),
        )

        # Only include if something changed
        if any(
            [
                change.cc_delta != 0,
                change.cog_delta != 0,
                change.len_delta != 0,
                change.nest_delta != 0,
            ]
        ):
            comparison.changes.append(change)

            if change.is_improved:
                comparison.improved.append(change)
            elif change.is_regressed:
                comparison.regressed.append(change)

    # Find new functions
    for key in after_keys - before_keys:
        a = after_funcs[key]
        change = FunctionChange(
            name=key.name,
            file=key.file,
            line=a.get("line_start", 0),
            cc_before=0,
            cc_after=a.get("cyclomatic_complexity", 0),
            cc_delta=a.get("cyclomatic_complexity", 0),
            cog_before=0,
            cog_after=a.get("cognitive_complexity", 0),
            cog_delta=a.get("cognitive_complexity", 0),
            len_before=0,
            len_after=a.get("length", 0),
            len_delta=a.get("length", 0),
            nest_before=0,
            nest_after=a.get("max_nesting_depth", 0),
            nest_delta=a.get("max_nesting_depth", 0),
            is_new=True,
        )
        comparison.new_functions.append(change)

    # Find removed functions
    for key in before_keys - after_keys:
        b = before_funcs[key]
        change = FunctionChange(
            name=key.name,
            file=key.file,
            line=b.get("line_start", 0),
            cc_before=b.get("cyclomatic_complexity", 0),
            cc_after=0,
            cc_delta=-b.get("cyclomatic_complexity", 0),
            cog_before=b.get("cognitive_complexity", 0),
            cog_after=0,
            cog_delta=-b.get("cognitive_complexity", 0),
            len_before=b.get("length", 0),
            len_after=0,
            len_delta=-b.get("length", 0),
            nest_before=b.get("max_nesting_depth", 0),
            nest_after=0,
            nest_delta=-b.get("max_nesting_depth", 0),
            is_removed=True,
        )
        comparison.removed_functions.append(change)

    # Compute summary
    all_cc_delta = sum(c.cc_delta for c in comparison.changes)
    all_cog_delta = sum(c.cog_delta for c in comparison.changes)
    all_len_delta = sum(c.len_delta for c in comparison.changes)

    comparison.summary = {
        "functions_before": len(before_funcs),
        "functions_after": len(after_funcs),
        "functions_changed": len(comparison.changes),
        "functions_improved": len(comparison.improved),
        "functions_regressed": len(comparison.regressed),
        "functions_new": len(comparison.new_functions),
        "functions_removed": len(comparison.removed_functions),
        "total_cc_delta": all_cc_delta,
        "total_cog_delta": all_cog_delta,
        "total_length_delta": all_len_delta,
        "overall_improved": all_cc_delta <= 0 and all_cog_delta <= 0,
    }

    return comparison


def format_text(comparison: MetricsComparison) -> str:
    """
    Format comparison as plain text.

    Args:
        comparison: MetricsComparison to format

    Returns:
        Formatted text string
    """
    lines = [
        "=" * 80,
        "METRICS COMPARISON REPORT",
        "=" * 80,
        "",
        "SUMMARY",
        "-" * 40,
        f"Functions before: {comparison.summary['functions_before']}",
        f"Functions after:  {comparison.summary['functions_after']}",
        f"Functions changed: {comparison.summary['functions_changed']}",
        f"Functions improved: {comparison.summary['functions_improved']}",
        f"Functions regressed: {comparison.summary['functions_regressed']}",
        f"New functions: {comparison.summary['functions_new']}",
        f"Removed functions: {comparison.summary['functions_removed']}",
        "",
        f"Total cyclomatic complexity delta: {comparison.summary['total_cc_delta']:+d}",
        f"Total cognitive complexity delta: {comparison.summary['total_cog_delta']:+d}",
        f"Total length delta: {comparison.summary['total_length_delta']:+d}",
        "",
    ]

    if comparison.summary["overall_improved"]:
        lines.append("Status: IMPROVED")
    elif comparison.regressed:
        lines.append("Status: REGRESSED")
    else:
        lines.append("Status: UNCHANGED")
    lines.append("")

    # Regressed functions
    if comparison.regressed:
        lines.append("-" * 40)
        lines.append("REGRESSED FUNCTIONS:")
        lines.append("-" * 40)
        for c in sorted(
            comparison.regressed, key=lambda x: -(x.cc_delta + x.cog_delta)
        ):
            lines.append(f"  {c.file}:{c.line} {c.name}")
            lines.append(
                f"    CC: {c.cc_before} -> {c.cc_after} ({c.cc_delta:+d}), "
                f"Cog: {c.cog_before} -> {c.cog_after} ({c.cog_delta:+d})"
            )
        lines.append("")

    # Improved functions
    if comparison.improved:
        lines.append("-" * 40)
        lines.append("IMPROVED FUNCTIONS:")
        lines.append("-" * 40)
        for c in sorted(comparison.improved, key=lambda x: x.cc_delta + x.cog_delta):
            lines.append(f"  {c.file}:{c.line} {c.name}")
            lines.append(
                f"    CC: {c.cc_before} -> {c.cc_after} ({c.cc_delta:+d}), "
                f"Cog: {c.cog_before} -> {c.cog_after} ({c.cog_delta:+d})"
            )
        lines.append("")

    # New functions with high complexity
    high_complexity_new = [
        c for c in comparison.new_functions if c.cc_after > 10 or c.cog_after > 15
    ]
    if high_complexity_new:
        lines.append("-" * 40)
        lines.append("NEW HIGH-COMPLEXITY FUNCTIONS:")
        lines.append("-" * 40)
        for c in high_complexity_new:
            lines.append(f"  {c.file}:{c.line} {c.name}")
            lines.append(f"    CC: {c.cc_after}, Cog: {c.cog_after}")
        lines.append("")

    return "\n".join(lines)


def format_markdown(comparison: MetricsComparison) -> str:
    """
    Format comparison as Markdown.

    Args:
        comparison: MetricsComparison to format

    Returns:
        Markdown formatted string
    """
    status = (
        "Improved"
        if comparison.summary["overall_improved"]
        else "Regressed" if comparison.regressed else "Unchanged"
    )

    lines = [
        "# Metrics Comparison Report",
        "",
        f"**Status**: {status}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Functions Before | {comparison.summary['functions_before']} |",
        f"| Functions After | {comparison.summary['functions_after']} |",
        f"| Functions Changed | {comparison.summary['functions_changed']} |",
        f"| Functions Improved | {comparison.summary['functions_improved']} |",
        f"| Functions Regressed | {comparison.summary['functions_regressed']} |",
        f"| Total CC Delta | {comparison.summary['total_cc_delta']:+d} |",
        f"| Total Cog Delta | {comparison.summary['total_cog_delta']:+d} |",
        "",
    ]

    # Regressed functions table
    if comparison.regressed:
        lines.extend(["## Regressed Functions", ""])
        lines.append("| Function | File | CC | Cog | Length |")
        lines.append("|----------|------|----|----|--------|")
        for c in sorted(
            comparison.regressed, key=lambda x: -(x.cc_delta + x.cog_delta)
        ):
            lines.append(
                f"| `{c.name}` | `{Path(c.file).name}:{c.line}` | "
                f"{c.cc_before}->{c.cc_after} ({c.cc_delta:+d}) | "
                f"{c.cog_before}->{c.cog_after} ({c.cog_delta:+d}) | "
                f"{c.len_before}->{c.len_after} ({c.len_delta:+d}) |"
            )
        lines.append("")

    # Improved functions table
    if comparison.improved:
        lines.extend(["## Improved Functions", ""])
        lines.append("| Function | File | CC | Cog | Length |")
        lines.append("|----------|------|----|----|--------|")
        for c in sorted(comparison.improved, key=lambda x: x.cc_delta + x.cog_delta):
            lines.append(
                f"| `{c.name}` | `{Path(c.file).name}:{c.line}` | "
                f"{c.cc_before}->{c.cc_after} ({c.cc_delta:+d}) | "
                f"{c.cog_before}->{c.cog_after} ({c.cog_delta:+d}) | "
                f"{c.len_before}->{c.len_after} ({c.len_delta:+d}) |"
            )
        lines.append("")

    # New functions
    if comparison.new_functions:
        lines.extend([f"## New Functions ({len(comparison.new_functions)})", ""])
        lines.append("| Function | File | CC | Cog |")
        lines.append("|----------|------|----|-----|")
        for c in sorted(
            comparison.new_functions, key=lambda x: -(x.cc_after + x.cog_after)
        )[:20]:
            lines.append(
                f"| `{c.name}` | `{Path(c.file).name}:{c.line}` | "
                f"{c.cc_after} | {c.cog_after} |"
            )
        if len(comparison.new_functions) > 20:
            lines.append(f"\n*... and {len(comparison.new_functions) - 20} more*")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 if improved or unchanged, 1 if regressed)
    """
    parser = argparse.ArgumentParser(
        description="Compare before/after complexity metric files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s before.json after.json
    %(prog)s before.json after.json --output comparison.json
    %(prog)s before.json after.json --format markdown
    %(prog)s before.json after.json --fail-on-regression
        """,
    )
    parser.add_argument("before", type=Path, help="Before (baseline) metrics JSON")
    parser.add_argument("after", type=Path, help="After metrics JSON")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output file for JSON comparison"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit non-zero if any function regressed",
    )
    parser.add_argument(
        "--max-new-complexity",
        type=int,
        default=10,
        help="Max CC allowed for new functions (default: 10)",
    )

    args = parser.parse_args()

    # Validate inputs
    for path in [args.before, args.after]:
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            return 2

    # Load metrics
    try:
        before = load_metrics(args.before)
        after = load_metrics(args.after)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 2

    # Compare
    comparison = compare_metrics(before, after)

    # Write JSON output
    if args.output:
        args.output.write_text(
            json.dumps(comparison.to_dict(), indent=2), encoding="utf-8"
        )
        print(f"Comparison written to {args.output}")

    # Display formatted output
    if args.format == "json":
        print(json.dumps(comparison.to_dict(), indent=2))
    elif args.format == "markdown":
        print(format_markdown(comparison))
    else:
        print(format_text(comparison))

    # Determine exit code
    exit_code = 0

    if args.fail_on_regression and comparison.regressed:
        print(
            f"\nFailed: {len(comparison.regressed)} function(s) regressed",
            file=sys.stderr,
        )
        exit_code = 1

    # Check new functions for high complexity
    high_complexity_new = [
        c for c in comparison.new_functions if c.cc_after > args.max_new_complexity
    ]
    if high_complexity_new:
        print(
            f"\nWarning: {len(high_complexity_new)} new function(s) exceed "
            f"complexity threshold {args.max_new_complexity}",
            file=sys.stderr,
        )
        if args.fail_on_regression:
            exit_code = 1

    if exit_code == 0:
        if comparison.summary["overall_improved"]:
            print("\nMetrics improved!")
        else:
            print("\nNo regressions detected.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
