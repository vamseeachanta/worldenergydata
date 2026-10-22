"""Opt-in HSE report review using the union of two explicit policy sources.

Issue 420 defines the matching policy; no engineering acceptance is inferred.
Only relative report locations and severity are emitted, never matched text.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys throughout the policy, including merged mappings."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError("duplicate policy key")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_rules(path):
    """Read workspace-compatible literal entries and explicit regex extensions."""
    loader = UniqueKeyLoader(path.read_text(encoding="utf-8"))
    try:
        policy = loader.get_single_data()
    finally:
        loader.dispose()
    if not isinstance(policy, dict):
        raise TypeError("policy must be a mapping")
    default = policy.get("default_severity", "block")
    if default not in ("block", "warn"):
        raise ValueError("invalid default severity")
    rules = []
    sections = 0
    metadata = {"version", "updated", "sources", "exclusions", "default_severity"}
    for key, entries in policy.items():
        if key in metadata:
            continue
        sections += 1
        if not isinstance(entries, list):
            raise TypeError("rule section must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise TypeError("rule must be a mapping")
            pattern = entry.get("pattern")
            severity = entry.get("severity", default)
            sensitive = entry.get("case_sensitive", False)
            regex = entry.get("regex", False)
            if not isinstance(pattern, str) or not pattern.strip():
                raise ValueError("pattern must be nonempty text")
            if severity not in ("block", "warn"):
                raise ValueError("invalid severity")
            if type(sensitive) is not bool or type(regex) is not bool:
                raise ValueError("matching flags must be Boolean")
            expression = pattern if regex else re.escape(pattern)
            expression = r"(?<!\w)(?:" + expression + r")(?!\w)"
            rules.append(
                (re.compile(expression, 0 if sensitive else re.IGNORECASE), severity)
            )
    if not sections:
        raise ValueError("policy has no rule sections")
    return rules


def scan_reports(reports, rules):
    """Scan every UTF-8 report file; missing, binary or linked inputs are errors."""
    if reports.is_symlink() or not reports.is_dir():
        raise ValueError("report directory missing or linked")
    files = []
    for path in sorted(reports.rglob("*")):
        if path.is_symlink():
            raise ValueError("linked report input")
        if path.is_file():
            files.append(path)
    if not files:
        raise ValueError("report directory is empty")
    blocked = False
    for path in files:
        text = path.read_text(encoding="utf-8")
        if "\x00" in text:
            raise ValueError("binary report input")
        findings = {}
        for pattern, severity in rules:
            for match in pattern.finditer(text):
                number = text.count("\n", 0, match.start()) + 1
                findings.setdefault(number, set()).add(severity)
        for number, severities in sorted(findings.items()):
            severity = "block" if "block" in severities else "warn"
            print(f"{severity.upper()} {path.relative_to(reports).as_posix()}:{number}")
            blocked |= severity == "block"
    print(
        f"Scanned {len(files)} report files; {'BLOCK' if blocked else 'no blocking matches'}"
    )
    return int(blocked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=ROOT / "reports/hse")
    parser.add_argument("--workspace-denylist", type=Path, required=True)
    parser.add_argument(
        "--operator-denylist",
        type=Path,
        default=ROOT / "data/modules/bsee/operator-aggregation-denylist.yaml",
    )
    args = parser.parse_args()
    try:
        rules = load_rules(args.workspace_denylist) + load_rules(args.operator_denylist)
        return scan_reports(args.reports, rules)
    except (OSError, UnicodeError, TypeError, ValueError, yaml.YAMLError, re.error):
        # Exception strings can contain restricted patterns or absolute paths.
        print(
            "ERROR: invalid or unreadable policy/report input; review inputs locally",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
