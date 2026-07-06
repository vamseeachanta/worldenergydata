#!/usr/bin/env python3
"""Read-only verifier for claimed-vs-shipped drift in recently-closed issues.

Motivation (issue #368): issues get closed and the work is assumed shipped, but
months-later audits expose that the claimed deliverable was never wired up (e.g.
#298 -> #359). This verifier re-examines recently-closed issues and surfaces
those whose machine-checkable claims are not observable in the live repo tree.

Cheap checks performed against each recently-closed issue body:
  1. Acceptance-criteria checkboxes: a closed issue that still has unchecked
     ``- [ ]`` boxes is flagged ("closed but acceptance criteria incomplete").
  2. Referenced file / test paths: backticked ``path/to/file.py`` or
     ``tests/...`` references that do not exist in the local repo tree are
     flagged ("claimed deliverable missing").

STRICTLY READ-ONLY. This script never edits, closes, comments on, reopens, or
labels any issue. It only reads issues via ``gh`` and reads the local tree.
It writes a markdown report and exits non-zero when drift is found, so it can
gate a CI/cron cadence.

The parsing + checking logic is implemented as pure functions
(``find_unchecked_acceptance_boxes``, ``extract_referenced_paths``,
``analyze_issue``) that take issue-body text plus an injected
path-existence checker, so they are deterministically unit-testable without any
live ``gh`` calls or filesystem access.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Sequence

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DEFAULT_OWNER_REPO = "vamseeachanta/worldenergydata"
DEFAULT_SINCE_DAYS = 30
DEFAULT_MAX_ISSUES = 40
REPORT_DIR = Path("reports/hygiene")

# Unchecked / checked acceptance-criteria checkbox lines.
#   - [ ] foo   (unchecked)   - [x] foo   (checked)
_UNCHECKED_RE = re.compile(r"^\s*[-*]\s+\[\s\]\s+(.*\S.*)$", re.MULTILINE)
_CHECKED_RE = re.compile(r"^\s*[-*]\s+\[[xX]\]\s+(.*\S.*)$", re.MULTILINE)

# Inline-code spans: `...`. We extract candidate paths from these.
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")

# A path looks like a file path if it contains a "/" and ends in a known source
# extension, OR it starts with a known repo top-level dir. Heuristic only.
_PATH_EXT_RE = re.compile(
    r"\.(py|sh|ps1|yml|yaml|json|md|cfg|ini|toml|txt|csv|sql)$",
    re.IGNORECASE,
)
_REPO_TOPDIRS = (
    "scripts/",
    "src/",
    "tests/",
    "test/",
    "data/",
    "reports/",
    "docs/",
    "config/",
    ".github/",
)


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class IssueRef:
    """A recently-closed issue fetched from gh (only fields we use)."""

    number: int
    title: str
    body: str
    closed_at: str = ""
    url: str = ""


@dataclass(frozen=True)
class IssueFinding:
    """The verifier's verdict for one issue."""

    number: int
    title: str
    url: str
    unchecked_boxes: tuple[str, ...] = ()
    missing_paths: tuple[str, ...] = ()

    @property
    def has_drift(self) -> bool:
        return bool(self.unchecked_boxes) or bool(self.missing_paths)


# --------------------------------------------------------------------------- #
# Pure parsing / checking logic (unit-tested, no gh / no real fs required)
# --------------------------------------------------------------------------- #


def find_unchecked_acceptance_boxes(body: str) -> list[str]:
    """Return the text of every unchecked ``- [ ]`` checkbox in the body.

    Pure: depends only on the input string. Order-preserving.
    """
    if not body:
        return []
    return [m.strip() for m in _UNCHECKED_RE.findall(body)]


def find_checked_acceptance_boxes(body: str) -> list[str]:
    """Return the text of every checked ``- [x]`` checkbox in the body."""
    if not body:
        return []
    return [m.strip() for m in _CHECKED_RE.findall(body)]


def _looks_like_path(token: str) -> bool:
    """Heuristic: does a backticked token look like a repo file/test path?"""
    token = token.strip()
    if not token or " " in token or "\t" in token:
        return False
    # Disqualify obvious non-paths (commands, urls, globs we can't test).
    if token.startswith(("http://", "https://", "-", "$", "#")):
        return False
    if any(c in token for c in "*?<>|"):
        return False
    if token.startswith(_REPO_TOPDIRS):
        return True
    # path-with-slash ending in a known source extension
    if "/" in token and _PATH_EXT_RE.search(token):
        return True
    return False


def extract_referenced_paths(body: str) -> list[str]:
    """Extract candidate repo file/test paths from backticked spans in a body.

    Pure: deterministic, de-duplicated, order-preserving. Leading ``./`` is
    normalized away so existence checks are relative to the repo root.
    """
    if not body:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in _BACKTICK_RE.findall(body):
        token = raw.strip()
        # strip a trailing ) or , or . that markdown sometimes glues on
        token = token.rstrip(").,;:")
        if token.startswith("./"):
            token = token[2:]
        if _looks_like_path(token) and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def analyze_issue(
    issue: IssueRef,
    path_exists: Callable[[str], bool],
) -> IssueFinding:
    """Apply the cheap checks to one closed issue.

    Pure given an injected ``path_exists`` checker:
      * unchecked acceptance boxes -> flagged
      * referenced paths that fail ``path_exists`` -> flagged

    No gh calls, no real filesystem access (the checker is injected).
    """
    unchecked = tuple(find_unchecked_acceptance_boxes(issue.body))
    referenced = extract_referenced_paths(issue.body)
    missing = tuple(p for p in referenced if not path_exists(p))
    return IssueFinding(
        number=issue.number,
        title=issue.title,
        url=issue.url,
        unchecked_boxes=unchecked,
        missing_paths=missing,
    )


