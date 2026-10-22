#!/usr/bin/env python3
"""Read effective branch rules and audit the knowledge-pack requirement.

No settings are changed. Offline input must use the branch-rules API response
shape, not a ruleset import file: disabled/evaluate rulesets are not effective.
Source: GitHub REST API 2022-11-28, "Get rules for a branch":
https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import quote

# Required display name: issue #1353 and the PR Validation workflow.
REQUIRED_CHECK = "Lint Changed Knowledge Packs"
# CLI result contract: README.md, "CI guards" (conventional success/failure,
# with a separate result for unavailable evidence).
EXIT_CODES = {"PASS": 0, "FAIL": 1, "NOT_EVALUATED": 2}


def evaluate_rules(rules: object) -> str:
    """Inspect active effective rules; reject incomplete or malformed evidence."""
    if not isinstance(rules, list):
        return "NOT_EVALUATED"
    contexts: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("type"), str):
            return "NOT_EVALUATED"
        if rule["type"] != "required_status_checks":
            continue
        parameters = rule.get("parameters")
        if not isinstance(parameters, dict):
            return "NOT_EVALUATED"
        checks = parameters.get("required_status_checks")
        if not isinstance(checks, list):
            return "NOT_EVALUATED"
        for check in checks:
            if not isinstance(check, dict):
                return "NOT_EVALUATED"
            context = check.get("context")
            if not isinstance(context, str) or not context.strip():
                return "NOT_EVALUATED"
            contexts.add(context)
    return "PASS" if REQUIRED_CHECK in contexts else "FAIL"


def read_branch_rules(repository: str, branch: str) -> list:
    """GET all applicable active rules, including inherited rules, read-only.

    The API omits disabled/evaluate rulesets and performs branch matching.
    `gh api --help`: --paginate emits each page in sequence. Decode every
    JSON document, including with versions that predate --slurp. Never infer
    absence from a single page of rulesets.
    """
    endpoint = f"repos/{repository}/rules/branches/{quote(branch, safe='')}"
    result = subprocess.run(
        ["gh", "api", "--method", "GET", "--paginate", endpoint],
        check=True,
        capture_output=True,
        text=True,
    )
    remaining = result.stdout.strip()
    if not remaining:
        raise ValueError("Empty branch rules response")
    rules = []
    decoder = json.JSONDecoder()
    while remaining:
        page, end = decoder.raw_decode(remaining)
        if not isinstance(page, list):
            raise TypeError("Unreadable branch rules response")
        rules.extend(page)
        remaining = remaining[end:].lstrip()
    return rules


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo", help="Repository in organization/repository form")
    source.add_argument(
        "--rules-json", type=Path, help="Recorded effective branch rules"
    )
    parser.add_argument("--branch", default="main")
    args = parser.parse_args(argv)
    if args.repo and not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        parser.error("--repo must have organization/repository form")
    try:
        rules = (
            json.loads(args.rules_json.read_text(encoding="utf-8"))
            if args.rules_json is not None
            else read_branch_rules(args.repo, args.branch)
        )
        status = evaluate_rules(rules)
    except (OSError, TypeError, ValueError, subprocess.CalledProcessError):
        # Do not echo authentication diagnostics or server response bodies.
        status = "NOT_EVALUATED"
    messages = {
        "PASS": f"{REQUIRED_CHECK} is required by effective branch rules.",
        "FAIL": f"{REQUIRED_CHECK} is absent from effective branch rules.",
        "NOT_EVALUATED": "Effective branch rules could not be read or validated.",
    }
    print(f"{status}: {messages[status]}")
    return EXIT_CODES[status]


if __name__ == "__main__":
    raise SystemExit(main())
