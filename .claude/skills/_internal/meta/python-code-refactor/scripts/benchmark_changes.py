#!/usr/bin/env python3
"""
Performance regression detection through benchmarking.

Features:
- Run defined benchmarks
- Compare timings before/after
- Flag if >10% degradation
- Output comparison report

Usage:
    python benchmark_changes.py run --module mymodule --output baseline.json
    python benchmark_changes.py compare baseline.json current.json
    python benchmark_changes.py run --module mymodule --compare baseline.json
"""

from __future__ import annotations

import argparse
import gc
import importlib
import json
import statistics
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class BenchmarkResult:
    """Result of a single benchmark."""

    name: str
    iterations: int
    mean_time: float  # seconds
    median_time: float
    std_dev: float
    min_time: float
    max_time: float
    total_time: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BenchmarkComparison:
    """Comparison of two benchmark results."""

    name: str
    before_mean: float
    after_mean: float
    delta_percent: float
    is_regression: bool
    is_improvement: bool
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""

    timestamp: str
    module: str
    python_version: str
    results: list[BenchmarkResult] = field(default_factory=list)
    total_time: float = 0.0
    errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["results"] = [r.to_dict() for r in self.results]
        return result


@dataclass
class ComparisonReport:
    """Comparison of two benchmark reports."""

    before_file: str
    after_file: str
    threshold_percent: float
    comparisons: list[BenchmarkComparison] = field(default_factory=list)
    regressions: list[BenchmarkComparison] = field(default_factory=list)
    improvements: list[BenchmarkComparison] = field(default_factory=list)
    has_regressions: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "before_file": self.before_file,
            "after_file": self.after_file,
            "threshold_percent": self.threshold_percent,
            "has_regressions": self.has_regressions,
            "comparisons": [c.to_dict() for c in self.comparisons],
            "regressions": [c.to_dict() for c in self.regressions],
            "improvements": [c.to_dict() for c in self.improvements],
        }
        return result


def discover_benchmarks(module_path: str) -> list[tuple[str, Callable[[], None]]]:
    """
    Discover benchmark functions in a module.

    Benchmark functions should be named with 'benchmark_' prefix.

    Args:
        module_path: Module path (e.g., 'mypackage.benchmarks')

    Returns:
        List of (name, function) tuples
    """
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error importing module {module_path}: {e}", file=sys.stderr)
        return []

    benchmarks = []
    for name in dir(module):
        if name.startswith("benchmark_"):
            func = getattr(module, name)
            if callable(func):
                benchmarks.append((name, func))

    return benchmarks


def run_benchmark(
    name: str,
    func: Callable[[], None],
    iterations: int = 100,
    warmup: int = 10,
) -> BenchmarkResult:
    """
    Run a single benchmark function.

    Args:
        name: Benchmark name
        func: Function to benchmark
        iterations: Number of iterations
        warmup: Number of warmup iterations (not counted)

    Returns:
        BenchmarkResult with timing statistics
    """
    # Warmup
    for _ in range(warmup):
        try:
            func()
        except Exception:
            pass

    # Collect garbage before timing
    gc.collect()
    gc.disable()

    times = []
    error = None

    try:
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        # Fill with zeros if error occurred
        while len(times) < iterations:
            times.append(0.0)
    finally:
        gc.enable()

    if not times:
        times = [0.0]

    return BenchmarkResult(
        name=name,
        iterations=iterations,
        mean_time=statistics.mean(times),
        median_time=statistics.median(times),
        std_dev=statistics.stdev(times) if len(times) > 1 else 0.0,
        min_time=min(times),
        max_time=max(times),
        total_time=sum(times),
        error=error,
    )


def run_benchmarks(
    module_path: str,
    iterations: int = 100,
    warmup: int = 10,
    pattern: str | None = None,
) -> BenchmarkReport:
    """
    Run all benchmarks in a module.

    Args:
        module_path: Module path
        iterations: Iterations per benchmark
        warmup: Warmup iterations
        pattern: Optional pattern to filter benchmark names

    Returns:
        BenchmarkReport with all results
    """
    import datetime

    benchmarks = discover_benchmarks(module_path)

    if pattern:
        benchmarks = [(n, f) for n, f in benchmarks if pattern in n]

    report = BenchmarkReport(
        timestamp=datetime.datetime.now().isoformat(),
        module=module_path,
        python_version=sys.version,
    )

    start_time = time.perf_counter()

    for name, func in benchmarks:
        print(f"Running {name}...", file=sys.stderr)
        result = run_benchmark(name, func, iterations, warmup)
        report.results.append(result)
        if result.error:
            report.errors += 1
            print(f"  Error: {result.error}", file=sys.stderr)
        else:
            print(f"  Mean: {result.mean_time * 1000:.3f}ms", file=sys.stderr)

    report.total_time = time.perf_counter() - start_time
    return report


