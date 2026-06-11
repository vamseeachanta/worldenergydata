"""Asserts that live agent instruction docs (root CLAUDE.md + the .claude tree)
exist and are free of git merge-conflict markers.

Filed as durable enforcement against a recurring failure mode: unresolved
conflict blocks committed into agent docs. First seen in .claude/docs/agents.md
(commit 7493f543, resolved via issue #414); recurred 2026-06 in
.claude/skills/bsee-data-extractor/SKILL.md (resolved via #467/#468).

The claude-flow-era agents.md this test originally guarded was archived to
.claude/_archive/claude-flow-era/ in the 2026-06-11 provider rework
(workspace-hub#3040), so the guard now covers every live agent-doc surface
instead of that single file. Archived content is exempt by design.

Refs: worldenergydata#414, worldenergydata#467, workspace-hub#2719,
workspace-hub#3040.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_DIR = REPO_ROOT / ".claude"
ROOT_ADAPTER = REPO_ROOT / "CLAUDE.md"
NESTED_POINTER = CLAUDE_DIR / "CLAUDE.md"

# `<<<<<<< ` / `>>>>>>> ` always carry a trailing space + ref label in real
# conflicts; bare `=======` is excluded because it is also a valid Markdown
# setext-header underline.
CONFLICT_MARKER_PATTERN = re.compile(r"^(<<<<<<< |>>>>>>> )", re.MULTILINE)


def _live_agent_docs() -> list[Path]:
    docs = [ROOT_ADAPTER]
    if CLAUDE_DIR.is_dir():
        docs.extend(
            p for p in sorted(CLAUDE_DIR.rglob("*.md")) if "_archive" not in p.parts
        )
    return [p for p in docs if p.is_file()]


def test_adapter_docs_exist():
    """Root adapter and the nested .claude pointer must both exist."""
    assert ROOT_ADAPTER.is_file(), f"{ROOT_ADAPTER} missing"
    assert NESTED_POINTER.is_file(), f"{NESTED_POINTER} missing"


def test_live_agent_docs_have_no_conflict_markers():
    """No live agent doc may contain committed merge-conflict markers."""
    offenders: dict[str, int] = {}
    for doc in _live_agent_docs():
        body = doc.read_text(encoding="utf-8", errors="replace")
        matches = CONFLICT_MARKER_PATTERN.findall(body)
        if matches:
            offenders[str(doc.relative_to(REPO_ROOT))] = len(matches)
    assert (
        not offenders
    ), f"unresolved merge-conflict markers committed in agent docs: {offenders}"
