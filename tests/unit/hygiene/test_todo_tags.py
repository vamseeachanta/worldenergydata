"""Reject personal todo tags without exposing their contents in diagnostics."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RULE = "todo-personal-tag"
PERSONAL_TAG = re.compile(r"#[0-9]{1,3}_[a-z]+")


def tagged_todo(text):
    """Include sibling tags anywhere in a file containing a todo marker."""
    return "#todo" in text and PERSONAL_TAG.search(text) is not None


def tagged_paths(root):
    """Read only tracked text candidates, independently of caller Git bindings."""
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)
    result = subprocess.run(
        ["git", "grep", "-I", "-l", "-z", "-F", "#todo", "--"],
        cwd=root,
        env=env,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        pytest.fail(f"{RULE}: tracked-text scan failed", pytrace=False)
    paths = []
    for name in result.stdout.split(b"\0"):
        if not name:
            continue
        relative = os.fsdecode(name)
        with (root / relative).open(
            encoding="utf-8", errors="surrogateescape", newline="\n"
        ) as stream:
            if tagged_todo(stream.read()):
                paths.append(relative)
    return sorted(paths)


def test_tracked_text_has_no_personal_todo_tags():
    paths = tagged_paths(ROOT)
    if paths:
        pytest.fail("\n".join(f"{path}: {RULE}" for path in paths), pytrace=False)


@pytest.mark.parametrize(
    ("placement", "expected"),
    [("inline", True), ("before", True), ("after", True), ("no-todo", False)],
)
def test_personal_tag_forms(placement, expected):
    tag = "#" + "12" + "_" + "example"
    text = {
        "inline": "#todo " + tag + " keep this task",
        "before": tag + "\n#todo keep this task",
        "after": "#todo keep this task\n" + tag,
        "no-todo": tag,
    }[placement]
    assert tagged_todo(text) is expected


@pytest.mark.parametrize("text", ["#todo keep this task", "#todo see #123", ""])
def test_plain_todos_are_allowed(text):
    assert not tagged_todo(text)