def compare_reports(
    before: BenchmarkReport,
    after: BenchmarkReport,
    threshold_percent: float = 10.0,
) -> ComparisonReport:
    """
    Compare two benchmark reports.

    Args:
        before: Baseline report
        after: New report
        threshold_percent: Regression threshold percentage

    Returns:
        ComparisonReport with comparisons
    """
    before_by_name = {r.name: r for r in before.results}
    after_by_name = {r.name: r for r in after.results}

    comparison = ComparisonReport(
        before_file="before",
        after_file="after",
        threshold_percent=threshold_percent,
    )

    common_names = set(before_by_name.keys()) & set(after_by_name.keys())

    for name in sorted(common_names):
        b = before_by_name[name]
        a = after_by_name[name]

        # Skip if either had an error
        if b.error or a.error:
            continue

        if b.mean_time > 0:
            delta_percent = ((a.mean_time - b.mean_time) / b.mean_time) * 100
        else:
            delta_percent = 0.0 if a.mean_time == 0 else 100.0

        is_regression = delta_percent > threshold_percent
        is_improvement = delta_percent < -threshold_percent

        comp = BenchmarkComparison(
            name=name,
            before_mean=b.mean_time,
            after_mean=a.mean_time,
            delta_percent=delta_percent,
            is_regression=is_regression,
            is_improvement=is_improvement,
            threshold=threshold_percent,
        )

        comparison.comparisons.append(comp)
        if is_regression:
            comparison.regressions.append(comp)
            comparison.has_regressions = True
        if is_improvement:
            comparison.improvements.append(comp)

    return comparison


def format_comparison_text(comparison: ComparisonReport) -> str:
    """
    Format comparison as plain text.

    Args:
        comparison: ComparisonReport to format

    Returns:
        Formatted text string
    """
    lines = [
        "=" * 80,
        "BENCHMARK COMPARISON REPORT",
        "=" * 80,
        "",
        f"Regression threshold: {comparison.threshold_percent}%",
        f"Total benchmarks compared: {len(comparison.comparisons)}",
        f"Regressions: {len(comparison.regressions)}",
        f"Improvements: {len(comparison.improvements)}",
        "",
    ]

    if comparison.has_regressions:
        lines.append("Status: REGRESSIONS DETECTED")
    else:
        lines.append("Status: NO REGRESSIONS")
    lines.append("")

    # All comparisons table
    lines.append("-" * 80)
    lines.append("BENCHMARK RESULTS:")
    lines.append("-" * 80)
    lines.append(f"{'Name':<40} {'Before':>12} {'After':>12} {'Delta':>10}")
    lines.append("-" * 80)

    for comp in sorted(comparison.comparisons, key=lambda x: -x.delta_percent):
        before_ms = comp.before_mean * 1000
        after_ms = comp.after_mean * 1000
        delta_str = f"{comp.delta_percent:+.1f}%"

        # Add markers
        if comp.is_regression:
            marker = " [REGRESSION]"
        elif comp.is_improvement:
            marker = " [improved]"
        else:
            marker = ""

        lines.append(
            f"{comp.name:<40} {before_ms:>10.3f}ms {after_ms:>10.3f}ms {delta_str:>10}{marker}"
        )

    lines.append("")

    # Regressions detail
    if comparison.regressions:
        lines.append("-" * 40)
        lines.append("REGRESSIONS (>10% slower):")
        lines.append("-" * 40)
        for comp in sorted(comparison.regressions, key=lambda x: -x.delta_percent):
            lines.append(
                f"  {comp.name}: {comp.before_mean * 1000:.3f}ms -> "
                f"{comp.after_mean * 1000:.3f}ms ({comp.delta_percent:+.1f}%)"
            )
        lines.append("")

    # Improvements detail
    if comparison.improvements:
        lines.append("-" * 40)
        lines.append("IMPROVEMENTS (>10% faster):")
        lines.append("-" * 40)
        for comp in sorted(comparison.improvements, key=lambda x: x.delta_percent):
            lines.append(
                f"  {comp.name}: {comp.before_mean * 1000:.3f}ms -> "
                f"{comp.after_mean * 1000:.3f}ms ({comp.delta_percent:+.1f}%)"
            )

    return "\n".join(lines)


