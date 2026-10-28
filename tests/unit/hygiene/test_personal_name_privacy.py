"""Prevent personal-name disclosures in tracked text without publishing the name."""

import hashlib
import os
import re
import subprocess
from pathlib import Path

import pytest

# A digest keeps the protected word out of the rule and its diagnostics.
PERSONAL_NAME_SHA256 = (
    "229198ac50189365a5dd6412995ab24b4126c777fd69673153f92a0b1ba46882"
)
PERSONAL_NAME_LENGTH = 4
RULE = "personal-name-privacy"


def _matching_paths(root, paths, digest, length):
    word = re.compile(rf"(?<!\w)\w{{{length}}}(?!\w)")
    matches = []
    for relative in paths:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        content = path.read_bytes()
        if b"\0" in content:
            continue
        text = content.decode("utf-8", errors="replace")
        if any(
            hashlib.sha256(token.casefold().encode("utf-8")).hexdigest() == digest
            for token in word.findall(text)
        ):
            matches.append(relative)
    return sorted(matches)


def test_tracked_text_has_no_personal_name():
    root = Path(__file__).resolve().parents[3]
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, env=env, capture_output=True, check=True
    )
    paths = [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]
    matches = _matching_paths(root, paths, PERSONAL_NAME_SHA256, PERSONAL_NAME_LENGTH)
    if matches:
        pytest.fail(RULE + ":\n" + "\n".join(matches), pytrace=False)


@pytest.mark.parametrize(
    ("content", "matches"),
    [
        (b"sampleword", True),
        (b"SAMPLEWORD", True),
        (b"(Sampleword).", True),
        (b"prefixsampleword samplewords prefix_sampleword", False),
        (b"sampleword\0binary", False),
        (b"\xff sampleword", True),
    ],
)
def test_privacy_rule_word_boundaries_and_text_detection(tmp_path, content, matches):
    relative = "example.txt"
    (tmp_path / relative).write_bytes(content)
    digest = hashlib.sha256(b"sampleword").hexdigest()
    assert _matching_paths(tmp_path, [relative], digest, 10) == (
        [relative] if matches else []
    )


def test_privacy_scan_ignores_inherited_git_bindings(monkeypatch, tmp_path):
    unrelated = str(tmp_path / "unrelated")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        monkeypatch.setenv(key, unrelated)
    test_tracked_text_has_no_personal_name()