def make_repo_path_checker(repo_root: Path) -> Callable[[str], bool]:
    """Build a path-existence checker rooted at ``repo_root`` (path traversal-safe)."""
    root = repo_root.resolve()

    def _exists(rel: str) -> bool:
        candidate = (root / rel).resolve()
        # Stay inside the repo; a "../" escape is treated as not-found.
        try:
            candidate.relative_to(root)
        except ValueError:
            return False
        return candidate.exists()

    return _exists


# --------------------------------------------------------------------------- #
# gh integration (read-only) + report rendering
# --------------------------------------------------------------------------- #


def fetch_recent_closed_issues(
    owner_repo: str,
    since_days: int,
    max_issues: int,
    runner: Callable[[Sequence[str]], str] | None = None,
) -> list[IssueRef]:
    """Fetch recently-closed issues via ``gh`` (READ-ONLY).

    ``runner`` is injectable for testing; by default it shells out to ``gh``.
    """
    run = runner or _default_gh_runner
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    cmd = [
        "gh",
        "issue",
        "list",
        "-R",
        owner_repo,
        "--state",
        "closed",
        "--limit",
        str(max_issues),
        "--search",
        f"closed:>={since[:10]}",
        "--json",
        "number,title,body,closedAt,url",
    ]
    raw = run(cmd)
    data = json.loads(raw) if raw.strip() else []
    issues: list[IssueRef] = []
    for item in data:
        issues.append(
            IssueRef(
                number=int(item.get("number", 0)),
                title=str(item.get("title", "")),
                body=str(item.get("body") or ""),
                closed_at=str(item.get("closedAt") or ""),
                url=str(item.get("url") or ""),
            )
        )
    return issues


def _default_gh_runner(cmd: Sequence[str]) -> str:
    proc = subprocess.run(
        list(cmd),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh failed ({proc.returncode}): {proc.stderr.strip()[:300]}"
        )
    return proc.stdout


def render_report(
    findings: Sequence[IssueFinding],
    *,
    owner_repo: str,
    since_days: int,
    scanned: int,
    today: str | None = None,
) -> str:
    """Render the markdown drift report (pure)."""
    today = today or date.today().isoformat()
    drifted = [f for f in findings if f.has_drift]
    lines: list[str] = []
    lines.append(f"# Recently-closed issue drift report — {today}")
    lines.append("")
    lines.append(f"- Repo: `{owner_repo}`")
    lines.append(f"- Window: issues closed in the last {since_days} days")
    lines.append(f"- Issues scanned: {scanned}")
    lines.append(f"- Issues with drift: {len(drifted)}")
    lines.append("")
    lines.append(
        "_Read-only verifier (#368). Drift = a closed issue with unchecked "
        "acceptance boxes or a claimed file/test path missing from the tree. "
        "Human decides whether to reopen._"
    )
    lines.append("")
    if not drifted:
        lines.append("No claimed-vs-shipped drift detected. ✅")
        lines.append("")
        return "\n".join(lines)

    for f in drifted:
        heading = f"## #{f.number} — {f.title}"
        lines.append(heading)
        if f.url:
            lines.append(f"{f.url}")
        lines.append("")
        if f.missing_paths:
            lines.append(
                "**Claimed deliverable missing (referenced but not in tree):**"
            )
            for p in f.missing_paths:
                lines.append(f"- `{p}`")
            lines.append("")
        if f.unchecked_boxes:
            lines.append("**Closed but acceptance criteria still unchecked:**")
            for b in f.unchecked_boxes:
                lines.append(f"- [ ] {b}")
            lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_OWNER_REPO)
    parser.add_argument("--since-days", type=int, default=DEFAULT_SINCE_DAYS)
    parser.add_argument("--max-issues", type=int, default=DEFAULT_MAX_ISSUES)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Local repo root used for path-existence checks.",
    )
    parser.add_argument(
        "--report-dir",
        default=str(REPORT_DIR),
        help="Directory to write the markdown report into.",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Print to stdout only; do not write a report file.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    path_exists = make_repo_path_checker(repo_root)

    try:
        issues = fetch_recent_closed_issues(args.repo, args.since_days, args.max_issues)
    except Exception as exc:  # pragma: no cover - network/gh failure path
        print(f"ERROR: could not fetch closed issues: {exc}", file=sys.stderr)
        return 2

    findings = [analyze_issue(i, path_exists) for i in issues]
    report = render_report(
        findings,
        owner_repo=args.repo,
        since_days=args.since_days,
        scanned=len(issues),
    )

    if not args.no_report:
        report_dir = Path(args.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        out = report_dir / f"verify_recent_closures_{date.today().isoformat()}.md"
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {out}", file=sys.stderr)

    print(report)

    drifted = [f for f in findings if f.has_drift]
    # Exit non-zero when drift found, so CI/cron can gate on it.
    return 1 if drifted else 0


if __name__ == "__main__":
    raise SystemExit(main())