def format_comparison_markdown(comparison: ComparisonReport) -> str:
    """
    Format comparison as Markdown.

    Args:
        comparison: ComparisonReport to format

    Returns:
        Markdown formatted string
    """
    status = "Regressions Detected" if comparison.has_regressions else "No Regressions"

    lines = [
        "# Benchmark Comparison Report",
        "",
        f"**Status**: {status}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Threshold | {comparison.threshold_percent}% |",
        f"| Benchmarks | {len(comparison.comparisons)} |",
        f"| Regressions | {len(comparison.regressions)} |",
        f"| Improvements | {len(comparison.improvements)} |",
        "",
    ]

    # Results table
    lines.extend(["## All Results", ""])
    lines.append("| Benchmark | Before | After | Delta | Status |")
    lines.append("|-----------|--------|-------|-------|--------|")

    for comp in sorted(comparison.comparisons, key=lambda x: -x.delta_percent):
        status_str = ""
        if comp.is_regression:
            status_str = "REGRESSION"
        elif comp.is_improvement:
            status_str = "improved"

        lines.append(
            f"| `{comp.name}` | {comp.before_mean * 1000:.3f}ms | "
            f"{comp.after_mean * 1000:.3f}ms | {comp.delta_percent:+.1f}% | {status_str} |"
        )
    lines.append("")

    # Regressions
    if comparison.regressions:
        lines.extend(["## Regressions", ""])
        for comp in sorted(comparison.regressions, key=lambda x: -x.delta_percent):
            lines.append(
                f"- **{comp.name}**: {comp.before_mean * 1000:.3f}ms -> "
                f"{comp.after_mean * 1000:.3f}ms ({comp.delta_percent:+.1f}%)"
            )
        lines.append("")

    return "\n".join(lines)


def format_report_text(report: BenchmarkReport) -> str:
    """
    Format benchmark report as plain text.

    Args:
        report: BenchmarkReport to format

    Returns:
        Formatted text string
    """
    lines = [
        "=" * 80,
        "BENCHMARK REPORT",
        "=" * 80,
        "",
        f"Module: {report.module}",
        f"Timestamp: {report.timestamp}",
        f"Python: {report.python_version.split()[0]}",
        f"Total time: {report.total_time:.2f}s",
        f"Benchmarks: {len(report.results)}",
        f"Errors: {report.errors}",
        "",
        "-" * 80,
        "RESULTS:",
        "-" * 80,
        f"{'Name':<40} {'Mean':>12} {'Median':>12} {'StdDev':>12}",
        "-" * 80,
    ]

    for r in sorted(report.results, key=lambda x: -x.mean_time):
        mean_ms = r.mean_time * 1000
        median_ms = r.median_time * 1000
        std_ms = r.std_dev * 1000
        error_marker = " [ERROR]" if r.error else ""
        lines.append(
            f"{r.name:<40} {mean_ms:>10.3f}ms {median_ms:>10.3f}ms "
            f"{std_ms:>10.3f}ms{error_marker}"
        )

    return "\n".join(lines)


