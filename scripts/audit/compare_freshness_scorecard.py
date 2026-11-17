#!/usr/bin/env python3
"""Compare saved and candidate scorecards without writing either one.

Paths are JSON pointers relative to the scorecard. Exit 0 permits fixture and
generation metadata differences; exit 1 requires review of legacy values or
module membership; exit 2 indicates invalid input. Arrays compare as whole values.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from data_freshness_scorecard import build_scorecard

_MISSING = object()


def _validate_scorecard(value: Any) -> None:
    if not isinstance(value, dict) or not isinstance(value.get("modules"), dict):
        raise ValueError("scorecard must contain a modules mapping")
    if any(
        not isinstance(key, str) or not isinstance(row, dict)
        for key, row in value["modules"].items()
    ):
        raise ValueError("modules must map names to objects")
    json.dumps(value, allow_nan=False)


def compare_scorecards(
    before: dict[str, Any], after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return sorted differences, preserving absent values separately from null."""
    _validate_scorecard(before)
    _validate_scorecard(after)
    differences: list[dict[str, Any]] = []

    def visit(old: Any, new: Any, parts: tuple[str, ...]) -> None:
        membership = len(parts) == 2 and parts[0] == "modules"
        absent = old is _MISSING or new is _MISSING
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(old.keys() | new.keys()):
                visit(old.get(key, _MISSING), new.get(key, _MISSING), (*parts, key))
            return
        if not absent and json.dumps(old, sort_keys=True) == json.dumps(
            new, sort_keys=True
        ):
            return
        if membership and absent:
            category = "module_membership"
        elif (
            len(parts) == 3
            and parts[0] == "modules"
            and parts[2] == "fixture_readiness"
        ):
            category = "fixture_readiness"
        elif parts in {("generated_at",), ("report_date",)}:
            category = "generation_metadata"
        else:
            category = "legacy_value"
        differences.append(
            {
                "path": "/"
                + "/".join(p.replace("~", "~0").replace("/", "~1") for p in parts),
                "category": category,
                "before_present": old is not _MISSING,
                "after_present": new is not _MISSING,
                "before": None if old is _MISSING else old,
                "after": None if new is _MISSING else new,
            }
        )

    visit(before, after, ())
    return sorted(differences, key=lambda entry: entry["path"])


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def _read_input(root: Path, relative: str, *, as_json: bool = False) -> Any:
    """Read required files with diagnostics that never echo paths or contents."""
    try:
        text = (root / relative).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError(f"{relative}: missing input") from None
    except (OSError, UnicodeError):
        raise ValueError(f"{relative}: unreadable input") from None
    try:
        if as_json:
            value = json.loads(
                text, object_pairs_hook=_unique_object, parse_constant=_reject_constant
            )
            _validate_scorecard(value)
        else:
            value = yaml.safe_load(text)
            if not isinstance(value, dict):
                raise ValueError("expected mapping")
            modules = value.get("modules")
            if relative == "module-manifest.yaml":
                if not isinstance(modules, list) or any(
                    not isinstance(row, dict) or not isinstance(row.get("id"), str)
                    for row in modules
                ):
                    raise ValueError("expected module declarations")
            elif not isinstance(modules, dict):
                raise ValueError("expected module mapping")
        return value
    except (ValueError, TypeError, RecursionError, yaml.YAMLError):
        raise ValueError(f"{relative}: invalid input") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--date", required=True, help="Report date as YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        if date.fromisoformat(args.date).isoformat() != args.date:
            raise ValueError
    except ValueError:
        print("--date: invalid report date", file=sys.stderr)
        return 2
    try:
        root = args.project_root.resolve()
        saved = _read_input(root, "data/freshness-scorecard.json", as_json=True)
        _read_input(root, "module-manifest.yaml")
        _read_input(root, "data/catalog.yaml")
    except (ValueError, OSError) as error:
        # Only the fixed relative diagnostics from _read_input are exposed.
        message = (
            str(error)
            if isinstance(error, ValueError)
            else "candidate inputs: unreadable root"
        )
        print(message, file=sys.stderr)
        return 2
    try:
        candidate = build_scorecard(root, report_date=args.date)
        differences = compare_scorecards(saved, candidate)
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OverflowError,
        RecursionError,
        yaml.YAMLError,
    ):
        print("candidate inputs: invalid local data", file=sys.stderr)
        return 2
    print(json.dumps(differences, indent=2, sort_keys=True, allow_nan=False))
    return int(
        any(d["category"] in {"legacy_value", "module_membership"} for d in differences)
    )


if __name__ == "__main__":
    raise SystemExit(main())
