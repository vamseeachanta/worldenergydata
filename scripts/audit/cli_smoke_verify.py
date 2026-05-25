#!/usr/bin/env python3
"""Run bounded-safe worldenergydata CLI smoke checks.

The harness intentionally excludes data refreshes, scrapers, credentialed
commands, and server-starting commands. It records enough output to classify
public examples without requiring BSEE binary data or network access.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Sequence


DEFAULT_TIMEOUT_S = 30
SNIPPET_CHARS = 500
REPORT_DIR = Path("docs/reports")


@dataclass(frozen=True)
class SmokeCase:
    command: tuple[str, ...]
    safety: str
    source: str = ""


@dataclass(frozen=True)
class SmokeResult:
    command: str
    safety: str
    exit_code: int
    status: str
    stdout_snippet: str
    stderr_snippet: str
    source: str = ""


Runner = Callable[
    [Sequence[str]],
    subprocess.CompletedProcess[str],
]


def build_smoke_cases(cli: str = "worldenergydata") -> list[SmokeCase]:
    """Return the bounded-safe smoke command matrix for issue #352."""
    subapps = (
        "bsee",
        "dashboard",
        "eia",
        "marine-safety",
        "fdas",
        "lower-tertiary",
        "forecast",
        "sodir",
        "metocean",
        "ndbc",
        "texas-rrc",
        "canada",
        "mexico-cnh",
        "landman",
        "lng-terminals",
        "safety-analysis",
    )

    cases = [
        SmokeCase((cli, "--help"), "bounded-safe", "README.md"),
        SmokeCase((cli, "version"), "bounded-safe", "README.md"),
        SmokeCase((cli, "info"), "bounded-safe", "README.md"),
        SmokeCase((cli, "status"), "bounded-safe", "docs/CLI.md"),
    ]
    cases.extend(
        SmokeCase((cli, subapp, "--help"), "bounded-safe", "docs/CLI.md")
        for subapp in subapps
    )
    cases.extend(
        [
            SmokeCase(
                (
                    cli,
                    "fdas",
                    "calculate-npv",
                    "--cashflows",
                    "[-1000,100,200,300]",
                    "--discount-rate",
                    "0.10",
                ),
                "fixture-only",
                "README.md",
            ),
            SmokeCase(
                (
                    cli,
                    "fdas",
                    "calculate-all",
                    "--cashflows",
                    "[-5000,1000,1500,2000]",
                ),
                "fixture-only",
                "README.md",
            ),
            SmokeCase(
                (cli, "fdas", "classify", "5000"),
                "fixture-only",
                "README.md",
            ),
            SmokeCase(
                (
                    cli,
                    "marine-safety",
                    "db",
                    "init",
                    "--dev-mode",
                    "--dry-run",
                ),
                "bounded-safe",
                "docs/CLI.md",
            ),
        ]
    )
    return cases


def _default_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(Path("src").resolve())
    assetutilities_path = str(Path("../assetutilities/src").resolve())
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (src_path, assetutilities_path, env.get("PYTHONPATH", "")) if p
    )
    return env


def _default_runner(
    command: Sequence[str],
    *,
    timeout: int,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env=env,
    )


def _snippet(text: str) -> str:
    text = text.strip()
    if len(text) <= SNIPPET_CHARS:
        return text
    return text[:SNIPPET_CHARS] + "..."


def _result_from_process(
    case: SmokeCase,
    completed: subprocess.CompletedProcess[str],
) -> SmokeResult:
    status = "pass" if completed.returncode == 0 else "fail"
    return SmokeResult(
        command=" ".join(case.command),
        safety=case.safety,
        exit_code=completed.returncode,
        status=status,
        stdout_snippet=_snippet(completed.stdout),
        stderr_snippet=_snippet(completed.stderr),
        source=case.source,
    )


def _result_from_timeout(
    case: SmokeCase, exc: subprocess.TimeoutExpired
) -> SmokeResult:
    stdout = exc.stdout if isinstance(exc.stdout, str) else ""
    stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    return SmokeResult(
        command=" ".join(case.command),
        safety=case.safety,
        exit_code=124,
        status="timeout",
        stdout_snippet=_snippet(stdout),
        stderr_snippet=_snippet(stderr),
        source=case.source,
    )


def write_markdown_report(results: Sequence[SmokeResult], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# worldenergydata CLI Smoke Verification",
        "",
        f"- Date: {date.today().isoformat()}",
        "- Issue: #352",
        "- Scope: bounded-safe and fixture-only commands only",
        "- Excluded: network scrapes, refresh/download commands, credentialed commands, and server starts",
        "",
        "| Command | Safety | Exit | Status |",
        "|---|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            f"| `{result.command}` | {result.safety} | {result.exit_code} | {result.status} |"
        )

    failures = [r for r in results if r.status != "pass"]
    if failures:
        lines.extend(["", "## Failure Details", ""])
        for result in failures:
            lines.extend(
                [
                    f"### `{result.command}`",
                    "",
                    f"- status: {result.status}",
                    f"- exit_code: {result.exit_code}",
                    "",
                    "stdout:",
                    "",
                    "```text",
                    result.stdout_snippet,
                    "```",
                    "",
                    "stderr:",
                    "",
                    "```text",
                    result.stderr_snippet,
                    "```",
                    "",
                ]
            )

    report_path.write_text("\n".join(lines) + "\n")


def write_json_report(results: Sequence[SmokeResult], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date.today().isoformat(),
        "issue": 352,
        "results": [asdict(result) for result in results],
    }
    report_path.write_text(json.dumps(payload, indent=2) + "\n")


def run_smoke_cases(
    cases: Sequence[SmokeCase] | None = None,
    *,
    runner=_default_runner,
    report_path: Path | None = None,
    json_path: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT_S,
    env: dict[str, str] | None = None,
) -> list[SmokeResult]:
    """Run smoke cases and write reports."""
    cases = list(cases or build_smoke_cases())
    env = env or _default_env()
    results: list[SmokeResult] = []
    for case in cases:
        try:
            completed = runner(case.command, timeout=timeout, env=env)
        except subprocess.TimeoutExpired as exc:
            results.append(_result_from_timeout(case, exc))
        else:
            results.append(_result_from_process(case, completed))

    if report_path is None:
        report_path = REPORT_DIR / f"cli-smoke-report-{date.today().isoformat()}.md"
    write_markdown_report(results, report_path)

    if json_path is None:
        json_path = report_path.with_suffix(".json")
    write_json_report(results, json_path)

    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bounded-safe worldenergydata CLI smoke checks.",
    )
    parser.add_argument(
        "--cli",
        default="worldenergydata",
        help="CLI executable to invoke (default: worldenergydata).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        help=f"Timeout per command in seconds (default: {DEFAULT_TIMEOUT_S}).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Markdown report path.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="JSON report path.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    results = run_smoke_cases(
        build_smoke_cases(cli=args.cli),
        report_path=args.report,
        json_path=args.json,
        timeout=args.timeout,
    )
    failures = [result for result in results if result.status != "pass"]
    print(f"Wrote CLI smoke report for {len(results)} commands")
    if failures:
        print(f"{len(failures)} command(s) failed or timed out")
        return 1
    print("All CLI smoke commands passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