def create_sample_benchmarks(output_path: Path) -> None:
    """
    Create a sample benchmarks module.

    Args:
        output_path: Path to write the sample module
    """
    content = '''"""Sample benchmark module."""

import time


def benchmark_list_comprehension():
    """Benchmark list comprehension."""
    result = [i * 2 for i in range(1000)]
    return result


def benchmark_map_function():
    """Benchmark map function."""
    result = list(map(lambda x: x * 2, range(1000)))
    return result


def benchmark_for_loop():
    """Benchmark for loop."""
    result = []
    for i in range(1000):
        result.append(i * 2)
    return result


def benchmark_dict_comprehension():
    """Benchmark dict comprehension."""
    result = {i: i * 2 for i in range(100)}
    return result


def benchmark_string_join():
    """Benchmark string join."""
    result = "".join(str(i) for i in range(100))
    return result


def benchmark_string_concat():
    """Benchmark string concatenation."""
    result = ""
    for i in range(100):
        result += str(i)
    return result
'''
    output_path.write_text(content, encoding="utf-8")
    print(f"Sample benchmarks written to {output_path}")


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 if no regressions, 1 if regressions found)
    """
    parser = argparse.ArgumentParser(
        description="Performance regression detection through benchmarking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s run --module mypackage.benchmarks --output baseline.json
    %(prog)s compare baseline.json current.json
    %(prog)s run --module mypackage.benchmarks --compare baseline.json
    %(prog)s create-sample benchmarks.py
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run benchmarks")
    run_parser.add_argument(
        "--module", "-m", required=True, help="Module path containing benchmarks"
    )
    run_parser.add_argument("-o", "--output", type=Path, help="Output JSON file")
    run_parser.add_argument(
        "--iterations", "-n", type=int, default=100, help="Iterations per benchmark"
    )
    run_parser.add_argument(
        "--warmup", "-w", type=int, default=10, help="Warmup iterations"
    )
    run_parser.add_argument("--pattern", "-p", help="Filter benchmarks by pattern")
    run_parser.add_argument(
        "--compare", "-c", type=Path, help="Compare against baseline JSON"
    )
    run_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=10.0,
        help="Regression threshold percent (default: 10)",
    )
    run_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format",
    )

    # Compare subcommand
    compare_parser = subparsers.add_parser(
        "compare", help="Compare two benchmark reports"
    )
    compare_parser.add_argument("before", type=Path, help="Baseline benchmark JSON")
    compare_parser.add_argument("after", type=Path, help="Current benchmark JSON")
    compare_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=10.0,
        help="Regression threshold percent (default: 10)",
    )
    compare_parser.add_argument("-o", "--output", type=Path, help="Output JSON file")
    compare_parser.add_argument(
        "-f",
        "--format",
        choices=["json", "text", "markdown"],
        default="text",
        help="Output format",
    )

    # Create sample subcommand
    sample_parser = subparsers.add_parser(
        "create-sample", help="Create sample benchmark module"
    )
    sample_parser.add_argument("output", type=Path, help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "create-sample":
        create_sample_benchmarks(args.output)
        return 0

    if args.command == "run":
        # Add module path to sys.path if needed
        module_parts = args.module.split(".")
        if len(module_parts) > 1:
            package_path = Path.cwd() / module_parts[0]
            if package_path.exists():
                sys.path.insert(0, str(Path.cwd()))

        report = run_benchmarks(
            args.module,
            iterations=args.iterations,
            warmup=args.warmup,
            pattern=args.pattern,
        )

        if args.output:
            args.output.write_text(
                json.dumps(report.to_dict(), indent=2), encoding="utf-8"
            )
            print(f"Report written to {args.output}")

        if args.format == "json":
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(format_report_text(report))

        # Compare if baseline provided
        if args.compare:
            if not args.compare.exists():
                print(f"Baseline not found: {args.compare}", file=sys.stderr)
                return 1

            try:
                baseline = json.loads(args.compare.read_text(encoding="utf-8"))
                baseline_report = BenchmarkReport(
                    timestamp=baseline.get("timestamp", ""),
                    module=baseline.get("module", ""),
                    python_version=baseline.get("python_version", ""),
                    results=[BenchmarkResult(**r) for r in baseline.get("results", [])],
                )
            except (json.JSONDecodeError, TypeError) as e:
                print(f"Error loading baseline: {e}", file=sys.stderr)
                return 1

            comparison = compare_reports(baseline_report, report, args.threshold)

            print("\n" + "=" * 80)
            print("COMPARISON WITH BASELINE")
            print("=" * 80 + "\n")

            if args.format == "markdown":
                print(format_comparison_markdown(comparison))
            else:
                print(format_comparison_text(comparison))

            if comparison.has_regressions:
                return 1

        return 0

    if args.command == "compare":
        for path in [args.before, args.after]:
            if not path.exists():
                print(f"File not found: {path}", file=sys.stderr)
                return 2

        try:
            before_data = json.loads(args.before.read_text(encoding="utf-8"))
            after_data = json.loads(args.after.read_text(encoding="utf-8"))

            before = BenchmarkReport(
                timestamp=before_data.get("timestamp", ""),
                module=before_data.get("module", ""),
                python_version=before_data.get("python_version", ""),
                results=[BenchmarkResult(**r) for r in before_data.get("results", [])],
            )
            after = BenchmarkReport(
                timestamp=after_data.get("timestamp", ""),
                module=after_data.get("module", ""),
                python_version=after_data.get("python_version", ""),
                results=[BenchmarkResult(**r) for r in after_data.get("results", [])],
            )
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error loading reports: {e}", file=sys.stderr)
            return 2

        comparison = compare_reports(before, after, args.threshold)
        comparison.before_file = str(args.before)
        comparison.after_file = str(args.after)

        if args.output:
            args.output.write_text(
                json.dumps(comparison.to_dict(), indent=2), encoding="utf-8"
            )
            print(f"Comparison written to {args.output}")

        if args.format == "json":
            print(json.dumps(comparison.to_dict(), indent=2))
        elif args.format == "markdown":
            print(format_comparison_markdown(comparison))
        else:
            print(format_comparison_text(comparison))

        if comparison.has_regressions:
            print(
                f"\nFailed: {len(comparison.regressions)} regression(s) detected",
                file=sys.stderr,
            )
            return 1

        print("\nNo performance regressions detected.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
