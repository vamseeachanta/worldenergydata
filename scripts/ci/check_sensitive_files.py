#!/usr/bin/env python3
"""Check changed filenames in a pull-request merge checkout; never read contents."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

# Policy: sensitive-files in .github/workflows/pr-validation.yml at the base
# revision of this extraction; issue #1321. Preserve its case-sensitive policy.
# Python uses \Z for absolute end: unlike $, it cannot match before a trailing
# newline. Source: Python re documentation, "Regular Expression Syntax".
# https://docs.python.org/3/library/re.html#regular-expression-syntax
SENSITIVE_PATTERNS = {
    "environment": re.compile(r"(^|/)\.env(\Z|\.)"),
    "private-key": re.compile(r"\.(pem|key|p12)\Z"),
    "secret-token": re.compile(r"secret|credential"),
    "ssh-key": re.compile(r"(^|/)(id_rsa|id_dsa)\Z"),
}


def changed_filenames(repo: Path) -> list[str]:
    """Compare the merge result with its first parent, including rename targets.

    Git gitrevisions, "Specifying Revisions": ^1 and ^2 select merge parents.
    Git git-diff, "Options": -z preserves filenames, lowercase d excludes only
    deletions, and --no-renames exposes destinations as additions.
    https://git-scm.com/docs/gitrevisions
    https://git-scm.com/docs/git-diff
    """
    try:
        for parent in ("HEAD^1", "HEAD^2"):
            subprocess.run(
                ["git", "rev-parse", "--verify", parent],
                cwd=repo,
                check=True,
                stdout=subprocess.PIPE,
            )
    except subprocess.CalledProcessError as error:
        raise ValueError(
            "Expected the pull_request merge ref with both parents."
        ) from error
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--no-renames",
                "--diff-filter=d",
                "-z",
                "HEAD^1",
                "HEAD",
                "--",
            ],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as error:
        raise ValueError("Unable to compute PR filename diff.") from error
    return [os.fsdecode(name) for name in result.stdout.split(b"\0") if name]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        filenames = changed_filenames(args.repo)
    except (OSError, ValueError) as error:
        print(f"::error::{error}")
        return 1
    found = False
    for filename in filenames:
        if any(pattern.search(filename) for pattern in SENSITIVE_PATTERNS.values()):
            # Escape control characters and Actions' percent escapes so a
            # filename cannot add annotations. Actions toolkit command escaping:
            # https://github.com/actions/toolkit/blob/main/packages/core/src/command.ts
            escaped = json.dumps(filename, ensure_ascii=True).replace("%", "%25")
            print(f"::error::Potentially sensitive filename: {escaped}")
            found = True
    if found:
        return 1
    print("No potentially sensitive filenames in PR changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
