"""Asserts that .claude/docs/agents.md remains free of git merge-conflict markers
and renders as valid Markdown.

Filed as durable enforcement against a recurring failure mode. The conflict-
introducing commit was 7493f543 ("chore: fresh repo after slimming") which left
two unresolved conflict blocks in the file. Resolution landed via issue #414.

Refs: worldenergydata#414, workspace-hub#2719 (audit that surfaced the bug).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DOC = REPO_ROOT / ".claude" / "docs" / "agents.md"

CONFLICT_MARKER_PATTERN = re.compile(r"^(<<<<<<< |=======$|>>>>>>> )", re.MULTILINE)


def test_agent_doc_exists():
    """The agents.md reference doc must exist."""
    assert AGENTS_DOC.exists(), f"{AGENTS_DOC} missing"


def test_agent_doc_no_conflict_markers():
    """The agents.md must not contain git merge-conflict markers."""
    body = AGENTS_DOC.read_text(encoding="utf-8")
    matches = CONFLICT_MARKER_PATTERN.findall(body)
    assert not matches, (
        f"{AGENTS_DOC.relative_to(REPO_ROOT)} contains {len(matches)} conflict marker(s); "
        f"unresolved merge conflict regression"
    )


def test_agent_doc_starts_with_canonical_header():
    """The agents.md must lead with the documented title — guards against accidental truncation."""
    body = AGENTS_DOC.read_text(encoding="utf-8")
    assert body.startswith("# Available Agents Reference"), (
        f"{AGENTS_DOC.relative_to(REPO_ROOT)} missing canonical title — file may be corrupted"
    )


def test_agent_doc_has_no_empty_section_headers():
    """No `## ...` line followed immediately by another `## ...` (sign of dropped content during conflict resolution)."""
    body = AGENTS_DOC.read_text(encoding="utf-8")
    lines = body.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("## ") and lines[i + 1].startswith("## "):
            raise AssertionError(
                f"{AGENTS_DOC.relative_to(REPO_ROOT)}:{i + 1} — section header '{line}' "
                f"is followed immediately by another header; section body is missing"
            )
