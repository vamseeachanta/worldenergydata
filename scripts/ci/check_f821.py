#!/usr/bin/env python3
"""Repeat complete F821 inventories without hiding failed tool invocations.

Protocol sources (accessed 2026-10-20):
* https://flake8.pycqa.org/en/latest/user/options.html (format, isolated, jobs)
* https://docs.astral.sh/ruff/configuration/ (isolated, JSON)
* https://docs.astral.sh/ruff/linter/#exit-codes (exit statuses)
* https://docs.astral.sh/uv/reference/cli/ (run --no-project, --no-sync, --python)
See docs/ci/f821-scans.md for the protocol, worked example and limitations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def digest(value: object) -> str:
    """Hash canonical JSON so output order does not affect inventory identity."""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot(paths: list[Path], root: Path) -> dict[str, str]:
    """Enumerate Python inputs once, without linter-specific discovery filters."""
    inventory = {}
    for path in paths:
        if not path.exists():
            raise ValueError("scan target does not exist")
        candidates = path.rglob("*.py") if path.is_dir() else [path]
        for candidate in candidates:
            if candidate.suffix != ".py" or not candidate.is_file():
                continue
            relative = candidate.resolve().relative_to(root).as_posix()
            inventory[relative] = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if not inventory:
        raise ValueError("scan has no Python files")
    return dict(sorted(inventory.items()))


def capture(command: list[str], timeout: float, prefix: Path, root: Path) -> dict:
    """Retain both streams even when a command cannot finish or cannot start."""
    result = {"command": command, "returncode": None, "error": None}
    stdout = stderr = ""
    try:
        process = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env={**os.environ, "RUFF_NUM_THREADS": "1"},
        )
        stdout, stderr = process.stdout, process.stderr
        result["returncode"] = process.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or "", exc.stderr or ""
        result["error"] = "command timed out"
    except OSError as exc:
        result["error"] = f"command could not start: {exc}"
    for suffix, content in (("stdout", stdout), ("stderr", stderr)):
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        prefix.with_suffix(f".{suffix}").write_text(content, encoding="utf-8")
    return result


def require_unchanged(paths: list[Path], root: Path, files: dict[str, str]) -> None:
    """A removed or unreadable file also invalidates the original inventory."""
    try:
        unchanged = snapshot(paths, root) == files
    except (OSError, ValueError) as exc:
        raise ValueError("source inventory changed or became unreadable") from exc
    if not unchanged:
        raise ValueError("source inventory changed")


def parse_findings(
    tool: str, text: str, root: Path, canary: Path, files: dict[str, str]
) -> list[dict]:
    """Reject malformed, unexpected, duplicate or non-F821 diagnostics."""
    records = []
    if tool == "flake8":
        for line in text.splitlines():
            match = re.fullmatch(r"(.*):(\d+):(\d+):([^:]+):(.*)", line)
            if match is None:
                raise ValueError("unrecognized flake8 output")
            path, row, column, code, message = match.groups()
            records.append((path, int(row), int(column), code, message.strip()))
    else:
        try:
            entries = json.loads(text)
            if not isinstance(entries, list):
                raise TypeError("Ruff output is not an array")
            for entry in entries:
                records.append(
                    (
                        entry["filename"],
                        entry["location"]["row"],
                        entry["location"]["column"],
                        entry["code"],
                        entry["message"],
                    )
                )
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("unrecognized Ruff output") from exc

    findings = []
    canary_count = 0
    for filename, row, column, code, message in records:
        if code != "F821":
            raise ValueError("non-F821 diagnostic: scan could be incomplete")
        if (
            type(row) is not int
            or type(column) is not int
            or row < 1
            or column < 1
            or not isinstance(message, str)
            or not isinstance(filename, str)
        ):
            raise ValueError("invalid diagnostic fields")
        path = (root / filename).resolve()
        if path == canary:
            if (row, column) != (1, 1) or "scan_canary_missing" not in message:
                raise ValueError("invalid canary diagnostic")
            canary_count += 1
            continue
        name = path.relative_to(root).as_posix()
        if name not in files:
            raise ValueError("finding outside the requested inventory")
        findings.append(
            {
                "path": name,
                "row": row,
                "column": column,
                "code": code,
                "message": message,
            }
        )
    # The fixture contains exactly one undefined expression; see the worked example.
    if canary_count != 1:
        raise ValueError("missing or duplicate canary diagnostic")
    findings.sort(key=lambda item: json.dumps(item, sort_keys=True))
    if len({json.dumps(item, sort_keys=True) for item in findings}) != len(findings):
        raise ValueError("duplicate findings")
    return findings


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("paths", nargs="+", type=Path)
    result.add_argument("--tool", choices=("flake8", "ruff"), default="flake8")
    result.add_argument("--launcher", choices=("direct", "uv"), default="direct")
    result.add_argument("--uv", default="uv", help="uv executable for the uv launcher")
    # Five observations: docs/plans/2026-05-04-issue-328-flake8-race.md, acceptance.
    result.add_argument("--runs", type=int, default=5)
    result.add_argument(
        "--timeout", type=float, required=True, help="seconds per command"
    )
    result.add_argument(
        "--output", type=Path, required=True, help="new evidence directory"
    )
    result.add_argument(
        "--allow-findings", action="store_true", help="inventory mode only"
    )
    return result


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_intermixed_args(argv)
    if args.runs < 2 or not 0 < args.timeout < float("inf"):
        cli.error("provide at least two runs and a finite positive timeout")
    root = Path.cwd().resolve()
    paths = [(root / path).resolve() for path in args.paths]
    output = args.output.resolve()
    if any(path.is_dir() and output.is_relative_to(path) for path in paths):
        cli.error("evidence directory must be outside scan targets")
    if output.exists():
        cli.error("evidence directory already exists; use a new directory")
    output.mkdir(parents=True)
    report = {
        "status": "ERROR",
        "tool": args.tool,
        "launcher": args.launcher,
        "runs": [],
    }
    try:
        files = snapshot(paths, root)
        report.update(files=files, source_sha256=digest(files), python=sys.version)
        canary = output / "scan_canary.py"
        canary.write_text("scan_canary_missing\n", encoding="utf-8")
        command = [sys.executable, "-m", args.tool]
        if args.launcher == "uv":
            # Pin the same interpreter and prevent project resolution/environment writes.
            command = [
                args.uv,
                "run",
                "--no-project",
                "--no-sync",
                "--python",
                sys.executable,
                "python",
                "-m",
                args.tool,
            ]
        version = capture(
            command + ["--version"], args.timeout, output / "version", root
        )
        report["version"] = version
        if version["error"] or version["returncode"] != 0:
            raise ValueError("tool version command failed")
        if args.tool == "flake8":
            options = [
                "--isolated",
                "--jobs=1",
                "--select=F821,E9",
                "--exclude=",
                "--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s",
            ]
        else:
            options = [
                "check",
                "--isolated",
                "--no-cache",
                "--no-respect-gitignore",
                "--no-force-exclude",
                "--select=F821",
                "--output-format=json",
            ]
        command += options + ["--", *files, str(canary)]
        for number in range(1, args.runs + 1):
            require_unchanged(paths, root, files)
            prefix = output / f"run-{number}"
            run = capture(command, args.timeout, prefix, root)
            report["runs"].append(run)
            if run["error"]:
                raise ValueError(run["error"])
            # Both tools must return 1 because the required canary is an F821.
            # Ruff exit conventions: linter docs, "Exit codes" (accessed 2026).
            if run["returncode"] != 1:
                raise ValueError("unexpected tool exit status")
            findings = parse_findings(
                args.tool,
                prefix.with_suffix(".stdout").read_text(encoding="utf-8"),
                root,
                canary,
                files,
            )
            run.update(
                count=len(findings), findings=findings, findings_sha256=digest(findings)
            )
            require_unchanged(paths, root, files)
            # Write progress after each completed observation; never overwrite old evidence.
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        stable = len({run["findings_sha256"] for run in report["runs"]}) == 1
        report["status"] = "STABLE" if stable else "UNSTABLE"
    except (OSError, ValueError) as exc:
        report.update(status="ERROR", error=str(exc))
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "counts": [r.get("count") for r in report["runs"]],
            }
        )
    )
    # Checker contract: 0 = clean/stable, 1 = stable findings, 2 = invalid evidence.
    # Inventory mode changes only the stable-findings result, never an error.
    if report["status"] != "STABLE":
        return 2
    return int(bool(report["runs"][0]["count"]) and not args.allow_findings)


if __name__ == "__main__":
    raise SystemExit(main())
