#!/usr/bin/env python3
"""Validate normalized read-only scan evidence; never infer parity from counts.

See docs/development/ruff-migration-evaluation.md for the input contract.
This summarizes evidence, rather than launching tools or trusting console totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from statistics import median

TOOLS = ("flake8", "black", "isort", "ruff-check", "ruff-format")


def digest(value: object) -> str:
    """Use the canonical source-map digest protocol of check_f821.snapshot."""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject repeated JSON keys before decoding can discard evidence."""
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def valid_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not PurePosixPath(value).is_absolute()
        and all(part not in ("", ".", "..") for part in value.split("/"))
        and not any(char in value for char in "\\:\n\r\x00")
    )


def validated_findings(tool: str, value: object, files: dict) -> list[dict]:
    require(isinstance(value, list), "findings must be a list")
    formatter_paths = set()
    for item in value:
        require(isinstance(item, dict), "invalid diagnostic")
        require(
            set(item) == {"path", "row", "column", "code", "message"},
            "invalid diagnostic fields",
        )
        require(item["path"] in files, "finding outside inventory")
        require(
            all(type(item[key]) is int and item[key] > 0 for key in ("row", "column")),
            "invalid diagnostic location",
        )
        require(isinstance(item["message"], str), "invalid diagnostic message")
        code = item["code"]
        require(isinstance(code, str), "invalid rule code")
        if tool in ("black", "isort", "ruff-format"):
            require(code == "FORMAT", "invalid formatter diagnostic")
            require(item["row"] == item["column"] == 1, "invalid formatter location")
            require(item["path"] not in formatter_paths, "duplicate formatter path")
            formatter_paths.add(item["path"])
        else:
            require(
                bool(re.fullmatch(r"[EWF]\d{3}", code))
                or (tool == "ruff-check" and code == "I001"),
                "unexpected rule",
            )
            require(code not in ("E901", "E902", "E999"), "source parse failure")
    keys = [json.dumps(item, sort_keys=True) for item in value]
    require(len(set(keys)) == len(keys), "duplicate diagnostic")
    return sorted(value, key=lambda item: json.dumps(item, sort_keys=True))


def summarize(evidence: dict) -> dict:
    """Require five stable, complete observations of every tool on identical files."""
    try:
        return _summarize(evidence)
    except (KeyError, TypeError) as exc:
        raise ValueError("invalid evidence structure") from exc
    except OverflowError as exc:
        raise ValueError("invalid duration in seconds") from exc


def _summarize(evidence: dict) -> dict:
    require(isinstance(evidence, dict), "evidence must be an object")
    files = evidence["files"]
    require(isinstance(files, dict) and bool(files), "missing source inventory")
    require(
        all(
            valid_path(path)
            and path.endswith(".py")
            and isinstance(sha, str)
            and re.fullmatch(r"[a-f0-9]{64}", sha)
            for path, sha in files.items()
        ),
        "invalid source inventory",
    )
    unsupported = evidence["unsupported_rules"]
    require(
        isinstance(unsupported, list)
        and all(isinstance(code, str) for code in unsupported),
        "invalid unsupported rules",
    )
    require(set(evidence["tools"]) == set(TOOLS), "missing or unexpected tools")
    source = digest(files)
    tools = {}
    for name in TOOLS:
        tool = evidence["tools"][name]
        require(
            isinstance(tool["version"], str) and bool(tool["version"].strip()),
            "missing tool version",
        )
        require(tool["files"] == files, "tool inventory differs")
        runs = tool["runs"]
        require(isinstance(runs, list) and len(runs) == 5, "five runs required")
        observations, durations = [], []
        for run in runs:
            require(run["error"] is None, "scanner error")
            require(run["before"] == run["after"] == source, "source digest changed")
            require(run["probe"] is True, "positive probe failed")
            seconds = run["seconds"]
            require(
                type(seconds) in (int, float)
                and math.isfinite(seconds)
                and seconds > 0,
                "invalid duration in seconds",
            )
            findings = validated_findings(name, run["findings"], files)
            require(
                type(run["returncode"]) is int
                and run["returncode"] == int(bool(findings)),
                "scanner exit disagrees with findings",
            )
            observations.append(findings)
            durations.append(seconds)
        require(
            all(items == observations[0] for items in observations), "unstable scans"
        )
        tools[name] = {
            "version": tool["version"],
            "file_count": len(files),
            "source_sha256": source,
            "seconds": durations,
            "median_seconds": median(durations),
            "maximum_seconds": max(durations),
            "findings": observations[0],
            "rules": dict(sorted(Counter(i["code"] for i in observations[0]).items())),
        }

    def difference(legacy: set, candidate: set) -> dict:
        return {
            "legacy_only": sorted(legacy - candidate),
            "candidate_only": sorted(candidate - legacy),
        }

    lint_sets = []
    for name in ("flake8", "ruff-check"):
        lint_sets.append(
            {
                json.dumps(item, sort_keys=True)
                for item in tools[name]["findings"]
                if item["code"] != "I001"
            }
        )
    lint_delta = {
        key: [json.loads(item) for item in values]
        for key, values in difference(*lint_sets).items()
    }
    import_delta = difference(
        {item["path"] for item in tools["isort"]["findings"]},
        {i["path"] for i in tools["ruff-check"]["findings"] if i["code"] == "I001"},
    )
    format_delta = difference(
        {item["path"] for item in tools["black"]["findings"]},
        {item["path"] for item in tools["ruff-format"]["findings"]},
    )
    different = any(
        any(delta.values()) for delta in (lint_delta, import_delta, format_delta)
    )
    dirty_format = any(
        tools[name]["findings"] for name in ("black", "isort", "ruff-format")
    )
    combined = [
        a + b
        for a, b in zip(tools["ruff-check"]["seconds"], tools["ruff-format"]["seconds"])
    ]
    require(all(math.isfinite(value) for value in combined), "invalid combined timing")
    if unsupported:
        parity = "BLOCKED"
    elif different:
        parity = "DIFFERENT"
    elif dirty_format:
        parity = "UNVERIFIED"
    else:
        parity = "MATCH"
    return {
        "status": "VALID",
        "files": files,
        "source_sha256": source,
        "tools": tools,
        "unsupported_rules": unsupported,
        "parity": parity,
        "lint_delta": lint_delta,
        "import_delta": import_delta,
        "format_delta": format_delta,
        "timing": {
            "combined_seconds": combined,
            "median_seconds": median(combined),
            "maximum_seconds": max(combined),
            "under_30_seconds": max(combined) < 30,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        same_file = args.evidence.resolve() == args.output.resolve() or (
            args.evidence.exists()
            and args.output.exists()
            and args.evidence.samefile(args.output)
        )
    except (OSError, RuntimeError):
        parser.error("cannot verify evidence and output paths")
    if same_file:
        parser.error("output must not overwrite evidence")
    try:
        result = summarize(
            json.loads(
                args.evidence.read_text(encoding="utf-8"),
                object_pairs_hook=unique_object,
            )
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {
            "status": "ERROR",
            "error": type(exc).__name__,
            "parity": "UNVERIFIED",
            "timing": None,
        }
    args.output.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return 0 if result["status"] == "VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
