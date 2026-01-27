#!/usr/bin/env python3
"""
Compare before/after flake8 reports to detect regressions.

Compares two flake8 JSON reports and reports:
- New issues introduced
- Issues resolved
- Issue count delta
- Exit non-zero if issues increased

Usage:
    python compare_flake8_reports.py before.json after.json
    python compare_flake8_reports.py before.json after.json --output diff.json
    python compare_flake8_reports.py before.json after.json --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class IssueKey:
    """Unique identifier for an issue."""

    file: str
    line: int
    code: str

    def __hash__(self) -> int:
        """Make hashable for set operations."""
        return hash((self.file, self.line, self.code))

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, IssueKey):
            return False
        return (
            self.file == other.file
            and self.line == other.line
            and self.code == other.code
        )


@dataclass
class ComparisonResult:
    """Result of comparing two flake8 reports."""

    before_total: int = 0
    after_total: int = 0
    new_issues: list[dict[str, Any]] = field(default_factory=list)
    resolved_issues: list[dict[str, Any]] = field(default_factory=list)
    delta: int = 0
    improved: bool = False
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)
    by_code: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "before_total": self.before_total,
            "after_total": self.after_total,
            "delta": self.delta,
            "improved": self.improved,
            "new_issues_count": len(self.new_issues),
            "resolved_issues_count": len(self.resolved_issues),
            "new_issues": self.new_issues,
            "resolved_issues": self.resolved_issues,
            "by_category": self.by_category,
            "by_code": self.by_code,
        }


def load_report(path: Path) -> dict[str, Any]:
    """
    Load a flake8 JSON report.

    Args:
        path: Path to JSON report file

    Returns:
        Parsed report dictionary
    """
    content = path.read_text(encoding="utf-8")
    return json.loads(content)


def extract_issues(report: dict[str, Any]) -> dict[IssueKey, dict[str, Any]]:
    """
    Extract issues from a report into a keyed dictionary.

    Args:
        report: Parsed flake8 report

    Returns:
        Dictionary mapping IssueKey to issue details
    """
    issues = {}
    for issue in report.get("issues", []):
        key = IssueKey(
            file=issue.get("file", ""),
            line=issue.get("line", 0),
            code=issue.get("code", ""),
        )
        issues[key] = issue
    return issues


def compare_reports(before: dict[str, Any], after: dict[str, Any]) -> ComparisonResult:
    """
    Compare two flake8 reports.

    Args:
        before: The baseline report
        after: The new report to compare against baseline

    Returns:
        ComparisonResult with detailed comparison data
    """
    before_issues = extract_issues(before)
    after_issues = extract_issues(after)

    before_keys = set(before_issues.keys())
    after_keys = set(after_issues.keys())

    new_keys = after_keys - before_keys
    resolved_keys = before_keys - after_keys

    result = ComparisonResult(
        before_total=len(before_issues),
        after_total=len(after_issues),
        new_issues=[after_issues[k] for k in new_keys],
        resolved_issues=[before_issues[k] for k in resolved_keys],
        delta=len(after_issues) - len(before_issues),
        improved=len(after_issues) < len(before_issues),
    )

    # Compute changes by category
    before_categories: dict[str, int] = {}
    after_categories: dict[str, int] = {}

    for issue in before_issues.values():
        cat = issue.get("category", "Other")
        before_categories[cat] = before_categories.get(cat, 0) + 1

    for issue in after_issues.values():
        cat = issue.get("category", "Other")
        after_categories[cat] = after_categories.get(cat, 0) + 1

    all_categories = set(before_categories.keys()) | set(after_categories.keys())
    for cat in all_categories:
        b = before_categories.get(cat, 0)
        a = after_categories.get(cat, 0)
        result.by_category[cat] = {"before": b, "after": a, "delta": a - b}

    # Compute changes by code
    before_codes: dict[str, int] = {}
    after_codes: dict[str, int] = {}

    for issue in before_issues.values():
        code = issue.get("code", "")
        before_codes[code] = before_codes.get(code, 0) + 1

    for issue in after_issues.values():
        code = issue.get("code", "")
        after_codes[code] = after_codes.get(code, 0) + 1

    all_codes = set(before_codes.keys()) | set(after_codes.keys())
    for code in all_codes:
        b = before_codes.get(code, 0)
        a = after_codes.get(code, 0)
        result.by_code[code] = {"before": b, "after": a, "delta": a - b}

    return result


def format_text(result: ComparisonResult) -> str:
    """
    Format comparison result as plain text.

    Args:
        result: ComparisonResult to format

    Returns:
        Formatted text string
    """
    lines = [
        "=" * 80,
        "FLAKE8 REPORT COMPARISON",
        "=" * 80,
        "",
        f"Before: {result.before_total} issues",
        f"After:  {result.after_total} issues",
        f"Delta:  {result.delta:+d} issues",
        "",
    ]

    if result.improved:
        lines.append("Status: IMPROVED")
    elif result.delta > 0:
        lines.append("Status: REGRESSED")
    else:
        lines.append("Status: UNCHANGED")
    lines.append("")

    # Summary by category
    if result.by_category:
        lines.append("-" * 40)
        lines.append("Changes by Category:")
        lines.append("-" * 40)
        for cat, changes in sorted(
            result.by_category.items(), key=lambda x: abs(x[1]["delta"]), reverse=True
        ):
            delta = changes["delta"]
            if delta != 0:
                sign = "+" if delta > 0 else ""
                lines.append(
                    f"  {cat}: {changes['before']} -> {changes['after']} ({sign}{delta})"
                )
        lines.append("")

    # New issues
    if result.new_issues:
        lines.append("-" * 40)
        lines.append(f"NEW ISSUES ({len(result.new_issues)}):")
        lines.append("-" * 40)
        for issue in sorted(result.new_issues, key=lambda x: (x["file"], x["line"])):
            lines.append(
                f"  {issue['file']}:{issue['line']} {issue['code']} {issue['message']}"
            )
        lines.append("")

    # Resolved issues
    if result.resolved_issues:
        lines.append("-" * 40)
        lines.append(f"RESOLVED ISSUES ({len(result.resolved_issues)}):")
        lines.append("-" * 40)
        for issue in sorted(
            result.resolved_issues, key=lambda x: (x["file"], x["line"])
        ):
            lines.append(
                f"  {issue['file']}:{issue['line']} {issue['code']} {issue['message']}"
            )
        lines.append("")

    # Top code changes
    significant_changes = [
        (code, changes)
        for code, changes in result.by_code.items()
        if changes["delta"] != 0
    ]
    if significant_changes:
        lines.append("-" * 40)
        lines.append("Significant Code Changes:")
        lines.append("-" * 40)
        for code, changes in sorted(
            significant_changes, key=lambda x: abs(x[1]["delta"]), reverse=True
        )[:15]:
            delta = changes["delta"]
            sign = "+" if delta > 0 else ""
            lines.append(
                f"  {code}: {changes['before']} -> {changes['after']} ({sign}{delta})"
            )

    return "\n".join(lines)


def format_markdown(result: ComparisonResult) -> str:
    """
    Format comparison result as Markdown.

    Args:
        result: ComparisonResult to format

    Returns:
        Markdown formatted string
    """
    status_emoji = ""
    if result.improved:
        status_emoji = "Improved"
    elif result.delta > 0:
        status_emoji = "Regressed"
    else:
        status_emoji = "Unchanged"

    lines = [
        "# Flake8 Report Comparison",
        "",
        f"**Status**: {status_emoji}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Before | {result.before_total} |",
        f"| After | {result.after_total} |",
        f"| Delta | {result.delta:+d} |",
        f"| New Issues | {len(result.new_issues)} |",
        f"| Resolved Issues | {len(result.resolved_issues)} |",
        "",
    ]

    # Category changes
    category_changes = [
        (cat, c) for cat, c in result.by_category.items() if c["delta"] != 0
    ]
    if category_changes:
        lines.extend(["## Changes by Category", ""])
        lines.append("| Category | Before | After | Delta |")
        lines.append("|----------|--------|-------|-------|")
        for cat, changes in sorted(
            category_changes, key=lambda x: abs(x[1]["delta"]), reverse=True
        ):
            delta = (
                f"+{changes['delta']}"
                if changes["delta"] > 0
                else str(changes["delta"])
            )
            lines.append(
                f"| {cat} | {changes['before']} | {changes['after']} | {delta} |"
            )
        lines.append("")

    # New issues
    if result.new_issues:
        lines.extend([f"## New Issues ({len(result.new_issues)})", ""])
        lines.append("| File | Line | Code | Message |")
        lines.append("|------|------|------|---------|")
        for issue in sorted(result.new_issues, key=lambda x: (x["file"], x["line"]))[
            :50
        ]:
            msg = (
                issue["message"][:50] + "..."
                if len(issue["message"]) > 50
                else issue["message"]
            )
            lines.append(
                f"| `{issue['file']}` | {issue['line']} | `{issue['code']}` | {msg} |"
            )
        if len(result.new_issues) > 50:
            lines.append(f"\n*... and {len(result.new_issues) - 50} more*")
        lines.append("")

    # Resolved issues
    if result.resolved_issues:
        lines.extend([f"## Resolved Issues ({len(result.resolved_issues)})", ""])
        lines.append("| File | Line | Code | Message |")
        lines.append("|------|------|------|---------|")
        for issue in sorted(
            result.resolved_issues, key=lambda x: (x["file"], x["line"])
        )[:50]:
            msg = (
                issue["message"][:50] + "..."
                if len(issue["message"]) > 50
                else issue["message"]
            )
            lines.append(
                f"| `{issue['file']}` | {issue['line']} | `{issue['code']}` | {msg} |"
            )
        if len(result.resolved_issues) > 50:
            lines.append(f"\n*... and {len(result.resolved_issues) - 50} more*")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 if improved or unchanged, 1 if regressed)
    """
    parser = argparse.ArgumentParser(
        description="Compare before/after flake8 reports to detect regressions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s before.json after.json
    %(prog)s before.json after.json --output diff.json
    %(prog)s before.json after.json --format markdown
    %(prog)s before.json after.json --strict
        """,
    )
    parser.add_argument(
        "before", type=Path, help="Before (baseline) flake8 JSON report"
    )
    parser.add_argument("after", type=Path, help="After flake8 JSON report")
    parser.add_argument("-o", "--output", type=Path, help="Output file for JSON diff")
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any new issues introduced (even if total decreased)",
    )
    parser.add_argument(
        "--allow-increase",
        type=int,
        default=0,
        help="Allow up to N new issues before failing (default: 0)",
    )

    args = parser.parse_args()

    # Validate inputs
    for path in [args.before, args.after]:
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            return 2

    # Load reports
    try:
        before = load_report(args.before)
        after = load_report(args.after)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 2

    # Compare
    result = compare_reports(before, after)

    # Output JSON if requested
    if args.output:
        args.output.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        print(f"Comparison written to {args.output}")

    # Display formatted output
    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2))
    elif args.format == "markdown":
        print(format_markdown(result))
    else:
        print(format_text(result))

    # Determine exit code
    if args.strict and result.new_issues:
        print(
            f"\nFailed: {len(result.new_issues)} new issue(s) introduced",
            file=sys.stderr,
        )
        return 1

    if result.delta > args.allow_increase:
        print(
            f"\nFailed: Issue count increased by {result.delta} "
            f"(allowed: {args.allow_increase})",
            file=sys.stderr,
        )
        return 1

    if result.improved:
        print(f"\nSuccess: Improved by {-result.delta} issue(s)")
    elif result.delta == 0:
        print("\nSuccess: No change in issue count")
    else:
        print(f"\nWarning: Increased by {result.delta} issue(s) (within threshold)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
