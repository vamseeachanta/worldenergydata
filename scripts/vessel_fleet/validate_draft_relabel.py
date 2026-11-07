#!/usr/bin/env python3
"""Check that draft relabelling preserves all original extracted YAML values."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

import yaml


def validate_relabel(before: dict, after: dict) -> int:
    """Permit only additive load-line keys matching the original legacy value.

    Equal parsed documents, including formatting-only changes, return zero.
    A different original value, removed field or changed metadata is rejected.
    """
    normalized = deepcopy(after)
    additions = 0
    for name, entry in normalized.get("vessels", {}).items():
        specs = entry.get("specs", {})
        original = before.get("vessels", {}).get(name, {}).get("specs", {})
        field = "RAW_DRAFT_LOAD_LINE_FT"
        if field in specs and field not in original:
            legacy = original.get("RAW_DRAFT_OPERATING_FT")
            if legacy is None or specs[field] != legacy:
                raise ValueError("Load-line draft differs from the original raw draft")
            del specs[field]
            additions += 1
    if before != normalized:
        raise ValueError("Original extracted values or metadata changed")
    return additions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--formatting-only", action="store_true")
    args = parser.parse_args()
    before = yaml.safe_load(args.before.read_text(encoding="utf-8"))
    after = yaml.safe_load(args.after.read_text(encoding="utf-8"))
    try:
        additions = validate_relabel(before, after)
        if args.formatting_only and additions:
            raise ValueError("Formatting-only check found added data fields")
    except ValueError as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print(f"PASS: {additions} load-line keys added; all original values preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
